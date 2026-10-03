"""Explicit Psych note health and ignore flags affect native judgement."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class PsychNoteHealthCompatTest(unittest.TestCase):
    def test_explicit_zero_and_scaled_health_plus_botplay_ignore(self):
        note_source = (ROOT / "source/Note.hx").read_text()
        methods = "\n".join(extract_method(note_source, marker) for marker in (
            "public function canAutoHit(", "public function getHealth(",
        ))
        fixture = '''
class OptionsHandler {
  public static var options = {useKadeHealth: false};
}
class PlayState {
  public static var healthGainMultiplier:Float = 2;
  public static var healthLossMultiplier:Float = 3;
}
class PsychNoteHealthFixture {
  public var mineNote = false;
  public var nukeNote = false;
  public var consistentHealth = false;
  public var healCutoff:Null<String> = null;
  public var damageAmount:Null<Float> = null;
  public var healAmount:Null<Float> = null;
  public var damageMultiplier:Float = 1;
  public var healMultiplier:Float = 1;
  public var ignoreHealthMods = false;
  public var hitHealth:Null<Float> = null;
  public var missHealth:Null<Float> = null;
  // Outside Nightmare Vision, Note.canMiss defaults to false.
  public var canMiss:Bool = false;
  public var nightmareVisionTypeRuntime:Dynamic = null;
  public var mustPress = true;
  public var sourcePlayfieldPlayerControlled:Null<Bool> = null;
  public var ignoreNote = false;
  public var blockHit = false;
  public var hitCausesMiss = false;
  public var avoidAutoHit = false;
  public var dontCountNote = false;
  public var aiShouldHit = false;
  public function new() {}
  public inline function isPlayerControlled():Bool
    return sourcePlayfieldPlayerControlled == null ? mustPress : sourcePlayfieldPlayerControlled;
__METHODS__
  static function main():Void {
    var note = new PsychNoteHealthFixture();
    note.hitHealth = 0;
    note.missHealth = 0;
    if (note.getHealth('sick') != 0 || note.getHealth('miss') != 0)
      throw 'explicit Psych zero health was replaced by native defaults';
    note.hitHealth = 0.1;
    note.missHealth = 0.05;
    if (Math.abs(note.getHealth('sick') - 0.2) > 0.00001
      || Math.abs(note.getHealth('miss') + 0.15) > 0.00001)
      throw 'Psych health overrides lost native gain/loss multipliers';
    if (!note.canAutoHit()) throw 'ordinary note was blocked from botplay';
    note.ignoreNote = true;
    if (note.canAutoHit()) throw 'ignored Psych note was automatically hit';
    note.ignoreNote = false;
    note.hitCausesMiss = true;
    if (note.canAutoHit()) throw 'hit-causes-miss note was automatically hit';
    note.hitCausesMiss = false;
    note.blockHit = true;
    if (note.canAutoHit()) throw 'blocked Psych player note was automatically hit';
    note.mustPress = false;
    if (!note.canAutoHit()) throw 'Psych blockHit incorrectly blocked opponent note';
  }
}
'''.replace("__METHODS__", methods)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "PsychNoteHealthFixture.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "PsychNoteHealthFixture", "--interp"],
                cwd=ROOT, env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("&& !daNote.ignoreNote", (ROOT / "source/PlayState.hx").read_text())

    def test_manual_hit_causing_miss_uses_miss_route_and_leaves_codename_alone(self):
        play_source = (ROOT / "source/PlayState.hx").read_text()
        method = extract_method(play_source, "function dispatchHitCausesMiss(")
        splash_method = extract_method(play_source, "function splashHitCausesMissNote(")
        splash_gate = extract_method(play_source, "function shouldShowNoteSplash(")
        hit_method = extract_method(play_source, "function goodNoteHit(")
        self.assertLess(hit_method.index("if (hitCodenameNote(note)) return;"),
                        hit_method.index("dispatchHitCausesMiss(note, playerOne)"))
        self.assertIn("if (hitCausesMiss)", hit_method)
        self.assertIn("finishGoodNoteHit(note, playerOne, hxcHitEvent, false)", hit_method)
        self.assertIn("!note.isSustainNote && !hitCausesMiss", hit_method)
        self.assertIn("setVocalsVolume(0)", method)
        self.assertIn("splashHitCausesMissNote(note)", method)
        self.assertIn("shouldShowNoteSplash(note)", splash_method)
        self.assertIn("!note.isSustainNote && !note.isNoteSplashDisabled()", splash_gate)
        self.assertIn("&& useNoteSplashes && grpNoteSplashes != null", splash_gate)
        finish_method = extract_method(play_source, "function finishGoodNoteHit(")
        self.assertIn("if (restoreVocals)", finish_method)

        fixture = '''
class Note {
  public var hitCausesMiss = false;
  public var wasGoodHit = false;
  public var codenameInputLine:Dynamic = null;
  public var noteData = 2;
  public var isSustainNote = false;
  public var sourcePlayfieldIndex = -1;
  public function isNoteSplashDisabled():Bool return false;
  public function new() {}
}
class Strumline {
  public var showNotesplash = true;
  public var members:Array<Int> = [0, 1, 2, 3];
  public var spawned:Array<Int> = [];
  public function new() {}
  public function doSplash(lane:Int):Int { spawned.push(lane); return lane; }
}
class SplashGroup {
  public var spawned:Array<Int> = [];
  public function new() {}
  public function add(value:Int):Void spawned.push(value);
}
class PsychManualHazardFixture {
  public var misses:Array<Note> = [];
  public var vocalVolume:Float = 1;
  public var useNoteSplashes = true;
  public var grpNoteSplashes:SplashGroup = new SplashGroup();
  public var codenameNoteSplashHandler:Dynamic = null;
  public var strumline:Strumline = new Strumline();
  public function new() {}
  function setVocalsVolume(value:Float):Void vocalVolume = value;
  function getNoteStrumline(note:Note):Strumline return strumline;
  function nightmareVisionSkinForField(field:Int):Dynamic return null;
  function noteMiss(direction:Int, playerOne:Bool, note:Null<Note>,
      ?playMissSound:Bool = true, ?sourceLine:Dynamic):Void {
    if (note == null || !note.wasGoodHit || !playerOne || direction != note.noteData)
      throw 'miss route did not receive the marked player note';
    misses.push(note);
  }
__METHOD__
__SPLASH_GATE__
__SPLASH_METHOD__
  static function main():Void {
    var state = new PsychManualHazardFixture();
    var ordinary = new Note();
    if (state.dispatchHitCausesMiss(ordinary, true) || ordinary.wasGoodHit || state.misses.length != 0)
      throw 'ordinary note entered the hit-causes-miss route';

    var opponent = new Note();
    opponent.hitCausesMiss = true;
    if (state.dispatchHitCausesMiss(opponent, false) || opponent.wasGoodHit || state.misses.length != 0)
      throw 'opponent note entered the manual player miss route';

    var codename = new Note();
    codename.hitCausesMiss = true;
    codename.codenameInputLine = {};
    if (state.dispatchHitCausesMiss(codename, true) || codename.wasGoodHit || state.misses.length != 0)
      throw 'Codename note entered the Psych hit-causes-miss route';

    var hazard = new Note();
    hazard.hitCausesMiss = true;
    if (!state.dispatchHitCausesMiss(hazard, true) || !hazard.wasGoodHit
        || state.misses.length != 1 || state.misses[0] != hazard || state.vocalVolume != 0
        || state.grpNoteSplashes.spawned.length != 1 || state.grpNoteSplashes.spawned[0] != 2)
      throw 'manual hit-causes-miss note did not dispatch one miss';
    if (state.dispatchHitCausesMiss(hazard, true) || state.misses.length != 1)
      throw 'already-hit hazard dispatched its miss twice';

    var sustainHazard = new Note();
    sustainHazard.hitCausesMiss = true;
    sustainHazard.isSustainNote = true;
    if (!state.dispatchHitCausesMiss(sustainHazard, true)
        || state.grpNoteSplashes.spawned.length != 1 || state.misses.length != 2)
      throw 'sustain hazard should miss without a note splash';

    var disabled = new Note();
    disabled.hitCausesMiss = true;
    state.useNoteSplashes = false;
    if (!state.dispatchHitCausesMiss(disabled, true)
        || state.grpNoteSplashes.spawned.length != 1 || state.misses.length != 3)
      throw 'global splash option did not gate the hazard splash';

    var lineDisabled = new Note();
    lineDisabled.hitCausesMiss = true;
    state.useNoteSplashes = true;
    state.strumline.showNotesplash = false;
    if (!state.dispatchHitCausesMiss(lineDisabled, true)
        || state.grpNoteSplashes.spawned.length != 1 || state.misses.length != 4)
      throw 'strumline splash option did not gate the hazard splash';
  }
}
'''.replace("__METHOD__", method).replace("__SPLASH_GATE__", splash_gate).replace(
            "__SPLASH_METHOD__", splash_method
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "PsychManualHazardFixture.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "PsychManualHazardFixture", "--interp"],
                cwd=ROOT, env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
