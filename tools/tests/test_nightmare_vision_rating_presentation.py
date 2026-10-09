"""Execute NMV's PsychHUD rating popup bridge with small Flixel test doubles."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class NightmareVisionRatingPresentationTest(unittest.TestCase):
    def test_owner_assets_callbacks_geometry_recycling_and_tweens(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe unavailable")
        files = {
            "NightmareVisionPaths.hx": r'''class NightmareVisionPaths {
 public var RATINGS_PREFIX:String = 'owner/ratings/';
 public var COMBO_PREFIX:String = 'owner/combo/';
 public var usesSharedRatingPrefix:Bool = false;
 public var calls:Array<String> = [];
 public function new() {}
 public function image(path:String):Dynamic { calls.push(path); return {path:path}; }
}
''',
            "Conductor.hx": r'''class Conductor { public static var stepCrochet:Float = 125; }
''',
            "flixel/FlxCamera.hx": r'''package flixel;
class FlxCamera { public function new() {} }
''',
            "flixel/FlxG.hx": r'''package flixel;
class FlxG { public static var width:Int = 1280; public static var height:Int = 720; }
''',
            "flixel/tweens/FlxEase.hx": r'''package flixel.tweens;
class FlxEase { public static var expoOut:Dynamic = 'expoOut'; }
''',
            "flixel/tweens/FlxTween.hx": r'''package flixel.tweens;
class FlxTween {
 public static var calls:Array<String> = [];
 public static function cancelTweensOf(target:Dynamic, ?fields:Array<String>):Void
  calls.push('cancel:' + target.testName + ':' + (fields == null ? '*' : fields.join('|')));
 public static function tween(target:Dynamic, values:Dynamic, duration:Float, ?options:Dynamic):Dynamic {
  calls.push('tween:' + target.testName + ':' + duration + ':' + Reflect.fields(values).join('|'));
  return {};
 }
}
''',
            "flixel/FlxSprite.hx": r'''package flixel;
class TestScale {
 public var x:Float = 1; public var y:Float = 1; public var testName:String;
 public function new(name:String) testName = name + '.scale';
 public function set(x:Float, y:Float):Void { this.x=x; this.y=y; }
}
class FlxSprite {
 public var x:Float=0; public var y:Float=0; public var width:Float=100; public var height:Float=40;
 public var frameWidth:Float=100; public var frameHeight:Float=40; public var alpha:Float=1;
 public var scale:TestScale; public var cameras:Array<FlxCamera>;
 public var alive:Bool=true; public var exists:Bool=true; public var visible:Bool=true;
 public var graphicPath:String=''; public var testName:String='sprite';
 public function new() scale = new TestScale(testName);
 public function loadGraphic(graphic:Dynamic):FlxSprite {
  graphicPath = Std.string(Reflect.field(graphic, 'path'));
  if (graphicPath.indexOf('/num') >= 0) { frameWidth=10; frameHeight=20; }
  else { frameWidth=100; frameHeight=40; }
  width=frameWidth; height=frameHeight; return this;
 }
 public function screenCenter():Void { x=(FlxG.width-width)/2; y=(FlxG.height-height)/2; }
 public function updateHitbox():Void { width=frameWidth*scale.x; height=frameHeight*scale.y; }
 public function kill():Void { alive=false; exists=false; }
 public function revive():Void { alive=true; exists=true; }
}
''',
            "flixel/group/FlxGroup.hx": r'''package flixel.group;
class FlxGroup {}
class FlxTypedGroup<T> {
 public var members:Array<T> = []; public var cameras:Array<flixel.FlxCamera>;
 public function new() {}
 public function add(value:T):T { if (members.indexOf(value)<0) members.push(value); return value; }
 public function recycle(?type:Class<T>):T {
  for (item in members) {
   var basic:Dynamic=item;
   if (basic != null && basic.exists == false && Std.isOfType(item, type)) {
    basic.revive(); return item;
   }
  }
  return add(Type.createInstance(type, []));
 }
 public function iterator():Iterator<T> return members.iterator();
}
''',
            "Main.hx": r'''import flixel.FlxCamera;
import flixel.FlxSprite;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.tweens.FlxTween;
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main() {
  var paths = new NightmareVisionPaths();
  var camera = new FlxCamera();
  var attached:Array<Dynamic> = [];
  var callbackLog:Array<String> = [];
  var hidden=false;
  var ratingObj = {image:'sick'};
  var note = {id:9};
  var presentation = new NightmareVisionRatingPresentation({
   paths:paths, camera:camera,
   addDisplay:function(value:Dynamic):Dynamic { attached.push(value); return value; },
   callScript:function(name:String, args:Array<Dynamic>):Dynamic {
    check(args.length==4 && args[0]==note
     && (args[1]==ratingObj || Reflect.getProperty(args[1], 'name')=='good'
      || Reflect.getProperty(args[1], 'name')=='bad'),
     'source callbacks receive note, source-shaped rating, and real groups');
    check(Std.isOfType(args[2], FlxSprite) && Std.isOfType(args[3], FlxTypedGroup),
     'callback values are actual display objects');
    callbackLog.push(name); return null;
   },
   hideHud:function():Bool return hidden,
   useEpicRankings:function():Bool return true,
   showRatings:true, comboOffsets:[5,7,11,17]
  });
  check(attached.length==2 && attached[0]==presentation.ratingGraphic
   && attached[1]==presentation.ratingNumGroup, 'real objects are attached exactly once');
  check(presentation.ratingGraphic.cameras[0]==camera
   && presentation.ratingNumGroup.cameras[0]==camera, 'popup roots use the HUD camera');
  check(presentation.ratingPrefix=='owner/ratings/'
   && presentation.comboPrefix=='owner/combo/', 'prefixes are selected-owner defaults');

  presentation.cachePopUpScore();
  check(paths.calls.length==15, 'source cache loads 4 ratings plus epic and ten digits');
  check(paths.calls[0]=='owner/ratings/sick' && paths.calls[4]=='owner/ratings/epic'
   && paths.calls[5]=='owner/combo/num0' && paths.calls[14]=='owner/combo/num9',
   'all cache paths go through owner Paths');

  paths.calls.resize(0); FlxTween.calls.resize(0);
  presentation.popUpScore(ratingObj, 1234, note);
  check(callbackLog.join(',')=='onPopUpScore,onPopUpScorePost', 'callbacks bracket rendering');
  check(presentation.ratingGraphic.graphicPath=='owner/ratings/sick', 'rating image uses owner path');
  check(presentation.ratingGraphic.x==413 && presentation.ratingGraphic.y==273,
   'rating center/offset placement matches source');
  check(presentation.ratingGraphic.scale.x==0.785 && presentation.ratingGraphic.scale.y==0.785,
   'rating scale starts at source tween value');
  check(paths.calls.join(',')=='owner/ratings/sick,owner/combo/num1,owner/combo/num2,owner/combo/num3,owner/combo/num4',
   '1000+ combo uses the donor thousands digit and owner paths');
  var group:FlxTypedGroup<FlxSprite> = presentation.ratingNumGroup;
  check(group.members.length==4, 'four-digit combo has four actual sprite members');
  var first:FlxSprite = group.members[0];
  check(first.graphicPath=='owner/combo/num1' && first.x==369 && first.y==413,
   'digits use source spacing and combo offsets');
  check(first.scale.x==0.6 && first.scale.y==0.6 && first.cameras==null,
   'digits use source tween start scale and inherit the live group camera');
  check(FlxTween.calls.indexOf('tween:sprite.scale:0.5:x|y')>=0,
   'digit scale animates toward the source final value');

  // `showCombo` is public in the donor but is not read by this popup; the
  // source actually gates its number group using showRatingNum.
  presentation.showCombo=false;
  presentation.popUpScore('good', 8, note);
  check(group.members.length==4 && group.members[0]==first,
   'later combo recycles the existing digit pool');
  check(group.members[0].graphicPath=='owner/combo/num0', 'recycled digits reload current combo graphic');
  for (i in 0...group.members.length)
   check(group.members[i].alive == (i < 3), 'only digits used by the latest popup remain alive');

  paths.calls.resize(0);
  presentation.showRating=false;
  presentation.showRatingNum=false;
  presentation.popUpScore('bad', 99, note);
  check(paths.calls.length==0, 'disabled rating and number layers do not load popup images');
  check(callbackLog.length==6 && callbackLog[4]=='onPopUpScore'
   && callbackLog[5]=='onPopUpScorePost', 'hidden components still receive source callbacks');
  hidden=true;
  presentation.popUpScore('bad', 99, note);
  check(callbackLog.length==6, 'hideHud returns before source callbacks');

  // Legacy PlayState writes before HUD creation survive attachment and use
  // this existing renderer. Modern HUD defaults survive an untouched owner.
  hidden=false;
  var legacy = new NightmareVisionLegacyHudControls();
  legacy.showRating=false; legacy.showCombo=false;
  legacy.bind(presentation);
  paths.calls.resize(0);
  presentation.popUpScore('bad', 99, note);
  check(paths.calls.length==0 && !presentation.showRatingNum,
   'legacy switches suppress ratings and combo digits through the real renderer');
  legacy.showCombo=true;
  paths.calls.resize(0);
  presentation.popUpScore('bad', 12, note);
  check(paths.calls.length==3 && paths.calls[0]=='owner/combo/num0',
   'legacy combo restores digits independently of rating');
  legacy.showRating=true; legacy.showCombo=false;
  paths.calls.resize(0);
  presentation.popUpScore('bad', 12, note);
  check(paths.calls.join(',')=='owner/ratings/bad',
   'legacy rating restores independently of combo');
  var untouched = new NightmareVisionLegacyHudControls();
  var other:Dynamic={showRating:false,showCombo:false,showRatingNum:false};
  untouched.bind(other);
  check(!other.showRating && !other.showRatingNum && untouched.showRating,
   'untouched legacy defaults do not override HUD preferences or inherit another owner');
  legacy.release();
  var rejected=false; try legacy.showCombo=true catch (_:Dynamic) rejected=true;
  check(rejected && !presentation.showRatingNum, 'released controls cannot mutate old HUD');
  untouched.release();

  // Release builds with flat engine assets expose one prefix for both types.
  // Pixel suffixes and subsequent script mutations must affect digits too.
  paths.usesSharedRatingPrefix=true;
  presentation.ratingPrefix='pixelUI/';
  presentation.ratingSuffix='-pixel';
  paths.calls.resize(0);
  presentation.cachePopUpScore();
  check(paths.calls[0]=='pixelUI/sick-pixel' && paths.calls[5]=='pixelUI/num0-pixel',
   'legacy shared prefix and suffix resolve exact selected-owner assets');
  presentation.ratingPrefix='UI/game/ratings/';
  presentation.ratingSuffix='';
  check(presentation.comboPrefix=='UI/game/ratings/', 'legacy digit prefix tracks live rating prefix');
  presentation.comboPrefix='explicit/digits/';
  presentation.ratingPrefix='another/ratings/';
  check(presentation.comboPrefix=='explicit/digits/', 'explicit split prefix overrides legacy link');
  paths.calls.resize(0);
  presentation.cachePopUpScore();
  check(paths.calls[5]=='explicit/digits/num0', 'explicit combo path does not silently fall back');
  presentation.release();
  var released=false;
  try presentation.cachePopUpScore() catch (_:Dynamic) released=true;
  check(released && presentation.ratingGraphic==null && presentation.ratingNumGroup==null,
   'release severs references without destroying PlayState-owned display objects');
 }
}
''',
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            for name, source in files.items():
                if source is None:
                    continue
                target = work / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(source, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_visibility_callbacks_and_release_are_explicit(self):
        source = (ROOT / "source/NightmareVisionRatingPresentation.hx").read_text()
        self.assertIn("if (hideHud()) return;", source)
        self.assertIn("callScript('onPopUpScore', [note, scriptRating, ratingGraphic, ratingNumGroup]);", source)
        self.assertIn("callScript('onPopUpScorePost', [note, scriptRating, ratingGraphic, ratingNumGroup]);", source)
        self.assertIn("public function release():Void", source)
        self.assertIn("ratingGraphic = null;", source)
        self.assertIn("ratingNumGroup = null;", source)
        self.assertNotIn("extends PsychRatingPresentation", source)
        self.assertIn("PsychRatingPresentationCommon.positionRating", source)
        self.assertIn("PsychRatingPresentationCommon.positionComboDigit", source)
        self.assertIn("paths.image(", source)


if __name__ == "__main__":
    unittest.main()
