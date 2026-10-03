import importlib.util
import json
from pathlib import Path
from haxe_test_support import FixturePath as Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('repair', ROOT / 'tools/repair_imported_assets.py')
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


class ImportedNotesTest(unittest.TestCase):
    def test_note_definitions_import_with_exact_runtime_case(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / 'source', Path(folder) / 'target'
            original = source / 'data/Smoked/noteinfo.json'
            original.parent.mkdir(parents=True)
            original.write_text('[{}]', newline='\n')
            destination = target / 'data/smoked/noteInfo.json'
            destination.parent.mkdir(parents=True)
            self.assertEqual(list(repair.missing_assets(source, target)), [(original, destination)])
            destination.write_text('[{"id":"edited"}]', newline='\n')
            self.assertEqual(list(repair.missing_assets(source, target)), [])
            self.assertEqual(json.loads(destination.read_text()), [{'id': 'edited'}])

    def test_scripts_and_definitions_restore_without_overwriting_charts(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / 'source', Path(folder) / 'target'
            (target / 'data/song').mkdir(parents=True)
            for name, text in {
                'images/custom_ui/ui_layouts/postal.hscript': 'function start(song) {}',
                'images/custom_chars/char.json': '{"animations":[]}',
                'data/Song/events.json': '[]',
                'data/Song/song-hard.json': '{"song":{"notes":[]}}',
                'data/global.hscript': 'old global configuration',
            }.items():
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, newline='\n')
            destinations = {str(d.relative_to(target)) for _, d in repair.missing_assets(source, target)}
            self.assertEqual(destinations, {'images/custom_ui/ui_layouts/postal.hscript',
                                           'images/custom_chars/char.json', 'data/song/events.json'})

    def test_smoked_custom_slots_keep_glitch_appearance_and_hazard_behavior(self):
        chart_fixture = ROOT / 'assets/data/smoked/smoked-hard.json'
        definitions_fixture = ROOT / 'assets/data/smoked/noteInfo.json'
        if not chart_fixture.is_file() or not definitions_fixture.is_file():
            self.skipTest(f'mounted Smoked chart fixtures unavailable: {chart_fixture}, {definitions_fixture}')
        chart = json.loads(chart_fixture.read_text())['song']
        definitions = json.loads(definitions_fixture.read_text())
        custom = [n for sec in chart['notes'] for n in sec['sectionNotes'] if n[1] >= 40]
        self.assertEqual(len(custom), 136)
        self.assertEqual({n[1] // 8 - 5 for n in custom}, {0, 1})
        for note in custom:
            definition = definitions[note[1] // 8 - 5]
            self.assertEqual(definition['id'], 'glitch')
            self.assertTrue(definition['consistentHealth'])
            self.assertEqual(definition['healCutoff'], 'miss')
            self.assertLess(definition['healAmount'], 0)
            self.assertEqual(definition['damageAmount'], 0)
            self.assertTrue(definition['dontCountNote'])
            self.assertTrue(definition['dontStrum'])
            self.assertFalse(definition['shouldSing'])
            self.assertTrue(definition['aiShouldHit'])
            atlas = ROOT / (definition['customNotePath'] + '.xml')
            self.assertTrue((ROOT / (definition['customNotePath'] + '.png')).is_file())
            frames = [frame.attrib['name'] for frame in ET.fromstring(atlas.read_text())]
            prefix = definition['animNames'][note[1] % 4] + '0'
            self.assertTrue(any(frame.startswith(prefix) for frame in frames))


if __name__ == '__main__':
    unittest.main()
