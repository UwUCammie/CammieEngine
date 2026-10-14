"""DynamicAtlasFrames cache keys, inline metadata handling and invalidation.

Runs the real DynamicAtlasFrames class against small fakes of flixel's atlas
builder and FNFAssets, so builds, metadata reads and path probes are counted.
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND, TEST_TMP


ROOT = Path(__file__).resolve().parents[2]


class DynamicAtlasCacheKeyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (ROOT / "source/DynamicSprite.hx").read_text(encoding="utf-8")
        start = source.index("class DynamicAtlasFrames {")
        cls.atlas_class = source[start:source.index("\nclass DynamicTiledSprite", start)]

    def run_fixture(self, body: str):
        fixture = r'''typedef FlxGraphicAsset = Dynamic;
class FlxGraphic {
	public var key:String;
	public var useCount:Int = 0;
	public var isDestroyed:Bool = false;
	public function new(key:String) this.key = key;
	public function incrementUseCount():Void useCount++;
	public function decrementUseCount():Void useCount--;
}
class FlxAtlasFrames {
	public static var builds:Int = 0;
	public static var lastMetadata:String;
	public var parent:FlxGraphic;
	public function new(parent:FlxGraphic) this.parent = parent;
	static function build(png:Dynamic, metadata:String):FlxAtlasFrames {
		builds++;
		lastMetadata = metadata;
		return new FlxAtlasFrames(Std.isOfType(png, FlxGraphic) ? png : FNFAssets.graphic(Std.string(png)));
	}
	public static function fromSparrow(png:Dynamic, xml:String):FlxAtlasFrames return build(png, xml);
	public static function fromSpriteSheetPacker(png:Dynamic, txt:String):FlxAtlasFrames return build(png, txt);
	public static function fromTexturePackerJson(png:Dynamic, json:String):FlxAtlasFrames return build(png, json);
	public function addAtlas(other:FlxAtlasFrames):Void {}
}
class FNFAssets {
	public static var epoch:Int = 0;
	public static var probes:Array<String> = [];
	public static var reads:Int = 0;
	public static var loads:Int = 0;
	public static var files:Map<String, String> = new Map();
	static var graphics:Map<String, FlxGraphic> = new Map();
	public static function pathEpoch():Int return epoch;
	public static function exists(id:String):Bool { probes.push(id); return files.exists(id); }
	public static function getText(id:String):String { reads++; return files.get(id); }
	public static function graphic(id:String):FlxGraphic {
		if (!graphics.exists(id)) graphics.set(id, new FlxGraphic(id));
		return graphics.get(id);
	}
	public static function getFlxGraphic(id:String):FlxGraphic { loads++; return graphic(id); }
}
ATLAS
class AtlasFixture {
	static function check(ok:Bool, message:String):Void if (!ok) throw message;
	static function main() {
BODY
		Sys.println('OK');
	}
}
'''.replace("ATLAS", self.atlas_class).replace("BODY", body)
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / "AtlasFixture.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "AtlasFixture", "--interp"],
                cwd=folder, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def test_inline_xml_is_cached_without_probing_it_as_a_path(self):
        self.run_fixture(r'''
		var xml = '<?xml version="1.0"?>\n<TextureAtlas imagePath="a.png"><SubTexture name="idle0000"/></TextureAtlas>';
		var first = DynamicAtlasFrames.fromSparrow('images/a.png', xml);
		var second = DynamicAtlasFrames.fromSparrow('images/a.png', xml + '');
		check(first == second && FlxAtlasFrames.builds == 1, 'the same inline atlas was built twice');
		check(FNFAssets.probes.indexOf(xml) < 0, 'inline XML was probed as a file path');
		check(FNFAssets.loads == 1 && FlxAtlasFrames.lastMetadata == xml, 'the image or metadata was not passed through');
		check(first.parent.useCount == 1, 'the cache did not hold its sheet exactly once');
		var changed = DynamicAtlasFrames.fromSparrow('images/a.png', xml + ' ');
		check(changed != first && FlxAtlasFrames.builds == 2, 'different inline text reused the old frames');
		check(first.parent.useCount == 1, 'replacing an inline slot leaked or lost a use count');
		var long = StringTools.lpad('', 'x', 2000);
		DynamicAtlasFrames.fromSpriteSheetPacker('images/b.png', long);
		check(FNFAssets.probes.indexOf(long) < 0, 'very long single-line metadata was probed as a path');
''')

    def test_metadata_paths_are_read_once_and_keyed_by_path(self):
        self.run_fixture(r'''
		FNFAssets.files.set('images/a.xml', '<TextureAtlas/>');
		var first = DynamicAtlasFrames.fromSparrow('images/a.png', 'images/a.xml');
		check(FNFAssets.probes.indexOf('images/a.xml') >= 0 && FNFAssets.reads == 1, 'a metadata path was not read');
		check(FlxAtlasFrames.lastMetadata == '<TextureAtlas/>', 'the file text did not reach the atlas builder');
		var second = DynamicAtlasFrames.fromSparrow('images/a.png', 'images/a.xml');
		check(second == first && FNFAssets.reads == 1 && FlxAtlasFrames.builds == 1, 'a cached path atlas was read again');
		DynamicAtlasFrames.fromSpriteSheetPacker('images/a.png', 'images/a.xml');
		check(FlxAtlasFrames.builds == 2, 'Sparrow and Packer atlases shared a cache entry');
		var json = '{"frames":{}}';
		var tp = DynamicAtlasFrames.fromTexturePackerJson('images/c.png', json);
		check(DynamicAtlasFrames.fromTexturePackerJson('images/c.png', json) == tp && FlxAtlasFrames.builds == 3,
			'TexturePacker JSON text missed the cache');
		// A brace inside a folder name is still a path, not JSON text.
		FNFAssets.files.set('images/{b}/b.xml', '<B/>');
		DynamicAtlasFrames.fromSparrow('images/{b}/b.png', 'images/{b}/b.xml');
		check(FNFAssets.probes.indexOf('images/{b}/b.xml') >= 0 && FlxAtlasFrames.lastMetadata == '<B/>',
			'a metadata path with a brace in it was treated as inline text');
		DynamicAtlasFrames.fromSparrow('images/e.png', '');
		check(FlxAtlasFrames.builds == 5, 'empty metadata broke the inline check');
''')

    def test_epoch_change_and_song_end_release_every_atlas(self):
        self.run_fixture(r'''
		var frames = DynamicAtlasFrames.fromSparrow('images/a.png', '<A/>');
		var sheet = frames.parent;
		FNFAssets.epoch = 1;
		var rebuilt = DynamicAtlasFrames.fromSparrow('images/a.png', '<A/>');
		check(rebuilt != frames && FlxAtlasFrames.builds == 2, 'an import refresh served frames from before it');
		check(sheet.useCount == 1, 'the old entry kept its use count after the epoch moved');
		DynamicAtlasFrames.fromSparrow('images/b.png', '<B/>');
		DynamicAtlasFrames.releaseAll();
		check(sheet.useCount == 0 && FNFAssets.graphic('images/b.png').useCount == 0, 'releaseAll kept a use count');
		DynamicAtlasFrames.fromSparrow('images/a.png', '<A/>');
		check(FlxAtlasFrames.builds == 4, 'releaseAll left an entry behind');
''')

    def test_destroyed_sheets_are_rebuilt(self):
        self.run_fixture(r'''
		var frames = DynamicAtlasFrames.fromSparrow('images/a.png', '<A/>');
		frames.parent.isDestroyed = true;
		var next = DynamicAtlasFrames.fromSparrow('images/a.png', '<A/>');
		check(next != frames && FlxAtlasFrames.builds == 2, 'a destroyed sheet was served from the cache');
''')


if __name__ == "__main__":
    unittest.main()
