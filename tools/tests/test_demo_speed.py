"""Run the production demo controls and note-spawning loop with renderer stubs."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class DemoSpeedTest(unittest.TestCase):
    def test_controls_audio_pause_limits_and_dense_note_spawning(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        start = source.index('\tfunction setDemoPlaybackRate(')
        # draw() is a FlxState override with renderer dependencies; this
        # extraction covers the demo-control methods immediately before it.
        draw = source.index('\toverride public function draw():Void', start)
        update = source.index('\toverride public function update(', draw)
        methods = source[start:draw]
        controls = source[update:source.index("\t\t//setAllHaxeVar", update)]
        controls = controls.replace('override public function update', 'public function update') + '\n}\n'
        queue = source.index('\t\twhile (unspawnNotes.length > 0 && unspawnNotes[0].strumTime - Conductor.songPosition < noteSpawnLookahead)')
        spawn = source[queue:source.index('\n\t\tif (generatedMusic)', queue)]
        fixture = '''
class Audio { public var pitch:Float=1; public var time:Float=10000; public var playing:Bool=true; public function new() {} }
class FlxG {
 public static var timeScale:Float=1;
 public static var sound={music:new Audio()};
 public static var keys={justPressed:{LEFT:false,RIGHT:false}};
}
class FlxMath { public static function bound(v:Float,low:Float,high:Float) return Math.max(low,Math.min(high,v)); }
class Conductor {
 public static var songPosition:Float=10000;
 public static var bpm:Float=120;
 public static var crochet:Float=500;
 public static var stepCrochet:Float=125;
}
class SongStub { public var song:String=''; public function new() {} }
class FNFAssets {
 public static function exists(_path:String):Bool return false;
 public static function getText(_path:String):String return '';
}
class Note {
 public var strumTime:Float; public var alive:Bool=true; public var active:Bool=true; public var visible:Bool=true;
 public var spawned:Bool=false;
 public var sourcePlayfieldIndex:Int=0; public var isSustainNote:Bool=false;
 public var frameWidth:Float=10; public var frameHeight:Float=10; public var clipRect:Dynamic=null;
 public var nightmareVisionRenderer:Dynamic=null;
 public function new(t:Float) {strumTime=t;}
 public function kill():Void alive=false;
 public function destroy():Void {}
}
class EngineCompat {
 public static function hxcNoteIncomingPayload(note:Dynamic):Dynamic return {};
 public static function hxcApplyNoteCallbackPayload(payload:Dynamic):Void {}
}
class CodenameModRuntime {
 public static function updateGlobal(_elapsed:Float):Void {}
}
class NightmareVisionScriptGroup {
 public static inline var CONTINUE_FUNC:Int=1;
 public static inline var STOP_FUNC:Int=2;
}
class NightmareVisionNoteTypeRuntime {
 public static function noteTypeOf(_note:Dynamic):Dynamic return null;
}
class FlxRect {public function new(_x:Float,_y:Float,_width:Float,_height:Float) {}}
// PlayState's production runtime smoke hook is intentionally inert in this
// renderer-free extraction fixture. Keep the call in the extracted update
// loop so the fixture continues to pin the real production method body.
class RuntimeSmokeHarness {
 public static function tick(_elapsed:Float):Bool return false;
 public static function profileEnabled():Bool return false;
 public static function profileSection(_section:String, _seconds:Float):Void {}
}
class Group {
 public var members:Array<Note>=[];
 public function new() {}
 public function add(note:Note) {members.push(note);}
}
class StrumGroup {public var members:Array<Dynamic>=[]; public function new() {}}
class DemoTest {
 var demoMode=true; var demoPlaybackRate:Float=1;
 var demoSpeedTxt={text:""}; var vocals=new Audio();
 var missesTxt:Dynamic=null; var misses=0; var comboBreaks=true;
 var paused=false; var startingSong=false; var endingSong=false;
 var psychGameOverTransitionPending=false;
 var startedCountdown=true; var inCutscene=false;
 var demoSongFinished=false; var songLength:Float=12000;
 var unspawnNotes:Array<Note>=[]; var notes=new Group(); var loaded=0;
 var hxcStrumlineNoteSurface:Dynamic=null;
 var codenameInputLines:Array<Dynamic>=[];
 function bindCodenameNoteLine(note:Note):Void {}
 var noteSpawnLookahead:Float=1500;
 var compatCustomSubstateName:String=''; var compatCustomSubstateOpen:Bool=false;
 var legacyOffsetDiagnosticEmitted:Bool=false;
 var nightmareVisionNoteTypes:Dynamic=null; var nightmareVisionScripts:Dynamic=null;
 var nightmareContext:Dynamic=null; var playerStrums:StrumGroup=new StrumGroup(); var enemyStrums:StrumGroup=new StrumGroup();
 var SONG:SongStub=null;
 var haxeVars:Map<String,Dynamic>=new Map();
 function callAllHScript(name:String,args:Array<Dynamic>,?skipHxc:Bool=false) {if (name == 'noteLoaded') loaded++;}
 function callHxcNoteHScript(name:String,args:Array<Dynamic>):Void {}
 function setAllHaxeVar(name:String, value:Dynamic):Void haxeVars.set(name, value);
 function setVocalsPitch(pitch:Float):Void vocals.pitch = pitch;
 function syncVocalTrackState():Void {}
 // The fixture runs without a selected NMV owner, so gameplay callbacks use
 // the production group's default continue result.
 function callNightmareVision(_event:String, ?_args:Array<Dynamic>):Dynamic
  return NightmareVisionScriptGroup.CONTINUE_FUNC;
 function processNightmareVisionHolds():Void {}
 function currentSongDataPath(fileName:String):String return 'assets/data/demo/' + fileName;
 function nightmareVisionRenderer(_field:Int):Dynamic return {configureNote:function(_note:Note):Void {}};
 function nightmareVisionRenderContext():Dynamic return null;
 public function new() {}
''' + methods + controls + '\nfunction spawn() {\n' + spawn + '''\n}
 static function check(ok:Bool, message:String) {if(!ok) throw message;}
 static function main() {
  var state=new DemoTest();
  FlxG.keys.justPressed.RIGHT=true;
  state.update(0);
  check(state.demoPlaybackRate==1.5, "Right should add 0.5x");
  check(FlxG.timeScale==1.5 && FlxG.sound.music.pitch==1.5 && state.vocals.pitch==1.5, "Gameplay and both tracks must agree");
  check(state.haxeVars.get("songPos") == Conductor.songPosition
    && state.haxeVars.get("curBpm") == Conductor.bpm
    && state.haxeVars.get("crochet") == Conductor.crochet
    && state.haxeVars.get("stepCrochet") == Conductor.stepCrochet,
    "Timing globals must follow the authoritative Conductor clock");
  check(state.demoSpeedTxt.text.indexOf("1.5x")>=0, "HUD should display the speed");
  for(i in 0...200) state.update(0);
  check(state.demoPlaybackRate==50, "Speed must cap at 50x");
  FlxG.keys.justPressed.LEFT=true;
  state.update(0); check(state.demoPlaybackRate==50, "Opposing keys should cancel");
  FlxG.keys.justPressed.RIGHT=false;
  for(i in 0...200) state.update(0);
  check(state.demoPlaybackRate==1, "Speed must not fall below 1x");
  state.setDemoPlaybackRate(4);
  state.paused=true; state.applyDemoPlaybackRate();
  check(FlxG.timeScale==1, "Pause menu must run at normal speed");
  state.update(0); check(state.demoPlaybackRate==4, "Paused input must not change speed");
  state.paused=false; state.applyDemoPlaybackRate();
  check(FlxG.timeScale==4 && state.vocals.pitch==4, "Resume must restore speed");
  state.resetDemoPlaybackRate();
  check(FlxG.timeScale==1 && state.vocals.pitch==1 && FlxG.sound.music.pitch==1, "Leaving must reset global speed and audio");
  state.startingSong=true; state.setDemoPlaybackRate(3);
  check(FlxG.timeScale==3 && FlxG.sound.music.pitch==1, "Countdown must not pitch menu music");
  state.startingSong=false; state.applyDemoPlaybackRate();
  check(FlxG.sound.music.pitch==3, "Song start must apply pending speed");
  state.demoSongFinished=true; FlxG.sound.music.time=0;
  state.updateDemoClock();
  check(Conductor.songPosition==12000, "Audio completion must advance to the end, not rewind");
  state.demoSongFinished=false; FlxG.sound.music.time=10000;
  state.updateDemoClock();
  check(Conductor.songPosition==10000, "Demo clock must sample current audio");
  Conductor.songPosition=11970; FlxG.sound.music.time=0; FlxG.sound.music.playing=false;
  state.updateDemoClock();
  check(Conductor.songPosition==12000, "Stopped audio must not rewind beat hooks before completion callback");
  Conductor.songPosition=11970; FlxG.sound.music.time=0; FlxG.sound.music.playing=true;
  state.updateDemoClock();
  check(Conductor.songPosition==12000, "A native end-position wrap must not rewind beat hooks while the channel is still marked playing");
  state.paused=true; Conductor.songPosition=11970; FlxG.sound.music.time=0;
  state.updateDemoClock();
  check(Conductor.songPosition==11970, "Pause must freeze the sampled beat clock");
  state.paused=false; Conductor.songPosition=10000; FlxG.sound.music.time=0;
  state.updateDemoClock();
  check(Conductor.songPosition==0, "A deliberate seek before the final-second boundary must remain available");
  state.songLength=500; Conductor.songPosition=0; FlxG.sound.music.time=0;
  state.updateDemoClock();
  check(Conductor.songPosition==0, "A zero position at the start of a subsecond song must not look completed");
  Conductor.songPosition=400; FlxG.sound.music.time=0;
  state.updateDemoClock();
  check(Conductor.songPosition==500, "A near-end wrap must still complete a subsecond song");
  state.songLength=12000;
  FlxG.sound.music.playing=true; FlxG.sound.music.time=5000;
  state.updateDemoClock();
  check(Conductor.songPosition==5000, "A playing track may still seek backwards");
  Conductor.songPosition=10000;
  state.resetDemoPlaybackRate(); state.demoMode=false;
  state.setDemoPlaybackRate(5);
  check(FlxG.timeScale==1 && FlxG.sound.music.pitch==1, "Normal gameplay must remain unchanged");
  for(i in 0...100) state.unspawnNotes.push(new Note(10000+i));
  state.unspawnNotes.push(new Note(12000));
  state.spawn();
  check(state.notes.members.length==100 && state.loaded==100, "All due notes and hooks must spawn in the same frame");
  check(state.unspawnNotes.length==1 && state.unspawnNotes[0].strumTime==12000, "Future notes must remain queued");
 }
}
'''
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'DemoTest.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder,
                                     '-main', 'DemoTest', '--interp'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
