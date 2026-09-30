"""Round 24 character resolution: preserve Popipo ids and choose complete aliases."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.character_dependencies import read_json


ROOT = Path(__file__).resolve().parents[2]
DONOR = Path("/run/media/cammie/External Storage/modding-plus-fnf")


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class CharacterResolutionRound24Test(unittest.TestCase):
    def test_donor_popipo_normal_and_hard_keep_authored_ids(self):
        normal_path = DONOR / "assets/data/popipo/popipo.json"
        hard_path = DONOR / "assets/data/popipo/popipo-hard.json"
        registry_path = DONOR / "assets/images/custom_chars/custom_chars.jsonc"
        if not all(path.is_file() for path in (normal_path, hard_path, registry_path)):
            self.skipTest(f"mounted Popipo donor fixtures unavailable under {DONOR}")

        normal = json.loads(normal_path.read_text())['song']
        hard = json.loads(hard_path.read_text())['song']
        registry = read_json(registry_path)
        self.assertEqual(normal['player2'], 'mikuv2')
        self.assertEqual(hard['player2'], 'miku')
        self.assertEqual(registry['miku']['like'], 'dad')
        self.assertEqual(registry['mikuv2']['like'], 'miku')
        self.assertTrue((DONOR / 'assets/images/custom_chars/miku.hscript').is_file())
        self.assertFalse((DONOR / 'assets/images/custom_chars/miku').is_dir())
        self.assertTrue((DONOR / 'assets/images/custom_chars/mikuv2/char.png').is_file())

    def test_modding_plus_preload_role_suffixes_are_not_character_ids(self):
        preload = DONOR / 'assets/data/chaos/preload.txt'
        registry_path = DONOR / 'assets/images/custom_chars/custom_chars.jsonc'
        if not all(path.is_file() for path in (preload, registry_path)):
            self.skipTest(f'mounted Chaos donor fixtures unavailable under {DONOR}')
        entries = [line.strip() for line in preload.read_text().splitlines() if line.strip()]
        self.assertEqual(entries, [
            'fleetway-extras:dad', 'fleetway-extras2:dad', 'Fleetway:dad',
            'bf:bf', 'bf-ss:bf'
        ])
        registry = read_json(registry_path)
        keys = {str(key).lower() for key in registry}
        for authored in entries:
            character = authored.rsplit(':', 1)[0]
            self.assertIn(character.lower(), keys)
            self.assertTrue((DONOR / 'assets/images/custom_chars' / f'{character}.hscript').is_file())
            self.assertTrue((DONOR / 'assets/images/custom_chars' / character / 'char.png').is_file())
        self.assertFalse(any(path.name.lower().startswith('agoti-eye')
                             for path in (DONOR / 'assets/images/custom_chars').rglob('*')))

    def test_synthetic_resolver_selects_sibling_and_reports_missing_assets(self):
        source = (ROOT / 'source/Song.hx').read_text()
        registry_key = extract_method(source, '\tstatic function registryKey(')
        resolver = extract_method(source, '\tpublic static function resolveCharacterVisualFromData(')
        fixture = '''
using StringTools;
typedef CharacterVisualResolution = {
  var requested:String;
  var registryName:String;
  var selectedRegistryName:String;
  var likeName:String;
  var implementationName:String;
  var assetName:String;
  var implementationPath:String;
  var assetPath:String;
  var assetRootPath:String;
  var complete:Bool;
  var diagnosticCode:String;
  var diagnostic:String;
}
class Song {
''' + registry_key + '\n' + resolver + '''
  static function main() {
    var available = new Map<String, Bool>();
    for (path in [
      'assets/images/custom_chars/miku.hscript',
      'assets/images/custom_chars/mikuv2/char.png',
      'assets/images/custom_chars/dad.hscript',
      'assets/images/custom_chars/dad/char.png'
    ]) available.set(path, true);
    var registry:Dynamic = {
      miku: {like: 'dad'}, mikuv2: {like: 'miku'}, dad: {like: 'dad'},
      broken: {like: 'missing'}
    };
    var result = resolveCharacterVisualFromData('miku', registry,
      function(path:String):Bool return available.exists(path));
    if (!result.complete || result.requested != 'miku'
      || result.selectedRegistryName != 'mikuv2'
      || result.implementationName != 'miku'
      || result.assetName != 'mikuv2')
      throw 'miku did not select complete sibling visual';
    var folded = resolveCharacterVisualFromData('MIKU', registry,
      function(path:String):Bool return available.exists(path));
    if (!folded.complete || folded.requested != 'MIKU'
      || folded.selectedRegistryName != 'mikuv2')
      throw 'case-insensitive registry resolution lost authored id';
    var alias = resolveCharacterVisualFromData('alias',
      {alias: {like: 'dad'}, dad: {like: 'dad'}},
      function(path:String):Bool return path == 'assets/images/custom_chars/dad.hscript'
        || path == 'assets/images/custom_chars/dad/char.png');
    if (!alias.complete || alias.selectedRegistryName != 'alias'
      || alias.implementationName != 'dad' || alias.assetName != 'dad')
      throw 'shared alias did not use base implementation';
    var missing = resolveCharacterVisualFromData('broken', registry,
      function(path:String):Bool return available.exists(path));
    if (missing.complete || missing.diagnosticCode != 'character-implementation-missing'
      || missing.diagnostic.indexOf('missing animation implementation') < 0)
      throw 'missing implementation diagnostic was not precise';

    for (path in [
      'assets/images/custom_chars/fleetway-extras.hscript',
      'assets/images/custom_chars/fleetway-extras/char.png',
      'assets/images/custom_chars/fleetway-extras2.hscript',
      'assets/images/custom_chars/fleetway-extras2/char.png',
      'assets/images/custom_chars/Fleetway.hscript',
      'assets/images/custom_chars/Fleetway/char.png',
      'assets/images/custom_chars/bf.hscript',
      'assets/images/custom_chars/bf/char.png',
      'assets/images/custom_chars/bf-ss.hscript',
      'assets/images/custom_chars/bf-ss/char.png'
    ]) available.set(path, true);
    var colonRegistry:Dynamic = {
      'fleetway-extras': {like: 'fleetway-extras'},
      'fleetway-extras2': {like: 'fleetway-extras2'},
      'Fleetway': {like: 'Fleetway'},
      'bf': {like: 'bf'},
      'bf-ss': {like: 'bf-ss'}
    };
    var scoped = resolveCharacterVisualFromData('fleetway-extras:dad', colonRegistry,
      function(path:String):Bool return available.exists(path));
    if (!scoped.complete || scoped.requested != 'fleetway-extras:dad'
      || scoped.selectedRegistryName != 'fleetway-extras'
      || scoped.implementationName != 'fleetway-extras')
      throw 'Modding Plus character:role id did not resolve its character portion';
    var scoped2 = resolveCharacterVisualFromData('fleetway-extras2:dad', colonRegistry,
      function(path:String):Bool return available.exists(path));
    var scoped3 = resolveCharacterVisualFromData('Fleetway:dad', colonRegistry,
      function(path:String):Bool return available.exists(path));
    var scoped4 = resolveCharacterVisualFromData('bf:bf', colonRegistry,
      function(path:String):Bool return available.exists(path));
    var scoped5 = resolveCharacterVisualFromData('bf-ss:bf', colonRegistry,
      function(path:String):Bool return available.exists(path));
    if (!scoped2.complete || !scoped3.complete || !scoped4.complete || !scoped5.complete
      || scoped2.selectedRegistryName != 'fleetway-extras2'
      || scoped3.selectedRegistryName != 'Fleetway'
      || scoped4.selectedRegistryName != 'bf'
      || scoped5.selectedRegistryName != 'bf-ss')
      throw 'one or more Modding Plus character:role ids did not resolve';
    var incomplete = resolveCharacterVisualFromData('miku', registry,
      function(path:String):Bool return path == 'assets/images/custom_chars/miku.hscript');
    if (incomplete.complete || incomplete.diagnosticCode != 'character-asset-missing')
      throw 'missing named asset did not stay incomplete';
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            path = Path(folder) / 'Song.hx'
            path.write_text(fixture)
            env = os.environ.copy()
            env['TMPDIR'] = str(ROOT / 'tmp')
            result = subprocess.run(
                [str(ROOT / '.tools/haxe/haxe'), '-cp', folder, '-main', 'Song', '--interp'],
                cwd=ROOT, env=env, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_character_keeps_authored_id_and_reports_resolution(self):
        character = (ROOT / 'source/Character.hx').read_text()
        constructor = character[character.index('\tpublic function new('):character.index('\n\tpublic static function characterExists(')]
        self.assertIn('Song.resolveCharacterVisualForCurrentSong(curCharacter)', constructor)
        self.assertNotIn("curCharacter = 'dad'", constructor)
        self.assertIn('Character.reportResolution(visualResolution)', constructor)
        self.assertIn('!visualResolution.complete && !isDie && codenameLiveDefinition == null', constructor)
        self.assertLess(constructor.index('codenameLiveDefinition = builtCodenameDefinition;'),
                        constructor.index('Character.reportResolution(visualResolution)'))
        self.assertIn('interp.variables.set("charName", requested);', character)

    def test_complete_legacy_character_can_be_loaded_without_registry_row(self):
        source = (ROOT / 'source/Song.hx').read_text()
        registry_key = extract_method(source, '\tstatic function registryKey(')
        resolver = extract_method(source, '\tpublic static function resolveCharacterVisualFromData(')
        fixture = '''
using StringTools;
typedef CharacterVisualResolution = {
  var requested:String;
  var registryName:String;
  var selectedRegistryName:String;
  var likeName:String;
  var implementationName:String;
  var assetName:String;
  var implementationPath:String;
  var assetPath:String;
  var assetRootPath:String;
  var complete:Bool;
  var diagnosticCode:String;
  var diagnostic:String;
}
class Song {
''' + registry_key + '\n' + resolver + '''
  static function main() {
    var registry:Dynamic = {dad: {like: 'dad'}};
    var result = resolveCharacterVisualFromData('Fleetway', registry,
      function(path:String):Bool {
        var key = path.toLowerCase();
        return key == 'assets/images/custom_chars/fleetway.hscript'
          || key == 'assets/images/custom_chars/fleetway/char.png'
          || key == 'assets/images/custom_chars/fleetway/char.xml';
      });
    if (!result.complete || result.selectedRegistryName != 'Fleetway')
      throw 'complete direct legacy character was not accepted beside registry';
    var direct = resolveCharacterVisualFromData('Fleetway', {},
      function(path:String):Bool {
        var key = path.toLowerCase();
        return key == 'assets/images/custom_chars/fleetway.hscript'
          || key == 'assets/images/custom_chars/fleetway/char.png';
      });
    if (!direct.complete || direct.selectedRegistryName != 'Fleetway'
      || direct.implementationName != 'Fleetway' || direct.assetName != 'Fleetway')
      throw 'complete direct legacy character was not accepted';
    var unsafe = resolveCharacterVisualFromData('../outside', {},
      function(path:String):Bool return true);
    if (unsafe.complete || unsafe.diagnosticCode != 'character-registry-entry-missing')
      throw 'unsafe character id bypassed direct resolver';
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            path = Path(folder) / 'Song.hx'
            path.write_text(fixture)
            env = os.environ.copy()
            env['TMPDIR'] = str(ROOT / 'tmp')
            result = subprocess.run(
                [str(ROOT / '.tools/haxe/haxe'), '-cp', folder,
                 '-main', 'Song', '--interp'],
                cwd=ROOT, env=env, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
