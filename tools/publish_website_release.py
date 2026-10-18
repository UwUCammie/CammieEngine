"""Upload a prepared release over SSH, verify it on the VPS and activate it.

Only absent content objects are transferred. Versioned public release files
are never overwritten. Authentication uses the existing OpenSSH configuration.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess
import tarfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
REMOTE_ROOT = '/srv/uwucammie/cammie-engine'


def public_permissions(entry):
    # Windows reports synthetic writable modes. Do not transfer those modes
    # to the VPS, where the account service runs as a different Unix user.
    entry.mode = 0o755 if entry.isdir() else 0o644
    return entry


def remote(host, code, *args):
    command = 'python3 -c ' + shlex.quote(code)
    if args:
        command += ' ' + ' '.join(shlex.quote(str(value)) for value in args)
    return subprocess.run(['ssh', '-o', 'BatchMode=yes', host, command],
                          check=True, capture_output=True, text=True).stdout


def publish(prepared, tag, host):
    if not re.fullmatch(r'v\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?', tag):
        raise ValueError('Invalid release tag')
    if not re.fullmatch(r'[A-Za-z0-9_.@-]+', host) or host.startswith('-'):
        raise ValueError('Invalid SSH host')
    descriptor = prepared / 'releases' / tag / 'release.json'
    if json.loads(descriptor.read_text())['tag'] != tag:
        raise ValueError('Prepared release does not match tag')
    present = set(json.loads(remote(host, """
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
if (root / 'releases' / sys.argv[2]).exists():
    raise SystemExit('Public release already exists; immutable releases cannot be replaced')
print(json.dumps([item.name for item in (root / 'objects').glob('*') if item.is_file()]))
""", REMOTE_ROOT, tag)))
    incoming = '/srv/uwucammie/.cammie-upload-' + uuid.uuid4().hex
    command = 'mkdir ' + shlex.quote(incoming) + ' && tar -xf - -C ' + shlex.quote(incoming)
    missing = [item for item in (prepared / 'objects').iterdir() if item.name not in present]
    print(f'Uploading {len(missing)} new content objects ({sum(item.stat().st_size for item in missing)} bytes) and the full ZIP', flush=True)
    with subprocess.Popen(['ssh', '-o', 'BatchMode=yes', host, command], stdin=subprocess.PIPE) as process:
        assert process.stdin is not None
        with tarfile.open(fileobj=process.stdin, mode='w|') as archive:
            for item in missing:
                archive.add(item, arcname='objects/' + item.name, recursive=False, filter=public_permissions)
            archive.add(descriptor.parent, arcname='releases/' + tag, filter=public_permissions)
            for name in ('prepare_website_release.py', 'activate_website_release.py'):
                archive.add(ROOT / 'tools' / name, arcname='maintenance/' + name, filter=public_permissions)
            for name in ('index.html', 'engine.css', 'engine.js'):
                archive.add(ROOT / 'tools/website' / name, arcname='static/' + name, filter=public_permissions)
        process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError('Upload failed; the current release is unchanged. Staging: ' + incoming)
    print(remote(host, """
import os, pathlib, shutil, subprocess, sys
incoming, root = map(pathlib.Path, sys.argv[1:3])
tag = sys.argv[3]
maintenance = root.parent / 'cammie-engine-maintenance'
maintenance.mkdir(exist_ok=True)
(root / 'objects').mkdir(parents=True, exist_ok=True)
(root / 'releases').mkdir(exist_ok=True)
for item in (incoming / 'objects').glob('*'):
    destination = root / 'objects' / item.name
    if not destination.exists():
        os.replace(item, destination)
for item in (incoming / 'maintenance').iterdir():
    shutil.copyfile(item, maintenance / item.name)
destination = root / 'releases' / tag
if destination.exists():
    raise SystemExit('Release appeared during upload; refusing to overwrite it')
os.rename(incoming / 'releases' / tag, destination)
subprocess.run(['python3', str(maintenance / 'activate_website_release.py'), '--root', str(root), '--tag', tag], check=True)
for item in (incoming / 'static').iterdir():
    os.replace(item, root / item.name)
# Only the exact UUID staging directory created for this upload is removed.
if incoming.parent != root.parent or not incoming.name.startswith('.cammie-upload-'):
    raise SystemExit('Unexpected staging path')
shutil.rmtree(incoming)
""", incoming, REMOTE_ROOT, tag), end='')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--ssh-host', default='uwucammie-vps')
    args = parser.parse_args()
    publish(args.prepared, args.tag, args.ssh_host)
