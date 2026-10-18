"""Validate an uploaded website release, then atomically switch its public pointer.

Run on the VPS after uploading objects and releases/<tag> to the website root.
No web service restart is needed. Existing release directories are immutable.
"""
import argparse
import json
import os
from pathlib import Path
import re

from prepare_website_release import sha256, SITE_ROOT, safe_path


def atomic_json(path, data):
    temporary = path.with_suffix('.pending')
    temporary.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    os.replace(temporary, path)


def activate(root, tag):
    if not re.fullmatch(r'v\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?', tag):
        raise ValueError('Invalid release tag')
    release = root / 'releases' / tag
    metadata = json.loads((release / 'release.json').read_text())
    manifest_path = release / 'manifest.json'
    if metadata['tag'] != tag or metadata['schema'] != 1 or metadata['platform'] != 'windows-x64':
        raise ValueError('Invalid release descriptor')
    if sha256(manifest_path) != metadata['manifest']['sha256']:
        raise ValueError('Manifest verification failed')
    manifest = json.loads(manifest_path.read_text())
    if manifest['tag'] != tag or manifest['schema'] != 1 or manifest['platform'] != 'windows-x64':
        raise ValueError('Invalid release inventory')
    for entry in manifest['files']:
        if not safe_path(entry['path']) or not re.fullmatch(r'[0-9a-f]{64}', entry['sha256']):
            raise ValueError('Unsafe release object')
        blob = root / 'objects' / entry['sha256']
        if blob.stat().st_size != entry['size'] or sha256(blob) != entry['sha256']:
            raise ValueError('Object verification failed: ' + entry['path'])
    archive = release / f'CammieEngine-{tag}-windows-x64.zip'
    if archive.stat().st_size != metadata['archive']['size'] or sha256(archive) != metadata['archive']['sha256']:
        raise ValueError('Archive verification failed')
    base = SITE_ROOT + 'releases/' + tag + '/'
    if (metadata['archive']['url'] != base + archive.name
            or metadata['manifest']['url'] != base + 'manifest.json'
            or metadata['checksumUrl'] != base + 'SHA256SUMS.txt'
            or metadata['changelogUrl'] != base + 'changelog.txt'):
        raise ValueError('Invalid release URLs')
    if (release / 'SHA256SUMS.txt').read_text().strip() != metadata['archive']['sha256'] + '  ' + archive.name:
        raise ValueError('Invalid release sidecar')
    (release / 'changelog.txt').read_text(encoding='utf-8')
    history = []
    for descriptor in root.glob('releases/*/release.json'):
        item = json.loads(descriptor.read_text())
        if item['tag'] != tag and not (descriptor.parent / 'PUBLISHED').is_file():
            continue
        history.append(item)
    history.sort(key=lambda item: tuple(int(n) for n in item['tag'][1:].split('-')[0].split('.')), reverse=True)
    (release / 'PUBLISHED').touch()
    atomic_json(root / 'history.json', {'schema': 1, 'releases': history})
    temporary = root / 'download.pending'
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(Path('releases') / tag / archive.name)
    os.replace(temporary, root / 'download.zip')
    atomic_json(root / 'latest.json', metadata)
    print('Published ' + tag + ' at ' + SITE_ROOT)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    activate(args.root, args.tag)
