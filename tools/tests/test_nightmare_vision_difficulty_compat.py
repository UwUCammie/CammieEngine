"""NMV source menu difficulty declarations stay owner scoped."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class NightmareVisionDifficultyCompatTest(unittest.TestCase):
    def run_haxe(self, body, args=()):
        main = "class Main { static function main() {\n" + body + "\n} }\n"
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temp:
            temp_path = Path(temp)
            (temp_path / "Main.hx").write_text(main, encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", temp, "--run", "Main", *map(str, args)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_literal_menu_list_and_default_fallback(self):
        self.run_haxe(r'''var declared = NightmareVisionDifficultyCompat.parseMenuScript(
  "function onLoad() {\n\tDifficulty.difficulties = ['Easy', 'Normal', 'Hard', 'Encore'];\n}",
  "owner/scripts/states/FreeplayState.hx");
if (!declared.declared || declared.names.join(",") != "easy,normal,hard,encore")
  throw "literal source menu list was not parsed: " + declared.names.join(",");
var fallback = NightmareVisionDifficultyCompat.parseMenuScript(
  "Difficulty.difficulties = makeDynamicList();");
if (fallback.declared || fallback.names.join(",") != "easy,normal,hard"
  || fallback.diagnostic.indexOf("nightmare-vision-difficulty-menu-fallback") < 0)
  throw "dynamic list did not use diagnosed source defaults";
''')

    def test_each_selected_owner_uses_its_own_freeplay_script(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as owner_folder:
            self.run_haxe(r'''
var parent = Sys.args()[0];
var first = parent + "/nmv-owner-one";
var second = parent + "/nmv-owner-two";
for (owner in [first, second]) {
  sys.FileSystem.createDirectory(owner);
  sys.FileSystem.createDirectory(owner + "/scripts");
  sys.FileSystem.createDirectory(owner + "/scripts/states");
}
sys.io.File.saveContent(first + "/scripts/states/FreeplayState.hx",
  "Difficulty.difficulties = ['Easy', 'Normal', 'Hard'];");
sys.io.File.saveContent(second + "/scripts/states/FreeplayState.hx",
  "Difficulty.difficulties = ['Normal', 'Hard', 'Mania'];");
var firstMenu = NightmareVisionDifficultyCompat.fromSourceRoot(first);
var secondMenu = NightmareVisionDifficultyCompat.fromSourceRoot(second);
if (!firstMenu.declared || !secondMenu.declared
  || NightmareVisionDifficultyCompat.allows(firstMenu.names, "crowd")
  || !NightmareVisionDifficultyCompat.allows(secondMenu.names, "mania")
  || NightmareVisionDifficultyCompat.allows(secondMenu.names, "easy"))
  throw "selected owner menu metadata leaked across roots";
''', [owner_folder])


if __name__ == "__main__":
    unittest.main()
