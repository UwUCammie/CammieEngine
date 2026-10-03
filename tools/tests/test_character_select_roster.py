"""Character select only offers identities with their own installed visual."""
from haxe_test_support import HAXE_COMMAND

import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"


class CharacterSelectRosterTest(unittest.TestCase):
    def test_missing_release_media_and_borrowed_aliases_are_hidden(self):
        fixture = r'''
class Main {
  static function main() {
    var registry:Dynamic = {
      missing: {like: "missing"},
      installed: {like: "installed"},
      borrowed: {like: "installed"},
      base: {like: "base"}
    };
    var newMediaInstalled = false;
    var resolve = function(name:String):Dynamic return switch (name) {
      case "missing": newMediaInstalled
        ? {complete: true, assetName: "missing"}
        : {complete: false, assetName: null};
      case "borrowed": {complete: true, assetName: "installed"};
      case "installed": {complete: true, assetName: "installed"};
      case "base": {complete: true, assetName: "base"};
      default: null;
    };
    var clean = CharacterSelectRoster.availableNames(registry, resolve);
    if (clean.join("|") != "base|installed")
      throw "clean release exposed unavailable character: " + clean.join("|");
    newMediaInstalled = true;
    var refreshed = CharacterSelectRoster.availableNames(registry, resolve);
    if (refreshed.join("|") != "base|installed|missing")
      throw "installed character did not appear after refresh: " + refreshed.join("|");
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder, "-main", "Main", "--interp"],
                cwd=folder,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        picker = (ROOT / "source" / "ChooseCharState.hx").read_text()
        self.assertIn("characters = CharacterSelectRoster.availableNames(charJson, Song.resolveCharacterVisual)", picker)
        self.assertNotIn("if (characters == null) {", picker)


if __name__ == "__main__":
    unittest.main()
