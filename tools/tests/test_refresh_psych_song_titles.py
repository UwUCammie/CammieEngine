"""A Psych title refresh changes only owner-selected chart identity."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'refresh_psych_song_titles', ROOT / 'tools/refresh_psych_song_titles.py')
refresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(refresh)
OWNER = 'assets/imported_mods/psych-engine-fixture-1234'
CHART = 'assets/data/title-(hq)/title-(hq).json'


class PsychSongTitleRefreshTest(unittest.TestCase):
    def test_owner_scoped_title_only_refresh_and_backup(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            root = Path(folder)
            old_tmp = refresh.TMP
            refresh.TMP = root
            try:
                donor, preview, runtime = (root / name for name in ('donor', 'preview', 'runtime'))
                authored = {'song': {'song': 'Title (HQ)', 'notes': [
                    {'sectionNotes': [[1000, 1, 0]]}], 'events': []}}
                fresh = json.loads(json.dumps(authored))
                fresh['song']['compatPreserveSongTitle'] = True
                installed = json.loads(json.dumps(authored))
                installed['song']['song'] = 'title-(hq)'
                installed['song']['nativeField'] = {'keep': [1, False, None]}
                source_path = donor / 'data/title-(hq)/title-(hq).json'
                preview_path = preview / CHART
                live_path = runtime / CHART
                for path, data in ((source_path, authored), (preview_path, fresh),
                                   (live_path, installed)):
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps(data))
                for path in (preview_path, live_path):
                    (path.parent / 'compatScripts.json').write_text(
                        json.dumps({'selectedRoot': OWNER}))
                (runtime / 'assets/data/options.json').write_text('{}')
                matrix = root / 'matrix.json'
                matrix.write_text(json.dumps({'rows': [
                    {'package': 'fixture', 'runtimeChart': CHART}]}))
                planned = refresh.plan(donor, preview, runtime, OWNER, matrix, 'fixture')
                self.assertEqual(len(planned['charts']), 1)
                self.assertTrue(planned['charts'][0]['changed'])
                receipt = refresh.apply(planned, root / 'receipt.json')
                self.assertEqual(receipt['changed'], 1)
                changed = json.loads(live_path.read_text())
                self.assertEqual(changed['song']['song'], 'Title (HQ)')
                self.assertIs(changed['song']['compatPreserveSongTitle'], True)
                self.assertEqual(changed['song']['nativeField'], {'keep': [1, False, None]})
                saved = Path(receipt['backup']) / CHART
                self.assertEqual(json.loads(saved.read_text()), installed)
                self.assertEqual(json.loads(source_path.read_text()), authored)
                self.assertEqual(json.loads(preview_path.read_text()), fresh)
                with self.assertRaises(ValueError):
                    refresh.apply(planned, root / 'stale-receipt.json')
            finally:
                refresh.TMP = old_tmp

    def test_rejects_foreign_owner_and_different_notes(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            root = Path(folder)
            old_tmp = refresh.TMP
            refresh.TMP = root
            try:
                donor, preview, runtime = (root / name for name in ('donor', 'preview', 'runtime'))
                source = {'song': {'song': 'Title (HQ)', 'notes': [], 'events': []}}
                imported = {'song': {'song': 'Title (HQ)', 'notes': [], 'events': [],
                                     'compatPreserveSongTitle': True}}
                for target, data in ((donor / 'data/title-(hq)/title-(hq).json', source),
                                     (preview / CHART, imported), (runtime / CHART, imported)):
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(json.dumps(data))
                for target in (preview / CHART, runtime / CHART):
                    (target.parent / 'compatScripts.json').write_text(
                        json.dumps({'selectedRoot': OWNER}))
                (runtime / 'assets/data/options.json').write_text('{}')
                matrix = root / 'matrix.json'
                matrix.write_text(json.dumps({'rows': [
                    {'package': 'fixture', 'runtimeChart': CHART}]}))
                (runtime / CHART).parent.joinpath('compatScripts.json').write_text(
                    json.dumps({'selectedRoot': 'assets/imported_mods/foreign'}))
                with self.assertRaisesRegex(ValueError, 'owner mismatch'):
                    refresh.plan(donor, preview, runtime, OWNER, matrix, 'fixture')
                (runtime / CHART).parent.joinpath('compatScripts.json').write_text(
                    json.dumps({'selectedRoot': OWNER}))
                source['song']['notes'] = [{'sectionNotes': [[1000, 1, 0]]}]
                (donor / 'data/title-(hq)/title-(hq).json').write_text(json.dumps(source))
                with self.assertRaisesRegex(ValueError, 'notes or events differ'):
                    refresh.plan(donor, preview, runtime, OWNER, matrix, 'fixture')
            finally:
                refresh.TMP = old_tmp


if __name__ == '__main__':
    unittest.main()
