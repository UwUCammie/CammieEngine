"""Exercise extracted source-owned game-over callback lifecycle methods."""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND, HAXE


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source" / "GameOverSubstate.hx"


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


def run_fixture(fixture: str) -> subprocess.CompletedProcess:
    (ROOT / "tmp").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temp:
        folder = Path(temp)
        (folder / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
        return subprocess.run(
            [*HAXE_COMMAND, "-cp", str(folder), "--run", "Main"],
            cwd=ROOT,
            env={**os.environ, "TMPDIR": temp},
            capture_output=True,
            text=True,
            timeout=30,
        )


class SourceGameOverLifecycleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")

    @unittest.skipUnless(HAXE.is_file(), "portable Haxe is unavailable")
    def test_create_order_stop_behavior_and_post_hook(self):
        create = extract_method(self.source, "override function create():Void")
        fixture = r'''class Trace {
 public static var events:Array<String>=[];
 public static function add(value:String):Void events.push(value);
 public static function reset():Void events=[];
}
class ScriptCallbackResult { public static inline var STOP:String="PSY_STOP"; }
class NightmareVisionScriptGroup { public static inline var STOP_FUNC:String="NV_STOP"; }
class Conductor { public static var songPosition:Float=55; }
class MusicBeatSubstate {
 public function new() {}
 public function create():Void Trace.add("super.create");
}
class PlayState {
 public var mode:Int;
 public var startResult:Dynamic;
 public function new(mode:Int,startResult:Dynamic) { this.mode=mode; this.startResult=startResult; }
 public function sourceGameOverSetInGameOver(value:Bool):Void Trace.add("inGameOver:"+value);
 public function sourceGameOverCall(hook:String,args:Array<Dynamic>):Dynamic {
  Trace.add("call:"+hook+":"+args.length+(hook=="onGameOverStart" ? ":pos="+Conductor.songPosition : ""));
  return hook=="onGameOverStart" ? startResult : null;
 }
}
class GameOverSubstate extends MusicBeatSubstate {
 public static var instance:GameOverSubstate;
 var sourceOwner:PlayState;
 var sourceMode:Int;
 var sourceStartStopped:Bool=false;
 var quoteCharacter:Dynamic;
 public function new(mode:Int,result:Dynamic) { super(); sourceMode=mode; sourceOwner=new PlayState(mode,result); }
 function setupSourceGameOver(character:Dynamic,name:Null<String>,resetSongPosition:Bool=true):Void {
  if(resetSongPosition) Conductor.songPosition=0;
  Trace.add("setup:"+name);
 }
 function preloadPsychGameOverLoop():Void Trace.add("preload-loop");
 function setupPsychPicoOverlay():Void Trace.add("pico-overlay");
 function sourceDeathCharacterName():String return "bf-dead";
''' + create + r'''
 public function runCreate():Void create();
}
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function joined():String return Trace.events.join(",");
 static function main():Void {
  var nvStop=new GameOverSubstate(2,"NV_STOP");
  nvStop.runCreate();
  check(joined()=="inGameOver:true,call:onGameOverStart:0:pos=0,super.create,call:onGameOverPost:0",
   "NV STOP must skip default setup while still calling super and post: "+joined());

  Trace.reset();
  var nvContinue=new GameOverSubstate(2,null);
  nvContinue.runCreate();
  check(joined()=="inGameOver:true,call:onGameOverStart:0:pos=0,setup:bf-dead,super.create,call:onGameOverPost:0",
   "NV create order changed: "+joined());

  Trace.reset();
  var psychStop=new GameOverSubstate(1,"PSY_STOP");
  psychStop.runCreate();
  check(joined()=="setup:bf-dead,inGameOver:true,call:onGameOverStart:0:pos=0,preload-loop,pico-overlay,super.create",
   "Psych start must follow setup, preload afterward, and ignore STOP: "+joined());

  Trace.reset();
  var native=new GameOverSubstate(0,null);
  native.runCreate();
  check(joined()=="super.create","native create path changed: "+joined());
 }
}
'''
        result = run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(HAXE.is_file(), "portable Haxe is unavailable")
    def test_update_order_input_cancellation_and_confirm_arguments(self):
        methods = "\n".join(
            extract_method(self.source, marker)
            for marker in (
                "function dispatchSourceGameOverUpdateBeforeSuper(",
                "function dispatchSourceGameOverUpdateAfterSuper(",
                "function dispatchSourceGameOverUpdatePost(",
                "function notifySourceGameOverConfirmed(",
                "function sourceResultStops(",
                "function updateSourceGameOverInput(",
            )
        )
        update = extract_method(self.source, "override function update(elapsed:Float)")
        before = update.index("dispatchSourceGameOverUpdateBeforeSuper(elapsed);")
        super_update = update.index("super.update(elapsed);", before)
        after = update.index("dispatchSourceGameOverUpdateAfterSuper(elapsed);", super_update)
        post = update.index("dispatchSourceGameOverUpdatePost(elapsed);", after)
        self.assertLess(before, super_update)
        self.assertLess(super_update, after)
        self.assertLess(after, post)
        self.assertIn("return;", update[post:])

        fixture = r'''class Trace {
 public static var events:Array<String>=[];
 public static function add(value:String):Void events.push(value);
 public static function reset():Void events=[];
}
class ScriptCallbackResult { public static inline var STOP:String="PSY_STOP"; }
class NightmareVisionScriptGroup { public static inline var STOP_FUNC:String="NV_STOP"; }
class MusicBeatSubstate { public function new() {} public function update(elapsed:Float):Void Trace.add("super"); }
class PlayState {
 public var confirmResult:Dynamic=null;
 public var cancelResult:Dynamic=null;
 public var acceptControl:Bool=false;
 public var backControl:Bool=false;
 public function new() {}
 public function sourceGameOverCheckControl(action:String):Bool {
  Trace.add("control:"+action);
  return action=="ACCEPT" ? acceptControl : backControl;
 }
 public function sourceGameOverCall(hook:String,args:Array<Dynamic>):Dynamic {
  Trace.add("call:"+hook+":"+args.length+(args.length>0 ? ":"+Std.string(args[0]) : ""));
  return hook=="onGameOverConfirm" && args.length==0 ? confirmResult
   : hook=="onGameOverCancel" ? cancelResult : null;
 }
}
class GameOverSubstate extends MusicBeatSubstate {
 public var sourceMode:Int=0;
 public var sourceOwner:PlayState;
 public var isEnding:Bool=false;
 public function new(mode:Int) { super(); sourceMode=mode; sourceOwner=new PlayState(); }
 function endBullshit():Void Trace.add("end");
 function sourceBackToMenu():Void Trace.add("menu");
''' + methods + r'''
 public function runBefore(elapsed:Float):Void dispatchSourceGameOverUpdateBeforeSuper(elapsed);
 public function runAfter(elapsed:Float):Void dispatchSourceGameOverUpdateAfterSuper(elapsed);
 public function runPost(elapsed:Float):Void dispatchSourceGameOverUpdatePost(elapsed);
 public function runInput():Void updateSourceGameOverInput();
 public function runConfirm():Void notifySourceGameOverConfirmed();
 public function setResults(confirm:Dynamic,cancel:Dynamic):Void {
  sourceOwner.confirmResult=confirm; sourceOwner.cancelResult=cancel;
 }
}
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function joined():String return Trace.events.join(",");
 static function main():Void {
  var nv=new GameOverSubstate(2);
  nv.runBefore(0.25);
  Trace.add("super");
  nv.runAfter(0.25);
  nv.runPost(0.25);
  check(joined()=="call:onUpdate:1:0.25,super,call:onUpdatePost:1:0.25",
   "NV update must precede super and post must be last: "+joined());

  Trace.reset();
  var psych=new GameOverSubstate(1);
  Trace.add("super");
  psych.runAfter(0.5);
  psych.runPost(0.5);
  check(joined()=="super,call:onUpdate:1:0.5,call:onUpdatePost:1:0.5",
   "Psych update must follow super and post must be last: "+joined());

  Trace.reset();
  psych.sourceOwner.acceptControl=true; psych.sourceOwner.backControl=true;
  psych.runInput();
  check(joined()=="control:ACCEPT,end","Psych accept must take precedence over back: "+joined());
  Trace.reset(); psych.isEnding=true;
  psych.runInput();
  check(joined()=="","Psych input must stop once ending: "+joined());

  Trace.reset();
  var nvInput=new GameOverSubstate(2);
  nvInput.sourceOwner.acceptControl=true; nvInput.sourceOwner.backControl=true;
  nvInput.runInput();
  check(joined()=="control:ACCEPT,call:onGameOverConfirm:0,end,control:BACK,call:onGameOverCancel:0,menu",
   "NV accept and back must remain independent: "+joined());

  Trace.reset();
  nvInput=new GameOverSubstate(2);
  nvInput.sourceOwner.acceptControl=true;
  nvInput.sourceOwner.backControl=true; nvInput.setResults("NV_STOP","NV_STOP");
  nvInput.runInput();
  check(joined()=="control:ACCEPT,call:onGameOverConfirm:0,control:BACK,call:onGameOverCancel:0",
   "NV STOP must cancel both transitions: "+joined());

  Trace.reset();
  psych=new GameOverSubstate(1);
  psych.runConfirm();
  check(joined()=="call:onGameOverConfirm:1:true","end confirmation arguments changed: "+joined());
 }
}
'''
        result = run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_menu_callback_and_end_callback_order(self):
        back = extract_method(self.source, "function sourceBackToMenu():Void")
        self.assertLess(back.index("sourceGameOverResetForMenu()"), back.index("loadAndSwitchState"))
        self.assertLess(back.index("loadAndSwitchState"), back.index("playMusic"))
        self.assertLess(back.index("playMusic"), back.index("onGameOverConfirm", back.index("playMusic")))
        end = extract_method(self.source, "function endBullshit():Void")
        self.assertLess(end.index("new FlxTimer().start"), end.index("notifySourceGameOverConfirmed()"))

        fixture = r'''class Trace {
 public static var events:Array<String>=[];
 public static function add(value:String):Void events.push(value);
}
class FakeMusic { public function new() {} public function stop():Void Trace.add("music.stop"); }
class SoundFrontEnd {
 public var music:FakeMusic=new FakeMusic();
 public function new() {}
 public function playMusic(path:Dynamic):Void Trace.add("menuMusic:"+Std.string(path));
}
class SourceGameOverSettings { public static inline var PSYCH:Int=1; }
class Camera {
 public var visible(get,set):Bool;
 var value:Bool=true;
 public function new() {}
 function get_visible():Bool return value;
 function set_visible(next:Bool):Bool { Trace.add("camera.visible:"+next); return value=next; }
}
class FlxG {
 public static var sound:SoundFrontEnd=new SoundFrontEnd();
 public static var camera:Camera=new Camera();
}
class HxcCompatRuntime { public static function clearGameOverCharacter(value:Dynamic):Void Trace.add("hxc.clear"); }
class Paths { public static function music(key:String):String return key; }
class StoryMenuState { public function new() {} }
class FreeplayState { public function new() {} }
class LoadingState {
 public static function loadAndSwitchState(value:Dynamic):Void
  Trace.add("load:"+(Std.isOfType(value,StoryMenuState) ? "story" : "freeplay"));
}
class PlayState {
 public static var isStoryMode:Bool=true;
 public function new() {}
 public function sourceGameOverResetForMenu():Void Trace.add("reset");
 public function sourceGameOverCall(hook:String,args:Array<Dynamic>):Dynamic {
  Trace.add("call:"+hook+":"+args.length+(args.length>0 ? ":"+Std.string(args[0]) : ""));
  return null;
 }
}
class GameOverSubstate {
 var sourceMode:Int;
 var sourceOwner:PlayState=new PlayState();
 var bf:Dynamic=null;
 var isEnding:Bool=false;
 public function new(mode:Int) sourceMode=mode;
 function cancelDeathQuote():Void Trace.add("quote.cancel");
 function hxcClearDeathOverlays():Void Trace.add("overlays.clear");
''' + back + r'''
 public function runBack():Void sourceBackToMenu();
}
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function joined():String return Trace.events.join(",");
 static function main():Void {
  var psych=new GameOverSubstate(1);
  psych.runBack();
  check(joined()=="quote.cancel,overlays.clear,hxc.clear,camera.visible:false,music.stop,reset,load:story,menuMusic:freakyMenu,call:onGameOverConfirm:1:false",
   "Psych back callback must follow menu transition and music: "+joined());

  Trace.events=[];
  var nv=new GameOverSubstate(2);
  nv.runBack();
  check(joined()=="quote.cancel,overlays.clear,hxc.clear,music.stop,reset,load:story,menuMusic:freakyMenu",
   "NV cancel must not send Psych's false confirmation: "+joined());
 }
}
'''
        result = run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
