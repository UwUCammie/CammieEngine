"""Regression coverage for literal-disabled HXC modules."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DDTO_MODIFIERS = (
    Path("/run/media/cammie/External Storage/FNF-Example-Mods")
    / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/DDTOModifiers.hxc"
)


def hx_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


@unittest.skipUnless(HAXE.is_file() and DDTO_MODIFIERS.is_file(),
                     "portable Haxe toolchain or mounted DDTOModifiers HXC unavailable")
class DisabledHxcModuleTest(unittest.TestCase):
    def run_fixture(self, source: str) -> subprocess.CompletedProcess:
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="hxc-round13-disabled-", dir=ROOT / "tmp") as folder:
            main = Path(folder) / "Main.hx"
            main.write_text(source)
            env = os.environ.copy()
            env["TMPDIR"] = str(ROOT / "tmp")
            return subprocess.run(
                [
                    str(HAXE),
                    "-cp", str(ROOT / "source"),
                    "-cp", folder,
                    "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                    "-main", "Main", "--interp",
                ],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )

    def test_mounted_ddto_modifiers_keeps_false_state_but_emits_no_callbacks(self):
        before = DDTO_MODIFIERS.read_bytes()
        source = hx_string(DDTO_MODIFIERS.read_text(errors="ignore"))
        path = hx_string(str(DDTO_MODIFIERS))
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var result = HxcCompat.analyze({source}, {path});
    if (result.kind != "module" || !result.moduleDisabled
      || !result.moduleSafe || !result.moduleInitializationSafe
      || result.stateFields.indexOf("active") < 0
      || result.stateInitializers.length != 1
      || result.stateInitializers[0].name != "active"
      || result.stateInitializers[0].value != "false"
      || result.callbackAdapters.length != 0
      || result.callbacks.length != 0 || result.canonicalCallbacks.length != 0
      || hasCode(result, "unsupported-hxc-module-body")
      || hasCode(result, "unsupported-hxc-callback-body")
      || result.generatedHscript.indexOf("var active = false;") < 0
      || result.generatedHscript.indexOf("function subStateOpenEnd") >= 0
      || result.generatedHscript.indexOf("function stateChangeEnd") >= 0)
      fail("mounted disabled module was dispatched: " + result.moduleSafetyReasons.join(",")
        + "\\n" + result.generatedHscript);
    new Parser().parseString(result.generatedHscript);
    Sys.println("round13-disabled-mounted-ok");
  }}
}}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("round13-disabled-mounted-ok", result.stdout)
        self.assertEqual(before, DDTO_MODIFIERS.read_bytes())

    def test_synthetic_literal_rule_is_generic_and_dynamic_flag_stays_guarded(self):
        main = r'''import hscript.Parser;
class Main {
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }
  static function main() {
    var disabled = HxcCompat.analyze(
      "class AnyDisabled extends Module { function new() { super('any-disabled'); active = false; } "
        + "function onSubStateOpenEnd(event) { new FunkinCamera('unsafe'); } "
        + "function onStateOpenEnd(event) {} }",
      "synthetic/scripts/modules/any-disabled.hxc");
    if (!disabled.moduleDisabled || !disabled.moduleSafe || !disabled.moduleInitializationSafe
      || disabled.callbackAdapters.length != 0 || disabled.callbacks.length != 0
      || disabled.generatedHscript.indexOf("var active = false;") < 0
      || hasCode(disabled, "unsupported-hxc-module-body")
      || hasCode(disabled, "unsupported-hxc-callback-body"))
      fail("literal disabled rule is not generic: " + disabled.moduleSafetyReasons.join(",")
        + "\\n" + disabled.generatedHscript);
    new Parser().parseString(disabled.generatedHscript);

    var dynamicResult = HxcCompat.analyze(
      "class DynamicFlag extends Module { var flag:Bool = true; "
        + "function new() { super('dynamic-flag'); active = flag; } "
        + "function onSubStateOpenEnd(event) { new FunkinCamera('unsafe'); } }",
      "synthetic/scripts/modules/dynamic-flag.hxc");
    if (dynamicResult.moduleDisabled || dynamicResult.moduleSafe
      || !hasCode(dynamicResult, "unsupported-hxc-module-body"))
      fail("dynamic active expression was treated as a literal disable");
    Sys.println("round13-disabled-synthetic-ok");
  }
}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("round13-disabled-synthetic-ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
