"""Regression coverage for Psych Character healthColorArray reads."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")


class PsychHealthColorArrayTest(unittest.TestCase):
    def test_mounted_silhouette_reads_use_the_executable_engine_adapter(self):
        script = DONOR / "psych/PERFEXION Demo1/custom_events/coloredSilhouette.lua"
        if not script.is_file():
            self.skipTest("mounted PERFEXION donor is unavailable")

        source = script.read_text(errors="ignore")
        self.assertEqual(
            len(re.findall(r"healthColorArray\[[012]\]", source)),
            9,
        )

        play_state = (ROOT / "source/PlayState.hx").read_text()
        engine = (ROOT / "source/EngineCompat.hx").read_text()
        self.assertIn("EngineCompat.psychHealthColorArray", play_state)
        self.assertIn("public static function psychHealthColorArray", engine)

        fixture = r'''
class PsychHealthColorArraySmoke {
  static function check(value:Bool, message:String):Void {
    if (!value) throw message;
  }

  static function main() {
    var player:Dynamic = {playerColor: 0xFF010203};
    var dad:Dynamic = {enemyColor: 0xFF040506};
    var gf:Dynamic = {enemyColor: 0xFF070809};
    var playerIcon:Dynamic = {healthColors: [0xFFA1B2C3]};
    var dadIcon:Dynamic = {healthColors: [0xFFD4E5F6]};

    var playerRgb = EngineCompat.psychHealthColorArray(
      player, player, dad, gf, playerIcon, dadIcon);
    check(playerRgb.length == 3 && playerRgb[0] == 0xA1
      && playerRgb[1] == 0xB2 && playerRgb[2] == 0xC3,
      "player icon RGB was not adapted");

    var dadRgb = EngineCompat.psychHealthColorArray(
      dad, player, dad, gf, playerIcon, dadIcon);
    check(dadRgb[0] == 0xD4 && dadRgb[1] == 0xE5 && dadRgb[2] == 0xF6,
      "opponent icon RGB was not adapted");

    var gfRgb = EngineCompat.psychHealthColorArray(
      gf, player, dad, gf, null, null);
    check(gfRgb[0] == 7 && gfRgb[1] == 8 && gfRgb[2] == 9,
      "GF role RGB fallback was not adapted");

    var direct:Dynamic = {healthColorArray: [11, 22, 33]};
    var directRgb = EngineCompat.psychHealthColorArray(
      direct, player, dad, gf, null, null);
    check(directRgb[0] == 11 && directRgb[1] == 22 && directRgb[2] == 33,
      "native healthColorArray was not preserved");
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            folder = Path(folder)
            (folder / "PsychHealthColorArraySmoke.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(folder), "-cp", str(ROOT / "source"),
                 "--run", "PsychHealthColorArraySmoke"],
                cwd=ROOT,
                env={**__import__("os").environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
