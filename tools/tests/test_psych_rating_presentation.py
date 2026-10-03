"""Pin classic Psych's per-hit physics popups separately from NMV's pooled HUD."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class PsychRatingPresentationTest(unittest.TestCase):
    def test_classic_popups_use_new_physics_sprites_and_destruction_tweens(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter unavailable")
        stubs = {
            "flixel/FlxCamera.hx": r'''package flixel;
class FlxCamera { public function new(){} }
''',
            "flixel/FlxG.hx": r'''package flixel;
class FakeRandom {
 public function new(){}
 public function int(min:Int,max:Int):Int return min;
 public function float(min:Float,max:Float):Float return min;
}
class FlxG { public static var width:Int=1280; public static var height:Int=720; public static var random:FakeRandom=new FakeRandom(); }
''',
            "flixel/FlxSprite.hx": r'''package flixel;
class Point { public var x:Float=0; public var y:Float=0; public function new(){} }
class FlxSprite {
 public var x:Float=0; public var y:Float=0; public var width:Float=100; public var height:Float=40;
 public var alpha:Float=1; public var visible:Bool=true; public var antialiasing:Bool=true;
 public var scale:Point=new Point(); public var acceleration:Point=new Point(); public var velocity:Point=new Point();
 public var cameras:Array<FlxCamera>; public var path:String=''; public var destroyed:Bool=false;
 public function new(){}
 public function loadGraphic(asset:Dynamic):FlxSprite {
  path=Std.string(Reflect.field(asset,'path'));
  if(path.indexOf('num')>=0){width=10;height=20;} else {width=100;height=40;}
  return this;
 }
 public function screenCenter():Void {x=(FlxG.width-width)/2;y=(FlxG.height-height)/2;}
 public function setGraphicSize(width:Int,?height:Int):Void {
  var factor=width/this.width; this.width=width; this.height=Std.int(this.height*factor);
  scale.x*=factor; scale.y*=factor;
 }
 public function updateHitbox():Void{}
 public function destroy():Void destroyed=true;
}
''',
            "flixel/group/FlxGroup.hx": r'''package flixel.group;
class FlxGroup {}
class FlxTypedGroup<T> {
 public var members:Array<T>=[]; public var cameras:Array<flixel.FlxCamera>;
 public function new(){}
 public function add(value:T):T {members.push(value);return value;}
 public function remove(value:T,splice:Bool=false):T {members.remove(value);return value;}
 public function iterator():Iterator<T> return members.iterator();
}
''',
            "flixel/tweens/FlxTween.hx": r'''package flixel.tweens;
class FlxTween {
 public static var calls:Array<Dynamic>=[];
 public static function tween(target:Dynamic,values:Dynamic,duration:Float,?options:Dynamic):Dynamic {
  calls.push({target:target,duration:duration,options:options,fields:Reflect.fields(values)});return {};
 }
}
''',
        }
        fixture = r'''import flixel.FlxCamera;
import flixel.FlxG;
import flixel.FlxSprite;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.tweens.FlxTween;
class Main {
 static function check(ok:Bool,message:String):Void if(!ok)throw message;
 static function main():Void {
  var loaded:Array<String>=[]; var attached:Array<Dynamic>=[];
  var presentation=new PsychRatingPresentation({
   image:function(path:String):Dynamic {loaded.push(path);return {path:path};},
   camera:new FlxCamera(),
   addDisplay:function(value:Dynamic):Dynamic {attached.push(value);return value;},
   hideHud:function():Bool return false,
   comboOffsets:[5,7,11,17], assetPrefix:'ui/', assetSuffix:'.png',
   showRating:true, showCombo:true, showComboNum:true,
   playbackRate:function():Float return 2,
   crochet:function():Float return 120,
   randomInt:function(min:Int,max:Int):Int return min,
   randomFloat:function(min:Float,max:Float):Float return min
  });
  check(attached.length==1 && attached[0]==presentation.comboGroup,
   'classic Psych owns one shared combo group');
  presentation.cachePopUpScore();
  check(loaded.length==14 && loaded[0]=='ui/sick.png' && loaded[3]=='ui/shit.png'
   && loaded[4]=='ui/num0.png' && loaded[13]=='ui/num9.png',
   'classic Psych caches ratings and ten number assets');

  loaded.resize(0); FlxTween.calls.resize(0);
  presentation.popUpScore({image:'good'},12,{id:1});
  var group:FlxTypedGroup<FlxSprite>=presentation.comboGroup;
  check(group.members.length==5,'one hit creates rating, combo graphic, and three new digits');
  var rating:FlxSprite=group.members[0];
  var combo:FlxSprite=group.members[1];
  var digit:FlxSprite=group.members[2];
  check(rating.path=='ui/good.png' && rating.x==413 && rating.y==273,
   'rating image and common source placement');
  check(rating.acceleration.y==2200 && rating.velocity.y==-280 && rating.width==70,
   'rating uses classic random physics and 0.7 non-pixel sizing');
  check(combo.path=='ui/combo.png' && combo.acceleration.y==800
   && combo.velocity.y==-280 && combo.velocity.x==2 && combo.x==505,
   'classic combo graphic retains its own physics and rightmost-digit placement');
  check(digit.path=='ui/num0.png' && digit.x==369 && digit.y==413
   && digit.acceleration.y==800 && digit.velocity.y==-280 && digit.velocity.x==-10,
   'new combo digits use classic physics and shared digit geometry');
  check(loaded.join(',')=='ui/good.png,ui/combo.png,ui/num0.png,ui/num1.png,ui/num2.png',
   'per-hit popup loads only current images');
  check(FlxTween.calls.length==5,'one fade tween is scheduled for rating, combo, and each digit');
  check(FlxTween.calls[0].duration==0.1 && FlxTween.calls[0].options.startDelay==0.12
   && FlxTween.calls[3].duration==0.1 && FlxTween.calls[3].options.startDelay==0.06
   && FlxTween.calls[4].duration==0.1 && FlxTween.calls[4].options.startDelay==0.12,
   'classic fades scale with playback rate and crochet');

  var prior=group.members.copy();
  presentation.release();
  check(prior.length==5 && presentation.comboGroup==null
   && !prior[0].destroyed && !prior[1].destroyed && !prior[2].destroyed
   && !prior[3].destroyed && !prior[4].destroyed,
   'release clears adapter references without destroying owner-owned sprites');

  var pixel=new PsychRatingPresentation({
   image:function(path:String):Dynamic {return {path:path};}, camera:new FlxCamera(),
   addDisplay:function(value:Dynamic):Dynamic return value,
   hideHud:function():Bool return false, comboOffsets:[0,0,0,0],
   isPixelStage:true, pixelZoom:6
  });
  pixel.popUpScore('sick',1,null);
  var pixelRating:FlxSprite=pixel.comboGroup.members[0];
  check(pixelRating.width==510 && !pixelRating.antialiasing,
   'pixel popups use the source pixel zoom scale and disable antialiasing');
  Sys.println('psych-classic-rating-presentation-ok');
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            (work / "Main.hx").write_text(fixture, newline='\n')
            for name, content in stubs.items():
                target = work / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, newline='\n')
            for name in ("PsychRatingPresentation.hx", "PsychRatingPresentationCommon.hx"):
                shutil.copy2(ROOT / "source" / name, work / name)
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(work), "--run", "Main"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("psych-classic-rating-presentation-ok", result.stdout)

    def test_classic_source_does_not_share_nmv_persistent_root_lifecycle(self):
        psych = (ROOT / "source/PsychRatingPresentation.hx").read_text()
        nmv = (ROOT / "source/NightmareVisionRatingPresentation.hx").read_text()
        self.assertIn("new FlxSprite()", psych)
        self.assertIn("acceleration.y", psych)
        self.assertIn("randomInt(140, 175)", psych)
        self.assertIn("comboSprite.destroy()", psych)
        self.assertNotIn("extends PsychRatingPresentation", nmv)
        self.assertIn("ratingNumGroup.recycle(FlxSprite)", nmv)
        self.assertIn("{x:0.7, y:0.7}", nmv)


if __name__ == "__main__":
    unittest.main()
