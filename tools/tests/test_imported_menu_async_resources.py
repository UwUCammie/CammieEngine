"""Execute the shared async ownership contracts without external donor fixtures."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_source_event_preparation import extract_method
ROOT=Path(__file__).resolve().parents[2]

class ImportedMenuAsyncResourcesTest(unittest.TestCase):
    def test_owned_timer_tween_audio_pause_and_retirement(self):
        source=(ROOT/'source/CodenameScriptInterp.hx').read_text(encoding='utf-8')
        methods='\n'.join(extract_method(source,m) for m in ['public function ownTimer(', 'public function ownSound(', 'public function setPaused('])
        release_start=source.index('public function release():Void')
        cleanup=source[source.index('\t\tfor (tween in ownedTweens)',release_start):source.index('\t\tfor (owned in ownedCameraFilters.copy())',release_start)]
        # The block above is the real shared release body, including sound manager removal.
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            work=FixturePath(directory)
            (work/'flixel/sound').mkdir(parents=True)
            (work/'flixel/sound/FlxSound.hx').write_text('package flixel.sound;class FlxSound {public var playing=true;public var destroyed=false;public var onComplete:Dynamic;public var fadeTween:Dynamic;public function new(){}public function pause():Void playing=false;public function resume():Void playing=true;public function stop():Void playing=false;public function destroy():Void destroyed=true;}')
            (work/'Main.hx').write_text(r'''import flixel.sound.FlxSound;
class FlxTimer {public var active=true;public var finished=false;public var calls=0;public function new(){}public function tick(){if(active)calls++;}public function cancel(){active=false;finished=true;}}
class FlxTween {public var active=true;public var finished=false;public var calls=0;public function new(){}public function tick(){if(active)calls++;}public function cancel(){active=false;finished=true;}}
class FlxG {public static var removed:Array<FlxSound>=[];public static var sound:Dynamic={music:null,list:{remove:function(s:FlxSound,v:Bool){removed.push(s);}}};}
class Scope {
 var ownedTimers:Array<FlxTimer>=[];var ownedTweens:Array<FlxTween>=[];var ownedSounds:Array<FlxSound>=[];
 var pausedTimers:Map<FlxTimer,Bool>=[];var pausedTweens:Map<FlxTween,Bool>=[];var pausedSounds:Map<FlxSound,Bool>=[];var paused=false;
 public function new(){}public function tween(t:FlxTween)ownedTweens.push(t);
'''+methods+'\n public function release():Void {\n'+cleanup+r'''}
}
class Main {static function main(){
 var first=new Scope();var second=new Scope();var timer=new FlxTimer();var tween=new FlxTween();var sound=new FlxSound();var otherSound=new FlxSound();
 first.ownTimer(timer);first.tween(tween);first.ownSound(sound);first.ownSound(sound);second.ownSound(otherSound);
 timer.tick();tween.tick();first.setPaused(true);timer.tick();tween.tick();
 if(timer.calls!=1||tween.calls!=1||sound.playing||!otherSound.playing)throw 'parked resources escaped';
 first.setPaused(false);timer.tick();tween.tick();if(timer.calls!=2||tween.calls!=2||!sound.playing)throw 'resume lost resource state';
 FlxG.sound.music=sound;first.release();first.release();timer.tick();tween.tick();
 if(timer.calls!=2||tween.calls!=2||sound.playing||!sound.destroyed||otherSound.destroyed||FlxG.sound.music!=null||FlxG.removed.length!=1)throw 'retired callbacks/audio escaped or foreign ownership destroyed';
 second.release();if(!otherSound.destroyed)throw 'second owner resource survived';
}}''')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','Main','--interp'],cwd=work,text=True,capture_output=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_actual_lowered_safe_tween_returns_owned_native_resource(self):
        source=(ROOT/'source/CodenameScriptInterp.hx').read_text()
        runtime=(ROOT/'source/HxcCompatRuntime.hx').read_text()
        ownership='\n'.join(extract_method(source,m) for m in ['public function trackReturnedTween(', 'public function ownTween('])
        helpers='\n'.join(extract_method(runtime,m) for m in ['public static function safeTween(', 'static function runtimeField(', 'static function runtimeFloatValue('])
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            work=FixturePath(directory)
            (work/'flixel/tweens').mkdir(parents=True)
            (work/'flixel/tweens/FlxTween.hx').write_text('package flixel.tweens;@:keep class FlxTween {public var active=true;public function new(){}public static function tween(t:Dynamic,v:Dynamic,d:Float,o:Dynamic):FlxTween return new FlxTween();public function cancel():Void active=false;}')
            (work/'HxcCompatRuntime.hx').write_text('class HxcCompatRuntime {public static function markSongEventNativeHandled(e:Dynamic):Void {} public static function beginActiveSong(?s:Dynamic):Void {} public static function observeIncoming(n:Dynamic):Void {} static var missingTweenFields:Map<String,Bool>=[];static function runtimeString(v:Dynamic):String return Std.string(v);'+helpers+'}')
            (work/'Main.hx').write_text(r'''import flixel.tweens.FlxTween;
class Scope extends hscript.Interp {
 public var ownedTweens:Array<FlxTween>=[];var paused=false;var pausedTweens:Map<FlxTween,Bool>=[];
 public function new(){super();}
 override function fcall(o:Dynamic,f:String,a:Array<Dynamic>):Dynamic {
 var result=super.fcall(o,f,a);trackReturnedTween(result);return result;
 }
 __OWNERSHIP__
}
class Main {static function main(){
 var adapted=HxcCompat.analyze("class MainMenuState extends MusicBeatState {override function create():Void {var label={alpha:1.0};FlxTween.tween(label,{alpha:0.5},30);}}","MainMenuState.hx");
 if(adapted.generatedHscript.indexOf("HxcCompatRuntime.safeTween(")<0)throw 'fixture was not lowered through actual helper';
 var parser=new hscript.ParserEx();var scope=new Scope();scope.variables.set('HxcCompatRuntime',HxcCompatRuntime);
 scope.execute(parser.parseString(adapted.generatedHscript));Reflect.callMethod(null,scope.variables.get('start'),[]);
 if(scope.ownedTweens.length!=1||!scope.ownedTweens[0].active)throw 'lowered native tween escaped tracker';
 var tween=scope.ownedTweens[0];scope.trackReturnedTween(tween);if(scope.ownedTweens.length!=1)throw 'duplicate tracking';
 tween.cancel();if(tween.active)throw 'resource retirement did not cancel';
 }}'''.replace('__OWNERSHIP__',ownership))
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-ex/git/src'),'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
