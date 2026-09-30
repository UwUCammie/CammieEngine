"""Psych compiled class modules retain Haxe indexed-loop semantics in HScript."""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
PSYCH_SOURCE = (ROOT / "tmp/psych-archive-real-import-v3/runtime/assets/imported_mods"
                / "psych-engine-fnf-psychengine-main-d942d5457b/source")
STORY_MENU = PSYCH_SOURCE / "states/StoryMenuState.hx"
RAIN_SHADER = PSYCH_SOURCE / "shaders/RainShader.hx"


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
        str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base),
        "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
        "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), *arguments,
    ]


class PsychIndexedModuleLoopTest(unittest.TestCase):
    def test_structural_generic_field_type_is_erased_without_changing_expressions(self):
        if not RAIN_SHADER.is_file():
            self.skipTest("private Psych archive source fixture unavailable")
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "Main.hx").write_text(r'''import sys.io.File;
@:access(CodenameScriptClassLoader)
class Main {
 static function main():Void {
  var source=File.getContent(Sys.args()[0]);
  var normalized=CodenameScriptClassLoader.normalizeGenericTypePositions(source);
  if(normalized.error!="") throw normalized.error;
  if(normalized.source.indexOf("public var lights:Array<")>=0)
   throw "RainShader structural generic field remained unsupported";
  if(normalized.source.indexOf("public var lights:Array")<0)
   throw "RainShader field type was removed";
  var expression='class Test { function call() { return factory<Array<{ value:Int }>>(); } }';
  var unchanged=CodenameScriptClassLoader.normalizeGenericTypePositions(expression);
  if(unchanged.error!="" || unchanged.source!=expression)
   throw "generic-looking expression was rewritten as a type position";
 }
}''', encoding="utf-8")
            result = subprocess.run(
                fixture_command(base, "--run", "Main", str(RAIN_SHADER)),
                cwd=ROOT, env=haxe_env(), text=True, capture_output=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_psych_bindings_expose_pair_iteration_and_lime_assets(self):
        bindings = (ROOT / "source/PsychCompiledStageBindings.hx").read_text(encoding="utf-8")
        self.assertIn("create(ownerRoot:String, ?initialLibrary:String)", bindings)
        self.assertIn("var ownerPaths = PsychOwnerPaths.create(ownerRoot, initialLibrary);", bindings)
        self.assertIn("bind(bindings, 'Paths', ownerPaths);", bindings)
        self.assertIn("bind(bindings, 'backend.Paths', ownerPaths);", bindings)
        self.assertIn("bind(bindings, 'lime.utils.Assets', PsychOwnerLimeAssets.create(ownerRoot));", bindings)
        self.assertIn("var openFlAssets = PsychOwnerOpenFlAssets.create(ownerRoot);", bindings)
        self.assertIn("bind(bindings, 'openfl.utils.Assets', openFlAssets);", bindings)
        self.assertIn("bindings.set('CodenameKeyValueIterator', CodenameKeyValueIterator.facade());", bindings)
        self.assertIn("bind(bindings, 'FlxPoint', PsychFlxPointCompat);", bindings)
        self.assertIn("bind(bindings, 'flixel.math.FlxPoint', PsychFlxPointCompat);", bindings)
        self.assertIn("bind(bindings, 'flixel.util.FlxSort', FlxSort);", bindings)
        self.assertIn("bind(bindings, 'flixel.util.FlxDestroyUtil', FlxDestroyUtil);", bindings)
        self.assertIn("bind(bindings, 'flixel.addons.display.FlxPieDial', FlxPieDial);", bindings)
        self.assertIn("bind(bindings, 'haxe.Json', haxe.Json);", bindings)
        self.assertIn("bind(bindings, 'FlxGraphic', FlxGraphic);", bindings)
        self.assertIn("bind(bindings, 'flixel.graphics.FlxGraphic', FlxGraphic);", bindings)
        lime_assets = (ROOT / "source/PsychOwnerLimeAssets.hx").read_text(encoding="utf-8")
        self.assertIn("LimeAssets.cache", lime_assets)
        self.assertIn("FNFAssets.getText(resolved.path)", lime_assets)
        self.assertIn("Refused asset outside selected owner", lime_assets)
        point_compat = (ROOT / "source/PsychFlxPointCompat.hx").read_text(encoding="utf-8")
        self.assertIn("class PsychFlxPointCompat extends FlxBasePoint", point_compat)
        self.assertIn("public static function get(x:Float = 0, y:Float = 0):FlxPoint", point_compat)
        self.assertIn("public static function weak(x:Float = 0, y:Float = 0):FlxPoint", point_compat)

    def test_mounted_psych_story_menu_module_normalizes(self):
        if not STORY_MENU.is_file():
            self.skipTest("private Psych archive source fixture unavailable")
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "Main.hx").write_text(r'''import hscript.ScriptClassScope;
import sys.io.File;
@:access(CodenameScriptClassLoader)
class Main {
 static function main():Void {
  var root=Sys.args()[0];
  var path=Sys.args()[1];
  var loader=new CodenameScriptClassLoader(root,new Map(),new ScriptClassScope());
  var source=File.getContent(path);
  var normalized=CodenameScriptClassLoader.normalizeIndexedModuleLoops(source);
  if(normalized.error!="") throw "Psych StoryMenuState normalization failed: "+normalized.error;
  if(normalized.source.indexOf("=> item in")>=0 || normalized.source.indexOf("=> lock in")>=0)
   throw "Psych indexed loops remained in normalized module source";
  if(normalized.source.indexOf("CodenameKeyValueIterator.iterate(grpWeekText.members)")<0
   || normalized.source.indexOf("CodenameKeyValueIterator.iterate(grpLocks.members)")<0)
   throw "Psych StoryMenuState indexed loop expressions were not preserved";
  if(normalized.source.indexOf("item.y = FlxMath.lerp")<0 || normalized.source.indexOf("lock.y = grpWeekText.members")<0)
   throw "Psych StoryMenuState single-statement loop bodies were not preserved";
  var genericTypes=CodenameScriptClassLoader.normalizeGenericTypePositions(source);
  if(genericTypes.error!="") throw "Psych StoryMenuState generic type normalization failed: "+genericTypes.error;
  if(genericTypes.source.indexOf("var grpWeekText:FlxTypedGroup<MenuItem>")>=0)
   throw "Psych StoryMenuState field generic type remained unsupported";
  if(genericTypes.source.indexOf("new FlxTypedGroup<MenuItem>()")<0)
   throw "type-position normalization changed a generic constructor expression";
 }
}''', encoding="utf-8")
            result = subprocess.run(
                fixture_command(base, "--run", "Main", str(PSYCH_SOURCE), str(STORY_MENU)),
                cwd=ROOT, env=haxe_env(), text=True, capture_output=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_generic_type_positions_load_and_execute_without_rewriting_expressions(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            owner = base / "owner"
            module = owner / "source/demo/GenericTypeProbe.hx"
            module.parent.mkdir(parents=True)
            module.write_text('''package demo;
class GenericTypeProbe {
 var points:Array<Int>;
 public function new() { points = []; }
 public function copyRows(input:Array<Int>):Array<Int> {
  var result:Array<Array<Int>> = [];
  var row:Array<Int> = [];
  for (value in input) row.push(value);
  result.push(row);
  return result[0];
 }
}''', encoding="utf-8")
            (base / "Main.hx").write_text(r'''import hscript.ScriptClassScope;
import sys.io.File;
@:access(CodenameScriptClassLoader)
class Main {
 static function main():Void {
  var root=Sys.args()[0];
  var source='class ExpressionProbe { function call() { return factory<Array<Int>>(); } }';
  var expression=CodenameScriptClassLoader.normalizeGenericTypePositions(source);
  if(expression.error!="" || expression.source!=source)
   throw "generic-looking expression was rewritten as a type position";
  var bindings:Map<String,Dynamic>=new Map();
  var loaded=CodenameScriptClassLoader.load(root,["demo.GenericTypeProbe"],bindings,new Map());
  if(loaded.diagnostics.length!=0) throw "generic type annotations were not normalized: "+loaded.diagnostics;
  var probe=loaded.scope.createInstance("demo.GenericTypeProbe",[]);
  if(Std.string(probe.callFunction("copyRows",[[2,4,6]]))!="[2,4,6]")
   throw "generic type erasure changed function argument, local, or return behavior";
  loaded.scope.release();
 }
}''', encoding="utf-8")
            result = subprocess.run(
                fixture_command(base, "--run", "Main", str(owner)),
                cwd=ROOT, env=haxe_env(), text=True, capture_output=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_indexed_loop_modules_execute_arrays_maps_nested_and_call_iterables(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            owner = base / "owner"
            module = owner / "source/demo/IndexedLoopProbe.hx"
            module.parent.mkdir(parents=True)
            module.write_text('''package demo;
class IndexedLoopProbe {
 public function new() {}
 static function choose(rows:Dynamic):Dynamic { return rows; }
 public function arrayRows(rows:Dynamic):String {
  var output = "";
  for (index => row in rows)
   output += index + ":" + row + ";";
  return output;
 }
 public function mutateRows(rows:Dynamic):String {
  var output = "";
  for (index => row in rows) {
   output += index + ":" + row + ";";
   if (index == 0) rows[1] = "changed";
  }
  return output;
 }
 public function appendRows(rows:Dynamic):String {
  var output = "";
  for (index => row in rows) {
   output += index + ":" + row + ";";
   if (index == 0) rows.push("added");
  }
  return output;
 }
 public function mapRows(rows:Dynamic):String {
  var output = "";
  for (key => row in rows) { output += key + ":" + row + ";"; }
  return output;
 }
 public function nestedRows(rows:Dynamic):String {
  var output = "";
  for (index => row in choose(rows)) {
   for (column => value in row) { output += index + "," + column + "=" + value + ";"; }
  }
  return output;
 }
}''', encoding="utf-8")
            (base / "Main.hx").write_text(r'''class Main {
 static function main():Void {
  var bindings:Map<String,Dynamic>=new Map();
  bindings.set("CodenameKeyValueIterator",CodenameKeyValueIterator.facade());
  var loaded=CodenameScriptClassLoader.load(Sys.args()[0],["demo.IndexedLoopProbe"],bindings,new Map());
  if(loaded.diagnostics.length!=0) throw "indexed-loop class rejected: "+loaded.diagnostics;
  var probe=loaded.scope.createInstance("demo.IndexedLoopProbe",[]);
  if(probe.callFunction("arrayRows",[["first","second"]])!="0:first;1:second;")
   throw "array index/value pairs were not preserved";
  if(probe.callFunction("mutateRows",[["first","second"]])!="0:first;1:changed;")
   throw "array values were snapshotted instead of read when each item was reached";
  if(probe.callFunction("appendRows",[["first","second"]])!="0:first;1:second;2:added;")
   throw "array iteration did not observe its live length";
  var map=CodenameMapCompat.fromPairs([
   {key:"left",value:3},{key:"right",value:5}]);
  if(probe.callFunction("mapRows",[map])!="left:3;right:5;")
   throw "map key/value pairs were not preserved";
  if(probe.callFunction("nestedRows",[[[7,8],[9]]])!="0,0=7;0,1=8;1,0=9;")
   throw "nested indexed loops or computed iterables changed";
  loaded.scope.release();
 }
}''', encoding="utf-8")
            result = subprocess.run(
                fixture_command(base, "--run", "Main", str(owner)),
                cwd=ROOT, env=haxe_env(), text=True, capture_output=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
