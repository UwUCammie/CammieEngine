from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import json
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"
WIZ_MAKER = ROOT / "tmp/compatibility-visual-check/assets/data/swag-messiah/wiz-maker.lua"


class LuaFunctionTablesTest(unittest.TestCase):
    def run_haxe(self, source):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Fixture.hx").write_text(source, newline="\n")
            return subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "-cp", str(HSCRIPT), "-main", "Fixture", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )

    def test_function_table_sugar_closures_and_lua_fallback_semantics(self):
        fixture = r'''
class Fixture {
 static function main() {
  var source = "function onCreate()\n"
   + " globalResult = switch('global') { ['global'] = function () return 'global'; end }\n"
   + " bareCall = pickCase { ['space key'] = 'bare' }\n"
   + " local default = 'fallback'\n"
   + " local new = 'new-value'\n"
   + " local this = 'this-value'\n"
   + " local case = 'case-value'\n"
   + " local null = 'null-value'\n"
   + " reservedValues = new .. ':' .. this .. ':' .. case .. ':' .. null\n"
   + " local effects = ''\n"
   + " local record = function(tag) effects = effects .. tag; return tag; end\n"
   + " local switch = function(value)\n"
   + "  return function(cases)\n"
   + "    local chosen = cases[value] or cases[default] or function () end\n"
   + "    return chosen()\n"
   + "  end\n"
   + " end\n"
   + "  emptyKey = switch('') {\n"
   + "    [''] = function () return 'empty'; end,\n"
   + "    ['space key'] = function () return 'space'; end,\n"
   + "    ['quote\\\"key'] = function () return 'quoted'; end\n"
   + "  }\n"
   + "  emptyFunction = function () end\n"
   + "  emptyCall = emptyFunction()\n"
   + "  spacedKey = switch('space key') { ['space key'] = function () return 'matched'; end }\n"
   + "  fallbackKey = switch('missing') { ['fallback'] = function () return 'fallback'; end }\n"
   + "  falseFallback = switch('false') { ['false'] = false, ['fallback'] = function () return 'false-fallback'; end }\n"
   + "  nilFallback = switch('nil') { ['nil'] = 'discarded', ['nil'] = nil, ['fallback'] = function () return 'nil-fallback'; end }\n"
   + "  noFallback = switch('missing') { ['other'] = function () return 'other'; end }\n"
   + "  mixedTable = { 'sequence', ['space key'] = function () return 'mixed'; end }\n"
   + "  mixedSequence = mixedTable[1]\n"
   + "  mixedKey = mixedTable['space key']()\n"
   + "  orderedTable = { ['first key'] = record('A'), record('B'), ['last key'] = record('C') }\n"
   + "  orderedEffects = effects\n"
   + "  orderedSequence = orderedTable[1]\n"
   + "  duplicateTable = { ['same key'] = record('D'), ['same key'] = record('E') }\n"
   + "  duplicateValue = duplicateTable['same key']\n"
   + "  nilTable = { ['nil'] = record('F'), ['nil'] = nil }\n"
   + "  nilValue = nilTable['nil']\n"
   + "  allEffects = effects\n"
   + "  fieldNames = { switch = 'field', default = 'fallback-field' }\n"
   + "  namedField = fieldNames.switch\n"
   + "  quotedField = fieldNames['default']\n"
   + "end\n"
   + "function switch (value)\n"
   + " return function(cases)\n"
   + "  local chosen = cases[value] or function () end\n"
   + "  return chosen()\n"
   + " end\n"
   + "end\n"
   + "function pickCase(cases)\n"
   + " return cases['space key']\n"
   + "end\n";
  var converted = LuaCompat.translate(source, 'function-table.lua');
  if (!converted.supported) throw converted.diagnostics.join(' | ') + '\n' + converted.hscript;
  if (converted.hscript.indexOf('__luaCompatReserved_switch') < 0
      || converted.hscript.indexOf('__luaCompatReserved_default') < 0)
   throw 'reserved Lua identifiers were not consistently rewritten: ' + converted.hscript;
  if (converted.hscript.indexOf("switch: 'field'") < 0
      || converted.hscript.indexOf("default: 'fallback-field'") < 0)
   throw 'reserved names changed as Lua table fields: ' + converted.hscript;
  var interp = new LuaCompatInterp();
  interp.execute(new hscript.Parser().parseString(converted.hscript));
  Reflect.callMethod(null, interp.variables.get('onCreate'), []);
  var expected = [
   ['emptyKey', 'empty'], ['spacedKey', 'matched'], ['fallbackKey', 'fallback'],
   ['falseFallback', 'false-fallback'], ['nilFallback', 'nil-fallback'],
   ['emptyCall', null], ['noFallback', null], ['mixedSequence', 'sequence'], ['mixedKey', 'mixed'],
   ['orderedEffects', 'ABC'], ['orderedSequence', 'B'],
   ['duplicateValue', 'E'], ['nilValue', null], ['allEffects', 'ABCDEF'],
   ['namedField', 'field'], ['quotedField', 'fallback-field'],
   ['globalResult', 'global'], ['bareCall', 'bare'],
   ['reservedValues', 'new-value:this-value:case-value:null-value']
  ];
  for (row in expected) {
   var actual = interp.variables.get(row[0]);
   if (actual != row[1]) throw row[0] + ' expected=' + row[1] + ' actual=' + actual + ' type=' + Type.typeof(actual)
    + '\n' + converted.hscript;
  }
 }
}
'''
        result = self.run_haxe(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_dynamic_bracket_expression_still_reports_a_specific_table_key_error(self):
        fixture = r'''
class Fixture {
 static function main() {
  var converted = LuaCompat.translate(
   "function onCreate()\n local key = 'x'\n local values = {[key] = function() end}\nend",
   'dynamic-function-table.lua');
  if (converted.supported || converted.diagnostics.join(' | ').indexOf('lua-table-key') < 0)
   throw 'unsupported dynamic table key lost its diagnostic: ' + converted.diagnostics.join(' | ');
 }
}
'''
        result = self.run_haxe(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_private_wiz_maker_companion_table_dispatch_parses_when_present(self):
        if not WIZ_MAKER.exists():
            self.skipTest("private wiz-maker companion fixture is unavailable")
        path = str(WIZ_MAKER).replace("\\", "/")
        fixture = f'''
class Fixture {{
 static function main() {{
  var embeddedSource = "function onBeatHit()\\n"
   + " runHaxeCode([[\\n if (]]..curBeat..[[ % 2 == 0) {{ game.dance(); }}\\n ]])\\n"
   + "end";
  var embedded = LuaCompat.translate(embeddedSource, "isolated-embedded.lua", true);
  if (embedded.diagnostics.join(" | ").indexOf("lua-generated-syntax") >= 0)
   throw embedded.diagnostics.join(" | ") + "\\n" + embedded.hscript;
  var path = {json.dumps(path)};
  var converted = LuaCompat.translate(sys.io.File.getContent(path), path, true);
  var diagnostics = converted.diagnostics.join(" | ");
  if (diagnostics.indexOf("lua-table-key") >= 0
      || diagnostics.indexOf("lua-unbalanced-end") >= 0
      || diagnostics.indexOf("lua-generated-syntax") >= 0)
   throw diagnostics + "\\n" + converted.hscript;
  if (converted.hscript.indexOf("__luaCompatReserved_switch") < 0
      || converted.hscript.indexOf('["Green-Wiz Sing"]') < 0)
   throw "generic function-valued table lowering was absent: " + converted.hscript;
  new hscript.Parser().parseString(converted.hscript);
 }}
}}
'''
        result = self.run_haxe(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
