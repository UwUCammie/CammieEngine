"""A replacement actor inherits the stage role depth without retaining the old actor."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for position in range(opening, len(source)):
        if source[position] == "{":
            depth += 1
        elif source[position] == "}":
            depth -= 1
            if depth == 0:
                return source[start : position + 1]
    raise AssertionError(marker)


class StageCharacterZRebindTest(unittest.TestCase):
    def test_replacement_preserves_role_depth_and_cleans_old_actor(self):
        source = (ROOT / "source/StageHelper.hx").read_text()
        method = extract_method(source, "\tpublic function rebindCharacterZ(")
        fixture = """
class FlxSprite {
  public function new() {}
}
class Character extends FlxSprite {
  public function new() { super(); }
}
class RoleInfo {
  public var zIndex:Int;
  public function new(zIndex:Int) this.zIndex = zIndex;
}
class StageHelper {
  public var zIndexes:Map<FlxSprite, Int> = [];
  public var presentedCharacters:Map<Character, String> = [];
  var dadInfo = new RoleInfo(210);
  var bfInfo = new RoleInfo(-69);
  public function new() {}
  public function getInfo(role:String):RoleInfo return switch (role) {
    case 'dad': dadInfo;
    case 'boyfriend' | 'bf': bfInfo;
    default: null;
  }
  public function setZIndex(sprite:Dynamic, depth:Int):Void zIndexes.set(cast sprite, depth);
""" + method + """
}
class Main {
  static function main() {
    var stage = new StageHelper();
    var oldDad = new Character();
    var newDad = new Character();
    stage.zIndexes.set(oldDad, 210);
    stage.presentedCharacters.set(oldDad, 'dad');
    stage.rebindCharacterZ('dad', oldDad, newDad);
    if (stage.zIndexes.exists(oldDad) || stage.zIndexes.get(newDad) != 210)
      throw 'authored role depth did not move to replacement';
    if (stage.presentedCharacters.exists(oldDad)) throw 'outgoing actor retained by stage';
    var oldBf = new FlxSprite();
    var newBf = new FlxSprite();
    stage.zIndexes.set(oldBf, 42);
    stage.rebindCharacterZ('boyfriend', oldBf, newBf);
    if (stage.zIndexes.exists(oldBf) || stage.zIndexes.exists(newBf))
      throw 'unset role depth should not invent an actor depth';
    stage.rebindCharacterZ('unknown', null, new FlxSprite());
    if (stage.zIndexes.keys().hasNext() != true)
      throw 'known actor depth disappeared';
  }
}
"""
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(fixture, newline='\n')
            env = os.environ.copy()
            env["TMPDIR"] = folder
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
