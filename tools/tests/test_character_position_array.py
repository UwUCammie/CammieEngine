"""Character.positionArray retains authored source metadata without placement math."""
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


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index('{', start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(marker)


class CharacterPositionArrayTest(unittest.TestCase):
    def test_selected_psych_owner_returns_raw_authored_pair(self):
        character = (ROOT / 'source/Character.hx').read_text()
        method = extract_method(character, '\tstatic function psychCharacterPositionArray(')
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            work = Path(folder)
            (work / 'PsychCharacterPosition.hx').write_text(
                (ROOT / 'source/PsychCharacterPosition.hx').read_text(), newline='\n')
            (work / 'FNFAssets.hx').write_text('''
class FNFAssets {
  public static var files:Map<String, String> = new Map();
  public static function exists(path:String):Bool return files.exists(path);
  public static function getText(path:String):String return files.get(path);
}
''', newline='\n')
            (work / 'CoolUtil.hx').write_text('''
class CoolUtil {
  public static function parseJson(source:String):Dynamic return haxe.Json.parse(source);
}
''', newline='\n')
            (work / 'Probe.hx').write_text('''
class Probe {
''' + method + '''
  static function eq(actual:Array<Float>, x:Float, y:Float, label:String):Void {
    if (actual == null || actual.length != 2 || actual[0] != x || actual[1] != y)
      throw label + ': ' + actual;
  }
  static function main():Void {
    FNFAssets.files.set('owner/characters/bf.json', '{"position":[12.25,-5.75]}');
    FNFAssets.files.set('owner/shared/characters/bf.json', '{"position":[90,91]}');
    FNFAssets.files.set('owner/characters/gf.json', '{"position":"bad"}');
    FNFAssets.files.set('owner/shared/characters/gf.json', '{"position":[2.5,3.75]}');
    eq(psychCharacterPositionArray('bf', 'owner'), 12.25, -5.75,
      'selected characters folder must preserve authored float pair');
    eq(psychCharacterPositionArray('gf', 'owner'), 2.5, 3.75,
      'shared folder must supply a valid authored float pair');
    eq(psychCharacterPositionArray('missing', 'owner'), 0, 0,
      'missing source metadata must stay neutral');
    eq(psychCharacterPositionArray('../bf', 'owner'), 0, 0,
      'unsafe ids must not escape selected owner');
    eq(psychCharacterPositionArray('bf', ''), 0, 0,
      'unscoped native characters must stay neutral');
  }
}
''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(work), '-main', 'Probe', '--interp'],
                cwd=work, env={**os.environ, 'TMPDIR': str(TMP)}, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_psych_and_nightmare_vision_set_raw_alias_without_changing_offsets(self):
        source = (ROOT / 'source/Character.hx').read_text()
        self.assertIn('@:keep public var positionArray:Array<Float> = [0, 0];', source)
        self.assertIn('positionArray = psychCharacterPositionArray(curCharacter, psychCameraRoot);', source)
        self.assertIn('positionArray = [position[0], position[1]];', source)
        self.assertIn('enemyOffsetX = playerOffsetX = gfOffsetX = Std.int(Math.round(position[0]));', source)
        self.assertIn('enemyOffsetY = playerOffsetY = gfOffsetY = Std.int(Math.round(position[1]));', source)

        number = extract_method(source, '\tstatic function nightmareVisionNumber(')
        pair = extract_method(source, '\tstatic function nightmareVisionPair(')
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            work = Path(folder)
            (work / 'Probe.hx').write_text('''
class Probe {
''' + number + '\n' + pair + '''
  static function main():Void {
    var authored = nightmareVisionPair([12.25, -5.75]);
    var positionArray = [authored[0], authored[1]];
    if (positionArray[0] != 12.25 || positionArray[1] != -5.75)
      throw 'Nightmare Vision positionArray lost source float precision';
    if (Std.int(Math.round(authored[0])) != 12 || Std.int(Math.round(authored[1])) != -6)
      throw 'existing rounded native placement offsets changed';
  }
}
''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(work), '-main', 'Probe', '--interp'],
                cwd=work, env={**os.environ, 'TMPDIR': str(TMP)}, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
