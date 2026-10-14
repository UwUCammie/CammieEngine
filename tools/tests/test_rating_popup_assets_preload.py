"""Rating and combo popup images are resolved and loaded before the song."""
from haxe_test_support import HAXE_COMMAND, FixturePath

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class RatingPopupAssetsPreloadTest(unittest.TestCase):
    def test_hits_after_preload_probe_and_load_nothing(self):
        fixture = r'''class RatingPopupFixture {
 static function fail(message:String):Void throw message;
 static function main() {
  var present:Map<String, Bool> = new Map();
  for (digit in [0, 1, 2, 3, 4])
   present.set("assets/images/custom_ui/ui_packs/neon/num" + digit + ".png", true);
  var probes = 0;
  function exists(path:String):Bool { probes++; return present.exists(path); }

  var assets = new RatingPopupAssets("neon", false, exists, 3);
  var loaded:Array<String> = [];
  var kept = assets.preload(function(path:String) loaded.push(path));
  if (kept != 10 || loaded.length != 10) fail("expected ten digit images, got " + loaded.length);
  var afterPreload = probes;

  // 100 popups of a three digit combo.
  for (hit in 0...100) {
   var combo = Std.string(100 + hit);
   for (i in 0...combo.length) {
    var path = assets.digit(combo.charAt(i));
    if (path == null) fail("a digit had no path");
    if (loaded.indexOf(path) < 0) fail("a popup needed an image that was not preloaded: " + path);
   }
  }
  if (probes != afterPreload) fail("popups probed the disk " + (probes - afterPreload) + " times");

  // Same fallback order as before: pack image, else stock.
  if (assets.digit("3") != "assets/images/custom_ui/ui_packs/neon/num3.png") fail("pack digit not preferred");
  if (assets.digit("7") != "assets/images/num7.png") fail("stock digit fallback changed");
  var pixel = new RatingPopupAssets("retro", true, function(path) return path == "assets/images/custom_ui/ui_packs/retro/num1-pixel.png");
  if (pixel.digit("1") != "assets/images/custom_ui/ui_packs/retro/num1-pixel.png") fail("pixel pack digit");
  if (pixel.digit("2") != "assets/images/weeb/pixelUI/num2-pixel.png") fail("pixel stock fallback changed");
  if (assets.digit("-") != null || assets.digit("") != null || assets.digit(null) != null || assets.digit("12") != null)
   fail("a non digit was given a remembered path");
  if (RatingPopupAssets.digitPath("neon", "-", false, function(_) return false) != "assets/images/num-.png")
   fail("the long way must keep the old spelling for odd characters");

  // The owner rebuilds when the pack, the pixel flag or the library changes.
  if (!assets.matches("neon", false, 3)) fail("same request did not match");
  if (assets.matches("neon", false, 4)) fail("a library change was ignored");
  if (assets.matches("neon", true, 3) || assets.matches("other", false, 3)) fail("a different pack matched");

  // One unreadable image does not stop the others.
  var seen = 0;
  var done = assets.preload(function(path:String) { seen++; if (seen == 2) throw "bad png"; });
  if (seen != 10 || done != 9) fail("a bad image stopped the preload");

  // Shared stock paths are only handed over once.
  var shared = new RatingPopupAssets("plain", false, function(_) return false);
  var unique:Map<String, Int> = new Map();
  shared.preload(function(path:String) unique.set(path, (unique.exists(path) ? unique.get(path) : 0) + 1));
  for (count in unique) if (count != 1) fail("an image was preloaded twice");
  if (RatingPopupAssets.RATINGS.join(",") != "sick,good,bad,shit,wayoff,miss") fail("rating list changed");
  Sys.println("OK");
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (FixturePath(folder) / "RatingPopupFixture.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"), "--run", "RatingPopupFixture"],
                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def test_playstate_preloads_and_keeps_popup_graphics_for_the_song(self):
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        start = play.index("function preloadHitFeedback():Void")
        preload = play[start:start + 1800]
        self.assertIn("graphic.destroyOnNoUse = false;", preload)
        self.assertIn("popupAssets().preload(", preload)
        self.assertIn("for (name in RatingPopupAssets.RATINGS)", preload)
        self.assertIn("new Judgement(0, 0, name, preferredJudgement, false, pixelUI)", preload)
        self.assertIn("FNFAssets.precacheSound('assets/sounds/hitSound.ogg')", preload)
        popup = play[play.index("private function popUpScore("):]
        popup = popup[:popup.index("public var psychClientPrefs")]
        self.assertIn("FNFAssets.getBitmapData(comboDigitPath(numBer))", popup)
        self.assertNotIn("FNFAssets.exists('assets/images/custom_ui/ui_packs/' + uiSmelly.uses + '/num'", popup)


if __name__ == "__main__":
    unittest.main()
