"""Executable Psych miss-animation and NV animation-timer field contracts."""

from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    quote = None
    escaped = False
    line_comment = False
    block_comment = False
    index = brace
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and following == "/":
                block_comment = False
                index += 1
        elif quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char == "/" and following == "/":
            line_comment = True
            index += 1
        elif char == "/" and following == "*":
            block_comment = True
            index += 1
        elif char in ("'", '"'):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
        index += 1
    raise AssertionError(f"unterminated method: {marker}")


def extract_field(source: str, marker: str) -> str:
    start = source.index(marker)
    return source[start:source.index(";", start) + 1]


class SourceMissAnimationFieldsTest(unittest.TestCase):
    def test_actual_accessors_and_nv_timer_helper(self):
        source = (ROOT / "source/Character.hx").read_text(encoding="utf-8")
        members = "\n".join((
            extract_field(source, "var explicitHasMissAnimations:Null<Bool> = null;"),
            extract_field(source, "@:keep public var hasMissAnimations(get, set):Bool;"),
            extract_field(source, "@:keep public var animTimer:Float = 0;"),
            extract_field(source, "@:keep public var forceDance:Bool = false;"),
        ))
        methods = "\n".join((
            extract_method(source, "@:keep function get_hasMissAnimations():Bool"),
            extract_method(source, "@:keep function set_hasMissAnimations(value:Bool):Bool"),
            extract_method(source, "function updateNightmareVisionAnimationTimer(elapsed:Float):Void"),
        ))
        update = extract_method(source, "override function update(elapsed:Float)")
        self.assertIn("updateNightmareVisionAnimationTimer(elapsed);", update)
        self.assertIn("if (!canPlayAnimations) return;", source[source.index("public function playAnim("):])
        self.assertIn("playAnim(danced ? right : left, forced);", source)

        fixture = r'''
import hscript.Interp;
import hscript.Parser;
class FakeAnimation { public var name:String; public function new(name:String) this.name=name; }
class FakeController { public var curAnim:FakeAnimation; public function new(name:String) curAnim=new FakeAnimation(name); }
class SourceCharacterProbe {
 public var animation:FakeController;
 public var debugMode:Bool=false;
 public var nightmareVisionLegacyActor:Bool=false;
 public var nightmareVisionCharacterData:Dynamic;
 public var canPlayAnimations:Bool=true;
 public var danceRequests:Int=0;
 public var lastDanceForced:Bool=false;
 public var animations:Map<String,Bool>=new Map<String,Bool>();
 __MEMBERS__
 public function new() {}
 public function hasAnimation(name:String):Bool return animations.exists(name);
 public function dance(forced:Bool=false):Void {danceRequests++;lastDanceForced=forced;}
 public function tickTimer(elapsed:Float):Void updateNightmareVisionAnimationTimer(elapsed);
 __METHODS__
}
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function near(a:Float,b:Float,message:String):Void if(Math.abs(a-b)>0.00001) throw message;
 static function main():Void {
  var psych=new SourceCharacterProbe();
  check(!psych.hasMissAnimations,'miss animation availability defaults from empty source animations');
  var exact=['singLEFTmiss','singDOWNmiss','singUPmiss','singRIGHTmiss'];
  for(name in exact) {
   psych.animations=new Map<String,Bool>();
   psych.animations.set(name,true);
   check(psych.hasMissAnimations,'exact Psych miss name should be recognized: '+name);
  }
  psych.animations=new Map<String,Bool>();
  psych.animations.set('singLEFT-miss',true);
  check(!psych.hasMissAnimations,'non-donor miss spelling is not inferred');
  psych.hasMissAnimations=true;
  psych.animations=new Map<String,Bool>();
  check(psych.hasMissAnimations,'script true override survives later animation changes');
  psych.hasMissAnimations=false;
  psych.animations.set('singRIGHTmiss',true);
  check(!psych.hasMissAnimations,'script false override survives present miss animations');
  var interp=new Interp();
  interp.variables.set('character',psych);
  interp.execute(new Parser().parseString('character.hasMissAnimations = true;'));
  check(psych.hasMissAnimations,'HScript can write the public compatibility field');

  var nv=new SourceCharacterProbe();
  nv.nightmareVisionCharacterData={};
  nv.animation=new FakeController('singLEFT');
  nv.animTimer=0.75;
  nv.tickTimer(0.25);
  near(nv.animTimer,0.5,'NV timer subtracts elapsed without playback-rate scaling');
  check(nv.danceRequests==0,'positive remaining timer does not dance early');

  nv.animation.curAnim.name='singLEFT-return';
  nv.tickTimer(0.2);
  near(nv.animTimer,0.5,'return transition pauses the timer');
  nv.animation.curAnim.name='singLEFT-return-loop';
  nv.tickTimer(0.2);
  near(nv.animTimer,0.3,'only names ending exactly in -return pause the timer');

  nv.debugMode=true;
  nv.tickTimer(0.1);
  near(nv.animTimer,0.3,'debug mode exits before source timer updates');
  nv.debugMode=false;
  nv.animation=null;
  nv.tickTimer(0.1);
  near(nv.animTimer,0.3,'missing current animation exits before source timer updates');
  nv.animation=new FakeController('singLEFT');
  nv.forceDance=true;
  nv.canPlayAnimations=false;
  nv.tickTimer(0.5);
  check(nv.animTimer==0 && nv.danceRequests==1 && nv.lastDanceForced,
   'expiration clamps the timer and requests dance(forceDance)');
  check(!nv.canPlayAnimations,'timer does not alter the separate Bopper animation lock');

  var legacy=new SourceCharacterProbe();
  legacy.nightmareVisionLegacyActor=true;
  legacy.animation=new FakeController('singLEFT-return');
  legacy.animTimer=0.2;
  legacy.tickTimer(0.3);
  check(legacy.animTimer==0 && legacy.danceRequests==1,
   'historical timer runs without modern metadata and does not pause on return');

  var native=new SourceCharacterProbe();
  native.animation=new FakeController('singLEFT');
  native.animTimer=1;
  native.tickTimer(0.5);
  near(native.animTimer,1,'non-NV characters ignore the source timer');
 }
}
'''.replace("__MEMBERS__", members).replace("__METHODS__", methods)

        with tempfile.TemporaryDirectory(prefix="source-miss-animation-", dir=ROOT / "tmp") as folder:
            scratch = FixturePath(folder)
            (scratch / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(scratch), "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
