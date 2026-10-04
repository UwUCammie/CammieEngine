"""Exercise Nightmare Vision cache eviction and selected-owner disposal rules."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"


class NightmareVisionAssetCacheTest(unittest.TestCase):
    def test_active_permanent_disposal_and_release(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        fixture = r'''
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var root='assets/imported_mods/selected';
  var paths=new NightmareVisionPaths(root, true);
  var cache=new NightmareVisionFunkinAssetCache(paths);
  var activeSound=root+'/audio/active.ogg';
  var coldSound=root+'/audio/cold.ogg';
  var permanentSound=root+'/audio/permanent.ogg';
  cache.currentTrackedSounds.set(activeSound,new openfl.media.Sound());
  cache.currentTrackedSounds.set(coldSound,new openfl.media.Sound());
  cache.currentTrackedSounds.set(permanentSound,new openfl.media.Sound());
  cache.currentTrackedSounds.addPermanentKey(permanentSound);
  check(cache.currentTrackedSounds.cache.exists(activeSound),'source CacheMap exposes public cache map');
  cache.localTrackedAssets.push(activeSound);
  cache.clearStoredMemory();
  check(cache.currentTrackedSounds.exists(activeSound),'clearStoredMemory retains active sounds');
  check(cache.currentTrackedSounds.exists(permanentSound),'clearStoredMemory retains permanent sounds');
  check(!cache.currentTrackedSounds.exists(coldSound),'clearStoredMemory evicts inactive sounds');
  check(openfl.utils.Assets.cache.cleared.length==1 && openfl.utils.Assets.cache.cleared[0]==coldSound,
    'sound eviction clears only the selected owner asset key');
  check(cache.localTrackedAssets.length==0,'clearStoredMemory starts a fresh active set');

  var activeGraphicKey=root+'/images/active.png';
  var coldGraphicKey=root+'/images/cold.png';
  var permanentGraphicKey=root+'/images/permanent.png';
  var activeGraphic=new flixel.graphics.FlxGraphic(activeGraphicKey);
  var coldGraphic=new flixel.graphics.FlxGraphic(coldGraphicKey);
  var permanentGraphic=new flixel.graphics.FlxGraphic(permanentGraphicKey);
  cache.currentTrackedGraphics.set(activeGraphicKey,activeGraphic);
  cache.currentTrackedGraphics.set(coldGraphicKey,coldGraphic);
  cache.currentTrackedGraphics.set(permanentGraphicKey,permanentGraphic);
  cache.currentTrackedGraphics.addPermanentKey(permanentGraphicKey);
  var activeTextKey=root+'/data/active.txt';
  var coldTextKey=root+'/data/cold.txt';
  var permanentTextKey=root+'/data/permanent.txt';
  cache.currentTrackedTexts.set(activeTextKey,'active');
  cache.currentTrackedTexts.set(coldTextKey,'cold');
  cache.currentTrackedTexts.set(permanentTextKey,'permanent');
  cache.currentTrackedTexts.addPermanentKey(permanentTextKey);
  cache.localTrackedAssets.push(activeGraphicKey);
  cache.localTrackedAssets.push(activeTextKey);
  cache.clearUnusedMemory();
  check(cache.currentTrackedGraphics.exists(activeGraphicKey),'clearUnusedMemory retains active graphics');
  check(cache.currentTrackedGraphics.exists(permanentGraphicKey),'clearUnusedMemory retains permanent graphics');
  check(!cache.currentTrackedGraphics.exists(coldGraphicKey),'clearUnusedMemory evicts inactive graphics');
  check(cache.currentTrackedTexts.exists(activeTextKey),'clearUnusedMemory retains active text');
  check(cache.currentTrackedTexts.exists(permanentTextKey),'clearUnusedMemory retains permanent text');
  check(!cache.currentTrackedTexts.exists(coldTextKey),'clearUnusedMemory evicts inactive text');
  check(flixel.FlxG.bitmap.removed.indexOf(coldGraphic)>=0,'evicted graphic is removed from Flixel bitmap cache');
  check(openfl.utils.Assets.cache.cleared.indexOf(coldTextKey)>=0,'evicted text clears its OpenFL cache entry');

  var noDisposeSound=root+'/audio/no-dispose.ogg';
  cache.currentTrackedSounds.set(noDisposeSound,new openfl.media.Sound());
  cache.removeFromCache(noDisposeSound,false);
  check(openfl.utils.Assets.cache.cleared.indexOf(noDisposeSound)<0,'disposeToo=false preserves underlying sound cache');
  var disposeText=root+'/data/dispose.txt';
  cache.currentTrackedTexts.set(disposeText,'value');
  cache.removeFromCache(disposeText,true);
  check(openfl.utils.Assets.cache.cleared.indexOf(disposeText)>=0,'disposeToo=true clears underlying text cache');

  var bitmap=new openfl.display.BitmapData();
  var before=openfl.display.BitmapData.imageDisposals;
  var gpuGraphic=cache.cacheBitmap(root+'/images/gpu.png',bitmap,true);
  check(gpuGraphic!=null && gpuGraphic.persist && !gpuGraphic.destroyOnNoUse,'cacheBitmap keeps source graphics persistent');
  check(openfl.display.BitmapData.imageDisposals==before+1,'cacheBitmap obeys allowGPU and owner GPU preference');
  var cpuBitmap=new openfl.display.BitmapData();
  cache.cacheBitmap(root+'/images/cpu.png',cpuBitmap,false);
  check(openfl.display.BitmapData.imageDisposals==before+1,'allowGPU=false skips GPU disposal');
  var remote=cache.cacheRemoteBitmap('https://example.invalid/chart.png',new openfl.display.BitmapData(),false);
  check(remote!=null && cache.currentTrackedGraphics.exists('https://example.invalid/chart.png'),'PNG URL gets owner cache entry');
  var otherPaths=new NightmareVisionPaths('assets/imported_mods/other',true);
  var otherCache=new NightmareVisionFunkinAssetCache(otherPaths);
  var otherRemote=otherCache.cacheRemoteBitmap('https://example.invalid/chart.png',new openfl.display.BitmapData(),false);
  check(remote.key!=otherRemote.key,'the same remote URL gets distinct process-global FlxGraphic keys per owner');
  check(cache.cacheRemoteBitmap('https://example.invalid/chart.jpg',new openfl.display.BitmapData(),true)==null,
    'remote cache accepts PNG only');
  check(!cache.removeFromCache('assets/imported_mods/other/private.png'),'foreign owner key is rejected');
  check(cache.removeFromCache('https://example.invalid/chart.png'),'remote graphic can be evicted by its exact URL');

  cache.release();
  check(!cache.currentTrackedGraphics.keys().hasNext() && !cache.currentTrackedSounds.keys().hasNext()
    && !cache.currentTrackedTexts.keys().hasNext(),'owner release removes all cache entries, including permanent ones');
  check(otherCache.currentTrackedGraphics.exists('https://example.invalid/chart.png')
    && flixel.FlxG.bitmap.removed.indexOf(otherRemote)<0,'releasing one owner leaves another owner remote graphic live');
  check(flixel.FlxG.bitmap.removed.length>=4,'owner release removes its remaining graphics');
  var rejected=false;
  try cache.removeFromCache(activeGraphicKey) catch (_:Dynamic) rejected=true;
  check(rejected && cache.isReleased(),'released cache rejects further operations');
 }
}
'''
        stubs = {
            "NightmareVisionPaths.hx": '''class NightmareVisionPaths {
 public final root:String; final gpu:Bool;
 public function new(root:String,gpu:Bool){this.root=root;this.gpu=gpu;}
 public function scopeAssetPath(key:String):Null<String> {
  if(key==null)return null;
  if(key==root || StringTools.startsWith(key,root+'/'))return key;
  if(StringTools.startsWith(key,'assets/imported_mods/'))return null;
  if(StringTools.startsWith(key,'/') || key.indexOf('..')>=0 || key.indexOf(':')>=0)return null;
  return root+'/'+key;
 }
 public function gpuCachingEnabled():Bool return gpu;
}''',
            "flixel/FlxBitmapCache.hx": '''package flixel;
class FlxBitmapCache {public var removed:Array<flixel.graphics.FlxGraphic>=[];public function new(){} public function add(value:Dynamic,unique:Bool=false,?key:String):flixel.graphics.FlxGraphic return new flixel.graphics.FlxGraphic(key==null?Std.string(value):key,Std.isOfType(value,openfl.display.BitmapData)?cast value:null); public function remove(g:flixel.graphics.FlxGraphic):Bool {removed.push(g);return true;}}''',
            "flixel/FlxG.hx": '''package flixel;
class FlxG {public static var bitmap:FlxBitmapCache=new FlxBitmapCache();}''',
            "flixel/graphics/FlxGraphic.hx": '''package flixel.graphics;
class FlxGraphic {public var key:String;public var bitmap:openfl.display.BitmapData;public var persist:Bool=false;public var destroyOnNoUse:Bool=true;public function new(key:String,?bitmap:openfl.display.BitmapData){this.key=key;this.bitmap=bitmap==null?new openfl.display.BitmapData():bitmap;}}''',
            "openfl/display/BitmapData.hx": '''package openfl.display;
class Texture {public var disposed:Int=0;public function new(){} public function dispose():Void disposed++;}
class BitmapData {public static var imageDisposals:Int=0;public var __texture:Texture=new Texture();public function new(){} public function disposeImage():Void imageDisposals++; public function dispose():Void {}}''',
            "openfl/media/Sound.hx": '''package openfl.media;
class Sound {public function new(){}}''',
            "openfl/utils/Assets.hx": '''package openfl.utils;
class AssetCache {public var cleared:Array<String>=[];public function new(){}public function clear(key:String):Void cleared.push(key);}
class Assets {public static var cache:AssetCache=new AssetCache();}''',
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            for name, content in stubs.items():
                path = work / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
            (work / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "--main", "Main", "--interp"], cwd=work, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
