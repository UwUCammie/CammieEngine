"""Executable extracted-method coverage for the native game-over smoke path."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HARNESS_PATH = ROOT / "source" / "RuntimeSmokeHarness.hx"
HAXE = ROOT / ".tools" / "haxe" / "haxe"


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
    raise AssertionError(f"unterminated Haxe method: {marker}")


def run_haxe_fixture(fixture: str) -> subprocess.CompletedProcess:
    (ROOT / "tmp").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
        folder = Path(work)
        (folder / "Main.hx").write_text(fixture, encoding="utf-8", newline='\n')
        return subprocess.run(
            [*HAXE_COMMAND, "-cp", str(folder), "--run", "Main"],
            cwd=ROOT,
            env={**os.environ, "TMPDIR": work},
            capture_output=True,
            text=True,
            timeout=30,
        )


class RuntimeSmokeGameOverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = HARNESS_PATH.read_text(encoding="utf-8")

    @unittest.skipUnless(HAXE.is_file(), "portable Haxe is unavailable")
    def test_trigger_waits_for_ready_song_start_position_and_active_playstate(self):
        method = extract_method(self.harness, "static function maybeTriggerGameOver()")
        fixture = r'''class Conductor { public static var songPosition:Float=0; }
class FlxG { public static var state:Dynamic=null; }
class NonGameplayState { public function new() {} }
class PlayState {
 public static var instance:PlayState;
 public static var opponentPlayer:Bool=false;
 public var health:Float=1;
 public var subState:Dynamic=null;
 public function new() { instance=this; }
}
class Main {
 static var cfg:Dynamic={gameOverAfterMs:50.0,gameOverTriggered:false};
 static var active=true;
 static var finished=false;
 static var playStateReady=false;
 static var songStartObserved=false;
 static var events:Array<Dynamic>=[];
 static function config():Dynamic return cfg;
 static function enabled():Bool return active;
 static function emit(name:String,details:Dynamic):Void events.push({name:name,details:details});
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
''' + method + r'''
 static function main():Void {
  var game=new PlayState();
  FlxG.state=game;
  Conductor.songPosition=100;
  cfg.gameOverAfterMs=-1;
  playStateReady=true; songStartObserved=true;
  maybeTriggerGameOver();
  check(game.health==1 && events.length==0,"disabled trigger changed health");

  cfg.gameOverAfterMs=50;
  playStateReady=false;
  maybeTriggerGameOver();
  check(game.health==1,"trigger ran before PlayState readiness");
  playStateReady=true; songStartObserved=false;
  maybeTriggerGameOver();
  check(game.health==1,"trigger ran before song start");
  songStartObserved=true; Conductor.songPosition=49;
  maybeTriggerGameOver();
  check(game.health==1,"trigger ran before target position");

  Conductor.songPosition=100;
  FlxG.state=new NonGameplayState();
  maybeTriggerGameOver();
  check(game.health==1,"trigger ran outside gameplay");
  FlxG.state=game; game.subState={active:true};
  maybeTriggerGameOver();
  check(game.health==1,"trigger ran while a substate was open");

  game.subState=null;
  maybeTriggerGameOver();
  check(game.health==0 && cfg.gameOverTriggered && events.length==1,
   "player death trigger did not set the native losing health value");
  game.health=1;
  maybeTriggerGameOver();
  check(game.health==1 && events.length==1,"one-shot trigger ran twice");

  cfg.gameOverTriggered=false;
  PlayState.opponentPlayer=true;
  maybeTriggerGameOver();
  check(game.health==2 && events.length==2,
   "opponent death trigger did not set the native losing health value");

  cfg.gameOverTriggered=false; active=false; game.health=1;
  maybeTriggerGameOver();
  check(game.health==1 && events.length==2,"disabled harness triggered game over");
  active=true; finished=true;
  maybeTriggerGameOver();
  check(game.health==1 && events.length==2,"finished harness triggered game over");
 }
}
'''
        result = run_haxe_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(HAXE.is_file(), "portable Haxe is unavailable")
    def test_configuration_guards_and_missing_trigger_gate(self):
        unsupported = extract_method(
            self.harness,
            "public static function unsupportedGameOverConfiguration(",
        )
        missing = extract_method(
            self.harness,
            "public static function missingRequiredGameOver(",
        )
        fixture = "class Main {\n" + unsupported + "\n" + missing + r'''
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main():Void {
  check(!unsupportedGameOverConfiguration(-1,false,false,false,false,1),"disabled mode rejected");
  check(!unsupportedGameOverConfiguration(100,false,false,false,false,1),"valid game-over mode rejected");
  check(unsupportedGameOverConfiguration(100,true,false,false,false,1),"practice mode accepted");
  check(unsupportedGameOverConfiguration(100,false,true,false,false,1),"player-hit mode accepted");
  check(unsupportedGameOverConfiguration(100,false,false,true,false,1),"song-end mode accepted");
  check(unsupportedGameOverConfiguration(100,false,false,false,true,1),"chart editor accepted");
  check(unsupportedGameOverConfiguration(100,false,false,false,false,2),"multi-visit mode accepted");
  check(!missingRequiredGameOver(-1,false),"disabled mode required a trigger");
  check(missingRequiredGameOver(100,false),"missing trigger was not detected");
  check(!missingRequiredGameOver(100,true),"observed trigger was rejected");
 }
}
'''
        result = run_haxe_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("case '--smoke-gameover-after-ms'", self.harness)
        self.assertIn("gameOverAfterMs: -1", self.harness)
        self.assertIn(
            "missingRequiredGameOver(config().gameOverAfterMs, config().gameOverTriggered)",
            self.harness,
        )

    @unittest.skipUnless(HAXE.is_file(), "portable Haxe is unavailable")
    def test_gameover_phase_marker_keeps_only_bounded_primitive_details(self):
        method = extract_method(
            self.harness,
            "public static function markGameOverPhase(",
        )
        bounded = extract_method(
            self.harness,
            "static function boundedSmokeText(",
        )
        fixture = r'''class Main {
 static var active=true;
 static var finished=false;
 static var events:Array<Dynamic>=[];
 static function enabled():Bool return active;
 static function emit(name:String,payload:Dynamic):Void events.push({name:name,payload:payload});
''' + bounded + "\n" + method + r'''
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main():Void {
  var longText="x";
  for (_ in 0...300) longText += "x";
  markGameOverPhase("quote_start",{count:2,active:true,note:"ready",items:[1,2],object:{x:1},longText:longText});
  check(events.length==1 && events[0].name=="gameover_phase","phase marker missing");
  var payload=events[0].payload;
  check(payload.phase=="quote_start","phase marker altered its phase");
  check(payload.details.count==2 && payload.details.active==true && payload.details.note=="ready",
   "primitive details were dropped");
  check(payload.details.items==null && payload.details.object==null,
   "non-primitive details were serialized");
  check(payload.details.longText.length==256,"string details were not bounded");
  finished=true;
  markGameOverPhase("destroy",{count:3});
  check(events.length==1,"finished harness emitted a phase marker");
  finished=false; active=false;
  markGameOverPhase("destroy",{count:3});
  check(events.length==1,"disabled harness emitted a phase marker");
 }
}
'''
        result = run_haxe_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(HAXE.is_file(), "portable Haxe is unavailable")
    def test_post_update_clock_ticks_only_after_configured_death_leaves_playstate(self):
        gate = extract_method(
            self.harness,
            "public static function gameOverClockShouldTick(",
        )
        observer = extract_method(
            self.harness,
            "static function onGameOverClockPostUpdate()",
        )
        fixture = r'''class FlxG {
 public static var state:Dynamic=null;
 public static var elapsed:Float=0.016;
}
class PlayState { public function new() {} }
class FreeplayState { public function new() {} }
class Main {
 static var cfg:Dynamic=null;
 static var finished=false;
 static var tickCount=0;
 static var tickElapsed:Float=-1;
 static function config():Dynamic return cfg;
 static function tick(elapsed:Float):Bool { tickCount++; tickElapsed=elapsed; return false; }
''' + gate + "\n" + observer + r'''
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main():Void {
  FlxG.state=new FreeplayState();
  onGameOverClockPostUpdate();
  check(tickCount==0,"observer ticked without smoke configuration");

  cfg={gameOverAfterMs:-1.0,gameOverTriggered:true};
  onGameOverClockPostUpdate();
  check(tickCount==0,"observer ticked with the game-over mode disabled");
  cfg={gameOverAfterMs:100.0,gameOverTriggered:false};
  onGameOverClockPostUpdate();
  check(tickCount==0,"observer ticked before the death trigger");

  cfg.gameOverTriggered=true;
  FlxG.state=new PlayState();
  onGameOverClockPostUpdate();
  check(tickCount==0,"observer double-ticked active PlayState or its substate");

  FlxG.state=new FreeplayState();
  onGameOverClockPostUpdate();
  check(tickCount==1 && tickElapsed==FlxG.elapsed,
   "observer did not advance the smoke clock after leaving PlayState");
  finished=true;
  onGameOverClockPostUpdate();
  check(tickCount==1,"finished smoke observer ticked again");
 }
}
'''
        result = run_haxe_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("if (config().gameOverAfterMs >= 0)", self.harness)
        self.assertIn("installGameOverClock();", self.harness)
        self.assertIn("FlxG.signals.postUpdate.add(onGameOverClockPostUpdate);", self.harness)


if __name__ == "__main__":
    unittest.main()
