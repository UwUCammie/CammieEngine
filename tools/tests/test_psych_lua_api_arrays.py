"""Psych Lua source APIs copy returned Haxe arrays across the Lua table boundary."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
import subprocess
import tempfile
import unittest
import re

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"


class PsychLuaApiArraysTest(unittest.TestCase):
    def run_haxe(self, source):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "Fixture.hx").write_text(source, newline="\n")
            return subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "-cp", str(HSCRIPT), "-main", "Fixture", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=45,
            )

    def test_api_result_wrappers_follow_the_final_source_getter_bindings(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        marker = "function seedEngineCompat(interp:Interp, ?extraPsychOwnerRoot:String):Void"
        start = source.index(marker)
        opening = source.index("{", start)
        depth = 0
        end = None
        for index in range(opening, len(source)):
            if source[index] == "{":
                depth += 1
            elif source[index] == "}":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        self.assertIsNotNone(end, "seedEngineCompat body was not closed")
        body = source[start:end]

        wrapper = "PsychLuaApiResults.install(interp);"
        self.assertEqual(body.count(wrapper), 1)
        wrapper_index = body.index(wrapper)
        reflection_index = body.rfind("new PsychReflectionBindings(this, interp).install();")
        runtime_index = body.rfind("runtime.install();")
        self.assertGreaterEqual(reflection_index, 0, "final reflection getters were not installed")
        self.assertGreaterEqual(runtime_index, 0, "runtime overlay was not installed")
        self.assertLess(reflection_index, wrapper_index)
        self.assertLess(runtime_index, wrapper_index)

        tail = body[wrapper_index + len(wrapper):]
        for getter in ("getProperty", "getPropertyFromGroup", "getPropertyFromClass"):
            self.assertIsNone(
                re.search(r"variables\.set\(['\"]" + re.escape(getter) + r"['\"]", tail),
                f"{getter} is rebound after the Lua result wrapper",
            )

    def test_source_api_arrays_become_recursive_one_based_snapshots(self):
        fixture = r'''
class ApiValue {
 public var label:String;
 public function new(label:String) this.label = label;
}
class Fixture {
 static function main() {
  var sourceNative:Array<Dynamic> = ['zero', 'one', 'two'];
  var nested:Array<Dynamic> = ['nested-a', 'nested-b'];
  var sourceActor = new ApiValue('actor');
  var sourceResult:Array<Dynamic> = [sourceNative, [nested, sourceActor], sourceActor];
  var sourceCycle:Array<Dynamic> = [];
  var sourceChild:Array<Dynamic> = [];
  sourceCycle.push(sourceChild);
  sourceCycle.push(sourceChild);
  sourceChild.push(sourceCycle);

  var propertyArgs:Array<Dynamic> = [];
  var groupArgs:Array<Dynamic> = [];
  var classArgs:Array<Dynamic> = [];
  var lua = new LuaCompatInterp();
  lua.variables.set('sourceNative', sourceNative);
  lua.variables.set('sourceResult', sourceResult);
  lua.variables.set('sourceActor', sourceActor);
  lua.variables.set('check', function(condition:Dynamic, message:String):Void {
   if (condition != true) throw message;
  });
  lua.variables.set('getProperty', Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic {
   propertyArgs = args.copy();
   return switch (Std.string(args[0])) {
    case 'items': sourceResult;
    case 'items[0]': sourceNative;
    case 'items[0][0]': sourceNative[0];
    case 'cycle': sourceCycle;
    case 'actor': sourceActor;
    default: null;
   };
  }));
  lua.variables.set('getPropertyFromGroup', Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic {
   groupArgs = args.copy();
   return sourceNative;
  }));
  lua.variables.set('getPropertyFromClass', Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic {
   classArgs = args.copy();
   return sourceResult;
  }));
  PsychLuaApiResults.install(lua);

  var source = 'function onCreate()\n'
   + ' local items = getProperty("items")\n'
   + ' local group = getPropertyFromGroup("notes", 0, "values", true)\n'
   + ' local classItems = getPropertyFromClass("Fixture", "items", true)\n'
   + ' local pathZero = getProperty("items[0]")\n'
   + ' local pathScalar = getProperty("items[0][0]")\n'
   + ' local first = getProperty("cycle")\n'
   + ' local second = getProperty("cycle")\n'
   + ' local nestedArray = items[2][1]\n'
   + ' check(items[1][1] == "zero" and items[1][2] == "one", "array return was not one-based")\n'
   + ' check(#items == 3, "outer sequence length was not converted")\n'
   + ' check(#nestedArray == 2, "nested sequence length was not converted")\n'
   + ' check(nestedArray[1] == "nested-a", "nested array did not become one-based")\n'
   + ' check(group[1] == "zero" and classItems[1][3] == "two", "group/class arrays were not converted")\n'
   + ' check(pathZero[1] == "zero" and pathZero[0] == nil and pathScalar == "zero", "literal property path index zero changed")\n'
   + ' check(sourceNative[0] == "zero" and sourceNative[1] == "one", "native arrays lost zero-based indexing")\n'
   + ' check(items[2][2] == sourceActor and items[3] == sourceActor and getProperty("actor") == sourceActor, "class identity changed")\n'
   + ' check(first ~= second and first[1] == first[2] and first[1][1] == first, "cycle or repeated-array identity was not preserved")\n'
   + ' check(second[1][1] == second, "second return cycle was cross-linked")\n'
   + ' first[1][2] = "changed"\n'
   + ' check(second[1][2] == nil, "separate API result shared its mutable snapshot")\n'
   + 'end\n';
  var translated = LuaCompat.translate(source, 'api-arrays.lua');
  if (!translated.supported) throw translated.diagnostics.join('|');
  lua.execute(new hscript.Parser().parseString(translated.hscript));
  Reflect.callMethod(null, lua.variables.get('onCreate'), []);
  if (propertyArgs.length != 1 || propertyArgs[0] != 'actor')
   throw 'getProperty arguments were not forwarded unchanged: ' + propertyArgs.length
    + ':' + (propertyArgs.length == 0 ? 'none' : Std.string(propertyArgs[0]));
  if (groupArgs.length != 4 || groupArgs[0] != 'notes' || groupArgs[1] != 0
   || groupArgs[2] != 'values' || groupArgs[3] != true)
   throw 'getPropertyFromGroup arguments were not forwarded unchanged';
  if (classArgs.length != 3 || classArgs[0] != 'Fixture' || classArgs[1] != 'items'
   || classArgs[2] != true)
   throw 'getPropertyFromClass arguments were not forwarded unchanged';
  if (sourceChild.length != 1 || sourceNative[0] != 'zero')
   throw 'Lua mutation changed the native source arrays';
 }
}
'''
        result = self.run_haxe(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_non_lua_interpreters_and_non_array_results_keep_identity(self):
        fixture = r'''
class Holder {
 public var table:Array<Dynamic>;
 public function new() {}
}
class Fixture {
 static function main() {
  var native:Array<Dynamic> = ['zero', 'one'];
  var lua = new LuaCompatInterp();
  var object = {value: 7};
  var holder = new Holder();
  if (lua.sourceApiResult(object) != object) throw 'non-array Lua result was copied';
  lua.variables.set('holder', holder);
  lua.execute(new hscript.Parser().parseString(
   'holder.table = ["left", "right"]; holder.table.label = "kept";'
   + ' holder.table[0] = "zero-key";'
   + ' holder.table.callback = function() { return "ok"; };'));
  var owned = holder.table;
  if (owned == null) throw 'Lua-owned fixture array was not exported from interpreter scope';
  lua.variables.set('getProperty', function(_path:String):Dynamic return native);
  lua.variables.set('getPropertyFromGroup', function(_group:String):Dynamic return holder.table);
  PsychLuaApiResults.install(lua);
  var wrapped = Reflect.callMethod(null, lua.variables.get('getProperty'), ['items']);
  if (wrapped == native || !Std.isOfType(wrapped, Array)) throw 'Lua array result was not snapshotted';
  if (lua.sourceApiResult(native) == wrapped) throw 'each API result reused an earlier snapshot';
  var existingResult = Reflect.callMethod(null, lua.variables.get('getPropertyFromGroup'), ['existing']);
  if (existingResult != owned) throw 'an existing Lua-owned table was replaced';
  lua.execute(new hscript.Parser().parseString(
   'var returned = getPropertyFromGroup("existing");'
   + ' if (returned[1] != "left") throw "Lua-owned sequence changed";'
   + ' if (returned.label != "kept") throw "Lua-owned string sidecar changed";'
   + ' if (returned[0] != "zero-key") throw "Lua-owned numeric sidecar changed";'
   + ' if (returned.callback() != "ok") throw "Lua-owned function sidecar changed";'));

  var hscript = new hscript.Interp();
  hscript.variables.set('getProperty', function(_path:String):Dynamic return native);
  PsychLuaApiResults.install(hscript);
  hscript.execute(new hscript.Parser().parseString(
   'var values = getProperty("items"); if (values[0] != "zero" || values[1] != "one") throw "HScript array boundary changed";'));
  if (Reflect.callMethod(null, hscript.variables.get('getProperty'), ['items']) != native)
   throw 'HScript API callback was wrapped';
 }
}
'''
        result = self.run_haxe(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
