"""Execute PlayState's source miss router against small, observable host doubles."""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath


ROOT = Path(__file__).resolve().parents[2]
PSYCH_DONOR = FixturePath(
    "C:/Users/uwucammie/Documents/coding/FNF/fnf_sources/FNF-PsychEngine/source/states/PlayState.hx"
)
NV_DONOR = FixturePath(
    "C:/Users/uwucammie/Documents/coding/FNF/fnf_sources/NightmareVision/source/funkin/objects/note/PlayField.hx"
)


def extract_method(source: str, marker: str) -> str:
    """Extract a Haxe method while ignoring braces inside comments and strings."""
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    quote = None
    line_comment = False
    block_comment = False
    escaped = False
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
                return source[start : index + 1]
        index += 1
    raise AssertionError(f"unterminated Haxe method: {marker}")


class SourceMissLifecycleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        markers = (
            "function sourceNoteMiss(",
            "function sourceMissAnimation(",
            "function sourceMissPerformer(",
            "function setSourceVocalVolume(",
            "function applySourceMiss():Void",
            "function applySourceMissHealth(",
            "function refreshSourceAccuracy():Void",
            "function sourceMissCounts(",
        )
        cls.methods = "\n".join(
            extract_method(cls.play, marker).replace(marker, "public " + marker, 1)
            for marker in markers
        )

    def run_haxe(self, body: str) -> None:
        fixture = HAXE_FIXTURE.replace("__EXTRACTED_METHODS__", self.methods).replace(
            "__TEST_BODY__", body
        )
        with tempfile.TemporaryDirectory(prefix="source-miss-lifecycle-", dir=ROOT / "tmp") as folder:
            scratch = FixturePath(folder)
            (scratch / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(scratch), "--main", "Main", "--interp"],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_psych_instakill_and_miss_effects_keep_source_order(self):
        self.run_haxe(
            r'''
 static function main():Void {
  var host = new PlayState(false);
  var note = new Note();
  note.noteData = 2;
  note.strumTime = 100;
  note.animSuffix = '-alt';
  note.noteMiss = 'customMiss';
  host.notes.members = [note];
  host.instakillOnMiss = true;
  host.combo = 8;
  var hxcEvent = {eventCanceled:false, payload:'shared'};
  host.sourceNoteMiss(2, true, note, host.boyfriend, hxcEvent);

  check(host.health == 0.9, 'Psych miss applies source note health');
  check(host.misses == 1 && host.songScore == -10 && host.totalPlayed == 1,
   'Psych miss updates score and denominator once');
  check(host.combo == 0 && host.accuracy == 0, 'Psych miss clears combo and refreshes accuracy');
  check(host.boyfriend.played.join('|') == 'singUPmiss-alt',
   'Psych animation uses lane, source suffix, and actor miss capability');
  check(host.gf.played.join('|') == 'sad' && host.gf.specialAnim,
   'previous high combo triggers source GF sadness after the miss animation');
  check(host.vocalTracks.playerWrites == 2 && host.vocalTracks.opponentWrites == 1,
   'instakill mutes both buses before death and ordinary miss mutes player afterward');
  check(host.lastMissCallbackArgs != null && host.lastMissCallbackArgs.length == 4
   && host.lastMissCallbackArgs[3] == hxcEvent && host.lastMissCallbackSkipPsych,
   'the shared HXC event reaches the final source callback while native Psych callbacks are skipped');

  before(host.events, 'death', 'health:0.9', 'instakill check precedes health application');
  before(host.events, 'health:0.9', 'songScore:-10', 'health precedes miss bookkeeping');
  before(host.events, 'totalPlayed:1', 'rating:true', 'ledger bookkeeping precedes rating notification');
  before(host.events, 'rating:true', 'anim:boyfriend:singUPmiss-alt', 'rating precedes miss animation');
  before(host.events, 'anim:boyfriend:singUPmiss-alt', 'vocal:player:0#2', 'ordinary player mute follows animation');
  before(host.events, 'vocal:player:0#2', 'stage:noteMiss', 'stage sees completed miss effects');
  before(host.events, 'stage:noteMiss', 'psych:Luas:noteMiss', 'stage callback precedes Psych Lua');
  before(host.events, 'psych:Luas:noteMiss', 'psych:HScript:noteMiss', 'Psych Lua precedes HScript');
  before(host.events, 'psych:HScript:noteMiss', 'all:playerOneMiss', 'source globals follow the Psych router');
  before(host.events, 'one:customMiss', 'all:playerOneMiss', 'per-note HScript precedes owner-wide miss hooks');
 }
'''
        )

    def test_nightmare_local_hooks_tail_fade_sadness_and_counted_miss_order(self):
        self.run_haxe(
            r'''
 static function main():Void {
  var host = new PlayState(true);
  var note = new Note();
  note.sourcePlayfieldIndex = 0;
  note.noteData = 1;
  note.noteType = 'Alt Animation';
  note.strumTime = 200;
  note.alphaMod = 1;
  note.nightmareVisionTailState = new TailState(host.events);
  var piece = new TailPiece(host.events);
  note.nightmareVisionTailState.notes = [piece];
  host.notes.members = [note];
  host.nightmareVisionFields[0].singers = [host.boyfriend, host.enemy];
  host.skin.data = {singAnimations:['left', 'down', 'up', 'right']};
  host.combo = 9;
  host.instakillOnMiss = true;
  host.sourceNoteMiss(1, true, note, host.boyfriend, null);

  check(host.health == 0.9525, 'NV note miss applies owner health loss');
  check(host.boyfriend.played.join('|') == 'downmiss-alt'
   && host.enemy.played.join('|') == 'downmiss-alt', 'NV animates all field singers with its skin lane');
  check(host.boyfriend.holdTimer == 0 && host.enemy.holdTimer == 0,
   'NV miss animations reset each singer hold timer');
  check(note.nightmareVisionTailState.missed && piece.tooLate,
   'eligible missed head marks its live tail state and pieces late');
  check(Math.abs(note.alphaMod - 0.3) < 0.0001, 'NV miss fades the live note');
  check(host.gf.played.join('|') == 'sad', 'counted high-combo miss triggers timed GF sadness');
  check(host.combo == 0 && host.misses == 1 && host.songScore == -10 && host.totalPlayed == 1,
   'NV counted miss resets combo and updates score ledger once');
  check(host.vocalTracks.playerWrites == 1 && host.deathChecks == 1 && host.ratingChanges == 1,
   'NV counted miss mutes, checks death, and refreshes rating once');

  before(host.events, 'health:0.9525', 'anim:boyfriend:downmiss-alt', 'health precedes field animation');
  before(host.events, 'anim:enemy:downmiss-alt', 'nv-local:noteMiss', 'all singers animate before note type hook');
  before(host.events, 'nv-local:noteMiss', 'nv-main:noteMiss', 'note type hook precedes global NV note hook');
  before(host.events, 'nv-main:noteMiss', 'tail:missed', 'NV hooks precede sustain tail invalidation');
  before(host.events, 'tail:late', 'anim:gf:sad-duration', 'tail invalidation precedes GF sadness');
  before(host.events, 'anim:gf:sad-duration', 'combo:0', 'GF sadness precedes combo reset');
  before(host.events, 'combo:0', 'vocal:player:0#1', 'combo reset precedes player vocal mute');
  before(host.events, 'vocal:player:0#1', 'death', 'vocal mute precedes instakill check');
  before(host.events, 'death', 'songScore:-10', 'instakill check precedes counted ledger miss');
  before(host.events, 'totalPlayed:1', 'rating:true', 'ledger update precedes rating notification');
 }
'''
        )

    def test_nv_can_miss_still_reaches_local_hook_without_counting_or_death(self):
        self.run_haxe(
            r'''
 static function main():Void {
  var host = new PlayState(true);
  var note = new Note();
  note.sourcePlayfieldIndex = 0;
  note.canMiss = true;
  note.alphaMod = 1;
  note.nightmareVisionTailState = new TailState(host.events);
  var piece = new TailPiece(host.events);
  note.nightmareVisionTailState.notes = [piece];
  host.nightmareVisionFields[0].singers = [host.boyfriend];
  host.notes.members = [note];
  host.nightmareVisionNoteTypes.result = NightmareVisionScriptGroup.STOP_FUNC;
  host.combo = 4;
  host.sourceNoteMiss(0, true, note, host.boyfriend, null);

  check(host.health == 0.9525, 'canMiss notes retain local health reaction');
  check(host.boyfriend.played.length == 1, 'canMiss notes retain local miss animation');
  check(host.nightmareVisionNoteTypes.calls == 1, 'canMiss notes reach their local type hook');
  check(host.nightmareVisionScripts.calls == 0,
   'local STOP_FUNC suppresses the global NV note-type miss hook');
  check(!note.nightmareVisionTailState.missed && !piece.tooLate,
   'canMiss note does not terminate an otherwise eligible sustain tail');
  check(Math.abs(note.alphaMod - 0.3) < 0.0001, 'canMiss note still receives NV miss fade');
  check(host.combo == 4 && host.misses == 0 && host.songScore == 0 && host.totalPlayed == 0,
   'canMiss note does not reset combo or count in miss scoring');
  check(host.deathChecks == 0 && host.vocalTracks.playerWrites == 0 && host.ratingChanges == 0,
   'canMiss note does not mute, death-check, or refresh ratings');
 }
'''
        )

    def test_nv_stunned_empty_press_has_no_local_reaction_but_still_counts(self):
        self.run_haxe(
            r'''
 static function main():Void {
  var host = new PlayState(true);
  host.boyfriend.stunned = true;
  host.combo = 2;
  host.instakillOnMiss = true;
  host.sourceNoteMiss(3, true, null, host.boyfriend, null);

  check(host.health == 1, 'stunned NV empty press skips health reaction');
  check(host.boyfriend.played.length == 0 && host.enemy.played.length == 0,
   'stunned NV empty press skips miss animation');
  check(host.events.indexOf('sound:miss') < 0, 'stunned NV empty press skips miss sound');
  check(host.misses == 1 && host.totalPlayed == 1 && host.songScore == -10,
   'stunned press still follows the state-level counted-miss route');
  check(host.deathChecks == 1 && host.ratingChanges == 1,
   'counted stunned press still runs instakill check and rating update');
  check(host.events.indexOf('nv-local:noteMiss') < 0 && host.events.indexOf('nv-main:noteMiss') < 0,
   'empty press does not dispatch note-object type hooks');
 }
'''
        )

    def test_psych_guitar_hero_early_return_keeps_stage_and_source_callbacks(self):
        self.run_haxe(
            r'''
 static function main():Void {
  var host = new PlayState(false);
  var note = new Note();
  note.missed = true;
  host.notes.members = [note];
  host.guitarHeroSustains = true;
  host.combo = 6;
  host.sourceNoteMiss(1, true, note, host.boyfriend, null);

  check(host.health == 1 && host.misses == 0 && host.songScore == 0 && host.totalPlayed == 0,
   'GH already-missed sustain skips ordinary miss effects');
  check(host.ratingChanges == 0 && host.boyfriend.played.length == 0,
   'GH early return skips rating and animation');
  check(host.events.indexOf('stage:noteMiss') >= 0,
   'Psych stage noteMiss still dispatches after GH common returns early');
  check(host.events.indexOf('psych:Luas:noteMiss') >= 0
   && host.events.indexOf('psych:HScript:noteMiss') >= 0,
   'Psych Lua and HScript source callbacks still dispatch after GH common return');
  check(host.events.indexOf('all:playerOneMiss') >= 0 && host.events.indexOf('all:noteMiss') >= 0,
   'shared HScript source hooks still dispatch after GH common return');
 }
'''
        )

    def test_outer_note_miss_keeps_live_ghost_gate_before_hxc_and_owner_router(self):
        miss = extract_method(self.play, "function noteMiss(")
        ghost_gate = "if (note == null && sourceScoreLedgerActive() && sourceLivePreference('ghostTapping', ghostTapping)) return;"
        self.assertIn(ghost_gate, miss)
        self.assertLess(miss.index(ghost_gate), miss.index("callHxcNoteHScript('noteGhostMiss'"))
        self.assertLess(miss.index(ghost_gate), miss.index("sourceNoteMiss(direction, playerOne, note, actingOn, hxcMissEvent)"))
        self.assertIn("sourceLivePreference('ghostTapping', ghostTapping)", miss)
        hxc_start = miss.index("var hxcMissEvent:Dynamic = null;")
        cancel = miss.index("hxcMissEvent.eventCanceled == true")
        codename = miss.index("missCodenameNote(direction, note, playMissSound, authoredLine)")
        source_route = miss.index("sourceNoteMiss(direction, playerOne, note, actingOn, hxcMissEvent)")
        self.assertLess(hxc_start, cancel)
        self.assertLess(cancel, codename)
        self.assertLess(codename, source_route)

    def test_miss_routes_remain_tied_to_pinned_donor_order(self):
        if not PSYCH_DONOR.is_file() or not NV_DONOR.is_file():
            self.skipTest("mounted Psych and Nightmare Vision source donors are unavailable")
        psych = PSYCH_DONOR.read_text(encoding="utf-8")
        psych_miss = psych[psych.index("function noteMiss(daNote:Note)"):psych.index("function noteMissPress(")]
        psych_common = psych[psych.index("function noteMissCommon("):psych.index("function opponentNoteHit(")]
        self.assertLess(psych_miss.index("noteMissCommon(daNote.noteData, daNote)"), psych_miss.index("stagesFunc("))
        self.assertLess(psych_miss.index("stagesFunc("), psych_miss.index("callOnLuas('noteMiss'"))
        self.assertLess(psych_miss.index("callOnLuas('noteMiss'"), psych_miss.index("callOnHScript('noteMiss', [daNote])"))
        self.assertLess(psych_common.index("doDeathCheck(true)"), psych_common.index("health -= subtract * healthLoss"))
        self.assertLess(psych_common.index("RecalculateRating(true)"), psych_common.index("// play character anims"))
        self.assertGreater(psych_common.rindex("vocals.volume = 0;"), psych_common.index("// play character anims"))

        nv = NV_DONOR.read_text(encoding="utf-8")
        local_miss = nv[nv.index("function noteMiss(note:Note, field:PlayField)"):nv.index("function noteMissPress(")]
        self.assertIn("callNoteTypeScript(note.noteType, 'noteMiss'", local_miss)
        self.assertLess(local_miss.index("char.playAnim(animToPlay, true)"), local_miss.index("callNoteTypeScript(note.noteType, 'noteMiss'"))
        self.assertLess(local_miss.index("callNoteTypeScript(note.noteType, 'noteMiss'"), local_miss.index("note.alphaMod *= 0.3"))


