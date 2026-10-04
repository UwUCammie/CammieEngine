"""Pin pure source health magnitudes to the Psych and Nightmare Vision donors."""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND


ROOT = Path(__file__).resolve().parents[2]
DONORS = ROOT.parent / "fnf_sources"


class SourceHealthDeltaTest(unittest.TestCase):
    def test_donor_defaults_and_health_order_are_pinned(self):
        psych_note = (DONORS / "FNF-PsychEngine/source/objects/Note.hx").read_text()
        psych_play = (DONORS / "FNF-PsychEngine/source/states/PlayState.hx").read_text()
        nightmare_note = (
            DONORS / "NightmareVision/source/funkin/objects/note/Note.hx"
        ).read_text()
        nightmare_field = (
            DONORS / "NightmareVision/source/funkin/objects/note/PlayField.hx"
        ).read_text()
        nightmare_play = (
            DONORS / "NightmareVision/source/funkin/states/PlayState.hx"
        ).read_text()

        self.assertIn("public var hitHealth:Float = 0.02;", psych_note)
        self.assertIn("public var missHealth:Float = 0.1;", psych_note)
        self.assertIn("missHealth = isSustainNote ? 0.25 : 0.1;", psych_note)
        self.assertIn("hitCausesMiss = true;", psych_note)
        self.assertIn("public var pressMissDamage:Float = 0.05;", psych_play)
        self.assertIn("health -= subtract * healthLoss;", psych_play)
        self.assertIn("if (guitarHeroSustains && note.isSustainNote) gainHealth = false;", psych_play)

        self.assertIn("public var hitHealth:Float = 0.023;", nightmare_note)
        self.assertIn("public var missHealth:Float = 0.0475;", nightmare_note)
        self.assertIn("missHealth = isSustainNote ? 0.1 : 0.3;", nightmare_note)
        self.assertIn("public var holdSubdivisions:Int = 1;", nightmare_play)
        self.assertIn("note.hitHealth * PlayState.instance.healthGain * susMult", nightmare_field)
        self.assertIn("note.missHealth * PlayState.instance.healthLoss * susMult", nightmare_field)
        self.assertIn("health -= 0.05 * PlayState.instance.healthLoss;", nightmare_field)

    def test_hit_miss_and_press_magnitudes(self):
        source = (ROOT / "source/SourceHealthDelta.hx").read_text()
        fixture = r'''
class SourceHealthDeltaFixture {
  static function near(actual:Float, expected:Float, label:String):Void {
    if (Math.abs(actual - expected) > 0.000001)
      throw label + ': got ' + actual + ', expected ' + expected;
  }

  static function main():Void {
    near(SourceHealthDelta.hit(false, null), 0.02, 'Psych default tap hit');
    near(SourceHealthDelta.hit(false, 0.04, 2, 3), 0.24, 'Psych owner and native factors');
    near(SourceHealthDelta.hit(false, 0.04, 2, 3, true), 0.24,
      'Psych sustain hit without guitar-hero mode');
    near(SourceHealthDelta.hit(false, 0.04, 2, 3, true, 4, true), 0,
      'Psych guitar-hero sustain hit');
    near(SourceHealthDelta.hit(false, 0, 2, 3), 0, 'Psych explicit zero');

    near(SourceHealthDelta.hit(true, null), 0.023, 'Nightmare default tap hit');
    near(SourceHealthDelta.hit(true, 0.046, 2, 3), 0.276,
      'Nightmare owner and native factors');
    near(SourceHealthDelta.hit(true, null, 2, 3, true, 4), 0.0345,
      'Nightmare subdivided sustain hit');
    near(SourceHealthDelta.hit(true, 0, 2, 3, true, 4), 0,
      'Nightmare explicit zero');

    near(SourceHealthDelta.miss(false, null), 0.1, 'Psych default note miss');
    near(SourceHealthDelta.miss(false, 0.25, 2, 3, true, 4), 1.5,
      'Psych authored sustain miss without subdivision');
    near(SourceHealthDelta.miss(false, null, 2, 1, false, 1), 0.2,
      'Psych note miss owner factor and ignored native modifier');
    near(SourceHealthDelta.miss(true, null), 0.0475, 'Nightmare default note miss');
    near(SourceHealthDelta.miss(true, 0.1, 2, 3, true, 4), 0.15,
      'Nightmare subdivided authored sustain miss');
    near(SourceHealthDelta.miss(true, 0, 2, 3, true, 4), 0,
      'Nightmare explicit zero');

    near(SourceHealthDelta.pressMiss(), 0.05, 'empty keypress default');
    near(SourceHealthDelta.pressMiss(2), 0.1, 'empty keypress owner factor');
    near(SourceHealthDelta.pressMiss(2, 0.2), 0.4,
      'Psych authored pressMissDamage override');
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            folder_path = Path(folder)
            (folder_path / "SourceHealthDelta.hx").write_text(source, newline="\n")
            (folder_path / "SourceHealthDeltaFixture.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "SourceHealthDeltaFixture", "--interp"],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
