"""Executable coverage for Modding Plus's extended note-row ABI."""
from haxe_test_support import HAXE_COMMAND

import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
CHART = Path(
    "/run/media/cammie/External Storage/modding-plus-fnf/assets/data/"
    "fragmented surreality/fragmented surreality.json"
)


class LegacyExtendedNoteRowsTest(unittest.TestCase):
    def test_playstate_applies_the_shared_adapter_to_heads_and_sustains(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        self.assertGreaterEqual(
            source.count("EngineCompat.applyLegacyNoteRow("),
            2,
            "both generated note kinds must retain authored row metadata",
        )
        self.assertIn("legacyNoteAnimSuffix(songNotes)", source)

        note = (ROOT / "source/Note.hx").read_text()
        self.assertIn("authoredAnimSuffix:String = null", note)
        self.assertIn("animSuffix = StringTools.trim(authoredAnimSuffix)", note)

    @unittest.skipUnless(CHART.is_file(), "mounted Modding Plus corpus is unavailable")
    def test_mounted_fragmented_surrealty_preserves_health_and_timing_columns(self):
        fixture = r'''
import haxe.Json;
import sys.io.File;

class LegacyExtendedRowsCorpus {
	static function fail(message:String):Void throw message;

	static function main() {
		var path = Sys.args()[0];
		var before = File.getContent(path);
		var chart:Dynamic = Json.parse(before);
		var rows = 0;
		var timingRows = 0;
		var zeroHealRows = 0;
		for (section in (cast chart.song.notes:Array<Dynamic>)) {
			for (row in (cast section.sectionNotes:Array<Dynamic>)) {
				if (row.length <= 8 || row[1] == -1)
					continue;
				var note:Dynamic = {
					dontEdit: false,
					mineNote: false,
					nukeNote: false,
					isLiftNote: false,
					healMultiplier: 1.0,
					damageMultiplier: 1.0,
					consistentHealth: false,
					timingMultiplier: 1.0,
					shouldBeSung: true,
					ignoreHealthMods: false
				};
				EngineCompat.applyLegacyNoteRow(note, row);
				var timing = Std.parseFloat(Std.string(row[8]));
				if (Math.isNaN(timing) || note.timingMultiplier != timing)
					fail('timing multiplier was dropped at row ' + rows);
				if (Std.string(row[5]) == '0') {
					zeroHealRows++;
					if (note.healMultiplier != 0)
						fail('zero heal multiplier was dropped at row ' + rows);
				}
				if (timing != 1)
					timingRows++;
				rows++;
			}
		}
		if (rows < 200 || timingRows < 200 || zeroHealRows != rows)
			fail('mounted extended-row corpus unexpectedly changed: rows=' + rows
				+ ', timing=' + timingRows + ', heal=' + zeroHealRows);

		var authored:Dynamic = {
			dontEdit: false,
			mineNote: false,
			nukeNote: false,
			isLiftNote: false,
			healMultiplier: 1.0,
			damageMultiplier: 1.0,
			consistentHealth: false,
			timingMultiplier: 1.0,
			shouldBeSung: true,
			ignoreHealthMods: false
		};
		EngineCompat.applyLegacyNoteRow(authored,
			[0, 0, 0, false, false, 0.25, 1.5, true, 2.5, false, true]);
		if (authored.healMultiplier != 0.25 || authored.damageMultiplier != 1.5
			|| authored.consistentHealth != true || authored.timingMultiplier != 2.5
			|| authored.shouldBeSung != false || authored.ignoreHealthMods != true)
			fail('one or more authored optional note fields were dropped');

		// Hazard/noteInfo semantics own these fields and must not be overwritten
		// by optional chart columns.
		var blocked:Dynamic = {
			dontEdit: false,
			mineNote: true,
			nukeNote: false,
			isLiftNote: false,
			healMultiplier: 3.0,
			damageMultiplier: 4.0,
			consistentHealth: true,
			timingMultiplier: 5.0,
			shouldBeSung: false,
			ignoreHealthMods: true
		};
		EngineCompat.applyLegacyNoteRow(blocked, [0, 0, 0, false, false, 0, 0, false, 6, true, false]);
		if (blocked.healMultiplier != 3 || blocked.damageMultiplier != 4
			|| blocked.consistentHealth != true || blocked.timingMultiplier != 5
			|| blocked.shouldBeSung != false || blocked.ignoreHealthMods != true)
			fail('hazard metadata was overwritten');
		if (EngineCompat.legacyNoteAnimSuffix([0, 0, 0, false, false, 1, 1, false, 1, true, false, ' alt']) != 'alt')
			fail('authored animation suffix was not retained');
		if (File.getContent(path) != before)
			fail('donor chart was modified');
		trace('OK|rows=' + rows + '|timing=' + timingRows);
	}
}
'''
        donor_bytes = CHART.read_bytes()
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            source = Path(folder) / "LegacyExtendedRowsCorpus.hx"
            source.write_text(fixture, newline='\n')
            result = subprocess.run(
                [
                    *HAXE_COMMAND,
                    "-cp",
                    folder,
                    "-cp",
                    str(ROOT / "source"),
                    "--run",
                    "LegacyExtendedRowsCorpus",
                    str(CHART),
                ],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK|rows=", result.stdout + result.stderr)
        self.assertEqual(CHART.read_bytes(), donor_bytes, "donor chart was modified")


if __name__ == "__main__":
    unittest.main()
