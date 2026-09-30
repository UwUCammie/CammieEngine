from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HAXESCRIPT = ROOT / ".haxelib/hscript/2,5,0"


class LuaResultsCompatTest(unittest.TestCase):
    def test_results_string_and_math_subset_executes(self):
        fixture = r'''
class LuaResultsCompatTest {
 static function main() {
  var source = "function onCreate()\n"
   + " local raw = '  A-Song  1! '\n"
   + " local clean = string.gsub(raw, '[^%a%d]', ' ')\n"
   + " clean = string.gsub(clean, '%s+', ' ')\n"
   + " clean = string.gsub(clean, '^%s*(.-)%s*$', '%1')\n"
   + " title = string.upper(clean)\n"
   + " lowerTitle = string.lower(title)\n"
   + " found = string.find(lowerTitle, 'song')\n"
   + " missing = string.find(lowerTitle, 'absent')\n"
   + " power = math.pow(2, 5)\n"
   + "end\n";
  var converted = LuaCompat.translate(source, 'results.lua');
  if (!converted.supported) throw converted.diagnostics.join(' | ');
  var interp = new LuaCompatInterp();
  interp.variables.set('Math', Math);
  interp.variables.set('luaStringGsub', EngineCompat.luaStringGsub);
  interp.variables.set('luaStringFind', EngineCompat.luaStringFind);
  interp.variables.set('luaStringLower', EngineCompat.luaStringLower);
  interp.variables.set('luaStringUpper', EngineCompat.luaStringUpper);
  interp.execute(new hscript.Parser().parseString(converted.hscript));
  Reflect.callMethod(null, interp.variables.get('onCreate'), []);
  if (interp.variables.get('title') != 'A SONG 1') throw 'title cleanup/upper: ' + interp.variables.get('title');
  if (interp.variables.get('lowerTitle') != 'a song 1') throw 'lowercase conversion';
  if (interp.variables.get('found') != 3 || interp.variables.get('missing') != null)
   throw 'string.find literal results';
  if (interp.variables.get('power') != 32) throw 'math.pow mapping';
  if (EngineCompat.luaStringGsub('a b', '%s+', '-', 1) != 'a-b')
   throw 'gsub maximum count on a supported pattern';
  var unsupported = LuaCompat.translate(
   "function onCreate()\n local x = string.gsub('a1', '%d', '')\nend", 'unsupported-pattern.lua');
  if (unsupported.supported || unsupported.diagnostics.join(' | ').indexOf('lua-string-library') < 0)
   throw 'unsupported Lua patterns must remain diagnosed';
  Sys.println('ok');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "LuaResultsCompatTest.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "-cp", str(ROOT / "source"), "-cp", str(HAXESCRIPT),
                 "-main", "LuaResultsCompatTest", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
