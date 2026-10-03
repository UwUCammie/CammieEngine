#!/usr/bin/env python3
"""Upgrade old actor and source-line sidecars from an isolated import preview.

Only additive metadata changes are allowed; every pre-existing value must agree
with the preview. Charts, scripts, registries, settings and donors are untouched.
Generate the preview with the current engine in an isolated offscreen runtime.
"""
import argparse
import base64
from datetime import datetime, timezone
try:
    from tools import file_lock as fcntl
except ModuleNotFoundError:
    import file_lock as fcntl  # Direct python tools/<script>.py invocation.
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import refresh_codename_events as shared

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / 'tmp'
LOCK_ROOT = ROOT / '.tools'
CAMERA = '__cammie_compat_camera.json'
ADDITIONS = {'nativeCharacters', 'nativeStage', 'stagePlacement'}
LINE_ADDITIONS = {'keyCount', 'strumLinePos', 'strumPos', 'strumScale', 'strumSpacing'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_text(), object_pairs_hook=unique_pairs)


def fingerprint():
    names = ('tools/refresh_codename_actor_metadata.py', 'tools/refresh_codename_events.py',
             'tools/CodenameActorMetadataValidate.hx', 'source/CodenameScriptPlan.hx',
             'source/CodenameStagePlacement.hx', 'source/CodenameScriptDiscovery.hx',
             'source/CodenameImporter.hx', 'source/ModuleFunctions.hx')
    return {name: digest((ROOT / name).read_bytes()) for name in names}


def additive_upgrade(old, fresh):
    """Preserve existing values; refuse edits rather than normalize them away."""
    if old.get('version') != 1 or fresh.get('version') != 1 or old.get('song') != fresh.get('song'):
        raise ValueError('sidecar identity mismatch')
    if set(old) != {'version', 'song', 'difficulties'} or set(fresh) != set(old):
        raise ValueError('unrecognized top-level metadata')
    if set(old['difficulties']) != set(fresh['difficulties']):
        raise ValueError('authored difficulties changed')
    result = json.loads(json.dumps(old))
    for diff, current in old['difficulties'].items():
        generated = fresh['difficulties'][diff]
        for key, value in current.items():
            if key == 'lines':
                result['difficulties'][diff]['lines'] = additive_lines(value, generated.get(key), diff)
                continue
            # Older placement records lack only the newly added order list.
            expected = generated.get(key)
            if key == 'stagePlacement' and isinstance(value, dict) and isinstance(expected, dict):
                expected = dict(expected)
                if 'order' not in value or value['order'] is None:
                    expected.pop('order', None)
                    value = {k: v for k, v in value.items() if k != 'order'}
            if value is None and key in ADDITIONS:
                continue
            if key not in generated or shared.canonical(value) != shared.canonical(expected):
                raise ValueError('edited or changed metadata: ' + diff + '.' + key)
        # Plans are reviewed and applied in separate Python processes. Set
        # iteration order changes with the hash seed and would change the
        # serialized after-image even when every input file stayed identical.
        for key in sorted(ADDITIONS):
            if generated.get(key) is None:
                raise ValueError('preview lacks current actor metadata: ' + diff + '.' + key)
            result['difficulties'][diff][key] = generated[key]
    return result


def additive_lines(current, generated, diff):
    """Add importer-owned visual fields without replacing any authored line value."""
    if not isinstance(current, list) or not isinstance(generated, list) or len(current) != len(generated):
        raise ValueError('edited or changed metadata: ' + diff + '.lines')
    upgraded = json.loads(json.dumps(current))
    for index, (old_line, fresh_line) in enumerate(zip(current, generated)):
        path = f'{diff}.lines[{index}]'
        if old_line is None and fresh_line is None:
            continue
        if not isinstance(old_line, dict) or not isinstance(fresh_line, dict):
            raise ValueError('edited or changed metadata: ' + path)
        if set(fresh_line) - set(old_line) - LINE_ADDITIONS:
            raise ValueError('unexpected new metadata: ' + path)
        for key, value in old_line.items():
            if key not in fresh_line or shared.canonical(value) != shared.canonical(fresh_line[key]):
                raise ValueError('edited or changed metadata: ' + path + '.' + key)
        for key in sorted(LINE_ADDITIONS):
            if key in fresh_line:
                upgraded[index][key] = fresh_line[key]
    return upgraded


