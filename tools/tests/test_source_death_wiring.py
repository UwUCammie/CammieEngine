"""Execute source-owned death transitions extracted from PlayState."""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND


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


def compact(source: str) -> str:
    return "".join(source.split())


FIXTURE = r'''
class DeathTrace {
  public static var events:Array<String> = [];
  public static function add(value:String):Void events.push(value);
  public static function reset():Void events = [];
  public static function index(value:String):Int return events.indexOf(value);
}

class ScriptCallbackResult { public static inline var STOP:String = 'STOP'; }
class NightmareVisionScriptGroup { public static inline var STOP_FUNC:String = 'NV_STOP'; }

class DeathManager {
  public function new() {}
  public function clear():Void DeathTrace.add('manager.clear');
}

class FlxTimer {
  public static var globalManager:DeathManager = new DeathManager();
  public var delay:Float = 0;
  public var callback:FlxTimer->Void;
  public function new() {}
  public function start(delay:Float, callback:FlxTimer->Void):FlxTimer {
    this.delay = delay;
    this.callback = callback;
    DeathTrace.add('timer.start:' + delay);
    return this;
  }
  public function fire():Void {
    DeathTrace.add('timer.fire');
    if (callback != null) callback(this);
  }
}

class FlxTween { public static var globalManager:DeathManager = new DeathManager(); }

class DeathMusic {
  public function new() {}
  public function stop():Void DeathTrace.add('music.stop');
}
class DeathSoundSystem {
  public var music:DeathMusic = new DeathMusic();
  public function new() {}
}
class FlxG {
  public static var animationTimeScale:Float = 1;
  public static var sound:DeathSoundSystem = new DeathSoundSystem();
}

class DeathCamera {
  var storedFilters:Array<Dynamic> = [];
  public var filters(get, set):Array<Dynamic>;
  public function new() {}
  function get_filters():Array<Dynamic> return storedFilters;
  function set_filters(value:Array<Dynamic>):Array<Dynamic> {
    DeathTrace.add('camera.filters');
    storedFilters = value;
    return value;
  }
}
class DeathCameraPosition {
  public function new() {}
  public function cancel():Void DeathTrace.add('camera.cancel');
}
class Character {
  public var stunned:Bool = false;
  public function new() {}
}
class DeathField { public var owner:Character; public function new(owner:Character) this.owner = owner; }
class GameOverSubstate { public var actor:Character; public function new(actor:Character) this.actor = actor; }

class PsychRuntimeBindings {
  public static function dispatch(host:Dynamic, name:String, args:Array<Dynamic>,
      family:String = 'Scripts', ignoreStops:Bool = false):Dynamic {
    DeathTrace.add('callback:' + name);
    host.callbackSnapshot = [host.boyfriend.stunned, host.balls, host.paused,
      host.persistentUpdate, host.persistentDraw];
    host.callbackArgs = args;
    return host.psychResult;
  }
}

class SourceDeathWiringFixture {
  public var sourceScoreNightmare:Bool = false;
  public var health:Float = 0;
  public var sourceDeathBounds:Array<Float> = [0, 2];
  public var healthBounds:Dynamic = {min: 0.0, max: 2.0};
  public var instakillOnMiss:Bool = false;
  public var practiceMode:Bool = false;
  public var isDead:Bool = false;
  public var gameOverTimer:FlxTimer;
  public var cpuControlled:Bool = false;
  public var boyfriend:Character = new Character();
  public var nightmareOwner:Character = new Character();
  public var fieldAvailable:Bool = true;
  public var balls:Int = 0;
  public var paused:Bool = false;
  public var canPause:Bool = true;
  public var canResync:Bool = true;
  public var persistentUpdate:Bool = true;
  public var persistentDraw:Bool = true;
  public var psychGameOverTransitionPending:Bool = false;
  public var psychDelay:Float = 0;
  public var psychResult:Dynamic = null;
  public var nightmareResult:Dynamic = null;
  public var callbackSnapshot:Array<Dynamic>;
  public var callbackArgs:Array<Dynamic>;
  public var vocalsStops:Int = 0;
  public var openedGameOver:GameOverSubstate;
  public var camGame:DeathCamera = new DeathCamera();
  public var curCamPos:DeathCameraPosition = new DeathCameraPosition();
  public function new() {}
  public function sourceScoreLedgerActive():Bool return true;
  public function callNightmareVision(name:String, args:Array<Dynamic>):Dynamic {
    DeathTrace.add('callback:' + name);
    callbackSnapshot = [nightmareOwner.stunned, balls, paused, persistentUpdate, persistentDraw];
    callbackArgs = args;
    return nightmareResult;
  }
  public function getNightmareVisionField(index:Int):DeathField return fieldAvailable ? new DeathField(nightmareOwner) : null;
  public function psychGameOverDeathDelay():Float return psychDelay;
  public function stopVocals():Void {
    vocalsStops++;
    DeathTrace.add('vocals.stop');
  }
  public function openSubState(state:GameOverSubstate):Void {
    openedGameOver = state;
    DeathTrace.add('substate.open');
  }
  public function setAllHaxeVar(name:String, value:Dynamic):Void DeathTrace.add('sync:' + name);

__DO_DEATH_CHECK__

__OPEN_SOURCE_GAME_OVER__
}

class SourceDeathWiringTestMain {
  static function check(value:Bool, message:String):Void if (!value) throw message;
  static function equal<T>(actual:T, expected:T, message:String):Void
    if (actual != expected) throw message + ': ' + actual + ' != ' + expected;

  static function main():Void {
    var deferred = new SourceDeathWiringFixture();deferred.sourceScoreNightmare = true;deferred.fieldAvailable = false;
    deferred.nightmareResult = NightmareVisionScriptGroup.STOP_FUNC;
    check(!deferred.doDeathCheck() && !deferred.boyfriend.stunned && deferred.balls == 0,
      'stopped deferred death preserves callback and transition ordering');
    deferred.nightmareResult = 0;
    check(deferred.doDeathCheck() && deferred.boyfriend.stunned && deferred.balls == 1 && deferred.openedGameOver != null,
      'accepted pre-field source death uses player actor and preserves full transition');

    psychStopIsSideEffectFree();
    psychDelayKeepsMusicUntilTimer();
    nightmareStopIsSideEffectFree();
    nightmareBoundsAndImmediateTransition();
    nightmareSkipInstakillPreservesDonorPrecedence();
  }

  static function psychStopIsSideEffectFree():Void {
    DeathTrace.reset();
    var state = new SourceDeathWiringFixture();
    state.psychResult = ScriptCallbackResult.STOP;
    check(!state.doDeathCheck(), 'Psych STOP should cancel death transition');
    equal(DeathTrace.events.join(','), 'callback:onGameOver', 'STOP should precede and prevent transition effects');
    check(state.callbackSnapshot[0] == false && state.callbackSnapshot[1] == 0
      && state.callbackSnapshot[2] == false && state.callbackSnapshot[3] == true
      && state.callbackSnapshot[4] == true, 'callback must see untouched actor/counter/pause state: '
      + state.callbackSnapshot.join(','));
    check(state.balls == 0 && !state.paused && !state.boyfriend.stunned && !state.isDead,
      'STOP should leave death state untouched');
    check(state.gameOverTimer == null && state.vocalsStops == 0 && state.openedGameOver == null,
      'STOP should not create timer or stop audio/open game over');
  }

  static function psychDelayKeepsMusicUntilTimer():Void {
    DeathTrace.reset();
    var state = new SourceDeathWiringFixture();
    state.health = 0;
    state.psychDelay = 0.75;
    check(state.doDeathCheck(), 'eligible Psych death should start transition');
    check(state.callbackSnapshot[0] == false && state.callbackSnapshot[1] == 0
      && state.callbackSnapshot[2] == false && state.callbackSnapshot[3] == true
      && state.callbackSnapshot[4] == true, 'Psych callback must run before death effects');
    check(state.boyfriend.stunned && state.balls == 1 && state.paused && state.isDead,
      'Psych death should stun and mark the state immediately');
    check(!state.canPause && !state.canResync && !state.persistentUpdate && !state.persistentDraw,
      'Psych death should close gameplay update/pause gates');
    check(state.gameOverTimer != null && state.gameOverTimer.delay == 0.75,
      'Psych death delay should be retained on its timer');
    check(state.vocalsStops == 0 && state.openedGameOver == null
      && DeathTrace.index('music.stop') < 0 && DeathTrace.index('substate.open') < 0,
      'Psych audio and game-over substate should wait for the timer');
    check(DeathTrace.index('callback:onGameOver') < DeathTrace.index('manager.clear')
      && DeathTrace.index('manager.clear') < DeathTrace.index('timer.start:0.75'),
      'Psych transition order should dispatch, apply state, then start timer');

    var timer = state.gameOverTimer;
    timer.fire();
    check(state.vocalsStops == 1 && state.openedGameOver != null
      && state.openedGameOver.actor == state.boyfriend,
      'Psych timer should stop vocals and open game over for boyfriend');
    check(state.gameOverTimer == null, 'Psych timer should clear after opening game over');
    check(DeathTrace.index('timer.fire') < DeathTrace.index('vocals.stop')
      && DeathTrace.index('vocals.stop') < DeathTrace.index('music.stop')
      && DeathTrace.index('music.stop') < DeathTrace.index('substate.open'),
      'Psych delayed transition should stop audio before opening the substate');
  }

  static function nightmareBoundsAndImmediateTransition():Void {
    DeathTrace.reset();
    FlxG.animationTimeScale = 2;
    var equalBounds = new SourceDeathWiringFixture();
    equalBounds.sourceScoreNightmare = true;
    equalBounds.health = 1;
    equalBounds.healthBounds = {min: 1.0, max: 1.0};
    check(!equalBounds.doDeathCheck(), 'equal NV bounds must not trigger death');
    check(equalBounds.sourceDeathBounds[0] == 1 && equalBounds.sourceDeathBounds[1] == 1,
      'NV health bounds should be copied into reusable policy storage');
    check(DeathTrace.events.length == 0, 'equal bounds should not dispatch onGameOver');

    DeathTrace.reset();
    var inverted = new SourceDeathWiringFixture();
    inverted.sourceScoreNightmare = true;
    inverted.health = 2.5;
    inverted.healthBounds = {min: 2.0, max: 0.0};
    inverted.cpuControlled = true;
    check(inverted.doDeathCheck(), 'inverted NV bounds should trigger at health >= min');
    check(inverted.callbackSnapshot[0] == false && inverted.callbackSnapshot[1] == 0
      && inverted.callbackSnapshot[2] == false && inverted.callbackSnapshot[3] == true
      && inverted.callbackSnapshot[4] == true, 'NV callback must run before transition state');
    check(inverted.nightmareOwner.stunned && !inverted.boyfriend.stunned && inverted.balls == 1,
      'NV death should stun the field owner and increment its counter');
    check(inverted.paused && inverted.isDead && !inverted.persistentUpdate && !inverted.persistentDraw,
      'NV death should pause and mark the transition immediately');
    check(inverted.openedGameOver != null && inverted.openedGameOver.actor == inverted.nightmareOwner
      && inverted.gameOverTimer == null,
      'NV should open game over immediately for the field owner without a Psych timer');
    check(inverted.vocalsStops == 1
      && DeathTrace.index('callback:onGameOver') < DeathTrace.index('vocals.stop')
      && DeathTrace.index('vocals.stop') < DeathTrace.index('music.stop')
      && DeathTrace.index('music.stop') < DeathTrace.index('manager.clear')
      && DeathTrace.index('manager.clear') < DeathTrace.index('substate.open'),
      'NV should dispatch first, stop audio before timer cleanup, then open immediately');
    check(inverted.canPause && inverted.canResync && FlxG.animationTimeScale == 2,
      'NV should not apply Psych-only pause/resync/animation settings');
  }

  static function nightmareStopIsSideEffectFree():Void {
    DeathTrace.reset();
    var state = new SourceDeathWiringFixture();
    state.sourceScoreNightmare = true;
    state.health = 0;
    state.nightmareResult = NightmareVisionScriptGroup.STOP_FUNC;
    check(!state.doDeathCheck(), 'NV STOP_FUNC should cancel death transition');
    equal(DeathTrace.events.join(','), 'callback:onGameOver', 'NV STOP_FUNC should prevent transition effects');
    check(state.callbackSnapshot[0] == false && state.callbackSnapshot[1] == 0
      && state.callbackSnapshot[2] == false && state.callbackSnapshot[3] == true
      && state.callbackSnapshot[4] == true, 'NV callback must see untouched actor/counter/pause state');
    check(!state.nightmareOwner.stunned && !state.paused && state.balls == 0 && !state.isDead,
      'NV STOP_FUNC should leave death state untouched');
    check(state.vocalsStops == 0 && state.openedGameOver == null,
      'NV STOP_FUNC should not stop audio or open game over');
  }

  static function nightmareSkipInstakillPreservesDonorPrecedence():Void {
    DeathTrace.reset();
    var state = new SourceDeathWiringFixture();
    state.sourceScoreNightmare = true;
    state.health = 5;
    state.instakillOnMiss = true;
    state.practiceMode = true;
    state.isDead = true;
    state.cpuControlled = true;
    state.gameOverTimer = new FlxTimer();
    check(state.doDeathCheck(true),
      'NV instakill skip arm should bypass practice, isDead, timer, and CPU state');
    check(state.nightmareOwner.stunned && state.balls == 1 && state.openedGameOver != null,
      'accepted NV instakill arm should execute normal immediate transition');
  }
}
'''


class SourceDeathWiringTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.play_source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")

    def test_extracted_death_methods_preserve_source_transition_order(self):
        helpers = "\n\n".join(
            extract_method(self.play_source, marker)
            for marker in ("public function doDeathCheck(", "function openSourceGameOver(")
        )
        fixture = FIXTURE.replace("__DO_DEATH_CHECK__", helpers.split("\n\nfunction openSourceGameOver(")[0])
        # Preserve the production private method's body while removing only its declaration;
        # it is inserted adjacent to doDeathCheck inside the test host class.
        fixture = fixture.replace(
            "__OPEN_SOURCE_GAME_OVER__",
            "function openSourceGameOver(" + helpers.split("\n\nfunction openSourceGameOver(", 1)[1],
        )
        policy = (ROOT / "source/SourceDeathPolicy.hx").read_text(encoding="utf-8")

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            (work / "SourceDeathPolicy.hx").write_text(policy, encoding="utf-8", newline="\n")
            (work / "SourceDeathWiringTestMain.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "SourceDeathWiringTestMain", "--interp"],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_update_and_end_song_only_route_source_owners_through_source_death_policy(self):
        update = extract_method(self.play_source, "override public function update(")
        end_song = extract_method(self.play_source, "function endSong(")
        compact_update = compact(update)
        compact_end_song = compact(end_song)

        self.assertRegex(
            compact_update,
            re.compile(
                r"if\(sourceScoreLedgerActive\(\)\)\{if\(doDeathCheck\(\)\)return;\}"
                r"elseif\(\(health<=0&&!opponentPlayer\)\|\|\(health>=2&&opponentPlayer\)\)\{"
            ),
        )
        self.assertIn("boyfriend.stunned=true;balls+=1;", compact_update)
        self.assertIn(
            "if(sourceScoreLedgerActive()&&doDeathCheck())return;resetDemoPlaybackRate();",
            compact_end_song,
        )
        self.assertIn("if(force){", compact_end_song)
        self.assertIn("varcodenameSongEndEvent=newCodenameGameEvent();", compact_end_song)
        self.assertIn("if(callNightmareVision('onEndSong',[])==NightmareVisionScriptGroup.STOP_FUNC)",
                      compact_end_song)


if __name__ == "__main__":
    unittest.main()
