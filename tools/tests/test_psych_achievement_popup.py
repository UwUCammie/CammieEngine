"""Compile the actual Psych achievement popup against narrow native API stubs."""
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND, TEST_TMP

ROOT = Path(__file__).resolve().parents[2]


class PsychAchievementPopupTest(unittest.TestCase):
    def test_owner_visuals_timing_resize_and_captured_lifecycle(self):
        main = r'''package;
import openfl.display.BitmapData;
import flixel.FlxG;
import flixel.graphics.FlxGraphic;
import flixel.text.FlxText;
import openfl.display.Graphics;
import openfl.display.Sprite;
import openfl.display.Stage;
import openfl.events.Event;
import PsychAchievementInfo;
import PsychAchievementPopup.PsychAchievementPopupAssets;
import PsychAchievementPopup.PsychAchievementPopupHost;

@:access(PsychAchievementPopup)
class PopupFixtureMain {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  BitmapData.resetCounts();
  var slash = String.fromCharCode(92);
  check(PsychAchievementPopup.cleanAchievementId('nested/chapter..v1') == 'nested/chapter..v1'
   && PsychAchievementPopup.cleanAchievementId('nested' + slash + 'chapter..v1') == 'nested/chapter..v1',
   'safe nested relative keys and filenames containing literal dots must be retained');
  check(PsychAchievementPopup.cleanAchievementId('../escape') == null
   && PsychAchievementPopup.cleanAchievementId('nested/../escape') == null
   && PsychAchievementPopup.cleanAchievementId('nested/./escape') == null
   && PsychAchievementPopup.cleanAchievementId('/absolute') == null
   && PsychAchievementPopup.cleanAchievementId('C:root') == null
   && PsychAchievementPopup.cleanAchievementId('nul' + String.fromCharCode(0) + 'id') == null,
   'rooted, dot-segment and invalid paths must be rejected before asset lookup');
  var capturedStage = new Stage(); capturedStage.stageHeight = 720;
  var capturedGame = new Sprite();
  var otherStage = new Stage();
  var otherGame = new Sprite();
  FlxG.stage = capturedStage; FlxG.game = capturedGame; FlxG.height = 720;
  var pixelBitmap = new BitmapData(200, 100);
  var pixelGraphic = new FlxGraphic(pixelBitmap);
  var unknownBitmap = new BitmapData(100, 100);
  var unknownGraphic = new FlxGraphic(unknownBitmap);
  var imageRequests:Array<String> = [];
  var fileRequests:Array<String> = [];
  var modRequests:Array<String> = [];
  var phraseRequests:Array<String> = [];
  var registered:Array<PsychAchievementPopup> = [];
  var clock:Float = 0;
  var ownerIsActive = true;
  var assets:PsychAchievementPopupAssets = {
   fileExists:function(path:String):Bool {fileRequests.push(path);return path == 'images/achievements/freaky-pixel.png';},
   image:function(key:String):FlxGraphic {
    imageRequests.push(key);
    return key == 'achievements/freaky-pixel' ? pixelGraphic : key == 'unknownMod' ? unknownGraphic : null;
   },
   font:function(key:String):String return 'owner/fonts/' + key
  };
  var host:PsychAchievementPopupHost = {
   ownerRoot:'assets/imported_mods/family/root',
   assetsForAchievementMod:function(mod:Null<String>):PsychAchievementPopupAssets {modRequests.push(mod);return assets;},
   antialiasing:function():Bool return true,
   phrase:function(key:String, fallback:String):String {phraseRequests.push(key);return 'localized:' + fallback;},
   stage:capturedStage, game:capturedGame,
   now:function():Float return clock,
   ownerActive:function():Bool return ownerIsActive,
   registerPopup:function(popup:PsychAchievementPopup):Void registered.push(popup),
   unregisterPopup:function(popup:PsychAchievementPopup):Void registered.remove(popup)
  };
  var finishCalls = 0;
  var info:PsychAchievementInfo = {name:'Friday Player', description:'Play on Friday', mod:'family-child', ID:9};
  var popup = new PsychAchievementPopup('freaky', function() finishCalls++, info, host);
  check(popup.onFinish == null && finishCalls == 0,
   'the donor constructor accepts onFinish but leaves its public field null and never invokes it');
  check(modRequests.length == 1 && modRequests[0] == 'family-child',
   'achievement assets must resolve through the selected owner and metadata mod');
  check(fileRequests.length == 1 && fileRequests[0] == 'images/achievements/freaky-pixel.png'
   && imageRequests.join(',') == 'achievements/freaky-pixel',
   'a matching pixel icon should be selected without also loading the regular icon');
  check(phraseRequests.join(',') == 'achievement_freaky,description_freaky'
   && FlxText.lastFont == 'owner/fonts/vcr.ttf',
   'the popup should localize owner achievement text and use the owner VCR font');
  check(popup.graphics.roundRects[0].join(',') == '0,0,420,130,16,16'
   && popup.graphics.rects[0].join(',') == '15,15,110,110',
   'the popup should retain the 420 by 130 panel and 100-pixel icon layout');
  check(popup.graphics.bitmapFills[0].bitmap == pixelBitmap
   && popup.graphics.bitmapFills[0].smooth == false,
   'pixel artwork must be drawn without smoothing regardless of the owner AA preference');
  check(capturedGame.contains(popup) && registered.length == 1
   && capturedStage.listenerCount(Event.RESIZE) == 1
   && popup.listenerCount(Event.ENTER_FRAME) == 1,
   'the popup should attach once to captured display objects and the owner registry');
  check(!popup.destroyed && popup.attached && popup.listeningForResize
   && popup.listeningForFrame && popup.registrationAttempted && popup.bitmaps.length == 2,
   'native probes can inspect live owner/listener/bitmap state through @:access');
  check(popup.iconGraphic == pixelGraphic && popup.iconGraphicRetained && pixelGraphic.useCount == 1
   && pixelBitmap.disposeCalls == 0,
   'the selected cached icon graphic must hold one use-count lease while its bitmap fill is alive');
  check(popup.x == 20 && popup.y == -130 && popup.scaleX == 1 && popup.intendedY == 20,
   'initial stage scaling and offscreen position should match the donor');

  popup.dispatchEvent(new Event(Event.ENTER_FRAME));
  clock = 250;
  popup.dispatchEvent(new Event(Event.ENTER_FRAME));
  check(Math.abs(popup.y - -92.5) < 0.001,
   'entry should use wall-clock elapsed time and the elastic easing path');
  clock = 1250;
  popup.dispatchEvent(new Event(Event.ENTER_FRAME));
  check(Math.abs(Reflect.field(popup, 'countedTime') - 0.25) < 0.001,
   'a loading pause of at least half a second must be ignored by the toast timer');

  FlxG.stage = otherStage; FlxG.game = otherGame;
  capturedStage.stageHeight = 1440;
  capturedStage.dispatchEvent(new Event(Event.RESIZE));
  check(popup.scaleX == 2 && popup.scaleY == 2 && popup.x == 40 && popup.y == -185,
   'resize should use the captured stage while preserving the popup position ratio');
  clock = 1350;
  for (_ in 0...32) {
   popup.dispatchEvent(new Event(Event.ENTER_FRAME));
   clock += 100;
  }
  check(!capturedGame.contains(popup) && registered.length == 0
   && capturedStage.listenerCount(Event.RESIZE) == 0
   && popup.listenerCount(Event.ENTER_FRAME) == 0 && popup.destroyed && !popup.attached
   && !popup.listeningForResize && !popup.listeningForFrame && !popup.registrationAttempted
   && popup.bitmaps == null && !popup.iconGraphicRetained && popup.iconGraphic == null
   && pixelGraphic.useCount == 0,
   'the timed exit must remove the popup and all listeners from the captured display objects: y='
    + popup.y + ' counted=' + Reflect.field(popup,'countedTime') + ' children=' + capturedGame.children.length
    + ' registered=' + registered.length + ' resize=' + capturedStage.listenerCount(Event.RESIZE)
    + ' frame=' + popup.listenerCount(Event.ENTER_FRAME));
  check(finishCalls == 0 && pixelBitmap.disposeCalls == 0
   && BitmapData.created == 5 && BitmapData.disposed == 3 && BitmapData.imageDisposed == 3,
   'cleanup should dispose only temporary text bitmaps and never call the unused finish callback: finish='
    + finishCalls + ' pixel=' + pixelBitmap.disposeCalls + ' created=' + BitmapData.created
    + ' disposed=' + BitmapData.disposed + ' imageDisposed=' + BitmapData.imageDisposed);
  popup.destroy();
  check(BitmapData.disposed == 3 && registered.length == 0 && pixelGraphic.useCount == 0
   && pixelBitmap.disposeCalls == 0,
   'repeated destruction must not release the icon lease twice or dispose its borrowed bitmap');

  // Missing metadata and images use the native unknown label/icon fallback.
  var missingStage = new Stage(); missingStage.stageHeight = 720;
  var missingGame = new Sprite();
  var missingBitmap = new BitmapData(100, 100);
  var missingGraphic = new FlxGraphic(missingBitmap);
  var missingImages:Array<String> = [];
  var missingFiles:Array<String> = [];
  var missingRegistered:Array<PsychAchievementPopup> = [];
  var missingActive = true;
  var missingAssets:PsychAchievementPopupAssets = {
   fileExists:function(path:String):Bool {missingFiles.push(path);return false;},
   image:function(key:String):FlxGraphic {missingImages.push(key);return key == 'unknownMod' ? missingGraphic : null;},
   font:function(key:String):String return 'shared/fonts/' + key
  };
  var missingHost:PsychAchievementPopupHost = {
   ownerRoot:'assets/imported_mods/family/root',
   assetsForAchievementMod:function(mod:Null<String>):PsychAchievementPopupAssets return missingAssets,
   antialiasing:function():Bool return false,
   phrase:function(key:String, fallback:String):String return fallback,
   stage:missingStage, game:missingGame,
   now:function():Float return 0,
   ownerActive:function():Bool return missingActive,
   registerPopup:function(popup:PsychAchievementPopup):Void missingRegistered.push(popup),
   unregisterPopup:function(popup:PsychAchievementPopup):Void missingRegistered.remove(popup)
  };
  var missing = new PsychAchievementPopup('missing', null, null, missingHost);
  check(missingImages.join(',') == 'achievements/missing,unknownMod'
   && missing.graphics.bitmapFills[0].bitmap == missingBitmap
   && missing.graphics.bitmapFills[0].smooth == false && missing.iconGraphic == missingGraphic
   && missing.iconGraphicRetained && missingGraphic.useCount == 1,
   'missing achievement metadata/icon should keep source fallback text and owner antialiasing for unknownMod');
  FlxG.stage = otherStage; FlxG.game = otherGame;
  missingActive = false;
  missing.dispatchEvent(new Event(Event.ENTER_FRAME));
  check(!missingGame.contains(missing) && missingRegistered.length == 0
   && missingStage.listenerCount(Event.RESIZE) == 0 && missingGraphic.useCount == 0
   && !missing.iconGraphicRetained && missing.iconGraphic == null && missingBitmap.disposeCalls == 0,
   'an owner departure should retire a popup even if the host game and stage globals changed');
 }
}
'''
        stubs = {
            "openfl/events/Event.hx": r'''package openfl.events;
class Event {
 public static inline var RESIZE:String='resize';
 public static inline var ENTER_FRAME:String='enterFrame';
 public final type:String;
 public function new(type:String) this.type=type;
}
''',
            "openfl/geom/Matrix.hx": r'''package openfl.geom;
class Matrix {
 public final a:Float; public final b:Float; public final c:Float; public final d:Float;
 public final tx:Float; public final ty:Float;
 public function new(a:Float=1,b:Float=0,c:Float=0,d:Float=1,tx:Float=0,ty:Float=0) {
  this.a=a;this.b=b;this.c=c;this.d=d;this.tx=tx;this.ty=ty;
 }
}
''',
            "openfl/display/BitmapData.hx": r'''package openfl.display;
class BitmapData {
 public static var created:Int=0; public static var disposed:Int=0; public static var imageDisposed:Int=0;
 public var width:Int; public var height:Int; public var disposeCalls:Int=0; public var imageDisposeCalls:Int=0;
 public function new(width:Int=1,height:Int=1) {this.width=width;this.height=height;created++;}
 public function clone():BitmapData return new BitmapData(width,height);
 public function dispose():Void {disposeCalls++;disposed++;}
 public function disposeImage():Void {imageDisposeCalls++;imageDisposed++;}
 public static function resetCounts():Void {created=0;disposed=0;imageDisposed=0;}
}
''',
            "openfl/display/Graphics.hx": r'''package openfl.display;
import openfl.display.BitmapData;
import openfl.geom.Matrix;
typedef BitmapFill = { var bitmap:BitmapData; var matrix:Matrix; var smooth:Bool; }
class Graphics {
 public var roundRects:Array<Array<Float>>=[];
 public var rects:Array<Array<Float>>=[];
 public var bitmapFills:Array<BitmapFill>=[];
 public function new() {}
 public function beginFill(color:Int,alpha:Float=1):Void {}
 public function endFill():Void {}
 public function drawRoundRect(x:Float,y:Float,w:Float,h:Float,rx:Float,ry:Float):Void
  roundRects.push([x,y,w,h,rx,ry]);
 public function beginBitmapFill(bitmap:BitmapData,matrix:Matrix,repeat:Bool=true,smooth:Bool=false):Void
  bitmapFills.push({bitmap:bitmap,matrix:matrix,smooth:smooth});
 public function drawRect(x:Float,y:Float,w:Float,h:Float):Void rects.push([x,y,w,h]);
}
''',
            "openfl/display/Sprite.hx": r'''package openfl.display;
import openfl.events.Event;
class Sprite {
 public var graphics:Graphics=new Graphics();
 public var x:Float=0; public var y:Float=0; public var scaleX:Float=1; public var scaleY:Float=1;
 public var children:Array<Sprite>=[];
 var listeners:Map<String,Array<Dynamic>>=new Map();
 public function new() {}
 public function addChild(child:Sprite):Sprite {children.push(child);return child;}
 public function contains(child:Sprite):Bool return children.indexOf(child)>=0;
 public function removeChild(child:Sprite):Sprite {children.remove(child);return child;}
 public function addEventListener(type:String,callback:Dynamic,useCapture:Bool=false,priority:Int=0,useWeakReference:Bool=false):Void {
  var list=listeners.get(type);if(list==null){list=[];listeners.set(type,list);}if(list.indexOf(callback)<0)list.push(callback);
 }
 public function removeEventListener(type:String,callback:Dynamic,useCapture:Bool=false):Void {
  var list=listeners.get(type);if(list!=null)list.remove(callback);
 }
 public function listenerCount(type:String):Int {var list=listeners.get(type);return list==null?0:list.length;}
 public function dispatchEvent(event:Event):Bool {
  var list=listeners.get(event.type);if(list!=null)for(callback in list.copy())Reflect.callMethod(this,callback,[event]);return true;
 }
}
''',
            "openfl/display/Stage.hx": "package openfl.display; class Stage extends Sprite { public var stageHeight:Float=720; public function new() super(); }\n",
            "flixel/FlxG.hx": r'''package flixel;
import openfl.display.Sprite;
import openfl.display.Stage;
class FlxG { public static var height:Float=720; public static var stage:Stage=new Stage(); public static var game:Sprite=new Sprite(); }
''',
            "flixel/graphics/FlxGraphic.hx": r'''package flixel.graphics;
import openfl.display.BitmapData;
class FlxGraphic {
 public var bitmap:BitmapData; public var useCount:Int=0;
 public function new(bitmap:BitmapData) this.bitmap=bitmap;
 public function incrementUseCount():Void useCount++;
 public function decrementUseCount():Void useCount--;
}
''',
            "flixel/text/FlxText.hx": r'''package flixel.text;
import flixel.graphics.FlxGraphic;
import openfl.display.BitmapData;
enum abstract FlxTextAlign(String) from String to String { var LEFT='left'; }
class FlxText {
 public static var lastFont:String;
 public var text:String; public var width:Float; public var height:Float=16; public var graphic:FlxGraphic;
 public var destroyed:Bool=false;
 public function new(x:Float,y:Float,width:Float,text:String,size:Int) {
  this.width=width;this.text=text;graphic=new FlxGraphic(new BitmapData(270,16));
 }
 public function setFormat(font:String,size:Int,color:Int,align:FlxTextAlign):Void lastFont=font;
 public function updateHitbox():Void width=text.length*8;
 public function destroy():Void destroyed=true;
}
''',
            "flixel/util/FlxColor.hx": "package flixel.util; class FlxColor { public static inline var BLACK:Int=0xFF000000; public static inline var WHITE:Int=0xFFFFFFFF; }\n",
            "flixel/tweens/FlxEase.hx": "package flixel.tweens; class FlxEase { public static function elasticOut(t:Float):Float return t; }\n",
        }
        with tempfile.TemporaryDirectory(prefix="psych-achievement-popup-", dir=TEST_TMP) as directory:
            work = Path(directory)
            (work / "PopupFixtureMain.hx").write_text(main, encoding="utf-8", newline="\n")
            for relative, content in stubs.items():
                target = work / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "-cp", str(ROOT / "source"), "--main", "PopupFixtureMain", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
