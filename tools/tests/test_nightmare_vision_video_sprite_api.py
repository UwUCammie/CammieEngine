"""The owner video sprite carries the full source FunkinVideoSprite surface over a fake decoder."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND
from menu_async_fixture_support import install_menu_async_contracts

ROOT = Path(__file__).resolve().parents[2]

FILES = {
    'Event.hx': """class Event {
 public var handlers:Array<{f:Dynamic,once:Bool,priority:Int}>=[]; public function new(){}
 public function has(f:Dynamic):Bool {for(h in handlers)if(Reflect.compareMethods(h.f,f))return true;return false;}
 public function add(f:Dynamic,once:Bool=false,priority:Int=0):Void {
  var i=handlers.length; while(i>0&&handlers[i-1].priority<priority)i--; handlers.insert(i,{f:f,once:once,priority:priority});
 }
 public function remove(f:Dynamic):Void {handlers=handlers.filter(function(h)return !Reflect.compareMethods(h.f,f));}
 public function dispatch(?arg:Dynamic):Void {
  for(h in handlers.copy()){if(h.once)handlers.remove(h);Reflect.callMethod(null,h.f,arg==null?[]:[arg]);}
 }
}""",
    'flixel/FlxG.hx': """package flixel; class FlxG {
 public static var autoPause=true; public static var width=1280; public static var height=720;
 public static var signals={focusGained:new Event(),focusLost:new Event()};
}""",
    'flixel/util/FlxTimer.hx': """package flixel.util; class FlxTimer {
 public static var lastDelay:Float=-1; public static var pending:Array<Void->Void>=[];
 public function new(){}
 public function start(t:Float,f:FlxTimer->Void):FlxTimer {lastDelay=t;var self=this;pending.push(function()f(self));return this;}
 public function cancel():Void {}
}""",
    'hxvlc/openfl/Location.hx': 'package hxvlc.openfl; typedef Location=Dynamic;',
    'hxvlc/flixel/FlxInternalVideo.hx': """package hxvlc.flixel;
 class FlxInternalVideo {
 public var onEndReached=new Event();public var onOpening=new Event();public var onFormatSetup=new Event();
 public var onPaused=new Event();public var onStopped=new Event();public var onEncounteredError=new Event();
 public var isPlaying=false;public var rate:Float=1;public var volumeAdjust:Float=1;
 public var length:haxe.Int64=0;public var time:haxe.Int64=0;
 public function new(){}
 public function load(p:String,o:Array<String>):Bool return true;
 public function play():Bool {isPlaying=true;onOpening.dispatch();return true;}
 public function pause():Void {isPlaying=false;onPaused.dispatch();}public function resume():Void isPlaying=true;
 public function stop():Void {isPlaying=false;onStopped.dispatch();}
 public function dispose():Void {}
 }
""",
    'hxvlc/flixel/FlxVideoSprite.hx': """package hxvlc.flixel; import hxvlc.openfl.Location;
 class FlxVideoSprite {
 public var bitmap:FlxInternalVideo;public var x:Float;public var y:Float;public var exists=true;public var alive=true;
 public var fitted:String='';
 public function new(?instance:Dynamic,x:Float=0,y:Float=0){this.x=x;this.y=y;bitmap=new FlxInternalVideo();}
 public function load(path:Location,?options:Array<String>):Bool return bitmap.load(path,options);
 public function play():Bool return bitmap!=null&&bitmap.play();
 public function pause():Void {if(bitmap!=null)bitmap.pause();}public function resume():Void {if(bitmap!=null)bitmap.resume();}
 public function setGraphicSize(w:Float=0,h:Float=0):Void fitted+='size:'+w+'x'+h+';';
 public function updateHitbox():Void fitted+='hitbox;';
 public function screenCenter():Void fitted+='center;';
 public function destroy():Void {exists=false;bitmap=null;}
 }
