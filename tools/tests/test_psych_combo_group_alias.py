"""Regression coverage for Psych's mounted combo-group visibility alias."""

from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")


class PsychComboGroupAliasTest(unittest.TestCase):
    def test_combo_group_visibility_uses_the_native_rating_gate(self):
        fixture = r'''
class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    if (EngineCompat.propertyPath("comboGroup.visible") != "showRatings")
      fail("comboGroup visibility was not routed to showRatings");
    if (EngineCompat.propertyPath("game.comboGroup.visible") != "showRatings")
      fail("game comboGroup visibility was not routed to showRatings");
    if (EngineCompat.propertyPath("comboGroup.alpha") != "comboGroup.alpha")
      fail("unrelated comboGroup members must remain unresolved");
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "Main.hx"
            path.write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", folder,
                 "-main", "Main", "--interp"],
                cwd=ROOT,
                env={**__import__("os").environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(DONOR.is_dir(), "mounted FNF-Example-Mods corpus is unavailable")
    def test_mounted_donor_exercises_the_exact_alias(self):
        script = DONOR / "psych/PERFEXION Demo1/data/Resonance/Note.lua"
        self.assertTrue(script.is_file())
        source = script.read_text(errors="ignore")
        calls = re.findall(
            r"setProperty\s*\(\s*['\"]comboGroup\.visible['\"]\s*,\s*false\s*\)",
            source,
            re.IGNORECASE,
        )
        self.assertEqual(len(calls), 1)

        engine = (ROOT / "source/EngineCompat.hx").read_text()
        self.assertIn("value.toLowerCase() == 'combogroup.visible'", engine)
        self.assertIn("return 'showRatings'", engine)


if __name__ == "__main__":
    unittest.main()