def additive_line_upgrade(old, fresh, allow_new_difficulties=False):
    """Refresh only source-line geometry; leave actor/stage metadata byte values intact."""
    if old.get('version') != 1 or fresh.get('version') != 1 or old.get('song') != fresh.get('song'):
        raise ValueError('sidecar identity mismatch')
    if (set(old) != {'version', 'song', 'difficulties'} or set(fresh) != set(old)
            or (not set(old['difficulties']) <= set(fresh['difficulties']))
            or (not allow_new_difficulties and set(old['difficulties']) != set(fresh['difficulties']))):
        raise ValueError('authored difficulties changed')
    result = json.loads(json.dumps(old))
    for diff, current in old['difficulties'].items():
        generated = fresh['difficulties'][diff]
        if not isinstance(current, dict) or not isinstance(generated, dict):
            raise ValueError('invalid difficulty metadata: ' + diff)
        result['difficulties'][diff]['lines'] = additive_lines(
            current.get('lines'), generated.get('lines'), diff)
    for diff in sorted(set(fresh['difficulties']) - set(old['difficulties'])):
        result['difficulties'][diff] = fresh['difficulties'][diff]
    return result


def matching_new_difficulty_charts(runtime, preview, folder, difficulties):
    """Only append source metadata where the installed native chart is identical."""
    hashes = {}
    for diff in sorted(difficulties):
        stem = folder.name if diff == 'normal' else folder.name + '-' + diff
        for base in (runtime, preview):
            chart = base / 'assets/data' / folder.name / (stem + '.json')
            if not chart.is_file() or not shared.within(chart, base):
                raise ValueError('missing native chart for new difficulty: ' + diff)
            hashes[chart.as_posix()] = digest(chart.read_bytes())
        old = read(runtime / 'assets/data' / folder.name / (stem + '.json'))
        fresh = read(preview / 'assets/data' / folder.name / (stem + '.json'))
        if shared.canonical(old) != shared.canonical(fresh):
            raise ValueError('changed native chart for new difficulty: ' + diff)
    return hashes


def owned_source_plan(runtime, owner, folder):
    """Find the source-song sidecar, including owner-qualified destinations."""
    source_name = folder.name
    provenance = folder / 'importProvenance.json'
    if provenance.is_file():
        if not shared.within(provenance, runtime):
            raise ValueError('unsafe source provenance')
        data = read(provenance)
        if (data.get('version') != 1 or data.get('sourceEngine') != 'Codename Engine'
                or data.get('sourceOwner') != owner
                or data.get('destinationFolder') != folder.name
                or not shared.safe_segment(data.get('sourceFolder', ''))):
            raise ValueError('changed source provenance')
        source_name = data['sourceFolder']
    elif not shared.safe_segment(source_name):
        raise ValueError('unsafe source song')
    plan = runtime / owner / 'songs' / source_name / '__cammie_compat_scripts.json'
    if not plan.is_file() or not shared.within(plan, runtime):
        raise ValueError('missing owned source song plan')
    data = read(plan)
    if data.get('version') != 1 or data.get('song') != source_name:
        raise ValueError('changed owned source song plan')
    return source_name, plan, provenance if provenance.is_file() else None


def validate(paths):
    if not paths:
        return
    TMP.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='actor-schema-', dir=TMP) as work:
        request = Path(work) / 'paths.json'
        request.write_text(json.dumps([str(p) for p in paths]))
        run = subprocess.run([(ROOT / '.tools/haxe/haxe').as_posix(), '-cp', (ROOT / 'source').as_posix(),
                              '-cp', (ROOT / 'tools').as_posix(), '--run', 'CodenameActorMetadataValidate', request.as_posix()],
                             cwd=ROOT, env={**os.environ, 'TMPDIR': work},
                             text=True, capture_output=True, timeout=60)
        if run.returncode:
            raise ValueError('actor schema rejected input: ' + run.stderr.strip())


