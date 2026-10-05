"""Imported Psych stage GameOverSubstate writes reach native per-song settings."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


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
                return source[start : index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class PsychGameOverClassCompatTest(unittest.TestCase):
    def test_owner_facades_share_live_nullable_settings_and_expire_with_owner(self):
        fixture = r'''
class Host {
 public var sourceGameOverSettings:SourceGameOverSettings;
 public function new(chart:Dynamic) sourceGameOverSettings = new SourceGameOverSettings(1, chart);
 public function setPsychClassProperty(_className:String, key:String, value:Dynamic):Void
  sourceGameOverSettings.write(key, value);
}
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var chart = {gameOverChar:'  alternate-dead  ', gameOverSound:'chart-loss'};
  var host = new Host(chart);
  var first = new PsychGameOverClassCompat(host, chart);
  host.sourceGameOverSettings.loopSoundName = 'stage-loop';
  var second = new PsychGameOverClassCompat(host, chart);
  check(first.characterName == '  alternate-dead  ', 'chart name was trimmed');
  check(second.loopSoundName == 'stage-loop', 'constructing a facade overwrote prior stage writes');
  first.deathSoundName = '';
  check(second.deathSoundName == '', 'empty direct setting reverted to chart default');
  second.endSoundName = null;
  check(first.endSoundName == null, 'null direct setting reverted to cached default');
  host.sourceGameOverSettings.characterName = 'lua-dead';
  check(first.characterName == 'lua-dead' && second.characterName == 'lua-dead', 'reflection writes did not reach both facades');
  first.deathDelay = -0.5;
  check(second.deathDelay == -0.5, 'source numeric delay was replaced or rejected');
  second.resetVariables();
  check(first.characterName == '  alternate-dead  ' && first.deathSoundName == 'chart-loss'
   && first.loopSoundName == 'gameOver' && first.endSoundName == 'gameOverEnd' && first.deathDelay == 0,
   'reset did not restore source chart/default values across facades');
  var other = new Host({});
  var otherFacade = new PsychGameOverClassCompat(other, {});
  first.characterName = 'isolated-death';
  check(otherFacade.characterName == 'bf-dead', 'owner mutation leaked into next song');
  host.sourceGameOverSettings = null;
  var readRejected = false;
  var writeRejected = false;
  try first.characterName catch (_:Dynamic) readRejected = true;
  try second.deathSoundName = 'stale-loss' catch (_:Dynamic) writeRejected = true;
  check(readRejected && writeRejected, 'disposed owner facade fell back to stale local state');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            Path(folder, 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                 '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_compiled_stage_binds_the_per_song_class_surface(self):
        source = (ROOT / "source/PsychCompiledStageBindings.hx").read_text(encoding="utf-8")
        self.assertIn("new PsychGameOverClassCompat(PlayState.instance, PlayState.SONG)", source)
        self.assertIn("bind(bindings, 'substates.GameOverSubstate', gameOverClass);", source)

    def test_source_death_delay_routes_to_native_transition(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        self.assertIn("'endsoundname', 'deathdelay'", source)
        self.assertIn("psychGameOverDeathDelaySeconds = delay;", source)
        self.assertIn("public function psychGameOverDeathDelay():Float", source)
        self.assertIn("new FlxTimer().start(deathDelay", source)
        self.assertIn("function runPsychGameOverTransition():Void", source)
        self.assertIn("if (psychGameOverTransitionPending)", source)

    def test_source_style_static_writes_route_to_native_bridge(self):
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        source_instance_method = extract_method(play_state, "@:keep public function sourceGameOverInstance")
        source_instance_method = source_instance_method.replace("@:keep ", "", 1)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder)
            (path / "PsychGameOverClassProbe.hx").write_text(r'''import hscript.Parser;
import hscript.Interp;
class GameOverSubstate { public static var instance:Dynamic; }
class PsychGameOverHost {
 public var calls:Array<String> = [];
 public var sourceScoreOwner:Bool = false;
 public var isDead:Bool = false;
 public function new() {}
 public function setPsychClassProperty(className:String, field:String, value:Dynamic):Void
  calls.push(className + ":" + field + ":" + Std.string(value));
__SOURCE_INSTANCE_METHOD__
}
class PsychGameOverClassProbe {
 static function check(ok:Bool, label:String):Void if (!ok) throw label;
 static function main():Void {
  var host = new PsychGameOverHost();
  var sourceClass = new PsychGameOverClassCompat(host, {gameOverChar:"pico-dead"});
  check(sourceClass.characterName == "pico-dead", "chart character default");
  check(host.calls.length == 0, "construction must not overwrite prior stage state");
  check(sourceClass.instance == null, "class compatibility instance must be null before death");
  var pending = {tag: "pending-substate"};
  GameOverSubstate.instance = pending;
  check(sourceClass.instance == null, "a static substate before active source death must remain hidden");
  host.sourceScoreOwner = true;
  host.isDead = true;
  check(sourceClass.instance == pending, "active source death did not expose the live GameOverSubstate instance");
  GameOverSubstate.instance = null;
  check(sourceClass.instance == null, "class compatibility instance did not clear after substate teardown");
  host.sourceScoreOwner = false;
  GameOverSubstate.instance = pending;
  check(sourceClass.instance == null, "native/non-source owner must not expose the source instance");
  host.sourceScoreOwner = true;
  GameOverSubstate.instance = null;
  var interp = new Interp();
  interp.variables.set("GameOverSubstate", sourceClass);
  interp.execute(new Parser().parseString("GameOverSubstate.deathSoundName = 'custom-loss'; GameOverSubstate.characterName = 'custom-death';"));
  check(host.calls[0] == "GameOverSubstate:deathSoundName:custom-loss", "death sound did not reach native bridge");
  check(host.calls[1] == "GameOverSubstate:characterName:custom-death", "death actor did not reach native bridge");
  check(sourceClass.deathSoundName == "custom-loss" && sourceClass.characterName == "custom-death", "source readback");
  interp.execute(new Parser().parseString("GameOverSubstate.deathDelay = 0.15;"));
  check(host.calls[2] == "GameOverSubstate:deathDelay:0.15", "death delay did not reach native bridge");
  check(sourceClass.deathDelay == 0.15, "death delay source readback");
  sourceClass.resetVariables();
  check(sourceClass.characterName == "pico-dead" && sourceClass.deathSoundName == "fnf_loss_sfx", "source defaults");
  check(sourceClass.deathDelay == 0, "death delay did not reset");
  check(host.calls[host.calls.length - 1] == "GameOverSubstate:deathDelay:0", "reset did not clear native delay");
  var invalid = false;
  try sourceClass.deathDelay = -0.15 catch (error:Dynamic)
   invalid = Std.string(error).indexOf("finite nonnegative number") >= 0;
  check(invalid, "negative death delay was accepted");
 }
}''', encoding="utf-8", newline='\n')
            source_path = path / "PsychGameOverClassProbe.hx"
            source_path.write_text(source_path.read_text(encoding="utf-8").replace(
                "__SOURCE_INSTANCE_METHOD__", source_instance_method), encoding="utf-8", newline="\n")
            env = dict(os.environ)
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(path), "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "--run", "PsychGameOverClassProbe"],
                cwd=ROOT, env=env, text=True, capture_output=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_nightmare_gameover_updates_keep_source_clock_and_paired_phases(self):
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        game_over = (ROOT / "source/GameOverSubstate.hx").read_text(encoding="utf-8")
        self.assertIn(
            "dispatchSourceGameOverUpdateBeforeSuper(elapsed);\n\t\t\tsuper.update(elapsed);\n\t\t\tdispatchSourceGameOverUpdateAfterSuper(elapsed);",
            game_over,
            "source game-over update lost its before/after-super callback order",
        )
        self.assertIn("dispatchSourceGameOverUpdatePost(elapsed);", game_over)
        self.assertIn("if (sourceMode == 2 && sourceOwner != null)", game_over)
        self.assertIn("if (sourceMode == 1 && sourceOwner != null)", game_over)
        mode_match = re.search(r"@:keep public function sourceGameOverMode\(\):Int[^\n]+", play_state)
        self.assertIsNotNone(mode_match, "PlayState sourceGameOverMode contract is missing")
        methods = [mode_match.group().replace("@:keep ", "", 1)]
        for marker in (
            "@:keep public function sourceGameOverCall",
            "function dispatchNightmareVisionUpdatePost",
            "@:keep public function sourceGameOverSetInGameOver",
        ):
            method = extract_method(play_state, marker)
            method = method.replace("@:keep ", "", 1)
            methods.append(method)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder)
            fixture = r'''class NightmareVisionFlxGView {
 public static var captures:Int = 0;
 public static var active:Bool = false;
 public static var tickElapsed:Float = 0;
 public static var phases:Array<String> = [];
 public static var finished:Array<Int> = [];
 public static function captureSourceFrame(_clock:CompatScriptClock):Void captures++;
 public static function runSourceTick(clock:CompatScriptClock, index:Int, count:Int,
     callback:Void->Void):Void {
  if (active) throw "source tick context was nested";
  active = true;
  tickElapsed = clock.tickElapsed;
  phases.push(index + "/" + count);
  callback();
  active = false;
 }
 public static function finishSourceBatch(_clock:CompatScriptClock, count:Int):Void finished.push(count);
}
class PsychRuntimeBindings {
 public static var nextResult:Dynamic;
 public static var lastHost:Dynamic;
 public static var lastName:String;
 public static var lastArgs:Array<Dynamic>;
 public static var lastExcludedScopeKeys:Array<String>;
 public static var lastEligibleScopes:Array<String>;
 public static var availableScopes:Array<String> = ["selected-chart-global", "engine-results-provider"];
 public static function dispatch(host:Dynamic, name:String, args:Array<Dynamic>,
     family:String = "Scripts", ignoreStops:Bool = false, ?hscriptArgs:Array<Dynamic>,
     ?excludedScopeKeys:Array<String>):Dynamic {
  lastHost = host; lastName = name; lastArgs = args;
  lastExcludedScopeKeys = excludedScopeKeys;
  lastEligibleScopes = [for (scope in availableScopes)
   if (excludedScopeKeys == null || excludedScopeKeys.indexOf(scope) < 0) scope];
  return nextResult;
 }
}
class FakeNightmareGroup {
 public var writes:Map<String, Dynamic> = new Map();
 public function new() {}
 public function set(name:String, value:Dynamic):Void writes.set(name, value);
}
class FakeNightmareScripts { public var group:FakeNightmareGroup; public function new() group = new FakeNightmareGroup(); }
class FakeInterp { public var variables:Map<String, Dynamic> = new Map(); }
class NightmareGameOverBridgeProbe {
__METHODS__
 var sourceScoreOwner:Bool = true;
 var sourceScoreNightmare:Bool = true;
 var defaultPsychGlobalScopes:Array<String> = ["engine-results-provider"];
 var inGameOver:Bool = false;
 var compatScriptClock:CompatScriptClock = new CompatScriptClock();
 var sourceGameOverBatch:CompatScriptTickBatch;
 var nightmareVisionScripts:FakeNightmareScripts = new FakeNightmareScripts();
 var hscriptStates:Array<FakeInterp> = [];
 public var callbackResult:Dynamic;
 public var callbacks:Array<{name:String, args:Array<Dynamic>}> = [];
 public function new() {}
 public function callNightmareVision(name:String, args:Array<Dynamic>):Dynamic {
  if ((name == "onUpdate" || name == "onUpdatePost") && !NightmareVisionFlxGView.active)
   throw "NV game-over update escaped its source FlxG tick context";
  callbacks.push({name:name, args:args.copy()});
  return callbackResult;
 }
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var host = new NightmareGameOverBridgeProbe();
  host.sourceGameOverCall("onUpdate", [1 / 120]);
  host.sourceGameOverCall("onUpdatePost", []);
  check(host.callbacks.length == 0, "half tick was dispatched per render frame");
  host.sourceGameOverSetInGameOver(true);
  check(host.inGameOver && host.nightmareVisionScripts.group.writes.get("inGameOver") == true,
   "accepted game-over did not publish inGameOver to the NV group");
  host.sourceGameOverCall("onUpdate", [1 / 120]);
  host.sourceGameOverCall("onUpdatePost", []);
  check(host.callbacks.length == 0, "game-over entry kept stale gameplay clock phase");
  host.sourceGameOverCall("onUpdate", [1 / 120]);
  host.sourceGameOverCall("onUpdatePost", []);
  check(host.callbacks.length == 2, "source clock did not dispatch one update/post pair at 60 Hz");
  check(host.callbacks[0].name == "onUpdate" && host.callbacks[1].name == "onUpdatePost",
   "NV update and post callbacks were not paired in order");
  check(Math.abs((host.callbacks[0].args[0]:Float) - 1 / 60) < 0.000001
      && Math.abs((host.callbacks[1].args[0]:Float) - 1 / 60) < 0.000001,
   "source callback elapsed did not stay fixed at 1/60 second");
  check(NightmareVisionFlxGView.captures == 3,
   "native key snapshots were not captured once per game-over render frame");
  check(NightmareVisionFlxGView.phases.join(",") == "0/1,0/1",
   "update and post did not run in matching source tick contexts");
  check(NightmareVisionFlxGView.finished.join(",") == "0,0,1",
   "source input batch was not finished once for every paired game-over frame");
  var nvResult = {label: "continue"};
  host.callbackResult = nvResult;
  check(host.sourceGameOverCall("onGameOverStart", ["payload"]) == nvResult
      && host.callbacks[host.callbacks.length - 1].name == "onGameOverStart",
   "NV non-update game-over hook did not preserve its exact return value");
  host.sourceScoreNightmare = false;
  var psychResult = {label: "stop"};
  PsychRuntimeBindings.nextResult = psychResult;
  var psychArgs = ["psych-payload"];
  check(host.sourceGameOverCall("onGameOverStart", psychArgs) == psychResult
      && PsychRuntimeBindings.lastHost == host && PsychRuntimeBindings.lastName == "onGameOverStart"
      && PsychRuntimeBindings.lastArgs == psychArgs
      && PsychRuntimeBindings.lastExcludedScopeKeys == host.defaultPsychGlobalScopes,
   "Psych game-over hook did not preserve direct donor dispatch and return");
  check(PsychRuntimeBindings.lastEligibleScopes.join(",") == "selected-chart-global",
   "excluding the engine observer also excluded selected chart scopes");
 }
}'''.replace("__METHODS__", "\n".join(methods))
            (path / "NightmareGameOverBridgeProbe.hx").write_text(fixture, encoding="utf-8", newline="\n")
            env = dict(os.environ)
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(path),
                 "-main", "NightmareGameOverBridgeProbe", "--interp"],
                cwd=ROOT, env=env, text=True, capture_output=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
