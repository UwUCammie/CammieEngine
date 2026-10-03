"""Owner and payload gates for backed-up Psych girlfriend metadata refresh."""

import json
from pathlib import Path
from haxe_test_support import FixturePath as Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import refresh_psych_girlfriend_fields as refresh


class RefreshPsychGirlfriendFieldsTest(unittest.TestCase):
    def test_preview_owned_gf_field_refresh_and_backup(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as scratch:
            root = Path(scratch)
            source, preview, runtime = (root / name for name in ('source', 'tmp/preview', 'runtime'))
            owner = 'assets/imported_mods/psych-fixture'
            (root / 'assets/data').mkdir(parents=True)
            (root / 'assets/data/options.json').write_text('{}', newline='\n')
            (runtime / 'assets/data').mkdir(parents=True)
            (runtime / 'assets/data/options.json').write_text('{}', newline='\n')
            rows = []
            for stem, source_gf, preview_gf in (
                    ('normal', 'gf_JUICY', 'gf_JUICY'), ('easy', None, None)):
                relative = f'assets/data/example/example-{stem}.json'
                rows.append({'package': 'fixture', 'runtimeChart': relative})
                authored = {'song': 'Example', 'notes': [{'sectionNotes': []}],
                            'events': [], 'stage': 'authored-stage'}
                if source_gf is not None:
                    authored['gfVersion'] = source_gf
                fresh = dict(authored)
                if preview_gf is not None:
                    fresh['gf'] = preview_gf
                live = dict(authored, gf='gf')
                for target_root, payload in ((source, authored), (preview, fresh), (runtime, live)):
                    path = target_root / (f'data/example/example-{stem}.json' if target_root == source else relative)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps({'song': payload}), newline='\n')
                    if target_root != source:
                        (path.parent / 'compatScripts.json').write_text(json.dumps({'selectedRoot': owner}), newline='\n')
            matrix = root / 'matrix.json'
            matrix.write_text(json.dumps({'rows': rows}), newline='\n')
            with patch.object(refresh, 'ROOT', root), patch.object(refresh, 'TMP', root / 'tmp'):
                planned = refresh.plan(source, preview, runtime, owner, matrix, 'fixture')
                self.assertEqual(sum(row['changed'] for row in planned['charts']), 2)
                receipt = refresh.apply(planned, root / 'receipt.json')
                self.assertEqual(receipt['changed'], 2)
                self.assertTrue(Path(receipt['backup']).is_dir())
                normal = refresh.chart(runtime / rows[0]['runtimeChart'])['song']
                easy = refresh.chart(runtime / rows[1]['runtimeChart'])['song']
                self.assertEqual(normal['gf'], 'gf_JUICY')
                self.assertNotIn('gf', easy)
                self.assertEqual(normal['notes'], [{'sectionNotes': []}])
                self.assertTrue(receipt['optionsUnchanged'])
                (runtime / 'assets/data/example/compatScripts.json').write_text(
                    json.dumps({'selectedRoot': 'assets/imported_mods/other'}), newline='\n')
                with self.assertRaisesRegex(ValueError, 'selected owner mismatch'):
                    refresh.plan(source, preview, runtime, owner, matrix, 'fixture')
                (runtime / 'assets/data/example/compatScripts.json').write_text(
                    json.dumps({'selectedRoot': owner}), newline='\n')
                wrong = refresh.chart(preview / rows[0]['runtimeChart'])
                wrong['song']['stage'] = 'another-stage'
                (preview / rows[0]['runtimeChart']).write_text(json.dumps(wrong), newline='\n')
                with self.assertRaisesRegex(ValueError, 'source actor or stage metadata differs'):
                    refresh.plan(source, preview, runtime, owner, matrix, 'fixture')


if __name__ == '__main__':
    unittest.main()
