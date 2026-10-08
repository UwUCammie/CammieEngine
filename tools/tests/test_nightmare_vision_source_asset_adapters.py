"""Focused portable checks for the owner-scoped source Paths/FunkinAssets APIs."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class NightmareVisionSourceAssetAdaptersTest(unittest.TestCase):
    def test_audio_paths_multi_atlas_and_owner_asset_reads(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        fixture = r'''
class Main {
 static function fail(message:String):Void throw message;
 static function check(value:Bool, message:String):Void if (!value) fail(message);
 static function eq(actual:Dynamic, expected:Dynamic, message:String):Void
  if (actual != expected) fail(message + ': expected ' + Std.string(expected) + ', got ' + Std.string(actual));
 static function main() {
  var root = 'assets/imported_mods/owner';
  var prefs:Dynamic = {streamedMusic:false, gpuCaching:true};
  var paths = new NightmareVisionPaths(root, null, prefs, 'source-pack');
  var assets = new NightmareVisionFunkinAssets(paths);
  check(paths.MODS_DIRECTORY == 'content', 'source MODS_DIRECTORY');
  eq(paths.mods('source-pack/songs/my-song'), root + '/songs/my-song', 'owner-only Paths.mods');
  eq(paths.scopeAssetPath('content/source-pack/songs/my-song/Inst.ogg'),
    root + '/songs/my-song/Inst.ogg', 'source content alias');
  eq(paths.getModFolder(root + '/songs/my-song/Inst.ogg'), 'source-pack', 'owner mod label');
  eq(paths.trackSwap('My Song').path, root + '/songs/my-song/audio/Track.ogg', 'track swap audio directory');
  eq(paths.voices('My Song', 'player').path, root + '/songs/my-song/audio/Voices-player.wav', 'voices postfix and wav');
  eq(paths.inst('My Song').path, root + '/songs/my-song/audio/Inst.ogg', 'instrumental path');
  eq(paths.inst('Missing Song').path, 'flixel/sounds/beep', 'source missing Inst fallback');
  prefs.streamedMusic = true;
  eq(paths.voices('My Song'), null, 'streamed Voices uses Vorbis only');
  eq(paths.inst('My Song').path, root + '/songs/my-song/audio/Inst.ogg', 'streamed Inst falls back to cached Sound');
  prefs.streamedMusic = false;
  var keys = ['sheet1', 'sheet2'];
  var atlas = paths.getMultiAtlas(keys);
  eq(keys.join(','), 'sheet2', 'source multi-atlas consumes the first key');
  eq(atlas.kind, 'merged', 'multi-atlas merges remaining atlases');
  eq(assets.getContent(root + '/data/message.txt'), 'owned text', 'owner text');
  eq(assets.getContent('content/source-pack/data/message.txt'), 'owned text', 'source path alias through FunkinAssets');
  eq(assets.getBytes(root + '/data/message.txt').length, 10, 'owner bytes');
  eq(assets.exists(root + '/data/message.txt'), true, 'owner exists');
  eq(assets.exists('assets/data/engine-only.txt'), false, 'native asset is not exposed');
  eq(assets.exists('assets/imported_mods/other/data/secret.txt'), false, 'foreign owner is not exposed');
  eq(assets.getSound(root + '/songs/my-song/audio/Inst.ogg').path,
    root + '/songs/my-song/audio/Inst.ogg', 'owner sound');
  eq(assets.getSoundUnsafe(root + '/songs/missing/Voices.ogg'), null, 'unsafe sound missing is null');
  var parsed:Dynamic = assets.parseJson('{"ok":true}');
  check(parsed != null && parsed.ok, 'source JSON parse');
  eq(assets.parseJson('{'), null, 'invalid JSON returns null');
  eq(assets.readDirectory(root + '/data').join(','), 'message.txt', 'owner directory listing');
  eq(assets.isDirectory(root + '/data'), true, 'owner directory check');
  var priorImageDisposals = openfl.display.BitmapData.imageDisposals;
  var canonicalImage = FNFAssets.getFlxGraphic(root + '/images/gpu-check.png');
  var gpuImage = paths.image('gpu-check', null, true, true);
  check(gpuImage == canonicalImage, 'Paths.image tracks FNFAssets canonical graphic identity');
  check(assets.cache.currentTrackedGraphics.get(root + '/images/gpu-check.png') == canonicalImage,
    'owner cache tracks the canonical graphic under its owner path');
  check(openfl.display.BitmapData.imageDisposals == priorImageDisposals + 1, 'Paths.image forwards allowGPU and gpuCaching preference');
  var cpuImage = paths.image('cpu-check', null, false, true);
  check(cpuImage != null && openfl.display.BitmapData.imageDisposals == priorImageDisposals + 1, 'allowGPU=false preserves bitmap data');
  var missingImage = paths.image('not-present');
  check(missingImage != null && missingImage.key == 'flixel/images/logo/default.png', 'missing image returns source Flixel logo');
  var remoteKey = 'https://example.invalid/chart-art.png';
  var remote = assets.cache.cacheRemoteBitmap(remoteKey, new openfl.display.BitmapData(), false);
  check(paths.imageFromURL(remoteKey) == remote, 'imageFromURL returns an already cached owner graphic');
  check(paths.imageFromURL('https://example.invalid/chart-art.jpg') == null, 'imageFromURL remains PNG-only');
  var combined = paths.listAllFilesInDirectory('data');
  check(combined.length == 2 && combined[0].indexOf('__nmv_core/data/core.txt') >= 0
    && combined[1].indexOf('/data/message.txt') >= 0, 'core-first owner directory listing');
  var rejected = false;
  try assets.getContent(root + '/../other/data/secret.txt') catch (_:Dynamic) rejected = true;
  check(!rejected && assets.getContent(root + '/../other/data/secret.txt') == '', 'traversal cannot read another owner');
  paths.releaseOwnerAssets();
  var canonicalRemovals=0;
  for (graphic in flixel.FlxG.bitmap.removed) if (graphic == canonicalImage) canonicalRemovals++;
  check(canonicalRemovals==1, 'owner teardown removes the single canonical graphic once');
 }
}
'''
        stubs = {
            "ImportRefreshManager.hx": '''package;
class ImportRefreshManager {
 public static var generation:Int = 0;
 public static function availabilityRevision():Int return 0;
 public static function ownerAssetIndexBinding(owner:String,engine:String,scope:String):Dynamic return null;
}''',
            # These adapter fixtures exercise NV paths and file reads, not the
            # separate Psych Lime-library loader. Keep the identity teardown
            # hook available without pulling Lime Future/AssetLibrary into this
            # intentionally narrow Haxe eval fixture.
            "PsychOwnerAssetLibraryCache.hx": '''package;
class PsychOwnerAssetLibraryCache {
 public static function releaseIdentity(identity:RuntimeOwnerAssetIdentity):Void
  if (identity != null) identity.retireAssetLibraryViews();
}''',
            "PsychOwnerAssetLibraryView.hx": '''package;
class PsychOwnerAssetLibraryView {
 public function new() {}
 public function retire():Void {}
}''',
            "tjson/TJSON.hx": '''package tjson;
class TJSON {}
enum EncodeStyle { Full; }
class TJSONEncoder {
 public function new(){}
 public function doEncode(value:Dynamic, ?style:String):String return haxe.Json.stringify(value);
 public function encodeValue(value:Dynamic, style:EncodeStyle, depth:Int):String return haxe.Json.stringify(value);
}''',
            # Script-name cache type only; real module execution has separate Stage/Iris coverage.
            "NightmareVisionScriptModule.hx": "class NightmareVisionScriptModule {}",
            "flixel/FlxBitmapCache.hx": '''package flixel;
class FlxBitmapCache {public var removed:Array<flixel.graphics.FlxGraphic>=[];public var cached:Map<String,flixel.graphics.FlxGraphic>=new Map();public function new(){} public function add(value:Dynamic, unique:Bool=false, ?key:String):flixel.graphics.FlxGraphic {
 var bitmap:openfl.display.BitmapData=Std.isOfType(value,openfl.display.BitmapData)?cast value:null;
 var selected=key;
 if(selected==null && bitmap!=null)for(candidate in cached.keys())if(cached.get(candidate).bitmap==bitmap){selected=candidate;break;}
 if(selected==null)selected=Std.string(value);
 if(cached.exists(selected))return cached.get(selected);
 var graphic=new flixel.graphics.FlxGraphic(selected,bitmap);cached.set(selected,graphic);return graphic;
 }
 public function remove(graphic:flixel.graphics.FlxGraphic):Bool {removed.push(graphic);return true;} }''',
            "flixel/FlxRandom.hx": '''package flixel;
class FlxRandom {public function new(){} public function int(min:Int,max:Int):Int return min;}''',
            "flixel/FlxG.hx": '''package flixel;
class FlxG {public static var bitmap:FlxBitmapCache=new FlxBitmapCache(); public static var random:FlxRandom=new FlxRandom();}''',
            "flixel/graphics/FlxGraphic.hx": '''package flixel.graphics;
class FlxGraphic {public var key:String;public var bitmap:openfl.display.BitmapData;public var persist:Bool=false;public var destroyOnNoUse:Bool=true;public function new(key:String,?bitmap:openfl.display.BitmapData){this.key=key;this.bitmap=bitmap==null?new openfl.display.BitmapData():bitmap;}}''',
            "flixel/graphics/frames/FlxAtlasFrames.hx": '''package flixel.graphics.frames;
class FlxAtlasFrames {public var kind:String;public var image:flixel.graphics.FlxGraphic;public var text:String;public var parent:flixel.graphics.FlxGraphic;
public function new(parent:flixel.graphics.FlxGraphic){this.parent=parent;kind='plain';image=parent;}
public function addAtlas(other:FlxAtlasFrames, overwrite:Bool):Void kind='merged';
public static function fromSparrow(i:flixel.graphics.FlxGraphic,t:String):FlxAtlasFrames {var a=new FlxAtlasFrames(i);a.kind='xml';a.text=t;return a;}
public static function fromAseprite(i:flixel.graphics.FlxGraphic,t:String):FlxAtlasFrames {var a=new FlxAtlasFrames(i);a.kind='json';a.text=t;return a;}
public static function fromSpriteSheetPacker(i:flixel.graphics.FlxGraphic,t:String):FlxAtlasFrames {var a=new FlxAtlasFrames(i);a.kind='txt';a.text=t;return a;}}''',
            "animate/FlxAnimateFrames.hx": '''package animate;
import flixel.graphics.frames.FlxAtlasFrames;
typedef SpritemapInput = {source:Dynamic, json:String}
class FlxAnimateFrames extends FlxAtlasFrames {
public function new(parent:flixel.graphics.FlxGraphic)super(parent);
public static function fromAnimate(input:String,maps:Array<SpritemapInput>,?metadata:String,?key:String):FlxAnimateFrames
 return new FlxAnimateFrames(new flixel.graphics.FlxGraphic(key));
}''',
            "openfl/media/Sound.hx": '''package openfl.media;
class Sound {public var path:String;public function new(path:String)this.path=path;}''',
            "openfl/display/BitmapData.hx": '''package openfl.display;
class Texture {public var disposed:Int=0;public function new(){}public function dispose():Void disposed++;}
class BitmapData {public static var imageDisposals:Int=0;public static var disposals:Int=0;public var __texture:Texture=new Texture();public static function fromBytes(bytes:haxe.io.Bytes):BitmapData return new BitmapData();public function new(){}public function disposeImage():Void imageDisposals++;public function dispose():Void disposals++;}''',
            "openfl/utils/Assets.hx": '''package openfl.utils;
class AssetCache {public var cleared:Array<String>=[];public function new(){}public function clear(key:String):Void cleared.push(key);}
class Assets {public static var cache:AssetCache=new AssetCache();}''',
            "flixel/system/FlxAssets.hx": '''package flixel.system;
class FlxAssets {public static function getSoundAddExtension(path:String):openfl.media.Sound return new openfl.media.Sound(path);}''',
            "FNFAssets.hx": '''import haxe.io.Bytes;
class FNFAssets {
static var bitmaps:Map<String,openfl.display.BitmapData>=new Map();
public static function exists(path:String):Bool return sys.FileSystem.exists(path);
public static function resolveCaseInsensitivePath(path:String):String return exists(path)?path:null;
public static function getText(path:String):String return sys.io.File.getContent(path);
public static function getBytes(path:String):Bytes return sys.io.File.getBytes(path);
public static function getBitmapData(path:String,useCache:Bool=true):openfl.display.BitmapData {
 if(!bitmaps.exists(path)){var bitmap=new openfl.display.BitmapData();bitmaps.set(path,bitmap);flixel.FlxG.bitmap.add(bitmap,false,'canonical:'+path);}
 return bitmaps.get(path);
}
public static function getFlxGraphic(path:String,useCache:Bool=true):flixel.graphics.FlxGraphic return flixel.FlxG.bitmap.add(getBitmapData(path,useCache));
public static function getSound(path:String,useCache:Bool=true):openfl.media.Sound return new openfl.media.Sound(path);
public static function readDirectory(path:String):Array<String> return sys.FileSystem.readDirectory(path);
public static function isDirectory(path:String):Bool return sys.FileSystem.exists(path)&&sys.FileSystem.isDirectory(path);
}''',
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            for name, content in stubs.items():
                path = work / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
            owner = work / "assets/imported_mods/owner"
            fixture_files = {
                "songs/my-song/audio/Track.ogg": "track",
                "songs/my-song/audio/Voices-player.wav": "voices",
                "songs/my-song/audio/Inst.ogg": "inst",
                "songs/my-song/Track.ogg": "fallback-track",
                "images/sheet1.png": "img1", "images/sheet1.txt": "atlas1",
                "images/sheet2.png": "img2", "images/sheet2.txt": "atlas2",
                "images/gpu-check.png": "gpu", "images/cpu-check.png": "cpu",
                "data/message.txt": "owned text",
                "__nmv_core/data/core.txt": "core",
            }
            for name, content in fixture_files.items():
                path = owner / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
            (work / "assets/data/engine-only.txt").parent.mkdir(parents=True, exist_ok=True)
            (work / "assets/data/engine-only.txt").write_text("native", encoding="utf-8")
            (work / "assets/imported_mods/other/data").mkdir(parents=True)
            (work / "assets/imported_mods/other/data/secret.txt").write_text("foreign", encoding="utf-8")
            (work / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "--main", "Main", "--interp"], cwd=work, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
