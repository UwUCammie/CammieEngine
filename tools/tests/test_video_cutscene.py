from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class VideoCutsceneTest(unittest.TestCase):
    def test_event_video_resolves_selected_owner_before_global_media(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        method = self.extract_method(source, 'function compatEventVideoPath(name:String):String')
        fixture = '''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;
class FNFAssets {
 public static function isInScope(path:String):Bool
  return path.startsWith("assets/") && path.indexOf("..") < 0;
 public static function exists(path:String):Bool return FileSystem.exists(path);
}
class CompatScriptManifest {
 public static function selectedRoot(manifest:Dynamic):String return manifest.owner;
}
class VideoOwnerFixture {
 var owner:String;
 public function new(owner:String) this.owner=owner;
 function getCompatScriptManifest():Dynamic return {owner:owner};
__METHOD__
 static function check(actual:String, expected:String):Void
  if (actual != expected) throw "video owner mismatch: " + actual + " != " + expected;
 static function main():Void {
  check(new VideoOwnerFixture("assets/imported_mods/first").compatEventVideoPath("clip"),
   "assets/imported_mods/first/videos/videos/clip.mp4");
  check(new VideoOwnerFixture("assets/imported_mods/second").compatEventVideoPath("clip"),
   "assets/imported_mods/second/videos/clip.mp4");
  check(new VideoOwnerFixture("assets/imported_mods/second").compatEventVideoPath("videos/webm-only.webm"),
   "assets/imported_mods/second/videos/webm-only.webm");
  check(new VideoOwnerFixture("assets/imported_mods/missing").compatEventVideoPath("clip"), null);
  check(new VideoOwnerFixture("").compatEventVideoPath("clip"), "assets/videos/clip.mp4");
  check(new VideoOwnerFixture("assets/imported_mods/first").compatEventVideoPath("../clip"), null);
 }
}'''.replace('__METHOD__', method)
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            for relative in ('assets/videos/clip.mp4',
                             'assets/imported_mods/first/videos/videos/clip.mp4',
                             'assets/imported_mods/second/videos/clip.mp4',
                             'assets/imported_mods/second/videos/webm-only.webm'):
                asset = Path(folder) / relative
                asset.parent.mkdir(parents=True, exist_ok=True)
                asset.write_bytes(b'clip')
            (Path(folder) / 'VideoOwnerFixture.hx').write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', folder, '-main', 'VideoOwnerFixture', '--interp'],
                cwd=folder, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_only_chart_event_video_uses_native_pause_lifecycle(self):
        play_state = (ROOT / 'source/PlayState.hx').read_text()
        open_substate = self.extract_method(play_state, 'override function openSubState(')
        close_substate = self.extract_method(play_state, 'override function closeSubState()')
        self.assertIn('if (compatEventVideo != null) compatEventVideo.suspend();', open_substate)
        self.assertIn('if (resumeEventVideo && compatEventVideo != null) compatEventVideo.resume();',
                      close_substate)

    @staticmethod
    def extract_method(source, signature):
        start = source.index(signature)
        opening = source.index('{', start)
        depth = 0
        for index in range(opening, len(source)):
            if source[index] == '{':
                depth += 1
            elif source[index] == '}':
                depth -= 1
                if depth == 0:
                    return source[start:index + 1]
        raise AssertionError(f'unclosed method {signature}')

    def test_completion_skip_failure_and_cleanup(self):
        source = (ROOT / 'source/VideoCutscene.hx').read_text().replace('#if cpp', '').replace('#end', '')
        files = {
            'VideoCutscene.hx': source,
            'flixel/FlxBasic.hx': 'package flixel; class FlxBasic {public function new(){} public function update(t:Float){} public function destroy(){}}',
            'Event.hx': '''class Event {var handlers:Array<Dynamic>=[]; public function new(){} public function add(f:Dynamic){handlers.push(f);} public function remove(f:Dynamic){} public function dispatch(){for(f in handlers) Reflect.callMethod(null,f,[]);}}''',
            'flixel/FlxG.hx': '''package flixel; class FlxG {
                public static var children=0;
                public static var firstChild:Dynamic;
                public static var stage={stageWidth:1280,stageHeight:720,numChildren:8,setChildIndex:function(v:Dynamic,i:Int){}};
                public static var signals={gameResized:new Event(),focusGained:new Event()};
                public static var keys={justPressed:{SPACE:false}};
                public static function addChildBelowMouse(v:Dynamic){if(children==0)firstChild=v;children++;}
                public static function removeChild(v:Dynamic){children--;}
            }''',
            'openfl/display/Sprite.hx': '''package openfl.display; class Sprite {
                public var visible=true;
                public var graphics={clear:function(){},beginFill:function(c:Int){},drawRect:function(x:Int,y:Int,w:Int,h:Int){},endFill:function(){}};
                public function new(){}
            }''',
            'hxvlc/flixel/FlxVideo.hx': '''package hxvlc.flixel;
                enum abstract Axes(Int) {var NONE=0;}
                class FlxVideo {
                public static var last:FlxVideo; public static var loadOK=true;
                public var resizeMode:Axes; public var disposed=false; public var playing=false;
                public var isPlaying(get,never):Bool;
                function get_isPlaying():Bool return playing&&!paused;
                public var visible=true; public var paused=false; public var pauseCalls=0; public var resumeCalls=0;
                public var volumeAdjust:Float=1; public var volume:Float=1; public var time:Int=0;
                public var length:Int=20840; public var duration:Int=20840;
                public var onEndReached=new Event(); public var onEncounteredError=new Event(); public var onFormatSetup=new Event();
                public var bitmapData={width:1920,height:1080};
                public var width:Float=0;public var height:Float=0;public var x:Float=0;public var y:Float=0;
                public function new(){last=this;} public function load(p:String){return loadOK;}
                public function play(){playing=true;return true;} public function dispose(){disposed=true;}
                public function pause():Void {paused=true;pauseCalls++;}
                public function resume():Void {paused=false;resumeCalls++;}
            }''',
            'VideoTest.hx': '''import flixel.FlxG; import hxvlc.flixel.FlxVideo;
            class VideoTest {
              static function main(){
                var count=0; var clip:VideoCutscene=null;
                function make(path:String){clip=new VideoCutscene(path,function(){count++;clip.destroy();});return clip;}
                var path="__VIDEO_FIXTURE__";
                var normal=make(path);normal.update(0); var native=FlxVideo.last;
                if(!native.playing||count!=0||FlxG.children!=2)throw "Video must play before countdown";
                normal.suspend();normal.suspend();
                if(!native.paused||native.pauseCalls!=1||native.visible||FlxG.firstChild.visible||count!=0)
                 throw "Chart video was not suspended exactly once";
                native.paused=false;FlxG.signals.focusGained.dispatch();
                if(!native.paused||native.pauseCalls!=2)throw "Focus gain restarted a paused chart video";
                FlxG.keys.justPressed.SPACE=true;normal.update(0);
                if(count!=0)throw "Suspended clip consumed skip input";
                FlxG.keys.justPressed.SPACE=false;
                normal.resume();normal.resume();
                if(native.paused||native.resumeCalls!=1||!native.visible||!FlxG.firstChild.visible)
                 throw "Chart video did not resume exactly once";
                native.onFormatSetup.dispatch();
                if(native.width!=1280||native.height!=720)throw "Incorrect fit";
                native.onEndReached.dispatch();normal.update(0);normal.update(0);
                if(count!=1||!native.disposed||FlxG.children!=0)throw "Completion must clean up once";
                if(normal.skipped)throw "Natural completion was marked as a skip";
                var skip=make(path);skip.update(0);FlxG.keys.justPressed.SPACE=true;
                if(skip.durationMs!=20840)throw "Clip duration is not available for event seek";
                skip.update(0);FlxG.keys.justPressed.SPACE=false;
                if(count!=2||FlxG.children!=0)throw "Skip failed";
                if(!skip.skipped)throw "Explicit skip was not distinguished from completion";
                var deferred=make(path);deferred.update(0);native=FlxVideo.last;
                native.length=-1;native.duration=-1;
                FlxG.keys.justPressed.SPACE=true;deferred.update(0.016);FlxG.keys.justPressed.SPACE=false;
                if(count!=2||FlxG.children!=2)throw "Skip should wait briefly for delayed VLC metadata";
                native.duration=20840;deferred.update(0.016);
                if(count!=3||!deferred.skipped||FlxG.children!=0)throw "Deferred skip did not seek when metadata arrived";
                var unavailable=make(path);unavailable.update(0);native=FlxVideo.last;
                native.length=-1;native.duration=-1;
                FlxG.keys.justPressed.SPACE=true;unavailable.update(0.016);FlxG.keys.justPressed.SPACE=false;
                unavailable.update(1.0);
                if(count!=4||unavailable.skipped||!unavailable.skipRequested||FlxG.children!=0)throw "Missing metadata trapped the player";
                make("missing-cutscene.mp4").update(0);
                FlxVideo.loadOK=false;make(path).update(0);FlxVideo.loadOK=true;
                if(count!=6||FlxG.children!=0)throw "Failure must resume";
                var leave=make(path);leave.update(0);native=FlxVideo.last;leave.destroy();native.onEndReached.dispatch();leave.update(0);
                if(count!=6||FlxG.children!=0)throw "Leaving state must not start countdown";
                var configured= new VideoCutscene(path,function(){count++;}, {mute:true,timestamp:15,zIndex:4});
                configured.update(0); native=FlxVideo.last;
                if(native.volumeAdjust!=0||native.time!=15)throw "Playback options were not applied";
                configured.destroy();
                if(FlxG.children!=0)throw "Configured video cleanup failed";
                var eventVideo=new VideoCutscene(path,function(){}, {allowSkip:false});
                eventVideo.update(0);native=FlxVideo.last;
                FlxG.keys.justPressed.SPACE=true;eventVideo.update(0.5);
                if(eventVideo.skipped||eventVideo.skipRequested||FlxG.children!=2)
                 throw "Source event video accepted native skip input";
                FlxG.keys.justPressed.SPACE=false;
                native.onEndReached.dispatch();eventVideo.update(0);eventVideo.destroy();
                if(FlxG.children!=0)throw "Non-skippable event video did not complete";
                var accepting=false;
                var held=new VideoCutscene(path,function(){count++;},
                 {skipHoldSeconds:1,skipPressed:function() return accepting});
                held.update(0);FlxG.keys.justPressed.SPACE=true;held.update(0.5);
                if(held.skipped||count!=6)throw "Psych video ignored mapped accept hold";
                FlxG.keys.justPressed.SPACE=false;accepting=true;held.update(0.4);
                if(held.skipped||count!=6)throw "Psych video skipped before one second";
                held.update(0.6);
                if(!held.skipped||count!=7)throw "Psych video did not skip on held accept";
                held.destroy();
              }
            }'''
        }
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            fixture = Path(folder) / 'video-fixture.mp4'
            fixture.write_bytes(b'fixture')
            files['VideoTest.hx'] = files['VideoTest.hx'].replace('__VIDEO_FIXTURE__', str(fixture).replace('\\', '/'))
            for name, text in files.items():
                path = Path(folder) / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'VideoTest', '--interp'], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_event_video_skip_time_and_native_seek_boundary(self):
        source = (ROOT / 'source/EventVideoSkip.hx').read_text()
        play_state = (ROOT / 'source/PlayState.hx').read_text()
        files = {
            'EventVideoSkip.hx': source,
            'SeekTest.hx': '''class SeekTest {
                static function same(actual:Float, expected:Float, label:String) {
                    if (Math.abs(actual-expected)>0.001) throw label+": "+actual;
                }
                static function main() {
                    same(EventVideoSkip.target(500, 0, 20840, 140000), 20840, "video endpoint");
                    same(EventVideoSkip.target(21500, 0, 20840, 140000), 21500, "never rewind");
                    same(EventVideoSkip.target(10, 1000, 9000, 8000), 8000, "song end cap");
                    same(EventVideoSkip.target(10, 0, -1, 8000), 10, "unknown duration");
                    same(EventVideoSkip.target(10, 0, Math.NaN, 8000), 10, "invalid duration");
                }
            }'''
        }
        self.assertIn('if (video.skipped)', play_state)
        self.assertIn('skipCompatEventVideoToEnd(eventTime, video.durationMs)', play_state)
        self.assertIn('unspawnNotes[0].strumTime < target', play_state)
        self.assertIn('songEvents[songEventIndex].time < target', play_state)
        self.assertIn("EngineCompat.eventName(event.name) != 'Play Video'", play_state)
        self.assertIn('fireSongEvent(event);', play_state)
        self.assertIn('updateCurStep();', play_state)
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            for name, text in files.items():
                (Path(folder) / name).write_text(text, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder,
                                     '-main', 'SeekTest', '--interp'], cwd=ROOT,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_event_video_skip_updates_audio_notes_events_and_beat_cursor(self):
        play_state = (ROOT / 'source/PlayState.hx').read_text()
        note_source = (ROOT / 'source/Note.hx').read_text()
        seek_method = self.extract_method(
            play_state, 'function seekForwardSongTime(target:Float, captureSmokeState:Bool):Dynamic')
        repair_method = self.extract_method(
            note_source, 'public function repairSustainChainAfterSeek():Void')
        method = self.extract_method(play_state,
                                     'function skipCompatEventVideoToEnd(eventTime:Float, durationMs:Float):Void')
        method = method.replace('function skipCompatEventVideoToEnd(',
                                'public function skipCompatEventVideoToEnd(', 1)
        files = {
            'EventVideoSkip.hx': (ROOT / 'source/EventVideoSkip.hx').read_text(),
            'Conductor.hx': '''class Conductor {
                public static var songPosition:Float=500;
                public static var lastSongPos:Float=500;
                public static var bpm:Float=100;
                public static var bpmChangeMap:Array<{songTime:Float,bpm:Float}>=[{songTime:10000,bpm:150}];
                public static function changeBPM(value:Float):Void bpm=value;
            }''',
            'EngineCompat.hx': '''class EngineCompat {
                public static function eventName(name:String):String
                    return name=="PlayVideo" ? "Play Video" : name;
            }''',
            'FlxG.hx': '''class FlxG {
                public static var sound={music:new MockMusic()};
                public static var game={ticks:12345};
            }
            class MockMusic {public var time:Float=500;public function new(){}}''',
            'RuntimeSmokeHarness.hx': '''class RuntimeSmokeHarness {
                public static var skip:Dynamic;
                public static function markEventVideoSkip(eventTime:Float, from:Float,
                    target:Float, duration:Float, crossedEvents:Int):Void
                    skip={eventTime:eventTime,from:from,target:target,
                        duration:duration,crossedEvents:crossedEvents};
            }''',
            'SeekHost.hx': '''class NoteStub {
                public var strumTime:Float;
                public var destroyed=false;
                public var alive=true;
                public var exists=true;
                public var wasAliveWhenDestroyed=true;
                public var isSustainNote=false;
                public var prevNote:NoteStub;
                public var sustainHead:NoteStub;
                public var sustainHeadCenterX:Null<Float>;
                public var width:Float=112;
                public var origin:Dynamic={x:0.0};
                public var offset:Dynamic={x:0.0,y:0.0};
                public var scale:Dynamic={y:1.0};
                public function new(time:Float) { strumTime=time; prevNote=this; }
                public function kill():Void { alive=false; exists=false; }
                public function destroy():Void {
                    wasAliveWhenDestroyed=alive;
                    destroyed=true;
                    scale=null;
                    exists=false;
                }
                public function graphicCenterOffsetX():Float return width/2;
                __REPAIR_METHOD__
            }
            class NoteGroup {
                public var members:Array<NoteStub>=[];
                public function new(){}
                public function remove(note:NoteStub, splice:Bool):Void members.remove(note);
            }
            class SeekHost {
                public var startingSong=false;
                public var endingSong=false;
                public var songLength:Float=140000;
                public var songTime:Float=500;
                public var previousFrameTime=0;
                public var SONG={bpm:100.0};
                public var unspawnNotes:Array<NoteStub>=[];
                public var notes=new NoteGroup();
                public var songEvents:Array<Dynamic>=[];
                public var songEventIndex=1;
                public var replayed:Array<String>=[];
                public var compatEventVideo:Dynamic=null;
                public var curStep=0;
                public var curBeat=0;
                public var curSection=0;
                public var pausedVocals=0;
                public var resumedVocals=0;
                public var vocalClock:Float=500;
                public var vocalTracks:Dynamic=null;
                public var vocals:Dynamic={};
                public function new(){}
                function pauseVocals():Void pausedVocals++;
                function seekVocals(time:Float):Void vocalClock=time;
                function playVocals():Void resumedVocals++;
                function vocalTime():Float return vocalClock;
                function updateCurStep():Void curStep=Std.int(Conductor.songPosition/100);
                function getSection():Int return Std.int(curStep/16);
                function setAllHaxeVar(name:String,value:Dynamic):Void {}
                function syncPsychTimingGlobals():Void {}
                function syncLegacyKadeGlobals():Void {}
                function fireSongEvent(event:Dynamic):Void replayed.push(event.name);
                __SEEK_METHOD__
                __SKIP_METHOD__
            }'''.replace('__SEEK_METHOD__', seek_method).replace('__SKIP_METHOD__', method)
                .replace('__REPAIR_METHOD__', repair_method),
            'SkipIntegrationTest.hx': '''import SeekHost.NoteStub;
            class SkipIntegrationTest {
                static function check(ok:Bool,label:String):Void if(!ok) throw label;
                static function main():Void {
                    var host=new SeekHost();
                    var old=new NoteStub(5000), boundary=new NoteStub(20840), next=new NoteStub(20869);
                    var active=new NoteStub(10000);
                    host.unspawnNotes=[old,boundary,next];host.notes.members=[active];
                    host.songEvents=[
                        {time:0,name:"Play Video"}, {time:500,name:"Focus Camera"},
                        {time:19434,name:"Zoom Camera"}, {time:20000,name:"PlayVideo"},
                        {time:20769,name:"Flash"}, {time:20840,name:"At Boundary"}
                    ];
                    host.skipCompatEventVideoToEnd(0,20840);
                    check(Conductor.songPosition==20840 && FlxG.sound.music.time==20840
                        && host.vocalClock==20840, "audio clocks did not seek together");
                    check(old.destroyed && active.destroyed && !boundary.destroyed && !next.destroyed
                        && host.unspawnNotes.length==2 && host.notes.members.length==0,
                        "notes before endpoint were not retired exactly");
                    check(!old.wasAliveWhenDestroyed && !active.wasAliveWhenDestroyed
                        && !old.alive && !active.alive,
                        "seek destroyed notes before marking them dead for sustain references");
                    check(host.replayed.join(",")=="Focus Camera,Zoom Camera,Flash"
                        && host.songEventIndex==5, "crossed chart state was not replayed in order");
                    check(Conductor.bpm==150 && host.curStep==208 && host.curBeat==52
                        && host.curSection==13, "beat cursor or BPM remained before the seek");
                    check(host.pausedVocals==1 && host.resumedVocals==1,
                        "vocal seek should suspend and resume once");
                    check(RuntimeSmokeHarness.skip.from==500
                        && RuntimeSmokeHarness.skip.target==20840
                        && RuntimeSmokeHarness.skip.crossedEvents==4,
                        "native skip evidence did not match crossed chart state");
                    host.skipCompatEventVideoToEnd(0,20840);
                    check(host.replayed.length==3 && host.pausedVocals==1,
                        "repeat skip replayed events or audio");
                }
            }'''
        }
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            for name, text in files.items():
                (Path(folder) / name).write_text(text, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder,
                                     '-main', 'SkipIntegrationTest', '--interp'], cwd=ROOT,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
