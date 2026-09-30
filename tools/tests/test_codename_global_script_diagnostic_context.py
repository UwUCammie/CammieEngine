"""Owner global callbacks carry source context and run postStateSwitch once."""

from pathlib import Path
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


class CodenameGlobalScriptDiagnosticContextTest(unittest.TestCase):
    def test_global_callbacks_restore_context_and_post_switch_dispatch_is_registered(self):
        runtime_source = (ROOT / "source/CodenameGlobalScriptRuntime.hx").read_text(encoding="utf-8")
        mod_runtime_source = (ROOT / "source/CodenameModRuntime.hx").read_text(encoding="utf-8")
        context_helper = extract_method(runtime_source, "\tfunction withDiagnosticContext(")
        call = extract_method(runtime_source, "\tfunction call(name:String, args:Array<Dynamic>):Bool {")
        post_switch = extract_method(runtime_source, "\tpublic function postStateSwitch():Void {")

        self.assertIn("withDiagnosticContext('module'", runtime_source)
        self.assertIn("withDiagnosticContext(name", call)
        self.assertIn("globalRuntime.postStateSwitch()", mod_runtime_source)
        self.assertIn("FlxG.signals.postStateSwitch.add(postSwitchHandler)", mod_runtime_source)
        self.assertIn("FlxG.signals.postStateSwitch.remove(postSwitchHandler)", mod_runtime_source)

        fixture = '''class FakeInterp {
 public var variables:Map<String, Dynamic> = new Map();
 public function new() {}
}
class Probe {
 public var interp:FakeInterp = new FakeInterp();
 public var scriptPath:String = "data/global.hx";
 public var initialized:Bool = true;
 public var released:Bool = false;
 public var failedCallbacks:Map<String, Bool> = new Map();
 public var observed:String = "";
 public var lastFailure:String = "";
 public function new() {}
''' + context_helper + '\n' + post_switch + '\n' + call + '''
 public function invoke(name:String, args:Array<Dynamic>):Bool return call(name, args);
 public function report(name:String, error:Dynamic):Void lastFailure = name + ":" + Std.string(error);
 static function assert(value:Bool, message:String):Void if (!value) throw message;
 public function run():Void {
  interp.variables.set("postStateSwitch", function():Void {
   observed = interp.variables.get("__compatDiagnosticSource") + "#"
    + interp.variables.get("__compatDiagnosticCallback");
  });
  postStateSwitch();
  assert(observed == "data/global.hx#postStateSwitch", "post switch context missing: " + observed);
  assert(interp.variables.get("__compatDiagnosticSource") == null
   && interp.variables.get("__compatDiagnosticCallback") == null, "post switch context leaked");

  interp.variables.set("update", function(elapsed:Float):Void {
   observed = interp.variables.get("__compatDiagnosticSource") + "#"
    + interp.variables.get("__compatDiagnosticCallback") + ":" + elapsed;
  });
  assert(invoke("update", [0.25]), "global update failed");
  assert(observed == "data/global.hx#update:0.25", "global update context missing: " + observed);
  assert(interp.variables.get("__compatDiagnosticSource") == null
   && interp.variables.get("__compatDiagnosticCallback") == null, "update context leaked");

  interp.variables.set("preStateSwitch", function():Void {
   observed = interp.variables.get("__compatDiagnosticSource") + "#"
    + interp.variables.get("__compatDiagnosticCallback");
   throw "expected callback error";
  });
  assert(!invoke("preStateSwitch", []), "throwing callback unexpectedly succeeded");
  assert(observed == "data/global.hx#preStateSwitch", "failure callback context missing");
  assert(lastFailure == "preStateSwitch:expected callback error", "callback error not reported");
  assert(interp.variables.get("__compatDiagnosticSource") == null
   && interp.variables.get("__compatDiagnosticCallback") == null, "error path leaked callback context");
 }
}
class Main {
 static function main():Void new Probe().run();
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temporary:
            work = Path(temporary)
            (work / "Main.hx").write_text(fixture, encoding="utf-8")
            result = subprocess.run(
                [str(HAXE), "-cp", str(work), "--run", "Main"],
                cwd=ROOT, text=True, capture_output=True, timeout=60,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