HAXE_FIXTURE = r'''
class RuntimeEvent { public var name:String; public var args:Array<Dynamic>; public function new(n,a) {name=n;args=a;} }
class Note {
 public var noteData:Int = 0;
 public var sourcePlayfieldIndex:Int = 0;
 public var isSustainNote:Bool = false;
 public var strumTime:Float = 0;
 public var mustPress:Bool = true;
 public var exists:Bool = true;
 public var alive:Bool = true;
 public var missed:Bool = false;
 public var canMiss:Bool = false;
 public var blockHit:Bool = false;
 public var hitCausesMiss:Bool = false;
 public var noMissAnimation:Bool = false;
 public var noteType:String = 'Default';
 public var animSuffix:String = '';
 public var forceGfSing:Bool = false;
 public var gfNote:Bool = false;
 public var missHealth:Null<Float> = null;
 public var alphaMod:Float = 1;
 public var noteMiss:String = null;
 public var nightmareVisionTailState:TailState = null;
 public function new() {}
}
class NoteGroup { public var members:Array<Note> = []; public function new() {} }
class Character {
 public var name:String;
 public var events:Array<String>;
 public var animTimer:Float = 0;
 public var hasMissAnimations:Bool = true;
 public var stunned:Bool = false;
 public var holdTimer:Float = 4;
 public var specialAnim:Bool = false;
 public var played:Array<String> = [];
 public function new(name:String, events:Array<String>) { this.name=name; this.events=events; }
 public function hasAnimation(name:String):Bool return name == 'sad';
 public function playAnim(name:String, force:Bool=false):Void {
  played.push(name); events.push('anim:' + this.name + ':' + name);
 }
 public function playAnimForDuration(name:String, duration:Float, force:Bool=false):Void {
  played.push(name); events.push('anim:' + this.name + ':' + name + '-duration');
 }
}
class FakeVocalTracks {
 public var events:Array<String>;
 public var playerWrites:Int = 0;
 public var opponentWrites:Int = 0;
 public function new(events:Array<String>) this.events=events;
 public function setRoleVolume(role:String, value:Float, fallback:Bool=false):Bool {
  if (role == 'player') playerWrites++;
  if (role == 'opponent') opponentWrites++;
  var count = role == 'player' ? playerWrites : opponentWrites;
  events.push('vocal:' + role + ':' + Std.string(value) + '#' + count);
  return true;
 }
}
class FakeSound {
 public var events:Array<String>;
 public function new(events:Array<String>) this.events=events;
 public function play(asset:Dynamic, volume:Float):Void events.push('sound:miss');
}
class FakeRandom {
 public function new() {}
 public function int(min:Int, max:Int):Int return min;
 public function float(min:Float, max:Float):Float return min;
}
class FlxG {
 public static var sound:FakeSound;
 public static var random:FakeRandom;
}
class TitleState { public static var soundExt:String = '.ogg'; }
class TailPiece {
 var _tooLate:Bool = false;
 public var events:Array<String>;
 public var tooLate(get,set):Bool;
 public function new(events:Array<String>) this.events=events;
 function get_tooLate():Bool return _tooLate;
 function set_tooLate(value:Bool):Bool { _tooLate=value; if(value) events.push('tail:late'); return value; }
}
class TailState {
 var _missed:Bool = false;
 public var events:Array<String>;
 public var missed(get,set):Bool;
 public var notes:Array<TailPiece> = [];
 public function new(events:Array<String>) this.events=events;
 function get_missed():Bool return _missed;
 function set_missed(value:Bool):Bool { _missed=value; if(value) events.push('tail:missed'); return value; }
}
class NVField {
 public var playerControls:Bool = true;
 public var singers:Array<Character> = [];
 public function new() {}
}
class NVSkin { public var data:Dynamic = null; public function new() {} }
class SongData { public var notes:Array<Dynamic> = []; public function new() {} }
class NightmareVisionScriptGroup { public static inline var STOP_FUNC:Int = 1; }
class NightmareVisionNoteTypeRuntime {
 public static function noteTypeOf(note:Note):String return note.noteType;
}
class FakeNoteTypes {
 var host:PlayState;
 public var calls:Int = 0;
 public var result:Int = 0;
 public function new(host:PlayState) this.host=host;
 public function noteMiss(note:Note, fieldID:Int):Int {
  calls++; host.events.push('nv-local:noteMiss'); return result;
 }
}
class FakeNVScripts {
 var host:PlayState;
 public var calls:Int = 0;
 public function new(host:PlayState) this.host=host;
 public function call(name:String,args:Array<Dynamic>,ignoreStops:Bool=false,?hscriptArgs:Array<Dynamic>):Dynamic {
  calls++; host.events.push('nv-main:' + name); return 0;
 }
}
class PsychRuntimeBindings {
 public static function dispatch(host:PlayState, name:String, args:Array<Dynamic>, family:String='Scripts', ignoreStops:Bool=false, ?hscriptArgs:Array<Dynamic>):Dynamic {
  host.events.push('psych:' + family + ':' + name);
  return host.psychResult;
 }
}
class PlayState {
 public var events:Array<String> = [];
 public var notes:NoteGroup = new NoteGroup();
 public var sourceScoreNightmare:Bool;
 public var sourceScoreOwner:Bool = true;
 public var combo(default,set):Int = 0;
 public var songScore(default,set):Int = 0;
 public var misses(default,set):Int = 0;
 public var totalPlayed(default,set):Int = 0;
 public var health(default,set):Float = 1;
 public var accuracy(default,set):Float = 0;
 public var totalNotesHit:Float = 0;
 public var practiceMode:Bool = false;
 public var endingSong:Bool = false;
 public var instakillOnMiss:Bool = false;
 public var guitarHeroSustains:Bool = false;
 public var healthLoss:Float = 1;
 public var healthLossMultiplier:Float = 1;
 public var pressMissDamage:Float = 0.05;
 public var holdSubdivisions:Int = 1;
 public var ratingChanges:Int = 0;
 public var deathChecks:Int = 0;
 public var vocalTracks:FakeVocalTracks;
 public var vocals:Dynamic = null;
 public var boyfriend:Character;
 public var enemy:Character;
 public var gf:Character;
 public var nightmareVisionFields:Array<NVField> = [];
 public var nightmareVisionNoteTypes:FakeNoteTypes;
 public var nightmareVisionScripts:FakeNVScripts;
 public var skin:NVSkin = new NVSkin();
 public var SONG:SongData = new SongData();
 public var sourceScoreDynamic:Bool = false;
 public var psychResult:Dynamic = ScriptCallbackResult.CONTINUE;
 public var curSection:Int = -1;
 public var sourceScoreNoteState:Dynamic;
 public var stateStop:Bool = false;
 public var lastMissCallbackArgs:Array<Dynamic> = null;
 public var lastMissCallbackSkipPsych:Bool = false;
 public function new(nightmare:Bool) {
  sourceScoreNightmare=nightmare;
  FlxG.sound = new FakeSound(events);
  FlxG.random = new FakeRandom();
  vocalTracks = new FakeVocalTracks(events);
  boyfriend = new Character('boyfriend', events);
  enemy = new Character('enemy', events);
  gf = new Character('gf', events);
  nightmareVisionFields = [new NVField(), new NVField()];
  nightmareVisionNoteTypes = new FakeNoteTypes(this);
  nightmareVisionScripts = new FakeNVScripts(this);
 }
 function set_combo(value:Int):Int { combo=value; events.push('combo:' + value); return value; }
 function set_songScore(value:Int):Int { songScore=value; events.push('songScore:' + value); return value; }
 function set_misses(value:Int):Int { misses=value; events.push('misses:' + value); return value; }
 function set_totalPlayed(value:Int):Int { totalPlayed=value; events.push('totalPlayed:' + value); return value; }
 function set_health(value:Float):Float { health=value; events.push('health:' + Std.string(value)); return value; }
 function set_accuracy(value:Float):Float { accuracy=value; events.push('accuracy:' + Std.string(value)); return value; }
 public function sourceScoreLedgerActive():Bool return sourceScoreOwner;
 public function getNightmareVisionField(index:Int):NVField return nightmareVisionFields[index];
 public function nightmareVisionSkinForField(index:Int):NVSkin return skin;
 public function invalidateSourceInputNote(note:Note):Void events.push('invalidate');
 public function doDeathCheck(?force:Bool=false):Void {deathChecks++; events.push('death');}
 public function notifyPsychRatingChange(?missed:Bool=false,?scoreBop:Bool=true):Void {ratingChanges++; events.push('rating:' + missed);}
 public function dispatchPsychCompiledStage(name:String,args:Array<Dynamic>):Void events.push('stage:' + name);
 public function setAllHaxeVar(name:String,value:Dynamic):Void events.push('global:' + name);
 public function callHscript(name:String,args:Array<Dynamic>,family:String='Scripts'):Dynamic {events.push('one:' + name); return null;}
 public function callAllHScript(name:String,args:Array<Dynamic>,?skipHxc:Bool=false,
  ?returnValues:Array<Dynamic>,?hxcArgs:Array<Dynamic>,?skipPsych:Bool=false):Void {
  events.push('all:' + name);
  if (name == 'noteMiss') {lastMissCallbackArgs=args; lastMissCallbackSkipPsych=skipPsych;}
 }
 public function sourceScoreLedgerActiveDummy():Bool return true;
 __EXTRACTED_METHODS__
 public function exercise(note:Note, direction:Int=1, playerOne:Bool=true, ?actingOn:Character, ?hxcMissEvent:Dynamic):Void
  sourceNoteMiss(direction, playerOne, note, actingOn == null ? boyfriend : actingOn, hxcMissEvent);
}
class Main {
 static function check(value:Bool,message:String):Void if(!value) throw message;
 static function before(events:Array<String>, first:String, second:String, message:String):Void {
  var a=events.indexOf(first); var b=events.indexOf(second);
  check(a>=0 && b>=0 && a<b, message + ' (' + first + ' at ' + a + ', ' + second + ' at ' + b + ')');
 }
 __TEST_BODY__
}
'''


if __name__ == "__main__":
    unittest.main()
