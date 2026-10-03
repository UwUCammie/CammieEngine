"""Imported-state null access warnings carry the owner script and callback."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for at in range(brace, len(source)):
        if source[at] == "{":
            depth += 1
        elif source[at] == "}":
            depth -= 1
            if depth == 0:
                return source[start:at + 1]
    raise AssertionError(f"unterminated method: {marker}")


class CodenameStateDiagnosticContextTest(unittest.TestCase):
    def test_module_and_lifecycle_callbacks_scope_and_restore_context(self):
        source = (ROOT / "source/CodenameModStateRuntime.hx").read_text()
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "\tfunction withDiagnosticContext(",
                "\tfunction executeModule(",
                "\tfunction call(",
            )
        )
        fixture = '''
class InterpStub {
 public var variables:Map<String, Dynamic> = new Map();
 public var executeProbe:Void->Void;
 public function new() {}
 public function execute(_program:Dynamic):Void if (executeProbe != null) executeProbe();
}
class RuntimeProbe {
 var interp:InterpStub = new InterpStub();
 var scriptPath:String = "data/states/HL17MainMenu.hx";
 var failed:Map<String, Bool> = new Map();
 public function new() {}
''' + methods + '''
 static function assert(value:Bool, message:String):Void if (!value) throw message;
 public static function run():Void {
  var runtime = new RuntimeProbe();
  var seen = "";
  runtime.interp.variables.set("__compatDiagnosticSource", "outer-source");
  runtime.interp.variables.set("__compatDiagnosticCallback", "outer-callback");
  runtime.interp.executeProbe = function():Void {
   seen = runtime.interp.variables.get("__compatDiagnosticSource") + "#"
    + runtime.interp.variables.get("__compatDiagnosticCallback");
  };
  runtime.executeModule(null);
  assert(seen == "data/states/HL17MainMenu.hx#module", "module context missing: " + seen);
  assert(runtime.interp.variables.get("__compatDiagnosticSource") == "outer-source",
   "module execution did not restore source context");
  assert(runtime.interp.variables.get("__compatDiagnosticCallback") == "outer-callback",
   "module execution did not restore callback context");

  runtime.interp.variables.set("postCreate", function():Void {
   seen = runtime.interp.variables.get("__compatDiagnosticSource") + "#"
    + runtime.interp.variables.get("__compatDiagnosticCallback");
  });
  assert(runtime.call("postCreate", []), "successful callback returned false");
  assert(seen == "data/states/HL17MainMenu.hx#postCreate", "callback context missing: " + seen);
  assert(runtime.interp.variables.get("__compatDiagnosticSource") == "outer-source",
   "successful callback did not restore source context");
  assert(runtime.interp.variables.get("__compatDiagnosticCallback") == "outer-callback",
   "successful callback did not restore callback context");

  runtime.interp.variables.set("broken", function():Void {
   seen = runtime.interp.variables.get("__compatDiagnosticSource") + "#"
    + runtime.interp.variables.get("__compatDiagnosticCallback");
   throw "expected test failure";
  });
  assert(!runtime.call("broken", []), "throwing callback returned true");
  assert(seen == "data/states/HL17MainMenu.hx#broken", "error callback context missing: " + seen);
  assert(runtime.interp.variables.get("__compatDiagnosticSource") == "outer-source",
   "throwing callback did not restore source context");
  assert(runtime.interp.variables.get("__compatDiagnosticCallback") == "outer-callback",
   "throwing callback did not restore callback context");
 }
}
class Main {
 static function main():Void RuntimeProbe.run();
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(fixture, encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "Main"],
                cwd=ROOT, text=True, capture_output=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[codename-state-script-error] data/states/HL17MainMenu.hx.broken", result.stdout)


if __name__ == "__main__":
    unittest.main()
