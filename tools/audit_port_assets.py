#!/usr/bin/env python3
"""Audit recoverable port omissions and registered/static asset dependencies.

Static references can be optional or belong to inactive script branches; these
are reported separately, never silently replaced with unrelated assets.
"""
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import re
import shutil
from repair_imported_assets import missing_assets

ROOT = Path(__file__).resolve().parents[1]


def read_registry(path):
    text = re.sub(r'/\*.*?\*/', '', path.read_text(), flags=re.S)
    text = re.sub(r'//[^\n]*', '', text)
    return json.loads(re.sub(r',\s*([}\]])', r'\1', text))


def audit(root, donor, repair_case=False):
    index = defaultdict(list)
    for base in (root, donor):
        for path in (base / 'assets').rglob('*'):
            if path.is_file():
                index[str(path.relative_to(base)).lower()].append(path)
    repaired = []
    chart_uses = defaultdict(set)
    for chart in (root / 'assets/data').glob('*/*.json'):
        try:
            song = json.JSONDecoder().raw_decode(chart.read_text().lstrip())[0].get('song')
            if not isinstance(song, dict) or 'notes' not in song:
                continue
            for field in ('player1', 'player2', 'gf', 'stage', 'cutsceneType', 'forceLayout'):
                if isinstance(song.get(field), str):
                    chart_uses[(field, song[field])].add(str(chart.relative_to(root)))
        except (ValueError, AttributeError):
            pass
    missing = defaultdict(set)

    def check(relative, origin):
        relative = os.path.normpath(relative.replace('\\', '/'))
        if not relative.startswith('assets/'):
            return
        dest = root / relative
        if dest.is_file():
            return
        candidates = index[relative.lower()]
        # Prefer this port's edited version. Ambiguous case collisions need review.
        local = [p for p in candidates if p.is_relative_to(root)]
        choices = local or candidates
        if len(choices) == 1 and repair_case:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(choices[0], dest)
            repaired.append(relative)
        else:
            missing[relative].add(origin)

    images = root / 'assets/images'
    contexts = defaultdict(set)
    for registry in ('custom_chars/custom_chars.jsonc', 'custom_stages/custom_stages.json',
                     'custom_cutscenes/cutscenes.json'):
        path = images / registry
        for name, value in read_registry(path).items():
            impl = value.get('like', name) if isinstance(value, dict) else value
            if not isinstance(impl, str):
                continue
            extensions = ('.hscript', '.hxs', '.json', '.jsonc') if registry.startswith('custom_chars') else ('.hscript', '.hxs')
            candidate = next((path.parent / (impl + ext) for ext in extensions
                              if (path.parent / (impl + ext)).is_file()), None)
            if candidate is None:
                candidate = next((path.parent / (impl + ext) for ext in extensions
                                  if index[str((path.parent / (impl + ext)).relative_to(root)).lower()]), path.parent / (impl + '.hscript'))
                check(str(candidate.relative_to(root)), 'registry: ' + registry + ': ' + name)
            if candidate.is_file() and candidate.suffix in ('.hscript', '.hxs'):
                contexts[candidate].add(path.parent / name)
    scripts = list((root / 'assets/images').rglob('*.hscript')) + list((root / 'assets/data').rglob('*.hscript'))
    literal = re.compile(r'''["'](assets/[^"'\n]+\.(?:png|xml|ogg|mp3|wav|mp4|webm|ttf|otf|json|jsonc|hscript|txt))["']''')
    relative = re.compile(r'''hscriptPath\s*\+\s*["']([^"'\n]+\.(?:png|xml|ogg|mp3|wav|json|jsonc|txt))["']''')
    for script in scripts:
        text = re.sub(r'/\*.*?\*/', '', script.read_text(errors='replace'), flags=re.S)
        text = re.sub(r'//[^\n]*', '', text)
        origin = str(script.relative_to(root))
        for asset in literal.findall(text):
            check(asset, origin)
        folders = contexts.get(script, {script.parent if script.is_relative_to(root / 'assets/data') else script.with_suffix('')})
        for folder in folders:
            for asset in relative.findall(text):
                check(str((folder / asset.lstrip("/")).relative_to(root)), origin)
    active_missing = []
    for path, origins in sorted(missing.items()):
        charts = set()
        for origin in origins:
            if origin.startswith('registry: '):
                _, registry, name = origin.split(': ', 2)
                fields = ('player1', 'player2', 'gf') if registry.startswith('custom_chars') else ('stage',) if registry.startswith('custom_stages') else ('cutsceneType',)
                for field in fields:
                    charts.update(chart_uses[(field, name)])
        if charts:
            active_missing.append({'path': path, 'charts': sorted(charts)})
    for (field, name), charts in chart_uses.items():
        if field == 'forceLayout' and name != 'none':
            path = 'assets/images/custom_ui/ui_layouts/' + name + '.hscript'
            if not (root / path).is_file():
                active_missing.append({'path': path, 'charts': sorted(charts)})
    return {
        'active_chart_missing_implementations': active_missing,
        'recoverable_port_omissions': [str(d.relative_to(root)) for _, d in missing_assets(donor / 'assets', root / 'assets')],
        'case_paths_repaired': sorted(set(repaired)),
        'unresolved_references': [{'path': p, 'referenced_by': sorted(origins)} for p, origins in sorted(missing.items())],
        'scope': 'Registered character/stage/cutscene implementations and literal references in image/song scripts. Literal references may be optional; computed paths require gameplay verification.'
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('donor', type=Path)
    parser.add_argument('--repair-case', action='store_true')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = audit(ROOT, args.donor.resolve(), args.repair_case)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    for key in ('recoverable_port_omissions', 'case_paths_repaired', 'unresolved_references'):
        print(f'{key}: {len(result[key])}')


if __name__ == '__main__':
    main()
