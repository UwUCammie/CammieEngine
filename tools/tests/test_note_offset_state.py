"""Offscreen regression for script-authored absolute Note.offset writes."""
from haxe_test_support import HAXE_COMMAND

import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class NoteOffsetStateTest(unittest.TestCase):
    def test_independent_absolute_writes_survive_repeated_hitbox_scale_and_frame_updates(self):
        source = r'''
class Main {
  static function fail(message:String):Void throw message;
  static function same(actual:Float, expected:Float, label:String):Void {
    if (Math.abs(actual - expected) > 0.00001) fail(label + ": " + actual + " != " + expected);
  }
  static function main() {
    var state = new NoteOffsetState();
    // Construction's own offsets are recorded without being mistaken for
    // script writes. Flixel's native scale hitbox produces these bases.
    state.capture(0, 0, false);
    state.finish(261.5, 47);
    same(state.x, 261.5, "style X base");
    same(state.y, 47, "style Y base");
    // Repeated native updateHitbox calls must use the newly computed base.
    state.capture(state.x, state.y, true);
    state.finish(241.5, 52);
    same(state.x, 241.5, "X follows receptor scale");
    same(state.y, 52, "Y follows frame change");
    // A donor callback writes only Y as an absolute FlxPoint value.
    state.capture(state.x, 90, true);
    state.finish(231.5, 57);
    same(state.x, 231.5, "untouched X still follows style");
    same(state.y, 90, "script absolute Y");
    for (i in 0...3) {
      state.capture(state.x, state.y, true);
      state.finish(231.5 - i * 10, 62 + i);
      same(state.x, 231.5 - i * 10, "X update " + i);
      same(state.y, 90, "Y no drift " + i);
    }
    // A later script can independently set X without changing the Y owner.
    state.capture(45, state.y, true);
    state.finish(180, 80);
    same(state.x, 45, "script absolute X");
    same(state.y, 90, "Y retained");
    state.capture(state.x, state.y, true);
    state.finish(200, 100);
    same(state.x, 45, "X survives animation frame");
    same(state.y, 90, "Y survives animation frame");
    var untouched = new NoteOffsetState();
    untouched.capture(0, 0, false);
    untouched.finish(10, 20);
    untouched.capture(10, 20, true);
    untouched.finish(30, 40);
    same(untouched.x, 30, "ordinary note X");
    same(untouched.y, 40, "ordinary note Y");
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "Main.hx").write_text(source, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                 "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_note_tracks_external_writes_around_flixel_reset(self):
        note = (ROOT / "source/Note.hx").read_text()
        method = note[note.index("override public function updateHitbox():Void"):]
        method = method[:method.index("\n\tpublic function switchType")]
        self.assertLess(method.index("offsetState.capture"), method.index("super.updateHitbox()"))
        self.assertLess(method.index("super.updateHitbox()"), method.index("offsetState.finish"))
        self.assertIn("offset.set(offsetState.x, offsetState.y)", method)
        self.assertIn("offsetWritesReady = true", note)


if __name__ == "__main__":
    unittest.main()
