"""Prevent multiple FlxGraphics from owning the same cached BitmapData."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND


ROOT = Path(__file__).resolve().parents[2]


class FlxGraphicBitmapOwnershipTest(unittest.TestCase):
    def test_owner_path_facades_reuse_the_canonical_disk_graphic(self):
        callers = {
            "NightmareVisionPaths.hx": ("public function image(key:String", "ownedAssets().getGraphic(path, true, allowGPU)"),
            "CodenamePaths.hx": ("public function graphic(path:String", "FNFAssets.getFlxGraphic(resolved)"),
            "PsychOwnerPaths.hx": ("static function graphic(path:String", "FNFAssets.getFlxGraphic(path)"),
        }
        for filename, (marker, helper_call) in callers.items():
            source = (ROOT / "source" / filename).read_text(encoding="utf-8")
            start = source.index(marker)
            body = source[start:source.index("\n\t}", start) + 3]
            self.assertIn(helper_call, body, filename)
            self.assertNotIn("FlxG.bitmap.add(FNFAssets.getBitmapData", body, filename)

        nv_assets = (ROOT / "source/NightmareVisionFunkinAssets.hx").read_text(encoding="utf-8")
        start = nv_assets.index("public function getGraphicUnsafe(")
        body = nv_assets[start:nv_assets.index("\n\t}", start) + 3]
        self.assertIn("FNFAssets.getFlxGraphic(selected)", body)
        self.assertIn("cache.trackGraphic(selected, graphic, allowGPU)", body)
        self.assertNotIn("cache.cacheBitmap(selected, bitmap", body)

    def test_canonical_graphic_keeps_its_bitmap_alive_across_cache_sweep(self):
        source = (ROOT / "source/FNFAssets.hx").read_text(encoding="utf-8")
        marker = "public static function getFlxGraphic("
        start = source.index(marker)
        brace = source.index("{", start)
        depth = 0
        for index in range(brace, len(source)):
            if source[index] == "{":
                depth += 1
            elif source[index] == "}":
                depth -= 1
                if depth == 0:
                    method = source[start:index + 1]
                    break
        else:
            self.fail("unterminated getFlxGraphic method")

        fixture = """class FakeBitmapData { public function new(){} }
class FlxGraphic {
  public var key:String; public var bitmap:FakeBitmapData; public var useCount:Int=0;
  public var isDestroyed:Bool=false;
  public function new(key:String,bitmap:FakeBitmapData){this.key=key;this.bitmap=bitmap;}
  public function incrementUseCount():Void useCount++;
  public function destroy():Void {isDestroyed=true;bitmap=null;}
}
class FakeBitmapFrontEnd {
  public var entries:Map<String,FlxGraphic>=new Map();
  public function new(){}
  public function add(bitmap:FakeBitmapData,unique:Bool=false,?key:String):FlxGraphic {
    if(key==null) for(graphic in entries) if(graphic.bitmap==bitmap && !graphic.isDestroyed)return graphic;
    var actualKey=key==null?'bitmap':key;
    var graphic=new FlxGraphic(actualKey,bitmap);entries.set(actualKey,graphic);return graphic;
  }
  public function clearCache():Void for(graphic in entries) if(graphic.useCount==0)graphic.destroy();
}
class FlxG { public static var bitmap:FakeBitmapFrontEnd=new FakeBitmapFrontEnd(); }
class FNFAssets {
  public static var data:FakeBitmapData=new FakeBitmapData();
  public static function getBitmapData(_id:String,?useCache:Bool=true):FakeBitmapData return data;
  METHOD
}
class CanonicalGraphicTest {
  static function check(ok:Bool,message:String):Void if(!ok)throw message;
  static function main() {
    var cached=FlxG.bitmap.add(FNFAssets.data,false,'fnfassets:disk-bitmap:/owner/images/NOTE_assets.png');
    cached.incrementUseCount();
    var loaded=FNFAssets.getFlxGraphic('/owner/images/NOTE_assets.png');
    check(loaded==cached,'owner facade created a second FlxGraphic for the same bitmap');
    check(FlxG.bitmap.entries.exists('fnfassets:disk-bitmap:/owner/images/NOTE_assets.png'),
      'canonical graphic key was missing from cache');
    FlxG.bitmap.clearCache();
    check(!cached.isDestroyed && loaded.bitmap==FNFAssets.data,
      'zero-use alias disposal invalidated the live canonical graphic');
  }
}
""".replace("METHOD", method)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            source_path = Path(folder) / "CanonicalGraphicTest.hx"
            source_path.write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--interp", "-main", "CanonicalGraphicTest"],
                cwd=folder,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
