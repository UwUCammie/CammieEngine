from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class NightmareVisionPlayfieldLayoutTest(unittest.TestCase):
    def test_layout_matches_source_mod_manager_for_field_ids_key_counts_and_scroll(self):
        main = r'''class Main {
  static function near(actual:Float, expected:Float, label:String):Void {
    if (Math.abs(actual - expected) > 0.0001)
      throw label + ": expected " + expected + ", got " + actual;
  }

  static function main() {
    for (screenWidth in [1280.0, 1920.0]) {
      for (swagWidth in [100.0, 112.0]) {
        for (keys in [1, 3, 4, 6, 9]) {
          for (fieldCount in [2, 3, 5]) {
            for (field in 0...fieldCount) {
              var center:Float = switch (field) {
                case 0: screenWidth - swagWidth * (keys / 2) - 100 - 3;
                case 1: swagWidth * (keys / 2) + 100 - 3;
                default: screenWidth * 0.5 - 3;
              };
              near(NightmareVisionPlayfieldLayout.centerX(field, keys, screenWidth, swagWidth),
                center, "field center");
              for (direction in 0...keys) {
                var expectedX = center + swagWidth * (direction - (keys / 2) + 0.5);
                near(NightmareVisionPlayfieldLayout.receptorCenterX(field, direction, keys,
                  screenWidth, swagWidth), expectedX, "receptor center");
              }
            }
          }
        }
        for (screenHeight in [720.0, 1080.0]) {
          var baseY = swagWidth * 0.5 + 50;
          near(NightmareVisionPlayfieldLayout.receptorCenterY(screenHeight, swagWidth, false),
            baseY, "upscroll receptor center");
          near(NightmareVisionPlayfieldLayout.receptorCenterY(screenHeight, swagWidth, true),
            screenHeight - baseY, "downscroll receptor center");
        }
      }
    }
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(main)
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
