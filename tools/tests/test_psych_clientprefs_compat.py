"""Psych ClientPrefs source bindings follow the active owner preference view."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


def haxe_env():
    env = dict(os.environ)
    env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
    env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
    env["PATH"] = os.pathsep.join(
        [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
    )
    return env


KEYS = r'''package flixel.input.keyboard;
enum abstract FlxKey(Int) from Int to Int {
 var NONE=-1; var A=65; var B=66; var D=68; var R=82; var S=83; var W=87;
 var ZERO=48; var SEVEN=55; var EIGHT=56; var SPACE=32; var ENTER=13;
 var BACKSPACE=8; var ESCAPE=27; var PLUS=187; var MINUS=189;
 var UP=38; var DOWN=40; var LEFT=37; var RIGHT=39;
 var NUMPADPLUS=107; var NUMPADMINUS=109;
}'''

GAMEPAD = r'''package flixel.input.gamepad;
enum abstract FlxGamepadInputID(Int) from Int to Int {
 var NONE=-1; var A=0; var B=1; var X=2; var Y=3; var BACK=6; var START=7;
 var DPAD_UP=11; var DPAD_DOWN=12; var DPAD_LEFT=13; var DPAD_RIGHT=14;
 var LEFT_STICK_DIGITAL_UP=34; var LEFT_STICK_DIGITAL_DOWN=35;
 var LEFT_STICK_DIGITAL_LEFT=36; var LEFT_STICK_DIGITAL_RIGHT=37;
}'''


class PsychClientPrefsCompatTest(unittest.TestCase):
    def test_owner_class_string_paths_and_static_bridge_follow_active_owner(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            owner = base / "owner"
            module = owner / "source/demo/PrefsProbe.hx"
            module.parent.mkdir(parents=True)
            module.write_text(
                """package demo;
import backend.ClientPrefs;
using StringTools;
class PrefsProbe {
	public function new() {}
	public function noteSkin():String { return ClientPrefs.data.noteSkin.trim(); }
	public function defaultSkin():String { return ClientPrefs.defaultData.noteSkin.trim(); }
	public function lowQuality():Bool { return ClientPrefs.data.lowQuality; }
	public function antialiasing():Bool { return ClientPrefs.data.antialiasing; }
	public function shaders():Bool { return ClientPrefs.data.shaders; }
	public function mutate():Void {
		ClientPrefs.data.noteSkin = 'changed';
		ClientPrefs.data.lowQuality = false;
		ClientPrefs.data.antialiasing = true;
		ClientPrefs.data.shaders = true;
		ClientPrefs.defaultData.noteSkin = 'changed';
	}
}
""",
                encoding="utf-8",
                newline="\n",
            )
            (base / "Main.hx").write_text(
                r"""class MemoryOwnerSave {
 public function new() {}
 public function getField(_name:String):Dynamic return null;
 public function setField(_name:String, _value:Dynamic):Void {}
 public function flush():Void {}
}
class PlayState {
 public static var instance:PlayState;
 public var psychClientPrefs:PsychOwnerClientPrefs;
 public function new(prefs:PsychOwnerClientPrefs) psychClientPrefs = prefs;
}
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var native:Dynamic={antialiasing:false,gameplayShaders:false};
  var prefs=new PsychOwnerClientPrefs('assets/imported_mods/compat-a',new MemoryOwnerSave(),native);
  prefs.data.noteSkin='  Initial  ';
  prefs.data.lowQuality=true;
  prefs.defaultData.noteSkin='  Default  ';
  var paths:Array<String>=cast Reflect.getProperty(prefs,'__hscriptStringFieldPaths');
  if(paths.indexOf('data.noteSkin')<0 || paths.indexOf('defaultData.noteSkin')<0)
   throw 'owner-bound ClientPrefs string field metadata is missing';

  var bindings:Map<String,Dynamic>=new Map();
  bindings.set('ClientPrefs',prefs);
  bindings.set('backend.ClientPrefs',prefs);
  var loaded=CodenameScriptClassLoader.load(Sys.args()[0],['demo.PrefsProbe'],bindings,new Map());
  if(loaded.diagnostics.length!=0) throw 'owner ClientPrefs source binding failed: '+loaded.diagnostics;
  var probe=loaded.scope.createInstance('PrefsProbe',[]);
  if(probe==null || probe.callFunction('noteSkin',[])!='Initial'
   || probe.callFunction('defaultSkin',[])!='Default'
   || Std.string(probe.callFunction('lowQuality',[]))!='true'
   || Std.string(probe.callFunction('antialiasing',[]))!='false'
   || Std.string(probe.callFunction('shaders',[]))!='false')
   throw 'owner-backed ClientPrefs fields or StringTools receiver paths were not exposed';
  probe.callFunction('mutate',[]);
  if(prefs.data.noteSkin!='changed' || prefs.defaultData.noteSkin!='changed'
   || prefs.data.lowQuality!=false || prefs.data.antialiasing!=true || prefs.data.shaders!=true
   || native.antialiasing!=false || native.gameplayShaders!=false)
   throw 'owner script writes did not mutate only its preference view';

  var play=new PlayState(prefs);
  PlayState.instance=play;
  if(PsychClientPrefsCompat.data!=prefs.data || PsychClientPrefsCompat.defaultData!=prefs.defaultData)
   throw 'static ClientPrefs bridge did not expose the current owner objects';
  var replacement:Dynamic={noteSkin:'replacement'};
  PsychClientPrefsCompat.data=replacement;
  if(prefs.data!=replacement) throw 'static ClientPrefs setter did not reach the current owner';
  var next=new PsychOwnerClientPrefs('assets/imported_mods/compat-b',new MemoryOwnerSave());
  play.psychClientPrefs=next;
  if(PsychClientPrefsCompat.data!=next.data)
   throw 'static ClientPrefs bridge stayed pinned to a previous owner';
  PlayState.instance=null;
  var detached=PsychClientPrefsCompat.data;
  if(detached!=PsychClientPrefsCompat.data) throw 'standalone fallback was not stable';
  loaded.scope.release(); prefs.release(); next.release();
 }
}""",
                encoding="utf-8",
                newline="\n",
            )
            keyboard = base / "flixel/input/keyboard/FlxKey.hx"
            gamepad = base / "flixel/input/gamepad/FlxGamepadInputID.hx"
            keyboard.parent.mkdir(parents=True, exist_ok=True)
            gamepad.parent.mkdir(parents=True, exist_ok=True)
            keyboard.write_text(KEYS, encoding="utf-8", newline="\n")
            gamepad.write_text(GAMEPAD, encoding="utf-8", newline="\n")
            command = [
                *HAXE_COMMAND,
                "-cp",
                str(ROOT / "source"),
                "-cp",
                str(base),
                "-cp",
                str(ROOT / ".haxelib/hscript/2,5,0"),
                "-cp",
                str(ROOT / ".haxelib/hscript-ex/git/src"),
                "--run",
                "Main",
                str(owner),
            ]
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=haxe_env(),
                text=True,
                capture_output=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
