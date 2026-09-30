"""Behavior tests for native disk bitmap cache semantics."""

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class DiskBitmapCacheTest(unittest.TestCase):
    def test_cache_reuses_loaded_value_and_uncached_reads_bypass_it(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        fixture = r'''class DiskBitmapCacheFixture {
 static function fail(message:String):Void throw message;
 static function main() {
  var cache:Map<String, String> = new Map();
  var loads = 0;
  var stores = 0;
  function request(path:String, useCache:Bool):String {
   var key = DiskBitmapCache.key(path);
   return DiskBitmapCache.getOrLoad(key, useCache,
    function(k:String) return cache.get(k),
    function() { loads++; return "decoded-" + loads; },
    function(k:String, value:String) { stores++; cache.set(k, value); return value; });
  }
  var first = request("/tmp/assets/images/../bg.png", true);
  var second = request("/tmp/assets/bg.png", true);
  if(first != "decoded-1" || second != first || loads != 1 || stores != 1)
   fail("normalized disk paths did not share the cached decode");
  var uncached = request("/tmp/assets/bg.png", false);
  if(uncached != "decoded-2" || loads != 2 || stores != 1)
   fail("useCache=false did not load fresh data without storing it");
  if(request("/tmp/assets/bg.png", true) != first || loads != 2)
   fail("uncached load replaced the existing cached value");
  if(!StringTools.startsWith(DiskBitmapCache.key("/tmp/assets/bg.png"), "fnfassets:disk-bitmap:"))
   fail("disk paths were not isolated in their own FlxGraphic cache key space");
  Sys.println("OK");
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "DiskBitmapCacheFixture.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "-cp", str(ROOT / "source"),
                 "--run", "DiskBitmapCacheFixture"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_fnfassets_uses_flixel_cache_for_disk_images(self):
        source = (ROOT / "source/FNFAssets.hx").read_text()
        self.assertIn("DiskBitmapCache.getOrLoad(bitmapKey, useCache", source)
        self.assertIn("FlxG.bitmap.get(key)", source)
        self.assertIn("FlxG.bitmap.add(data, false, key)", source)
        self.assertIn("Assets.getBitmapData(id, useCache)", source)
        self.assertIn("BitmapData.fromFile(path)", source)


if __name__ == "__main__":
    unittest.main()
