"""Pin NV input-event timing and the host's per-frame input drain route."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_source_input_lifecycle import extract_method


ROOT = Path(__file__).resolve().parents[2]


FIXTURE = r'''class Note {
 public var noteData:Int;
 public var alive:Bool=true;
 public var canBeHit:Bool=true;
 public var tooLate:Bool=false;
 public var wasGoodHit:Bool=false;
 public var isSustainNote:Bool=false;
 public var hitPriority:Int=1;
 public var strumTime:Float=0;
 public var sourcePlayfieldIndex:Int=0;
 public function new(noteData:Int, strumTime:Float=0) {
  this.noteData=noteData; this.strumTime=strumTime;
 }
}
class NoteGroup { public var members:Array<Note>=[]; public function new() {} }
class NightmareVisionInputEvent {
 public var noteData:Int;
 public var timer:Float;
 public function new(noteData:Int, timer:Float) { this.noteData=noteData; this.timer=timer; }
}
class InputMissPressSignal {
 public var dispatches:Int=0;
 public function new() {}
 public function dispatch(_key:Int):Void dispatches++;
}
class InputFixtureReceptor {
 public var ID:Int;
 public var animation:Dynamic={curAnim:{name:'static'}};
 public var resetAnim:Float=0;
 public var holding:Bool=false;
 public function new(ID:Int) this.ID=ID;
 public function playAnim(name:String, ?force:Bool):Void animation.curAnim.name=name;
}
class InputFixtureStrumline {
 public var members:Array<InputFixtureReceptor>=[];
 public function new() for (id in 0...4) members.push(new InputFixtureReceptor(id));
 public function forEachReceptor(callback:InputFixtureReceptor->Void):Void
  for (receptor in members) callback(receptor);
}
class InputField {
 public var ID:Int;
 public var input:Bool=true;
 public var playAnims:Bool=true;
 public var strumline:InputFixtureStrumline=new InputFixtureStrumline();
 public var onMissPress:InputMissPressSignal=new InputMissPressSignal();
 public function new(ID:Int) this.ID=ID;
 public function canInput():Bool return input;
}
class InputPrefsView { public var ghostTapping:Bool=true; public function new() {} }
class InputPrefs { public var view:InputPrefsView=new InputPrefsView(); public function new() {} }

class InputFixture {
 public var events:Array<String>=[];
 public var nightmareVisionLegacyFieldCameras=false;
 public function broadcastHistoricalNightmareScripts(n:String,a:Array<Dynamic>):Dynamic return callNightmareVision(n,a);
 public function nightmareVisionLegacyNoteMissPress(k:Int):Void {events.push('legacyMiss:'+k);broadcastHistoricalNightmareScripts('noteMissPress',[k]);}
 public var callbackTimes:Map<String,Array<Float>>=new Map();
 public var notes:NoteGroup=new NoteGroup();
 public var nightmareVisionFields:Array<InputField>=[];
 public var nightmareVisionNoteFields:haxe.ds.ObjectMap<Note,InputField>=new haxe.ds.ObjectMap();
 public var nightmareVisionCurrentInputEvent:NightmareVisionInputEvent=null;
 public var nightmareVisionPrefs:InputPrefs=new InputPrefs();
 public var startedCountdown:Bool=true;
 public var demoMode:Bool=false;
 public var paused:Bool=false;
 public var generatedMusic:Bool=true;
 public var endingSong:Bool=false;
 public var disableKeys:Bool=false;
 public var compatEventVideoControlsDisabled:Bool=false;
 public var hxcVideoControlsDisabled:Bool=false;
 public var strumsBlocked:Array<Bool>=[false,false,false,false];
 public var hits:Array<Note>=[];
 public var hitTimes:Array<Float>=[];
 public var hitSides:Array<Bool>=[];
 public var throwOnHit:Bool=false;
 public var nestedEvent:NightmareVisionInputEvent=null;
 public var nesting:Bool=false;
 public var nestedRestoredEvent:Bool=false;
 public var nestedRestoredTime:Float=Math.NaN;
 var playerStrums:InputFixtureStrumline=new InputFixtureStrumline();
 var enemyStrums:InputFixtureStrumline=new InputFixtureStrumline();

 public function new() {
  nightmareVisionFields=[new InputField(0),new InputField(1)];
 }
 public function getNightmareVisionField(id:Int):InputField {
  for (field in nightmareVisionFields) if (field != null && field.ID==id) return field;
  return id>=0 && id<nightmareVisionFields.length ? nightmareVisionFields[id] : null;
 }
 function getInputStrumline(_line:Dynamic, playerOne:Bool):InputFixtureStrumline
  return playerOne ? playerStrums : enemyStrums;
 __FIELD_FOR_NOTE__
 function goodNoteHit(note:Note, playerOne:Bool):Void {
  hits.push(note); hitTimes.push(Conductor.songPosition); hitSides.push(playerOne);
  note.wasGoodHit=true;
  if (throwOnHit) throw 'core hit failed';
 }
 function callNightmareVision(name:String, args:Array<Dynamic>):Dynamic {
  events.push(name);
  if (!callbackTimes.exists(name)) callbackTimes.set(name,[]);
  callbackTimes.get(name).push(Conductor.songPosition);
  if (name=='onGhostTap' && nestedEvent!=null && !nesting) {
   var previousEvent=nightmareVisionCurrentInputEvent;
   var previousTime=Conductor.songPosition;
   nesting=true;
   dispatchPress(nestedEvent);
   nesting=false;
   nestedRestoredEvent=nightmareVisionCurrentInputEvent==previousEvent;
   nestedRestoredTime=Conductor.songPosition;
  }
  return null;
 }
 public function dispatchPress(event:NightmareVisionInputEvent):Void onNightmareVisionInputPress(event);
 __PRESS_WRAPPER__
 __NV_PRESS__
 __RECEPTOR_HELPER__
}

class DrainCounter { public var count:Int=0; public function new() {} public function update():Void count++; }
class DrainScope { public var input:DrainCounter=new DrainCounter(); public function new() {} }
class InputDrainHost {
 public var nightmareVisionInputScope:DrainScope=new DrainScope();
 public var compatScriptClock:CompatScriptClock=new CompatScriptClock();
 public var paused:Bool=false;
 public var sourceTicks:Int=0;
 public function new() {}
 public function update(elapsed:Float):Void {
  var sourceBatch=compatScriptClock.advance(paused ? 0 : elapsed);
  sourceBatch.dispatchUpdate(function(_,_) sourceTicks++);
  __INPUT_DRAIN__
 }
}

class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function eq(actual:Dynamic,expected:Dynamic,message:String):Void
  if(actual!=expected) throw message+': expected '+expected+', got '+actual;
 static function note(host:InputFixture,key:Int,time:Float,field:Int=0):Note {
  var value=new Note(key,time); value.sourcePlayfieldIndex=field;
  host.notes.members.push(value);
  host.nightmareVisionNoteFields.set(value,host.nightmareVisionFields[field]);
  return value;
 }
 static function timeValues(host:InputFixture,name:String):Array<Float>
  return host.callbackTimes.exists(name) ? host.callbackTimes.get(name) : [];
 static function main():Void {
  // A raw Lime timestamp is reconciled with the live playing audio clock, and
  // the source callbacks observe the exact pre-dispatch Conductor position.
  var playing=new InputFixture();
  var timedNote=note(playing,0,9960);
  Conductor.songPosition=4200;
  FlxG.sound.music={playing:true,time:10000.0};
  lime.system.System.now=10350;
  playing.dispatchPress(new NightmareVisionInputEvent(0,10310));
  eq(playing.hitTimes[0],9960.0,'playing audio time minus raw event dispatch latency');
  eq(timeValues(playing,'onKeyPress')[0],4200.0,'onKeyPress sees restored Conductor position');
  eq(timeValues(playing,'onInputPress')[0],4200.0,'onInputPress sees restored Conductor position');
  eq(Conductor.songPosition,4200.0,'normal wrapper return restores Conductor position');
  eq(playing.nightmareVisionCurrentInputEvent,null,'normal wrapper return restores prior event');
  eq(playing.hits[0],timedNote,'playing-clock input selected the expected note');

  // Without playing audio, timestamp compensation starts at the existing
  // Conductor position rather than stale music time.
  var fallback=new InputFixture();
  note(fallback,0,5970);
  Conductor.songPosition=6000;
  FlxG.sound.music={playing:false,time:30000.0};
  lime.system.System.now=50050;
  fallback.dispatchPress(new NightmareVisionInputEvent(0,50020));
  eq(fallback.hitTimes[0],5970.0,'stopped audio falls back to Conductor plus raw event latency');
  eq(timeValues(fallback,'onKeyPress')[0],6000.0,'fallback source callback sees restored position');
  eq(Conductor.songPosition,6000.0,'fallback wrapper restores Conductor');

  // Nested input must temporarily replace, then restore, the outer raw event
  // and its compensated Conductor position before returning to the outer edge.
  var nested=new InputFixture(); nested.nightmareVisionPrefs.view.ghostTapping=true;
  note(nested,1,19950);
  Conductor.songPosition=5000;
  FlxG.sound.music={playing:true,time:20000.0};
  lime.system.System.now=20200;
  var outerEvent=new NightmareVisionInputEvent(0,20100);
  nested.nestedEvent=new NightmareVisionInputEvent(1,20150);
  nested.dispatchPress(outerEvent);
  eq(nested.hitTimes.length,1,'nested input judged its own eligible note once');
  eq(nested.hitTimes[0],19950.0,'nested raw event used its own latency-adjusted timestamp');
  check(nested.nestedRestoredEvent,'nested wrapper did not restore the outer input event');
  eq(nested.nestedRestoredTime,19900.0,'nested wrapper did not restore the outer event time');
  eq(timeValues(nested,'onKeyPress').join(','),'19900,5000',
   'nested and outer onKeyPress callbacks saw their respective restored positions');
  eq(timeValues(nested,'onInputPress').join(','),'19900,5000',
   'nested and outer onInputPress callbacks saw their respective restored positions');
  eq(Conductor.songPosition,5000.0,'outer wrapper restored Conductor after nested dispatch');
  eq(nested.nightmareVisionCurrentInputEvent,null,'outer wrapper restored the original event');

  // If note processing throws before its local restore, the wrapper still
  // restores both the previous event and previous Conductor value.
  var failing=new InputFixture(); note(failing,2,9980); failing.throwOnHit=true;
  var priorEvent=new NightmareVisionInputEvent(3,1);
  failing.nightmareVisionCurrentInputEvent=priorEvent;
  Conductor.songPosition=7000;
  FlxG.sound.music={playing:true,time:10000.0};
  lime.system.System.now=10100;
  var coreError='';
  try failing.dispatchPress(new NightmareVisionInputEvent(2,10080))
  catch (error:Dynamic) coreError=Std.string(error);
  eq(coreError,'core hit failed','wrapper changed the core input exception');
  eq(Conductor.songPosition,7000.0,'wrapper exception path did not restore Conductor');
  eq(failing.nightmareVisionCurrentInputEvent,priorEvent,
   'wrapper exception path did not restore the previous raw event');

  // Demo and paused edges skip judgement, ghost signals and event-time shifts,
  // while still notifying source key hooks at the restored host position.
  for (gate in [{name:'demo',demo:true,paused:false},{name:'paused',demo:false,paused:true}]) {
   var gated=new InputFixture(); note(gated,0,1);
   gated.demoMode=gate.demo; gated.paused=gate.paused;
   Conductor.songPosition=777;
   FlxG.sound.music={playing:true,time:90000.0};
   lime.system.System.now=90100;
   gated.dispatchPress(new NightmareVisionInputEvent(0,90000));
   eq(gated.hits.length,0,gate.name+' input must not judge notes');
   eq(gated.events.join(','),'onKeyPress,onInputPress',
    gate.name+' input must suppress gameplay hooks but preserve edge notifications');
   eq(timeValues(gated,'onKeyPress')[0],777.0,gate.name+' onKeyPress position');
   eq(timeValues(gated,'onInputPress')[0],777.0,gate.name+' onInputPress position');
   eq(Conductor.songPosition,777.0,gate.name+' position restoration');
   eq(gated.nightmareVisionFields[0].onMissPress.dispatches,0,gate.name+' field miss signal');
  }

  // A multi-field ghost emits the global hook once. With one enabled field,
  // its field-local miss signal is dispatched once and the other field is quiet.
  var ghost=new InputFixture(); ghost.nightmareVisionPrefs.view.ghostTapping=true;
  Conductor.songPosition=55; FlxG.sound.music={playing:false,time:99};
  lime.system.System.now=10; ghost.dispatchPress(new NightmareVisionInputEvent(0,10));
  eq(ghost.events.filter(function(name) return name=='onGhostTap').length,1,
   'multiple active fields emitted duplicate global ghost callbacks');
  eq(ghost.nightmareVisionFields[0].onMissPress.dispatches,0,
   'enabled ghost tapping dispatched a field miss signal');

  var oneField=new InputFixture(); oneField.nightmareVisionPrefs.view.ghostTapping=false;
  oneField.nightmareVisionFields[1].input=false;
  Conductor.songPosition=55; lime.system.System.now=10;
  oneField.dispatchPress(new NightmareVisionInputEvent(0,10));
  eq(oneField.nightmareVisionFields[0].onMissPress.dispatches,1,
   'eligible field did not receive exactly one ghost miss signal');
  eq(oneField.nightmareVisionFields[1].onMissPress.dispatches,0,
   'inactive field received a ghost miss signal');
  eq(oneField.events.filter(function(name) return name=='noteMissPress').length,1,
   'single field ghost did not emit exactly one source miss callback');

  // Membership keeps an admitted note attached to the original field object
  // when mutable IDs shift the fallback lookup to another field.
  var membership=new InputFixture();
  var admitted=note(membership,0,0,0);
  membership.nightmareVisionFields[0].ID=1;
  membership.nightmareVisionFields[1].ID=0;
  eq(membership.getNightmareVisionField(0),membership.nightmareVisionFields[1],
   'fixture mutable-ID lookup did not shift');
  Conductor.songPosition=300; FlxG.sound.music={playing:false,time:0};
  lime.system.System.now=10;
  membership.dispatchPress(new NightmareVisionInputEvent(0,10));
  eq(membership.hits.length,1,'field membership lost the admitted note after ID mutation');
  eq(membership.hits[0],admitted,'source admission changed the note object');
  eq(membership.hitSides[0],false,
   'route selected the fallback ID field rather than the field object that admitted the note');

  // The real PlayState callsite appears once after its fixed-rate script batch.
  var drainHost=new InputDrainHost();
  for (_ in 0...8) drainHost.update(1.0/120.0);
  eq(drainHost.nightmareVisionInputScope.input.count,8,
   'raw input must drain once for every host update');
  eq(drainHost.sourceTicks,4,'fixed-rate script callbacks did not remain at 60 Hz');
  eq(drainHost.compatScriptClock.sourceHz,60,'source callback clock rate changed');
  drainHost.paused=true; drainHost.update(1.0/60.0);
  eq(drainHost.nightmareVisionInputScope.input.count,9,
   'paused host update failed to drain the live input queue once');
  eq(drainHost.sourceTicks,4,'paused source clock advanced while raw input drained');
  trace('NV_INPUT_CLOCK_ROUTE_OK');
 }
}'''


class NightmareVisionInputClockRouteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        cls.press_wrapper = extract_method(play, "function onNightmareVisionInputPress(")
        cls.nv_press = extract_method(play, "function nightmareVisionSourceKeyPressed(")
        cls.field_for_note = extract_method(play, "function nightmareVisionFieldForNote(").replace(
            "NightmareVisionPlayFieldView", "InputField"
        )
        cls.receptor_helper = extract_method(play, "function setSourceInputReceptor(")
        cls.update = extract_method(play, "override public function update(elapsed:Float)")
        marker = "if (nightmareVisionInputScope != null && nightmareVisionInputScope.input != null)"
        start = cls.update.index(marker)
        cls.input_drain = cls.update[start:cls.update.index(";", start) + 1]

    def test_raw_input_time_nested_restore_gates_membership_and_live_drain(self):
        self.assertEqual(self.update.count("nightmareVisionInputScope.input.update();"), 1,
                         "PlayState must drain its live input once per host update")
        clock_start = self.update.index("var sourceBatch = compatScriptClock.advance(paused ? 0 : elapsed);")
        dispatch_start = self.update.index("sourceBatch.dispatchUpdate(function", clock_start)
        dispatch_end = self.update.index("\n\t\t});", dispatch_start)
        input_start = self.update.index("nightmareVisionInputScope.input.update();")
        self.assertGreater(input_start, dispatch_end,
                           "live input drain must stay outside the 60 Hz callback batch")
        self.assertGreater(input_start, clock_start)

        fixture = (FIXTURE
                   .replace("__FIELD_FOR_NOTE__", self.field_for_note)
                   .replace("__PRESS_WRAPPER__", self.press_wrapper)
                   .replace("__NV_PRESS__", self.nv_press)
                   .replace("__RECEPTOR_HELPER__", self.receptor_helper.replace(
                       "Strumline.StrumNote", "InputFixtureReceptor"))
                   .replace("__INPUT_DRAIN__", self.input_drain)
                   .replace("Strumline.StrumNote", "InputFixtureReceptor"))
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            (work / "Conductor.hx").write_text(
                "class Conductor { public static var songPosition:Float=0; }", newline="\n")
            (work / "FlxG.hx").write_text(
                "class FlxG { public static var sound:Dynamic={music:null}; }", newline="\n")
            (work / "SourceInputNotes.hx").write_text(
                (ROOT / "source/SourceInputNotes.hx").read_text(encoding="utf-8"), newline="\n")
            for name in ("CompatScriptClock.hx", "CompatScriptTickBatch.hx"):
                (work / name).write_text(
                    (ROOT / "source" / name).read_text(encoding="utf-8"), newline="\n")
            (work / "lime/system").mkdir(parents=True)
            (work / "lime/system/System.hx").write_text(
                "package lime.system; class System { public static var now:Float=0; "
                "public static function getTimer():Float return now; }", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("NV_INPUT_CLOCK_ROUTE_OK", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
