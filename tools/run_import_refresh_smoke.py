#!/usr/bin/env python3
"""Check two native imports and automatic retained-source refresh offscreen.

Uses an existing Linux build, default private settings, muted audio and the
runtime build lock. --wine checks the Windows build using a private prefix.
Only fixture files under repository tmp are modified.
"""
from __future__ import annotations
import argparse
try:
    from tools import file_lock as fcntl
except ModuleNotFoundError:
    import file_lock as fcntl  # Direct python tools/<script>.py invocation.
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
from run_runtime_smoke_matrix import _prepare_case_overlay, _case_environment, offscreen_command

ROOT = Path(__file__).resolve().parents[1]


def materialize_directory(path: Path) -> None:
    if path.is_symlink():
        original = path.resolve()
        path.unlink()
        path.mkdir()
        for entry in original.iterdir():
            (path / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
    else:
        path.mkdir(parents=True, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path)
    parser.add_argument('--wine', action='store_true', help='check the Windows build under Wine')
    parser.add_argument('--wine-prefix-seed', type=Path, help='copy an initialized test prefix; never change the seed')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    default_binary = 'export/release/windows/bin/Funkin.exe' if args.wine else 'export/release/linux/bin/Funkin'
    binary = (args.binary or ROOT / default_binary).resolve()
    default_output = 'tmp/import-refresh-wine-native-check' if args.wine else 'tmp/import-refresh-native-check'
    output = (args.output or ROOT / default_output).resolve()
    if not binary.is_file():
        parser.error('Build first with ./run.sh build')
    if not output.is_relative_to(ROOT / 'tmp'):
        parser.error('Evidence output must be inside repository tmp')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'verification.json').unlink(missing_ok=True)
    ROOT.joinpath('tmp').mkdir(exist_ok=True)
    if args.wine_prefix_seed and (not args.wine or not (args.wine_prefix_seed / 'system.reg').is_file()):
        parser.error('--wine-prefix-seed requires --wine and an initialized prefix')
    with tempfile.TemporaryDirectory(prefix='retained-import-', dir=ROOT / 'tmp') as scratch_name:
        scratch = Path(scratch_name)
        if args.wine_prefix_seed:
            shutil.copytree(args.wine_prefix_seed, scratch / 'wine-prefix', symlinks=True)
        runtime = scratch / 'runtime'
        runtime.mkdir()
        _prepare_case_overlay(binary.parent, runtime)
        cached = runtime / 'import-cache'
        if cached.is_symlink():
            cached.unlink()
        for relative in ['assets/images', 'assets/images/custom_chars', 'assets/images/custom_stages',
                         'assets/images/custom_cutscenes', 'assets/images/custom_difficulties',
                         'assets/images/custom_ui', 'assets/images/custom_ui/ui_packs',
                         'assets/module', 'assets/module/import', 'assets/songs']:
            materialize_directory(runtime / relative)
        for relative in ['assets/data/freeplaySongJson.jsonc', 'assets/data/freeplaySongJson.json',
                         'assets/images/custom_chars/custom_chars.jsonc',
                         'assets/images/custom_stages/custom_stages.json',
                         'assets/images/custom_cutscenes/cutscenes.json',
                         'assets/images/custom_difficulties/difficulties.json',
                         'assets/images/custom_ui/ui_packs/ui.json']:
            target = runtime / relative
            if target.is_symlink():
                content = target.read_bytes()
                target.unlink()
                target.write_bytes(content)
        # Small real registry keeps this import test independent of library size.
        registry = runtime / 'assets/data/freeplaySongJson.jsonc'
        registry.write_text(json.dumps([
            {'name': 'All', 'songs': [{'name': 'Random-Song', 'character': 'bf', 'week': 0}]},
            {'name': 'Base', 'songs': [{'name': 'Tutorial', 'character': 'gf', 'week': 0,
                                      'sourceLabel': 'Café 🎵'}]},
        ], ensure_ascii=False), encoding='utf-8')
        audio = ROOT / 'assets/songs/tutorial/Inst.ogg'
        if not audio.exists():
            audio = next((ROOT / 'assets/songs/tutorial').glob('*.ogg'))
        for key in ['a', 'b']:
            source = scratch / f'Source {key}'
            chart_root = source / 'data' / f'retained-native-{key}'
            song_root = source / 'songs' / f'retained-native-{key}'
            chart_root.mkdir(parents=True)
            song_root.mkdir(parents=True)
            (source / 'pack.json').write_text(json.dumps({'name': f'Retained Native {key}',
                                                        'id': f'retained-native-{key}'}))
            (source / 'future.asset').write_bytes(b'unknown retained source content')
            (source / 'mesh.obj').write_text('v 0 0 0\nf 1 1 1\n')
            (source / 'Dependency.class').write_bytes(bytes.fromhex('cafebabe0000003d0001') + bytes(5000))
            (source / 'engine.exe').write_bytes(b'MZ' + bytes(100))
            (chart_root / f'retained-native-{key}.json').write_text(json.dumps({'song': {
                'song': f'retained-native-{key}', 'bpm': 100, 'speed': 1, 'needsVoices': False,
                'player1': 'bf', 'player2': 'dad', 'gfVersion': 'gf', 'stage': 'stage', 'notes': [{
                    'mustHitSection': True, 'sectionNotes': [[1000, 0, 0], [1500, 1, 0]],
                    'lengthInSteps': 16, 'typeOfSection': 0, 'bpm': 100, 'changeBPM': False,
                }],
            }}))
            shutil.copyfile(audio, song_root / 'Inst.ogg')

        def run(case: str, flags: list[str]) -> None:
            log_path = output / (case + '.jsonl')
            process_log = output / (case + '.process.log')
            failure_path = output / (case + '.failure-state.json')
            failure_path.unlink(missing_ok=True)
            log_path.write_text('')
            command = [str(binary), '--smoke-runtime-root', str(runtime), *flags, str(log_path)]
            environment = _case_environment(binary, runtime, args.wine)
            if args.wine:
                # Each check gets its own prefix and default Z: mapping. Never
                # use the desktop Wine prefix or its saved game preferences.
                environment['WINEPREFIX'] = str(scratch / 'wine-prefix')
                environment['WINEDEBUG'] = '-all'
                environment['WINEDLLOVERRIDES'] = 'mscoree,mshtml='
                command = ['wine', command[0], *[
                    'Z:' + value.replace('/', '\\') if value.startswith('/') else value
                    for value in command[1:]
                ]]
            lock_index = 1 if binary.is_relative_to(ROOT / 'export/debug') else 0
            timed_out = False
            with (ROOT / f'.tools/runtime-{lock_index}.lock').open('w') as lock, process_log.open('w') as log:
                fcntl.flock(lock, fcntl.LOCK_EX)
                process = subprocess.Popen(offscreen_command(command), cwd=runtime, env=environment,
                                           stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    returncode = process.wait(timeout=90)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    returncode = -1
                finally:
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGTERM)
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid, signal.SIGKILL)
                            process.wait()
                    if args.wine:
                        subprocess.run(['wineserver', '-k'], env=environment, stdout=log,
                                       stderr=subprocess.STDOUT, timeout=10, check=False)
            records = [json.loads(line.split('|', 1)[1]) for line in log_path.read_text().splitlines()
                       if line.startswith(('RUNTIME_SMOKE|', 'RUNTIME_IMPORT_SMOKE|'))]
            if timed_out or returncode != 0 or not any(row.get('event') == 'success' for row in records):
                staged = runtime / 'import-cache/staging'
                inventory = [str(path.relative_to(runtime)) for path in staged.rglob('*')]
                failure_path.write_text(json.dumps({
                    'returncode': returncode, 'timedOut': timed_out, 'markers': records, 'stagingPaths': inventory,
                }, indent=2))
                raise RuntimeError(f'{case} failed (exit {returncode}); see {process_log}')
            staged = runtime / 'import-cache/staging'
            if staged.exists() and any(staged.iterdir()):
                raise RuntimeError(f'{case} left disposable import staging behind; see {process_log}')
            print(f'{case}: passed', flush=True)
            (output / (case + '.registry.json')).write_bytes(registry.read_bytes())

        for key in ['a', 'b']:
            run('import-' + key, ['--smoke-import-source', str(scratch / f'Source {key}'),
                                 '--smoke-import-type', 'Psych Engine',
                                 '--smoke-import-timeout-ms', '60000', '--smoke-import-log'])
        manifests = list((runtime / 'import-cache/state').glob('*/manifest.json'))
        if len(manifests) != 2:
            raise RuntimeError('Two separate committed owners were not created')
        stale_path = None
        for path in manifests:
            document = json.loads(path.read_text())
            record = document['revision']['importRecord']
            content = runtime / 'import-cache' / record['source']
            if not all((content / name).exists() for name in ['future.asset', 'mesh.obj', 'Dependency.class']):
                raise RuntimeError('Non-native source content was not retained')
            if (content / 'engine.exe').exists():
                raise RuntimeError('Native executable was retained')
            if record['label'] == 'Source a':
                # Model a valid prior importer stamp; maintain its receipt.
                for stamp in record['revisions']:
                    stamp['commonRevision'] = 0
                path.write_text(json.dumps(document))
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                transaction = path.parent / 'transactions' / document['transactionId']
                receipt_path = transaction / 'receipt.json'
                receipt = json.loads(receipt_path.read_text())
                receipt['manifestSha256'] = digest
                receipt_path.write_text(json.dumps(receipt))
                for journal_path in transaction.glob('journal-*.json'):
                    journal = json.loads(journal_path.read_text())
                    journal['manifestAfterSha256'] = digest
                    journal_path.write_text(json.dumps(journal))
                stale_path = path
                shutil.rmtree(scratch / 'Source a')
        if stale_path is None:
            raise RuntimeError('Expected source owner is missing')
        run('automatic-refresh', ['--smoke-freeplay', '--smoke-duration-ms', '12000', '--smoke-log'])
        refreshed = json.loads(stale_path.read_text())
        if not all(stamp['commonRevision'] > 0 for stamp in refreshed['revision']['importRecord']['revisions']):
            raise RuntimeError('Browsing did not publish the automatic refresh')
        for key in ['a', 'b']:
            if not (runtime / 'assets/data' / f'retained-native-{key}' / f'retained-native-{key}.json').exists():
                raise RuntimeError('A separate import was lost during refresh')
        registry_rows = json.loads(registry.read_text(encoding='utf-8'))
        base_row = next((row for row in registry_rows if row.get('name') == 'Base'), {})
        if not any(song.get('sourceLabel') == 'Café 🎵' for song in base_row.get('songs', [])):
            raise RuntimeError(f'Unicode base registry content was changed: {base_row!r}')
        (output / 'verification.json').write_text(json.dumps({
            'binarySha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
            'target': 'windows-wine' if args.wine else 'linux',
            'imports': 2, 'donorDeletedBeforeRefresh': True, 'automaticRefresh': True,
            'unknownAssetsRetained': True, 'nativeExecutableExcluded': True,
            'bothImportsPreserved': True, 'unicodeRegistryPreserved': True,
            'stagingCleanedAfterEachImport': True,
            'runtimeCleanedAfterCheck': True,
        }, indent=2))
    print(f'All retained-source native checks passed. Evidence: {output}', flush=True)


if __name__ == '__main__':
    main()
