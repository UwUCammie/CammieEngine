"""Psych graphics and color tweens use the native disk/color boundaries."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

from test_psych_animation_indices import extract_method

ROOT = Path(__file__).resolve().parents[2]


class PsychRenderPrimitivesTest(unittest.TestCase):
    def test_post_update_runs_after_native_hud_and_note_updates(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        start = source.index("override public function update(elapsed:Float)")
        end = source.index("function runtimeSmokePlayerHits", start)
        update = source[start:end]
        post = "callAllHScript('updatePost', [elapsed]);"
        self.assertEqual(update.count(post), 2)
        self.assertGreater(update.rindex(post), update.rindex("iconP1.x ="))
        self.assertGreater(update.rindex(post), update.index("runtimeSmokePlayerHits();"))
        self.assertGreater(update.index(post), update.index("super.update(elapsed);"))

    def test_disk_graphics_and_color_tween_dispatch(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        methods = "\n".join(extract_method(source, marker) for marker in [
            "function compatMakeLuaSprite(", "function compatLoadGraphic(",
            "function compatTweenObject(", "function compatCancelTween(",
            "function compatDoTween(",
            "function compatParseColor(",
        ])
        fixture = r'''
abstract FlxColor(Int) from Int to Int {
 public var alphaFloat(never,set):Float;
 inline function set_alphaFloat(value:Float):Float {
  this = (this & 0xFFFFFF) | (Std.int(value * 255) << 24); return value;
 }
 public static function fromString(value:String):Null<Int> return Std.parseInt(value);
 public static function interpolate(a:FlxColor,b:FlxColor,t:Float):FlxColor {
  var av:Int = a; var bv:Int = b;
  var r = Std.int(((av >> 16) & 255) + (((bv >> 16) & 255) - ((av >> 16) & 255)) * t);
  var g = Std.int(((av >> 8) & 255) + (((bv >> 8) & 255) - ((av >> 8) & 255)) * t);
  var blue = Std.int((av & 255) + ((bv & 255) - (av & 255)) * t);
  return cast (0xFF000000 | (r << 16) | (g << 8) | blue);
 }
}
class Bitmap { public var path:String; public function new(path:String) { this.path = path; } }
class FNFAssets {
 public static function exists(path:String):Bool return path == 'assets/images/imported.png' || path == 'runtime/second.png';
 public static function getBitmapData(path:String):Bitmap return new Bitmap(path);
}
class FlxPoint {
 public var x:Float; public var y:Float;
 public function new(x:Float,y:Float) { this.x=x; this.y=y; }
}
class FlxSprite {
 public var color:Int = 0xFF00FF00; public var alpha:Float = 0.5;
 public var x:Float = 0; public var y:Float = 0;
 public var scale:FlxPoint = new FlxPoint(10,10);
 public var image:Bitmap;
 public function new(x:Float = 0, y:Float = 0) {}
 public function loadGraphic(value:Dynamic):FlxSprite {
  if (!Std.isOfType(value, Bitmap)) throw 'unregistered disk path passed to asset manifest';
  image = cast value; return this;
 }
}
class FlxCamera {
 public var color:FlxColor = cast 0xFFFFFFFF;
 public var alpha:Float = 1;
 public function new() {}
}
class FlxEase { public static function linear(t:Float):Float return t; }
class FlxTween {
 public var route:String; public var start:Int; public var end:Int;
 public var sprite:FlxSprite;
 public var owner:Dynamic; public var props:Dynamic;
 public var options:Dynamic; public var cancelled:Bool = false;
 public var sample:Float->Void;
 public function new(route:String, options:Dynamic) { this.route = route; this.options = options; }
 public function cancel():Void { cancelled = true; }
 public static function tween(owner:Dynamic, props:Dynamic, time:Float, options:Dynamic):FlxTween {
  if (Reflect.hasField(props,'color') && (Std.isOfType(owner,FlxSprite) || Std.isOfType(owner,FlxCamera))) throw 'scalar RGB interpolation';
  var result = new FlxTween('scalar', options);
  result.owner = owner; result.props = props;
  var field = Reflect.fields(props)[0];
  var first:Dynamic = Reflect.getProperty(owner, field);
  var last:Dynamic = Reflect.field(props, field);
  result.sample = function(progress:Float) Reflect.setProperty(owner, field, first + (last - first) * progress);
  return result;
 }
 public static function color(sprite:FlxSprite, time:Float, from:FlxColor, to:FlxColor, options:Dynamic):FlxTween {
  var result = new FlxTween('channels', options); result.start = from; result.end = to;
  result.sprite = sprite;
  result.sample = function(progress:Float) {
   if (sprite != null) sprite.color = FlxColor.interpolate(from, to, progress);
  };
  return result;
 }
}
class RenderFixture {
 var haxeSprites:Map<String,FlxSprite> = [];
 var haxeSpriteAtlasNames:Map<String,Array<String>> = [];
 var compatTweens:Map<String,FlxTween> = [];
 var completed:Array<String> = [];
 var model:Dynamic = {point:{x:3.0,y:7.0}};
 function new() {}
 function compatForgetSpriteAtlas(sprite:Dynamic):Void {}
 function compatFindObject(name:Dynamic):Dynamic return haxeSprites.get(Std.string(name));
 function compatGetProperty(name:Dynamic):Dynamic {
  var path = Std.string(name).split('.');
  var value:Dynamic = path.shift() == 'model' ? model : null;
  if (value == null) {
   var first = Std.string(name).split('.')[0];
   value = haxeSprites.get(first);
  }
  for (part in path) {
   if (value == null) return null;
   value = Reflect.getProperty(value, part);
  }
  return value;
 }
 function compatReadPath(target:Dynamic, path:String):Dynamic return Reflect.field(target,path);
 function callAllHScript(name:String, args:Array<Dynamic>):Void completed.push(args[0]);
''' + methods + r'''
 static function main() {
  var state = new RenderFixture();
  var sprite = state.compatMakeLuaSprite('sprite','imported',10,20);
  if (sprite.image == null || sprite.image.path != 'assets/images/imported.png')
   throw 'disk sprite did not decode';
  state.compatLoadGraphic('sprite','runtime/second.png');
  if (sprite.image.path != 'runtime/second.png') throw 'replacement disk graphic did not decode';
  state.compatTweenObject('effect',sprite,'color','FF0000',0.5,'linear');
  var color = state.compatTweens.get('effect');
  if (color == null || color.route != 'channels' || color.end != 0xFFFF0000
   || color.start != 0x7F00FF00) throw 'color channels/current alpha not preserved';
  var camera = new FlxCamera();
  state.compatTweenObject('camera',camera,'color','990000',4,'linear');
  var cameraTween = state.compatTweens.get('camera');
  if(cameraTween == null || cameraTween.route != 'channels' || cameraTween.sprite != null)
   throw 'camera colour must use Psych null-sprite ColorTween';
  cameraTween.sample(0.5);
  if(camera.color != 0xFFFFFFFF) throw 'camera-wide tint changed at midpoint';
  cameraTween.sample(1);
  if(camera.color != 0xFFFFFFFF) throw 'camera-wide tint changed at completion';
  cameraTween.options.onComplete(cameraTween);
  if (state.compatTweens.exists('camera') || state.completed.join(',') != 'camera')
   throw 'null-sprite tween did not complete and release its tag';
  state.compatTweenObject('effect',sprite,'alpha',0,0.2,'linear');
  if (!color.cancelled || state.compatTweens.get('effect').route != 'scalar')
   throw 'replacement tween ownership failed';
  var alpha = state.compatTweens.get('effect'); alpha.options.onComplete(alpha);
  if (state.compatTweens.exists('effect') || state.completed.join(',') != 'camera,effect')
   throw 'completion cleanup/callback failed';
  state.compatDoTween('sx','sprite.scale','x',0.67,8,'linear');
  var sx = state.compatTweens.get('sx');
  if (sx == null || sx.owner != sprite.scale || Reflect.field(sx.props,'x') != 0.67)
   throw 'nested sprite scale.x did not own a tween';
  sx.sample(1);
  if (Math.abs(sprite.scale.x - 0.67) > 0.0001) throw 'nested x did not reach target';
  state.compatDoTween('sy','sprite.scale','y',0.67,7,'linear');
  var sy = state.compatTweens.get('sy'); sy.sample(1);
  if (sy.owner != sprite.scale || Math.abs(sprite.scale.y - 0.67) > 0.0001)
   throw 'nested y did not reach target';
  state.compatDoTween('direct','sprite','x',20,1,'linear');
  var direct = state.compatTweens.get('direct'); direct.sample(1);
  if (direct.owner != sprite || sprite.x != 20) throw 'direct tag tween changed';
  state.compatDoTween('plain','model.point','y',11,1,'linear');
  var plain = state.compatTweens.get('plain'); plain.sample(1);
  if (plain.owner != state.model.point || state.model.point.y != 11)
   throw 'nested plain object tween did not resolve';
  state.compatDoTween('invalid','model.missing','x',1,1,'linear');
  if (state.compatTweens.exists('invalid')) throw 'invalid path created a tween';
 }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "RenderFixture.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder,
                 "-main", "RenderFixture", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
