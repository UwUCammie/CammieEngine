#!/usr/bin/env python3
"""Restore missing media, scripts and supporting definitions from modding-plus-fnf without overwriting
ported charts, scripts, registries, or existing assets. Dry-run unless --apply.
"""
import argparse
from collections import Counter
from pathlib import Path
import shutil
import re
import json
try:
    from character_dependencies import audit_characters
except ModuleNotFoundError:
    from tools.character_dependencies import audit_characters


def missing_assets(source, target):
    media = {'.png', '.xml', '.ogg', '.wav', '.mp3', '.mp4', '.webm', '.ttf',
             '.otf', '.jpg', '.jpeg', '.gif', '.frag', '.vert', '.fon',
             '.hscript', '.hxs', '.hx', '.json', '.jsonc', '.txt', '.offset'}
    for path in sorted(source.rglob('*')):
        is_note_info = path.name.lower() == 'noteinfo.json'
        if not path.is_file() or (path.suffix.lower() not in media and not is_note_info):
            continue
        relative = path.relative_to(source)
        if relative.parts[0] not in {'images', 'music', 'sounds', 'fonts',
                                    'shaders', 'videos', 'data', 'scripts'}:
            continue
        # Backup scripts and old engine-wide configuration are not runtime dependencies.
        if any(' - Copy' in part or part.lower() == 'backup' for part in relative.parts):
            continue
        if relative.parts[0] == 'data' and len(relative.parts) <= 2:
            continue
        if relative.parts[0] == 'data' and len(relative.parts) > 2:
            # Chart folders were normalized for Linux by the port. Only restore
            # supporting media for songs already imported into this project.
            relative = Path('data', relative.parts[1].lower(), *relative.parts[2:])
            if not (target / 'data' / relative.parts[1]).is_dir():
                continue
        if relative.parts[0] == 'data' and path.suffix.lower() in {'.json', '.jsonc'} and not is_note_info:
            # Existing charts were deliberately converted; restore their dependencies,
            # not extra unconverted charts/difficulties from the donor installation.
            content = path.read_text(errors='replace')
            if re.search(r'"song"\s*:\s*\{', content) and re.search(r'"notes"\s*:', content):
                continue
        if is_note_info:
            relative = relative.with_name('noteInfo.json')
        destination = target / relative
        if not destination.exists():
            if destination.is_symlink():
                raise ValueError(f'Broken destination symlink: {destination}')
            yield path, destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Original game directory')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--character-report', type=Path, help='Write missing character dependencies and donor availability as JSON')
    args = parser.parse_args()
    source = args.source.resolve() / 'assets'
    target = Path(__file__).resolve().parents[1] / 'assets'
    if not source.is_dir() or source == target:
        parser.error('source must be another game directory containing assets/')
    pending = list(missing_assets(source, target))
    print(f'{len(pending)} missing asset files ({sum(p.stat().st_size for p, _ in pending):,} bytes)')
    print(dict(Counter(str(d.relative_to(target).parts[0]) for _, d in pending)))
    if args.apply:
        for original, destination in pending:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, destination)
        print('Restored missing assets; existing files preserved.')
    # Zero copy candidates does not mean the imported library is playable.
    # Never invent assets or rewrite charts for characters absent in the donor.
    problems = audit_characters(target, source)
    for problem in problems:
        origin = 'also incomplete in donor' if problem['donor_problems'] else 'available in donor; check registry/assets'
        print(f"Missing character {problem['character']!r}: {', '.join(problem['problems'])}; {origin}")
    if args.character_report:
        args.character_report.parent.mkdir(parents=True, exist_ok=True)
        args.character_report.write_text(json.dumps(problems, indent=2) + '\n')
    if problems:
        print(f'{len(problems)} unresolved character dependencies; import is incomplete.')
        raise SystemExit(1)


if __name__ == '__main__':
    main()
