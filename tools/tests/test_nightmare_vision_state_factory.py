"""Constructor-based NV state redirect and transition restoration contracts."""
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionStateFactoryTest(unittest.TestCase):
    def test_core_keeps_owner_resolution_and_engine_classes_behind_typed_host(self):
        source = (ROOT / "source/NightmareVisionStateFactory.hx").read_text(encoding="utf-8")
        self.assertIn("interface INightmareVisionStateFactoryHost", source)
        self.assertIn("stateRedirectPath(requestedName:String):Null<String>", source)
        self.assertIn("makeScriptState(ownerPath:String):Dynamic", source)
        self.assertIn("destroyState(state:Dynamic):Void", source)
        self.assertIn("afterPostStateSwitch(callback:Void->Void):Void", source)
        self.assertIn("public function resetState()", source)
        self.assertIn("public function switchWithTransitions(", source)
        self.assertNotIn("flixel.", source)
        self.assertNotIn("old-dsides", source)
        self.assertNotIn("new-dsides", source)

    def test_recording_host_redirect_reset_nested_request_null_and_transitions(self):
        main = r'''
import NightmareVisionStateFactory.INightmareVisionStateFactoryHost;
import NightmareVisionStateFactory.NightmareVisionStateFactoryResult;
import NightmareVisionStateFactory.NightmareVisionStateTransitionOverrides;

class NativeTitleState { public function new() {} }
class NativeMenuState { public function new() {} }
class ScriptedState { public function new() {} }

class RecordingHost implements INightmareVisionStateFactoryHost {
 public var calls:Array<String> = [];
 public var redirects:Map<String,String> = new Map();
 public var existing:Map<String,Bool> = new Map();
 public var missing:Array<String> = [];
 public var transitionCallbacks:Array<Void->Void> = [];
 public var transitions:NightmareVisionStateTransitionOverrides = {
  transitionIn:'native-in', transitionOut:'native-out'
 };
 public var onLoad:Void->Void;
 public function new() {}
 public function requestedStateName(state:Dynamic):String {
  calls.push('name');
  if (Std.isOfType(state, NativeTitleState)) return 'TitleState';
  if (Std.isOfType(state, NativeMenuState)) return 'MainMenuState';
  return '';
 }
 public function stateRedirectPath(name:String):Null<String> {
  calls.push('path:' + name);
  return redirects.get(name);
 }
 public function scriptExists(path:String):Bool {
  calls.push('exists:' + path);
  return existing.exists(path) && existing.get(path);
 }
 public function makeScriptState(path:String):Dynamic {
  calls.push('make:' + path);
  calls.push('bind');
  calls.push('onLoad');
  if (onLoad != null) onLoad();
  return new ScriptedState();
 }
 public function destroyState(state:Dynamic):Void calls.push('destroy');
 public function warnMissingRedirect(name:String, path:String):Void {
  calls.push('warn:' + name + ':' + path);
  missing.push(path);
 }
 public function getTransitionOverrides():NightmareVisionStateTransitionOverrides
  return {transitionIn:transitions.transitionIn, transitionOut:transitions.transitionOut};
 public function setTransitionOverrides(value:NightmareVisionStateTransitionOverrides):Void {
  transitions = {transitionIn:value.transitionIn, transitionOut:value.transitionOut};
  calls.push('transitions:' + Std.string(value.transitionIn) + ':' + Std.string(value.transitionOut));
 }
 public function afterPostStateSwitch(callback:Void->Void):Void {
  calls.push('post-callback-registered');
  transitionCallbacks.push(callback);
 }
}

class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function hasCalls(calls:Array<String>, expected:Array<String>):Bool {
  for (entry in expected) if (calls.indexOf(entry) < 0) return false;
  return true;
 }
 static function main():Void {
  var host = new RecordingHost();
  host.redirects.set('TitleState', 'owner/scripts/states/TitleState.hscript');
  host.existing.set('owner/scripts/states/TitleState.hscript', true);
  var factory = new NightmareVisionStateFactory(host);
  var nativeBuilds = 0;
  var result = factory.construct(function():Dynamic {
   nativeBuilds++;
   host.calls.push('native-construct');
   return new NativeTitleState();
  });
  check(result.redirected && Std.isOfType(result.state, ScriptedState),
   'existing selected-owner redirect should materialize a scripted state');
  check(hasCalls(host.calls, [
   'native-construct', 'name', 'path:TitleState',
   'exists:owner/scripts/states/TitleState.hscript', 'destroy',
   'make:owner/scripts/states/TitleState.hscript', 'bind', 'onLoad'
  ]), 'redirect should construct, identify, destroy, bind, then run onLoad in order');
  check(host.calls.indexOf('destroy') < host.calls.indexOf('make:owner/scripts/states/TitleState.hscript'),
   'the requested native state must be destroyed before wrapper construction');
  check(factory.lastConstructor == result.constructor && factory.lastWasRedirected,
   'the resolved scripted constructor must be retained for resetState');
  host.calls.resize(0);
  var reset = factory.resetState();
  check(reset.redirected && Std.isOfType(reset.state, ScriptedState) && nativeBuilds == 1,
   'reset must call the retained redirect constructor without rebuilding the native alias');
  check(host.calls.join(',') == 'make:owner/scripts/states/TitleState.hscript,bind,onLoad',
   'reset must reconstruct the same owner-scoped wrapper directly');

  host.calls.resize(0);
  host.redirects.set('MainMenuState', 'owner/scripts/states/MainMenuState.hscript');
  host.existing.set('owner/scripts/states/MainMenuState.hscript', false);
  var nativeMenu:Dynamic = null;
  var missing = factory.construct(function():Dynamic {
   nativeMenu = new NativeMenuState();
   host.calls.push('menu-construct');
   return nativeMenu;
  });
  check(!missing.redirected && missing.state == nativeMenu && host.missing.length == 1,
   'missing configured script must warn and keep the constructed native state');
  check(host.calls.indexOf('warn:MainMenuState:owner/scripts/states/MainMenuState.hscript') >= 0
   && host.calls.indexOf('destroy') < 0,
   'missing script must not destroy the requested native state');

  // Flixel also accepts a legacy state instance. Preserve the instance for the
  // initial switch but use its separate no-arg factory for reset.
  host.calls.resize(0);
  host.redirects.remove('MainMenuState');
  var legacyInstance = new NativeMenuState();
  var resetBuilds = 0;
  var legacy = factory.construct(function():Dynamic return legacyInstance, function():Dynamic {
   resetBuilds++;
   return new NativeMenuState();
  });
  check(legacy.state == legacyInstance && !legacy.redirected,
   'legacy Flixel instance should remain the first requested state');
  var legacyReset = factory.resetState();
  check(legacyReset.state != legacyInstance && Std.isOfType(legacyReset.state, NativeMenuState)
   && resetBuilds == 1,
   'legacy reset must construct a fresh state through its retained no-arg factory');

  host.calls.resize(0);
  var nullResult = factory.construct(function():Dynamic return null);
  check(nullResult.state == null && !nullResult.redirected && host.calls.length == 0,
   'a raw requested constructor returning null must stop before class or redirect lookup');
  check(factory.resetState().state == null,
   'reset of a retained constructor returning null must also remain guarded');

  // A wrapper's onLoad can request another state. The nested request becomes
  // the factory's current reset constructor even as the outer result returns.
  host.redirects.set('TitleState', 'owner/scripts/states/TitleState.hscript');
  host.existing.set('owner/scripts/states/TitleState.hscript', true);
  host.redirects.remove('MainMenuState');
  host.onLoad = function():Void {
   factory.construct(function():Dynamic return new NativeMenuState());
  };
  var outer = factory.construct(function():Dynamic return new NativeTitleState());
  check(outer.redirected && !factory.lastWasRedirected,
   'nested onLoad state request must take precedence for subsequent reset');
  var nestedReset = factory.resetState();
  check(Std.isOfType(nestedReset.state, NativeMenuState) && !nestedReset.redirected,
   'reset must preserve the nested request selected during onLoad');

  host.onLoad = null;
  host.calls.resize(0);
  host.transitions = {transitionIn:'native-in', transitionOut:'native-out'};
  var requestResult = factory.switchWithTransitions('temporary-in', 'temporary-out', function():Dynamic {
   check(host.transitions.transitionIn == 'temporary-in' && host.transitions.transitionOut == 'temporary-out',
    'temporary transitions must be active during the state request');
   check(host.transitionCallbacks.length == 0,
    'postStateSwitch restoration must be registered after the state request');
   host.calls.push('switch-request');
   return 'switched';
  });
  check(requestResult == 'switched' && host.transitions.transitionIn == 'temporary-in',
   'temporary transitions remain active through state construction');
  check(host.calls.indexOf('switch-request') < host.calls.indexOf('post-callback-registered'),
   'CoolUtil registers restoration only after FlxG.switchState returns');
  host.transitionCallbacks[host.transitionCallbacks.length - 1]();
  check(host.transitions.transitionIn == 'native-in' && host.transitions.transitionOut == 'native-out',
   'post-switch restores both captured transition globals');

  host.transitionCallbacks.resize(0);
  host.transitions = {transitionIn:'native-in', transitionOut:'native-out'};
  factory.switchWithTransitions('outer-in', 'outer-out', function():Dynamic {
   return factory.switchWithTransitions('inner-in', 'inner-out', function():Dynamic {
    check(host.transitions.transitionIn == 'inner-in', 'nested request must see its own transition pair');
    return 'nested';
   });
  });
  check(host.transitionCallbacks.length == 2,
   'each nested CoolUtil request registers an independent post-switch callback');
  host.transitionCallbacks[0]();
  check(host.transitions.transitionIn == 'outer-in',
   'callbacks restore their own captured transition pair in registration order');
  host.transitionCallbacks[1]();
  check(host.transitions.transitionIn == 'native-in' && host.transitions.transitionOut == 'native-out',
   'the final registered callback restores the base transition pair');

  var thrown = false;
  try factory.switchWithTransitions('throw-in', 'throw-out', function():Dynamic throw 'switch-failed')
  catch (_:Dynamic) thrown = true;
  check(thrown && host.transitions.transitionIn == 'throw-in' && host.transitions.transitionOut == 'throw-out',
   'a thrown switch request occurs before donor postStateSwitch restoration registration');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(main, encoding="utf-8")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--main", "Main", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
