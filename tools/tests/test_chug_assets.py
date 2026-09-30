"""Chug's difficulty charts must use its installed Miku character."""
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


class ChugAssetsTest(unittest.TestCase):
    def setUp(self):
        chart = ROOT / 'assets/data/chug/chug.json'
        character = ROOT / 'assets/images/custom_chars/mikuv2/char.xml'
        registry = ROOT / 'assets/images/custom_chars/custom_chars.jsonc'
        script = ROOT / 'assets/images/custom_chars/miku.hscript'
        if not all(path.is_file() for path in (chart, character, registry, script)):
            self.skipTest(f'mounted Chug/Mikuv2 fixtures unavailable: {chart}, {character}')
        if '"mikuv2"' not in registry.read_text():
            self.skipTest(f'mounted Mikuv2 registry entry unavailable: {registry}')

    def test_all_difficulties_use_installed_miku(self):
        folder = ROOT / 'assets/data/chug'
        normal = json.loads((folder / 'chug.json').read_text())['song']
        self.assertEqual(normal['player2'], 'mikuv2')
        for name in ['chug.json', 'chug-easy.json', 'chug-hard.json']:
            with self.subTest(chart=name):
                song = json.loads((folder / name).read_text())['song']
                self.assertEqual(song['player2'], normal['player2'])
                character = ROOT / 'assets/images/custom_chars' / song['player2']
                for asset in ['char.png', 'char.xml', 'icons.png']:
                    self.assertTrue((character / asset).is_file(), str(character / asset))

    def test_mikuv2_has_matching_animation_script(self):
        registry = json.loads((ROOT / 'assets/images/custom_chars/custom_chars.jsonc').read_text())
        self.assertEqual(registry['mikuv2']['like'], 'miku')
        script = (ROOT / 'assets/images/custom_chars/miku.hscript').read_text()
        atlas = ET.parse(ROOT / 'assets/images/custom_chars/mikuv2/char.xml')
        names = [frame.attrib['name'] for frame in atlas.getroot()]
        for prefix in ['Miku idle dance', 'Miku Sing Note UP', 'Miku Sing Note LEFT',
                       'Miku Sing Note RIGHT', 'Miku Sing Note DOWN']:
            self.assertIn(prefix, script)
            self.assertTrue(any(name.startswith(prefix) for name in names), prefix)


if __name__ == '__main__':
    unittest.main()
