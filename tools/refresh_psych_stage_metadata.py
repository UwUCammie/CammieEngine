#!/usr/bin/env python3
"""Plan or apply a backed-up Psych chart stage refresh from its donor source.

Planning is the default and writes a reviewable receipt. Application requires
an explicit --apply and a saved plan. Only charts selected by the donor's exact
Psych Engine owner are considered. A chart must omit stage in the donor, still
have the old host default installed, and match donor notes/events before its
stage value can be patched.
"""

from __future__ import annotations

import argparse
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


ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / 'tmp'
HAXE = ROOT / '.tools/haxe/haxe'
RENDERER = ROOT / 'tools/PsychStageRefreshRender.hx'
LOCK = ROOT / '.tools/runtime-0.lock'
OLD_DEFAULT = 'stage'
ENGINE = 'Psych Engine'
JSON_SIDECARS = frozenset({
    'compatScripts.json', 'events.json', 'importProvenance.json', 'noteInfo.json',
    'preload.json', 'preloadData.json',
})
JSON_SIDECAR_KEYS = frozenset(name.casefold() for name in JSON_SIDECARS)
DATA_ROOTS = (
    'assets/data',
    'assets/base_game/shared/data',
    'assets/base_game/data',
    'assets/shared/data',
    'assets/preload/data',
    'data',
)
TOOL_INPUTS = (
    Path(__file__), RENDERER,
    ROOT / 'source/PsychStageInference.hx',
    ROOT / 'source/CompatScriptManifest.hx',
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    return digest(path.read_bytes())


def within(path: Path, root: Path) -> bool:
    return path.resolve().is_relative_to(root.resolve())


def regular_child(root: Path, relative: str, *, required: bool = True) -> Path:
    """Resolve a regular file below root, rejecting symlinks and traversal."""
    part = Path(relative)
    if part.is_absolute() or not part.parts or '..' in part.parts:
        raise ValueError(f'unsafe relative path: {relative}')
    base = root.resolve()
    candidate = base / part
    current = base
    for token in part.parts:
        current = current / token
        if current.is_symlink():
            raise ValueError(f'symlink in selected path: {relative}')
    if not within(candidate, base):
        raise ValueError(f'path leaves selected root: {relative}')
    if not candidate.is_file():
        if required:
            raise ValueError(f'missing regular file: {candidate}')
        return candidate
    return candidate


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON key: {key}')
        result[key] = value
    return result


def parse_chart(path: Path) -> tuple[dict, dict]:
    try:
        value = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f'invalid chart JSON: {path}: {error}') from error
    song = value.get('song') if isinstance(value, dict) else None
    if not isinstance(song, dict) or not isinstance(song.get('song'), str):
        raise ValueError(f'chart has no song identity: {path}')
    if not isinstance(song.get('notes'), list) or not isinstance(song.get('events'), list):
        raise ValueError(f'chart has no notes/events arrays: {path}')
    return value, song


