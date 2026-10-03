"""Destination-only retention records remain safe and deterministic."""
from haxe_test_support import HAXE_COMMAND

import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
TMP_ROOT = ROOT / "tmp"
HAXE = ROOT / ".tools/haxe/haxe"


class CompatOverlayManifestTest(unittest.TestCase):
    def test_retained_overlay_round_trip_and_path_sanitization(self):
        main = r'''import CompatScriptManifest.CompatScriptManifestData;
class Main {
  static function fail(message:String):Void throw message;
  static function main() {
    var data:CompatScriptManifestData = {
      version: 1,
      roots: [],
      overlays: [{
        engine: "Legacy FNF/Polymod",
        mod: "introMod",
        operation: "_append",
        kind: "textAppend",
        order: 4,
        relativePath: "data/introText.txt",
        targetPath: "data/introText.txt",
        provenance: "introMod/_append/data/introText.txt",
        reason: "missing-append-base",
        payload: "tail"
      }, {
        engine: "bad",
        mod: "bad",
        operation: "_merge",
        kind: "jsonPatch",
        relativePath: "../escape.json",
        targetPath: "data/escape.json",
        provenance: "bad",
        reason: "bad",
        payload: "[]"
      }]
    };
    var normalized = CompatScriptManifest.parse(CompatScriptManifest.stringify(data));
    if (normalized.overlays == null || normalized.overlays.length != 1)
      fail("unsafe overlay record was retained");
    var record = normalized.overlays[0];
    if (record.provenance != "introMod/_append/data/introText.txt"
      || record.targetPath != "data/introText.txt" || record.payload != "tail"
      || record.order != 4)
      fail("retained overlay fields changed");
    var duplicate = CompatScriptManifest.parse(CompatScriptManifest.stringify({
      version: 1, roots: [], overlays: [record, record]
    }));
    if (duplicate.overlays == null || duplicate.overlays.length != 1)
      fail("retained overlay deduplication");
  }
}'''
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as folder:
            folder_path = Path(folder)
            (folder_path / "Main.hx").write_text(main, newline='\n')
            env = os.environ.copy()
            env["TMPDIR"] = str(TMP_ROOT)
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(folder_path),
                 "--run", "Main"],
                cwd=folder_path,
                capture_output=True,
                text=True,
                env=env,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