""",
    'NightmareVisionSpriteMethods.hx': 'class NightmareVisionSpriteMethods {public static function bind(a:Dynamic,b:Dynamic):Void{}}',
    'NightmareVisionSpriteRegistry.hx': 'class NightmareVisionSpriteRegistry {public static function peek(a:Dynamic):Dynamic return null;}',
}

MAIN = r"""class Main {
 static function check(v:Bool,s:String):Void {if(!v)throw s;}
 static function paths(root:String):Dynamic return {root:root,
  scopeAssetPath:function(p:String):Dynamic return StringTools.startsWith(p,root+'/')?p:null,
  exists:function(p:String):Bool return sys.FileSystem.exists(p),
  video:function(p:String):String return root+'/'+p+'.mp4'};
 static function main():Void {
  var state={members:[]};
  var v=new NightmareVisionVideoSprite(state,paths('owner-a'),0,0,false);
  var log:Array<String>=[];
  v.onStart(function()log.push('start'));
  v.onPause(function()log.push('pause'),true);
  v.onStop(function()log.push('stop'));
  v.onError(function(message:String)log.push('error:'+message));
  v.onEnd(function()log.push('end-low'),false,-5);
  v.onEnd(function()log.push('end-high'),false,10);
  v.onEnd(function()log.push('end-once'),true);
  v.onFormat(function()log.push('format-once'),true);
  check(v.load('clip'),'owner clip loads');
  v.delayAndStart(0.5);
  check(flixel.util.FlxTimer.lastDelay==0.5,'delayAndStart honours an explicit delay');
  v.delayAndStart();
  for(run in flixel.util.FlxTimer.pending.copy())run();
  check(log[0]=='start' && v.isPlaying,'onStart fires when playback opens');
  v.pause();v.pause();
  check(log.filter(function(e)return e=='pause').length==1,'a once pause listener fires a single time');
  v.bitmap.onEncounteredError.dispatch('bad frame');
  check(log.indexOf('error:bad frame')>=0,'onError receives the decoder message');
  v.bitmap.onFormatSetup.dispatch();
  check(log.indexOf('format-once')>=0,'onFormat accepts the source once argument');
  v.bitmap.length=haxe.Int64.ofInt(2000);v.bitmap.time=haxe.Int64.ofInt(500);
  check(v.duration==2000 && v.currentTime==500 && v.progress==0.25,'time, duration and progress read the decoder');
  v.seekToProgress(0.75);
  check(haxe.Int64.toInt(v.bitmap.time)==1500,'seekToProgress maps onto the clip length');
  v.seekToProgress(4);
  check(haxe.Int64.toInt(v.bitmap.time)==2000,'seekToProgress clamps past the end');
  v.seekTo(-10);
  check(haxe.Int64.toInt(v.bitmap.time)==0,'seekTo never goes negative');
  v.volume=1.5;
  check(v.volume==1 && v.bitmap.volumeAdjust==1,'volume clamps to 1');
  v.volume=0.3;
  check(v.bitmap.volumeAdjust==0.3,'volume drives the per-video volume adjustment');
  v.volume=-2;
  check(v.volume==0,'volume clamps to 0');
  v.playbackRate=1.5;
  check(v.bitmap.rate==1.5,'playbackRate drives the decoder rate');
  v.fitToScreen();
  check(v.fitted=='size:1280x720;hitbox;center;','fitToScreen scales to the window and centres');
  v.bitmap.onEndReached.dispatch();
  var ends=log.filter(function(e)return StringTools.startsWith(e,'end-'));
  check(ends.join(',')=='end-high,end-once,end-low','end callbacks run by priority, then registration order');
  var late:Array<String>=[];
  v.onEnd(function()late.push('late'),true);
  check(late.length==1,'a late end listener still hears a finished clip');
  check(@:privateAccess v.endCallbacks.length==2,'once listeners are dropped after firing');
  var other=new NightmareVisionVideoSprite(state,paths('owner-b'),0,0,false);
  check(NightmareVisionVideoSprite.instancesFor('owner-a').length==1
   && NightmareVisionVideoSprite.instancesFor('owner-a')[0]==v,'instances are narrowed to one owner');
  var seen=0;
  other.alive=false;
  NightmareVisionVideoSprite.forEachAlive(function(video)seen++, 'owner-b');
  check(seen==0,'forEachAlive skips dead clips');
  NightmareVisionVideoSprite.forEach(function(video)seen++, 'owner-b');
  check(seen==1,'forEach visits every clip of the owner');
  v.destroy();
  check(v.progress==0 && v.duration==-1 && !v.isPlaying,'a destroyed clip reports no playback');
  check(NightmareVisionVideoSprite.instancesFor('owner-a').length==0,'destroyed clips leave the instance list');
  other.destroy();
  check(SourceVideoPlayback.progress(5,0)==0 && SourceVideoPlayback.seekTime(0.5,0)==-1,
   'an unknown length gives no progress and no seek');
  check(SourceVideoPlayback.clampVolume(Math.NaN)==0 && SourceVideoPlayback.safeRate(0)==1,
   'bad volume and rate values are made safe');
  check(SourceVideoPlayback.hostRate(1.5)==1.5 && SourceVideoPlayback.hostRate('0.75')==0.75,
   'a host playbackRate number or numeric text is followed');
  check(Math.isNaN(SourceVideoPlayback.hostRate(null)) && Math.isNaN(SourceVideoPlayback.hostRate(0))
   && Math.isNaN(SourceVideoPlayback.hostRate(-2)) && Math.isNaN(SourceVideoPlayback.hostRate('fast'))
   && Math.isNaN(SourceVideoPlayback.hostRate(Math.POSITIVE_INFINITY)),
   'an unusable host rate leaves the decoder rate alone instead of forcing 1');
 }
}"""


class NightmareVisionVideoSpriteApiTest(unittest.TestCase):
    def test_source_video_members_over_the_decoder(self):
        files = dict(FILES)
        files['SourceVideoPlayback.hx'] = (ROOT / 'source/SourceVideoPlayback.hx').read_text()
        source = (ROOT / 'source/NightmareVisionVideoSprite.hx').read_text()
        files['NightmareVisionVideoSprite.hx'] = source.replace('#if cpp', '#if true').replace(
            '@:build(NightmareVisionSpriteMacro.build())', '')
        files['Main.hx'] = MAIN
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as d:
            base = Path(d)
            for name, content in files.items():
                target = base / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
            for owner in ['owner-a', 'owner-b']:
                (base / owner).mkdir()
                (base / owner / 'clip.mp4').write_bytes(b'fixture')
            install_menu_async_contracts(base, native_flixel=False)
            result = subprocess.run([*HAXE_COMMAND, '-cp', d, '--main', 'Main', '--interp'],
                                    cwd=base, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_decoder_free_build_has_the_same_members(self):
        source = (ROOT / 'source/NightmareVisionVideoSprite.hx').read_text()
        decoder, stub = source.split('#else', 1)
        for member in ('playbackRate', 'volume', 'isPlaying', 'progress', 'currentTime', 'duration',
                       'function onStart(', 'function onPause(', 'function onStop(', 'function onError(',
                       'function onEnd(callback:Dynamic, once:Bool = false, priority:Int = 0)',
                       'function seekTo(', 'function seekToProgress(', 'function fitToScreen(',
                       'function delayAndStart(delay:Float = 0)', 'static function instancesFor(',
                       'static function forEach(', 'static function forEachAlive('):
            self.assertIn(member, decoder, member)
            self.assertIn(member, stub, member)

    def test_hxc_video_follows_its_host_rate_through_the_shared_rule(self):
        source = (ROOT / 'source/HxcOwnedVideoSprite.hx').read_text()
        self.assertIn("SourceVideoPlayback.hostRate(Reflect.getProperty(ownerState, 'playbackRate'))", source)
        self.assertNotIn('Std.parseFloat', source)


if __name__ == '__main__':
    unittest.main()
