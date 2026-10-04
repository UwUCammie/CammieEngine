"""Execute the source-owned Note defaults and Hurt Note field contract."""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    semicolon = source.find(";", start)
    brace = source.index("{", start)
    if semicolon >= 0 and semicolon < brace:
        return source[start:semicolon + 1]
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
    raise AssertionError(f"unterminated Haxe method: {marker}")


def extract_field(source: str, marker: str) -> str:
    start = source.index(marker)
    return source[start:source.index(";", start) + 1]


class SourceNoteHealthFieldsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.note = (ROOT / "source/Note.hx").read_text(encoding="utf-8")

    def test_source_defaults_hurt_note_owner_and_missed_gate(self):
        note = self.note
        constructor_start = note.index(
            "if (PlayState.instance != null) sourceTimingMode = PlayState.instance.sourceNoteTimingMode();"
        )
        constructor_end = note.index("\n\t\tif (isSustainNote) {", constructor_start)
        constructor_timing = note[constructor_start:constructor_end]
        self.assertIn("initializeSourceHealthDefaults();", constructor_timing)
        self.assertLess(constructor_timing.index("initializeSourceHealthDefaults();"),
                        constructor_timing.index("if (sourceTimingMode == 1 && isSustainNote)"))

        source_getter = extract_method(note, "function get_canBeHit():Bool")
        self.assertIn("sourceTimingMode != 0 && missed", source_getter)
        update_start = note.index("override function update(elapsed:Float)")
        update_branch_start = note.index("else if (sourceTimingMode != 0)", update_start)
        update_branch_end = note.index("\n\t\t\t} else {", update_branch_start)
        source_update_branch = note[update_branch_start:update_branch_end]
        # Source missed state must override both Psych's cached value and NV's
        # live timing calculation.
        self.assertIn("nightmareVisionTailState.missed", source_getter)
        self.assertIn("if (sourceTimingMode == 1)", source_update_branch)
        self.assertNotIn("sourceTimingMode == 2) canBeHit", source_update_branch)

        fields = "\n".join((
            extract_field(note, "public var sourceTimingMode:Int = 0;"),
            extract_field(note, "public var hitbox:Float = Conductor.safeZoneOffset;"),
            extract_field(note, "public var earlyHitMult:Float = 1;"),
            extract_field(note, "public var lateHitMult:Float = 1;"),
            extract_field(note, "var cachedCanBeHit:Bool = false;"),
            extract_field(note, "public var canBeHit(get, set):Bool;"),
            extract_field(note, "public var strumTime:Float = 0;"),
            extract_field(note, "public var tooLate:Bool = false;"),
            extract_field(note, "public var wasGoodHit:Bool = false;"),
            extract_field(note, "@:keep public var mustPress:Bool = false;"),
            extract_field(note, "public var isSustainNote:Bool = false;"),
            extract_field(note, "@:keep public var parent:Note = null;"),
            extract_field(note, "@:keep public var tail:Array<Note> = [];"),
            extract_field(note, "@:keep public var missed:Bool = false;"),
            extract_field(note, "public var nightmareVisionTailState:{missed:Bool, notes:Array<Note>, ?active:Bool};"),
            extract_field(note, "@:keep public var nightmareVisionTypeRuntime:NightmareVisionNoteTypeRuntime;"),
            extract_field(note, "var pendingSourceCanMiss:Bool = false;"),
            extract_field(note, "public var hitHealth:Null<Float> = null;"),
            extract_field(note, "public var missHealth:Null<Float> = null;"),
            extract_field(note, "public var hitCausesMiss:Bool = false;"),
            extract_field(note, "public var ignoreNote:Bool = false;"),
            extract_field(note, "public var lowPriority:Bool = false;"),
            extract_field(note, "@:keep public var canMiss(get, set):Bool;"),
            extract_field(note, "public var sourceKind(default, set):Null<String> = null;"),
        ))
        methods = "\n".join(extract_method(note, marker) for marker in (
            "function get_canBeHit():Bool",
            "function set_canBeHit(value:Bool):Bool",
            "function get_canMiss():Bool",
            "function set_canMiss(value:Bool):Bool",
            "function set_sourceKind(value:Null<String>):Null<String>",
            "public function applyPendingSourceNoteSemantics():Void",
            "function applySourceHurtNoteSemantics():Void",
            "function initializeSourceHealthDefaults():Void",
        ))
        constructor_prelude = constructor_timing

        fixture = r'''
class Conductor {
 public static var songPosition:Float = 0;
 public static var safeZoneOffset:Float = 75;
}
class PlayState {
 public static var instance:PlayState;
 public var mode:Int;
 public function new(mode:Int) this.mode=mode;
 public function sourceNoteTimingMode():Int return mode;
}
class SourceNoteTiming {
 public static function nightmareCanBeHit(time:Float, position:Float, hitbox:Float,
   earlyHitMult:Float = 1):Bool return Math.abs(time-position) <= hitbox*earlyHitMult;
 public static function psychCanBeHit(time:Float, position:Float, safe:Float,
   early:Float = 1, late:Float = 1):Bool return Math.abs(time-position) < safe;
 public static function isLate(time:Float, position:Float, safe:Float,
   wasGoodHit:Bool):Bool return time < position-safe && !wasGoodHit;
}
class NoteTypeCompat {
 public static function canonical(value:Null<String>):Null<String> return value;
}
class NoteTypeApi {
 public function new() {}
 public function setCanMiss(note:Note,value:Bool):Bool {
   note.storedCanMiss=value; return value;
 }
 public function canMiss(note:Note):Bool return note.storedCanMiss;
}
class NightmareVisionNoteTypeRuntime {
 public var api:NoteTypeApi = new NoteTypeApi();
 public function new() {}
}
class Note {
 __FIELDS__
 __METHODS__
 public var storedCanMiss:Bool = false;
 public var hitPriority:Int = 1;
 function applyPsychNoteAnimationType(value:Null<String>):Void {}
 function refreshPsychNoteType():Void {}
 public function updateSourceModeBranch():Void {
   var signedDiff = Conductor.songPosition-strumTime;
   if (sourceTimingMode == 1)
     canBeHit = SourceNoteTiming.psychCanBeHit(strumTime,Conductor.songPosition,
       Conductor.safeZoneOffset,earlyHitMult,lateHitMult);
   if (sourceTimingMode != 0 && SourceNoteTiming.isLate(strumTime,
       Conductor.songPosition,Conductor.safeZoneOffset,wasGoodHit)) tooLate=true;
 }
 public function new(mode:Int,sustain:Bool=false,?authoredMustHit:Null<Bool>=null) {
   isSustainNote=sustain;
   PlayState.instance=new PlayState(mode);
   __CONSTRUCTOR_PRELUDE__
 }
}
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main():Void {
   Conductor.safeZoneOffset=75;
   var native=new Note(0);
   check(native.hitHealth==null && native.missHealth==null,
     'native notes preserve null health defaults');
   var nativeAuthored=new Note(0,false,true);
   check(!nativeAuthored.mustPress,
     'native constructor keeps its existing mustPress initialization path');
   check(native.parent==null && native.tail.length==0 && !native.missed,
     'source chain fields start detached and clear');

   var psychHead=new Note(1,false,true);
   check(psychHead.hitHealth==0.02 && psychHead.missHealth==0.1,
     'Psych owner notes use Psych hit/miss health defaults: mode='
       +psychHead.sourceTimingMode+' hit='+Std.string(psychHead.hitHealth)
       +' miss='+Std.string(psychHead.missHealth));
   psychHead.sourceKind='Hurt Note';
   check(psychHead.hitHealth==0.02 && psychHead.missHealth==0.1
     && psychHead.ignoreNote && psychHead.hitCausesMiss && psychHead.lowPriority,
     'Psych Hurt Note uses authored player ownership and source miss semantics');
   var psychTail=new Note(1,true,true);
   psychTail.sourceKind='Hurt Note';
   check(psychTail.hitHealth==0.02 && psychTail.missHealth==0.25
     && psychTail.ignoreNote && psychTail.hitCausesMiss,
     'Psych Hurt Note sustain uses its distinct miss damage');
   var psychOpponent=new Note(1);
   psychOpponent.sourceKind='Hurt Note';
   check(!psychOpponent.ignoreNote,
     'Hurt Note ownership is corrected after constructor-time note-kind recovery');

   var nvHead=new Note(2,false,true);
   check(nvHead.hitHealth==0.023 && nvHead.missHealth==0.0475,
     'Nightmare Vision notes use source hit/miss health defaults');
   nvHead.sourceKind='Hurt Note';
   check(nvHead.hitHealth==0.023 && nvHead.missHealth==0.3
     && nvHead.ignoreNote && nvHead.hitCausesMiss && nvHead.lowPriority
     && !nvHead.canMiss,
     'Nightmare Vision Hurt Note head defers canMiss until its type runtime exists');
   nvHead.nightmareVisionTypeRuntime=new NightmareVisionNoteTypeRuntime();
   nvHead.applyPendingSourceNoteSemantics();
   check(nvHead.canMiss,
     'deferred source canMiss is installed when the note type runtime attaches');
   var nvTail=new Note(2,true);
   nvTail.sourceKind='Hurt Note';
   check(nvTail.missHealth==0.1 && nvTail.hitCausesMiss,
     'Nightmare Vision Hurt Note sustain uses its distinct miss damage');

   Conductor.songPosition=500;
   var pending=new Note(2);
   pending.strumTime=500;
   pending.updateSourceModeBranch();
   check(pending.canBeHit,'unmissed NV note remains hittable inside the source window');
   pending.missed=true;
   pending.updateSourceModeBranch();
   check(!pending.canBeHit,'missed source note stays closed after Note.update timing work');
   pending.missed=false;
   pending.nightmareVisionTailState={missed:true,notes:[],active:false};
   pending.updateSourceModeBranch();
   check(!pending.canBeHit,'shared sustain missed flag also remains closed after update');

   PlayState.instance=new PlayState(1);
   var psychPending=new Note(1);
   psychPending.strumTime=500;
   psychPending.updateSourceModeBranch();
   check(psychPending.canBeHit,'unmissed Psych note keeps its cached hit window');
   psychPending.missed=true;
   psychPending.updateSourceModeBranch();
   check(!psychPending.canBeHit,'missed Psych note stays closed after cached update timing work');
 }
}
'''
        fixture = (fixture.replace("__FIELDS__", fields)
                   .replace("__METHODS__", methods)
                   .replace("__CONSTRUCTOR_PRELUDE__", constructor_prelude))

        with tempfile.TemporaryDirectory(prefix="source-note-health-", dir=ROOT / "tmp") as folder:
            scratch = FixturePath(folder)
            (scratch / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(scratch), "-main", "Main", "--interp"],
                cwd=ROOT, env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