def selected_owner(manifest: Path, expected: str) -> tuple[bool, str | None]:
    if manifest.is_symlink() or not manifest.is_file():
        return False, 'missing or unsafe compatScripts.json'
    try:
        value = json.loads(manifest.read_text(encoding='utf-8'), object_pairs_hook=unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        return False, f'invalid compatScripts.json: {error}'
    roots = value.get('roots') if isinstance(value, dict) else None
    selected = value.get('selectedRoot') if isinstance(value, dict) else None
    if selected != expected:
        return False, None
    matches = [row for row in roots if isinstance(row, dict)
               and row.get('path') == expected and row.get('engine') == ENGINE] \
        if isinstance(roots, list) else []
    if len(matches) != 1:
        return False, 'ambiguous selected Psych owner entry'
    return True, None


def safe_segment(value: object) -> bool:
    return (isinstance(value, str) and value.strip() not in ('', '.', '..')
            and all(token not in value for token in ('/', '\\', ':', '\0')))


def qualified_source_folder(destination: str, owner: str) -> str | None:
    owner_id = owner.rsplit('/', 1)[-1]
    owner_digest = owner_id.rsplit('-', 1)[-1]
    if len(owner_digest) != 10 or any(char not in '0123456789abcdef' for char in owner_digest):
        return None
    suffix = '--psych-engine-' + owner_digest
    if not destination.casefold().endswith(suffix):
        return None
    source_folder = destination[:-len(suffix)]
    return source_folder if safe_segment(source_folder) else None


def source_folder_for(runtime_folder: Path, owner: str) -> tuple[str | None, str | None]:
    provenance = runtime_folder / 'importProvenance.json'
    if provenance.is_symlink():
        return None, 'unsafe import provenance sidecar'
    if provenance.exists():
        if not provenance.is_file():
            return None, 'unsafe import provenance sidecar'
        try:
            value = json.loads(provenance.read_text(encoding='utf-8'),
                               object_pairs_hook=unique_object)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
            return None, f'invalid import provenance sidecar: {error}'
        if not isinstance(value, dict) or value.get('sourceOwner') != owner \
                or value.get('sourceEngine') != ENGINE \
                or value.get('destinationFolder') != runtime_folder.name:
            return None, 'import provenance does not match selected owner and folder'
        source_folder = value.get('sourceFolder')
        if not safe_segment(source_folder):
            return None, 'import provenance has an unsafe source folder'
        return source_folder.strip(), None
    qualified = qualified_source_folder(runtime_folder.name, owner)
    return (qualified or runtime_folder.name), None


def native_chart_name(filename: str, runtime_folder: str, source_folder: str) -> bool:
    if filename.casefold() in JSON_SIDECAR_KEYS:
        return False
    stem = Path(filename).stem.casefold()
    return any(stem == name.casefold() or stem.startswith(name.casefold() + '-')
               for name in {runtime_folder, source_folder})


def chart_files(runtime: Path, owner: str):
    data_root = runtime / 'assets/data'
    if data_root.is_symlink() or not data_root.is_dir() or not within(data_root, runtime):
        raise ValueError('runtime assets/data is missing or unsafe')
    for folder in sorted(data_root.iterdir(), key=lambda item: item.name.casefold()):
        if folder.is_symlink() or not folder.is_dir() or not within(folder, runtime):
            continue
        manifest = folder / 'compatScripts.json'
        if not manifest.exists():
            continue
        matched, reason = selected_owner(manifest, owner)
        if matched:
            source_folder, folder_issue = source_folder_for(folder, owner)
            if folder_issue is not None:
                yield {'folder': folder.name, 'reason': folder_issue}, None, None
                continue
            for candidate in sorted(folder.iterdir(), key=lambda item: item.name.casefold()):
                if (candidate.suffix.lower() == '.json'
                        and native_chart_name(candidate.name, folder.name, source_folder)
                        and not candidate.is_symlink() and candidate.is_file()
                        and within(candidate, runtime)):
                    yield candidate.relative_to(runtime).as_posix(), candidate, source_folder
        elif reason is not None:
            yield {'folder': folder.name, 'reason': reason}, None, None


def source_data_folders(donor: Path, folder_name: str) -> list[Path]:
    matches = []
    for relative in DATA_ROOTS:
        base = donor / relative
        if base.is_symlink() or not base.is_dir() or not within(base, donor):
            continue
        exact = base / folder_name
        if exact.is_dir() and not exact.is_symlink() and within(exact, donor):
            matches.append(exact)
            continue
        folded = [entry for entry in base.iterdir()
                  if entry.is_dir() and not entry.is_symlink()
                  and entry.name.casefold() == folder_name.casefold()
                  and within(entry, donor)]
        if len(folded) == 1:
            matches.append(folded[0])
        elif len(folded) > 1:
            matches.extend(folded)
    return matches


def source_name_aliases(runtime_chart: Path, runtime_folder: str,
                        source_folder: str) -> set[str]:
    stem = runtime_chart.stem
    aliases = {stem.casefold() + '.json'}
    runtime_prefix = runtime_folder.casefold() + '-'
    if stem.casefold().startswith(runtime_prefix):
        suffix = stem[len(runtime_folder) + 1:]
        aliases.add(suffix.casefold() + '.json')
        aliases.add((source_folder + '-' + suffix).casefold() + '.json')
    source_prefix = source_folder.casefold() + '-'
    if stem.casefold().startswith(source_prefix):
        difficulty = stem[len(source_folder) + 1:]
        aliases.add(difficulty.casefold() + '.json')
        aliases.add((source_folder + '-' + difficulty).casefold() + '.json')
    if stem.casefold() in (runtime_folder.casefold(), source_folder.casefold()):
        aliases.add((source_folder + '.json').casefold())
        aliases.add('normal.json')
    return aliases


def locate_source_chart(donor: Path, relative: str,
                        source_folder_name: str) -> tuple[Path | None, str | None]:
    native = Path(relative)
    if native.parts[:2] != ('assets', 'data') or len(native.parts) != 4:
        return None, 'installed chart is outside assets/data/<song>/<chart>.json'
    runtime_folder = native.parts[2]
    source_folders = source_data_folders(donor, source_folder_name)
    if not source_folders:
        return None, 'donor chart folder was not found in supported Psych data roots'
    aliases = source_name_aliases(native, runtime_folder, source_folder_name)
    matches = []
    for folder in source_folders:
        if not within(folder, donor):
            continue
        for candidate in folder.iterdir():
            if (candidate.is_file() and candidate.suffix.lower() == '.json'
                    and candidate.name.casefold() in aliases
                    and not candidate.is_symlink() and within(candidate, donor)):
                matches.append(candidate)
    unique = sorted(set(matches))
    if len(unique) > 1:
        return None, 'ambiguous donor chart match: ' + ', '.join(
            path.relative_to(donor).as_posix() for path in unique)
    if not unique:
        return None, 'matching donor chart was not found'
    return unique[0], None


def _skip_space(text: str, pos: int) -> int:
    while pos < len(text) and text[pos] in ' \t\r\n':
        pos += 1
    return pos


def _string_end(text: str, pos: int) -> int:
    if pos >= len(text) or text[pos] != '"':
        raise ValueError('expected JSON string')
    pos += 1
    while pos < len(text):
        if text[pos] == '\\':
            pos += 2
        elif text[pos] == '"':
            return pos + 1
        else:
            pos += 1
    raise ValueError('unterminated JSON string')


def _value_end(text: str, pos: int) -> int:
    if pos >= len(text):
        raise ValueError('missing JSON value')
    if text[pos] == '"':
        return _string_end(text, pos)
    if text[pos] in '{[':
        stack = ['}' if text[pos] == '{' else ']']
        pos += 1
        while stack:
            if pos >= len(text):
                raise ValueError('unterminated JSON value')
            char = text[pos]
            if char == '"':
                pos = _string_end(text, pos)
                continue
            if char in '{[':
                stack.append('}' if char == '{' else ']')
            elif char in ']}':
                if stack.pop() != char:
                    raise ValueError('malformed JSON nesting')
            pos += 1
        return pos
    while pos < len(text) and text[pos] not in ',]} \t\r\n':
        pos += 1
    return pos


def _object_fields(text: str, pos: int) -> dict[str, tuple[int, int]]:
    if text[pos] != '{':
        raise ValueError('expected JSON object')
    pos = _skip_space(text, pos + 1)
    fields = {}
    while pos < len(text) and text[pos] != '}':
        end = _string_end(text, pos)
        key = json.loads(text[pos:end])
        if key in fields:
            raise ValueError(f'duplicate JSON key: {key}')
        pos = _skip_space(text, end)
        if pos >= len(text) or text[pos] != ':':
            raise ValueError('expected JSON colon')
        start = _skip_space(text, pos + 1)
        end = _value_end(text, start)
        fields[key] = (start, end)
        pos = _skip_space(text, end)
        if pos < len(text) and text[pos] == ',':
            pos = _skip_space(text, pos + 1)
        elif pos >= len(text) or text[pos] != '}':
            raise ValueError('expected JSON delimiter')
    return fields


def stage_value_span(text: str) -> tuple[int, int]:
    root = _object_fields(text, _skip_space(text, 0))
    if 'song' not in root:
        raise ValueError('native chart has no song field')
    song = _object_fields(text, root['song'][0])
    if 'stage' not in song:
        raise ValueError('native chart has no stage field')
    return song['stage']


def replace_stage(text: str, stage: str) -> str:
    start, end = stage_value_span(text)
    encoded = json.dumps(stage, ensure_ascii=False, separators=(',', ':'))
    return text[:start] + encoded + text[end:]


def tool_fingerprints() -> dict[str, str]:
    return {path.relative_to(ROOT).as_posix(): file_digest(path) for path in TOOL_INPUTS}


def stage_data_fingerprints(donor: Path) -> dict[str, str]:
    files = {}
    for relative in ('source/backend/StageData.hx', 'source/StageData.hx',
                     'src/backend/StageData.hx', 'backend/StageData.hx'):
        candidate = donor / relative
        if candidate.is_symlink() or not candidate.is_file() or not within(candidate, donor):
            continue
        files[relative] = file_digest(candidate)
    return files


def render(donor: Path, charts: list[dict]) -> dict:
    if not HAXE.is_file():
        raise ValueError(f'portable Haxe interpreter is missing: {HAXE}')
    request = {'donorRoot': donor.resolve().as_posix(), 'charts': charts}
    TMP.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='psych-stage-refresh-', dir=TMP) as work:
        request_path = Path(work) / 'request.json'
        request_path.write_text(json.dumps(request), encoding='utf-8')
        run = subprocess.run(
            [HAXE.as_posix(), '-cp', (ROOT / 'source').as_posix(), '-cp', (ROOT / 'tools').as_posix(),
             '--run', 'PsychStageRefreshRender', str(request_path)],
            cwd=ROOT, capture_output=True, text=True, timeout=120)
        if run.returncode:
            message = run.stderr.strip() or run.stdout.strip() or 'no output'
            raise ValueError('Psych stage inference renderer failed: ' + message)
        try:
            output = json.loads(run.stdout)
        except json.JSONDecodeError as error:
            raise ValueError('Psych stage inference renderer returned invalid JSON') from error
    if not isinstance(output, dict) or not isinstance(output.get('owner'), str) \
            or not isinstance(output.get('charts'), list):
        raise ValueError('Psych stage inference renderer returned an invalid result')
    return output


