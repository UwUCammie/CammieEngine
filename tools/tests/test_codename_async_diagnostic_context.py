"""Asynchronous HScript timer callbacks retain and restore source context."""
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


class CodenameAsyncDiagnosticContextTest(unittest.TestCase):
    def test_timer_callback_context_and_arguments_are_preserved_and_restored(self):
        source = (ROOT / "source/CodenameScriptInterp.hx").read_text()
        helper = extract_method(source, "\tfunction callAsyncCallbackWithDiagnosticContext(")
        fcall = extract_method(source, "\toverride function fcall(")
        self.assertIn("var callbackSource = variables.get('__compatDiagnosticSource')", fcall)
        self.assertIn("var callbackName = variables.get('__compatDiagnosticCallback')", fcall)
        self.assertIn(
            "callAsyncCallbackWithDiagnosticContext(callback, [timer], callbackSource, callbackName)",
            fcall,
        )
        self.assertIn("var wrappedArgs = args.copy()", fcall)
        self.assertIn("args = wrappedArgs", fcall)
        self.assertIn("if (smokeTrace)", fcall)

        fixture = '''
class RuntimeProbe {
 var variables:Map<String, Dynamic> = new Map();
 public function new() {}
''' + helper + '''
 static function assert(value:Bool, message:String):Void if (!value) throw message;
 public function run():Void {
  variables.set("__compatDiagnosticSource", "outer-source");
  variables.set("__compatDiagnosticCallback", "outer-callback");
  var marker = {};
  var observed = "";
  var seenMarker:Dynamic = null;
  var seenArgument:Dynamic = null;
  var result = callAsyncCallbackWithDiagnosticContext(function(value:Dynamic, tag:String):String {
   observed = variables.get("__compatDiagnosticSource") + "#"
    + variables.get("__compatDiagnosticCallback");
   seenMarker = value;
   seenArgument = tag;
   return "callback-result";
  }, [marker, "authored argument"], "data/states/HL17MainMenu.hx", "update");
  assert(result == "callback-result", "callback return changed");
  assert(observed == "data/states/HL17MainMenu.hx#update -> FlxTimer.start callback",
   "async callback context missing: " + observed);
  assert(seenMarker == marker && seenArgument == "authored argument",
   "callback arguments changed");
  assert(variables.get("__compatDiagnosticSource") == "outer-source",
   "successful callback did not restore source");
  assert(variables.get("__compatDiagnosticCallback") == "outer-callback",
   "successful callback did not restore callback");

  observed = "";
  try {
   callAsyncCallbackWithDiagnosticContext(function():Void {
    observed = variables.get("__compatDiagnosticSource") + "#"
     + variables.get("__compatDiagnosticCallback");
    throw "expected callback failure";
   }, [], "songs/demo/scripts/script.hx", null);
   throw "throwing callback unexpectedly returned";
  } catch (error:Dynamic) {
   if (Std.string(error) != "expected callback failure") throw error;
  }
  assert(observed == "songs/demo/scripts/script.hx#FlxTimer.start callback",
   "error callback context missing: " + observed);
  assert(variables.get("__compatDiagnosticSource") == "outer-source",
   "throwing callback did not restore source");
  assert(variables.get("__compatDiagnosticCallback") == "outer-callback",
   "throwing callback did not restore callback");
 }
}
class Main {
 static function main():Void new RuntimeProbe().run();
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(fixture, encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "Main"],
                cwd=ROOT, text=True, capture_output=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
