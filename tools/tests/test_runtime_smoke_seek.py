from __future__ import annotations
from haxe_test_support import HAXE_COMMAND

import importlib.util
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"
RUNNER_PATH = ROOT / "tools" / "run_seek_smoke.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("runtime_smoke_seek", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load the native seek smoke runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.path.insert(0, str(RUNNER_PATH.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def extract_haxe_method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated Haxe method: {marker}")


def valid_marker() -> dict:
    return {
        "event": "seek_complete",
        "eventVideoActive": False,
        "hasVocals": True,
        "sourceNeedsVoices": True,
        "fromMs": 2050,
        "targetMs": 10000,
        "musicTimeBeforeMs": 2100,
        "musicTimeMs": 10000,
        "vocalTimeMs": 10000,
        "conductorPositionMs": 10000,
        "conductorLastPositionMs": 10000,
        "songTimeMs": 10000,
        "eventIndexBefore": 2,
        "eventIndexAfter": 5,
        "totalEvents": 7,
        "crossedEvents": 3,
        "firedEvents": 2,
        "skippedVideoEvents": 1,
        "removedUnspawnNotes": 1,
        "removedActiveNotes": 1,
        "discardedNotes": 2,
        "staleUnspawnNotes": 0,
        "staleActiveNotes": 0,
        "remainingNotes": 2,
        "firstRemainingNoteMs": 10000,
        "curStep": 100,
        "curBeat": 25,
        "curSection": 6,
        "bpm": 150,
    }


class RuntimeSmokeSeekTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = load_runner()
        cls.play_state = (ROOT / "source" / "PlayState.hx").read_text()

    def test_marker_validator_accepts_resynchronized_general_seek(self):
        problems, snapshot = self.runner.validate_seek_markers(
            [{"event": "song_start", "musicPlaying": True}, valid_marker(),
             {"event": "success"}],
            after_ms=2000,
            target_ms=10000,
        )
        self.assertEqual(problems, [])
        self.assertEqual(snapshot["eventIndexAfter"], 5)

    def test_marker_validator_requires_song_start_before_seek(self):
        problems, _ = self.runner.validate_seek_markers(
            [valid_marker(), {"event": "song_start", "musicPlaying": True}], 2000, 10000
        )
        self.assertIn("seek_complete marker preceded song_start", problems)

    def test_instrumental_only_seek_checks_nonvocal_clocks_and_rejects_leakage(self):
        marker = valid_marker()
        marker["sourceNeedsVoices"] = False
        marker["vocalTimeMs"] = None
        markers = [{"event": "song_start", "musicPlaying": True}, marker]
        problems, _ = self.runner.validate_seek_markers(
            markers, 2000, 10000, expect_vocals=False
        )
        self.assertEqual(problems, [])

        marker["conductorPositionMs"] = 9000
        marker["sourceNeedsVoices"] = True
        problems, _ = self.runner.validate_seek_markers(
            markers, 2000, 10000, expect_vocals=False
        )
        self.assertTrue(any("source chart still requests vocals" in item for item in problems))
        self.assertTrue(any("conductorPositionMs did not resynchronize" in item
                            for item in problems))

    def test_vocal_seek_rejects_silent_placeholder_for_instrumental_chart(self):
        marker = valid_marker()
        marker["sourceNeedsVoices"] = False
        problems, _ = self.runner.validate_seek_markers(
            [{"event": "song_start", "musicPlaying": True}, marker], 2000, 10000
        )
        self.assertIn("source chart does not request vocals", problems)

    def test_marker_validator_rejects_missing_or_duplicate_seek_evidence(self):
        problems, _ = self.runner.validate_seek_markers([], 2000, 10000)
        self.assertIn("expected one seek_complete marker, found 0", problems)
        problems, _ = self.runner.validate_seek_markers(
            [valid_marker(), valid_marker()], 2000, 10000
        )
        self.assertIn("expected one seek_complete marker, found 2", problems)

    def test_marker_validator_rejects_clock_event_and_note_drift(self):
        marker = valid_marker()
        marker["eventVideoActive"] = True
        marker["hasVocals"] = False
        marker["vocalTimeMs"] = 9500
        marker["eventIndexAfter"] = 6
        marker["crossedEvents"] = 2
        marker["discardedNotes"] = 0
        marker["staleActiveNotes"] = 1
        marker["firstRemainingNoteMs"] = 9000
        problems, _ = self.runner.validate_seek_markers([marker], 2000, 10000)
        for expected in (
            "no event video was active",
            "did not expose a vocal track",
            "vocalTimeMs did not resynchronize",
            "event cursor delta does not match crossedEvents",
            "crossed events do not reconcile",
            "discardedNotes does not match",
            "notes earlier than the landing time remain active",
            "first remaining note is earlier",
        ):
            self.assertTrue(any(expected in problem for problem in problems), expected)

    def test_smoke_seek_is_an_explicit_no_video_forward_path(self):
        method = extract_haxe_method(
            self.play_state, "@:keep public function seekForwardForSmoke(target:Float):Dynamic"
        )
        self.assertIn("RuntimeSmokeHarness.enabled()", method)
        self.assertIn("compatEventVideo != null", method)
        self.assertIn("target <= Conductor.songPosition", method)
        self.assertIn("eventVideoActive: compatEventVideo != null", self.play_state)
        self.assertIn("hasVocals: vocalTracks != null || vocals != null", self.play_state)
        self.assertIn("sourceNeedsVoices: SONG != null && Reflect.field(SONG, 'needsVoices') == true", self.play_state)

    @unittest.skipUnless(HAXE.is_file(), "portable Haxe is unavailable")
    def test_production_seek_helper_resynchronizes_clocks_events_and_notes(self):
        seek_method = extract_haxe_method(
            self.play_state,
            "function seekForwardSongTime(target:Float, captureSmokeState:Bool):Dynamic",
        )
        smoke_method = extract_haxe_method(
            self.play_state, "@:keep public function seekForwardForSmoke(target:Float):Dynamic"
        )
        note_source = (ROOT / "source" / "Note.hx").read_text()
        repair_method = extract_haxe_method(
            note_source, "public function repairSustainChainAfterSeek():Void"
        )
        self.assertIn("note.repairSustainChainAfterSeek();", seek_method)
        self.assertIn("daNote.prevNote.wasGoodHit && !daNote.canBeHit", self.play_state)
        self.assertIn("daNote.prevNote.alive && daNote.prevNote.isSustainNote", self.play_state)
        fixture = {
            "Conductor.hx": """class Conductor {
  public static var songPosition:Float = 1800;
  public static var lastSongPos:Float = 1800;
  public static var bpm:Float = 100;
  public static var bpmChangeMap:Array<Dynamic> = [{songTime:5000.0,bpm:150.0}];
  public static function changeBPM(value:Float):Void bpm = value;
}
""",
            "FlxG.hx": """class FlxG {
  public static var sound = {music:new MockMusic()};
  public static var game = {ticks:777};
}
class MockMusic {public var time:Float=2100;public function new(){}}
""",
            "RuntimeSmokeHarness.hx": """class RuntimeSmokeHarness {
  public static function enabled():Bool return true;
  public static var marker:Dynamic;
  public static function markSeekComplete(snapshot:Dynamic):Void marker=snapshot;
}
""",
            "EngineCompat.hx": """class EngineCompat {
  public static function eventName(name:String):String
    return name == "PlayVideo" ? "Play Video" : name;
}
""",
            "SeekHost.hx": """class NoteStub {
  public var strumTime:Float;
  public var destroyed:Bool=false;
  public var wasAliveWhenDestroyed:Bool=true;
  public var alive:Bool=true;
  public var exists:Bool=true;
  public var isSustainNote:Bool=false;
  public var wasGoodHit:Bool=false;
  public var canBeHit:Bool=false;
  public var normalSize:Float=0.7;
  public var height:Float=112;
  public var width:Float=112;
  public var prevNote:NoteStub;
  public var sustainHead:NoteStub;
  public var sustainHeadCenterX:Null<Float>;
  public var origin:Dynamic={x:0.0};
  public var offset:Dynamic={x:0.0,y:0.0};
  public var scale:Dynamic={x:1.0,y:1.0};
  public var animation:Dynamic={};
  public function new(time:Float) { strumTime=time; prevNote=this; }
  public function kill():Void { alive=false; exists=false; }
  public function destroy():Void {
    wasAliveWhenDestroyed=alive;
    destroyed=true;
    exists=false;
    origin=null; offset=null; scale=null; animation=null;
  }
  public function graphicCenterOffsetX():Float return width/2;
  public function exerciseDefaultUpscrollPredecessorReads():Void {
    if (!isSustainNote) return;
    // These mirror the default-upscroll and snap-to-strumline paths that
    // inspect prevNote on the first gameplay frame after a seek.
    var shouldClip=wasGoodHit || prevNote.wasGoodHit && !canBeHit;
    if (shouldClip && prevNote.alive && prevNote.isSustainNote)
      prevNote.scale.y=prevNote.normalSize;
  }
  __REPAIR_METHOD__
}
class NoteGroup {
  public var members:Array<NoteStub>=[];
  public function new(){}
  public function remove(note:NoteStub, splice:Bool):Void members.remove(note);
}
class SeekHost {
  public var startingSong:Bool=false;
  public var endingSong:Bool=false;
  public var compatEventVideo:Dynamic=null;
  public var songLength:Float=60000;
  public var songTime:Float=1800;
  public var previousFrameTime:Float=0;
  public var SONG={bpm:100.0, needsVoices:true};
  public var unspawnNotes:Array<NoteStub>=[];
  public var notes:NoteGroup=new NoteGroup();
  public var songEvents:Array<Dynamic>=[];
  public var songEventIndex:Int=1;
  public var replayed:Array<String>=[];
  public var curStep:Int=0;
  public var curBeat:Int=0;
  public var curSection:Int=0;
  public var pausedVocals:Int=0;
  public var resumedVocals:Int=0;
  public var vocalClock:Float=2100;
  public var vocalTracks:Dynamic=null;
  public var vocals:Dynamic={};
  public var psychSynced:Bool=false;
  public var legacySynced:Bool=false;
  public function new(){}
  function pauseVocals():Void pausedVocals++;
  function seekVocals(time:Float):Void vocalClock=time;
  function playVocals():Void resumedVocals++;
  function vocalTime():Float return vocalClock;
  function updateCurStep():Void curStep=Std.int(Conductor.songPosition/100);
  function getSection():Int return Std.int(curStep/16);
  function setAllHaxeVar(name:String,value:Dynamic):Void {}
  function syncPsychTimingGlobals():Void psychSynced=true;
  function syncLegacyKadeGlobals():Void legacySynced=true;
  function fireSongEvent(event:Dynamic):Void replayed.push(event.name);
  // The seek fixture has no field-backed notes to remove from an NV owner.
  function nightmareVisionRemoveFieldNoteMembership(_note:NoteStub):Void {}
  __SEEK_METHOD__
  __SMOKE_METHOD__
}
""".replace("__SEEK_METHOD__", seek_method).replace("__SMOKE_METHOD__", smoke_method)
            .replace("__REPAIR_METHOD__", repair_method),
            "SeekIntegrationTest.hx": """import SeekHost.NoteStub;
class SeekIntegrationTest {
  static function check(ok:Bool,label:String):Void if(!ok) throw label;
  static function main():Void {
    var host=new SeekHost();
    var staleUnspawn=new NoteStub(8000), boundaryUnspawn=new NoteStub(10000);
    var futureUnspawn=new NoteStub(11000), staleActive=new NoteStub(9000);
    var boundaryActive=new NoteStub(10000);
    boundaryUnspawn.isSustainNote=true;
    boundaryUnspawn.prevNote=staleUnspawn;
    boundaryUnspawn.sustainHead=staleUnspawn;
    boundaryUnspawn.sustainHeadCenterX=71;
    futureUnspawn.isSustainNote=true;
    futureUnspawn.prevNote=boundaryUnspawn;
    futureUnspawn.sustainHead=staleUnspawn;
    futureUnspawn.sustainHeadCenterX=71;
    host.unspawnNotes=[staleUnspawn,boundaryUnspawn,futureUnspawn];
    host.notes.members=[staleActive,boundaryActive];
    host.songEvents=[
      {time:1500,name:"Already handled"},
      {time:4000,name:"Focus Camera"},
      {time:7000,name:"Play Video"},
      {time:9000,name:"Flash"},
      {time:10000,name:"At Boundary"}
    ];
    var snapshot=host.seekForwardForSmoke(10000);
    check(snapshot!=null,"valid forward seek was rejected");
    check(Conductor.songPosition==10000 && Conductor.lastSongPos==10000
      && FlxG.sound.music.time==10000 && host.vocalClock==10000 && host.songTime==10000,
      "instrumental, vocal, Conductor, or song clocks did not resynchronize");
    check(snapshot.eventVideoActive==false && snapshot.hasVocals==true,
      "seek did not prove no active video and an available vocal track");
    check(staleUnspawn.destroyed && staleActive.destroyed
      && !boundaryUnspawn.destroyed && !boundaryActive.destroyed && !futureUnspawn.destroyed,
      "seek did not retire only notes before the landing time");
    check(!staleUnspawn.wasAliveWhenDestroyed && !staleActive.wasAliveWhenDestroyed,
      "seek destroyed notes before marking them dead");
    check(boundaryUnspawn.prevNote==boundaryUnspawn && boundaryUnspawn.sustainHead==null
      && boundaryUnspawn.sustainHeadCenterX==71
      && futureUnspawn.prevNote==boundaryUnspawn && futureUnspawn.sustainHead==null,
      "surviving sustains retained a retired predecessor/head or lost their cached anchor");
    boundaryUnspawn.exerciseDefaultUpscrollPredecessorReads();
    futureUnspawn.exerciseDefaultUpscrollPredecessorReads();
    check(boundaryUnspawn.scale!=null && futureUnspawn.scale!=null,
      "post-seek default-upscroll predecessor reads touched destroyed note fields");
    check(snapshot.discardedNotes==2 && snapshot.staleUnspawnNotes==0
      && snapshot.staleActiveNotes==0 && snapshot.remainingNotes==3
      && snapshot.firstRemainingNoteMs==10000,
      "note retirement snapshot is inconsistent");
    check(host.replayed.join(",")=="Focus Camera,Flash" && host.songEventIndex==4
      && snapshot.crossedEvents==3 && snapshot.firedEvents==2
      && snapshot.skippedVideoEvents==1,
      "seek did not replay crossed events while excluding Play Video");
    check(Conductor.bpm==150 && host.curStep==100 && host.curBeat==25
      && host.curSection==6 && host.psychSynced && host.legacySynced,
      "BPM or timing globals did not update at the landing point");
    check(host.pausedVocals==1 && host.resumedVocals==1,
      "vocal track was not paused, sought, and resumed exactly once");

    var blocked=new SeekHost();
    blocked.compatEventVideo={};
    var beforeMusic=FlxG.sound.music.time;
    check(blocked.seekForwardForSmoke(12000)==null
      && FlxG.sound.music.time==beforeMusic && blocked.songEventIndex==1,
      "smoke seek ran while an event video was active");
  }
}
""",
        }
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            for name, contents in fixture.items():
                (Path(folder) / name).write_text(contents, encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "SeekIntegrationTest", "--interp"],
                cwd=folder,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
