"""Kade/FPS anonymous death-note conversion stays engine-level."""
from haxe_test_support import HAXE_COMMAND

import json
import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
VSTRICKY = Path(
    "/run/media/cammie/External Storage/FNF-Example-Mods/"
    "vstricky-releasebuild-v21/assets/data"
)


class KadeNoteConversionTest(unittest.TestCase):
    def _run_adapter(self, body: str, *args: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            folder_path = Path(folder)
            (folder_path / "EngineCompat.hx").write_text(
                (ROOT / "source/EngineCompat.hx").read_text()
            , newline='\n')
            (folder_path / "NoteTypeCompat.hx").write_text(
                (ROOT / "source/NoteTypeCompat.hx").read_text()
            , newline='\n')
            (folder_path / "HxcEventSpriteDescriptor.hx").write_text(
                (ROOT / "source/HxcEventSpriteDescriptor.hx").read_text()
            , newline='\n')
            (folder_path / "HxcCompatRuntime.hx").write_text(
                """class HxcCompatRuntime {
  public static function beginActiveSong():Void {}
  public static function markSongEventNativeHandled(value:Dynamic):Void {}
  public static function observeIncoming(value:Dynamic):Void {}
}
"""
            , newline='\n')
            (folder_path / "CompatScriptManifest.hx").write_text(
                """class CompatScriptManifest {
  public static inline var ROOT_PREFIX:String = 'assets/imported_mods';
}
"""
            , newline='\n')
            (folder_path / "Main.hx").write_text(body, newline='\n')
            return subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "Main", *args],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=300,
            )

    def test_named_metadata_and_engine_provenance_route_without_chart_names(self):
        main = r'''class Main {
  static function fail(message:String):Void throw message;
  static function chart(rows:Array<Dynamic>, ?engine:String):Dynamic {
    var result:Dynamic = {song:{notes:[{sectionNotes:rows}]}};
    if (engine != null) result.song.compatMetadata = {engine:engine};
    return result;
  }
  static function flagged(value:Bool):Dynamic {
    var result = chart([[0, 8, 0]], 'Kade Engine');
    result.song.convertMineToNuke = value;
    return result;
  }
  static function main() {
    if (!EngineCompat.inferMineToNuke(chart([[0, 8, 0]], 'Kade Engine'), 4))
      fail('Kade extended mine block was not promoted');
    if (EngineCompat.inferMineToNuke(chart([[0, 8, 0]], 'Unknown Engine'), 4))
      fail('unknown engine was guessed as a death-note source');
    if (!EngineCompat.inferMineToNuke(chart([[0, 0, 0, 'Death Note']], 'Unknown Engine'), 4))
      fail('explicit death note metadata was not routed');
    if (EngineCompat.inferMineToNuke(chart([[0, 8, 0, 'Mine Note']], 'Kade Engine'), 4))
      fail('explicit mine metadata did not override engine inference');
    if (EngineCompat.inferMineToNuke(flagged(false), 4))
      fail('explicit false conversion flag was ignored');
    var explicit = chart([[0, 0, 0]], 'Unknown Engine');
    explicit.song.convertMineToNuke = true;
    if (!EngineCompat.inferMineToNuke(explicit, 4))
      fail('explicit true conversion flag was ignored');
    trace('OK');
  }
}
'''
        result = self._run_adapter(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    @unittest.skipUnless(VSTRICKY.is_dir(), "mounted Kade corpus is unavailable")
    def test_mounted_kade_death_block_charts_are_detected_without_mutation(self):
        main = r'''import haxe.Json;
import sys.io.File;
class Main {
  static function main() {
    var path = Sys.args()[0];
    var before = File.getContent(path);
    var chart:Dynamic = Json.parse(before);
    if (!EngineCompat.inferMineToNuke(chart, 4, 'Kade Engine'))
      throw 'mounted Kade death-note block was not detected: ' + path;
    if (File.getContent(path) != before)
      throw 'mounted donor chart was modified: ' + path;
    trace('OK');
  }
}
'''
        files = [
            VSTRICKY / "expurgation/expurgation-hard.json",
            VSTRICKY / "hellclown/hellclown.json",
            VSTRICKY / "madness/madness.json",
        ]
        for path in files:
            if not path.is_file():
                self.skipTest(f"mounted chart is unavailable: {path}")
            chart = json.loads(path.read_text())["song"]
            lanes = {
                int(row[1])
                for section in chart.get("notes", [])
                for row in section.get("sectionNotes", [])
                if len(row) > 1 and isinstance(row[1], (int, float))
            }
            self.assertTrue(
                any(8 <= lane < 16 for lane in lanes),
                f"mounted chart no longer carries its extended hazard block: {path}",
            )
            result = self._run_adapter(main, str(path))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("OK", result.stdout + result.stderr)

    def test_song_loader_no_longer_selects_by_expurgation_filename(self):
        source = (ROOT / "source/Song.hx").read_text()
        self.assertNotIn("parsedSongName.toLowerCase() == \"expurgation\"", source)
        self.assertIn("EngineCompat.inferMineToNuke", source)
        self.assertIn("CompatScriptManifest.FILE_NAME", source)


if __name__ == "__main__":
    unittest.main()