def implementation_inputs(runtime, preview, owner, fresh):
    """Metadata must describe the implementations actually installed in its owner.

    Limit this audit to the preview owner's converted character/stage bundles;
    never scan the global media library. A separate import repair supplies absent
    bundles. Custom or stale implementations are not overwritten by this tool.
    """
    hashes = {}
    native_names = {name for entry in fresh['difficulties'].values()
                    for name in (entry.get('nativeCharacters') or {}).values() if name is not None}
    builtin = {'bf', 'boyfriend', 'dad', 'daddy', 'gf', 'girlfriend', 'no-gf', 'nogf', 'no_gf'}
    for family in ('custom_chars', 'custom_stages'):
        generated = preview / owner / 'images' / family
        if not generated.is_dir():
            if family == 'custom_chars' and native_names <= builtin:
                continue
            raise ValueError('preview lacks owned implementations: ' + family)
        for source in sorted(generated.rglob('*')):
            if not source.is_file():
                continue
            if not shared.within(source, preview):
                raise ValueError('unsafe preview implementation')
            target = runtime / source.relative_to(preview)
            if not target.is_file() or not shared.within(target, runtime):
                raise ValueError('missing owned implementation: ' + target.relative_to(runtime).as_posix())
            source_hash, target_hash = digest(source.read_bytes()), digest(target.read_bytes())
            if source_hash != target_hash:
                raise ValueError('changed owned implementation: ' + target.relative_to(runtime).as_posix())
            hashes[source.as_posix()] = source_hash
            hashes[target.as_posix()] = target_hash
    return hashes


def make_plan(runtime_root, generated_root, line_only=False, include_new_difficulties=False):
    runtime, preview = runtime_root.resolve(), generated_root.resolve()
    if not shared.within(preview, TMP) or runtime == preview or shared.within(runtime, preview):
        raise ValueError('preview must be a separate repository-local tmp runtime')
    if not (runtime / 'assets/data').is_dir() or not (preview / 'assets/data').is_dir():
        raise ValueError('runtime or preview assets/data missing')
    candidates, skipped, inputs = [], [], {}
    for folder in sorted((preview / 'assets/data').iterdir()):
        manifest = folder / 'compatScripts.json'
        if not manifest.is_file() or not shared.within(manifest, preview):
            continue
        data = read(manifest)
        owner = data.get('selectedRoot')
        if (not isinstance(owner, str) or not owner.startswith('assets/imported_mods/')
                or len(owner.split('/')) != 3 or not shared.safe_segment(owner.split('/')[-1])):
            continue
        if not any(isinstance(r, dict) and r.get('path') == owner and r.get('engine') == 'Codename Engine'
                   for r in data.get('roots', [])):
            continue
        if not shared.within(preview / owner, preview) or not shared.within(runtime / owner, runtime):
            raise ValueError('unsafe owner path')
        selected = {f.name: (f, m) for f, m in shared.selected_songs(runtime, owner)}
        if folder.name not in selected:
            skipped.append({'song': folder.name, 'reason': 'installed song does not select preview owner'})
            continue
        installed_folder, installed_manifest = selected[folder.name]
        try:
            if line_only:
                old_source = owned_source_plan(runtime, owner, installed_folder)
                new_source = owned_source_plan(preview, owner, folder)
                if old_source[0] != new_source[0]:
                    raise ValueError('changed source song identity')
            else:
                old_source = shared.source_plan(runtime, owner, installed_folder)
                new_source = shared.source_plan(preview, owner, folder)
                if old_source is None or new_source is None or old_source[0] != new_source[0]:
                    raise ValueError('missing or changed source song plan')
            target, generated = old_source[1].with_name(CAMERA), new_source[1].with_name(CAMERA)
            for path, base in ((target, runtime), (generated, preview)):
                if not path.is_file() or not shared.within(path, base):
                    raise ValueError('missing or unsafe camera sidecar')
            if not line_only and read(old_source[1]) != read(new_source[1]):
                raise ValueError('authored stage script plan changed')
            old, fresh = read(target), read(generated)
            validate([target, generated])
            new_diffs = set(fresh.get('difficulties', {})) - set(old.get('difficulties', {}))
            chart_inputs = (matching_new_difficulty_charts(runtime, preview, folder, new_diffs)
                            if line_only and include_new_difficulties and new_diffs else {})
            after_data = (additive_line_upgrade(old, fresh, include_new_difficulties)
                          if line_only else additive_upgrade(old, fresh))
            if shared.canonical(old) == shared.canonical(after_data):
                continue
            owned_inputs = {} if line_only else implementation_inputs(runtime, preview, owner, fresh)
            before = target.read_bytes()
            after = (json.dumps(after_data, ensure_ascii=False, indent=2) + '\n').encode()
            for path in (target, generated, manifest, installed_manifest, old_source[1], new_source[1]):
                inputs[path.as_posix()] = digest(path.read_bytes())
            for provenance in (old_source[2], new_source[2]) if line_only else ():
                if provenance is not None:
                    inputs[provenance.as_posix()] = digest(provenance.read_bytes())
            inputs.update(owned_inputs)
            inputs.update(chart_inputs)
            candidates.append({'id': folder.name, 'target': target.as_posix(),
                               'beforeSha256': digest(before), 'afterSha256': digest(after),
                               'afterBase64': base64.b64encode(after).decode()})
        except (ValueError, OSError, TypeError, KeyError) as error:
            skipped.append({'song': folder.name, 'reason': str(error)})
    return {'version': 1, 'lineOnly': line_only, 'includeNewDifficulties': include_new_difficulties,
            'runtimeRoot': runtime.as_posix(), 'generatedRoot': preview.as_posix(),
            'toolSha256': fingerprint(), 'inputsSha256': inputs,
            'candidates': candidates, 'skipped': skipped}


