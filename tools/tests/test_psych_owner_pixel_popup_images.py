"""Psych pixel stages read a mod's own rating and combo art from pixelUI.

Psych builds popup names as uiPrefix + name + uiPostfix, which on a pixel stage
is pixelUI/<name>-pixel. Normal stages keep images/<name>.png, and a stage that
turns pixel mid-song must not answer from the normal stage's cache.
"""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_psych_charting_handoff import method

ROOT = Path(__file__).resolve().parents[2]


class PsychOwnerPixelPopupImagesTest(unittest.TestCase):
    def test_pixel_stage_reads_pixel_ui_folder_and_caches_each_mode(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        lookup = method(play, 'function psychOwnerPopupImage(')
        fixture = '''class OwnerPaths {
 public function new() {}
 public function __sourceOwnedPath(path:String):String return 'mods/owner/' + path;
}
class PsychOwnerPaths {
 public static var created = 0;
 public static function create(owner:String, library:Dynamic):Dynamic {created++; return new OwnerPaths();}
}
class FNFAssets {
 public static var probes:Array<String> = [];
 public static var files = ['mods/owner/images/sick.png', 'mods/owner/images/pixelUI/sick-pixel.png',
  'mods/owner/images/pixelUI/num1-pixel.png'];
 public static function exists(path:String):Bool {probes.push(path); return files.indexOf(path) >= 0;}
}
class Main {
 var pixelUI = false;
 var nightmareVisionScripts:Dynamic = null;
 var psychStageLibrary:Dynamic = null;
 var psychOwnerPopupImages:Map<String, String>;
 var psychOwnerPixelPopupImages:Map<String, String>;
 function selectedPsychSkinRoot():String return 'owner';
 public function new() {}
 @@LOOKUP@@
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var state = new Main();
  check(state.psychOwnerPopupImage('sick') == 'mods/owner/images/sick.png', 'normal stage rating');
  state.pixelUI = true;
  check(state.psychOwnerPopupImage('sick') == 'mods/owner/images/pixelUI/sick-pixel.png', 'pixel stage rating');
  check(state.psychOwnerPopupImage('num1') == 'mods/owner/images/pixelUI/num1-pixel.png', 'pixel combo digit');
  check(state.psychOwnerPopupImage('good') == null, 'missing pixel art falls back to the built-in one');
  var probes = FNFAssets.probes.length;
  state.psychOwnerPopupImage('sick');
  state.psychOwnerPopupImage('good');
  check(FNFAssets.probes.length == probes, 'pixel answers were not cached');
  state.pixelUI = false;
  check(state.psychOwnerPopupImage('sick') == 'mods/owner/images/sick.png', 'normal answer replaced by pixel one');
  check(state.psychOwnerPopupImage('num1') == null, 'normal stage read pixel art');
  state.nightmareVisionScripts = {};
  check(state.psychOwnerPopupImage('sick') == null, 'Nightmare Vision HUD draws its own popups');
 }
}'''.replace('@@LOOKUP@@', lookup)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            Path(folder, 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '--main', 'Main', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_owner_pixel_rating_gets_the_built_in_pixel_zoom(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        start = play.index('var ownerRatingImage = psychOwnerPopupImage(daRating);')
        block = play[start:play.index('rating.screenCenter();', start)]
        self.assertIn('rating.setGraphicSize(Std.int(rating.width * daPixelZoom));', block)
        self.assertIn('rating.antialiasing = false;', block)
        self.assertLess(block.index('daPixelZoom'), block.index('rating.updateHitbox();'))


if __name__ == '__main__':
    unittest.main()
