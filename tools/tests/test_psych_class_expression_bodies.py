"""HScript-ex class loading normalizes Haxe expression-bodied methods safely."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
PSYCH_SOURCE = (ROOT / "tmp/psych-archive-real-import-v3/runtime/assets/imported_mods"
                / "psych-engine-fnf-psychengine-main-d942d5457b/source")
GAMEPLAY_CHANGERS = PSYCH_SOURCE / "options/GameplayChangersSubstate.hx"


def haxe_env():
    env = dict(os.environ)
    env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
    env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
    env["PATH"] = os.pathsep.join(
        [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
    )
    return env


def fixture_command(base, *arguments):
    return [
        *HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
        "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
        "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), *arguments,
    ]


class PsychClassExpressionBodyTest(unittest.TestCase):
    def test_normalizes_direct_and_unbraced_if_bodies(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "Main.hx").write_text(r'''import hscript.ParserEx;
@:access(CodenameScriptClassLoader)
class Main {
 static function main():Void {
  var source='class Probe { var value:Int = 7; function get_value():Int return value; '
   +'function tick(n:Int) if(n % 2 == 0) dance(); '
   +'function choose(n:Int) if(n > 0) dance(); else rest(); '
   +'function block():Int { return value; } // function ignored() return 4;\n'
   +'var text:String = "function ignored() return 5;"; }';
  var normalized=CodenameScriptClassLoader.normalizeExpressionBodiedMethods(source);
  if(normalized.indexOf('function get_value():Int {return value;}')<0)
   throw 'expression body was not wrapped: '+normalized;
  if(normalized.indexOf('function tick(n:Int) {if(n % 2 == 0) dance();}')<0
   || normalized.indexOf('function choose(n:Int) {if(n > 0) dance(); else rest();}')<0)
   throw 'unbraced if method body was not wrapped: '+normalized;
  if(normalized.indexOf('function block():Int { return value; }')<0)
   throw 'block body changed';
  if(normalized.indexOf('// function ignored() return 4;')<0
   || normalized.indexOf('"function ignored() return 5;"')<0)
   throw 'comment/string changed';
  new ParserEx().parseModule(normalized,'fixture');
 }
}''', encoding="utf-8", newline='\n')
            result = subprocess.run(
                fixture_command(base, "--run", "Main"), cwd=ROOT, env=haxe_env(),
                text=True, capture_output=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_psych_gameplay_changers_class_parses(self):
        if not GAMEPLAY_CHANGERS.is_file():
            self.skipTest("private Psych archive source fixture unavailable")
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "Main.hx").write_text(r'''import hscript.ParserEx;
import hscript.ScriptClassScope;
import sys.io.File;
@:access(CodenameScriptClassLoader)
class Main {
 static function main():Void {
  var root=Sys.args()[0]; var path=Sys.args()[1];
  var source=File.getContent(path); var scope=new ScriptClassScope();
  scope.registerModule(new ParserEx().parseModule('class FlxTypedGroup {}','native-stub'));
  var loader=new CodenameScriptClassLoader(root,new Map(),scope);
  var normalized=loader.normalizeModuleSyntax(source,'options.GameplayChangersSubstate',
   'source/options/GameplayChangersSubstate.hx',0);
  if(normalized.error!='') throw normalized.error;
  if(normalized.source.indexOf('function get_curOption() {return optionsArray[curSelected];}')<0)
   throw 'mounted getter body was not normalized';
  if(normalized.source.indexOf('{ClientPrefs.data.gameplaySettings.set(variable, value);}')<0
   || normalized.source.indexOf('{this.child = child;}')<0)
   throw 'mounted setter expression body was not normalized';
  var repaired=CodenameScriptClassLoader.repairMissingArrayFieldTerminator(normalized.source);
  var module=new ParserEx().parseModule(repaired,path);
  if(module.length==0) throw 'mounted module parsed as empty';
 }
}''', encoding="utf-8", newline='\n')
            result = subprocess.run(
                fixture_command(base, "--run", "Main", str(GAMEPLAY_CHANGERS.parents[2]),
                                str(GAMEPLAY_CHANGERS)),
                cwd=ROOT, env=haxe_env(), text=True, capture_output=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
