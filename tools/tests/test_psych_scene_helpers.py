"""Psych Iris registry aliases and actor-layer insertion match the live scene."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
from tools.haxe_flixel_math_stubs import write_flixel_point_stub


ROOT = Path(__file__).resolve().parents[2]
IRIS = ROOT / ".haxelib/hscript-iris/1,1,3"


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    line_end = source.find("\n", start)
    opening = source.find("{", start)
    if line_end >= 0 and (opening < 0 or line_end < opening):
        return source[start:line_end].strip()
    if opening < 0:
        return source[start:].strip()
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"Unclosed method: {marker}")


class PsychSceneHelpersTest(unittest.TestCase):
    def test_embedded_registry_alias_and_actor_layer_helpers(self):
        play = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("@:keep public var modchartSprites(get, set):Map<String, FlxSprite>;", play)
        self.assertIn("function get_modchartSprites():Map<String, FlxSprite> return haxeSprites;", play)
        self.assertIn("function set_modchartSprites(value:Map<String, FlxSprite>):Map<String, FlxSprite> return haxeSprites = value;", play)
        self.assertIn("@:keep public var singAnimations:Array<String> = ['singLEFT', 'singDOWN', 'singUP', 'singRIGHT'];", play)
        helpers = "\n".join(extract_method(play, marker) for marker in (
            "function get_modchartSprites()",
            "function set_modchartSprites(",
            "public function getLuaObject(",
            "public function addBehindGF(",
            "public function addBehindBF(",
            "public function addBehindDad(",
        ))
        health_icon = (ROOT / "source/HealthIcon.hx").read_text()
        change_icon = extract_method(health_icon, "public function changeIcon(")

        fixture = r'''import hscript.Interp;
class FlxBasic { public var name:String; public function new(name:String) this.name=name; }
class FlxSprite extends FlxBasic { public function new(name:String) super(name); }
class FakeHost {
 var nightmareVisionScripts:Dynamic=null;
 // NV container branch is isolated; this fixture executes the native/Psych route.
 var stage:Dynamic=null;
 public var gfGroup:FlxBasic;public var boyfriendGroup:FlxBasic;public var dadGroup:FlxBasic;
 var haxeSprites:Map<String,FlxSprite>=new Map();
 public var modchartSprites(get,set):Map<String,FlxSprite>;
 @:keep public var singAnimations:Array<String>=['singLEFT','singDOWN','singUP','singRIGHT'];
 public var members:Array<FlxBasic>=[];
 public var gf:FlxBasic;
 public var boyfriend:FlxBasic;
 public var dad:FlxBasic;
 public function new() {}
 function compatFindObject(name:Dynamic):Dynamic return haxeSprites.get(Std.string(name));
 function insert(position:Int,object:FlxBasic):FlxBasic {
  if(object==null || members.indexOf(object)>=0) return object;
  if(position<0) position=0;
  if(position>members.length) position=members.length;
  members.insert(position,object);return object;
 }
 __HELPERS__
}
class FakeHealthIcon {
 public var curCharacter:String;
 public var ownerRoot:String;
 public var switchCalls:Array<String>=[];
 public function new(owner:String,character:String) {ownerRoot=owner;curCharacter=character;}
 public function switchAnim(char:String='bf',?async:Bool=false):Dynamic {
  switchCalls.push(ownerRoot+':'+char);curCharacter=char;return this;
 }
 __CHANGE_ICON__
}
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function count(values:Array<FlxBasic>,target:FlxBasic):Int {
  var result=0;for(value in values) if(value==target) result++;return result;
 }
 static function makeBridge(host:FakeHost):SourceIrisBridge {
  var bridge=new SourceIrisBridge(host);bridge.variables.set('game',host);return bridge;
 }
 static function main():Void {
  var a=new FakeHost();var b=new FakeHost();
  var originalA=a.modchartSprites;var originalB=b.modchartSprites;
  var first=new FlxSprite('first');var second=new FlxSprite('second');
  var ownerA=makeBridge(a);ownerA.variables.set('first',first);ownerA.variables.set('second',second);
  ownerA.evaluate("game.modchartSprites.set('shared', first); lookupOne=game.getLuaObject('shared');",'owner-a.hx');
  check(a.modchartSprites==originalA&&a.modchartSprites.get('shared')==first
   &&ownerA.variables.get('lookupOne')==first,"embedded Iris registry mutation was not visible to getLuaObject");
  check(b.modchartSprites==originalB&&!b.modchartSprites.exists('shared'),"scene registry leaked between owners");

  // PsychRuntimeBindings' embedded source bridge is a separate interpreter that
  // shares the same game owner, just as module() seeds the active host.
  var embedded=makeBridge(a);embedded.variables.set('second',second);
  embedded.evaluate("game.modchartSprites.set('embedded', second); lookupTwo=game.getLuaObject('embedded');",'embedded.hx');
  check(a.modchartSprites.get('embedded')==second&&embedded.variables.get('lookupTwo')==second
   &&ownerA.variables.get('lookupOne')==first,"embedded module did not share the owner registry");

  // Replacing the source map must replace the host storage pointer itself.
  var replacement:Map<String,FlxSprite>=new Map();replacement.set('old',first);
  embedded.variables.set('replacement',replacement);
  embedded.evaluate("game.modchartSprites=replacement; game.modchartSprites.set('new',second); replacedLookup=game.getLuaObject('new');",'replace.hx');
  check(a.modchartSprites==replacement
   &&replacement.get('new')==second&&embedded.variables.get('replacedLookup')==second
   &&!originalA.exists('new'),"Iris property assignment did not replace the live registry pointer");
  check(b.modchartSprites==originalB&&!b.modchartSprites.exists('new'),"map replacement crossed scene owners");
  embedded.evaluate("singDefaults=game.singAnimations.join(',');",'sing-animation-read.hx');
  check(embedded.variables.get('singDefaults')=='singLEFT,singDOWN,singUP,singRIGHT'
   &&(cast Reflect.getProperty(a,'singAnimations'):Array<String>).join(',')=='singLEFT,singDOWN,singUP,singRIGHT',
   "source actor-direction default was not available through Iris property access");

  // Actors are intentionally ordered Dad, BF, GF here to prove each helper
  // resolves the current native member position rather than a fixed layer.
  var back=new FlxBasic('back');var dad=new FlxBasic('dad');var bf=new FlxBasic('bf');
  var gf=new FlxBasic('gf');var front=new FlxBasic('front');
  a.members=[back,dad,bf,gf,front];a.dad=dad;a.boyfriend=bf;a.gf=gf;
  var behindDad=new FlxBasic('behindDad');var behindBF=new FlxBasic('behindBF');
  var behindGF=new FlxBasic('behindGF');
  a.addBehindDad(behindDad);a.addBehindBF(behindBF);a.addBehindGF(behindGF);
  check(a.members.indexOf(behindDad)==a.members.indexOf(dad)-1
   &&a.members.indexOf(behindBF)==a.members.indexOf(bf)-1
   &&a.members.indexOf(behindGF)==a.members.indexOf(gf)-1,
   "actor helpers did not insert immediately before the selected live actor");
  var wasAt=a.members.indexOf(behindGF);a.addBehindGF(behindGF);
  check(count(a.members,behindGF)==1&&a.members.indexOf(behindGF)==wasAt,
   "existing group member did not preserve FlxGroup.insert duplicate behavior");
  var existing=front;a.addBehindBF(existing);
  check(count(a.members,existing)==1,"addBehindBF duplicated an existing member");

  var iconA=new FakeHealthIcon('owner-a','dad');var iconB=new FakeHealthIcon('owner-b','bf');
  iconA.changeIcon('dad');iconA.changeIcon('opponent');iconA.changeIcon('opponent');
  iconB.changeIcon('player',false);iconB.changeIcon('player');
  check(iconA.switchCalls.join(',')=='owner-a:opponent'&&iconA.curCharacter=='opponent'
   &&iconB.switchCalls.join(',')=='owner-b:player'&&iconB.curCharacter=='player',
   "changeIcon did not skip unchanged ids or delegate changed ids through the current icon owner");

  ownerA.evaluator.release();embedded.evaluator.release();
 }
}'''.replace("__HELPERS__", helpers).replace("__CHANGE_ICON__", change_icon)

        with tempfile.TemporaryDirectory(prefix="psych-scene-helpers-", dir=ROOT / "tmp") as folder:
            scratch = Path(folder)
            write_flixel_point_stub(scratch)
            # This fixture exercises Psych's native scene branch; NV's group
            # insertion is executed by test_nv_legacy_stage/integration.
            (scratch / "NightmareVisionStageScene.hx").write_text('class NightmareVisionStageScene {public static function insertBehind(scene:Dynamic,stage:Dynamic,actor:Dynamic,object:Dynamic):Void {stage.insert(stage.members.indexOf(actor),object);}}', newline="\n")

            (scratch / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            runtime_stub = '''class HxcCompatRuntime {
 public static function getZIndex(_target:Dynamic):Dynamic return 0;
 public static function setZIndex(_target:Dynamic,value:Dynamic,?_op:String='='):Dynamic return value;
}'''
            (scratch / "HxcCompatRuntime.hx").write_text(runtime_stub, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"), "-cp", str(IRIS), "-cp", str(scratch),
                 "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=90,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
