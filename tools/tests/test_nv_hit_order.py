"""Behavioral regression coverage for Nightmare Vision's successful-hit order.

The final fixture extracts the host's source hit methods and supplies only the
gameplay objects/signals they call. The host orchestration is therefore the
code under test; the fixture records its phase effects.
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
import re

from haxe_test_support import HAXE_COMMAND, FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"


def extract_method(source: str, marker: str) -> str:
    """Extract one Haxe method, ignoring braces in comments and strings."""
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    quote = None
    escaped = False
    line_comment = False
    block_comment = False
    index = brace
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and following == "/":
                block_comment = False
                index += 1
        elif quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char == "/" and following == "/":
            line_comment = True
            index += 1
        elif char == "/" and following == "*":
            block_comment = True
            index += 1
        elif char in ("'", '"'):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
        index += 1
    raise AssertionError(f"Unclosed Haxe method: {marker}")


class NightmareVisionHitOrderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.play = (ROOT / "source" / "PlayState.hx").read_text(encoding="utf-8")
        cls.note_types = (ROOT / "source" / "NightmareVisionNoteTypeRuntime.hx").read_text(
            encoding="utf-8"
        )
        cls.note = (ROOT / "source" / "Note.hx").read_text(encoding="utf-8")

    def require_hit_pipeline(self) -> str:
        marker = "function hitNightmareVisionNote("
        if marker not in self.play:
            self.skipTest("shared NV hit pipeline is being added by the production owner")
        return extract_method(self.play, marker)

    def compile_haxe(self, source: str) -> None:
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(source, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "--main", "Main", "--interp"],
                cwd=work,
                capture_output=True,
                text=True,
                timeout=45,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_nv_note_render_updates_do_not_preempt_source_auto_admission(self):
        update_auto_hit = extract_method(self.note, "public function updateAutoHit(songPosition:Float):Void")
        fixture = r'''
class Note {
 public var nightmareVisionTypeRuntime:Dynamic;
 public var autoHitSuppressed:Bool = false;
 public var wasGoodHit:Bool = false;
 public var canBeHit:Bool = true;
 public var strumTime:Float = 10;
 public function new(runtime:Dynamic) nightmareVisionTypeRuntime = runtime;
 public function isAutoPlayed():Bool return true;
 public function canAutoHit():Bool return true;
 __NOTE_UPDATE_AUTO_HIT__
}
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var nv = new Note({});
  for (_ in 0...10000) nv.updateAutoHit(20);
  check(!nv.wasGoodHit && nv.canBeHit,
   'NV rendering marked the note hit before PlayState source-clock admission');

  var native = new Note(null);
  native.updateAutoHit(20);
  check(native.wasGoodHit && !native.canBeHit,
   'native automatic note update changed while adding the NV source-clock gate');
 }
}
'''.replace("__NOTE_UPDATE_AUTO_HIT__", update_auto_hit)
        self.compile_haxe(fixture)

    def test_nv_popup_fresh_judgement_preserves_hit_callback_rating(self):
        popup = extract_method(self.play, "private function popUpScore(")
        judge = extract_method(self.play, "function judgeSourceNote(")
        self.assertIn("judgeSourceNote(daNote, !sourceScoreNightmare)", popup)
        self.assertIn("daRating = sourceLedger ? sourceRating.name : daNote.rating", popup)
        fixture = r'''
class Note {
 public var strumTime:Float = 100;
 public var rating:Dynamic = 'authored';
 public var ratingMod:Float = 1;
 public function new() {}
}
class SourceRating {
 public var name:String = 'fresh-judgement';
 public var ratingMod:Float = 1;
 public function new() {}
 public static function judge(data:Dynamic, diff:Float):SourceRating return new SourceRating();
}
class SourceNoteTiming {
 public static function ratingDiff(strumTime:Float, position:Float, offset:Float, rate:Float):Float
  return Math.abs(strumTime - position);
}
class Prefs { public var view:Dynamic = {ratingOffset:0}; public function new() {} }
class PsychClientPrefsCompat { public static var data:Dynamic = {ratingOffset:0}; }
class Conductor { public static var songPosition:Float = 100; }
class Main {
 public var sourceScoreNightmare:Bool = true;
 public var nightmareVisionPrefs:Prefs = new Prefs();
 public var ratingsData:Dynamic = {};
 public var playbackRate:Float = 1;
 public function new() {}
 __JUDGE__
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var host = new Main();
  var note = new Note();
  var fresh = host.judgeSourceNote(note, !host.sourceScoreNightmare);
  check(fresh.name == 'fresh-judgement' && note.rating == 'authored',
   'NV popup judgement overwrote the rating already observed by hit callbacks');
 }
}
'''.replace("__JUDGE__", judge)
        self.compile_haxe(fixture)

    def test_source_hit_pipeline_and_auto_cadence(self):
        hit = extract_method(self.play, "function hitNightmareVisionNote(")
        pre = extract_method(self.play, "function dispatchNightmareVisionNoteHitPre(")
        dispatch = extract_method(self.play, "function dispatchNightmareVisionNoteHit(note:Note,")
        detach = extract_method(self.play, "function detachNightmareVisionTap(")
        auto_loop = extract_method(self.play, "function processNightmareVisionAutoHits(")
        fixture = r'''
class Note {
 public static inline var NOTE_AMOUNT:Int = 4;
 public var id:Int;
 public var events:Array<String>;
 public var alive:Bool = true;
 public var destroyed:Bool = false;
 public var wasGoodHit:Bool = false;
 public var nightmareVisionHitDispatched:Bool = false;
 public var tooLate:Bool = false;
 public var sourcePlayfieldIndex:Int = 0;
 public var sourcePlayfieldPlayerControlled:Bool = false;
 public var sourcePlayfieldAutoPlay:Bool = false;
 public var autoHitSuppressed:Bool = false;
 public var sourceDirection:Int = 0;
 public var noteData:Int = 0;
 public var noteType:String = 'before-type-hit';
 public var strumTime:Float = 0;
 public var ignoreNote:Bool = false;
 public var hitCausesMiss:Bool = false;
 public var canMiss:Bool = false;
 public var canBeHit:Bool = true;
 public var isSustainNote:Bool = false;
 public var nightmareVisionSustainEnd:Bool = false;
 public var nightmareVisionTailState:Dynamic;
 public var hitHealth:Dynamic = null;
 public var hitsoundDisabled:Bool = true;
 public var gfNote:Bool = false;
 public var owner:Dynamic;
 public var noAnimation:Bool = false;
 public var animSuffix:String = '';
 public var ratingMod:Float = 1;
 public var dontCountNote:Bool = false;
 public var noteHit:Dynamic;
 public var noteStrum:Dynamic;
 public var y:Float = 0;
 public var externalListeners:Int = 0;
 public var autoAttempts:Int = 0;
 public function new(id:Int, events:Array<String>) { this.id=id; this.events=events; }
 public function kill():Void { alive=false; events.push('kill'); }
 public function destroy():Void { destroyed=true; events.push('destroy'); }
}
class NoteGroup {
 public var members:Array<Note> = [];
 public function remove(note:Note, splice:Bool):Bool {
  events.push('remove'); return members.remove(note);
 }
 public var events:Array<String>;
 public function new(events:Array<String>) this.events=events;
}
class Strum {
 public var ID:Int;
 public var events:Array<String>;
 public var resetAnim:Float = 0;
 public var coyoteTime:Float = 0;
 public var _lastNote:Note;
 public var lastNote(get,set):Note;
 public function new(id:Int, events:Array<String>) { ID=id; this.events=events; }
 function get_lastNote():Note return _lastNote;
 function set_lastNote(value:Note):Note { _lastNote=value; events.push('receptor:' + ID); return value; }
 public function playConfirm(sustain:Bool, reset:Bool):Void events.push('confirm:' + ID);
}
class Strumline {
 public var members:Array<Strum>;
 public function new(strums:Array<Strum>) members=strums;
}
class NightmareVisionPlayFieldView {
 public var ID:Int;
 public var inControl:Bool = true;
 public var playerControls:Bool;
 public var autoPlayed:Bool = false;
 public var playAnims:Bool = true;
 public var showRatings:Bool = true;
 public var noteSplashes:Bool = true;
 public var holdDropLeniency:Float = 0.2;
 public var singers:Array<Dynamic> = [];
 public function new(id:Int, playerControls:Bool) { ID=id; this.playerControls=playerControls; }
}
class Scripts {
 public var events:Array<String>;
 public var preResult:Dynamic = 'NV_STOP';
 public var globalResult:Dynamic = 'NV_STOP';
 public var before:Note->Int->Void;
 public function new(events:Array<String>) this.events=events;
 public function call(name:String, args:Array<Dynamic>, ?ignoreReturn:Bool, ?typeFilter:Array<String>):Dynamic {
  var note:Note = cast args[0];
  var id:Int = args.length > 1 ? cast args[1] : -1;
  if (StringTools.endsWith(name, 'Pre')) {
   events.push('pre:' + name + ':' + id);
   note.autoAttempts += 1;
   if (before != null) before(note, id);
   return preResult;
  }
  events.push('global:' + name + ':' + id + ':' + (typeFilter == null ? '' : typeFilter[0]));
  return globalResult;
 }
}
class NoteTypes {
 public var events:Array<String>;
 public var sideResult:Dynamic = 'NV_CONTINUE';
 public function new(events:Array<String>) this.events=events;
 public function hit(note:Note, id:Int):Dynamic {
  events.push('type-hit:' + id + ':' + note.noteType);
  note.noteType='after-type-hit';
  return 'NV_CONTINUE';
 }
 public function goodNoteHit(note:Note, id:Int):Dynamic { events.push('side-good:' + id + ':' + note.noteType); return sideResult; }
 public function opponentNoteHit(note:Note, id:Int):Dynamic { events.push('side-opponent:' + id); return sideResult; }
 public function extraNoteHit(note:Note, id:Int):Dynamic { events.push('side-extra:' + id); return sideResult; }
}
class NightmareVisionNoteTypeRuntime {
 public static function noteTypeOf(note:Dynamic):String return note == null ? '' : note.noteType;
}
class NightmareVisionScriptGroup {
 public static inline var STOP_FUNC:String = 'NV_STOP';
 public static inline var CONTINUE_FUNC:String = 'NV_CONTINUE';
}
class SourceHealthDelta {
 public static function hit(controlled:Bool, authored:Dynamic, base:Float, multiplier:Float,
  sustain:Bool, subdivisions:Int, guitarHero:Bool):Float return 0.125;
}
class OptionValues { public var hitSounds:Bool = false; public function new() {} }
class OptionsHandler { public static var options:OptionValues = new OptionValues(); }
class SoundApi {
 public var events:Array<String>;
 public function new() {}
 public function play(sound:Dynamic):Void if (events != null) events.push('hitsound');
}
class FlxG { public static var sound:SoundApi = new SoundApi(); }
class FNFAssets { public static function getSound(path:String):Dynamic return null; }
class Conductor { public static var songPosition:Float = 1; }
class Main {
 public var events:Array<String> = [];
 public var nightmareVisionScripts:Scripts;
 public var nightmareVisionNoteTypes:NoteTypes;
 public var sourceScoreNightmare:Bool = true;
 public var fields:Array<NightmareVisionPlayFieldView>;
 public var playerStrums:Strumline;
 public var enemyStrums:Strumline;
 public var notes:NoteGroup;
 public var generatedMusic:Bool = true;
 public var paused:Bool = false;
 public var endingSong:Bool = false;
 public var inCutscene:Bool = false;
 public var healthGain:Float = 1;
 public var healthGainMultiplier:Float = 1;
 public var holdSubdivisions:Int = 1;
 public var playbackRate:Float = 1;
 public var camZooming:Bool = false;
 public var downscroll:Bool = false;
 public var notesPassing:Int = 0;
 var _health:Float = 1;
 public var health(get,set):Float;
 function get_health():Float return _health;
 function set_health(value:Float):Float { _health=value; events.push('health'); return value; }
 public function new() {
  nightmareVisionScripts = new Scripts(events);
  nightmareVisionNoteTypes = new NoteTypes(events);
  fields = [new NightmareVisionPlayFieldView(0, true),
   new NightmareVisionPlayFieldView(1, false), new NightmareVisionPlayFieldView(2, false)];
  playerStrums = new Strumline([new Strum(0, events), new Strum(1, events)]);
  enemyStrums = new Strumline([new Strum(0, events), new Strum(1, events)]);
  notes = new NoteGroup(events);
  FlxG.sound.events = events;
 }
 function getNightmareVisionField(index:Int):NightmareVisionPlayFieldView return fields[index];
 function prepareNightmareVisionHitSingers(note:Note, field:NightmareVisionPlayFieldView, id:Int):Void
  events.push('singers');
 function prepareNightmareVisionHitSplash(note:Note, field:NightmareVisionPlayFieldView, id:Int):Void
  events.push('splash');
 function judgeSourceNote(note:Note):Void {
  if (!note.wasGoodHit) throw 'rating ran before accepted-hit flag';
  events.push('rating');
 }
 function dispatchHitCausesMiss(note:Note, playerOne:Bool):Bool { events.push('hazard-miss'); return true; }
 function finishNightmareVisionExternalHit(note:Note, playerOne:Bool,
  field:NightmareVisionPlayFieldView, fieldID:Int, accepted:Bool, autoAttempt:Bool):Void {
  if (accepted && !note.isSustainNote && (note.alive || notes.members.contains(note)))
   throw 'tap reached external listener before kill/remove';
  if (accepted && note.isSustainNote && (!note.alive || !notes.members.contains(note)))
   throw 'sustain was retired before external listener';
  note.externalListeners++;
  events.push('external:' + fieldID + ':' + field.playerControls + ':' + field.showRatings + ':' + accepted);
 }

__HIT_METHOD__
__PRE_METHOD__
__DISPATCH_METHOD__
__DETACH_METHOD__
__AUTO_LOOP__

 static function check(value:Bool, message:String):Void if (!value) throw message;
 function newNote(id:Int, fieldID:Int = 0):Note {
  var note = new Note(id, events); note.sourcePlayfieldIndex=fieldID;
  notes.members.push(note); return note;
 }
 function clearEvents():Void events.resize(0);
 function mainCases():Void {
  // Pre STOP is ignored. The ordinary route keeps phase order and executes
  // after global STOP; type-hit mutations are visible to side/global calls.
  var tap = newNote(10);
  hitNightmareVisionNote(tap, true);
  check(events.join('|') == 'pre:goodNoteHitPre:0|receptor:0|confirm:0|health|singers|rating|splash|type-hit:0:before-type-hit|side-good:0:after-type-hit|global:goodNoteHit:0:after-type-hit|kill|remove|external:0:true:true:true|destroy',
   'tap phase order/callback mutation/global return changed: ' + events.join('|'));
  check(tap.destroyed && !tap.alive && tap.nightmareVisionHitDispatched,
   'accepted tap did not finish retirement');

  var stopped = new Main();
  stopped.nightmareVisionNoteTypes.sideResult = NightmareVisionScriptGroup.STOP_FUNC;
  var stoppedTap = stopped.newNote(11);
  stopped.hitNightmareVisionNote(stoppedTap, true);
  check(!StringTools.contains(stopped.events.join('|'), 'global:') && stoppedTap.destroyed
   && stoppedTap.externalListeners == 1,
   'exact side STOP cancelled global only, or incorrectly cancelled host completion');

  var extra = new Main();
  var extraNote = extra.newNote(12, 2);
  extra.hitNightmareVisionNote(extraNote, false);
  var extraLog = extra.events.join('|');
  check(StringTools.contains(extraLog, 'pre:extraNoteHitPre:2')
   && StringTools.contains(extraLog, 'side-extra:2') && StringTools.contains(extraLog, 'global:extraNoteHit:2:after-type-hit')
   && !StringTools.contains(extraLog, 'health'),
   'field ID > 1 did not use the extra callback family without player health');

  var mutated = new Main();
  var mutatedNote = mutated.newNote(13);
  mutated.nightmareVisionScripts.before = function(note:Note, id:Int):Void {
   note.sourcePlayfieldIndex = 1;
   note.noteData = 1;
   mutated.fields[0].playerControls = false;
   mutated.fields[0].showRatings = false;
  };
  mutated.hitNightmareVisionNote(mutatedNote, true);
  var mutationLog = mutated.events.join('|');
  check(StringTools.contains(mutationLog, 'pre:goodNoteHitPre:0')
   && mutated.playerStrums.members[1].lastNote == mutatedNote
   && mutated.playerStrums.members[0].lastNote == null
   && mutated.enemyStrums.members[0].lastNote == null
   && mutated.enemyStrums.members[1].lastNote == null
   && StringTools.contains(mutationLog, 'side-good:0:after-type-hit')
   && StringTools.contains(mutationLog, 'global:goodNoteHit:0:after-type-hit')
   && StringTools.contains(mutationLog, 'external:0:false:false:true')
   && !StringTools.contains(mutationLog, 'health') && !StringTools.contains(mutationLog, 'rating'),
   'Pre mutation changed captured callback context or hid live field flags: ' + mutationLog);

  var badLane = new Main();
  var badLaneNote = badLane.newNote(17);
  badLane.nightmareVisionScripts.before = function(note:Note, id:Int):Void note.noteData = 9;
  badLane.hitNightmareVisionNote(badLaneNote, true);
  check(badLane.playerStrums.members[0].lastNote == null
   && badLane.events.indexOf('receptor:0') < 0
   && badLane.events.indexOf('confirm:0') < 0
   && badLaneNote.destroyed,
   'out-of-range live noteData should skip receptor bookkeeping without cancelling the hit');

  var hold = new Main();
  var sustain = hold.newNote(14);
  sustain.isSustainNote = true;
  hold.hitNightmareVisionNote(sustain, true, false, true);
  check(sustain.wasGoodHit && sustain.alive && !sustain.destroyed
   && hold.notes.members.contains(sustain)
   && hold.events.indexOf('kill') < 0 && hold.events.indexOf('remove') < 0,
   'successful sustain was detached or destroyed');

  // Automatic player-owned hazards and canMiss heads take the PlayField early
  // return before the donor hit-sound site, even when the option is enabled.
  OptionsHandler.options.hitSounds = true;
  var autoHazardHost = new Main();
  autoHazardHost.fields[0].autoPlayed = true;
  var autoHazard = autoHazardHost.newNote(15);
  autoHazard.hitCausesMiss = true;
  autoHazard.hitsoundDisabled = false;
  autoHazardHost.hitNightmareVisionNote(autoHazard, true, true);
  check(autoHazardHost.events.indexOf('hitsound') < 0
   && autoHazard.externalListeners == 1 && autoHazard.alive,
   'auto hazard played a hit sound before taking the source early return');

  var manualHazardHost = new Main();
  var manualHazard = manualHazardHost.newNote(16);
  manualHazard.hitCausesMiss = true;
  manualHazard.hitsoundDisabled = false;
  manualHazardHost.hitNightmareVisionNote(manualHazard, true);
  var soundIndex = manualHazardHost.events.indexOf('hitsound');
  var missIndex = manualHazardHost.events.indexOf('hazard-miss');
  check(soundIndex >= 0 && missIndex > soundIndex && manualHazard.destroyed,
   'manual hit-causes-miss did not play its enabled hit sound before miss handling');
  OptionsHandler.options.hitSounds = false;
 }
 static function autoCadence():Void {
  for (hz in [30, 60, 240, 1440, 5000]) {
   var host = new Main();
   OptionsHandler.options.hitSounds = true;
   host.fields[0].autoPlayed = true;
   var hazard = host.newNote(20); hazard.hitCausesMiss = true;
   hazard.hitsoundDisabled = false;
   var canMiss = host.newNote(21); canMiss.canMiss = true;
   canMiss.hitsoundDisabled = false;
   var head = host.newNote(22);
   var sustain = host.newNote(23); sustain.isSustainNote = true;
   var ignored = host.newNote(24); ignored.ignoreNote = true;
   var clock = new CompatScriptClock();
   for (_ in 0...hz) host.processNightmareVisionAutoHits(clock.advance(1.0 / hz));
   check(hazard.autoAttempts == 60 && hazard.externalListeners == 60
    && hazard.alive && !hazard.wasGoodHit && !hazard.nightmareVisionHitDispatched,
    'hazard attempts/listeners depended on render rate ' + hz);
   check(canMiss.autoAttempts == 60 && canMiss.externalListeners == 60
    && canMiss.alive && !canMiss.wasGoodHit,
    'canMiss attempts/listeners depended on render rate ' + hz);
   check(host.events.indexOf('hitsound') < 0,
    'auto hazard/canMiss route played a hit sound before its source early return');
   check(head.autoAttempts == 1 && head.externalListeners == 1
    && head.destroyed && !head.alive,
    'accepted tap was not one-shot after removal at render rate ' + hz);
   check(sustain.autoAttempts == 1 && sustain.externalListeners == 1
    && sustain.alive && sustain.wasGoodHit,
    'accepted sustain repeated or was retired at render rate ' + hz);
   check(ignored.autoAttempts == 0 && ignored.alive,
    'auto loop failed to preserve the source ignoreNote exclusion');
  }
  OptionsHandler.options.hitSounds = false;
 }
 static function main():Void { new Main().mainCases(); autoCadence(); }
}
'''.replace("__HIT_METHOD__", hit).replace("__PRE_METHOD__", pre)
        fixture = fixture.replace("__DISPATCH_METHOD__", dispatch).replace(
            "__DETACH_METHOD__", detach
        ).replace("__AUTO_LOOP__", auto_loop)
        # Source PlayState references Note.NOTE_AMOUNT when mapping flattened
        # field lanes. Keep the fixture's Note model local without loading the
        # full sprite class and its Flixel dependencies.
        fixture = re.sub(r"\bNote\b", "NVNote", fixture)
        self.compile_haxe(fixture)
