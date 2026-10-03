"""Verify the generic Character Animate self-alias used by NMV scripts."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HAXESCRIPT = ROOT / ".haxelib/hscript/2,5,0"


def function_body(source, name):
    marker = "function " + name + "("
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    quote = None
    escaped = False
    index = opening
    while index < len(source):
        char = source[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in ('"', "'"):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
        index += 1
    raise AssertionError("unterminated function " + name)


class NightmareVisionAnimateAliasTest(unittest.TestCase):
    def test_character_animate_atlas_self_alias_is_script_accessible(self):
        if not HAXE.is_file() or not HAXESCRIPT.is_dir():
            self.skipTest("portable Haxe interpreter or HScript library is unavailable")

        source = (ROOT / "source/DisSprite.hx").read_text()
        field = "@:keep public var animateAtlas:FlxAnimate;"
        self.assertIn(field, source)
        constructor = function_body(source, "new").replace("function new(", "public function new(", 1)
        fixture = '''
class FlxAnimate {
 public var useRenderTexture:Bool=false;
 public function new(?x:Float=0,?y:Float=0) {}
}
class DisSprite extends FlxAnimate {
''' + field + "\n" + constructor + '''
}
class Main {
 static function main():Void {
  var actor:Dynamic = new DisSprite();
  var interp = new hscript.Interp();
  interp.variables.set('boyfriend', actor);
  interp.execute(new hscript.Parser().parseString(
   'boyfriend.animateAtlas.useRenderTexture = true;'));
  if (actor.animateAtlas != actor || !actor.useRenderTexture)
   throw 'Character animateAtlas did not forward to its FlxAnimate instance';
  Sys.println('nightmare-vision-animate-alias-ok');
 }
}
'''
        with tempfile.TemporaryDirectory(prefix="nmv-animate-alias-", dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "-cp", str(HAXESCRIPT), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("nightmare-vision-animate-alias-ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
