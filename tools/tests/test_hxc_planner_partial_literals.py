"""Pieces of a path built at run time are not planned as asset files."""
import json
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

SCRIPT = r'''class Results extends Module {
  static var DATAS = [5 => {spr: "shoot"}, 10 => {spr: "nice"}];
  function swap(state) {
    var img:String = "results/rankScroll" + state.rank.split("_")[0].toUpperCase() + "-alt";
    var sprite = new FlxBackdrop(Paths.image(img));
    var picked:String = "";
    for (key in DATAS.keys()) picked = DATAS[key].spr;
    sprite.loadGraphic(Paths.image("taunt/" + picked));
    var songId:String = state.capsule?.id ?? "";
    var format:String = songId + "-" + state.variation;
    FunkinSound.load(Paths.music("previews/" + format + "/intro"));
    var plain:String = "menu/" + "logo";
    Paths.image(plain);
    var chosen:String = FlxG.random.bool(50) ? "left" : "right";
    Paths.image("arrows/" + chosen);
    var prefix = "city" + (state.variation == 'pico' ? "-pico" : "");
    Paths.image(prefix + "/cloud");
    var passing = 'carPass' + FlxG.random.int(0, 1);
    FunkinSound.playOnce(Paths.sound(passing));
  }
  function spawn() {
    animated(this, 'mangle', 'idle');
    still(this, 'golden');
  }
  function animated(game:PlayState, assetName:String, prefix:String):FlxSprite
  {
    var spr = new FlxSprite();
    spr.frames = Paths.getSparrowAtlas(assetName, 'shared');
    return spr;
  }
  function still(game:PlayState, assetName:String):FlxSprite
  {
    var spr = new FlxSprite();
    spr.loadGraphic(Paths.image(assetName, 'shared'));
    return spr;
  }
}
'''

MAIN = '''class Main {
 static function main() {
  var keys = [for (reference in HxcAssetPlanner.literalReferences(%s)) reference.kind + ':' + reference.key];
  for (wanted in ['image:taunt/shoot', 'image:taunt/nice', 'image:menu/logo', 'image:arrows/left', 'image:arrows/right',
    'image:city/cloud', 'image:city-pico/cloud', 'sound:carPass0', 'sound:carPass1',
    'sparrow:mangle', 'image:golden'])
   if (keys.indexOf(wanted) < 0) throw 'lost ' + wanted + ' from ' + keys;
  for (key in keys) {
   if (key.charAt(key.length - 1) == '/') throw 'a folder prefix became a file: ' + keys;
   if (key.indexOf('rankScroll') >= 0 || key == 'image:_' || key == 'image:-alt')
    throw 'a piece of a runtime concatenation became a file: ' + keys;
   if (key.indexOf('previews/') >= 0) throw 'a path with a runtime middle became a file: ' + keys;
   if (key.indexOf('citypico') >= 0 || key == 'image:pico/cloud' || key == 'image:-pico/cloud' || key == 'sound:carPass')
    throw 'a ternary condition or a bare prefix became a file: ' + keys;
   // Two typed helpers share a parameter name; each keeps its own call sites.
   if (key == 'sparrow:golden' || key == 'image:mangle')
    throw 'a helper received the arguments of another helper: ' + keys;
  }
 }
}
'''


class HxcPlannerPartialLiteralsTest(unittest.TestCase):
    def test_runtime_concatenation_pieces_are_not_dependencies(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'Main.hx').write_text(MAIN % json.dumps(SCRIPT), newline=chr(10))
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
