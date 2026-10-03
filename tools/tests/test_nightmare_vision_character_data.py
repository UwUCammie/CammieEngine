"""Exercise owner-scoped Nightmare Vision character JSON and atlas discovery."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionCharacterDataTest(unittest.TestCase):
    def setUp(self):
        (ROOT / 'tmp').mkdir(exist_ok=True)
        self.scratch = tempfile.TemporaryDirectory(dir=ROOT / 'tmp')
        self.addCleanup(self.scratch.cleanup)
        self.work = Path(self.scratch.name)
        self.owner = self.work / 'game/assets/imported_mods/nmv-owner'
        self.owner.mkdir(parents=True)
        self.sibling = self.work / 'game/assets/imported_mods/other-owner'
        self.sibling.mkdir(parents=True)
        self.owner_arg = self.owner.relative_to(ROOT).as_posix()
        self.sibling_arg = self.sibling.relative_to(ROOT).as_posix()
        (self.work / 'CoolUtil.hx').write_text('''package;
class CoolUtil {
 public static function parseJson(value:String):Dynamic return haxe.Json.parse(value);
}
''', newline='\n')
        (self.work / 'Main.hx').write_text('''package;
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var args = Sys.args();
  var owner = args[0];
  var sibling = args[1];
  var dusk = NightmareVisionCharacterData.load(owner, 'dusk');
  check(dusk != null && dusk.image == 'characters/Dusk' && dusk.marker == 'owner',
   'owner character JSON loads first');
  check(NightmareVisionCharacterData.definitionPath(owner, 'dusk')
   == owner + '/data/characters/dusk.json', 'owner definition path stays runtime-relative');
  check(NightmareVisionCharacterData.imageRoot(owner, dusk)
   == owner + '/images/characters/Dusk', 'Animate atlas prefix stays runtime-relative');
  var sparrow = NightmareVisionCharacterData.load(owner, 'sparrow');
  check(NightmareVisionCharacterData.imageRoot(owner, sparrow)
   == owner + '/images/characters/Sparrow', 'Sparrow prefix resolves');
  var core = NightmareVisionCharacterData.load(owner, 'core-only');
  check(core != null && core.marker == 'core', 'installed core definition fallback');
  check(NightmareVisionCharacterData.definitionPath(owner, 'core-only')
   == owner + '/__nmv_core/data/characters/core-only.json', 'core definition path stays owner scoped');
  check(NightmareVisionCharacterData.imageRoot(owner, core)
   == owner + '/__nmv_core/images/characters/Core', 'core atlas prefix stays owner scoped');
  var localCoreAtlas = NightmareVisionCharacterData.load(owner, 'local-core-atlas');
  check(NightmareVisionCharacterData.imageRoot(owner, localCoreAtlas)
   == owner + '/__nmv_core/images/characters/LocalCore',
   'valid core atlas is considered when an empty owner directory exists');
  check(NightmareVisionCharacterData.load(owner, 'sibling-only') == null,
   'character definitions never escape to sibling owners');
  check(NightmareVisionCharacterData.definitionPath(owner, '../other-owner/sibling-only') == null,
   'unsafe character traversal is rejected');
  check(NightmareVisionCharacterData.imageRoot(owner, {image:'../outside'}) == null,
   'unsafe image traversal is rejected');
  check(NightmareVisionCharacterData.imageRoot(owner, {image:'characters/missing'}) == null,
   'missing atlas remains unresolved');
  Sys.println('nightmare-vision-character-data-ok');
 }
}
''', newline='\n')

    def write(self, root, relative, value='asset'):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, newline='\n')
        return path

    def make_animate(self, root, image_path):
        self.write(root, image_path + '/Animation.json', '{}')
        self.write(root, image_path + '/spritemap1.png')
        self.write(root, image_path + '/spritemap1.json', '{}')

    def test_character_json_atlas_and_core_lookup(self):
        self.write(self.owner, 'data/characters/dusk.json',
                   '{"image":"characters/Dusk","marker":"owner"}')
        self.write(self.owner, 'characters/dusk.json',
                   '{"image":"characters/Other","marker":"lower-priority"}')
        self.write(self.sibling, 'data/characters/sibling-only.json',
                   '{"image":"characters/Sibling","marker":"sibling"}')
        self.make_animate(self.owner, 'images/characters/Dusk')
        self.write(self.owner, 'data/characters/sparrow.json',
                   '{"image":"characters/Sparrow"}')
        self.write(self.owner, 'images/characters/Sparrow.png')
        self.write(self.owner, 'images/characters/Sparrow.xml', '<TextureAtlas/>')

        self.write(self.owner, '__nmv_core/data/characters/core-only.json',
                   '{"image":"characters/Core","marker":"core"}')
        self.make_animate(self.owner, '__nmv_core/images/characters/Core')
        self.write(self.owner, 'data/characters/local-core-atlas.json',
                   '{"image":"characters/LocalCore"}')
        (self.owner / 'images/characters/LocalCore').mkdir(parents=True)
        self.make_animate(self.owner, '__nmv_core/images/characters/LocalCore')

        result = subprocess.run(
            [*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(self.work),
             '--run', 'Main', self.owner_arg, self.sibling_arg],
            cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('nightmare-vision-character-data-ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
