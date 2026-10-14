"""The Psych owner OpenFL facade never hands a disposed cached bitmap to scripts."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath

ROOT = Path(__file__).resolve().parents[2]


def haxe_env():
    env = dict(os.environ)
    env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
    env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
    env["PATH"] = os.pathsep.join(
        [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
    )
    return env


STUBS = {
    "FNFAssets.hx": r'''package;
import haxe.io.Bytes;
import haxe.io.Path;
import openfl.display.BitmapData;
import openfl.media.Sound;
import sys.FileSystem;
import sys.io.File;
class FNFAssets {
 public static var decodes:Int = 0;
 static function resolve(id:String):String return Path.normalize(id);
 public static function exists(id:String, ?ext:Dynamic):Bool return id != null && FileSystem.exists(resolve(id));
 public static function resolveCaseInsensitivePath(id:String):String return exists(id) ? resolve(id) : null;
 public static function getText(id:String):String return File.getContent(resolve(id));
 public static function getBytes(id:String):Bytes return File.getBytes(resolve(id));
 public static function getBitmapData(id:String, ?useCache:Bool = true):BitmapData {
  decodes++;
  return new BitmapData(1, 1, true, 0);
 }
 public static function getSound(id:String, ?useCache:Bool = true):Sound return null;
}''',
    "CompatScriptManifest.hx": 'package; class CompatScriptManifest { public static inline var ROOT_PREFIX = "assets/imported_mods"; }',
    "ImportRefreshManager.hx": '''package;
class ImportRefreshManager {
 public static var generation:Int=1;
 public static function availabilityRevision():Int return 1;
 public static function ownerAssetIndexBinding(owner:String,engine:String,scope:String):Dynamic return null;
}''',
    "tjson/TJSON.hx": '''package tjson;
class TJSON {}
enum EncodeStyle { Full; }
class TJSONEncoder {
 public function new(){}
 public function doEncode(value:Dynamic,?style:String):String return haxe.Json.stringify(value);
 public function encodeValue(value:Dynamic,style:EncodeStyle,depth:Int):String return haxe.Json.stringify(value);
}''',
    "BitmapValidityProbe.hx": r'''package;
import openfl.display.BitmapData;
class BitmapValidityProbe {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var owner = "assets/imported_mods/bitmap-owner";
  var assets:Dynamic = PsychOwnerOpenFlAssets.create(owner);
  var get = Reflect.field(assets, "getBitmapData");
  var id = "assets/images/sprite.png";
  var first:BitmapData = Reflect.callMethod(assets, get, [id]);
  check(first != null && FNFAssets.decodes == 1, "owner bitmap did not decode once");
  check(Reflect.callMethod(assets, get, [id]) == first && FNFAssets.decodes == 1,
   "a live cached bitmap was decoded again");
  // Destroying the last FlxGraphic that shares these pixels disposes them.
  first.dispose();
  var second:BitmapData = Reflect.callMethod(assets, get, [id]);
  check(second != first && second.image != null && FNFAssets.decodes == 2,
   "a disposed cached bitmap reached the script");
  check(Reflect.callMethod(assets, get, [id]) == second && FNFAssets.decodes == 2,
   "the replacement bitmap was not cached");
  var uncached:BitmapData = Reflect.callMethod(assets, get, [id, false]);
  check(uncached != second && FNFAssets.decodes == 3, "useCache=false read the owner cache");
 }
}''',
}


class PsychOwnerOpenFlBitmapValidityTest(unittest.TestCase):
    def test_disposed_cached_bitmap_is_decoded_again(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = FixturePath(directory)
            for name, content in STUBS.items():
                path = work / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
            image = work / "assets/imported_mods/bitmap-owner/images/sprite.png"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"fixture image")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "-lib", "lime", "-lib", "openfl", "-D", "tools", "--run", "BitmapValidityProbe"],
                cwd=work, env=haxe_env(), text=True, capture_output=True, timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
