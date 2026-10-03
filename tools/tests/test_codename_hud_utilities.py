"""Codename HUD helpers retain source rounding and elapsed-based icon decay."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameHudUtilitiesTest(unittest.TestCase):
    def test_source_utility_values_at_60_240_and_480_fps(self):
        source = (ROOT / 'source/CodenameModBindings.hx').read_text()
        start = source.index('\tpublic static function coolUtil(')
        depth = 0
        for index in range(source.index('{', start), len(source)):
            depth += (source[index] == '{') - (source[index] == '}')
            if depth == 0:
                method = source[start:index + 1]
                break
        else:
            self.fail('coolUtil method is unterminated')
        fixture = '''import CodenameOpenURLCompat;
class Audio {
 public var playing:Bool=false; public var persist:Bool=false;
 public function new() {}
 public function fadeIn(_seconds:Float,_from:Float,_to:Float):Void {}
}
class SoundFront {
 public var music:Audio=null; public var looped:Bool=false;
 public var lastSfx:String=null; public var lastVolume:Float=-1;
 public function new() {}
 public function play(asset:String, volume:Float):Audio {
  lastSfx=asset; lastVolume=volume; return new Audio();
 }
 public function playMusic(_asset:Dynamic,_volume:Float,looped:Bool):Void {
  this.looped=looped; music=new Audio(); music.playing=true;
 }
}
class Conductor {
 public static var bpm:Float=0; public static var songPosition:Float=123;
 public static var lastSongPos:Float=122; public static var bpmChangeMap:Array<Int>=[1];
 public static function changeBPM(value:Float):Void bpm=value;
}
class FlxG {
 public static var elapsed:Float=1/60;
 public static var sound=new SoundFront();
 public static var lastOpenedURL:String=null;
 public static function openURL(url:String):Void lastOpenedURL=url;
}
class FlxFramesCollection {
 public var frames:Array<Int>;
 public function new(count:Int) frames=[for (i in 0...count) i];
}
class Animation {
 public var added:String=null; public var played:String=null;
 public function new() {}
 public function add(name:String,frames:Array<Int>,fps:Float,looped:Bool):Void added=name;
 public function play(name:String):Void played=name;
}
class FlxSprite {
 public static var defaultAntialiasing:Bool=false;
 public var frames:FlxFramesCollection;
 public var animation=new Animation();
 public var alpha:Float=1; public var visible:Bool=true; public var active:Bool=true;
 public var antialiasing:Bool=false;
 public var velocity=new Point(); public var acceleration=new Point(); public var drag=new Point();
 public function new() {}
 public function reset(_x:Float,_y:Float):Void {}
 public function loadGraphic(graphic:Dynamic):FlxSprite {
  frames=new FlxFramesCollection(1); return this;
 }
}
class Point { public function new() {} public function set():Void {} }
class FlxTween { public static function cancelTweensOf(_value:Dynamic):Void {} }
class CodenamePaths {
 public function new() {}
 public function sound(name:String):String return 'owner/sounds/'+name+'.ogg';
 public function getFrames(name:String):FlxFramesCollection return new FlxFramesCollection(3);
 public function music(name:String):String return name;
 public function getPath(name:String):String return name;
}
class FNFAssets { public static function getSound(path:String):Dynamic return path; }
class CodenameKeyCodeCompat {
 public static function keyToString(key:Dynamic):String return Std.string(key);
}
class Main {
''' + method + '''
 static function near(a:Float,b:Float):Bool return Math.abs(a-b)<0.000001;
 static function main():Void {
  var util=Main.coolUtil(new CodenamePaths());
  if (!util.openURL('https://youtube.com/@A2music')
   || FlxG.lastOpenedURL!='https://youtube.com/@A2music')
   throw 'source CoolUtil.openURL did not dispatch a validated URL';
  if (util.openURL('javascript:alert(1)')
   || FlxG.lastOpenedURL!='https://youtube.com/@A2music')
   throw 'source CoolUtil.openURL accepted an unsafe URL';
  var animated=new FlxSprite();
  Reflect.callMethod(util,Reflect.field(util,'loadAnimatedGraphic'),
   [animated,'game/stickers/simple/greenfriend']);
  if (animated.frames.frames.length!=3 || animated.animation.added!='idle'
   || animated.animation.played!='idle') throw 'source animated graphic load';
  var keys=['menu/scroll','menu/confirm','menu/cancel',
   'editors/checkboxChecked','editors/checkboxUnchecked','editors/warningMenu'];
  for (id in 0...keys.length) {
   util.playMenuSFX(id,0.35);
   if (FlxG.sound.lastSfx!='owner/sounds/'+keys[id]+'.ogg'
    || !near(FlxG.sound.lastVolume,0.35)) throw 'source menu sound '+id;
  }
  Reflect.callMethod(util, Reflect.field(util,'playMenuSFX'), []);
  if (FlxG.sound.lastSfx!='owner/sounds/menu/scroll.ogg')
   throw 'default menu sound';
  if (!near(util.quantize(98.765,100),98.77)) throw 'source quantize';
  if (util.addZeros('7',3)!='007') throw 'source zero padding';
  var recycled=new FlxSprite(); recycled.alpha=0; recycled.visible=false;
  util.resetSprite(recycled,10,20);
  if (recycled.alpha!=1 || !recycled.visible || !recycled.active)
   throw 'source sprite reset';
  for (fps in [60,240,480]) {
   FlxG.elapsed=1/fps;
   var value:Float=1;
   for (step in 0...fps) value=util.fpsLerp(value,0,0.165);
   if (!near(value,Math.pow(1-0.165,60))) throw 'fps lerp '+fps+': '+value;
  }
  util.playMusic('owner/music/menu.ogg', false, 1, false, 100);
  if (FlxG.sound.looped || FlxG.sound.music.persist || Conductor.bpm!=100
      || Conductor.songPosition!=0 || Conductor.lastSongPos!=0
      || Conductor.bpmChangeMap.length!=0)
   throw 'source music argument order';
  FlxG.sound.music=null;
  Conductor.songPosition=40;
  util.playMenuSong(true);
  if (!FlxG.sound.looped || !FlxG.sound.music.persist || Conductor.bpm!=102
      || Conductor.songPosition!=0)
   throw 'source menu music semantics';
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            (Path(directory) / 'Main.hx').write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                 '-cp', directory, '--run', 'Main'],
                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
