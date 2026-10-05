"""Exercise owner-local NMV input scopes through real Iris source bindings."""
import os
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_source_camera_reflection import FLIXEL_ARGS


ROOT = Path(__file__).resolve().parents[2]
IRIS = ROOT / ".haxelib/hscript-iris/1,1,3"


FIXTURES = {
    "Character.hx": '''package;
class Character { public var animation:InputProbeAnimation=new InputProbeAnimation(); }
class InputProbeAnimation {
 public var onFrameChange:Dynamic=null;
 public var onFinish:Dynamic=null;
 public var onLoop:Dynamic=null;
 public function new() {}
}
''',
    "NightmareVisionPlayableSongOwner.hx": '''package;
interface NightmareVisionPlayableSongOwner { public function nightmareVisionAudioView():Dynamic; }
''',
    "PsychBaseStageActorGroupCompat.hx": '''package;
class PsychBaseStageActorGroupCompat { public var zIndex:Int=0; public function new() {} }
''',
    "HxcCompatRuntime.hx": '''package;
class HxcCompatRuntime {
 public static function getZIndex(_object:Dynamic):Dynamic return 0;
 public static function setZIndex(_object:Dynamic,value:Dynamic):Dynamic return value;
}
''',
    "NightmareVisionFlxGView.hx": '''package;
class NightmareVisionFlxGView {
 public function getField(_field:String):Dynamic return null;
 public function setField(_field:String,value:Dynamic):Dynamic return value;
}
''',
    "NightmareVisionSaveData.hx": '''package;
class NightmareVisionSaveData {
 public function getField(_field:String):Dynamic return null;
 public function setField(_field:String,value:Dynamic):Dynamic return value;
}
''',
    "NightmareVisionSaveFacade.hx": '''package;
class NightmareVisionSaveFacade {
 public function new(_ownerRoot:String,_storage:Dynamic) {}
 public function release():Void {}
}
''',
}


