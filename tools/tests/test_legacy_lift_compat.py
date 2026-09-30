"""Regression coverage for Modding Plus's fifth note-row lift marker."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
CHART = DONOR / "modding-plus/vsfreddy_1_9_5/assets/data/slaughter/slaughter.json"


class LegacyLiftCompatibilityTest(unittest.TestCase):
    def test_song_loader_routes_the_shared_lift_adapter(self):
        song = (ROOT / "source/Song.hx").read_text()
        engine = (ROOT / "source/EngineCompat.hx").read_text()
        self.assertIn("EngineCompat.normalizeLegacyNoteRows(parsedJson", song)
        self.assertIn("public static function normalizeLegacyNoteRows", engine)
        self.assertIn("values[1] = lane + noteAmount * 4", engine)

    @unittest.skipUnless(CHART.is_file(), "mounted Modding Plus corpus is unavailable")
    def test_mounted_slaughter_lifts_become_native_lift_block(self):
        fixture = r'''
import haxe.Json;
import sys.io.File;

class LegacyLiftCorpus {
  static function fail(message:String):Void throw message;
  static function main() {
    var chart:Dynamic = Json.parse(File.getContent(Sys.args()[0]));
    var rows:Array<Dynamic> = [];
    for (section in (cast chart.song.notes:Array<Dynamic>))
      for (row in (cast section.sectionNotes:Array<Dynamic>))
        if (row.length >= 5 && row[4] == true)
          rows.push(row);
    if (rows.length != 3) fail('mounted slaughter lift corpus changed: ' + rows.length);
    for (row in rows)
      if (row[1] != 2) fail('fixture lane unexpectedly changed before normalization');

    EngineCompat.normalizeLegacyNoteRows(chart, 4);
    for (row in rows) {
      if (row[1] != 18) fail('lift lane was not moved to native block: ' + row[1]);
      if (!EngineCompat.legacyLiftRow(row)) fail('lift marker was not retained');
    }
    trace('OK');
  }
}
'''
        donor_bytes = CHART.read_bytes()
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            source = Path(folder) / "LegacyLiftCorpus.hx"
            source.write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "-cp", str(ROOT / "source"),
                 "--run", "LegacyLiftCorpus", str(CHART)],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)
        self.assertEqual(CHART.read_bytes(), donor_bytes, "donor chart was modified")


if __name__ == "__main__":
    unittest.main()
