"""Run with python3 -m unittest discover -s tests; no Blender/dependencies needed."""
import importlib.util
from concurrent.futures import ThreadPoolExecutor
import json
import pathlib
import sys
import tempfile
import threading
import time
import types
import unittest
import urllib.request
import urllib.error
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
for name, path in [('ATBridge', ROOT), ('ATBridge.utils', ROOT/'utils'), ('ATBridge.companion', ROOT/'companion')]:
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    sys.modules[name] = module
from ATBridge.companion.bridge import Bridge
from ATBridge.utils.zip_safety import validate_zip

ORIGIN = 'chrome-extension://' + 'a'*32


class BridgeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name).resolve()
        self.bridge = Bridge(self.root/'downloads', self.root/'cache', port=0)
        self.bridge.start()

    def tearDown(self):
        self.bridge.stop()
        self.temp.cleanup()

    def request(self, path, body=None, origin=ORIGIN, token=None):
        req = urllib.request.Request('http://127.0.0.1:%s%s' % (self.bridge.port, path),
            data=json.dumps(body or {}).encode(), headers={'Origin': origin,
            'Authorization': 'Bearer ' + (token if token is not None else self.bridge.token),
            'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            with error:
                return error.code, json.load(error)

    def test_pairing_and_origin(self):
        self.assertEqual(self.request('/hello', origin='https://evil.example')[0], 403)
        self.assertEqual(self.request('/hello', token='wrong')[0], 401)
        self.assertEqual(self.request('/poll')[0], 409)
        self.assertEqual(self.request('/hello')[0], 200)
        self.assertEqual(self.request('/poll', origin='chrome-extension://'+'b'*32)[0], 403)

    def test_convenient_pairing_requires_blender_approval(self):
        self.assertEqual(self.request('/pair/request', token='')[1]['state'], 'closed')
        self.bridge.open_pairing()
        pair = self.request('/pair/request', token='')[1]
        self.assertEqual(pair['state'], 'pending')
        self.assertNotIn('token', pair)
        snapshot = self.bridge.pairing_snapshot()
        self.assertEqual(snapshot['code'], pair['code'])
        self.assertNotIn('ticket', snapshot)
        self.assertEqual(self.request('/pair/request', token='')[1]['state'], 'busy')
        body = {'ticket': pair['ticket']}
        self.assertEqual(self.request('/pair/status', body, token='')[1]['state'], 'pending')
        self.assertEqual(self.request('/pair/status', body, origin='chrome-extension://'+'b'*32, token='')[1]['state'], 'expired')
        self.bridge.decide_pairing(snapshot['id'], True)
        result = self.request('/pair/status', body, token='')[1]
        self.assertEqual(result['state'], 'approved')
        self.assertEqual(self.request('/hello', token=result['token'])[0], 200)
        self.assertEqual(self.request('/pair/status', body, token='')[1]['state'], 'expired')
        previous = result['token']
        self.bridge.open_pairing()
        self.assertEqual(self.request('/hello', token=previous)[0], 401)

    def test_pairing_denial_expiry_and_stale_approval(self):
        self.bridge.open_pairing()
        pair = self.request('/pair/request', token='')[1]
        snapshot = self.bridge.pairing_snapshot()
        self.bridge.decide_pairing(snapshot['id'], False)
        self.assertEqual(self.request('/pair/status', {'ticket': pair['ticket']}, token='')[1]['state'], 'denied')
        self.bridge.open_pairing()
        pair = self.request('/pair/request', token='')[1]
        with self.assertRaises(ValueError):
            self.bridge.decide_pairing(snapshot['id'], True)
        snapshot = self.bridge.pairing_snapshot()
        self.bridge.pair_until = time.monotonic() - 1
        with self.assertRaises(ValueError):
            self.bridge.decide_pairing(snapshot['id'], True)
        self.assertEqual(self.request('/pair/status', {'ticket': pair['ticket']}, token='')[1]['state'], 'expired')
        self.assertEqual(self.request('/pair/request', origin='https://www.fab.com', token='')[0], 403)

    def test_pair_cancel_releases_ticket_without_closing_window(self):
        self.bridge.open_pairing()
        window_deadline = self.bridge.pair_until
        first = self.request('/pair/request', token='')[1]
        self.assertEqual(self.request('/pair/cancel', {'ticket': first['ticket']}, token='')[1]['state'], 'cancelled')
        self.assertEqual(self.bridge.pair_until, window_deadline)

        retry = self.request('/pair/request', token='')[1]
        self.assertEqual(retry['state'], 'pending')
        self.assertNotEqual(retry['ticket'], first['ticket'])
        self.assertEqual(self.request('/pair/cancel', {'ticket': first['ticket']}, token='')[1]['state'], 'expired')
        self.assertEqual(self.request('/pair/status', {'ticket': retry['ticket']}, token='')[1]['state'], 'pending')

    def test_repair_waits_for_authenticated_dispatch_and_revokes_old_token(self):
        self.bridge.open_pairing()
        pair = self.request('/pair/request', token='')[1]
        snapshot = self.bridge.pairing_snapshot()
        self.bridge.decide_pairing(snapshot['id'], True)
        old_token = self.request('/pair/status', {'ticket': pair['ticket']}, token='')[1]['token']

        entered_poll, release_poll = threading.Event(), threading.Event()
        original_poll = self.bridge.poll

        def blocked_poll():
            entered_poll.set()
            if not release_poll.wait(2):
                raise AssertionError('test did not release blocked poll')
            return original_poll()

        self.bridge.poll = blocked_poll
        rotation_started, rotation_done = threading.Event(), threading.Event()
        submit_started, submit_done = threading.Event(), threading.Event()

        def rotate_pairing():
            rotation_started.set()
            self.bridge.open_pairing()
            rotation_done.set()

        def submit_job():
            submit_started.set()
            result = self.bridge.submit('search', query='new session')
            submit_done.set()
            return result

        with ThreadPoolExecutor(max_workers=3) as pool:
            poll_future = pool.submit(self.request, '/poll', None, ORIGIN, old_token)
            self.assertTrue(entered_poll.wait(1), 'authenticated poll did not reach dispatch')
            rotate_future = pool.submit(rotate_pairing)
            submit_future = pool.submit(submit_job)
            self.assertTrue(rotation_started.wait(1))
            self.assertTrue(submit_started.wait(1))
            self.assertFalse(rotation_done.wait(0.05), 'pairing rotation must wait for dispatch lock')
            self.assertFalse(submit_done.wait(0.05), 'new jobs must wait for dispatch lock')

            release_poll.set()
            self.assertEqual(poll_future.result(timeout=1)[0], 200)
            rotate_future.result(timeout=1)
            self.assertTrue(submit_future.result(timeout=1))

        self.assertEqual(self.request('/hello', token=old_token)[0], 401)

    def test_cancel_and_auth_error(self):
        self.request('/hello')
        ident = self.bridge.submit('search', query='rock')
        self.assertEqual(self.request('/poll')[1]['job']['id'], ident)
        self.request('/result', {'id': ident, 'error': 'AUTH_REQUIRED'})
        self.assertEqual(self.bridge.snapshot(ident)['error'], 'AUTH_REQUIRED')
        ident = self.bridge.submit('search', query='rock')
        self.request('/poll')
        self.bridge.cancel()
        self.assertEqual(self.request('/result', {'id': ident, 'data': {'items': []}})[0], 400)
        self.assertEqual(self.bridge.snapshot(ident)['status'], 'cancelled')

    def test_handoff_and_wrong_path(self):
        self.request('/hello')
        archive = self.root/'source.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('model.fbx', 'test fixture')
        ident = self.bridge.submit('download', name='asset_test.zip', size=archive.stat().st_size)
        self.request('/poll')
        self.assertEqual(self.request('/result', {'id':ident,'data':{'path':str(archive)}})[0],400)
        expected = self.root/'downloads'/'ATBridge'/ident/'asset_test.zip'
        expected.parent.mkdir(parents=True)
        expected.write_bytes(archive.read_bytes())
        entered, release = threading.Event(), threading.Event()
        handoff = self.bridge._handoff
        def blocked_handoff(job, data):
            entered.set()
            if not release.wait(3):
                raise TimeoutError('test did not release handoff')
            return handoff(job, data)
        self.bridge._handoff = blocked_handoff
        with ThreadPoolExecutor(max_workers=1) as pool:
            response = pool.submit(self.request, '/result', {'id':ident,'data':{'path':str(expected)}})
            self.assertTrue(entered.wait(1), 'background transfer did not start')
            self.assertEqual(response.result(timeout=1)[0], 200)
            self.assertEqual(self.bridge.snapshot(ident)['status'], 'transferring')
            self.assertEqual(self.request('/result', {'id':ident,'error':'DOWNLOAD_FAILED'})[0],400)
            release.set()
            deadline = time.monotonic() + 2
            while self.bridge.snapshot(ident)['status'] == 'transferring' and time.monotonic() < deadline:
                time.sleep(0.01)
        self.assertEqual(self.bridge.snapshot(ident)['status'], 'done')
        result = self.bridge.snapshot(ident)['data']
        self.assertEqual(pathlib.Path(result['path']).read_bytes(), archive.read_bytes())
        self.assertEqual(len(result['sha256']),64)
        self.assertEqual(self.request('/result', {'id':ident,'data':{'path':str(expected)}})[0],400)

    def test_cancel_during_transfer_never_publishes_cache(self):
        self.request('/hello')
        archive = self.root/'source.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('model.fbx', 'test fixture')
        ident = self.bridge.submit('download', name='asset_test.zip', size=archive.stat().st_size)
        self.request('/poll')
        expected = self.root/'downloads'/'ATBridge'/ident/'asset_test.zip'
        expected.parent.mkdir(parents=True)
        expected.write_bytes(archive.read_bytes())
        entered, release = threading.Event(), threading.Event()
        handoff = self.bridge._handoff
        def blocked_handoff(job, data):
            entered.set()
            if not release.wait(3):
                raise TimeoutError('test did not release handoff')
            return handoff(job, data)
        self.bridge._handoff = blocked_handoff
        try:
            self.assertEqual(self.request('/result', {'id':ident,'data':{'path':str(expected)}})[0],200)
            self.assertTrue(entered.wait(1), 'background transfer did not start')
            self.assertEqual(self.bridge.snapshot(ident)['status'], 'transferring')
            self.bridge.cancel()
        finally:
            release.set()
        deadline = time.monotonic() + 2
        while self.bridge.snapshot(ident)['status'] == 'transferring' and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(self.bridge.snapshot(ident)['status'], 'cancelled')
        self.assertFalse((self.root/'cache'/ident).exists())
        self.assertEqual(self.request('/result', {'id':ident,'data':{'path':str(expected)}})[0],400)

    def test_zip_traversal_and_symlink(self):
        for name, mode in [('../escape', 0), ('link', 0o120777 << 16), ('A/../../escape', 0)]:
            p=self.root/'bad.zip'
            with zipfile.ZipFile(p,'w') as z:
                i=zipfile.ZipInfo(name);i.external_attr=mode;z.writestr(i,'payload')
            with zipfile.ZipFile(p) as z:
                with self.assertRaises(ValueError): validate_zip(z)

    def test_timeout(self):
        ident = self.bridge.submit('search', query='rock')
        self.bridge.jobs[ident]['created'] -= 901
        self.assertIsNone(self.bridge.poll()['job'])
        self.assertEqual(self.bridge.snapshot(ident)['error'], 'TIMEOUT')

if __name__ == '__main__':
    unittest.main()