def apply_plan(plan, plan_path):
    if plan.get('version') != 1 or plan.get('toolSha256') != fingerprint():
        raise ValueError('refresh implementation changed since review')
    locks = []
    try:
        for mode in ('0', '1'):
            lock = (LOCK_ROOT / ('runtime-' + mode + '.lock')).open('a+')
            locks.append(lock)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fresh = make_plan(Path(plan['runtimeRoot']), Path(plan['generatedRoot']),
                          plan.get('lineOnly') is True, plan.get('includeNewDifficulties') is True)
        if fresh != plan:
            raise ValueError('preview or destination changed since review')
        if not plan['candidates']:
            return None
        backup = TMP / 'import-refresh-backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup.mkdir(parents=True)
        shutil.copy2(plan_path, backup / 'plan.json')
        runtime = Path(plan['runtimeRoot'])
        for item in plan['candidates']:
            target = Path(item['target'])
            saved = backup / target.relative_to(runtime)
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
            if digest(saved.read_bytes()) != item['beforeSha256']:
                raise ValueError('backup verification failed')
        replaced = []
        try:
            for item in plan['candidates']:
                target = Path(item['target'])
                # Staging stays in ./tmp on this filesystem; no system temp.
                with tempfile.NamedTemporaryFile(dir=TMP, prefix='actor-refresh-', delete=False) as out:
                    staged = Path(out.name)
                    out.write(base64.b64decode(item['afterBase64'], validate=True))
                    out.flush()
                    os.fsync(out.fileno())
                try:
                    os.chmod(staged, target.stat().st_mode)
                    os.replace(staged, target)
                    replaced.append(target)
                finally:
                    staged.unlink(missing_ok=True)
        except Exception:
            for target in replaced:
                shutil.copy2(backup / target.relative_to(runtime), target)
            raise
        return backup
    finally:
        for lock in reversed(locks):
            lock.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    planning = commands.add_parser('plan')
    planning.add_argument('--runtime-root', type=Path, required=True)
    planning.add_argument('--generated-root', type=Path, required=True)
    planning.add_argument('--output', type=Path, required=True)
    planning.add_argument('--line-only', action='store_true',
                          help='add only source-line geometry and preserve older actor/stage fields')
    planning.add_argument('--include-new-difficulties', action='store_true',
                          help='with --line-only, append source difficulty sidecars when native charts match exactly')
    applying = commands.add_parser('apply')
    applying.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'plan':
        if args.include_new_difficulties and not args.line_only:
            parser.error('--include-new-difficulties requires --line-only')
        if args.output.exists() or not shared.within(args.output, TMP):
            parser.error('output must be a new repository-local tmp file')
        plan = make_plan(args.runtime_root, args.generated_root, args.line_only,
                         args.include_new_difficulties)
        args.output.write_text(json.dumps(plan, indent=2) + '\n')
        print('candidates=%d skipped=%d' % (len(plan['candidates']), len(plan['skipped'])))
    else:
        backup = apply_plan(read(args.plan), args.plan)
        print('backup: ' + backup.as_posix() if backup else 'no changes')


if __name__ == '__main__':
    main()
