"""Pin wildcard-imported owner classes passed to FlxTypedGroup.recycle."""
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


class PsychOwnerScriptClassRecycleTest(unittest.TestCase):
    def test_wildcard_imported_class_symbol_recycles_owner_proxy(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            owner = base / "owner"
            modules = {
                "source/demo/Main.hx": """package demo;
import flixel.FlxBasic;
import flixel.group.FlxGroup.FlxTypedGroup;
import demo.parts.*;
class Main {
 var group:FlxTypedGroup<FlxBasic>;
 public function new(group:FlxTypedGroup<FlxBasic>) {
  this.group=group;
 }
 public function spawn():Dynamic {
  return group.recycle(Particle);
 }
}
""",
                "source/demo/parts/Particle.hx": """package demo.parts;
import flixel.FlxBasic;
class Particle extends FlxBasic {
 public function new() { super(); }
 public function label():String { return 'owner-particle'; }
}
""",
            }
            for relative, content in modules.items():
                path = owner / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline='\n')

            probe = base / "PsychOwnerScriptClassRecycleProbe.hx"
            probe.write_text(
                r'''import flixel.FlxBasic;
import flixel.group.FlxGroup.FlxTypedGroup;
import hscript.ScriptClass;

class PsychOwnerScriptClassRecycleProbe {
 static function check(ok:Bool, message:String):Void {
  if (!ok) throw message;
 }
 static function main():Void {
  var bindings:Map<String,Dynamic>=new Map();
  bindings.set('flixel.FlxBasic',FlxBasic);
  bindings.set('FlxBasic',FlxBasic);
  bindings.set('flixel.group.FlxGroup.FlxTypedGroup',FlxTypedGroup);
  bindings.set('FlxTypedGroup',FlxTypedGroup);
  var loaded=CodenameScriptClassLoader.load(Sys.args()[0],['demo.Main'],bindings,bindings);
  check(loaded.diagnostics.length==0,'wildcard owner class load failed: '+loaded.diagnostics);

  var group:FlxTypedGroup<FlxBasic>=new FlxTypedGroup<FlxBasic>();
  var host=loaded.scope.createInstance('demo.Main',[group]);
  check(host!=null,'owner host did not instantiate');
  var first:Dynamic=host.callFunction('spawn',[]);
  check(Std.isOfType(first,ScriptClass),'recycle did not return the owner ScriptClass');
  var firstProxy:ScriptClass=cast first;
  check(loaded.scope.findDescriptor('demo.parts.Particle')!=null,
   'wildcard import did not register its referenced owner class');
  check(firstProxy.callFunction('label',[])=='owner-particle','recycled owner script method did not resolve');
  check(group.members.length==1 && Std.isOfType(group.members[0],PsychScriptClassBasic),
   'recycled owner class was not added to the native Flx group through its native adapter');

  var bridge:PsychScriptClassBasic=cast group.members[0];
  bridge.kill();
  var second:Dynamic=host.callFunction('spawn',[]);
  check(second==first,'recycle did not reuse the dead bridge for its requested owner class');
  check(group.members.length==1 && bridge.exists,'reused owner bridge was not revived in place');

  var cappedGroup:FlxTypedGroup<FlxBasic>=new FlxTypedGroup<FlxBasic>(1);
  var cappedHost=loaded.scope.createInstance('demo.Main',[cappedGroup]);
  var cappedFirst:Dynamic=cappedHost.callFunction('spawn',[]);
  check(Std.isOfType(cappedFirst,ScriptClass) && cappedGroup.members.length==1,
   'positive-capacity recycle did not create and add an owner bridge');
  var cappedSecond:Dynamic=cappedHost.callFunction('spawn',[]);
  check(cappedSecond==cappedFirst && cappedGroup.members.length==1,
   'positive-capacity recycle did not preserve FlxGroup rotating behavior');
  loaded.scope.release();
 }
}''',
                encoding="utf-8",
             newline='\n')
            command = [
                *HAXE_COMMAND,
                "-cp", str(base),
                "-cp", str(ROOT / "source"),
                "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"),
                *FLIXEL_ARGS,
                "--run", "PsychOwnerScriptClassRecycleProbe", str(owner),
            ]
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=haxe_env(),
                capture_output=True,
                text=True,
                timeout=90,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
