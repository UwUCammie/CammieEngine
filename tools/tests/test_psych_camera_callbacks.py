"""Exercise the production Psych section camera callback and lifecycle guards."""
from pathlib import Path
from haxe_test_support import FixturePath as Path, HAXE_COMMAND
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"Unclosed method: {marker}")


class PsychCameraCallbacksTest(unittest.TestCase):
    def test_psych_focus_callbacks_and_engine_lifecycle_guards(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "@:keep public function moveCameraSection(",
                "function updatePsychSectionCamera():Void",
                "function applyNightmareVisionSingDisplacement(",
            )
        )
        fixture = r'''class FlxPoint {
 public var x:Float;
 public var y:Float;
 public function new(x:Float=0,y:Float=0) {this.x=x;this.y=y;}
 public function put():Void {}
 public function putWeak():Void {}
 public function setPosition(x:Float,y:Float):Void {this.x=x;this.y=y;}
}
class Character {
 public var x:Float;
 public var y:Float;
 public var cameraPosition:Array<Float>=[0,0];
 public function new(x:Float,y:Float) {this.x=x;this.y=y;}
 public function getMidpoint():FlxPoint return new FlxPoint(x,y);
 public function getSingDisplacement():FlxPoint return new FlxPoint(20,0);
}
class FollowTarget {
 public var x:Float=0;
 public var y:Float=0;
 public function new() {}
 public function setPosition(x:Float,y:Float):Void {this.x=x;this.y=y;}
}
class ScriptGroup {
 public var whosTurn:String='';
 public function new() {}
 public function set(name:String,value:String):Void if(name=='whosTurn') whosTurn=value;
}
class NightmareScripts { public var group=new ScriptGroup(); public function new() {} }
class State {
 public var SONG:Dynamic;
 public var curSection:Int=0;
 public var gf:Character;
 public var dad:Character;
 public var boyfriend:Character;
 public var girlfriendCameraOffset:Array<Float>=[0,0];
 public var camFollow:FollowTarget=new FollowTarget();
 public var nightmareVisionScripts:Dynamic=null;
 public var nightmareVisionPrefs:Dynamic={view:{camFollowsCharacters:true}};
 public var psychCameraCompatibilityActive:Bool=true;
 public var generatedMusic:Bool=true;
 public var endingSong:Bool=false;
 public var isCameraOnForcedPos:Bool=false;
 public var forceCamera:Bool=false;
 public var targets:Array<String>=[];
 public var hscriptCalls:Array<String>=[];
 public var nightmareCalls:Array<String>=[];
 public var callbackX:Float=-1;
 public var callbackY:Float=-1;
 public function new() {
  boyfriend=new Character(100,200);
  dad=new Character(500,600);
  gf=new Character(700,300);
  var sections:Array<Dynamic>=[
   {mustHitSection:true,gfSection:false},
   {mustHitSection:false,gfSection:false},
   {mustHitSection:true,gfSection:true},
   null
  ];
  SONG={notes:sections};
 }
 function setCameraFollowActor(actor:Character,role:String):Void {
  if(actor==null) return;
  targets.push(role);
  camFollow.setPosition(actor.x,actor.y);
 }
 function moveCamera(isDad:Bool):Void setCameraFollowActor(isDad?dad:boyfriend,isDad?'dad':'boyfriend');
 function callAllHScript(name:String,args:Array<Dynamic>):Dynamic {
  hscriptCalls.push(name+':'+Std.string(args[0]));
  callbackX=camFollow.x; callbackY=camFollow.y;
  return null;
 }
 function callNightmareVision(name:String,args:Array<Dynamic>):Dynamic {
  nightmareCalls.push(name+':'+Std.string(args[0]));
  return null;
 }
 public function resetCalls():Void {
  targets=[];hscriptCalls=[];nightmareCalls=[];callbackX=-1;callbackY=-1;
 }
__METHODS__
}
@:access(State)
class Main {
 static function fail(message:String):Void throw message;
 static function check(value:Bool,message:String):Void if(!value) fail(message);
 static function near(actual:Float,expected:Float,message:String):Void
  if(Math.abs(actual-expected)>.00001) fail(message+': '+actual+' != '+expected);
 static function noPsychDispatch(s:State,message:String):Void
  check(s.hscriptCalls.length==0 && s.targets.length==0,message);
 static function main():Void {
  var s=new State();
  s.moveCameraSection(0);
  check(s.targets.join(',')=='boyfriend','BF section selects player focus');
  check(s.hscriptCalls.join(',')=='onMoveCamera:boyfriend','BF callback focus name');
  near(s.callbackX,100,'BF callback follows target x'); near(s.callbackY,200,'BF callback follows target y');

  s.resetCalls();s.moveCameraSection(1);
  check(s.targets.join(',')=='dad' && s.hscriptCalls.join(',')=='onMoveCamera:dad','opponent focus callback');
  near(s.callbackX,500,'dad callback sees moved focus');

  s.resetCalls();s.moveCameraSection(2);
  check(s.targets.join(',')=='gf' && s.hscriptCalls.join(',')=='onMoveCamera:gf','GF section callback');
  near(s.callbackX,700,'GF callback sees moved focus');

  // A GF-owned chart section with no GF falls back to the ordinary lane focus.
  s.resetCalls();s.gf=null;s.moveCameraSection(2);
  check(s.targets.join(',')=='boyfriend' && s.hscriptCalls.join(',')=='onMoveCamera:boyfriend',
   'null GF falls back to section ownership');
  near(s.callbackY,200,'null-GF callback sees fallback focus');

  // The public API clamps negative section indices and ignores missing rows.
  s.resetCalls();s.moveCameraSection(-1);
  check(s.hscriptCalls.join(',')=='onMoveCamera:boyfriend','negative section clamps to first');
  s.resetCalls();s.moveCameraSection(3);check(s.hscriptCalls.length==0,'null row has no callback');
  s.resetCalls();s.moveCameraSection(20);check(s.hscriptCalls.length==0,'out-of-range section has no callback');
  s.SONG=null;s.moveCameraSection();check(s.hscriptCalls.length==0,'missing chart has no callback');

  // A native song still follows its section but does not acquire Psych hooks.
  s=new State();s.psychCameraCompatibilityActive=false;s.moveCameraSection(0);
  check(s.targets.join(',')=='boyfriend' && s.hscriptCalls.length==0,'native section has no Psych callback');

  // NMV owns its callback path even though it also uses Psych camera metadata.
  s=new State();s.nightmareVisionScripts=new NightmareScripts();s.moveCameraSection(0);
  check(s.hscriptCalls.length==0 && s.nightmareCalls.join(',')=='onMoveCamera:boyfriend',
   'NMV callback is isolated from Psych scripts');

  // The lifecycle helper only moves and dispatches for active Psych gameplay.
  s=new State();s.updatePsychSectionCamera();
  check(s.hscriptCalls.join(',')=='onMoveCamera:boyfriend','eligible section transition dispatches');
  s=new State();s.psychCameraCompatibilityActive=false;s.updatePsychSectionCamera();noPsychDispatch(s,'native lifecycle guard');
  s=new State();s.nightmareVisionScripts=new NightmareScripts();s.updatePsychSectionCamera();noPsychDispatch(s,'NMV lifecycle guard');
  s=new State();s.generatedMusic=false;s.updatePsychSectionCamera();noPsychDispatch(s,'pre-generation guard');
  s=new State();s.endingSong=true;s.updatePsychSectionCamera();noPsychDispatch(s,'ending guard');
  s=new State();s.isCameraOnForcedPos=true;s.updatePsychSectionCamera();noPsychDispatch(s,'script-locked camera guard');
  s=new State();s.forceCamera=true;s.updatePsychSectionCamera();noPsychDispatch(s,'forced camera guard');
 }
}'''.replace("__METHODS__", methods)

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            (Path(scratch) / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", scratch, "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        # The camera hook runs after song scripts and swap preloads are ready,
        # but before intro selection can begin the countdown/cutscene path.
        create_start = source.index("RuntimeSmokeHarness.markStep('playstate:create:ui-layout-complete')")
        intro_start = source.index("RuntimeSmokeHarness.markStep('playstate:create:intro-selection-begin')", create_start)
        create_block = source[create_start:intro_start]
        self.assertLess(create_block.index("preloadSwapCharacters();"),
                        create_block.index("updatePsychSectionCamera();"))
        self.assertIn("} else {\n\t\t\tupdatePsychSectionCamera();\n\t\t}", create_block)

        # Section follow precedes all engine/script section-hit callbacks.
        section_start = source.index("if (curSection != previousSection) {")
        section_end = source.index("\n\t\t}", section_start) + len("\n\t\t}")
        section_block = source[section_start:section_end]
        camera_at = section_block.index("updatePsychSectionCamera();")
        for hook in (
            "NightmareVisionPluginHost.callActive('onSectionHit')",
            "callNightmareVision('onSectionHit', [])",
            "dispatchPsychCompiledStage('sectionHit', [])",
            "callAllHScript('sectionHit', [curSection])",
        ):
            self.assertLess(camera_at, section_block.index(hook), hook)


if __name__ == "__main__":
    unittest.main()
