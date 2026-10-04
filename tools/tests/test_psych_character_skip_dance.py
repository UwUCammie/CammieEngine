"""Psych-compatible dance suppression is a mutable Character runtime property."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for at in range(brace, len(source)):
        depth += (source[at] == "{") - (source[at] == "}")
        if depth == 0:
            return source[start:at + 1]
    raise AssertionError(f"unterminated method: {marker}")


class PsychCharacterSkipDanceTest(unittest.TestCase):
    def test_runtime_gate_is_shared_and_hscript_can_toggle_it(self):
        character_source = (ROOT / "source/Character.hx").read_text()
        module_source = (ROOT / "source/ModuleFunctions.hx").read_text()
        dance = extract_method(character_source, "public function dance(forced:Bool = false)")

        self.assertIn("public var skipDance:Bool = false;", character_source)
        self.assertLess(dance.index("if (skipDance) return;"),
                        dance.index('callInterp("dance", [this])'))
        self.assertIn("PsychCharacterDanceCompat.renderStandardScript(charJson", module_source)
        self.assertIn("PsychCharacterDanceCompat.renderAnimateDance(charJson)", module_source)

        fixture = '''import hscript.Parser;
import hscript.Interp;

class CodenameCharacterEvent {
  public var danced:Bool = false;
  public var cancelled:Bool = false;
  public function new() {}
}
class FakeRuntime {
  public function new() {}
  public function event(_name:String, _event:CodenameCharacterEvent):Void {}
}
class FakeAnimation {
  public var curAnim:Dynamic = null;
  public function new() {}
  public function exists(_name:String):Bool return false;
  public function getByName(_name:String):Dynamic return null;
}
class FlxColor { public static inline var WHITE:Int = 0xFFFFFFFF; }
class PlayState {
  public static var instance:PlayState = null;
  public function new() {}
  public function dispatchHxcCharacterMethod(_character:Character, _name:String,
    _args:Array<Dynamic>):Void {}
}
class Character {
  public var skipDance:Bool = false;
  public var nightmareVisionCharacterData:Dynamic = null;
  public var codenameLiveDefinition:Dynamic = null;
  var codenameVisualBuilding:Bool = false;
  public var codenameRuntime:FakeRuntime = new FakeRuntime();
  public var danced:Bool = false;
  public var animation:FakeAnimation = new FakeAnimation();
  public var idleSuffix:String = '';
  public var debugMode:Bool = false;
  public var specialAnim:Bool = false;
  public var beNormal:Bool = true;
  public var isDie:Bool = false;
  public var noDanceAnims:Array<String> = [];
  public var interp:Dynamic = true;
  public var color:Int = 0;
  public var renderer:String;
  public var danceCalls:Int = 0;
  public var plays:Array<String> = [];
  public var onScriptDance:String->Void;
  public function new(renderer:String) this.renderer = renderer;
  public function codenamePlayAnim(_name:String, ?force:Null<Bool>, ?context:Dynamic):Void {}
  public function callInterp(_name:String, _args:Array<Dynamic>):Void {
    danceCalls++;
    if (onScriptDance != null) onScriptDance(renderer);
  }
  public function playAnim(name:String, _force:Bool = false, _reversed:Bool = false,
    _frame:Int = 0):Void plays.push(name);
  function nightmareVisionNumber(_value:Dynamic, fallback:Float):Float return fallback;
  DANCE_METHOD
}
class Main {
  static function main() {
    var calls:Array<String> = [];
    var standard = new Character('standard');
    standard.onScriptDance = function(kind:String) calls.push(kind);
    var animate = new Character('animate');
    animate.onScriptDance = function(kind:String) calls.push(kind);

    // Both generated script kinds enter the same Character.dance() gate.
    standard.dance();
    animate.dance();
    if (calls.join(',') != 'standard,animate') throw 'false should allow both renderers';

    var stage = new Interp();
    stage.variables.set('char', standard);
    stage.execute(new Parser().parseString("char.skipDance = true; char.dance(); char.playAnim('singLEFT');"));
    if (standard.skipDance != true || standard.danceCalls != 1)
      throw 'true should suppress only the dance callback';
    if (standard.plays.join(',') != 'singLEFT')
      throw 'skipDance must leave explicit sing/playAnim intact';

    // A stage can resume the actor later; the next explicit or beat dance works.
    stage.execute(new Parser().parseString('char.skipDance = false; char.dance();'));
    if (standard.danceCalls != 2 || calls.join(',') != 'standard,animate,standard')
      throw 'false toggle should resume the same generated callback';

    stage.variables.set('char', animate);
    stage.execute(new Parser().parseString('char.skipDance = true; char.dance();'));
    if (animate.skipDance != true || animate.danceCalls != 1)
      throw 'Animate imports should use the same runtime gate';

    // A retired FlxSprite can remain in an owner callback list for one beat.
    // Its animation controller is already cleared by destroy().
    standard.animation = null;
    standard.dance();
    if (standard.danceCalls != 2)
      throw 'retired character must not run an idle script';
  }
}
'''.replace("DANCE_METHOD", dance)

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            (work / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"), "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
