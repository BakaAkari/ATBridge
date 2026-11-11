"""Loopback job transport; this module never imports bpy or reads browser cookies."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import threading
import time
import uuid
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ..utils.zip_safety import MAX_ARCHIVE, validate_zip

PORT = 28481
ORIGIN = re.compile(r'chrome-extension://[a-p]{32}\Z')
UUID = re.compile(r'[0-9a-f-]{36}\Z')
ERRORS = {'AUTH_REQUIRED', 'ACCESS_DENIED', 'RATE_LIMITED', 'NETWORK_ERROR',
          'SCHEMA_CHANGED', 'NOT_OWNED', 'UNSUPPORTED', 'DOWNLOAD_FAILED',
          'CANCELLED', 'NO_FAB_TAB', 'EXPIRED_URL'}


def safe_name(name):
    return (isinstance(name, str) and 0 < len(name) <= 180
            and name not in {'.', '..'} and not any(c in name for c in '/\\:')
            and not any(ord(c) < 32 for c in name) and name.lower().endswith('.zip'))


class Bridge:
    def __init__(self, downloads, cache, port=PORT):
        self.downloads = Path(downloads).expanduser().resolve()
        self.cache = Path(cache).expanduser().resolve()
        self.port = port
        self.token = secrets.token_hex(32)
        self.origin = None
        self.jobs = {}
        self.lock = threading.RLock()
        self.server = None
        self.last_seen = 0
        self.pair_until = 0
        self.pending_pair = None

    def start(self):
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def reply(self, status, body):
                raw = json.dumps(body).encode()
                self.send_response(status)
                origin = self.headers.get('Origin', '')
                if ORIGIN.fullmatch(origin):
                    self.send_header('Access-Control-Allow-Origin', origin)
                    self.send_header('Vary', 'Origin')
                self.send_header('Content-Type', 'application/json')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def valid_origin(self):
                return (ORIGIN.fullmatch(self.headers.get('Origin', ''))
                        and self.headers.get('Host') == '127.0.0.1:' + str(bridge.port))

            def do_OPTIONS(self):
                if not self.valid_origin():
                    return self.reply(403, {})
                self.send_response(204)
                self.send_header('Access-Control-Allow-Origin', self.headers['Origin'])
                self.send_header('Access-Control-Allow-Methods', 'POST')
                self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
                self.end_headers()

            def do_POST(self):
                if not self.valid_origin():
                    return self.reply(403, {'error': 'ORIGIN_REJECTED'})
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    if length < 0 or length > 256 * 1024:
                        return self.reply(413, {})
                    self.connection.settimeout(10)
                    body = json.loads(self.rfile.read(length) or b'{}')
                    if not isinstance(body, dict):
                        raise ValueError('Invalid body')
                    origin = self.headers['Origin']
                    if self.path in {'/pair/request', '/pair/status', '/pair/cancel'}:
                        if self.path == '/pair/request':
                            result = bridge.pair_request(origin)
                        else:
                            result = bridge.pair_status(origin, body.get('ticket'), cancel=self.path == '/pair/cancel')
                        return self.reply(200, result)
                    bearer = self.headers.get('Authorization', '')
                    with bridge.lock:
                        if not hmac.compare_digest(bearer, 'Bearer ' + bridge.token):
                            return self.reply(401, {'error': 'PAIRING_REQUIRED'})
                        if bridge.origin and bridge.origin != origin:
                            return self.reply(403, {'error': 'ORIGIN_REJECTED'})
                        if not bridge.origin and self.path != '/hello':
                            return self.reply(409, {'error': 'PAIR_FIRST'})
                        bridge.origin = origin
                        bridge.pending_pair = None
                        bridge.pair_until = 0
                        bridge.last_seen = time.monotonic()
                        if self.path == '/hello':
                            result = {'protocol': 1}
                        elif self.path == '/poll':
                            result = bridge.poll()
                        elif self.path == '/result':
                            bridge.complete(body)
                            result = {'accepted': True}
                        else:
                            return self.reply(404, {})
                    self.reply(200, result)
                except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile):
                    self.reply(400, {'error': 'INVALID_RESULT'})

        self.server = ThreadingHTTPServer(('127.0.0.1', self.port), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        self.cancel()
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=2)
            self.server = None
        self.token = secrets.token_hex(32)
        self.origin = None
        self.pending_pair = None
        self.pair_until = 0

    def open_pairing(self):
        """Explicit Blender user action revokes the previous connection."""
        with self.lock:
            self.cancel()
            self.token = secrets.token_hex(32)
            self.origin = None
            self.last_seen = 0
            self.pending_pair = None
            self.pair_until = time.monotonic() + 120

    def pairing_snapshot(self):
        with self.lock:
            if time.monotonic() >= self.pair_until:
                self.pending_pair = None
                return {'state': 'closed'}
            if self.pending_pair:
                return {k: self.pending_pair[k] for k in ('id', 'code', 'origin', 'state')}
            return {'state': 'waiting'}

    def pair_request(self, origin):
        with self.lock:
            if self.pairing_snapshot()['state'] == 'closed' or self.origin:
                return {'state': 'closed'}
            if self.pending_pair:
                return {'state': 'busy'}
            self.pending_pair = {'id': secrets.token_hex(8), 'ticket': secrets.token_hex(32),
                                 'code': '%06d' % secrets.randbelow(1000000),
                                 'origin': origin, 'state': 'pending'}
            return {k: self.pending_pair[k] for k in ('ticket', 'code', 'state')}

    def decide_pairing(self, request_id, allow):
        with self.lock:
            snapshot = self.pairing_snapshot()
            if snapshot['state'] != 'pending' or snapshot['id'] != request_id:
                raise ValueError('Pairing request expired; retry from Chrome')
            self.pending_pair['state'] = 'approved' if allow else 'denied'

    def pair_status(self, origin, ticket, cancel=False):
        with self.lock:
            self.pairing_snapshot()
            pending = self.pending_pair
            if (not pending or not isinstance(ticket, str) or pending['origin'] != origin
                    or not hmac.compare_digest(pending['ticket'], ticket)):
                return {'state': 'expired'}
            if cancel:
                self.pending_pair = None
                return {'state': 'cancelled'}
            state = pending['state']
            if state in {'approved', 'denied'}:
                self.pending_pair = None
                self.pair_until = 0
            if state == 'approved':
                self.origin = origin
                return {'state': 'approved', 'token': self.token}
            return {'state': state}

    def submit(self, action, **params):
        if action not in {'search', 'files', 'download'}:
            raise ValueError('Unknown action')
        with self.lock:
            if any(j['status'] in {'queued', 'running', 'transferring'} for j in self.jobs.values()):
                raise ValueError('A request is already active')
            if len(self.jobs) >= 100:
                raise ValueError('Restart companion after 100 prototype requests')
            job_id = uuid.uuid4().hex
            self.jobs[job_id] = dict(id=job_id, action=action, params=params,
                                    status='queued', created=time.monotonic())
            return job_id

    def cancel(self):
        with self.lock:
            for job in self.jobs.values():
                if job['status'] in {'queued', 'running', 'transferring'}:
                    job['status'] = 'cancelled'

    def poll(self):
        with self.lock:
            now = time.monotonic()
            for job in self.jobs.values():
                if job['status'] in {'queued', 'running', 'transferring'} and now-job['created'] > 900:
                    job['status'] = 'error'
                    job['error'] = 'TIMEOUT'
            active = [j['id'] for j in self.jobs.values() if j['status'] in {'running', 'transferring'}]
            for job in self.jobs.values():
                if job['status'] == 'queued':
                    job['status'] = 'running'
                    return {'job': {k: job[k] for k in ('id', 'action', 'params')},
                            'active': active + [job['id']]}
            return {'job': None, 'active': active}

    def snapshot(self, job_id):
        with self.lock:
            job = self.jobs[job_id]
            if job['status'] in {'queued', 'running', 'transferring'} and time.monotonic()-job['created'] > 900:
                job.update(status='error', error='TIMEOUT')
            return dict(job)

    def complete(self, body):
        with self.lock:
            job = self.jobs[body['id']]
            if job['status'] != 'running':
                raise ValueError('Stale result')
            if body.get('error'):
                code = body['error']
                job.update(status='error', error=code if code in ERRORS else 'NETWORK_ERROR')
                return
            data = body['data']
            if job['action'] == 'download':
                self._download_source(job, data)
                job['status'] = 'transferring'
                threading.Thread(target=self._transfer, args=(dict(job), dict(data)), daemon=True).start()
                return
            elif job['action'] == 'search':
                rows = data['items']
                if not isinstance(rows, list) or len(rows) > 24:
                    raise ValueError('Invalid search result')
                data = {'items': [{'uid': self._uid(x['uid']), 'title': str(x['title'])[:200]}
                                  for x in rows], 'cursor': str(data.get('cursor') or '')[:1024]}
            elif job['action'] == 'files':
                rows = data['files']
                if not isinstance(rows, list) or len(rows) > 100:
                    raise ValueError('Invalid files result')
                data = {'owned': data.get('owned') is True, 'files': [
                    {'uid': self._uid(x['uid']), 'name': x['name'], 'size': int(x['size'])}
                    for x in rows if safe_name(x.get('name')) and 0 < int(x['size']) <= MAX_ARCHIVE]}
            job.update(status='done', data=data)

    def _transfer(self, job, data):
        transferred = None
        try:
            transferred = self._handoff(job, data)
            with self.lock:
                current = self.jobs[job['id']]
                if current['status'] == 'transferring':
                    current.update(status='done', data=transferred)
                    return
        except Exception:
            with self.lock:
                current = self.jobs[job['id']]
                if current['status'] == 'transferring':
                    current.update(status='error', error='HANDOFF_FAILED')
        if transferred:
            # Only remove the private result produced by this cancelled transfer.
            path = Path(transferred['path'])
            try:
                path.unlink()
                path.parent.rmdir()
            except OSError:
                pass

    @staticmethod
    def _uid(value):
        if not isinstance(value, str) or not UUID.fullmatch(value):
            raise ValueError('Invalid uid')
        uuid.UUID(value)
        return value

    def _download_source(self, job, data):
        name = job['params']['name']
        if not safe_name(name):
            raise ValueError('Invalid filename')
        source = Path(data['path'])
        expected = self.downloads / 'ATBridge' / job['id'] / name
        if (source != expected or source.is_symlink() or source.resolve() != expected
                or not source.is_file()):
            raise ValueError('Unexpected download path')
        size = source.stat().st_size
        if size != job['params']['size'] or not 0 < size <= MAX_ARCHIVE:
            raise ValueError('Download size mismatch')
        return source, name, size

    def _handoff(self, job, data):
        source, name, size = self._download_source(job, data)
        destination = self.cache / job['id']
        destination.mkdir(parents=True, exist_ok=False)
        partial = destination / (name + '.part')
        final = destination / name
        try:
            with source.open('rb') as src, partial.open('xb') as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)
            if partial.stat().st_size != size:
                raise ValueError('Copy size mismatch')
            with zipfile.ZipFile(partial) as archive:
                validate_zip(archive)
                if archive.testzip():
                    raise ValueError('ZIP CRC failure')
            digest = hashlib.sha256()
            with partial.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
            os.replace(str(partial), str(final))
            return {'path': str(final), 'size': size, 'sha256': digest.hexdigest()}
        except Exception:
            if partial.exists():
                partial.unlink()
            destination.rmdir()
            raise
