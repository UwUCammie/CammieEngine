"""Executable and donor-source contracts for source note-miss duplicate cleanup."""

from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath


ROOT = Path(__file__).resolve().parents[2]
PSYCH_PLAYSTATE = FixturePath(
    "C:/Users/uwucammie/Documents/coding/FNF/fnf_sources/FNF-PsychEngine/source/states/PlayState.hx"
)
NV_PLAYSTATE = FixturePath(
    "C:/Users/uwucammie/Documents/coding/FNF/fnf_sources/NightmareVision/source/funkin/states/PlayState.hx"
)
NV_PLAYFIELD = FixturePath(
    "C:/Users/uwucammie/Documents/coding/FNF/fnf_sources/NightmareVision/source/funkin/objects/note/PlayField.hx"
)


class SourceMissDuplicatesTest(unittest.TestCase):
    def run_haxe(self, fixture: str) -> None:
        with tempfile.TemporaryDirectory(prefix="source-miss-duplicates-", dir=ROOT / "tmp") as folder:
            scratch = FixturePath(folder)
            (scratch / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(scratch), "--main", "Main", "--interp"],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_actual_selector_matches_psych_strict_runtime_rule(self):
        fixture = r'''
class FakeNote {
 public var mustPress:Bool;
 public var noteData:Int;
 public var isSustainNote:Bool;
 public var strumTime:Float;
 public var exists:Bool;
 public var alive:Bool;
 public function new(time:Float, lane:Int=1, sustain:Bool=false,
   player:Bool=true, exists:Bool=true, alive:Bool=true) {
  strumTime=time; noteData=lane; isSustainNote=sustain; mustPress=player;
  this.exists=exists; this.alive=alive;
 }
}
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var missed = new FakeNote(10);
  var justBefore = new FakeNote(9.001);
  var justAfter = new FakeNote(10.999);
  var exactBefore = new FakeNote(9);
  var exactAfter = new FakeNote(11);
  var otherLane = new FakeNote(10, 2);
  var otherSustain = new FakeNote(10, 1, true);
  var dead = new FakeNote(10, 1, false, true, true, false);
  var nonexistent = new FakeNote(10, 1, false, true, false, true);
  var candidateNotPlayerOwned = new FakeNote(10, 1, false, false);
  var candidates:Array<Dynamic> = [missed, justBefore, justAfter, exactBefore, exactAfter,
    otherLane, otherSustain, dead, nonexistent, candidateNotPlayerOwned];
  var selected = SourceMissDuplicates.select(missed, candidates, false);
  check(selected.length == 3 && selected[0] == justBefore && selected[1] == justAfter
    && selected[2] == candidateNotPlayerOwned,
    'selector keeps same-lane/sustain live siblings strictly within 1ms, in member order');
  check(justBefore.exists && justBefore.alive && candidateNotPlayerOwned.alive,
    'selection does not invalidate or otherwise mutate candidates');

  missed.mustPress = false;
  check(SourceMissDuplicates.select(missed, candidates, false).length == 0,
    'Psych only removes duplicates for a player-owned missed note');
  missed.mustPress = true;
  check(SourceMissDuplicates.select(missed, candidates, true).length == 0,
    'NV runtime misses never remove sibling notes');
  check(SourceMissDuplicates.select(null, candidates, false).length == 0
    && SourceMissDuplicates.select(missed, null, false).length == 0,
    'null note or member array produces no runtime cleanup candidates');
 }
}
'''
        self.run_haxe(fixture)

    def test_donor_duplicate_contracts_are_distinct(self):
        required = [PSYCH_PLAYSTATE, NV_PLAYSTATE, NV_PLAYFIELD]
        if not all(path.is_file() for path in required):
            self.skipTest("mounted Psych and Nightmare Vision source donors are unavailable")

        psych = PSYCH_PLAYSTATE.read_text(encoding="utf-8")
        self.assertRegex(
            psych,
            re.compile(
                r"daNote\s*!=\s*note\s*&&\s*daNote\.mustPress\s*"
                r"&&\s*daNote\.noteData\s*==\s*note\.noteData\s*"
                r"&&\s*daNote\.isSustainNote\s*==\s*note\.isSustainNote\s*"
                r"&&\s*Math\.abs\(daNote\.strumTime\s*-\s*note\.strumTime\)\s*<\s*1",
                re.S,
            ),
        )

        nv_playfield = NV_PLAYFIELD.read_text(encoding="utf-8")
        miss_start = nv_playfield.index("function noteMiss(note:Note, field:PlayField)")
        miss_end = nv_playfield.index("\n\tfunction noteMissPress(", miss_start)
        self.assertNotIn("forEachAlive", nv_playfield[miss_start:miss_end])

        nv_play = NV_PLAYSTATE.read_text(encoding="utf-8")
        self.assertRegex(nv_play, r"final killDifference:Float\s*=\s*3")
        self.assertRegex(
            nv_play,
            re.compile(r"Math\.abs\(lastNote\[0\]\s*-\s*note\[0\]\)\s*<\s*killDifference", re.S),
        )


if __name__ == "__main__":
    unittest.main()
