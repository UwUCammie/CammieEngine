"""Turn a tested release ZIP into immutable website files, without scanning assets."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SITE_ROOT = 'https://uwucammie.com/cammie-engine/'
PAYLOAD = 'CammieEngine-windows-x64/'
TAG = re.compile(r'v\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?\Z')


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def safe_path(name):
    return bool(name) and '\\' not in name and all(
        part not in ('', '.', '..') and not part.endswith(('.', ' '))
        and not re.search(r'[<>:"|?*\x00-\x1f\x7f]', part)
        and not re.match(r'^(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\.|$)', part, re.I)
        for part in name.split('/'))


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n', encoding='utf-8')


def prepare(archive, output, tag, changelog):
    if not TAG.fullmatch(tag) or archive.name != f'CammieEngine-{tag}-windows-x64.zip':
        raise ValueError('Archive name must match a semantic release tag')
    release = output / 'releases' / tag
    if release.exists():
        raise ValueError('Release staging directory already exists; use a new empty output')
    release.mkdir(parents=True)
    objects = output / 'objects'
    objects.mkdir(exist_ok=True)
    files, seen, dirs = [], set(), set()
    with zipfile.ZipFile(archive) as package:
        for entry in package.infolist():
            if entry.is_dir():
                continue
            if not entry.filename.startswith(PAYLOAD):
                raise ValueError('Unexpected release archive root')
            relative = entry.filename[len(PAYLOAD):]
            key = relative.lower()
            if not safe_path(relative) or key == 'release_files.json' or key in seen or key in dirs:
                raise ValueError('Unsafe or duplicate release file: ' + relative)
            parents = ['/'.join(key.split('/')[:i]) for i in range(1, len(key.split('/')))]
            if any(parent in seen for parent in parents):
                raise ValueError('Release file/directory collision')
            dirs.update(parents)
            seen.add(key)
            if entry.file_size > 2147483647:
                raise ValueError('Release file exceeds supported size')
            digest = hashlib.sha256()
            with tempfile.NamedTemporaryFile(dir=objects, delete=False) as target:
                temporary = Path(target.name)
                with package.open(entry) as source:
                    for block in iter(lambda: source.read(1024 * 1024), b''):
                        digest.update(block)
                        target.write(block)
            hashed = digest.hexdigest()
            blob = objects / hashed
            if blob.exists():
                if sha256(blob) != hashed:
                    raise ValueError('Corrupt existing content object')
                temporary.unlink()
            else:
                temporary.replace(blob)
            files.append({'path': relative, 'sha256': hashed, 'size': entry.file_size})
        for required in ('Funkin.exe', 'lime.ndll', 'CammieUpdateHelper.exe', 'RELEASE_TAG', 'BUNDLED_ASSETS.json'):
            if required.lower() not in seen:
                raise ValueError('Missing required release file: ' + required)
        if package.read(PAYLOAD + 'RELEASE_TAG').decode().strip() != tag:
            raise ValueError('Packaged release tag mismatch')
    manifest = release / 'manifest.json'
    write_json(manifest, {'schema': 1, 'tag': tag, 'platform': 'windows-x64', 'files': files})
    full = release / archive.name
    try:
        os.link(archive, full)
    except OSError:
        shutil.copyfile(archive, full)
    checksum = sha256(archive)
    (release / 'SHA256SUMS.txt').write_text(f'{checksum}  {archive.name}\n', encoding='ascii')
    (release / 'changelog.txt').write_text(changelog, encoding='utf-8')
    url = SITE_ROOT + 'releases/' + tag + '/'
    metadata = {'schema': 1, 'tag': tag, 'platform': 'windows-x64', 'prerelease': True,
                'archive': {'name': archive.name, 'url': url + archive.name,
                            'sha256': checksum, 'size': archive.stat().st_size},
                'manifest': {'url': url + 'manifest.json', 'sha256': sha256(manifest)},
                'checksumUrl': url + 'SHA256SUMS.txt', 'changelogUrl': url + 'changelog.txt'}
    write_json(release / 'release.json', metadata)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--changelog', type=Path, default=ROOT / 'updateLog.txt')
    args = parser.parse_args()
    result = prepare(args.archive, args.output, args.tag, args.changelog.read_text(encoding='utf-8'))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
