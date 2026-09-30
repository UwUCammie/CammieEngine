#!/usr/bin/env python3
"""Backed-up, owner-scoped Psych gfVersion refresh from a private import.

Only the native chart's `gf` field can change. A missing field in the fresh
import removes a stale synthetic default so difficulty inheritance can work.
"""

from __future__ import annotations

import argparse
import copy
import fcntl
import json
import os
from pathlib import Path
import shutil
import time

from refresh_psych_song_titles import (LOCK, ROOT, TMP, atomic_write, chart,
                                       digest, owner_for, regular_child,
                                       selected_rows)


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
        path = Path(relative)
        if path.parts[:2] != ('assets', 'data') or path.suffix != '.json':
            raise ValueError(f'not a native chart path: {relative}')
        donor = regular_child(source, str(Path('data').joinpath(*path.parts[2:])))
        fresh_path = regular_child(preview, relative)
        live_path = regular_child(runtime, relative)
        if owner_for(fresh_path) != owner or owner_for(live_path) != owner:
            raise ValueError(f'selected owner mismatch: {relative}')
        authored = chart(donor)['song']
        fresh = chart(fresh_path)['song']
        installed = chart(live_path)['song']
        if any(authored.get(key) != candidate.get(key) for key in ('song', 'notes', 'events')
               for candidate in (fresh, installed)):
            raise ValueError(f'source title, notes or events differ: {relative}')
        if any(authored.get(key) != candidate.get(key)
               for key in ('player1', 'player2', 'stage', 'gfVersion')
               if key in authored for candidate in (fresh, installed)):
            raise ValueError(f'source actor or stage metadata differs: {relative}')
        source_gf = authored.get('gf') or authored.get('gfVersion')
        if source_gf is not None and fresh.get('gf') != source_gf:
            raise ValueError(f'private import lost explicit source girlfriend: {relative}')
        desired = copy.deepcopy(installed)
        if 'gf' in fresh:
            desired['gf'] = fresh['gf']
        else:
            desired.pop('gf', None)
        entries.append({'relative': relative,
                        'sourceSha256': digest(donor),
                        'previewSha256': digest(fresh_path),
                        'installedSha256': digest(live_path),
                        'sourceGf': source_gf,
                        'freshGfPresent': 'gf' in fresh,
                        'freshGf': fresh.get('gf'),
                        'changed': desired != installed})
    return {'version': 1, 'source': str(source.resolve()),
            'preview': str(preview.resolve()), 'runtime': str(runtime.resolve()),
            'owner': owner, 'matrix': str(matrix.resolve()), 'package': package,
            'charts': entries,
            'repoOptionsSha256': digest(ROOT / 'assets/data/options.json'),
            'runtimeOptionsSha256': digest(runtime / 'assets/data/options.json')}


def apply(saved: dict, receipt_path: Path) -> dict:
    current = plan(Path(saved['source']), Path(saved['preview']), Path(saved['runtime']),
                   saved['owner'], Path(saved['matrix']), saved['package'])
    if current != saved:
        raise ValueError('source, preview, installed charts, owner, or settings changed since planning')
    runtime = Path(saved['runtime'])
    backup = TMP / 'psych-gf-backups' / (str(int(time.time())) + '-' + str(os.getpid()))
    backup.mkdir(parents=True, exist_ok=False)
    replaced = []
    try:
        for entry in saved['charts']:
            if not entry['changed']:
                continue
            relative = entry['relative']
            target = regular_child(runtime, relative)
            saved_file = backup / relative
            saved_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved_file)
            if digest(saved_file) != entry['installedSha256']:
                raise ValueError(f'backup changed: {relative}')
            desired = chart(target)
            if entry['freshGfPresent']:
                desired['song']['gf'] = entry['freshGf']
            else:
                desired['song'].pop('gf', None)
            content = (json.dumps(desired, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
            atomic_write(target, content, backup / (relative + '.new'))
            replaced.append(relative)
            if chart(target) != desired or owner_for(target) != saved['owner']:
                raise ValueError(f'girlfriend-only replacement failed: {relative}')
        if (digest(ROOT / 'assets/data/options.json') != saved['repoOptionsSha256']
                or digest(runtime / 'assets/data/options.json') != saved['runtimeOptionsSha256']):
            raise ValueError('options changed during girlfriend refresh')
    except Exception:
        for relative in reversed(replaced):
            target = regular_child(runtime, relative)
            saved_file = backup / relative
            atomic_write(target, saved_file.read_bytes(), backup / (relative + '.restore'))
        raise
    receipt = {'version': 1, 'status': 'applied', 'owner': saved['owner'],
               'backup': str(backup), 'changed': len(replaced),
               'charts': saved['charts'], 'optionsUnchanged': True}
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
