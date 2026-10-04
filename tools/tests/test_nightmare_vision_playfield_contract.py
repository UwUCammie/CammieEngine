"""Pin the shared Nightmare Vision field and sustain-input contracts."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
import re


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class NightmareVisionPlayFieldContractTest(unittest.TestCase):
    def test_checked_in_donor_has_the_pinned_field_and_grace_rules(self):
        donor = ROOT.parent / "fnf_sources/NightmareVision/source/funkin"
        if not donor.is_dir():
            self.skipTest("supplied Nightmare Vision source unavailable")
        play_field = (donor / "objects/note/PlayField.hx").read_text()
        play_state = (donor / "states/PlayState.hx").read_text()
        strum_note = (donor / "objects/note/StrumNote.hx").read_text()
        normalized_field = re.sub(r"\s+", " ", play_field)
        normalized_state = re.sub(r"\s+", " ", play_state)
        normalized_strum = re.sub(r"\s+", " ", strum_note)

        self.assertIn("singers.remove(owner); singers.unshift(owner);", normalized_field)
        self.assertIn("public var playAnims:Bool = true;", normalized_field)
        self.assertIn("public var noteSplashes:Bool = false;", normalized_field)
        self.assertIn("return (playerControls && inControl && !autoPlayed && (owner == null || !owner.stunned));",
                      normalized_field)
        self.assertIn("!daNote.alive || !daNote.isSustainNote || daNote.blockHit || daNote.tooLate || daNote.playField.autoPlayed",
                      normalized_state)
        self.assertIn("!daNote.playField.inControl || !daNote.playField.playerControls", normalized_state)
        self.assertIn("!daNote.ignoreNote && !daNote.canMiss && !daNote.tailState.missed && (!daNote.isSustainNote || daNote.strum.coyoteTime <= 0) && !endingSong",
                      normalized_state)
        self.assertIn("coyoteTime > 0 && !holding", normalized_strum)
        self.assertIn("Math.max(coyoteTime - elapsed, 0)", normalized_strum)

    def test_field_api_ownership_and_sustain_grace_match_source(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        fixture = r'''
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var defaultAutoplay = false;
  var player = new NightmareVisionPlayFieldView(0, function() return defaultAutoplay);
  check(player.ID == 0 && player.playerControls, 'field 0 is player-controlled');
  check(player.playAnims && player.showRatings && !player.noteSplashes && player.holdDropLeniency == 1 / 3,
   'source field defaults changed');
  player.showRatings = false;
  check(!player.showRatings, 'showRatings should remain a live mutable field flag');
  check(player.canInput(), 'ordinary player field accepts input');

  var bf = {stunned:false};
  var gf = {stunned:false};
  player.owner = bf;
  check(player.singers.length == 1 && player.singers[0] == bf,
   'owner setter must seed singers');
  player.singers.push(gf);
  player.owner = gf;
  check(player.singers.length == 2 && player.singers[0] == gf && player.singers[1] == bf,
   'owner changes must move owner to singer front');
  gf.stunned = true;
  check(!player.canInput(), 'stunned owner cannot input');
  gf.stunned = false;
  player.autoPlayed = true;
  check(!player.canInput(), 'autoplay field cannot receive manual input');
  player.autoPlayed = false;
  player.inControl = false;
  check(!player.canInput(), 'locked field cannot receive input');

  var opponent = new NightmareVisionPlayFieldView(1, function() return true);
  check(!opponent.playerControls && opponent.autoPlayed && !opponent.canInput(),
   'field 1 is an autoplay opponent field');
  var extra = new NightmareVisionPlayFieldView(2, function() return true);
  check(extra.playerControls, 'source extra fields retain playerControls ownership');

  check(NightmareVisionSustainInput.shouldProcessHold(false, true, true,
   false, false, false, true, true), 'eligible player hold was skipped');
  check(!NightmareVisionSustainInput.shouldProcessHold(true, true, true,
   false, false, false, true, true), 'stunned player processed holds');
  check(!NightmareVisionSustainInput.shouldProcessHold(false, true, true,
   false, false, true, true, true), 'autoplay field processed manual holds');
  check(!NightmareVisionSustainInput.shouldProcessHold(false, true, true,
   false, false, false, false, true), 'uncontrolled field processed holds');
  check(NightmareVisionSustainInput.shouldHitHold(false, true, 100, 100),
   'hold hit must include the exact strum-time boundary');
  check(!NightmareVisionSustainInput.shouldHitHold(false, true, 99.99, 100),
   'hold hit ran before strum time');
  check(NightmareVisionSustainInput.shouldMissHold(false, false, false,
   false, 0, true, false), 'released active tail misses after grace');
  check(!NightmareVisionSustainInput.shouldMissHold(false, false, false,
   false, 0.001, true, false), 'released tail misses during coyote grace');
  check(!NightmareVisionSustainInput.shouldMissHold(false, true, false,
   false, 0, true, false), 'held tail was marked missed');
  check(!NightmareVisionSustainInput.shouldMissHold(false, false, false,
   false, 0, false, false), 'inactive tail was marked missed');
  check(NightmareVisionSustainInput.shouldDispatchLateMiss(false, false,
   false, true, 0, false), 'late sustain misses when grace is over');
  check(!NightmareVisionSustainInput.shouldDispatchLateMiss(false, false,
   false, true, 0.001, false), 'late sustain respects coyote grace');
  check(NightmareVisionSustainInput.shouldDispatchLateMiss(false, false,
   false, false, 1, false), 'tap late miss ignores sustain grace');
  check(!NightmareVisionSustainInput.shouldDispatchLateMiss(false, true,
   false, false, 0, false), 'canMiss note avoids automatic late miss');
  check(!NightmareVisionSustainInput.shouldDispatchLateMiss(true, false,
   false, false, 0, false), 'ignored note avoids automatic late miss');
  check(!NightmareVisionSustainInput.shouldDispatchLateMiss(false, false,
   true, false, 0, false), 'already-missed tail is not dispatched twice');
  check(!NightmareVisionSustainInput.shouldDispatchLateMiss(false, false,
   false, false, 0, true), 'ending song suppresses late miss');
  check(NightmareVisionSustainInput.advanceCoyoteTime(0.3, 0.1, false) > 0.19
   && NightmareVisionSustainInput.advanceCoyoteTime(0.3, 0.1, false) < 0.21,
   'released coyote timer did not decay');
  check(NightmareVisionSustainInput.advanceCoyoteTime(0.3, 0.1, true) == 0.3,
   'held coyote timer should pause');
  check(NightmareVisionSustainInput.advanceCoyoteTime(0.05, 0.1, false) == 0,
   'coyote timer did not clamp at zero');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                 "-main", "Main", "--interp"],
                cwd=folder, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
