"""Exercise the production Codename judgement presenter with render boundary stubs."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameNotePresentationTest(unittest.TestCase):
    def test_positions_scoped_assets_and_tween_lifetime(self):
        stubs = {
            'flixel/FlxG.hx': '''package flixel;
class FlxG { public static var random=new FakeRandom(); }
class FakeRandom { public function new() {} public function int(a:Int,b:Int):Int return a;
 public function float(a:Float,b:Float):Float return a; }''',
            'flixel/FlxSprite.hx': '''package flixel;
class FlxSprite {
 public var x:Float=0; public var y:Float=0; public var alpha:Float=1; public var angle:Float=0;
 public var exists:Bool=true; public var frames:Dynamic; public var antialiasing:Bool=false;
 public var scale=new Point(); public var velocity=new Point(); public var acceleration=new Point();
 public function new() {} public function revive():Void exists=true; public function kill():Void exists=false;
 public function updateHitbox():Void {} public function setPosition(x:Float,y:Float):Void {this.x=x;this.y=y;}
}
class Point { public var x:Float=0; public var y:Float=0; public function new() {}
 public function set(x:Float=0,y:Float=0):Void {this.x=x;this.y=y;} }''',
            'flixel/group/FlxSpriteGroup.hx': '''package flixel.group;
import flixel.FlxSprite;
class FlxSpriteGroup {
 public var x:Float; public var y:Float; public var maxSize:Int; public var members:Array<FlxSprite>=[];
 public var length(get,never):Int; function get_length():Int return members.length;
 public function new(x:Float,y:Float,maxSize:Int) {this.x=x;this.y=y;this.maxSize=maxSize;}
 public function add(sprite:FlxSprite):FlxSprite {sprite.x+=x;sprite.y+=y;members.push(sprite);return sprite;}
 public function recycle(objectClass:Class<FlxSprite>):FlxSprite {
  for (sprite in members) if (!sprite.exists) {sprite.revive();return sprite;}
  var sprite=Type.createInstance(objectClass,[]);add(sprite);return sprite;
 }
 public function destroy():Void {members=[];}
}''',
            'flixel/tweens/FlxTween.hx': '''package flixel.tweens;
import flixel.FlxSprite;
class FlxTween {
 public static var all:Array<FlxTween>=[];
 public var active:Bool=true; public var cancelled:Bool=false; public var item:FlxSprite;
 public var onComplete:FlxTween->Void;
 public function new(item:FlxSprite) this.item=item;
 public static function tween(item:FlxSprite,props:Dynamic,duration:Float,options:Dynamic):FlxTween {
  var result=new FlxTween(item);result.onComplete=Reflect.field(options,'onComplete');all.push(result);return result;
 }
 public function cancel():Void {cancelled=true;active=false;}
 public function complete():Void {onComplete(this);}
}''',
            'flixel/graphics/frames/FlxFramesCollection.hx': '''package flixel.graphics.frames;
class FlxFramesCollection { public var key:String; public function new(key:String) this.key=key; }''',
            'flixel/graphics/frames/FlxImageFrame.hx': '''package flixel.graphics.frames;
class FlxImageFrame { public static function fromImage(image:Dynamic):FlxFramesCollection
 return new FlxFramesCollection(Std.string(image)); }''',
            'CodenamePaths.hx': '''class CodenamePaths {
 public function new(root:String) {} public function getFrames(key:String):flixel.graphics.frames.FlxFramesCollection {
  if(key.indexOf('custom/')==0) throw 'missing scoped';
  if(key.indexOf('game/score/')==0) throw 'missing default';
  return new flixel.graphics.frames.FlxFramesCollection(key);
 }
}''',
            'FNFAssets.hx': '''class FNFAssets {
 public static function exists(path:String):Bool return path=='assets/images/sick.png'
  || path=='assets/images/combo.png' || path.indexOf('assets/images/num')==0;
 public static function getBitmapData(path:String):Dynamic return path;
}''',
            'CodenameNoteHitEvent.hx': '''class CodenameNoteHitEvent {
 public var ratingPrefix:String='game/score/'; public var ratingSuffix:String='';
 public var ratingScale:Float=0.7; public var ratingAntialiasing:Bool=true;
 public var numScale:Float=0.5; public var numAntialiasing:Bool=true;
 public var displayCombo:Bool=true; public var displayRating:Bool=true; public var rating:String='sick';
 public function new() {}
}''',
            'Main.hx': '''import flixel.tweens.FlxTween;
class Main {
 static function check(ok:Bool,label:String):Void if(!ok) throw label;
 static function main():Void {
  var group=new CodenameNotePresentation('owned',500,300);
  var event=new CodenameNoteHitEvent();
  group.display(event,12,500,0);
  check(group.members.length==5,'combo plus three digits plus rating');
  check(group.members[0].x==500&&group.members[0].y==300,'group combo position');
  check(group.members[1].x==410&&group.members[1].y==380,'group digit position');
  check(group.members[4].x==460&&group.members[4].y==240,'group rating position');
  check(group.members[4].frames.key=='assets/images/sick.png','default graphic fallback');
  group.setPaused(true);
  for(tween in FlxTween.all) check(!tween.active,'pause active fade');
  var reused=group.members[0]; var old=FlxTween.all[0];reused.kill();
  event.displayRating=false;group.display(event,0,500,0);
  check(group.members[0]==reused&&old.cancelled,'recycle cancels old fade');
  old.complete();
  check(reused.exists,'old completion must not kill reused sprite');
  check(!FlxTween.all[FlxTween.all.length-1].active,'new fade paused');
  group.setPaused(false);
  check(!old.active&&FlxTween.all[FlxTween.all.length-1].active,'resume current fades only');
  var count=group.members.length;
  event.ratingPrefix='custom/';event.displayCombo=false;event.displayRating=true;
  group.display(event,7,500,0);
  check(group.members.length==count,'missing scoped asset borrowed no artwork');
  var current=FlxTween.all[FlxTween.all.length-1];
  current.complete();
  check(!current.item.exists,'current completion kills its sprite');
  group.destroy();
  for(tween in FlxTween.all) check(tween.cancelled||tween==current,
   'destroy cancels owned fades');
  Sys.println('presentation ok');
 }
}''',
        }
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            root = Path(directory)
            for name, body in stubs.items():
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(body, newline='\n')
            (root / 'CodenameNotePresentation.hx').write_text(
                (ROOT / 'source/CodenameNotePresentation.hx').read_text(), newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(root),
                                     '-main', 'Main', '--interp'], cwd=ROOT,
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('presentation ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
