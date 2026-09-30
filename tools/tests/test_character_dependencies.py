"""Importer reports missing characters, not merely missing copy candidates."""
import json
from pathlib import Path
import tempfile
import unittest
from tools.character_dependencies import audit_characters, character_problems


class CharacterDependenciesTest(unittest.TestCase):
    def test_registry_folder_and_implementation_are_all_required(self):
        with tempfile.TemporaryDirectory() as directory:
            assets = Path(directory)
            folder = assets / 'images/custom_chars'
            (folder / 'hero').mkdir(parents=True)
            registry = {'hero': {'like': 'shared'}}
            self.assertEqual(character_problems(assets, registry, 'hero'), ['missing animation implementation'])
            (folder / 'shared.hscript').write_text('function init(char) {}')
            self.assertEqual(character_problems(assets, registry, 'hero'), [])
            self.assertIn('missing character folder', character_problems(assets, {'icon': {'like': 'shared'}}, 'icon'))
            (folder / 'shared').mkdir()
            self.assertEqual(character_problems(assets, {'alias': {'like': 'shared'}}, 'alias'), [])
            self.assertIn('missing registry entry', character_problems(assets, {}, 'hero'))

    def test_donor_gaps_distinct_from_recoverable_omissions(self):
        with tempfile.TemporaryDirectory() as directory:
            target, donor = Path(directory) / 'target', Path(directory) / 'donor'
            for root in (target, donor):
                folder = root / 'images/custom_chars'
                folder.mkdir(parents=True)
                (folder / 'custom_chars.jsonc').write_text(json.dumps({'hero': {'like': 'hero'}}))
            (donor / 'images/custom_chars/hero').mkdir()
            (donor / 'images/custom_chars/hero.hscript').write_text('function init(char) {}')
            charts = target / 'data/song'
            charts.mkdir(parents=True)
            (charts / 'song-hard.json').write_text(json.dumps({'song': {'notes': [], 'player1': 'hero', 'player2': 'absent'}}))
            result = {item['character']: item for item in audit_characters(target, donor)}
            self.assertEqual(result['hero']['donor_problems'], [])
            self.assertTrue(result['absent']['donor_problems'])
            self.assertEqual(result['hero']['references'], [{'chart': 'data/song/song-hard.json', 'role': 'player1'}])


if __name__ == '__main__':
    unittest.main()
