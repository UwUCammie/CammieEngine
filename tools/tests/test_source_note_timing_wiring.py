"""Headless execution of the host Note and PlayState source-timing wiring."""

from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"


def extract_method(source: str, marker: str) -> str:
    """Extract a Haxe braced method, ignoring braces in comments and strings."""
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
                return source[start:index + 1]
        index += 1
    raise AssertionError(f"unterminated Haxe method: {marker}")


def extract_expression_member(source: str, marker: str) -> str:
    """Read an expression-bodied Haxe member through its terminating semicolon."""
    start = source.index(marker)
    end = source.index(";", start) + 1
    return source[start:end]


def extract_field(source: str, marker: str) -> str:
    start = source.index(marker)
    end = source.index(";", start) + 1
    return source[start:end]


class SourceNoteTimingWiringTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.note = (ROOT / "source/Note.hx").read_text(encoding="utf-8")
        cls.play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")

    def run_haxe(self, fixture: str, main: str) -> None:
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        with tempfile.TemporaryDirectory(prefix="source-note-timing-wiring-", dir=ROOT / "tmp") as scratch:
            scratch = FixturePath(scratch)
            (scratch / f"{main}.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(scratch),
                 "--main", main, "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_actual_note_getters_constructor_and_update_branch(self):
        note = self.note
        play = self.play
        update_start = note.index("override function update(elapsed:Float)")
        psych_update_start = note.index("if (sourceTimingMode == 1)", update_start)
        psych_update_end = note.index("\n\t\t\t} else {", psych_update_start)
        psych_update_branch = note[psych_update_start:psych_update_end]
        constructor_start = note.index(
            "if (PlayState.instance != null) sourceTimingMode = PlayState.instance.sourceNoteTimingMode();"
        )
        constructor_end = note.index("\n\t\tif (isSustainNote) {", constructor_start)
        constructor_timing = note[constructor_start:constructor_end]

        members = "\n ".join((
            extract_field(note, "public var sourceTimingMode:Int = 0;"),
            extract_field(note, "@:keep public var mustPress:Bool = false;"),
            extract_field(note, "public var hitbox:Float = Conductor.safeZoneOffset;"),
            extract_field(note, "public var earlyHitMult:Float = 1;"),
            extract_field(note, "public var lateHitMult:Float = 1;"),
            extract_field(note, "public var strumTime:Float = 0;"),
            extract_field(note, "public var noteDiff(get, never):Float;"),
            extract_field(note, "var cachedCanBeHit:Bool = false;"),
            extract_field(note, "public var canBeHit(get, set):Bool;"),
            extract_field(note, "public var isSustainNote:Bool = false;"),
            extract_field(note, "public var tooLate:Bool = false;"),
            extract_field(note, "public var wasGoodHit:Bool = false;"),
            extract_field(note, "@:keep public var missed:Bool = false;"),
            extract_field(note, "public var hitHealth:Null<Float> = null;"),
            extract_field(note, "public var missHealth:Null<Float> = null;"),
        ))
        getters = "\n ".join((
            extract_expression_member(note, "function get_noteDiff():Float"),
            extract_method(note, "function get_canBeHit():Bool"),
            extract_expression_member(note, "function set_canBeHit(value:Bool):Bool"),
            extract_expression_member(note, "public function isLate():Bool"),
            extract_method(note, "function initializeSourceHealthDefaults():Void"),
        ))
        source_mode = extract_expression_member(play, "@:keep public function sourceNoteTimingMode():Int")

        fixture = r'''
import SourceNoteTiming;

class Conductor {
 public static var songPosition:Float = 0;
 public static var safeZoneOffset:Float = 0;
}
class PlayState {
 public static var instance:PlayState;
 public var sourceScoreOwner:Bool = false;
 public var sourceScoreNightmare:Bool = false;
 public function new() {}
 __SOURCE_MODE__
}
class TimingNote {
 __MEMBERS__
 __GETTERS__
 public var nightmareVisionTailState:Dynamic;
 public function new(sustain:Bool = false, ?authoredMustHit:Null<Bool> = null) {
  isSustainNote = sustain;
  __CONSTRUCTOR_TIMING__
 }
 public function updateSourceTiming():Void {
  __PSYCH_UPDATE__
 }
}
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  Conductor.songPosition = 100;
  Conductor.safeZoneOffset = 60;
  PlayState.instance = new PlayState();
  var native = new TimingNote(false, true);
  check(native.sourceTimingMode == 0 && !native.mustPress,
   'native constructor retains the preexisting mustPress initialization path');
  PlayState.instance.sourceScoreOwner = true;

  var psych = new TimingNote(false, true);
  check(psych.sourceTimingMode == 1 && psych.earlyHitMult == 1 && psych.mustPress,
   'Psych tap constructor selects source mode without changing its early multiplier');
  psych.earlyHitMult = 0.5;
  psych.lateHitMult = 1.5;
  psych.strumTime = 10;
  psych.updateSourceTiming();
  check(!psych.canBeHit && psych.tooLate,
   'Psych update uses strict scaled canBeHit bounds and the unscaled strict late getter');
  psych = new TimingNote();
  psych.earlyHitMult = 0.5;
  psych.lateHitMult = 1.5;
  psych.strumTime = 10.001;
  psych.updateSourceTiming();
  check(psych.canBeHit && psych.tooLate,
   'Psych late multiplier can extend canBeHit past the independent tooLate threshold');
  psych.strumTime = Conductor.songPosition;
  psych.updateSourceTiming();
  psych.missed = true;
  check(!psych.canBeHit,
   'Psych missed notes remain closed even when update refreshes the cached hit window');
  psych = new TimingNote(true);
  check(psych.earlyHitMult == 0,
   'Psych sustain constructor sets the source early multiplier to zero');
  psych.strumTime = 100;
  psych.updateSourceTiming();
  check(!psych.canBeHit, 'zero early multiplier excludes exact sustain note time');
  psych.strumTime = 99.999;
  psych.updateSourceTiming();
  check(psych.canBeHit, 'zero early multiplier still allows a sustain just after its note time');

  PlayState.instance.sourceScoreNightmare = true;
  Conductor.safeZoneOffset = 75;
  var nv = new TimingNote(true, true);
  check(nv.sourceTimingMode == 2 && nv.earlyHitMult == 1 && nv.hitbox == 75,
   'NV note captures the current global hitbox and keeps its default multiplier');
  nv.earlyHitMult = 0.5;
  nv.strumTime = 62.5;
  check(nv.noteDiff == -37.5 && nv.canBeHit,
   'NV getter uses signed raw noteDiff and includes its captured early boundary');
  nv.strumTime = 137.5;
  check(nv.noteDiff == 37.5 && nv.canBeHit,
   'NV getter includes its captured late boundary');
  nv.strumTime = 62.499;
  check(!nv.canBeHit, 'NV getter rejects a point outside its captured scaled hitbox');

  Conductor.safeZoneOffset = 1;
  nv.earlyHitMult = 1;
  nv.strumTime = 99;
  nv.updateSourceTiming();
  check(nv.hitbox == 75 && nv.canBeHit && !nv.tooLate,
   'NV hitbox stays captured while isLate reads the live global window strictly');
  nv.strumTime = 98.999;
  nv.tooLate = false;
  nv.updateSourceTiming();
  check(nv.canBeHit && nv.tooLate,
   'NV canBeHit remains based on captured hitbox while late follows the live global edge');
  nv.wasGoodHit = true;
  nv.tooLate = false;
  nv.updateSourceTiming();
  check(!nv.tooLate, 'already-hit NV note is not marked late');
 }
}
'''
        fixture = (fixture.replace("__SOURCE_MODE__", source_mode)
                   .replace("__MEMBERS__", members)
                   .replace("__GETTERS__", getters)
                   .replace("__CONSTRUCTOR_TIMING__", constructor_timing)
                   .replace("__PSYCH_UPDATE__", psych_update_branch))
        self.run_haxe(fixture, "Main")

    def test_actual_safe_zone_capture_and_restoration_are_once_only(self):
        play = self.play
        init = extract_method(play, "function initializeSourceSafeZone(prefs:Dynamic)")
        init = init.replace("function initializeSourceSafeZone", "public function initializeSourceSafeZone", 1)
        destroy_start = play.index("function destroy()")
        # Isolate the actual safe-zone restoration block rather than unrelated
        # cleanup now inserted between it and superclass destruction.
        restore = extract_method(play[destroy_start:], "if (sourcePreviousSafeZone != null) {")

        fixture = r'''
import SourceNoteTiming;
class Conductor { public static var safeZoneOffset:Float = 0; }
class SafeZoneOwner {
 public var playbackRate:Float = 1;
 public var sourcePreviousSafeZone:Null<Float>;
 public function new() {}
 __INITIALIZE__
 public function restoreSourceSafeZone():Void {
  __RESTORE__
 }
}
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function near(actual:Float, expected:Float, message:String):Void
  if (Math.abs(actual - expected) > 0.0001) throw message + ': ' + actual + ' != ' + expected;
 static function main():Void {
  Conductor.safeZoneOffset = 166;
  var owner = new SafeZoneOwner();
  owner.playbackRate = 2;
  owner.initializeSourceSafeZone({safeFrames:6});
  near(Conductor.safeZoneOffset, 200, 'safe frames are scaled by playback rate');
  near(owner.sourcePreviousSafeZone, 166, 'first activation captures the host safe zone');

  owner.playbackRate = 1;
  owner.initializeSourceSafeZone({safeFrames:12});
  near(Conductor.safeZoneOffset, 200, 'later source preference changes update the active window');
  near(owner.sourcePreviousSafeZone, 166, 'reinitialization preserves the original host value');

  owner.restoreSourceSafeZone();
  near(Conductor.safeZoneOffset, 166, 'owner restoration returns the host safe zone');
  check(owner.sourcePreviousSafeZone == null, 'restoration consumes the saved value');
  Conductor.safeZoneOffset = 7;
  owner.restoreSourceSafeZone();
  near(Conductor.safeZoneOffset, 7, 'repeated restoration does not overwrite later state');

  owner.initializeSourceSafeZone({safeFrames:3});
  near(owner.sourcePreviousSafeZone, 7, 'a later owner activation captures its own baseline');
  owner.restoreSourceSafeZone();
  near(Conductor.safeZoneOffset, 7, 'a later owner restores its own baseline');
 }
}
'''
        fixture = fixture.replace("__INITIALIZE__", init).replace("__RESTORE__", restore)
        self.run_haxe(fixture, "Main")


if __name__ == "__main__":
    unittest.main()
