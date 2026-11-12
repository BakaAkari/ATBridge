#!/usr/bin/env python3
"""Build release packages (Windows / macOS / Linux).

  python3 scripts/package.py [--suffix beta.1] [--skip-browser]

Output in dist/release/<tag>/:
  ATBridge_<tag>.zip              add-on only (all platforms)
  ATBridge_<tag>_windows-x64.zip  add-on + self-contained Fab browser (needs .NET 10 SDK; cross-builds on macOS)
  SHA256SUMS.txt
"""
import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Only runtime add-on content goes into the package.
INCLUDE = ['__init__.py', 'config.py', 'LICENSE', 'assets', 'compat', 'core', 'locales', 'operators',
           'preferences', 'properties', 'server', 'state', 'tools', 'ui', 'utils']
SKIP_NAMES = {'__pycache__', '.DS_Store'}
SKIP_SUFFIXES = {'.pyc', '.pyo'}


def addon_version():
    text = (ROOT / '__init__.py').read_text(encoding='utf-8')
    m = re.search(r'"version":\s*\((\d+),\s*(\d+),\s*(\d+)\)', text)
    if not m:
        sys.exit('bl_info version not found')
    return '.'.join(m.groups())


def files_under(path):
    if path.is_file():
        yield path
        return
    for p in sorted(path.rglob('*')):
        if p.is_file() and not (set(p.relative_to(ROOT).parts) & SKIP_NAMES) and p.suffix not in SKIP_SUFFIXES:
            yield p


def write_zip(target, extra=None):
    # Fixed timestamps and sorted entries keep the archive reproducible across machines.
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for item in INCLUDE:
            src = ROOT / item
            if not src.exists():
                sys.exit(f'missing package item: {item}')
            for f in files_under(src):
                info = zipfile.ZipInfo('ATBridge/' + f.relative_to(ROOT).as_posix(), (2020, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                info.create_system = 3  # same header on every OS
                z.writestr(info, f.read_bytes())
        if extra:
            base, prefix = extra
            for f in sorted(p for p in base.rglob('*') if p.is_file()):
                info = zipfile.ZipInfo(f'ATBridge/{prefix}/' + f.relative_to(base).as_posix(), (2020, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o755 << 16 if f.suffix == '.exe' else 0o644 << 16
                info.create_system = 3
                z.writestr(info, f.read_bytes())


def publish_browser(version, out):
    dotnet = shutil.which('dotnet') or str(Path.home() / '.dotnet' / 'dotnet')
    if not Path(dotnet).exists() and not shutil.which('dotnet'):
        sys.exit('dotnet not found: install the .NET 10 SDK or pass --skip-browser')
    subprocess.run([dotnet, 'publish', str(ROOT / 'browser' / 'ATBridge.FabBrowser.csproj'), '-c', 'Release',
                    '-r', 'win-x64', '--self-contained', 'true', f'-p:Version={version}', '-p:DebugType=none',
                    '-p:EnableWindowsTargeting=true', '-o', str(out)], check=True)
    if not (out / 'ATBridge.FabBrowser.exe').is_file():
        sys.exit('browser executable missing after publish')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--suffix', default='')
    ap.add_argument('--skip-browser', action='store_true')
    a = ap.parse_args()
    version = addon_version()
    tag = f'v{version}-{a.suffix}' if a.suffix else f'v{version}'
    out = ROOT / 'dist' / 'release' / tag
    out.mkdir(parents=True, exist_ok=True)
    # Replace only previous packages; never wipe the folder (it may be open in a file browser).
    for old in list(out.glob('ATBridge_*.zip')) + [out / 'SHA256SUMS.txt']:
        old.unlink(missing_ok=True)

    zips = [out / f'ATBridge_{tag}.zip']
    write_zip(zips[0])
    if not a.skip_browser:
        build = ROOT / 'dist' / 'release' / f'.browser-{tag}'
        shutil.rmtree(build, ignore_errors=True)
        publish_browser(version, build)
        zips.append(out / f'ATBridge_{tag}_windows-x64.zip')
        write_zip(zips[1], (build, 'bin/fab-browser'))
        shutil.rmtree(build, ignore_errors=True)

    sums = [f'{hashlib.sha256(z.read_bytes()).hexdigest()}  {z.name}' for z in zips]
    (out / 'SHA256SUMS.txt').write_text('\n'.join(sums) + '\n', encoding='ascii')
    for f in sorted(out.iterdir()):
        print(f'{f.stat().st_size / 1048576:9.1f} MB  {f.name}')
    print(f'tag: {tag}')


if __name__ == '__main__':
    main()
