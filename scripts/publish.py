#!/usr/bin/env python3
"""Create the GitHub and Gitee releases for an existing, pushed tag and upload dist/release/<tag>/*.

  python3 scripts/publish.py v0.5.0-beta.1 [--only github|gitee]

Release notes: docs/release-notes/<tag>.md (committed, shared by GitHub and Gitee).

Credentials (release machine only, never committed):
  GitHub: gh CLI logged in (`gh auth login`).
  Gitee:  environment variable GITEE_TOKEN (personal access token with "projects" scope).
Tags containing a hyphen (v0.5.0-beta.1) are published as pre-releases and never marked latest.
Safe to re-run: existing releases are reused and existing assets are skipped.
"""
import argparse
import json
import mimetypes
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GITHUB_REPO = 'BakaAkari/ATBridge'
GITEE_OWNER, GITEE_REPO = 'baka-akari', 'ATBridge'


def assets_for(tag):
    folder = ROOT / 'dist' / 'release' / tag
    files = sorted(p for p in folder.glob('*') if p.suffix in ('.zip', '.txt') and p.is_file())
    if not files:
        sys.exit(f'no packages in {folder}; run scripts/package.py first')
    return files


def check_tag(tag):
    for remote in ('origin', 'gitee'):
        out = subprocess.run(['git', 'ls-remote', '--tags', remote, tag], cwd=ROOT, capture_output=True, text=True).stdout
        if tag not in out:
            sys.exit(f'tag {tag} is not on {remote}; push it first')


def github(tag, title, notes, files, pre):
    view = subprocess.run(['gh', 'release', 'view', tag, '-R', GITHUB_REPO, '--json', 'assets'], capture_output=True, text=True)
    if view.returncode != 0:
        cmd = ['gh', 'release', 'create', tag, '-R', GITHUB_REPO, '--title', title, '--notes-file', str(notes), '--verify-tag']
        cmd += ['--prerelease', '--latest=false'] if pre else ['--latest']
        subprocess.run(cmd, check=True)
        existing = set()
    else:
        existing = {a['name'] for a in json.loads(view.stdout)['assets']}
    todo = [str(f) for f in files if f.name not in existing]
    if todo:
        subprocess.run(['gh', 'release', 'upload', tag, '-R', GITHUB_REPO, *todo], check=True)
    print(f'GitHub: https://github.com/{GITHUB_REPO}/releases/tag/{tag}')


def gitee_request(method, path, token, data=None, files=None):
    url = f'https://gitee.com/api/v5/repos/{GITEE_OWNER}/{GITEE_REPO}{path}'
    headers = {}
    if files:
        boundary = uuid.uuid4().hex
        body = b''
        for k, v in {'access_token': token}.items():
            body += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        for f in files:
            ctype = mimetypes.guess_type(f.name)[0] or 'application/octet-stream'
            body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{f.name}"\r\n'
                     f'Content-Type: {ctype}\r\n\r\n').encode() + f.read_bytes() + b'\r\n'
        body += f'--{boundary}--\r\n'.encode()
        headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'
    elif data is not None:
        body = json.dumps({**data, 'access_token': token}).encode()
        headers['Content-Type'] = 'application/json'
    else:
        url += ('&' if '?' in url else '?') + urllib.parse.urlencode({'access_token': token})
        body = None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.loads(r.read() or b'null')
    except urllib.error.HTTPError as e:
        if e.code == 404 and method == 'GET':
            return None
        sys.exit(f'Gitee {method} {path} failed: HTTP {e.code} {e.read().decode("utf-8", "replace")[:300]}')


def gitee(tag, title, notes, files, pre):
    token = os.environ.get('GITEE_TOKEN')
    if not token:
        sys.exit('GITEE_TOKEN is not set (set it on the release machine only)')
    rel = gitee_request('GET', f'/releases/tags/{urllib.parse.quote(tag)}', token)
    if not rel:
        rel = gitee_request('POST', '/releases', token, {
            'tag_name': tag, 'name': title, 'body': notes.read_text(encoding='utf-8'),
            'prerelease': pre, 'target_commitish': tag})
    existing = {a.get('name') for a in gitee_request('GET', f'/releases/{rel["id"]}/attach_files', token) or []}
    for f in files:
        if f.name in existing:
            continue
        gitee_request('POST', f'/releases/{rel["id"]}/attach_files', token, files=[f])
        print(f'  uploaded {f.name}')
    print(f'Gitee: https://gitee.com/{GITEE_OWNER}/{GITEE_REPO}/releases/tag/{tag}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('tag')
    ap.add_argument('--notes', help='release notes markdown (default docs/release-notes/<tag>.md)')
    ap.add_argument('--only', choices=['github', 'gitee'])
    a = ap.parse_args()
    notes = Path(a.notes) if a.notes else ROOT / 'docs' / 'release-notes' / f'{a.tag}.md'
    if not notes.is_file():
        sys.exit(f'release notes not found: {notes}')
    files = [f for f in assets_for(a.tag)]
    pre = '-' in a.tag
    title = f'ATBridge {a.tag}'
    check_tag(a.tag)
    if a.only in (None, 'github'):
        github(a.tag, title, notes, files, pre)
    if a.only in (None, 'gitee'):
        gitee(a.tag, title, notes, files, pre)


if __name__ == '__main__':
    main()
