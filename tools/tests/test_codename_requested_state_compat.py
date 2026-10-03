"""Regression coverage for the legacy Codename requested-state view."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class CodenameRequestedStateCompatTest(unittest.TestCase):
    def test_known_target_lease_and_source_field_assignment(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "flixel").mkdir()
            (base / "flixel/FlxState.hx").write_text("""package flixel;
class FlxState { public function new() {} }
""", newline='\n')
            (base / "flixel/FlxG.hx").write_text("""package flixel;
class TestSignal {
 var listeners:Array<Void->Void> = [];
 public function new() {}
 public function addOnce(listener:Void->Void):Void listeners.push(listener);
 public function remove(listener:Void->Void):Void listeners.remove(listener);
 public function dispatch():Void {
  var pending = listeners.copy();
  listeners = [];
  for (listener in pending) listener();
 }
 public function count():Int return listeners.length;
}
class TestSignals { public var postStateSwitch:TestSignal; public function new() postStateSwitch = new TestSignal(); }
class FlxG {
 public static var game:Dynamic;
 public static var state:FlxState;
 public static var signals:Dynamic = new TestSignals();
}
""", newline='\n')
            (base / "CodenameRequestedStateCompat.hx").write_text(
                (ROOT / "source/CodenameRequestedStateCompat.hx").read_text()
            , newline='\n')
            (base / "Main.hx").write_text(r'''import flixel.FlxG;
import flixel.FlxState;

class Game { public var _nextState:Dynamic; public function new() {} }
class MenuState extends FlxState {}
class ImportedState extends FlxState {}
class ReplacementState extends FlxState {}

class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main() {
  var game = new Game();
  var outgoing = new MenuState();
  var imported = new ImportedState();
  FlxG.game = game;
  FlxG.state = outgoing;
  var factoryCalls = 0;
  var knownFactory:Void->FlxState = function():FlxState {
   factoryCalls++;
   return imported;
  };
  CodenameRequestedStateCompat.switchToKnownTarget(imported,
   function():Void game._nextState = knownFactory);
  check(CodenameRequestedStateCompat.getRequestedState(game) == imported,
   'known request factory was not represented by its leased concrete target');
  check(factoryCalls == 0, 'known request factory was eagerly invoked');
  check(FlxG.signals.postStateSwitch.count() == 1,
   'known target did not register post-switch cleanup');
  FlxG.signals.postStateSwitch.dispatch();
  check(CodenameRequestedStateCompat.getRequestedState(game) == knownFactory,
   'post-switch cleanup left a concrete target lease active');
  check(FlxG.signals.postStateSwitch.count() == 0,
   'one-shot post-switch cleanup listener survived dispatch');

  CodenameRequestedStateCompat.clear(game);
  var unknownFactory:Void->FlxState = function():FlxState {
   factoryCalls++;
   return new ImportedState();
  };
  game._nextState = unknownFactory;
  check(CodenameRequestedStateCompat.getRequestedState(game) == unknownFactory,
   'unknown lazy factory was not preserved as the raw request');
  check(factoryCalls == 0, 'unknown request factory was eagerly invoked');

  game._nextState = null;
  CodenameRequestedStateCompat.switchToKnownTarget(imported, function():Void {});
  check(FlxG.signals.postStateSwitch.count() == 1,
   'deferred target lease did not register cleanup');
  check(CodenameRequestedStateCompat.getRequestedState(game) == null,
   'unbound asynchronous lease was exposed before Flixel accepted its request');
  game._nextState = knownFactory;
  CodenameRequestedStateCompat.bindKnownTargetRequest(imported);
  check(CodenameRequestedStateCompat.getRequestedState(game) == imported,
   'known asynchronous request was not bound after its outro callback');
  check(factoryCalls == 0, 'asynchronous known request factory was eagerly invoked');
  CodenameRequestedStateCompat.clearKnownTarget(imported);
  check(CodenameRequestedStateCompat.getRequestedState(game) == knownFactory,
   'cancelled deferred target lease survived cleanup');
  check(FlxG.signals.postStateSwitch.count() == 0,
   'cancelled deferred target retained its cleanup listener');

  CodenameRequestedStateCompat.switchToKnownTarget(imported,
   function():Void game._nextState = knownFactory);
  FlxG.state = new ReplacementState();
  check(CodenameRequestedStateCompat.getRequestedState(game) == knownFactory,
   'lease escaped its outgoing-state scope');
  FlxG.state = outgoing;
  var replacementFactory:Void->FlxState = function():FlxState return new ReplacementState();
  game._nextState = replacementFactory;
  check(CodenameRequestedStateCompat.getRequestedState(game) == replacementFactory,
   'lease survived replacement of the native request');

  CodenameRequestedStateCompat.switchToKnownTarget(imported,
   function():Void game._nextState = knownFactory);
  var replacement = new ReplacementState();
  check(CodenameRequestedStateCompat.setRequestedState(game, replacement) == replacement,
   'legacy setter did not return the assigned value');
  check(game._nextState == replacement
   && CodenameRequestedStateCompat.getRequestedState(game) == replacement,
   'legacy setter did not write the concrete state directly');
  var assignedFactory:Void->FlxState = function():FlxState {
   factoryCalls++;
   return replacement;
  };
  check(CodenameRequestedStateCompat.setRequestedState(game, assignedFactory) == assignedFactory,
   'legacy setter changed a factory assignment');
  check(game._nextState == assignedFactory
   && CodenameRequestedStateCompat.getRequestedState(game) == assignedFactory,
   'legacy setter wrapped or replaced the supplied factory');
  check(factoryCalls == 0, 'setter eagerly invoked an assigned factory');
  CodenameRequestedStateCompat.clear();
 }
}''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(base), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_interpreter_and_known_switches_use_shared_bridge(self):
        interpreter = (ROOT / "source/CodenameScriptInterp.hx").read_text()
        loading = (ROOT / "source/LoadingState.hx").read_text()
        runtime = (ROOT / "source/CodenameModRuntime.hx").read_text()
        transition = (ROOT / "source/CodenameMusicBeatTransition.hx").read_text()
        self.assertIn("CodenameRequestedStateCompat.getRequestedState(object)", interpreter)
        self.assertIn("CodenameRequestedStateCompat.setRequestedState(object, value)", interpreter)
        self.assertIn("CodenameRequestedStateCompat.switchToKnownTarget(target", loading)
        self.assertIn("CodenameRequestedStateCompat.switchToKnownTarget(cast target", runtime)
        self.assertIn("CodenameRequestedStateCompat.switchToKnownTarget(target", transition)
        self.assertIn("CodenameRequestedStateCompat.switchToKnownTarget(newState", transition)
        self.assertIn("CodenameRequestedStateCompat.bindKnownTargetRequest(scriptTarget)", transition)
        destroy = transition[transition.index("override public function destroy():Void"):]
        self.assertIn("if (!finishing && scriptNewState != null)", destroy)
        self.assertIn("CodenameRequestedStateCompat.clearKnownTarget(scriptNewState)", destroy)
        self.assertLess(destroy.index("clearKnownTarget(scriptNewState)"),
                        destroy.index("if (runtime != null)"))
        compat = (ROOT / "source/CodenameRequestedStateCompat.hx").read_text()
        self.assertIn("FlxG.signals.postStateSwitch.addOnce(postSwitchCleanup)", compat)
        self.assertIn("FlxG.signals.postStateSwitch.remove(postSwitchCleanup)", compat)
        self.assertIn("FlxG.switchState(target);", loading)
        self.assertIn("loadAndSwitchStateFactory(target:()->FlxState)", loading)
        self.assertIn("CodenameRequestedStateCompat.getRequestedState(game)", runtime)
        factory = loading.split("public static function loadAndSwitchStateFactory", 1)[1].split(
            "public static function loadAndSwitchState", 1
        )[0]
        self.assertNotIn("switchToKnownTarget", factory)


if __name__ == "__main__":
    unittest.main()
