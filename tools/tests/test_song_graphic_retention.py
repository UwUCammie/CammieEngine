"""Song-scoped retention of disk graphics and the precacheImage contract.

The fixture runs the real FNFAssets image loader, SongGraphicRetention and
DiskBitmapCache against small fakes of flixel's bitmap cache, so use counts,
destruction, decodes and texture uploads can be counted exactly.
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND, TEST_TMP


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError("unterminated method " + marker)


FAKE_GRAPHIC = r'''package flixel.graphics;
import openfl.display.BitmapData;
class FlxGraphic {
	public var key:String;
	public var bitmap:BitmapData;
	public var useCount:Int = 0;
	public var isDestroyed:Bool = false;
	public var persist:Bool = false;
	public var destroyOnNoUse:Bool = true;
	public var width:Int;
	public var height:Int;
	function new(key:String, bitmap:BitmapData) {
		this.key = key; this.bitmap = bitmap; width = bitmap.width; height = bitmap.height;
	}
	static function createGraphic(bitmap:BitmapData, key:String, unique:Bool = false, cache:Bool = true):FlxGraphic {
		var graphic = new FlxGraphic(key, bitmap);
		flixel.FlxG.bitmap.entries.set(key, graphic);
		return graphic;
	}
	public function incrementUseCount():Void useCount++;
	public function decrementUseCount():Void {
		useCount--;
		if (useCount <= 0 && destroyOnNoUse && !persist) flixel.FlxG.bitmap.remove(this);
	}
	public function destroy():Void { isDestroyed = true; bitmap = null; }
}
'''

FAKE_FLXG = r'''package flixel;
import flixel.graphics.FlxGraphic;
import openfl.display.BitmapData;
class FakeBitmapFrontEnd {
	public var entries:Map<String, FlxGraphic> = new Map();
	public var scans:Int = 0;
	public function new() {}
	public function get(key:String):FlxGraphic return entries.get(key);
	public function add(bitmap:BitmapData, unique:Bool = false, ?key:String):FlxGraphic {
		scans++;
		for (graphic in entries) if (graphic.bitmap == bitmap) return graphic;
		return @:privateAccess FlxGraphic.createGraphic(bitmap, key == null ? 'generated' : key);
	}
	public function remove(graphic:FlxGraphic):Void {
		entries.remove(graphic.key);
		if (!graphic.isDestroyed) graphic.destroy();
	}
}
class FakeStage { public var context3D:Dynamic; public function new() {} }
class FlxG {
	public static var bitmap:FakeBitmapFrontEnd = new FakeBitmapFrontEnd();
	public static var stage:FakeStage = new FakeStage();
}
'''

FAKE_BITMAP = r'''package openfl.display;
class BitmapData {
	public static var decodes:Int = 0;
	public var width:Int;
	public var height:Int;
	public var image:Dynamic = {};
	public var uploads:Int = 0;
	public var path:String;
	public function new(path:String) { this.path = path; width = 10; height = 10; }
	public static function fromFile(path:String):BitmapData { decodes++; return new BitmapData(path); }
	public function getTexture(context:Dynamic):Dynamic { uploads++; return null; }
}
'''


class SongGraphicRetentionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assets = (ROOT / "source/FNFAssets.hx").read_text(encoding="utf-8")
        cls.main = (ROOT / "source/Main.hx").read_text(encoding="utf-8")
        cls.play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")

    def run_fixture(self, body: str):
        methods = "\n".join(extract_method(self.assets, marker) for marker in (
            "public static function getBitmapData(",
            "public static function getFlxGraphic(",
            "public static function precacheImage(",
            "public static function retainForSong(",
            "static function uploadTexture(",
            "static function readImage(",
        ))
        fixture = r'''import flixel.FlxG;
import flixel.graphics.FlxGraphic;
import openfl.display.BitmapData;
class Assets {
	public static function exists(id:String):Bool return false;
	public static function getBitmapData(id:String, useCache:Bool):BitmapData return null;
}
class FileSystem { public static function absolutePath(path:String):String return '/game/' + path; }
class RuntimeDecodeMetrics {
	public static var enabled:Bool = false;
	public static var hits:Int = 0;
	public static function recordHit():Void hits++;
	public static function recordMiss(ms:Float):Void {}
}
class SongLoadingWork { public static function complete<T>(value:T):T return value; }
class FNFAssets {
	public static var epoch:Int = 0;
	public static function pathEpoch():Int return epoch;
	static function resolveDiskPath(id:String):String return id;
	static function isInScope(id:String):Bool return true;
METHODS
}
class Sprite {
	public var graphic:FlxGraphic;
	public function new(graphic:FlxGraphic) { this.graphic = graphic; graphic.incrementUseCount(); }
	public function destroy():Void { graphic.decrementUseCount(); graphic = null; }
}
class RetentionFixture {
	static function check(ok:Bool, message:String):Void if (!ok) throw message;
	static function key(path:String):String return DiskBitmapCache.key('/game/' + path);
	static function main() {
BODY
		Sys.println('OK');
	}
}
'''.replace("METHODS", methods).replace("BODY", body)
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            work = Path(folder)
            for relative, text in (
                ("flixel/graphics/FlxGraphic.hx", FAKE_GRAPHIC),
                ("flixel/FlxG.hx", FAKE_FLXG),
                ("openfl/display/BitmapData.hx", FAKE_BITMAP),
                ("RetentionFixture.hx", fixture),
            ):
                target = work / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8", newline="\n")
            for name in ("SongGraphicRetention.hx", "DiskBitmapCache.hx"):
                (work / name).write_text((ROOT / "source" / name).read_text(encoding="utf-8"),
                    encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "-main", "RetentionFixture", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def test_outside_a_song_an_unused_graphic_is_freed_as_before(self):
        self.run_fixture(r'''
		var first = FNFAssets.getFlxGraphic('flash.png');
		var sprite = new Sprite(first);
		sprite.destroy();
		check(first.isDestroyed, 'outside a song the last user should still free the graphic');
		var second = FNFAssets.getFlxGraphic('flash.png');
		check(second != first && BitmapData.decodes == 2, 'expected a fresh decode outside a song');
''')

    def test_recreating_a_sprite_in_a_song_reuses_one_decode(self):
        self.run_fixture(r'''
		SongGraphicRetention.begin(0);
		var bitmap = FNFAssets.getBitmapData('flash.png');
		var first = FlxG.bitmap.get(key('flash.png'));
		check(first != null && first.bitmap == bitmap, 'the decode was not cached under its canonical key');
		var sprite = new Sprite(first);
		sprite.destroy();
		check(!first.isDestroyed, 'removing the last sprite destroyed a graphic held for the song');
		var again = FNFAssets.getFlxGraphic('flash.png');
		check(again == first && BitmapData.decodes == 1, 'recreating the sprite decoded the image again');
		check(RuntimeDecodeMetrics.hits == 1, 'the second request was not a cache hit');
		check(FlxG.bitmap.scans == 0, 'storing or returning a disk graphic scanned the whole bitmap cache');
		check(first.useCount == 1 && SongGraphicRetention.heldCount() == 1, 'a repeated request added a second hold');
		SongGraphicRetention.end();
		check(first.isDestroyed && FlxG.bitmap.get(key('flash.png')) == null,
			'ending the song kept an unused graphic alive');
''')

    def test_a_graphic_a_script_removes_is_decoded_again_and_never_double_released(self):
        self.run_fixture(r'''
		SongGraphicRetention.begin(0);
		var first = FNFAssets.getFlxGraphic('overlay.png');
		var user = new Sprite(first);
		FlxG.bitmap.remove(first);
		check(first.isDestroyed, 'fixture removal failed');
		var second = FNFAssets.getFlxGraphic('overlay.png');
		check(second != first && !second.isDestroyed && BitmapData.decodes == 2,
			'a graphic the script removed was served again');
		check(SongGraphicRetention.heldCount() == 1, 'the dead graphic was still counted as held');
		SongGraphicRetention.end();
		check(first.useCount == 2, 'releasing the song touched a graphic that was already destroyed');
		check(second.isDestroyed, 'the replacement graphic was not released with the song');
''')

    def test_live_sprites_keep_their_graphic_after_the_song_releases(self):
        self.run_fixture(r'''
		SongGraphicRetention.begin(0);
		var graphic = FNFAssets.getFlxGraphic('stage.png');
		var sprite = new Sprite(graphic);
		SongGraphicRetention.end();
		check(!graphic.isDestroyed && graphic.useCount == 1, 'releasing the hold freed a graphic a sprite still draws');
		sprite.destroy();
		check(graphic.isDestroyed, 'the graphic outlived its last user once the song ended');
''')

    def test_an_asset_epoch_change_releases_old_holds(self):
        self.run_fixture(r'''
		SongGraphicRetention.begin(0);
		var old = FNFAssets.getFlxGraphic('a.png');
		FNFAssets.epoch = 1;
		var fresh = FNFAssets.getFlxGraphic('b.png');
		check(old.isDestroyed, 'an import refresh or file write kept an old decode alive');
		check(!fresh.isDestroyed && SongGraphicRetention.heldCount() == 1, 'the new hold was lost');
		var reread = FNFAssets.getFlxGraphic('a.png');
		check(reread != old && BitmapData.decodes == 3, 'the stale decode was served after the epoch moved');
		SongGraphicRetention.end();
''')

    def test_the_first_read_after_an_epoch_change_decodes_the_same_image_again(self):
        # The image asked for right after a file write is the one that was
        # rewritten, so its old hold must go before the cache is consulted.
        self.run_fixture(r'''
		SongGraphicRetention.begin(0);
		var old = FNFAssets.getFlxGraphic('a.png');
		FNFAssets.epoch = 1;
		var reread = FNFAssets.getFlxGraphic('a.png');
		check(old.isDestroyed, 'the hold kept the old decode alive across a file write');
		check(reread != old && BitmapData.decodes == 2, 'the first read after the epoch moved served the old decode');
		check(reread.useCount == 1 && SongGraphicRetention.heldCount() == 1, 'the fresh decode was not held');
		var user = new Sprite(reread);
		FNFAssets.epoch = 2;
		var live = FNFAssets.getFlxGraphic('a.png');
		check(live == reread && !reread.isDestroyed && reread.useCount == 2,
			'a graphic a sprite still draws was destroyed or lost its count');
		SongGraphicRetention.end();
		check(reread.useCount == 1, 'the song end released the wrong number of holds');
''')

    def test_the_byte_cap_releases_the_oldest_unpinned_graphic(self):
        self.run_fixture(r'''
		SongGraphicRetention.begin(0);
		SongGraphicRetention.maxHeldBytes = 900;
		var a = FNFAssets.getFlxGraphic('a.png');
		var b = FNFAssets.getFlxGraphic('b.png');
		check(!a.isDestroyed && !b.isDestroyed, '800 bytes are under the cap');
		FNFAssets.getFlxGraphic('a.png');
		var c = FNFAssets.getFlxGraphic('c.png');
		check(b.isDestroyed, 'the least recently used graphic was not released at the cap');
		check(!a.isDestroyed && !c.isDestroyed, 'the cap released a recently used graphic');
		check(SongGraphicRetention.heldBytes() == 800, 'held byte total is wrong: ' + SongGraphicRetention.heldBytes());
		var pinned = FNFAssets.precacheImage('big.png');
		var d = FNFAssets.getFlxGraphic('d.png');
		check(!pinned.isDestroyed && SongGraphicRetention.isPinned(pinned.key), 'the cap released a precached image');
		check(a.isDestroyed && !d.isDestroyed, 'the cap did not move on to the next oldest graphic');
		SongGraphicRetention.end();
		check(pinned.isDestroyed, 'a precached image outlived the song');
''')

    def test_precache_holds_for_the_song_and_uploads_once(self):
        self.run_fixture(r'''
		FlxG.stage.context3D = {};
		SongGraphicRetention.begin(0);
		var graphic = FNFAssets.precacheImage('preload.png');
		check(graphic != null && graphic.bitmap.uploads == 1, 'precacheImage did not upload the texture');
		check(graphic.bitmap.image != null, 'precacheImage threw away the readable pixels');
		check(SongGraphicRetention.isPinned(graphic.key) && graphic.useCount == 1, 'precacheImage did not pin the image');
		check(!graphic.persist, 'precacheImage made the graphic persistent past the song');
		var sprite = new Sprite(graphic);
		sprite.destroy();
		check(!graphic.isDestroyed, 'the first user let go of a precached image');
		FNFAssets.retainForSong(graphic, false);
		check(graphic.useCount == 1 && graphic.bitmap.uploads == 1, 'pinning twice added a hold or an upload');
		SongGraphicRetention.end();
		check(graphic.isDestroyed, 'the precached image was not released at song end');
		FlxG.stage.context3D = null;
		var later = FNFAssets.precacheImage('preload.png');
		check(later.bitmap.uploads == 0, 'an upload was attempted without a GPU context');
		check(SongGraphicRetention.heldCount() == 0, 'an image was held while no song was running');
''')

    def test_a_zero_cap_keeps_only_precached_images(self):
        self.run_fixture(r'''
		SongGraphicRetention.maxHeldBytes = 0;
		SongGraphicRetention.begin(0);
		var plain = FNFAssets.getFlxGraphic('a.png');
		check(SongGraphicRetention.heldCount() == 0 && plain.useCount == 0, 'low memory mode held an ordinary image');
		var pinned = FNFAssets.precacheImage('b.png');
		check(SongGraphicRetention.isPinned(pinned.key) && pinned.useCount == 1, 'low memory mode dropped a precached image');
		SongGraphicRetention.end();
		check(pinned.isDestroyed, 'the precached image outlived the song');
''')

    def test_uncached_reads_bypass_retention(self):
        self.run_fixture(r'''
		SongGraphicRetention.begin(0);
		var one = FNFAssets.getBitmapData('a.png', false);
		var two = FNFAssets.getBitmapData('a.png', false);
		check(one != two && BitmapData.decodes == 2, 'useCache=false reused a decode');
		check(SongGraphicRetention.heldCount() == 0 && FlxG.bitmap.get(key('a.png')) == null,
			'an uncached read was registered or held');
		SongGraphicRetention.end();
''')

    def test_song_boundaries_and_precache_call_sites(self):
        create = self.main[self.main.index("FlxG.signals.preStateCreate.add("):]
        create = create[:create.index("});")]
        self.assertLess(create.index("SongGraphicRetention.end();"), create.index("pruneSongBitmapCache();"))
        self.assertLess(create.index("SongGraphicRetention.end();"), create.index("FlxG.bitmap.clearCache();"))
        self.assertLess(create.index("DynamicSprite.DynamicAtlasFrames.releaseAll();"),
            create.index("pruneSongBitmapCache();"))
        song_start = create[create.index("if (Std.isOfType(_state, PlayState)) {"):]
        self.assertIn("OptionsHandler.options.lowMemoryMode", song_start[:song_start.index("}")])
        self.assertIn("SongGraphicRetention.begin(FNFAssets.pathEpoch());", song_start[:song_start.index("}")])
        self.assertIn("SongGraphicRetention.bindOwnerThread();", self.main)

        plain = extract_method(self.play_state, "function compatPrecacheImage(")
        self.assertIn("FNFAssets.precacheImage(candidate);", plain)
        owner = extract_method(self.play_state, "function compatPrecacheImageForOwner(")
        self.assertIn("FNFAssets.retainForSong(graphic, allowGPU != false);", owner)
        self.assertNotIn("'persist'", owner)
        self.assertNotIn("'destroyOnNoUse'", owner)


if __name__ == "__main__":
    unittest.main()
