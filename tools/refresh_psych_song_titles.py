#!/usr/bin/env python3
"""Plan or apply an owner-scoped Psych chart title refresh from a private import.

Only the chart's song title and compatPreserveSongTitle flag change. Notes,
events, every other chart field, donor files, owner manifests, and options are
checked before and after. Applied charts are backed up under repository tmp.
"""

from __future__ import annotations

import argparse
import copy
try:
    from tools import file_lock as fcntl
except ModuleNotFoundError:
    import file_lock as fcntl  # Direct python tools/<script>.py invocation.
import hashlib
import json
import os
from pathlib import Path
import shutil
import time


ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / 'tmp'
LOCK = ROOT / '.tools/runtime-0.lock'


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def regular_child(root: Path, relative: str) -> Path:
    part = Path(relative)
    if part.is_absolute() or '..' in part.parts or not part.parts:
        raise ValueError(f'unsafe path: {relative}')
    candidate = root / part
    if candidate.is_symlink() or root.resolve() not in candidate.resolve().parents:
        raise ValueError(f'path leaves the selected root: {relative}')
    if not candidate.is_file():
        raise ValueError(f'missing regular file: {candidate}')
    return candidate


def chart(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8'))
    song = value.get('song')
    if not isinstance(song, dict) or not isinstance(song.get('song'), str):
        raise ValueError(f'invalid chart title: {path}')
    if not isinstance(song.get('notes'), list):
        raise ValueError(f'invalid chart notes: {path}')
    return value


def owner_for(path: Path) -> str:
    manifest = path.parent / 'compatScripts.json'
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError(f'missing regular owner manifest: {manifest}')
    owner = json.loads(manifest.read_text(encoding='utf-8')).get('selectedRoot')
    if not isinstance(owner, str):
        raise ValueError(f'invalid selected owner: {manifest}')
    return owner


def safe_title(value: str) -> bool:
    return bool(value.strip()) and value.strip() not in ('.', '..') and all(
        token not in value for token in ('/', '\\', ':', '\x00'))


def selected_rows(matrix: Path, package: str) -> list[dict]:
    rows = json.loads(matrix.read_text(encoding='utf-8'))['rows']
    selected = [row for row in rows if row.get('package', '').casefold() == package.casefold()]
    if not selected or len({row.get('runtimeChart') for row in selected}) != len(selected):
        raise ValueError('no unique chart rows selected')
    return selected


def plan(source: Path, preview: Path, runtime: Path, owner: str,
         matrix: Path, package: str) -> dict:
    if not source.is_dir() or not preview.is_dir() or not runtime.is_dir():
        raise ValueError('source, preview, and runtime roots must exist')
    if not preview.resolve().is_relative_to(TMP.resolve()):
        raise ValueError('preview must be a private repository tmp tree')
    if not owner.startswith('assets/imported_mods/') or '..' in Path(owner).parts:
        raise ValueError('expected owner must be an imported namespace')
    entries = []
    for row in selected_rows(matrix, package):
        relative = row['runtimeChart']
        chart_path = Path(relative)
        if chart_path.parts[:2] != ('assets', 'data') or chart_path.suffix != '.json':
            raise ValueError(f'not a native chart path: {relative}')
        source_relative = Path('data').joinpath(*chart_path.parts[2:]).as_posix()
        donor_chart = regular_child(source, source_relative)
        preview_chart = regular_child(preview, relative)
        live_chart = regular_child(runtime, relative)
        if owner_for(preview_chart) != owner or owner_for(live_chart) != owner:
            raise ValueError(f'selected owner mismatch: {relative}')
        authored = chart(donor_chart)['song']
        fresh = chart(preview_chart)['song']
        installed = chart(live_chart)['song']
        title = authored['song']
        if not safe_title(title) or fresh['song'] != title or fresh.get('compatPreserveSongTitle') is not True:
            raise ValueError(f'private import did not retain source title: {relative}')
        if any(authored.get(key) != candidate.get(key) for key in ('notes', 'events')
               for candidate in (fresh, installed)):
            raise ValueError(f'source notes or events differ: {relative}')
        desired = copy.deepcopy(installed)
        desired['song'] = title
        desired['compatPreserveSongTitle'] = True
        entries.append({'relative': relative, 'title': title,
                        'sourceSha256': digest(donor_chart),
                        'previewSha256': digest(preview_chart),
                        'installedSha256': digest(live_chart),
                        'changed': desired != installed})
    return {'version': 1, 'source': source.resolve().as_posix(),
            'preview': preview.resolve().as_posix(), 'runtime': runtime.resolve().as_posix(),
            'owner': owner, 'matrix': matrix.resolve().as_posix(), 'package': package,
            'charts': entries,
            'repoOptionsSha256': digest(ROOT / 'assets/data/options.json'),
            'runtimeOptionsSha256': digest(runtime / 'assets/data/options.json')}


def atomic_write(path: Path, content: bytes, scratch: Path) -> None:
    scratch.parent.mkdir(parents=True, exist_ok=True)
    scratch.write_bytes(content)
    os.replace(scratch, path)


def apply(saved_plan: dict, receipt_path: Path) -> dict:
    current = plan(Path(saved_plan['source']), Path(saved_plan['preview']),
                   Path(saved_plan['runtime']), saved_plan['owner'],
                   Path(saved_plan['matrix']), saved_plan['package'])
    if current != saved_plan:
        raise ValueError('source, preview, installed charts, owner, or settings changed since planning')
    runtime = Path(saved_plan['runtime'])
    backup = TMP / 'psych-title-backups' / (str(int(time.time())) + '-' + str(os.getpid()))
    backup.mkdir(parents=True, exist_ok=False)
    replacements = []
    try:
        for entry in saved_plan['charts']:
            if not entry['changed']:
                continue
            relative = entry['relative']
            target = regular_child(runtime, relative)
            saved = backup / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
            if digest(saved) != entry['installedSha256']:
                raise ValueError(f'backup changed: {relative}')
            before = chart(target)
            desired = copy.deepcopy(before)
            desired['song']['song'] = entry['title']
            desired['song']['compatPreserveSongTitle'] = True
            new_content = (json.dumps(desired, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
            atomic_write(target, new_content, backup / (relative + '.new'))
            replacements.append(relative)
            after = chart(target)
            if after != desired or owner_for(target) != saved_plan['owner']:
                raise ValueError(f'title-only replacement failed: {relative}')
        if (digest(ROOT / 'assets/data/options.json') != saved_plan['repoOptionsSha256']
                or digest(runtime / 'assets/data/options.json') != saved_plan['runtimeOptionsSha256']):
            raise ValueError('options changed during title refresh')
    except Exception:
        for relative in reversed(replacements):
            target = regular_child(runtime, relative)
            saved = backup / relative
            atomic_write(target, saved.read_bytes(), backup / (relative + '.restore'))
        raise
    receipt = {'version': 1, 'status': 'applied', 'owner': saved_plan['owner'],
               'backup': backup.as_posix(), 'changed': len(replacements),
               'charts': saved_plan['charts'], 'optionsUnchanged': True}
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--preview', type=Path)
    parser.add_argument('--runtime', type=Path, default=ROOT / 'export/release/linux/bin')
    parser.add_argument('--owner')
    parser.add_argument('--matrix', type=Path, default=TMP / 'example_mods_chart_matrix.json')
    parser.add_argument('--package')
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    with LOCK.open('a+') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        if args.apply:
            saved = json.loads(args.plan.read_text(encoding='utf-8'))
            result = apply(saved, args.receipt or args.plan.with_suffix('.receipt.json'))
            print(json.dumps({'status': result['status'], 'changed': result['changed'],
                              'backup': result['backup']}))
        else:
            if args.source is None or args.preview is None or args.owner is None or args.package is None:
                parser.error('--source, --preview, --owner and --package are required for planning')
            saved = plan(args.source, args.preview, args.runtime, args.owner,
                         args.matrix, args.package)
            args.plan.parent.mkdir(parents=True, exist_ok=True)
            args.plan.write_text(json.dumps(saved, indent=2) + '\n', encoding='utf-8')
            print(json.dumps({'status': 'planned', 'charts': len(saved['charts']),
                              'changed': sum(row['changed'] for row in saved['charts'])}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