MAIN = r'''import crowplexus.hscript.Parser;
import flixel.input.keyboard.FlxKey;
import nightmarevision.input.NightmareVisionInputEnums.Action;
import nightmarevision.input.NightmareVisionInputEnums.Control;
import nightmarevision.input.NightmareVisionInputEnums.Device;
import nightmarevision.input.NightmareVisionInputEnums.KeyboardScheme;
import NightmareVisionInputScope;
import NightmareVisionInputBindings;
import NightmareVisionInputSystem;

class MemoryOwnerSave {
 public var values:Dynamic = {};
 public function new() {}
 public function getField(name:String):Dynamic return Reflect.field(values, name);
 public function setField(name:String, value:Dynamic):Dynamic {
  Reflect.setField(values, name, value);
  return value;
 }
 public function flush():Void {}
}

class InputProbeHost {
 public var controls:Dynamic;
 public var input:Dynamic;
 public function new() { controls = null; input = null; }
}

class Main {
 static function fail(message:String):Void throw message;
 static function check(value:Bool, message:String):Void if (!value) fail(message);
 static function eq(actual:Dynamic, expected:Dynamic, message:String):Void
  if (actual != expected) fail(message + ': expected ' + expected + ', got ' + actual);

 static function main():Void {
  var rootA = 'assets/imported_mods/author-a';
  var rootB = 'assets/imported_mods/author-b';
  var prefsA = new NightmareVisionClientPrefs(rootA, new MemoryOwnerSave());
  var prefsB = new NightmareVisionClientPrefs(rootB, new MemoryOwnerSave());
  var scopeA = new NightmareVisionInputScope(rootA, prefsA.view, false);
  var scopeB = new NightmareVisionInputScope(rootB, prefsB.view, false);
  var scopes:Map<String, NightmareVisionInputScope> = new Map();
  scopes.set(rootA, scopeA); scopes.set(rootB, scopeB);
  var hostA = new InputProbeHost(); var hostB = new InputProbeHost();
  var hosts:Map<String, Dynamic> = new Map();
  hosts.set(rootA, hostA); hosts.set(rootB, hostB);
  var resolve = function(owner:String):NightmareVisionInputScope return scopes.get(owner);
  var resolveHost = function(owner:String):Dynamic return hosts.get(owner);
  var parser = new Parser(); parser.allowTypes = true; parser.allowMetadata = true;
  var interpA = new NightmareVisionScriptInterp();
  var interpB = new NightmareVisionScriptInterp();
  interpA.variables.set('host', hostA); interpB.variables.set('host', hostB);
  NightmareVisionInputBindings.install(interpA, rootA, resolve, resolveHost);
  NightmareVisionInputBindings.install(interpB, rootB, resolve, resolveHost);

  var originalControlsA = scopeA.controls;
  var originalInputA = scopeA.input;
  check(originalControlsA.actions.get(Action.NOTE_LEFT) != null,
   'scope construction must pass actual owner ClientPrefs key binds into Controls');
  eq(originalControlsA.getInputsFor(Control.NOTE_LEFT, Keys).join(','), '65,37',
   'owner A starts with source preference key binds');
  interpA.execute(parser.parseString(
   'import funkin.input.Controls; import funkin.input.InputSystem; '
   + 'bareControlsBefore=controls; bareInputBefore=input; '
   + 'madeA=new Controls("script-controls-A", KeyboardScheme.None); '
   + 'Controls.instance=madeA; staticControlsA=Controls.instance; '
   + 'targetControlsA=host.controls; '
   + 'madeSystemA=new InputSystem(madeA); host.input=madeSystemA; targetSetterObserved=input; '
   + 'bareReplacementA=new InputSystem(madeA); input=bareReplacementA; '
   + 'bareInputAfter=input; targetInputAfter=host.input;'));
  var madeA:Dynamic = interpA.variables.get('madeA');
  var madeSystemA:Dynamic = interpA.variables.get('madeSystemA');
  var bareReplacementA:Dynamic = interpA.variables.get('bareReplacementA');
  eq(interpA.variables.get('bareControlsBefore'), originalControlsA,
   'bare controls getter did not read owner A live state');
  eq(interpA.variables.get('bareInputBefore'), originalInputA,
   'bare input getter did not read owner A live state');
  check(Std.isOfType(madeA, NightmareVisionControls),
   'Controls constructor was intercepted by the colliding native class instead of the owner factory');
  eq(scopeA.controls, madeA, 'Controls.instance setter did not write into owner A');
  eq(interpA.variables.get('staticControlsA'), madeA, 'Controls.instance getter lost Controls identity');
  eq(interpA.variables.get('targetControlsA'), madeA,
   'target-object controls getter did not resolve the owner property');
  check(Std.isOfType(madeSystemA, NightmareVisionInputSystem),
   'InputSystem constructor was not routed through owner A');
  eq(madeSystemA.controls, madeA, 'InputSystem constructor lost its exact Controls argument');
  eq(interpA.variables.get('targetSetterObserved'), madeSystemA,
   'target-object input setter did not write through to the bare live property');
  eq(scopeA.input, bareReplacementA, 'bare input setter did not write into owner A');
  eq(interpA.variables.get('bareInputAfter'), bareReplacementA,
   'bare input getter did not observe the new owner input');
  eq(interpA.variables.get('targetInputAfter'), bareReplacementA,
   'target-object input getter did not observe the setter');

  interpB.execute(parser.parseString(
   'import funkin.input.Controls; import funkin.input.InputSystem; '
   + 'madeB=new funkin.input.Controls("script-controls-B", KeyboardScheme.None); '
   + 'Controls.instance=madeB; systemB=new InputSystem(madeB); input=systemB; '
   + 'staticControlsB=Controls.instance; targetControlsB=host.controls;'));
  var madeB:Dynamic = interpB.variables.get('madeB');
  var systemB:Dynamic = interpB.variables.get('systemB');
  check(Std.isOfType(madeB, NightmareVisionControls),
   'qualified Controls constructor bypassed owner B factory');
  check(madeB != madeA && scopeB.controls == madeB && scopeA.controls == madeA,
   'owner B Controls view crossed into owner A');
  check(systemB != madeSystemA && systemB.controls == madeB && scopeB.input == systemB,
   'owner B InputSystem factory or input setter crossed owners');
  eq(interpB.variables.get('staticControlsB'), madeB, 'owner B class view has the wrong identity');
  eq(interpB.variables.get('targetControlsB'), madeB, 'owner B target getter resolved another scene');
  eq(scopeB.actionList.join(','), 'note_left,note_down,note_up,note_right',
   'owner B action list starts from the source defaults');

  // Static-looking ACTION_LIST belongs to each owner and is captured per system.
  interpA.execute(parser.parseString(
   'InputSystem.ACTION_LIST=[Action.NOTE_RIGHT,Action.NOTE_LEFT];'));
  eq(scopeA.actionList.join(','), 'note_right,note_left', 'owner A action list write-through');
  eq(scopeB.actionList.join(','), 'note_left,note_down,note_up,note_right',
   'owner A ACTION_LIST mutation leaked to owner B');
  eq(madeSystemA.pressedActions.length, 4,
   'an existing owner A system refreshed its captured action list after replacement');
  interpA.execute(parser.parseString(
   'orderedSystemA=new InputSystem(madeA); input=orderedSystemA;'));
  var orderedSystemA:Dynamic = interpA.variables.get('orderedSystemA');
  eq(orderedSystemA.pressedActions.length, 2, 'new owner A system did not capture the assigned action list');
  eq(orderedSystemA.pressedActions[0], madeA.actions.get(Action.NOTE_RIGHT),
   'new system did not capture the exact first action object');
  eq(orderedSystemA.pressedActions[1], madeA.actions.get(Action.NOTE_LEFT),
   'new system did not capture the exact second action object');
  interpA.execute(parser.parseString('InputSystem.ACTION_LIST=[Action.NOTE_UP];'));
  eq(orderedSystemA.pressedActions.length, 2,
   'existing InputSystem changed when the owner replaced its ACTION_LIST array');
  eq(orderedSystemA.pressedActions[0], madeA.actions.get(Action.NOTE_RIGHT),
   'existing InputSystem lost its captured action object after ACTION_LIST replacement');
  eq(scopeA.actionList.join(','), 'note_up', 'second ACTION_LIST write-through');

  // Host class views route both static mutation and init to this owner's scope.
  var beforeInit:Dynamic = scopeA.controls;
  interpA.execute(parser.parseString('Controls.init(); postInitControls=Controls.instance;'));
  var afterInit:Dynamic = interpA.variables.get('postInitControls');
  check(afterInit != beforeInit && afterInit == scopeA.controls,
   'Controls.init did not reset only owner A Controls.instance');
  eq(afterInit.name, 'player', 'Controls.init did not use the source player registry name');
  eq(afterInit.keyboardScheme, Solo, 'Controls.init did not install Solo preference binds');
  eq(scopeA.actionList.join(','), 'note_up', 'Controls.init reset the owner action-list selection');
  eq(scopeB.controls, madeB, 'owner A Controls.init changed owner B');

  // Re-applying Solo consults owner A's live preferences only.
  prefsA.view.keyBinds.set('note_left', [FlxKey.C]);
  afterInit.setKeyboardScheme(Solo);
  eq(afterInit.getInputsFor(Control.NOTE_LEFT, Keys).join(','), '67',
   'owner A controls did not read their owner-local preferences');
  scopeB.controls.setKeyboardScheme(Solo);
  eq(scopeB.controls.getInputsFor(Control.NOTE_LEFT, Keys).join(','), '65,37',
   'owner A preference edit crossed into owner B');

  var staleControl:Dynamic = scopeA.controls;
  var staleInput:Dynamic = scopeA.input;
  var staleMade:Dynamic = madeA;
  var staleSystem:Dynamic = orderedSystemA;
  staleSystem.addEventListener('inputDown', function(_):Void {}, false, 0);
  scopeA.destroy();
  eq(scopeA.controls, null, 'destroyed scope still exposes owned Controls');
  eq(scopeA.input, null, 'destroyed scope still exposes current InputSystem');
  eq(staleControl.actions.iterator().hasNext(), false,
   'scene teardown did not destroy owner-created Controls instances');
  eq(staleMade.actions.iterator().hasNext(), false,
   'scene teardown did not destroy Controls created through the script constructor');
  eq(staleSystem.controls, null, 'scene teardown retained captured Controls in an owned InputSystem');
  eq(staleSystem.pressedActions.length, 0, 'scene teardown retained captured action references');
  @:privateAccess eq(staleSystem.__eventMap, null,
   'scene teardown retained script event listeners in an owned InputSystem');
  eq(staleInput.controls, null, 'scene teardown did not release the replaced owner InputSystem');
  scopes.remove(rootA);
  var staleError = '';
  try interpA.execute(parser.parseString('staleInput=InputSystem.ACTION_LIST;'))
  catch (error:Dynamic) staleError = Std.string(error);
  check(staleError.indexOf('[nightmare-vision-input] No active input scene for owner: ' + rootA) >= 0,
   'stale owner class-view closure did not reject a destroyed scene');
  staleError = '';
  try interpA.execute(parser.parseString('staleControls=controls;'))
  catch (error:Dynamic) staleError = Std.string(error);
  check(staleError.indexOf('[nightmare-vision-input] No active input scene for owner: ' + rootA) >= 0,
   'stale bare Controls closure did not reject a destroyed scene');
  staleError = '';
  try interpA.execute(parser.parseString('staleInput=input;'))
  catch (error:Dynamic) staleError = Std.string(error);
  check(staleError.indexOf('[nightmare-vision-input] No active input scene for owner: ' + rootA) >= 0,
   'stale bare InputSystem closure did not reject a destroyed scene');

  // The action selection outlives the destroyed scene for the same import root.
  var replacementScopeA = new NightmareVisionInputScope(rootA, prefsA.view, false);
  eq(replacementScopeA.actionList.join(','), 'note_up',
   'owner action list did not persist across scenes for the same import root');
  check(replacementScopeA.input.pressedActions.length == 1
   && replacementScopeA.input.pressedActions[0] == replacementScopeA.controls.actions.get(Action.NOTE_UP),
   'replacement scene did not capture the persisted owner action list');
  replacementScopeA.destroy();
  scopeB.destroy();
  prefsA.release(); prefsB.release();
  interpA.release(); interpB.release();
  trace('NV_INPUT_SCOPE_BINDINGS_OK');
 }
}'''


class NightmareVisionInputScopeBindingsTest(unittest.TestCase):
    def test_scope_ownership_live_bindings_constructors_and_teardown(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            for name, contents in FIXTURES.items():
                (work / name).write_text(contents, encoding="utf-8", newline="\n")
            (work / "Main.hx").write_text(MAIN, encoding="utf-8", newline="\n")
            env = os.environ.copy()
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["PATH"] = os.pathsep.join((str(ROOT / ".tools/haxe"),
                                            str(ROOT / ".tools/neko"), env.get("PATH", "")))
            result = subprocess.run(
                [*HAXE_COMMAND, "-D", "flixel", "-cp", str(ROOT / "source"),
                 "-cp", str(IRIS), "-cp", str(work), *FLIXEL_ARGS,
                 "-D", "FLX_KEYBOARD", "-D", "FLX_GAMEPAD", "-D", "FLX_MOUSE",
                 "-D", "FLX_MOUSE_ADVANCED", "--interp", "-main", "Main"],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=90,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("NV_INPUT_SCOPE_BINDINGS_OK", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