def parse_bytes_chart(data: bytes, path: Path) -> tuple[dict, dict]:
    try:
        value = json.loads(data.decode('utf-8'), object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f'invalid chart JSON after patch: {path}: {error}') from error
    song = value.get('song') if isinstance(value, dict) else None
    if not isinstance(song, dict) or not isinstance(song.get('notes'), list) \
            or not isinstance(song.get('events'), list):
        raise ValueError(f'chart structure changed after patch: {path}')
    return value, song


def make_plan(donor_root: Path, runtime_root: Path, old_default: str = OLD_DEFAULT) -> dict:
    donor, runtime = donor_root.resolve(), runtime_root.resolve()
    if not donor.is_dir() or not runtime.is_dir():
        raise ValueError('donor source and runtime roots must exist')
    if not old_default.strip():
        raise ValueError('old default stage must be nonempty')
    stage_data = stage_data_fingerprints(donor)
    if not stage_data:
        raise ValueError('donor has no StageData.hx in a supported source location')
    owner_result = render(donor, [])
    owner = owner_result['owner']
    if not owner.startswith('assets/imported_mods/') or '..' in Path(owner).parts:
        raise ValueError(f'engine returned an unsafe owner namespace: {owner}')

    issues = []
    inference_inputs = []
    pending = []
    owner_chart_count = 0
    for item, installed_path, source_folder_name in chart_files(runtime, owner):
        if installed_path is None:
            issues.append(item)
            continue
        relative = item
        owner_chart_count += 1
        try:
            installed, installed_song = parse_chart(installed_path)
        except ValueError as error:
            issues.append({'chart': relative, 'reason': str(error)})
            continue
        try:
            source_path, source_issue = locate_source_chart(
                donor, relative, source_folder_name)
        except OSError as error:
            issues.append({'chart': relative, 'reason': f'donor chart lookup failed: {error}'})
            continue
        if source_path is None:
            issues.append({'chart': relative, 'reason': source_issue or 'donor chart missing'})
            continue
        try:
            authored, authored_song = parse_chart(source_path)
        except ValueError as error:
            issues.append({'chart': relative, 'reason': f'invalid donor chart: {error}'})
            continue
        if 'stage' in authored_song:
            continue
        installed_stage = installed_song.get('stage')
        if not isinstance(installed_stage, str) or installed_stage.casefold() != old_default.casefold():
            continue
        if authored_song['notes'] != installed_song['notes'] or authored_song['events'] != installed_song['events']:
            issues.append({'chart': relative,
                           'reason': 'donor notes/events differ from installed chart; source match is ambiguous'})
            continue
        song_name = authored_song['song'].strip()
        if not song_name:
            issues.append({'chart': relative, 'reason': 'donor chart song identity is empty'})
            continue
        request_id = f'{relative}::{len(pending)}'
        pending.append({'id': request_id, 'relative': relative,
                        'installedSha256': file_digest(installed_path),
                        'donorChart': source_path.as_posix(),
                        'donorSha256': file_digest(source_path),
                        'song': song_name, 'oldStage': installed_stage})
        inference_inputs.append({'id': request_id, 'song': song_name})

    inferred = render(donor, inference_inputs)['charts'] if inference_inputs else []
    by_id = {row.get('id'): row for row in inferred if isinstance(row, dict)}
    candidates = []
    for item in pending:
        result = by_id.get(item['id'])
        stage = result.get('stage') if result is not None else None
        if not isinstance(stage, str) or not stage.strip() or stage.strip().casefold() == 'null':
            issues.append({'chart': item['relative'], 'reason': 'Psych StageData has no literal stage mapping'})
            continue
        stage = stage.strip()
        if stage.casefold() == item['oldStage'].casefold():
            continue
        target = regular_child(runtime, item['relative'])
        before = target.read_bytes()
        if digest(before) != item['installedSha256']:
            issues.append({'chart': item['relative'],
                           'reason': 'installed chart changed during planning'})
            continue
        try:
            text = before.decode('utf-8')
            patched = replace_stage(text, stage).encode('utf-8')
            _, after_song = parse_bytes_chart(patched, target)
            _, before_song = parse_chart(target)
        except (UnicodeError, ValueError) as error:
            issues.append({'chart': item['relative'], 'reason': f'cannot patch stage field: {error}'})
            continue
        if after_song.get('stage') != stage:
            issues.append({'chart': item['relative'], 'reason': 'stage-only patch verification failed'})
            continue
        if any(after_song.get(key) != before_song.get(key) for key in ('notes', 'events')):
            issues.append({'chart': item['relative'], 'reason': 'stage patch altered notes/events'})
            continue
        candidates.append({
            'chart': item['relative'], 'donorChart': Path(item['donorChart']).relative_to(donor).as_posix(),
            'donorChartSha256': item['donorSha256'], 'installedSha256': digest(before),
            'afterSha256': digest(patched), 'oldStage': item['oldStage'], 'newStage': stage,
        })

    if owner_chart_count == 0:
        issues.append({'reason': 'no runtime charts select the donor Psych Engine owner'})
    options = runtime / 'assets/data/options.json'
    options_sha = file_digest(options) if options.is_file() and not options.is_symlink() else None
    return {
        'version': 1,
        'donorRoot': donor.as_posix(),
        'runtimeRoot': runtime.as_posix(),
        'selectedRoot': owner,
        'oldDefault': old_default,
        'toolInputsSha256': tool_fingerprints(),
        'stageDataSha256': stage_data,
        'runtimeOptionsSha256': options_sha,
        'charts': candidates,
        'skipped': issues,
    }


