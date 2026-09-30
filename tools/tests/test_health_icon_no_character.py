"""The V-Slice missing-character sentinel must not draw a substitute icon."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.tests.test_psych_character_scope import extract_method


ROOT = Path(__file__).resolve().parents[2]


class HealthIconNoCharacterTest(unittest.TestCase):
    def test_sentinel_uses_native_default_only_as_hidden_backing_icon(self):
        source = (ROOT / "source/HealthIcon.hx").read_text()
        character = (ROOT / "source/Character.hx").read_text()
        icon_request = source[source.index("\tstatic function iconRequestForCharacter("):
                              source.index("\n\t/** Named HXC alias")].strip()
        is_no_girlfriend = extract_method(character, "public static function isNoGirlfriend")
        fixture = (
            "using StringTools;\nclass Character {\n" + is_no_girlfriend + "\n}\n"
            "class Main {\n" + icon_request + r'''
 static function check(ok:Bool, why:String):Void if (!ok) throw why;
 static function main():Void {
  for (id in ["no-gf", "nogf", "no_gf", "NO GF"]) {
   var result = iconRequestForCharacter(id, "assets/imported_mods/owner", true);
   check(result.hidden && result.name == "face" && result.ownerRoot == "",
    "missing character drew an icon or inherited a donor owner: " + id);
  }
  var menu = iconRequestForCharacter("no-gf", "assets/imported_mods/owner", false);
  check(!menu.hidden && menu.name == "no-gf"
   && menu.ownerRoot == "assets/imported_mods/owner",
   "menu icon lost its separate freeplay identity");
  var ordinary = iconRequestForCharacter("m1ku_fs", "assets/imported_mods/owner", true);
  check(!ordinary.hidden && ordinary.name == "m1ku_fs"
   && ordinary.ownerRoot == "assets/imported_mods/owner",
   "ordinary icon lost its authored identity or owner");
  check(freeplayPixelIconPath("no-gf", "assets/imported_mods/owner")
   == "assets/imported_mods/owner/images/freeplay/icons/no-gfpixel.png",
   "source Freeplay sentinel icon path did not stay owner scoped");
  check(freeplayPixelIconPath("M1kuPixel", "assets/imported_mods/owner")
   == "assets/imported_mods/owner/images/freeplay/icons/m1kupixel.png",
   "existing pixel suffix was doubled");
  check(freeplayPixelIconPath("../other", "assets/imported_mods/owner") == null
   && freeplayPixelIconPath("miko", "") == null,
   "Freeplay icon path escaped its owner");
 }
}
'''
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            (Path(scratch) / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", scratch, "-main", "Main", "--interp"],
                cwd=ROOT, text=True, capture_output=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
