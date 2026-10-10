"""Native lifecycle bridge for owner ScriptClass FlxBasic members."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
FLIXEL_ARGS = [
    "-lib", "openfl", "-lib", "lime", "-lib", "flixel", "-lib", "flixel-addons",
    "-lib", "flixel-animate", "-D", "FLX_STANDARD_ASSETS_DIRECTORY",
    "-D", "FLX_DEFAULT_SOUND_EXT=ogg", "-D", "FLX_SOUND_SYSTEM", "-D", "FLX_GAMEINPUT_API",
]


def haxe_env():
    env = dict(os.environ)
    env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
    env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
    env["PATH"] = os.pathsep.join(
        [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
    )
    return env


class PsychScriptClassBasicLifecycleTest(unittest.TestCase):
    def test_psych_bindings_expose_state_controls_and_transition_api(self):
        source = (ROOT / "source/PsychCompiledStageBindings.hx").read_text(encoding="utf-8")
        self.assertIn("bind(bindings, 'FlxG', PsychFlxGCompat);", source)
        self.assertIn("bind(bindings, 'Controls', PsychControlsCompat);", source)
        self.assertIn("bind(bindings, 'backend.Controls', PsychControlsCompat);", source)
        self.assertIn("bind(bindings, 'FlxTransitionableState', FlxTransitionableState);", source)
        self.assertIn(
            "bind(bindings, 'flixel.addons.transition.FlxTransitionableState', FlxTransitionableState);",
            source,
        )

    def test_state_controls_transition_bindings_and_cutscene_member_lifecycle(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            owner = base / "owner"
            module = owner / "source/demo/CutsceneProbe.hx"
            module.parent.mkdir(parents=True)
            module.write_text(
                """package demo;