def atomic_write(target: Path, content: bytes, scratch: Path) -> None:
    scratch.parent.mkdir(parents=True, exist_ok=True)
    scratch.write_bytes(content)
    os.chmod(scratch, target.stat().st_mode)
    os.replace(scratch, target)


def apply_plan(saved: dict, receipt_path: Path) -> dict:
    if saved.get('version') != 1 or saved.get('status') != 'planned':
        raise ValueError('unsupported or unapplied Psych stage refresh plan')
    if receipt_path.exists():
        raise ValueError(f'receipt already exists: {receipt_path}')
    donor, runtime = Path(saved['donorRoot']), Path(saved['runtimeRoot'])
    planned = {key: value for key, value in saved.items() if key != 'status'}
    current = make_plan(donor, runtime, saved['oldDefault'])
    if current != planned:
        raise ValueError('donor, selected owner, charts, settings, or tool changed since planning')
    if not saved['charts']:
        receipt = {'version': 1, 'status': 'applied', 'selectedRoot': saved['selectedRoot'],
                   'backup': None, 'changed': 0, 'charts': [], 'skipped': saved['skipped'],
                   'runtimeOptionsUnchanged': True}
        write_new_json(receipt_path, receipt)
        return receipt

    backup = TMP / 'psych-stage-refresh-backups' / (
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + str(os.getpid()))
    backup.mkdir(parents=True, exist_ok=False)
    for item in saved['charts']:
        relative = item['chart']
        target = regular_child(runtime, relative)
        saved_file = backup / relative
        saved_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, saved_file)
        if file_digest(saved_file) != item['installedSha256']:
            raise ValueError(f'backup verification failed: {relative}')

    replaced = []
    try:
        for item in saved['charts']:
            relative = item['chart']
            target = regular_child(runtime, relative)
            before = target.read_bytes()
            if digest(before) != item['installedSha256']:
                raise ValueError(f'installed chart changed during refresh: {relative}')
            patched = replace_stage(before.decode('utf-8'), item['newStage']).encode('utf-8')
            if digest(patched) != item['afterSha256']:
                raise ValueError(f'planned stage patch changed: {relative}')
            atomic_write(target, patched, backup / (relative + '.new'))
            replaced.append(relative)
            _, updated = parse_bytes_chart(target.read_bytes(), target)
            if updated.get('stage') != item['newStage']:
                raise ValueError(f'stage patch verification failed: {relative}')
        options = runtime / 'assets/data/options.json'
        current_options = file_digest(options) if options.is_file() and not options.is_symlink() else None
        if current_options != saved['runtimeOptionsSha256']:
            raise ValueError('runtime options changed during stage refresh')
    except Exception:
        for relative in reversed(replaced):
            target = regular_child(runtime, relative)
            saved_file = backup / relative
            atomic_write(target, saved_file.read_bytes(), backup / (relative + '.restore'))
        raise

    receipt = {'version': 1, 'status': 'applied', 'selectedRoot': saved['selectedRoot'],
               'backup': backup.as_posix(), 'changed': len(replaced), 'charts': saved['charts'],
               'skipped': saved['skipped'], 'runtimeOptionsUnchanged': True}
    write_new_json(receipt_path, receipt)
    return receipt


