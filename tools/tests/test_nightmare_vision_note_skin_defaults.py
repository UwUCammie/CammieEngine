"""Execute the owner-independent defaults of the source Nightmare Vision NoteSkin."""

import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]


MAIN = r'''class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function fails(action:Void->Void, fragment:String, message:String):Void {
  var error = "";
  try action() catch (value:Dynamic) error = Std.string(value);
  check(error.indexOf(fragment) >= 0, message + ": " + error);
 }
 static function main():Void {
  var first:Dynamic = {};
  NightmareVisionNoteSkinDefaults.resolveData(first);
  check(first.noteTexture == "UI/notes/NOTE_assets"
   && first.splashTexture == "UI/notes/noteSplashes"
   && first.sustainSplashTexture == "UI/notes/sustainHold",
   "source atlas defaults changed");
  check(first.noteAnimations.length == 4 && first.noteAnimations[0].length == 3
   && first.noteAnimations[0][0].anim == "scroll"
   && first.noteAnimations[0][0].xmlName == "purple"
   && first.noteAnimations[0][0].looping == true
   && first.noteAnimations[0][0].fps == 24,
   "source note animation defaults changed");
  check(first.receptorAnimations[3][2].anim == "confirm"
   && first.receptorAnimations[3][2].xmlName == "right confirm"
   && first.noteSplashAnimations.length == 4
   && first.susSplashAnimations[1][1].anim == "loop",
   "source receptor or splash animation defaults changed");
  check(first.arrowRGB.length == 4 && first.arrowRGB[0].r == 0xFFC24B99
   && first.arrowRGB[1].b == 0xFF1542B7 && first.inGameColoring == true
   && first.noteScale == 0.7 && first.receptorScale == 0.7
   && first.splashesEnabled == true && first.susSplashesEnabled == true,
   "source visual settings or palette defaults changed");

  var second:Dynamic = {};
  NightmareVisionNoteSkinDefaults.resolveData(second);
  check(first.noteAnimations != second.noteAnimations
   && first.noteAnimations[0] != second.noteAnimations[0]
   && first.noteAnimations[0][0] != second.noteAnimations[0][0]
   && first.noteAnimations[0][0].offsets != second.noteAnimations[0][0].offsets
   && first.arrowRGB != second.arrowRGB && first.arrowRGB[0] != second.arrowRGB[0],
   "default mutable tables must be independent per skin");
  first.noteAnimations[0][0].offsets[0] = 17;
  first.arrowRGB[0].r = 0;
  check(second.noteAnimations[0][0].offsets[0] == 0 && second.arrowRGB[0].r == 0xFFC24B99,
   "mutating one skin's tables leaked into another");

  var authored:Dynamic = {
   noteTexture: "", noteAnimations: [[{anim:"scroll", xmlName:"custom"}]],
   noteSplashAnimations: [{anim:"one", xmlName:"splash", offsets:[2,3]}], arrowRGB: []
  };
  NightmareVisionNoteSkinDefaults.resolveData(authored);
  check(authored.noteTexture == "" && authored.noteAnimations.length == 1
   && authored.noteAnimations[0][0].xmlName == "custom"
   && authored.noteAnimations[0][0].offsets[0] == 0
   && authored.noteAnimations[0][0].looping == false
   && authored.noteAnimations[0][0].fps == 24
   && authored.noteSplashAnimations[0].offsets[0] == 2
   && authored.arrowRGB.length == 0,
   "authored empty values or null-only animation normalization changed");
  fails(function() NightmareVisionNoteSkinDefaults.resolveData(null),
   "resolveData requires an object", "direct null resolveData must fail");
  fails(function() NightmareVisionNoteSkinDefaults.resolveData([]),
   "Skin data must be an object", "array skin data must fail with a useful type error");
  trace("NV_NOTE_SKIN_DEFAULTS_OK");
 }
}'''


class NightmareVisionNoteSkinDefaultsTest(unittest.TestCase):
    def test_defaults_are_exact_null_only_and_independent(self):
        if not (ROOT / ".tools/haxe/haxe").is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(MAIN, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                 "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("NV_NOTE_SKIN_DEFAULTS_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
