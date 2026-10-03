"""Scoped Psych stage refresh uses donor inference and patches only stage."""

import importlib.util
import json
from pathlib import Path
from haxe_test_support import FixturePath as Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'refresh_psych_stage_metadata', ROOT / 'tools/refresh_psych_stage_metadata.py')
refresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(refresh)


class RefreshPsychStageMetadataTest(unittest.TestCase):
    def test_infers_only_owner_matched_omitted_stage_chart_and_backs_it_up(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as scratch:
            root = Path(scratch)
            donor, runtime = root / 'donor', root / 'runtime'
            stage_data = donor / 'source/backend/StageData.hx'
            stage_data.parent.mkdir(parents=True)
            stage_data.write_text("""class StageData {
  public static function vanillaSongStage(songName:String):String {
    var stage = 'stage';
    switch (songName.toLowerCase()) {
      case 'spookeez': stage = 'spooky';
      default: stage = 'stage';
    }
    return stage;
  }
}""", encoding='utf-8', newline='\n')

            owner = refresh.render(donor, [])['owner']
            source_folder = donor / 'assets/base_game/shared/data/spookeez'
            live_folder = runtime / 'assets/data/spookeez'
            source_folder.mkdir(parents=True)
            live_folder.mkdir(parents=True)
            owner_digest = owner.rsplit('-', 1)[-1]
            qualified_name = f'spookeez--psych-engine-{owner_digest}'
            qualified_folder = runtime / 'assets/data' / qualified_name
            qualified_folder.mkdir()
            provenance_folder = runtime / 'assets/data' / f'alias--psych-engine-{owner_digest}'
            provenance_folder.mkdir()
            source_charts = {
                'spookeez-easy.json': {
                    'song': {'song': 'Spookeez', 'notes': [{'sectionNotes': [[1000, 1, 0]]}],
                             'events': []}
                },
                'spookeez-hard.json': {
                    'song': {'song': 'Spookeez', 'stage': 'authored-stage',
                             'notes': [{'sectionNotes': [[2000, 2, 0]]}], 'events': []}
                },
                'spookeez.json': {
                    'song': {'song': 'Spookeez', 'notes': [{'sectionNotes': [[3000, 3, 0]]}],
                             'events': []}
                },
                'spookeez-mismatch.json': {
                    'song': {'song': 'Spookeez', 'notes': [{'sectionNotes': [[4000, 4, 0]]}],
                             'events': []}
                },
            }
            installed = {
                'spookeez-easy.json': {
                    'song': {'song': 'Spookeez', 'stage': 'stage',
                             'notes': [{'sectionNotes': [[1000, 1, 0]]}], 'events': [],
                             'nativeSettings': {'keep': [True, 5]}}
                },
                # The donor authored a stage, so its old-looking installed stage
                # must remain untouched.
                'spookeez-hard.json': {
                    'song': {'song': 'Spookeez', 'stage': 'stage',
                             'notes': [{'sectionNotes': [[2000, 2, 0]]}], 'events': []}
                },
                # A custom installed stage is outside the old-default repair.
                'spookeez.json': {
                    'song': {'song': 'Spookeez', 'stage': 'custom-stage',
                             'notes': [{'sectionNotes': [[3000, 3, 0]]}], 'events': []}
                },
                'spookeez-mismatch.json': {
                    'song': {'song': 'Spookeez', 'stage': 'stage',
                             'notes': [{'sectionNotes': [[4001, 4, 0]]}], 'events': []}
                },
            }
            for name, value in source_charts.items():
                (source_folder / name).write_text(json.dumps(value), encoding='utf-8', newline='\n')
            original_bytes = {}
            for name, value in installed.items():
                path = live_folder / name
                path.write_text(json.dumps(value), encoding='utf-8', newline='\n')
                original_bytes[name] = path.read_bytes()
            qualified_chart = qualified_folder / f'{qualified_name}-spookeez-easy.json'
            qualified_chart.write_text(json.dumps(installed['spookeez-easy.json']),
                                       encoding='utf-8', newline='\n')
            provenance_chart = provenance_folder / (
                f'{provenance_folder.name}-spookeez-easy.json')
            provenance_chart.write_text(json.dumps(installed['spookeez-easy.json']),
                                        encoding='utf-8', newline='\n')
            (live_folder / 'compatScripts.json').write_text(json.dumps({
                'version': 1, 'selectedRoot': owner,
                'roots': [{'engine': 'Psych Engine', 'path': owner}],
            }), encoding='utf-8', newline='\n')
            for folder in (qualified_folder, provenance_folder):
                (folder / 'compatScripts.json').write_text(json.dumps({
                    'version': 1, 'selectedRoot': owner,
                    'roots': [{'engine': 'Psych Engine', 'path': owner}],
                }), encoding='utf-8', newline='\n')
            (provenance_folder / 'importProvenance.json').write_text(json.dumps({
                'version': 1, 'sourceOwner': owner, 'sourceEngine': 'Psych Engine',
                'sourceFolder': 'spookeez', 'destinationFolder': provenance_folder.name,
            }), encoding='utf-8', newline='\n')
            for name in ('events.json', 'preload.json'):
                (live_folder / name).write_text('[]', encoding='utf-8', newline='\n')
            (runtime / 'assets/data/options.json').write_text('{"volume":0.75}', encoding='utf-8', newline='\n')

            foreign = runtime / 'assets/data/foreign-song'
            foreign.mkdir()
            foreign_chart = foreign / 'foreign-song.json'
            foreign_chart.write_text(json.dumps({'song': {
                'song': 'Foreign', 'stage': 'stage', 'notes': [], 'events': []}}),
                encoding='utf-8', newline='\n')
            foreign_original = foreign_chart.read_bytes()
            foreign_owner = 'assets/imported_mods/another-source'
            (foreign / 'compatScripts.json').write_text(json.dumps({
                'version': 1, 'selectedRoot': foreign_owner,
                'roots': [{'engine': 'Psych Engine', 'path': foreign_owner}],
            }), encoding='utf-8', newline='\n')
            options = runtime / 'assets/data/options.json'
            original_options = options.read_bytes()

            old_tmp = refresh.TMP
            refresh.TMP = root / 'maintenance'
            refresh.TMP.mkdir()
            try:
                plan = refresh.make_plan(donor, runtime)
                self.assertEqual(plan['selectedRoot'], owner)
                self.assertEqual(
                    {row['chart'] for row in plan['charts']},
                    {
                        'assets/data/spookeez/spookeez-easy.json',
                        f'assets/data/{qualified_name}/{qualified_name}-spookeez-easy.json',
                        f'assets/data/{provenance_folder.name}/'
                        f'{provenance_folder.name}-spookeez-easy.json',
                    })
                self.assertTrue(all(row['newStage'] == 'spooky' for row in plan['charts']))
                self.assertTrue(any(
                    row.get('chart') == 'assets/data/spookeez/spookeez-mismatch.json'
                    and row['reason'] == 'donor notes/events differ from installed chart; source match is ambiguous'
                    for row in plan['skipped']))
                self.assertFalse(any(
                    row.get('chart', '').endswith(('/events.json', '/preload.json',
                                                   '/importProvenance.json'))
                    for row in plan['skipped']))

                reviewed = dict(plan, status='planned')
                receipt_path = root / 'applied-receipt.json'
                receipt = refresh.apply_plan(reviewed, receipt_path)
                self.assertEqual(receipt['status'], 'applied')
                self.assertEqual(receipt['changed'], 3)
                self.assertTrue(Path(receipt['backup']).is_dir())
                self.assertEqual((Path(receipt['backup']) /
                                  'assets/data/spookeez/spookeez-easy.json').read_bytes(),
                                 original_bytes['spookeez-easy.json'])
                self.assertEqual(
                    (Path(receipt['backup']) / qualified_chart.relative_to(runtime)).read_bytes(),
                    json.dumps(installed['spookeez-easy.json']).encode())
                self.assertEqual(
                    (Path(receipt['backup']) / provenance_chart.relative_to(runtime)).read_bytes(),
                    json.dumps(installed['spookeez-easy.json']).encode())

                changed_path = live_folder / 'spookeez-easy.json'
                changed_bytes = changed_path.read_bytes()
                self.assertEqual(changed_bytes, refresh.replace_stage(
                    original_bytes['spookeez-easy.json'].decode(), 'spooky').encode())
                changed = json.loads(changed_bytes)['song']
                self.assertEqual(changed['stage'], 'spooky')
                self.assertEqual(changed['notes'], installed['spookeez-easy.json']['song']['notes'])
                self.assertEqual(changed['events'], installed['spookeez-easy.json']['song']['events'])
                self.assertEqual(changed['nativeSettings'], {'keep': [True, 5]})
                for name in ('spookeez-hard.json', 'spookeez.json',
                             'spookeez-mismatch.json'):
                    self.assertEqual((live_folder / name).read_bytes(), original_bytes[name])
                self.assertEqual(json.loads(qualified_chart.read_text())['song']['stage'], 'spooky')
                self.assertEqual(json.loads(provenance_chart.read_text())['song']['stage'], 'spooky')
                self.assertEqual(foreign_chart.read_bytes(), foreign_original)
                self.assertEqual(options.read_bytes(), original_options)
                self.assertEqual((source_folder / 'spookeez-easy.json').read_text(encoding='utf-8'),
                                 json.dumps(source_charts['spookeez-easy.json']))
            finally:
                refresh.TMP = old_tmp


if __name__ == '__main__':
    unittest.main()
