"""Psych ClientPrefs source binding stays detached and owner scoped."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def haxe_env():
    env = dict(os.environ)
    env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
    env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
    env["PATH"] = os.pathsep.join(
        [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
    )
    return env


class PsychClientPrefsCompatTest(unittest.TestCase):
    def test_owner_class_reads_current_options_through_detached_psych_preferences(self):
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
		ClientPrefs.data.lowQuality = true;
		ClientPrefs.data.antialiasing = true;
		ClientPrefs.data.shaders = true;
		ClientPrefs.defaultData.noteSkin = 'changed';
	}
}
""",
                encoding="utf-8",
             newline='\n')
            (base / "OptionsHandler.hx").write_text(
                """class OptionsHandler {
	public static var options:Dynamic = {
		lowMemoryMode: true,
		antialiasing: false,
		gameplayShaders: false,
		untouched: 'keep'
	};
}""",
                encoding="utf-8",
             newline='\n')
            (base / "CodenameScriptInterp.hx").write_text(
                """class CodenameScriptInterp {
	public var variables:Map<String,Dynamic>=new Map();
	public function new() {}
	public function bindScriptClassScope(_scope:hscript.ScriptClassScope):Void {}
}""",
                encoding="utf-8",
             newline='\n')
            (base / "Main.hx").write_text(
                r"""import hscript.AbstractScriptClass;
class Main {
 static function main():Void {
  var root=Sys.args()[0];
  var bindings:Map<String,Dynamic>=new Map();
  PsychClientPrefsCompat.addBindings(bindings);
  if(bindings.get('ClientPrefs')!=PsychClientPrefsCompat
   || bindings.get('backend.ClientPrefs')!=PsychClientPrefsCompat)
   throw 'Psych ClientPrefs class aliases were not registered exactly';
  var loaded=CodenameScriptClassLoader.load(root,['demo.PrefsProbe'],bindings,new Map());
  if(loaded.diagnostics.length!=0) throw 'ClientPrefs source binding failed: '+loaded.diagnostics;
  var probe=loaded.scope.createInstance('PrefsProbe',[]);
  if(probe==null || probe.callFunction('noteSkin',[])!='Default'
   || probe.callFunction('defaultSkin',[])!='Default'
   || Std.string(probe.callFunction('lowQuality',[]))!='false'
   || Std.string(probe.callFunction('antialiasing',[]))!='false'
   || Std.string(probe.callFunction('shaders',[]))!='false')
   throw 'current engine options did not reach the owner ClientPrefs view';
  probe.callFunction('mutate',[]);
  if(probe.callFunction('noteSkin',[])!='Default'
   || probe.callFunction('defaultSkin',[])!='Default'
   || Std.string(probe.callFunction('lowQuality',[]))!='false'
   || Std.string(probe.callFunction('antialiasing',[]))!='false'
   || Std.string(probe.callFunction('shaders',[]))!='false'
   || OptionsHandler.options.antialiasing != false
   || OptionsHandler.options.gameplayShaders != false
   || OptionsHandler.options.untouched != 'keep')
   throw 'owner writes changed its detached view or native user settings';

  OptionsHandler.options = {lowMemoryMode:false, antialiasing:true, gameplayShaders:true};
  if(Std.string(probe.callFunction('lowQuality',[]))!='false'
   || Std.string(probe.callFunction('antialiasing',[]))!='true'
   || Std.string(probe.callFunction('shaders',[]))!='true')
   throw 'existing owner class did not observe changed current engine options';
  OptionsHandler.options = {lowMemoryMode:true, antialiasing:'invalid', gameplayShaders:null};
  if(Std.string(probe.callFunction('lowQuality',[]))!='false'
   || Std.string(probe.callFunction('antialiasing',[]))!='true'
   || Std.string(probe.callFunction('shaders',[]))!='true')
   throw 'invalid or absent options did not use engine-compatible defaults';
  if(PsychClientPrefsCompat.defaultData.lowQuality != false
   || PsychClientPrefsCompat.defaultData.antialiasing != true
   || PsychClientPrefsCompat.defaultData.shaders != true)
   throw 'Psych ClientPrefs.defaultData did not preserve engine defaults';
  loaded.scope.release();
 }
}""",
                encoding="utf-8",
             newline='\n')
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
