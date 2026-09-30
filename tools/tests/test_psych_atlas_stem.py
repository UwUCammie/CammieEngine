"""Character atlas stems remain usable through the shared Psych sprite API."""

from pathlib import Path
import subprocess
import tempfile
import unittest

from test_psych_animation_indices import extract_method

ROOT = Path(__file__).resolve().parents[2]


class PsychAtlasStemTest(unittest.TestCase):
    def test_native_stem_loads_the_exact_atlas_and_static_bitmap(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        methods = "\n".join(extract_method(source, "function " + name + "(") for name in (
            "compatMakeLuaSprite", "compatMakeAnimatedLuaSprite",
            "compatReadSparrowFrameNames", "compatLoadGraphic",
        ))
        fixture = r'''class Bitmap {
 public var path:String;
 public function new(path:String) this.path = path;
}
class FNFAssets {
 public static var stem = 'assets/images/custom_chars/actor/char';
 public static function exists(path:String):Bool
  return path == stem + '.png' || path == stem + '.xml';
 public static function getBitmapData(path:String):Bitmap {
  if (path != stem + '.png') throw 'wrong image path';
  return new Bitmap(path);
 }
 public static function getText(path:String):String {
  if (path != stem + '.xml') throw 'wrong atlas path';
  return '<TextureAtlas><SubTexture name="idle0000"/></TextureAtlas>';
 }
}
class FlxSprite {
 public var frames:Dynamic;
 public var bitmap:Bitmap;
 public function new(x:Float = 0, y:Float = 0) {}
 public function loadGraphic(value:Bitmap):Void bitmap = value;
}
class FlxAtlasFrames {
 public static function fromSparrow(bitmap:Bitmap, xml:String):Dynamic
  return {bitmap:bitmap, xml:xml};
}
class AtlasFixture {
 var haxeSprites:Map<String,FlxSprite> = [];
 var haxeSpriteAtlasNames:Map<String,Array<String>> = [];
 function new() {}
 function compatFindObject(name:Dynamic):Dynamic return haxeSprites.get(Std.string(name));
 function compatForgetSpriteAtlas(sprite:Dynamic):Void {}
 function compatRememberSpriteAtlas(tag:String, sprite:FlxSprite, names:Array<String>):Void
  haxeSpriteAtlasNames.set(tag, names);
''' + methods + r'''
 static function main() {
  var state = new AtlasFixture();
  var stem = FNFAssets.stem;
  var animated = state.compatMakeAnimatedLuaSprite('trail', stem);
  if (animated.frames == null || animated.frames.bitmap.path != stem + '.png'
   || state.haxeSpriteAtlasNames.get('trail').join(',') != 'idle0000')
   throw 'extensionless character atlas was not loaded';
  var image = state.compatMakeLuaSprite('image', stem);
  if (image.bitmap == null || image.bitmap.path != stem + '.png')
   throw 'extensionless static image was not loaded';
  image.bitmap = null;
  state.compatLoadGraphic('image', stem);
  if (image.bitmap == null) throw 'extensionless replacement was not loaded';
  var explicit = state.compatMakeLuaSprite('explicit', stem + '.png');
  if (explicit.bitmap == null || explicit.bitmap.path != stem + '.png')
   throw 'explicit PNG regressed';
 }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "AtlasFixture.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder,
                 "-main", "AtlasFixture", "--interp"],
                cwd=ROOT, text=True, capture_output=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
