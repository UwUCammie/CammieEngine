"""runHaxeCode reuses parsed trees per source string without changing results."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest

from test_psych_runtime_bindings import (HSCRIPT_PRESET, HXC_RUNTIME, LUA_INTERP, PLAY_STATE,
                                         write_point_stub)

ROOT = Path(__file__).resolve().parents[2]


MAIN = r'''package;
import hscript.Interp;

class ParseCacheFixture {
 static function check(value:Bool,message:String):Void if(!value)throw message;

 static function main():Void {
  var host=new PlayState();
  var lua=new LuaCompatInterp();
  lua.variables.set('__psychScoreGlobals',true);
  lua.variables.set('__compatDiagnosticSource','mods/cache.lua');
  host.hscriptStates.set('cache',lua);
  var runtime=new PsychRuntimeBindings(host,lua,'mods/cache.lua');
  runtime.install();
  host.psychRuntimeBindings.push(runtime);
  var run=lua.variables.get('runHaxeCode');
  // Psych reports a failing runHaxeCode instead of stopping the Lua callback.
  var reports:Array<String>=[];
  haxe.Log.trace=function(value:Dynamic,?infos:haxe.PosInfos):Void reports.push(Std.string(value));
  function exec(code:String,?vars:Dynamic):Dynamic {
   var before=reports.length;
   var result=Reflect.callMethod(null,run,vars==null?[code]:[code,vars]);
   if(reports.length>before&&reports[reports.length-1].indexOf('[psych-hscript-error]')==0)throw reports[reports.length-1];
   return result;
  }

  exec('counter = 0;');
  var bridge:SourceIrisBridge=@:privateAccess runtime.embedded;
  var parsed=function():Int return @:privateAccess bridge.parsedSourceCount;
  check(parsed()==1,'first runHaxeCode string was not kept');

  // A repeated string runs again with live state instead of a stale result.
  check(exec('counter += 1; counter;')==1&&exec('counter += 1; counter;')==2
   &&exec('counter += 1; counter;')==3,'cached tree did not run again');
  check(parsed()==2,'repeated string was parsed more than once');
  check(exec('return game != null;')==true&&exec('return game != null;')==true,'game probe changed');

  // varsToBring is applied on every call, cached or not.
  check(exec('brought + 1;',{brought:5})==6&&exec('brought + 1;',{brought:7})==8,
   'cached tree ignored new varsToBring');
  var missing=false;
  try exec('brought + 1;') catch(_:Dynamic) missing=true;
  check(missing,'previous varsToBring survived a call without them');

  // Imports are bound again on cached calls.
  var importCode='import haxe.ds.StringMap; var made = new StringMap(); made.set("k", 4); made.get("k");';
  check(exec(importCode)==4&&exec(importCode)==4,'cached import string changed its result');

  // A string that fails to parse is not kept and fails the same way each time.
  var before=parsed();
  var errors:Array<String>=[];
  for(i in 0...2) try exec('var = ;') catch(error:Dynamic) errors.push(Std.string(error));
  check(errors.length==2&&errors[0]==errors[1]&&parsed()==before,'parse failure was cached or changed');

  // A runtime error leaves the parsed tree usable.
  var thrown=0;
  for(i in 0...2) try exec('throw "boom";') catch(_:Dynamic) thrown++;
  check(thrown==2&&exec('counter;')==3,'runtime failure broke the cached tree');

  // Many distinct strings stay bounded and still evaluate correctly.
  for(i in 0...600) check(exec('' + i + ' + 1;')==i+1,'distinct string '+i+' gave a wrong result');
  check(parsed()<=256,'parse cache was not bounded: '+parsed());

  // Whole-file evaluation does not use the cache.
  var plain=new SourceIrisBridge(host);
  plain.evaluate('value = 2;','file.hx');
  plain.evaluate('value = 2;','file.hx');
  check(@:privateAccess plain.parsedSources==null,'file evaluation filled the runHaxeCode cache');

  runtime.release();
  check(@:privateAccess bridge.parsedSources==null,'release kept parsed trees');
  Sys.println('OK');
 }
}
'''


class RunHaxeCodeParseCacheTest(unittest.TestCase):
    def test_repeated_strings_reuse_the_parse_with_live_bindings(self):
        if not (ROOT / ".tools/haxe/haxe.exe").is_file() and not (ROOT / ".tools/haxe/haxe").is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        with tempfile.TemporaryDirectory(prefix="run-haxe-code-cache-", dir=ROOT / "tmp") as folder:
            scratch = Path(folder)
            from psych_standard_fixture_support import write_standard_services_stub
            write_standard_services_stub(scratch)
            write_point_stub(scratch)
            (scratch / "PlayState.hx").write_text(PLAY_STATE, encoding="utf-8", newline="\n")
            (scratch / "LuaCompatInterp.hx").write_text(LUA_INTERP, encoding="utf-8", newline="\n")
            (scratch / "PsychHscriptSourceBindings.hx").write_text(HSCRIPT_PRESET, encoding="utf-8", newline="\n")
            (scratch / "PsychAchievementsIntegration.hx").write_text(
                "class PsychAchievementsIntegration {\n"
                " public static function installLua(host:Dynamic,interp:Dynamic,origin:String):Void {}\n"
                " public static function installHscript(host:Dynamic,interp:Dynamic,origin:String):Void {}\n"
                "}\n", encoding="utf-8", newline="\n")
            (scratch / "HxcCompatRuntime.hx").write_text(HXC_RUNTIME, encoding="utf-8", newline="\n")
            (scratch / "ParseCacheFixture.hx").write_text(MAIN, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-iris/1,1,3"), "-cp", str(scratch),
                 "--run", "ParseCacheFixture"],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
