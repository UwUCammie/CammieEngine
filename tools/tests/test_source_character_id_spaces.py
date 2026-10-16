"""Psych character ids are file names, so ids with spaces keep their authored metadata."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / 'tmp'
TMP.mkdir(exist_ok=True)

PROBE = r'''
import sys.io.File;
class Probe {
  static function check(ok:Bool, label:String):Void if (!ok) throw label;
  static function eq(actual:Array<Float>, x:Float, y:Float, label:String):Void
    if (actual == null || actual.length < 2 || actual[0] != x || actual[1] != y)
      throw label + ': ' + actual;
  static function main():Void {
    check(SourceCharacterId.isFileName('bf fnia'), 'a space is part of a Psych file name');
    check(SourceCharacterId.isFileName('Bf-pixel_2.old (alt)'), 'dots and brackets are file name text');
    for (bad in [null, '', ' bf', 'bf ', '../bf', 'a/b', 'a\\b', 'c:bf', 'a*b', 'a?b', 'a"b', 'a<b', 'a>b', 'a|b',
        'bf' + String.fromCharCode(0), 'bf' + String.fromCharCode(10)])
      check(!SourceCharacterId.isFileName(bad), 'refused id was accepted: ' + bad);
    // Every id the previous strict pattern accepted must still be accepted.
    var old = new EReg('^[A-Za-z0-9_-]+$', '');
    var alphabet = ['a', 'Z', '0', '_', '-'];
    var samples = [''];
    for (round in 0...3)
      for (prefix in samples.copy())
        for (letter in alphabet)
          samples.push(prefix + letter);
    for (sample in samples)
      if (old.match(sample))
        check(SourceCharacterId.isFileName(sample), 'previously accepted id was refused: ' + sample);
    var readText = function(path:String):Null<String>
      return sys.FileSystem.exists(path) ? File.getContent(path) : null;
    eq(PsychCharacterPosition.resolve('bf fnia', 'scope'), 0, 350, 'spaced id position');
    eq(PsychCharacterPosition.characterCameraPosition('bf fnia', 'scope'), 4, -6, 'spaced id camera position');
    check(PsychCharacterOrientation.authoredFlipX('bf fnia', 'scope', readText) == true, 'spaced id flip_x');
    check(SourceCharacterDefinition.read('bf fnia', 'scope', readText) != null, 'spaced id definition');
    check(PsychCharacterHealthIcon.authored('bf fnia', 'scope', readText) == 'bffnia', 'spaced id icon');
    // A character kept in a dependency root of the same import supplies its own JSON.
    var present = ['dep/characters/bf fnia.json', 'owner/shared/characters/shared one.json', 'owner/characters/both.json',
      'dep/characters/both.json'];
    var exists = function(path:String):Bool return present.indexOf(path) >= 0;
    var roots = ['owner', 'dep'];
    check(SourceCharacterId.ownerRoot('bf fnia', roots, exists) == 'dep', 'dependency root holds the spaced id');
    check(SourceCharacterId.ownerRoot(' bf fnia ', roots, exists) == 'dep', 'the id is trimmed like the callers do');
    check(SourceCharacterId.ownerRoot('shared one', roots, exists) == 'owner', 'shared/characters counts');
    check(SourceCharacterId.ownerRoot('both', roots, exists) == 'owner', 'the selected owner wins a tie');
    check(SourceCharacterId.ownerRoot('missing one', roots, exists) == 'owner', 'no holder keeps the selected owner');
    check(SourceCharacterId.ownerRoot('../both', roots, exists) == 'owner', 'an unsafe id never searches');
    check(SourceCharacterId.ownerRoot('bf fnia', [], exists) == '', 'no roots, no owner');
    check(SourceCharacterId.ownerRoot('bf fnia', null, exists) == '', 'null roots, no owner');
    eq(PsychCharacterPosition.resolve('../bf fnia', 'scope'), 0, 0, 'unsafe id stays neutral');
    check(PsychCharacterOrientation.authoredFlipX('../bf fnia', 'scope', readText) == null, 'unsafe id flip');
    check(SourceCharacterDefinition.read('../bf fnia', 'scope', readText) == null, 'unsafe id definition');
  }
}
'''


class SourceCharacterIdSpacesTest(unittest.TestCase):
    def test_spaced_character_id_reads_every_authored_field(self):
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            work = Path(folder)
            for name in ('SourceCharacterId.hx', 'SourceCameraFollowPointMath.hx', 'PsychCharacterPosition.hx',
                         'PsychCharacterOrientation.hx', 'SourceCharacterDefinition.hx',
                         'PsychCharacterHealthIcon.hx'):
                (work / name).write_text((ROOT / 'source' / name).read_text(encoding='utf-8'), newline='\n')
            (work / 'scope/characters').mkdir(parents=True)
            (work / 'scope/characters/bf fnia.json').write_text(
                '{"position":[0,350],"camera_position":[4,-6],"flip_x":true,"healthicon":"bffnia","animations":[]}',
                newline='\n')
            (work / 'FNFAssets.hx').write_text('''
class FNFAssets {
  public static function exists(path:String):Bool return sys.FileSystem.exists(path);
  public static function getText(path:String):String return sys.io.File.getContent(path);
}
''', newline='\n')
            (work / 'CoolUtil.hx').write_text('''
class CoolUtil {
  public static function parseJson(source:String):Dynamic return haxe.Json.parse(source);
}
''', newline='\n')
            (work / 'Probe.hx').write_text(PROBE, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(work), '--run', 'Probe'],
                cwd=work, env={**os.environ, 'TMPDIR': str(TMP)}, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_runtime_callers_use_the_shared_id_check(self):
        for name in ('Character.hx', 'PsychCharacterPosition.hx', 'PsychCharacterOrientation.hx',
                     'SourceCharacterDefinition.hx', 'PsychCharacterHealthIcon.hx'):
            source = (ROOT / 'source' / name).read_text(encoding='utf-8')
            self.assertIn('SourceCharacterId.isFileName(', source, name)
            self.assertNotIn('A-Za-z0-9_-]+$/.match(name)', source, name)

    def test_gameplay_looks_for_the_character_in_every_root_of_the_import(self):
        character = (ROOT / 'source' / 'Character.hx').read_text(encoding='utf-8')
        self.assertIn('SourceCharacterId.ownerRoot(visualCharacterId, Song.currentPsychCharacterOwnerRoots()', character)
        play = (ROOT / 'source' / 'PlayState.hx').read_text(encoding='utf-8')
        self.assertIn('[psychStageCharacterRoot].concat(Song.currentPsychCharacterOwnerRoots())', play)
        song = (ROOT / 'source' / 'Song.hx').read_text(encoding='utf-8')
        self.assertIn('public static function psychCharacterOwnerRootsForSong(', song)


if __name__ == '__main__':
    unittest.main()
