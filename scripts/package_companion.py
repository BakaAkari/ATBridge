"""Build the Chrome upload ZIP locally. Never uploads or installs anything."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'companion' / 'extension'
FILES = ['manifest.json', 'connect.html', 'connect.mjs', 'fab-client.mjs', 'worker.js', 'style.css']


def main():
    manifest = json.loads((SOURCE / 'manifest.json').read_text())
    assert manifest['manifest_version'] == 3
    assert set(manifest['permissions']) == {'scripting', 'downloads'}
    assert set(manifest['host_permissions']) == {'https://www.fab.com/*', 'http://127.0.0.1/*'}
    files = sorted(FILES + list(manifest['icons'].values()))
    output = ROOT / 'dist' / ('atbridge-chrome-companion-' + manifest['version'] + '.zip')
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            source = SOURCE / name
            if source.is_symlink() or not source.is_file():
                raise ValueError('Missing or unsafe package file: ' + name)
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_text(digest + '  ' + output.name + '\n')
    print(str(output))
    print('SHA256 ' + digest)


if __name__ == '__main__':
    main()