def write_new_json(path: Path, value: dict) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as output:
        json.dump(value, output, indent=2, ensure_ascii=False)
        output.write('\n')


def output_outside_roots(path: Path, donor: Path, runtime: Path) -> bool:
    resolved = path.resolve()
    return not within(resolved, donor) and not within(resolved, runtime)


def default_receipt() -> Path:
    return TMP / ('psych-stage-refresh-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--donor-root', type=Path,
                        help='Psych source tree whose StageData.hx owns the inference')
    parser.add_argument('--runtime-root', type=Path,
                        help='installed game root containing assets/data')
    parser.add_argument('--old-default', default=OLD_DEFAULT,
                        help='installed host fallback stage to replace (default: stage)')
    parser.add_argument('--receipt', type=Path,
                        help='new dry-run or apply receipt path (default: a unique file in tmp/)')
    parser.add_argument('--plan', type=Path,
                        help='reviewed dry-run plan to apply')
    parser.add_argument('--apply', action='store_true',
                        help='apply a saved plan after creating and verifying backups')
    args = parser.parse_args()

    if args.apply:
        if args.plan is None or args.donor_root is not None or args.runtime_root is not None:
            parser.error('--apply requires --plan and cannot be combined with donor/runtime roots')
        saved = json.loads(args.plan.read_text(encoding='utf-8'))
        donor, runtime = Path(saved.get('donorRoot', '')), Path(saved.get('runtimeRoot', ''))
        receipt_path = args.receipt or args.plan.with_name(args.plan.stem + '.applied.json')
        if not output_outside_roots(receipt_path, donor, runtime):
            parser.error('apply receipt must be outside donor and runtime roots')
        TMP.mkdir(exist_ok=True)
        with LOCK.open('a+') as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            receipt = apply_plan(saved, receipt_path)
        print(json.dumps({'status': receipt['status'], 'changed': receipt['changed'],
                          'backup': receipt['backup'], 'receipt': receipt_path.resolve().as_posix()}))
        return 0

    if args.plan is not None or args.donor_root is None or args.runtime_root is None:
        parser.error('dry-run requires --donor-root and --runtime-root; --plan is for --apply')
    donor, runtime = args.donor_root.resolve(), args.runtime_root.resolve()
    receipt_path = args.receipt or default_receipt()
    if not output_outside_roots(receipt_path, donor, runtime):
        parser.error('dry-run receipt must be outside donor and runtime roots')
    plan = make_plan(donor, runtime, args.old_default)
    plan['status'] = 'planned'
    write_new_json(receipt_path, plan)
    print(json.dumps({'status': 'planned', 'selectedRoot': plan['selectedRoot'],
                      'changed': len(plan['charts']), 'skipped': len(plan['skipped']),
                      'receipt': receipt_path.resolve().as_posix()}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
