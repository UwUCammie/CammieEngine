"""State values in HXC maps resolve only when their map entry is read."""
from haxe_test_support import HAXE_COMMAND

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"


class HxcDeferredStateFactoryTest(unittest.TestCase):
    def test_map_state_factory_is_deferred_and_memoized_on_first_get(self):
        with tempfile.TemporaryDirectory(prefix="hxc-deferred-state-") as folder:
            temp = Path(folder)
            source = r'''class GenericMenu extends Module {
  var redirectStates:Map<FlxState, MusicBeatState> = [
    MainMenuState => new ImportedMenuState()
  ];
  function onCreate(event) {}
}'''
            main = f'''import hscript.Interp;
import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({json.dumps(source)}, "synthetic/scripts/modules/GenericMenu.hxc");
    if (!result.moduleInitializationSafe) fail("safe map initializer rejected: " + result.moduleSafetyReasons.join(","));
    if (result.generatedHscript.indexOf('hxcDeferredStateFactory("ImportedMenuState", [])') < 0)
      fail("map state factory was not deferred: " + result.generatedHscript);
    new Parser().parseString(result.generatedHscript);

    var factoryCalls = 0;
    var interp = new Interp();
    interp.variables.set("MainMenuState", "main-menu-key");
    interp.variables.set("hxcMap", function(entries) return new HxcDynamicMap(entries));
    interp.variables.set("hxcDeferredStateFactory", function(name, args) {{
      return new HxcDeferredValue(function() {{
        factoryCalls++;
        return {{name: name, args: args}};
      }});
    }});
    interp.execute(new Parser().parseString(result.generatedHscript
      + "\\nfunction readRedirectStates() {{ return redirectStates; }}"));
    if (factoryCalls != 0) fail("state constructed during HXC module initialization");
    var readMap:Dynamic = interp.variables.get("readRedirectStates");
    var map:Dynamic = readMap == null ? null : readMap();
    if (map == null) fail("translated state map missing: " + result.generatedHscript);
    var first = map.get("main-menu-key");
    if (factoryCalls != 1 || first == null || first.name != "ImportedMenuState")
      fail("first map read did not materialize the state exactly once");
    var second = map.get("main-menu-key");
    if (factoryCalls != 1 || second != first)
      fail("map read did not reuse the materialized state");
    Sys.println("deferred state factory OK");
  }}
}}'''
            (temp / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(HSCRIPT),
                 "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("deferred state factory OK", result.stdout)

    def test_direct_state_factory_calls_remain_eager(self):
        source = (ROOT / "source/HxcCompat.hx").read_text()
        self.assertIn("output = lowerStateConstructorValues(output);", source)
        self.assertIn("mapped = deferStateFactoryMapValue(mapped);", source)
        self.assertIn("HxcStateFactory.stateFactory(hxcRoot, name, args)",
                      (ROOT / "source/PlayState.hx").read_text())


if __name__ == "__main__":
    unittest.main()