import flixel.FlxBasic;
import flixel.FlxG;
import backend.Controls;
class CutsceneProbe extends FlxBasic {
	var log:Array<String>;
	var timerRemaining:Float = 0;
	var timerCallback:Void->Void;
	var holdingTime:Float = 0;
	var totalTime:Float = 0;
	public function new(outLog:Array<String>) {
		super();
		this.log = outLog;
		timer(0.3, function() log.push('timer'));
		FlxG.state.add(this);
	}
	function timer(delay:Float, callback:Void->Void):Void {
		timerRemaining = delay;
		timerCallback = callback;
	}
	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		log.push('update');
		totalTime += elapsed;
		if (timerCallback != null) {
			timerRemaining -= elapsed;
			if (timerRemaining <= 0) {
				var callback = timerCallback;
				timerCallback = null;
				callback();
			}
		}
		if (Controls.instance.pressed('accept')) holdingTime += elapsed;
		if (holdingTime >= 0.2) {
			log.push('skip');
			destroy();
			FlxG.state.remove(this);
		} else if (totalTime >= 1) {
			log.push('ended');
			destroy();
			FlxG.state.remove(this);
		}
	}
	override public function draw():Void {
		super.draw();
		log.push('draw');
	}
	override public function destroy():Void {
		log.push('destroy');
		super.destroy();
	}
}
""",
                encoding="utf-8",
             newline='\n')
            probe = base / "PsychScriptClassBasicLifecycleProbe.hx"
            probe.write_text(
                r'''import flixel.FlxBasic;
import flixel.FlxG;
import flixel.addons.transition.FlxTransitionableState;
import flixel.group.FlxGroup.FlxTypedGroup;
import PsychFlxCameraCompat.PsychFlxGCompat;

@:access(PsychControlsCompat)
class PsychScriptClassBasicLifecycleProbe {
 static function check(ok:Bool, label:String):Void if (!ok) throw label;
 static function main():Void {
  var owner=Sys.args()[0];
  var bindings:Map<String,Dynamic>=new Map();
  bindings.set('flixel.FlxBasic',FlxBasic);
  bindings.set('FlxBasic',FlxBasic);
  bindings.set('flixel.FlxG',{state:null});
  bindings.set('FlxG',bindings.get('flixel.FlxG'));
  bindings.set('backend.Controls',PsychControlsCompat);
  bindings.set('Controls',PsychControlsCompat);
  var state:FlxTypedGroup<FlxBasic>=new FlxTypedGroup<FlxBasic>();
  var psychFlxG:Dynamic={state:state};
  bindings.set('flixel.FlxG',psychFlxG);
  bindings.set('FlxG',psychFlxG);
  var symbols:Map<String,Dynamic>=new Map();
  for(name in bindings.keys()) symbols.set(name,bindings.get(name));

  var acceptDown=false;
  var nativeControls:Dynamic={checkByName:function(name:Dynamic):Bool {
   return Std.string(name)=='accept' && acceptDown;
  }};
  PsychControlsCompat._instance=new PsychControlsCompat(nativeControls);
  check(!PsychControlsCompat.instance.pressed('accept'),'controls facade starts released');
  acceptDown=true;
  check(PsychControlsCompat.instance.pressed('accept'),'controls facade reads active native action');
  check(!PsychControlsCompat.instance.pressed('back'),'controls facade forwards the requested action');
  acceptDown=false;

  check(PsychFlxGCompat.state==null,'FlxG state facade safely handles pre-state initialization');
  Reflect.setProperty(FlxTransitionableState,'skipNextTransIn',true);
  check(FlxTransitionableState.skipNextTransIn,'skipNextTransIn reaches native transition state');
  Reflect.setProperty(FlxTransitionableState,'skipNextTransIn',false);

  var loaded=CodenameScriptClassLoader.load(owner,['demo.CutsceneProbe'],bindings,symbols);
  if(loaded.diagnostics.length>0) throw 'cutscene owner class failed to load: '+loaded.diagnostics;
  var log:Array<String>=[];
  var handler=loaded.scope.createInstance('demo.CutsceneProbe',[log]);
  check(handler!=null && state.members.length==1,'FlxG.state.add inserts the owner class member');
  check(Std.isOfType(state.members[0],PsychScriptClassBasic),
   'native Flixel group stores the native lifecycle adapter');
  var handlerBridge=state.members[0];

  state.update(0.1);
  state.draw();
  check(log.indexOf('update')>=0 && log.indexOf('draw')>=0,
   'native group dispatches authored update and draw');
  check(log.indexOf('timer')<0,'source timer waits for its scheduled time');

  acceptDown=true;
  state.update(0.1);
  check(log.indexOf('timer')<0,'timer does not fire early while skip is held');
  state.update(0.1);
  check(log.indexOf('timer')>=0 && log.indexOf('skip')>=0,
   'timer and pressed accept drive the authored skip path');
  check(log.filter(function(entry:String):Bool return entry=='destroy').length==1,
   'manual cutscene removal invokes destroy once');
  check(state.members.indexOf(handlerBridge)<0 && handler!=null,
   'cutscene remove removes its owner bridge from the native group');

  acceptDown=false;
  var cleanupLog:Array<String>=[];
  var retained=loaded.scope.createInstance('demo.CutsceneProbe',[cleanupLog]);
  var retainedBridge:FlxBasic=null;
  for(member in state.members) if(member!=null && member.exists) retainedBridge=member;
  check(retained!=null && retainedBridge!=null && retainedBridge!=handlerBridge,
   'second owner member remains live before release');
  loaded.scope.release();
  check(cleanupLog.join(',')=='destroy','owner-scope release destroys retained script members');
  check(!retainedBridge.exists,
   'owner cleanup leaves no active native wrapper');
 }
}''',
                encoding="utf-8",
             newline='\n')
            command = [
                *HAXE_COMMAND,
                "-cp", str(ROOT / "source"), "-cp", str(base),
                "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), *FLIXEL_ARGS,
                "--run", "PsychScriptClassBasicLifecycleProbe", str(owner),
            ]
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=haxe_env(),
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
