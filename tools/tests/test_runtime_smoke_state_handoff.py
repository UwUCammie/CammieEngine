"""Pin smoke-clock continuity when gameplay hands off to an imported state."""

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
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class RuntimeSmokeStateHandoffTest(unittest.TestCase):
    def test_imported_state_ticks_once_after_gameplay_handoff(self):
        imported_source = (ROOT / "source/CodenameImportedState.hx").read_text()
        play_state_source = (ROOT / "source/PlayState.hx").read_text()
        imported_update = extract_method(
            imported_source, "override public function update(elapsed:Float):Void"
        )
        play_update = extract_method(
            play_state_source, "override public function update(elapsed:Float)"
        )
        self.assertEqual(imported_update.count("RuntimeSmokeHarness.tick(elapsed)"), 1)
        self.assertEqual(play_update.count("RuntimeSmokeHarness.tick(elapsed)"), 1)
        self.assertIn("if (RuntimeSmokeHarness.enabled())", imported_update)

        fixture = """class FlxG {
  public static var keys:Dynamic = {justPressed:{F10:false}};
}
class RuntimeSmokeHarness {
  public static var active:Bool = false;
  public static var ticks:Int = 0;
  public static function enabled():Bool return active;
  public static function tick(elapsed:Float):Bool { ticks++; return false; }
}
class CodenameModRuntime {
  public static var globalUpdates:Int = 0;
  public static var exits:Int = 0;
  public static var activeOwner:String = "owner";
  public static function isActiveOwner(root:String):Bool return root == activeOwner;
  public static function updateGlobal(elapsed:Float):Void globalUpdates++;
  public static function exitToNativeMenu():Void exits++;
}
class MusicBeatState {
  public var baseUpdates:Int = 0;
  public var afterBaseUpdate:Void->Void;
  public function new() {}
  public function update(elapsed:Float):Void {
    baseUpdates++;
    if (afterBaseUpdate != null) afterBaseUpdate();
  }
}
class FakeRuntime {
  public var updates:Int = 0;
  public var postUpdates:Int = 0;
  public function new() {}
  public function update(elapsed:Float):Void updates++;
  public function postUpdate(elapsed:Float):Void postUpdates++;
}
class SmokeEntryState {
  public function new() {}
  public function update(elapsed:Float):Void RuntimeSmokeHarness.tick(elapsed);
}
class Main extends MusicBeatState {
  public var runtime:FakeRuntime;
  public var ownerRoot:String = "owner";
""" + imported_update + """
  static function check(ok:Bool, reason:String):Void if (!ok) throw reason;
  static function main():Void {
    RuntimeSmokeHarness.active = true;
    var entry = new SmokeEntryState();
    entry.update(0.016);
    check(RuntimeSmokeHarness.ticks == 1, "entry state did not tick smoke clock");

    var imported = new Main();
    imported.runtime = new FakeRuntime();
    imported.update(0.016);
    check(RuntimeSmokeHarness.ticks == 2,
      "imported state did not continue the smoke clock exactly once");
    check(CodenameModRuntime.globalUpdates == 1
      && imported.runtime.updates == 1 && imported.runtime.postUpdates == 1
      && imported.baseUpdates == 1,
      "handoff tick disrupted imported state update phases");

    imported.afterBaseUpdate = function() CodenameModRuntime.activeOwner = "replacement-owner";
    imported.update(0.016);
    check(imported.runtime.postUpdates == 1,
      "outgoing owner ran postUpdate after the substate switched owners");
    check(RuntimeSmokeHarness.ticks == 3, "owner switch disrupted smoke handoff tick");

    RuntimeSmokeHarness.active = false;
    imported.update(0.016);
    check(RuntimeSmokeHarness.ticks == 3, "ordinary imported state ticked smoke harness");
    FlxG.keys = {justPressed:{F10:true}};
    RuntimeSmokeHarness.active = true;
    imported.update(0.016);
    check(CodenameModRuntime.exits == 1 && RuntimeSmokeHarness.ticks == 3,
      "F10 exit path ticked after leaving the imported state");
  }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            fixture_path = Path(work) / "Main.hx"
            fixture_path.write_text(fixture, encoding="utf-8")
            result = subprocess.run(
                [str(HAXE), "-cp", str(work), "--interp", "-main", "Main"],
                cwd=work,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
