"""V-Slice FunkinSprite.loadSparrow / loadTexture reach the owner's art and return the sprite."""
import json
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

SONG_SCRIPT = '''import funkin.graphics.FunkinSprite;
class LoadSong extends Song {
  var board:FunkinSprite;
  var shade:FunkinSprite;
  var back:FunkinSprite;
  function new() { super('load-song'); }
  function onCreate(event) {
    super.onCreate(event);
    board = new FunkinSprite(700, -300).loadSparrow('boardArt');
    shade = new FunkinSprite().loadTexture("shadeArt");
    var backKey = 'backArt';
    back = new FunkinSprite(0, 0);
    back.loadTexture(backKey);
    this.board.loadSparrow('boardArt');
  }
}
'''


class HxcFunkinSpriteLoadsTest(unittest.TestCase):
    def run_main(self, main: str, cwd: Path = ROOT) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'Main.hx').write_text(main, newline='\n')
            return subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                '-main', 'Main', '--interp'], cwd=cwd, capture_output=True, text=True, timeout=300)

    def test_loads_are_lowered_to_owner_scoped_helpers(self):
        result = self.run_main('''class Main {
 static function need(code:String, text:String):Void
  if (code.indexOf(text) < 0) throw 'missing ' + text + ' in ' + code;
 static function main() {
  var code:String = HxcCompat.analyze(%s, 'scripts/songs/load-song.hxc').generatedHscript;
  need(code, "HxcCompatRuntime.funkinLoadSparrow(HxcCompatRuntime.createFunkinSprite(hxcAssetRoot, 700, -300), hxcAssetRoot, 'boardArt')");
  need(code, 'HxcCompatRuntime.funkinLoadTexture(HxcCompatRuntime.createFunkinSprite(hxcAssetRoot), hxcAssetRoot, "shadeArt")');
  need(code, 'HxcCompatRuntime.funkinLoadTexture(back, hxcAssetRoot, backKey)');
  if (code.indexOf('.loadSparrow(') >= 0 || code.indexOf('.loadTexture(') >= 0)
   throw 'a load call still targets the native sprite: ' + code;
  // A subclass calling its parent keeps the plain call.
  var subclass:String = @:privateAccess HxcCompat.lowerFunkinSpriteLoads('super.loadTexture(key);');
  if (subclass != 'super.loadTexture(key);') throw 'super call was rewritten: ' + subclass;
 }
}
''' % json.dumps(SONG_SCRIPT))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_runtime_helpers_load_owner_art_and_return_the_sprite(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as runtime:
            images = Path(runtime) / 'assets/imported_mods/load-owner/images'
            images.mkdir(parents=True)
            (images / 'shadeArt.png').write_bytes(b'png')
            result = self.run_main('''class Main {
 static function main() {
  var loaded:Array<Dynamic> = [];
  var sprite:Dynamic = {loadGraphic: function(image:Dynamic) loaded.push(image)};
  var root = 'assets/imported_mods/load-owner';
  if (HxcCompatRuntime.funkinLoadTexture(sprite, root, 'shadeArt') != sprite)
   throw 'loadTexture did not return the sprite';
  if (loaded.length != 1 || Std.string(loaded[0]).indexOf('images/shadeArt.png') < 0)
   throw 'owner image was not loaded: ' + loaded;
  if (HxcCompatRuntime.funkinLoadTexture(sprite, root, 'absentArt') != sprite || loaded.length != 1)
   throw 'a missing image changed the sprite';
  // No Sparrow pair exists: the source keeps the sprite unchanged, and so do we.
  if (HxcCompatRuntime.funkinLoadSparrow(sprite, root, 'shadeArt') != sprite)
   throw 'loadSparrow did not return the sprite';
  if (HxcCompatRuntime.funkinLoadSparrow(null, root, 'shadeArt') != null)
   throw 'a null sprite was replaced';
 }
}
''', cwd=Path(runtime))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_importer_plans_the_art_named_by_loads(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as package:
            songs = Path(package) / 'scripts/songs'
            songs.mkdir(parents=True)
            (songs / 'load-song.hxc').write_text(SONG_SCRIPT, newline='\n')
            result = self.run_main('''class Main {
 static function main() {
  var seen:Array<String> = [];
  for (reference in HxcAssetPlanner.plan(%s).references) seen.push(reference.kind + ':' + reference.key);
  for (expected in ['sparrow:boardArt', 'image:shadeArt', 'image:backArt'])
   if (seen.indexOf(expected) < 0) throw 'missing ' + expected + ' in ' + seen;
 }
}
''' % json.dumps(str(package).replace('\\', '/')))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
