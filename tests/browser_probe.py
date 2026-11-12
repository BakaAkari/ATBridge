"""Run the actual WebView2 helper twice against a local download/cookie fixture.

No Fab account, external website, browser extension, or Blender is involved.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = ROOT / 'dist' / 'fab-browser'
MARKER = BUILD_ROOT / 'current.txt'
EXECUTABLE = BUILD_ROOT / MARKER.read_text().strip() / 'ATBridge.FabBrowser.exe' if MARKER.is_file() else BUILD_ROOT / 'ATBridge.FabBrowser.exe'


def main():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('fixture.bin', bytes(range(256)) * 2048, compress_type=zipfile.ZIP_STORED)
    payload = buffer.getvalue()
    cookies = []
    state = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path == '/fixture.zip':
                self.send_response(200)
                self.send_header('Content-Type', 'application/zip')
                self.send_header('Content-Disposition', 'attachment; filename="renamed (1).zip"')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                state['download_started'].set()
                try:
                    # Keep the transfer active well past the popup's page-requested close.
                    for offset in range(0, len(payload), 8192):
                        self.wfile.write(payload[offset:offset + 8192])
                        self.wfile.flush()
                        time.sleep(0.04)
                    state['download_finished'].set()
                except (BrokenPipeError, ConnectionResetError):
                    state['download_interrupted'].set()
            elif self.path == '/close-requested':
                state['close_requested'].set()
                self.send_response(204)
                self.end_headers()
            elif self.path == '/popup-closed':
                state['popup_closed'].set()
                self.send_response(204)
                self.end_headers()
            elif self.path == '/popup':
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(b'''<!doctype html><title>ATBridge popup probe</title>
                    <h1>Popup fixture</h1><a id="download" href="/fixture.zip" download>Download</a>
                    <script>
                    setTimeout(() => document.querySelector('#download').click(), 100);
                    setTimeout(() => fetch('/close-requested').then(() => window.close()), 1000);
                    </script>''')
            elif self.path == '/close':
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(b'''<!doctype html><title>Popup closure probe</title>
                    <script>setTimeout(() => window.close(), 300)</script>''')
            else:
                if self.path == '/':
                    cookies.append(self.headers.get('Cookie', ''))
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Set-Cookie', 'atbridge_probe=ready; Path=/; Max-Age=3600; SameSite=Lax')
                self.end_headers()
                self.wfile.write(b'''<!doctype html><title>ATBridge local probe</title>
                    <h1>Local fixture</h1>
                    <script>setTimeout(() => {
                        const popup = window.open('/close');
                        const timer = setInterval(() => {
                            if (popup.closed) {
                                clearInterval(timer);
                                const downloadPopup = window.open('/popup');
                                const downloadTimer = setInterval(() => {
                                    if (downloadPopup.closed) {
                                        clearInterval(downloadTimer);
                                        fetch('/popup-closed');
                                    }
                                }, 50);
                            }
                        }, 100);
                    }, 700)</script>''')

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with tempfile.TemporaryDirectory(prefix='atbridge-browser-probe-', ignore_cleanup_errors=True) as directory:
            root = Path(directory)
            for run in range(2):
                state.update({
                    'download_started': threading.Event(),
                    'download_finished': threading.Event(),
                    'download_interrupted': threading.Event(),
                    'close_requested': threading.Event(),
                    'popup_closed': threading.Event(),
                })
                cookies.clear()
                report = root / ('report-%d.json' % run)
                process = subprocess.Popen([str(EXECUTABLE), '--profile', str(root / 'profile'),
                    '--downloads', str(root / 'downloads'), '--probe-url', 'http://127.0.0.1:%d/' % server.server_port,
                    '--probe-report', str(report)])
                try:
                    assert state['download_started'].wait(timeout=15), 'Popup did not start the ZIP download'
                    assert state['close_requested'].wait(timeout=10), 'Download popup did not request page close'
                    while not state['download_finished'].wait(timeout=0.02):
                        assert not report.exists(), 'Native report was written while the closing popup download was active'
                        assert not state['download_interrupted'].is_set(), 'Closing popup interrupted its active download'
                    assert process.wait(timeout=45) == 0, 'Native probe process failed'
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    raise AssertionError('Native probe timed out')
                except BaseException:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
                    raise
                assert state['popup_closed'].wait(timeout=5), 'Opener did not observe the download popup close'
                result = json.loads(report.read_text())
                assert result['passed'], result
                downloaded = Path(result['result'])
                assert downloaded.read_bytes() == payload, 'Download changed in transit'
                assert downloaded.suffix == '.zip' and not Path(str(downloaded) + '.partial').exists()
                if run:
                    assert cookies and 'atbridge_probe=ready' in cookies[0], 'Profile cookie did not persist'
            assert len(list((root / 'downloads' / 'ATBridge').glob('*/*.zip'))) == 2
            print('PASS: page-close deferral during streamed ZIP download, opener observes popup closure, atomic ZIP publication, duplicate names, persistent fixture cookie, native bridge disabled')
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
