"""Psych Function_Stop must keep the PlayState end gate until handoff."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class PsychEndSongLifecycleTest(unittest.TestCase):
    def test_script_holds_and_hxc_outro_releases_the_end_gate(self):
        with tempfile.TemporaryDirectory(prefix="psych-end-lifecycle-", dir=ROOT / "tmp") as folder:
            work = Path(folder)
            (work / "Main.hx").write_text(r'''class Main {
  static function check(value:Bool, message:String):Void if (!value) throw message;
  static function main():Void {
    check(PsychEndSongLifecycle.selectedDisposition(false, true)
      == PsychEndSongLifecycle.HOLD_FOR_SCRIPT,
      "Psych Function_Stop must keep beat, step, and pause gates held");
    check(PsychEndSongLifecycle.selectedDisposition(false, false)
      == PsychEndSongLifecycle.CONTINUE_NATIVE,
      "ordinary script callback must continue native ending");
    check(PsychEndSongLifecycle.selectedDisposition(true, false)
      == PsychEndSongLifecycle.RELEASE_FOR_OUTRO,
      "HXC event-only cancellation must return control to its outro");
    check(PsychEndSongLifecycle.providerDisposition(false, true)
      == PsychEndSongLifecycle.HOLD_FOR_SCRIPT,
      "global results provider must hold the PlayState until its later handoff");
    check(PsychEndSongLifecycle.providerDisposition(false, false)
      == PsychEndSongLifecycle.CONTINUE_NATIVE,
      "provider without a results hold must continue native ending");
    check(PsychEndSongLifecycle.providerDisposition(true, false)
      == PsychEndSongLifecycle.HOLD_FOR_SCRIPT,
      "provider event cancellation must keep the results host alive");
  }
}''', encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--run", "Main"],
                cwd=work,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_playstate_keeps_and_releases_the_end_gate_by_disposition(self):
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        self.assertIn("PsychEndSongLifecycle.selectedDisposition(", play_state)
        self.assertIn("PsychEndSongLifecycle.providerDisposition(", play_state)
        self.assertIn("endingSong = true;\n\t\t\t\tcanPause = false;", play_state)
        self.assertIn("endingSong = false;\n\t\t\t\tcanPause = canPauseBeforeEnd;", play_state)

    def test_held_ending_keeps_post_update_callbacks_for_script_handoff(self):
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        update_start = play_state.index("override public function update(elapsed:Float)")
        held_end = play_state.index("if (endingSong) {", update_start)
        camera_update = play_state.index("if (generatedMusic && PlayState.SONG.notes[curSection]", held_end)
        held_branch = play_state[held_end:camera_update]
        self.assertIn("callAllHScript('updatePost', [elapsed]);", held_branch)
        self.assertIn("callCodenameScripts('postUpdate', [elapsed]);", held_branch)
        self.assertLess(held_branch.index("callAllHScript('updatePost', [elapsed]);"),
                        held_branch.index("return;"))


if __name__ == "__main__":
    unittest.main()
