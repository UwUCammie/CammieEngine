"""Execute the extracted native Nightmare Vision splash state with fake Flixel services."""
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionSplashStateTest(unittest.TestCase):
    def test_source_splash_assets_timing_cleanup_and_late_start_meta_binding(self):
        source = (ROOT / "source/NightmareVisionSplashState.hx").read_text(encoding="utf-8")
        body = source[source.index("typedef NightmareVisionSplashStateHost"):]
        self.assertIn("#if cpp", body)
        self.assertNotIn("VIDEOS_ALLOWED", body)
        self.assertIn("host.paths.video('intro')", body)
        self.assertIn("if (video.bitmap != null)", body)
        self.assertIn("new NightmareVisionVideoSprite(this, host.paths)", body)
        self.assertIn("video.onFormat(function()", body)
        self.assertIn("video.onEnd(finish)", body)
        self.assertIn("video.delayAndStart()", body)
        self.assertIn("if (!completed && video != null) video.delayAndStart();", body)
        self.assertIn("NightmareVisionVideoSprite.muted", body)
        self.assertIn("if (video != null)", body)
        self.assertIn("video.stop();", body)
        self.assertIn("if (video.load(videoPath, sourceVideoMuted()", body)
        self.assertIn("cleanupResources();", body)
        self.assertIn("tween.cancel()", body)
        self.assertIn("FlxG.sound.play(host.paths.sound('intro'))", body)
        self.assertIn("FlxEase.elasticOut", body)
        self.assertIn("FlxEase.quadIn", body)

        fixture = r'''
class Scale {
 public var x:Float=1;
 public var y:Float=1;
 public function new() {}
 public function set(x:Float,y:Float):Void {this.x=x;this.y=y;}
}
class FlxState {
 public var members:Array<Dynamic>=[];
 public var destroyed:Bool=false;
 public function new() {}
 public function create():Void {}
 public function update(elapsed:Float):Void {}
 public function add<T>(value:T):T {members.push(value);return value;}
 public function destroy():Void {destroyed=true;}
}
class FlxSprite {
 public var x:Float=0; public var y:Float=0; public var width:Float=0; public var height:Float=0;
 public var alpha:Float=1; public var visible:Bool=true; public var antialiasing:Bool=true;
 public var scale:Scale=new Scale(); public var graphic:Dynamic;
 public var requestedWidth:Float=-1; public var requestedHeight:Float=-1; public var hitboxUpdates:Int=0;
 public function new() {}
 public function loadGraphic(value:Dynamic):FlxSprite {graphic=value;width=400;height=200;return this;}
 public function setGraphicSize(width:Float=0,height:Float=0):Void {requestedWidth=width;requestedHeight=height;}
 public function updateHitbox():Void hitboxUpdates++;
 public function screenCenter():Void {x=(FlxG.width-width)/2;y=(FlxG.height-height)/2;}
 public function destroy():Void {}
}
class FlxKeys {
 public var justPressed:{var SPACE:Bool;var ENTER:Bool;}={SPACE:false,ENTER:false};
 public function new() {}
}
class SoundManager {
 public var volume:Float=0.4; public var muted:Bool=true; public var sounds:Array<Dynamic>=[];
 public function new() {}
 public function play(sound:Dynamic):Void sounds.push(sound);
}
class RandomObject {
 public function new() {}
 public function getObject<T>(values:Array<T>):Null<T> return values.length==0?null:values[values.length-1];
}
class FlxG {
 public static var width:Int=800; public static var height:Int=600; public static var autoPause:Bool=true;
 public static var updateFramerate:Float=10000; public static var drawFramerate:Float=10000;
 public static var keys:FlxKeys=new FlxKeys(); public static var sound:SoundManager=new SoundManager();
 public static var random:RandomObject=new RandomObject();
}
class FlxTimer {
 public static var all:Array<FlxTimer>=[];
 public var duration:Float=0; public var callback:FlxTimer->Void;
 public var active:Bool=false; public var cancelled:Bool=false; public var destroyed:Bool=false;
 public function new() all.push(this);
 public function start(duration:Float,callback:FlxTimer->Void):FlxTimer {
  this.duration=duration;this.callback=callback;active=true;return this;
 }
 public function reset(duration:Float):FlxTimer {this.duration=duration;active=true;return this;}
 public function cancel():Void {active=false;cancelled=true;}
 public function destroy():Void {active=false;destroyed=true;}
 public function run():Void {if(!active)return;active=false;callback(this);}
 public static function wait(duration:Float,callback:Void->Void):FlxTimer
  return new FlxTimer().start(duration,function(_:FlxTimer):Void callback());
 public static function lastActive(duration:Float):FlxTimer {
  var i=all.length;
  while(i-->0)if(all[i].active&&all[i].duration==duration)return all[i];
  return null;
 }
}
class FlxEase { public static var elasticOut:Dynamic='elasticOut'; public static var quadIn:Dynamic='quadIn'; }
class FlxTween {
 public static var all:Array<FlxTween>=[];
 public var target:Dynamic; public var properties:Dynamic; public var duration:Float; public var options:Dynamic;
 public var cancelled:Bool=false;
 public function new(target:Dynamic,properties:Dynamic,duration:Float,options:Dynamic) {
  this.target=target;this.properties=properties;this.duration=duration;this.options=options;all.push(this);
 }
 public function cancel():Void cancelled=true;
 public static function tween(target:Dynamic,properties:Dynamic,duration:Float,options:Dynamic):FlxTween
  return new FlxTween(target,properties,duration,options);
}
class NightmareVisionPaths {
 public var listed:Array<String>=[]; public var directories:Map<String,Bool>=new Map();
 public var images:Array<String>=[]; public var sounds:Array<String>=[]; public var videoFile:String='owner/videos/intro.mp4';
 public var videoFileExists:Bool=false; public var videoLoadSucceeds:Bool=true; public var videoDecoderAvailable:Bool=true;
 public var videoEndDuringRegistration:Bool=false;
 public var listCalls:Int=0;
 public function new() {}
 public function listAllFilesInDirectory(path:String):Array<String> {listCalls++;return listed.copy();}
 public function isDirectory(path:String):Bool return directories.exists(path);
 public function image(key:String):Dynamic {images.push(key);return {key:key};}
 public function sound(key:String):Dynamic {sounds.push(key);return 'sound:'+key;}
 public function video(key:String):String return videoFile;
 public function exists(path:String):Bool return path==videoFile&&videoFileExists;
}
class NightmareVisionVideoSprite extends FlxSprite {
 public static var muted:String=':no-audio';
 public static var all:Array<NightmareVisionVideoSprite>=[];
 public var ownerState:Dynamic; public var ownerPaths:NightmareVisionPaths; public var bitmap:Dynamic;
 public var loadedPath:String; public var loadOptions:Array<String>; public var started:Bool=false;
 public var stopped:Bool=false; public var destroyed:Bool=false; public var formatCallback:Void->Void; public var endCallback:Void->Void;
 public function new(ownerState:Dynamic,ownerPaths:NightmareVisionPaths) {
  super();this.ownerState=ownerState;this.ownerPaths=ownerPaths;
  bitmap=ownerPaths.videoDecoderAvailable?{}:null;all.push(this);
 }
 public function onFormat(callback:Void->Void):Void formatCallback=callback;
 public function onEnd(callback:Void->Void):Void {
  endCallback=callback;
  if(ownerPaths.videoEndDuringRegistration)callback();
 }
 public function load(path:String,?options:Array<String>):Bool {loadedPath=path;loadOptions=options;return ownerPaths.videoLoadSucceeds;}
 public function delayAndStart():Void started=true;
 public function stop():Void {stopped=true;if(endCallback!=null)endCallback();}
 override public function destroy():Void {destroyed=true;bitmap=null;super.destroy();}
}

class InitialState extends FlxState {
 public var label:String;
 public function new(label:String) {super();this.label=label;}
}
class Main {
 static function check(value:Bool,message:String):Void if(!value)throw message;
 static function main():Void {
  var paths=new NightmareVisionPaths();
  paths.listed=['owner/images/branding/watermarks/folder',
   'owner/images/branding/watermarks/nightmare-pixel.png'];
  paths.directories.set(paths.listed[0],true);
  var save:Map<String,Dynamic>=['mute'=>true,'volume'=>0.28];
  var currentInitialState='before';var factoryCalls=0;var queued:Array<Void->FlxState>=[];
  var disposedStates:Array<Dynamic>=[];
  var host:NightmareVisionSplashStateHost={
   paths:paths,
   readOwnerSave:function(field:String):Dynamic return save.get(field),
   onDisposed:function(state:Dynamic):Void disposedStates.push(state),
   initialStateConstructor:function():FlxState {factoryCalls++;return new InitialState(currentInitialState);},
   switchStartup:function(constructor:Void->FlxState):Void queued.push(constructor)
  };
  var state=new NightmareVisionSplashState(host);
  state.create();
  check(!FlxG.autoPause,'splash disables auto-pause during intro');
  check(FlxG.updateFramerate==10000&&FlxG.drawFramerate==10000,'splash leaves user unlimited FPS untouched');
  FlxTimer.lastActive(1).run();
  check(paths.images.length==1&&paths.images[0]=='branding/watermarks/nightmare-pixel',
   'watermark selection removes directories and uses the selected owner image key');
  var logo:FlxSprite=cast state.members[0];
  check(!logo.antialiasing&&Math.abs(logo.scale.x-1.6)<0.0001,
   'pixel watermark uses the source antialias flag and height/width scale calculation');
  var startAnimation=FlxTimer.lastActive(1);
  check(startAnimation!=null,'selected logo waits the source one second before animation');
  startAnimation.run();
  var animation=FlxTimer.lastActive(0.25);
  check(animation!=null,'logo steps begin after source quarter-second delay');
  animation.run();
  check(FlxG.sound.volume==1&&FlxG.sound.muted&&logo.visible&&paths.sounds[0]=='intro'
   &&Math.abs(logo.scale.x-0.32)<0.0001&&Math.abs(logo.scale.y-2.0)<0.0001
   &&animation.duration==0.06125,
   'first branding beat plays intro sound and applies the source squash');
  animation.run();
  check(Math.abs(logo.scale.x-2.0)<0.0001&&Math.abs(logo.scale.y-0.8)<0.0001
   &&animation.duration==0.06125,'second branding beat applies the source stretch');
  animation.run();
  check(Math.abs(logo.scale.x-1.8)<0.0001&&Math.abs(logo.scale.y-1.8)<0.0001
   &&FlxTween.all[0].duration==0.25&&Reflect.field(FlxTween.all[0].options,'ease')=='elasticOut'
   &&animation.duration==1.25,'third beat uses the elastic settle tween and source hold');
  animation.run();
  check(FlxTween.all.length==3&&FlxTween.all[1].duration==1.5&&FlxTween.all[2].duration==1.5
   &&Reflect.field(FlxTween.all[1].options,'ease')=='quadIn'
   &&Reflect.field(FlxTween.all[2].options,'ease')=='quadIn',
   'fourth beat fades the logo and scale with the source quad easing');
  var onFadeComplete:Dynamic=Reflect.field(FlxTween.all[2].options,'onComplete');
  Reflect.callMethod(null,onFadeComplete,[FlxTween.all[2]]);
  check(FlxTimer.lastActive(0.8)!=null,'fade waits the source final eight tenths before completion');
  FlxTimer.lastActive(0.8).run();
  check(queued.length==1&&factoryCalls==0,'completion queues the source initial-state constructor');
  check(FlxG.autoPause&&FlxG.sound.muted&&Math.abs(FlxG.sound.volume-0.28)<0.0001,
   'completion restores captured auto-pause and owner-private saved mute/volume');
  currentInitialState='after';
  var initial:InitialState=cast queued[0]();
  check(factoryCalls==1&&initial.label=='after','queued closure reads the live source initial state at construction');
  check(FlxG.updateFramerate==10000&&FlxG.drawFramerate==10000,
   'the full splash timing path preserves uncapped FPS');

  FlxG.autoPause=true;FlxG.sound.muted=true;FlxG.sound.volume=0.2;
  FlxG.keys.justPressed.SPACE=true;
  var skipped=new NightmareVisionSplashState(host);skipped.create();skipped.update(0.016);
  check(queued.length==2&&FlxG.autoPause&&FlxG.sound.muted&&FlxG.sound.volume==0.28,
   'space skips before video creation safely and restores owner audio and pause state');
  FlxG.keys.justPressed.SPACE=false;

  paths.listed=[];FlxG.autoPause=true;
  var empty=new NightmareVisionSplashState(host);empty.create();FlxTimer.lastActive(1).run();
  check(queued.length==3&&FlxG.autoPause,'empty branding directories complete without a null selection crash');

  FlxTimer.all=[];FlxTween.all=[];paths.listed=['owner/images/branding/watermarks/leave.png'];
  FlxG.autoPause=true;FlxG.sound.muted=true;FlxG.sound.volume=0.11;
  var departing=new NightmareVisionSplashState(host);departing.create();
  FlxTimer.lastActive(1).run();FlxTimer.lastActive(1).run();
  var departingAnimation=FlxTimer.lastActive(0.25);
  departingAnimation.run();departingAnimation.run();departingAnimation.run();
  var pendingStep=FlxTimer.lastActive(1.25);
  check(pendingStep!=null&&FlxTween.all.length==1,'departure fixture reaches an active source tween and timer');
  var queuedBeforeDestroy=queued.length;
  departing.destroy();
  departing.destroy();
  check(disposedStates.length==1&&disposedStates[0]==departing,
   'source host retires a destroyed splash exactly once without discarding pending states');
  check(departing.destroyed&&pendingStep.cancelled&&pendingStep.destroyed&&FlxTween.all[0].cancelled,
   'external state departure cancels every owned timer and tween');
  check(FlxG.autoPause&&FlxG.sound.muted&&Math.abs(FlxG.sound.volume-0.28)<0.0001
   &&queued.length==queuedBeforeDestroy,
   'unexpected departure restores owner sound and autopause without starting another state');

  FlxTimer.all=[];FlxTween.all=[];paths.listCalls=0;paths.videoFileExists=true;
  paths.videoDecoderAvailable=true;paths.videoLoadSucceeds=true;
  FlxG.autoPause=true;FlxG.sound.muted=false;FlxG.sound.volume=0.07;
  var beforeVideoStartup=queued.length;
  var videoState=new NightmareVisionSplashState(host);videoState.create();FlxTimer.lastActive(1).run();
  var video=NightmareVisionVideoSprite.all[NightmareVisionVideoSprite.all.length-1];
  check(video.ownerState==videoState&&video.ownerPaths==paths&&video.loadedPath==paths.videoFile
   &&video.loadOptions.length==1&&video.loadOptions[0]==NightmareVisionVideoSprite.muted&&video.started,
   'C++ video uses the shared owner wrapper, selected path, delayed start, and native muted option');
  video.formatCallback();
  check(video.requestedWidth==0&&video.requestedHeight==FlxG.height&&video.hitboxUpdates==1,
   'video format callback scales to the source screen height and centers its updated hitbox');
  var brandingReads=paths.listCalls;
  video.endCallback();
  check(queued.length==beforeVideoStartup+1&&video.stopped&&video.destroyed&&paths.listCalls==brandingReads
   &&FlxG.autoPause&&FlxG.sound.muted&&Math.abs(FlxG.sound.volume-0.28)<0.0001,
   'video completion releases shared decoder resources and restores source services without logo fallback');

  FlxTimer.all=[];FlxTween.all=[];paths.videoEndDuringRegistration=true;
  var beforeSynchronousEnd=queued.length;
  var immediateEndState=new NightmareVisionSplashState(host);immediateEndState.create();FlxTimer.lastActive(1).run();
  var immediateVideo=NightmareVisionVideoSprite.all[NightmareVisionVideoSprite.all.length-1];
  check(queued.length==beforeSynchronousEnd+1&&immediateVideo.destroyed&&!immediateVideo.started,
   'an already-ended owner video cannot leave a delayed start on a retired splash');
  paths.videoEndDuringRegistration=false;

  FlxTimer.all=[];FlxTween.all=[];paths.videoFileExists=true;paths.videoLoadSucceeds=false;
  paths.listed=['owner/images/branding/watermarks/load-fallback.png'];
  var fallbackReads=paths.listCalls;
  var failedVideoState=new NightmareVisionSplashState(host);failedVideoState.create();FlxTimer.lastActive(1).run();
  check(NightmareVisionVideoSprite.all[NightmareVisionVideoSprite.all.length-1].destroyed
   &&paths.listCalls==fallbackReads+1,
   'a video load failure retires its wrapper and falls through to source watermark branding');
  failedVideoState.destroy();

  FlxTimer.all=[];FlxTween.all=[];paths.videoFileExists=true;paths.videoDecoderAvailable=false;
  var decoderReads=paths.listCalls;
  var missingDecoderState=new NightmareVisionSplashState(host);missingDecoderState.create();FlxTimer.lastActive(1).run();
  check(NightmareVisionVideoSprite.all[NightmareVisionVideoSprite.all.length-1].destroyed
   &&paths.listCalls==decoderReads+1,
   'an unavailable video decoder is safely released before source watermark fallback');
  missingDecoderState.destroy();
 }
}
'''
        imports = "import haxe.io.Path;\nusing StringTools;\n"
        test_body = body.replace("#if cpp", "#if testCpp")
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(imports + fixture + test_body, encoding="utf-8")
            result = subprocess.run(
                [*HAXE_COMMAND, "-D", "testCpp", "-cp", str(work), "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
