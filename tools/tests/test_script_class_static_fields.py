"""Owner-scoped HScript-ex source-class static storage fixture."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
FLIXEL_ARGS = [
    "-lib", "openfl", "-lib", "lime", "-lib", "flixel",
    "-D", "FLX_STANDARD_ASSETS_DIRECTORY", "-D", "FLX_DEFAULT_SOUND_EXT=ogg",
    "-D", "FLX_SOUND_SYSTEM", "-D", "FLX_GAMEINPUT_API",
]


def haxe_env():
    env = dict(os.environ)
    env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
    env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
    env["PATH"] = os.pathsep.join(
        [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
    )
    return env


class ScriptClassStaticFieldsTest(unittest.TestCase):
    def test_hscript_and_native_access_share_owner_static_storage(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            hscript_ex = base / "hscript-ex"
            upstream = ROOT / ".haxelib/hscript-ex/git"
            shutil.copytree(upstream / "src/hscript", hscript_ex / "hscript")
            for filename in ("InterpEx.hx", "ScriptClass.hx", "AbstractScriptClass.hx"):
                original = subprocess.run(
                    ["git", "-C", str(upstream), "show", f"HEAD:src/hscript/{filename}"],
                    cwd=ROOT, check=True, capture_output=True, text=True,
                ).stdout
                (hscript_ex / "hscript" / filename).write_text(original, encoding="utf-8", newline='\n')
            for index in range(2):
                patch_result = subprocess.run(
                    [sys.executable, str(ROOT / "tools/patch_hscript_ex_owner_scope.py"),
                     str(hscript_ex / "hscript")],
                    cwd=ROOT, check=True, capture_output=True, text=True,
                )
                if index == 1:
                    self.assertIn("already patched", patch_result.stdout)

            owners = []
            for owner_name in ("owner_a", "owner_b"):
                owner = base / owner_name
                source = owner / "source/demo"
                source.mkdir(parents=True)
                (source / "TankmenBG.hx").write_text(
                    """package demo;
class TankmenBG {
 public static var animationNotes:Array<Dynamic> = [];
 public static var seed:Int = 5;
 public static var derived:Int = seed + 2;
}
""",
                    encoding="utf-8",
                 newline='\n')
                (source / "StaticProbe.hx").write_text(
                    """package demo;
import demo.TankmenBG;
class StaticProbe {
 public var instanceValue:Int = 11;
 public function new() {}
 public function count():Int return TankmenBG.animationNotes.length;
 public function replaceNotes(notes:Array<Dynamic>):Void TankmenBG.animationNotes = notes;
 public function derivedValue():Int return TankmenBG.derived;
}
""",
                    encoding="utf-8",
                 newline='\n')
                owners.append(owner)

            (base / "StaticFieldMain.hx").write_text(
                """import hscript.AbstractScriptClass;
class StaticFieldMain {
 static function call(instance:AbstractScriptClass, name:String, ?args:Array<Dynamic>):Dynamic {
  return instance.callFunction(name, args == null ? [] : args);
 }
 static function main():Void {
  var emptyBindings:Map<String,Dynamic> = new Map();
  var first = CodenameScriptClassLoader.load(Sys.args()[0], ['demo.StaticProbe'], emptyBindings, emptyBindings);
  var second = CodenameScriptClassLoader.load(Sys.args()[1], ['demo.StaticProbe'], emptyBindings, emptyBindings);
  if (first.diagnostics.length != 0 || second.diagnostics.length != 0)
   throw 'class load failed: ' + first.diagnostics + ' / ' + second.diagnostics;

  if (first.scope.setOwnerStaticField('demo.StaticProbe', 'instanceValue', 99))
   throw 'native API accepted an instance field';
  var injected:Array<Dynamic> = ['native'];
  if (!first.scope.setOwnerStaticField('demo.TankmenBG', 'animationNotes', injected))
   throw 'native API did not resolve a declared static field';

  var firstA = first.scope.createInstance('demo.StaticProbe');
  var firstB = first.scope.createInstance('demo.StaticProbe');
  if (call(firstA, 'count') != 1 || call(firstB, 'count') != 1)
   throw 'native static write was not visible to script instances';
  if (call(firstA, 'derivedValue') != 7 || call(firstB, 'derivedValue') != 7)
   throw 'static initializer did not resolve a same-class static field';
  var scripted:Array<Dynamic> = ['script', 'shared'];
  call(firstA, 'replaceNotes', [scripted]);
  if (call(firstB, 'count') != 2) throw 'HScript static write was not shared';

  var secondA = second.scope.createInstance('demo.StaticProbe');
  if (call(secondA, 'count') != 0)
   throw 'static values leaked between owner scopes';
  if (call(secondA, 'derivedValue') != 7)
   throw 'second owner did not initialize its own static value';

  first.scope.release();
  second.scope.release();
 }
}""",
                encoding="utf-8",
             newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(base),
                 "-cp", str(ROOT / "source"), "-cp", str(hscript_ex),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 *FLIXEL_ARGS, "--run", "StaticFieldMain", *(str(owner) for owner in owners)],
                cwd=ROOT, env=haxe_env(), capture_output=True, text=True, timeout=90,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
