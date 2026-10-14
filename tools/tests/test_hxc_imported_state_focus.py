"""Imported V-Slice states hear window focus changes, as V-Slice states do."""
from haxe_test_support import HAXE_COMMAND

import subprocess
import tempfile
import unittest
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class HxcImportedStateFocusTest(unittest.TestCase):
    def test_state_forwards_focus_to_its_runtime(self):
        state = (ROOT / "source/HxcImportedState.hx").read_text(encoding="utf-8")
        gained = extract_method(state, "override public function onFocus(")
        lost = extract_method(state, "override public function onFocusLost(")
        self.assertIn("super.onFocus();", gained)
        self.assertIn("runtime.focus(true)", gained)
        self.assertIn("super.onFocusLost();", lost)
        self.assertIn("runtime.focus(false)", lost)

    def test_runtime_sends_the_focus_hooks_with_an_event(self):
        runtime = (ROOT / "source/HxcImportedRuntime.hx").read_text(encoding="utf-8")
        focus = extract_method(runtime, "public function focus(")
        main = '''class FakeRuntime {
  public var created = true;
  public var failed = false;
  public var owner:Dynamic = {name: "menu"};
  public var calls:Array<Dynamic> = [];
  public function new() {}
  function call(name:String, args:Array<Dynamic>, optional:Bool):Bool {
    calls.push({name: name, args: args, optional: optional});
    return true;
  }
  ''' + focus + '''
}
class ImportedFocusFixture {
  static function fail(message:String):Void throw message;
  static function main() {
    var runtime = new FakeRuntime();
    runtime.focus(false);
    runtime.focus(true);
    if (runtime.calls.length != 2) fail("both focus changes are sent");
    if (runtime.calls[0].name != "focusLost" || runtime.calls[1].name != "focusGained") fail("hook names");
    if (runtime.calls[0].optional != true) fail("a state without the hook is fine");
    var event:Dynamic = runtime.calls[0].args[0];
    if (event == null || event.targetState != runtime.owner) fail("event carries the state");
    // Same names the lifecycle table gives the V-Slice methods.
    if (ScriptLifecycleNames.vsliceCanonical("onFocusLost") != "focusLost"
      || ScriptLifecycleNames.vsliceCanonical("onFocusGained") != "focusGained") fail("table names");
    // A state that failed to load, or never created, hears nothing.
    var failed = new FakeRuntime();
    failed.failed = true;
    failed.focus(true);
    var unborn = new FakeRuntime();
    unborn.created = false;
    unborn.focus(false);
    if (failed.calls.length != 0 || unborn.calls.length != 0) fail("dead runtime called");
    Sys.println("ok");
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "ImportedFocusFixture.hx").write_text(main, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"), "-main", "ImportedFocusFixture", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=180,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
