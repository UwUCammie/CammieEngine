"""Psych health-bar colours stay active after native bar refreshes."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


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


class PsychHealthBarColorsTest(unittest.TestCase):
    def test_authored_colours_survive_native_refresh_and_are_song_scoped(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        methods = "\n".join(extract_method(source, marker) for marker in (
            "function compatParseColor(",
            "function compatSetHealthBarColors(",
            "function updateHealthColors(",
        ))
        fixture = r'''
class FlxColor {
  public static function fromString(value:String):Null<Int> return null;
}
class OptionsHandler {
  public static var options = {useCharColor: false};
}
class FakeBar {
  public var left:Int = 0;
  public var right:Int = 0;
  public function new() {}
  public function createFilledBar(left:Int, right:Int):Void {
    this.left = left;
    this.right = right;
  }
  public function updateBar():Void {}
}
class PsychHealthBarFixture {
  var nightmareVisionScripts:Dynamic = null;
  var compatHealthBarLeft:Null<Int> = null;
  var compatHealthBarRight:Null<Int> = null;
  var barShowingPoison:Bool = false;
  var healthBar:FakeBar = new FakeBar();
  var dad:Dynamic = {enemyColor: 1, opponentColor: 2, poisonColorEnemy: 3};
  var boyfriend:Dynamic = {bfColor: 4, playerColor: 5, poisonColor: 6};
  var iconP1:Dynamic = {healthColors: [7]};
  var iconP2:Dynamic = {healthColors: [8]};
  var opponentPlayer:Bool = false;
  var duoMode:Bool = false;
  public function new() {}
__METHODS__
  static function main():Void {
    var first = new PsychHealthBarFixture();
    first.compatSetHealthBarColors('FF0000', 'FDFC01');
    if (first.healthBar.left != 0xFFFF0000 || first.healthBar.right != 0xFFFDFC01)
      throw 'authored bare-hex colours did not apply';
    first.updateHealthColors();
    if (first.healthBar.left != 0xFFFF0000 || first.healthBar.right != 0xFFFDFC01)
      throw 'native refresh erased authored colours';
    first.updateHealthColors(true);
    if (first.healthBar.right != 6)
      throw 'poison colour did not temporarily override the authored fill';
    first.updateHealthColors();
    if (first.healthBar.right != 0xFFFDFC01)
      throw 'authored fill did not return after poison';
    first.compatSetHealthBarColors('', '');
    if (first.healthBar.left != 1 || first.healthBar.right != 5)
      throw 'empty Psych colors did not restore native defaults';
    var second = new PsychHealthBarFixture();
    second.updateHealthColors();
    if (second.healthBar.left != 1 || second.healthBar.right != 5)
      throw 'colours leaked into another PlayState instance';
  }
}
'''.replace("__METHODS__", methods)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "PsychHealthBarFixture.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "PsychHealthBarFixture", "--interp"],
                cwd=ROOT, env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
