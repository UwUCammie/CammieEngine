"""Exercise source-health helpers and pin their PlayState call-site gates."""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND


ROOT = Path(__file__).resolve().parents[2]


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


def extract_block(source: str, marker: str) -> str:
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
    raise AssertionError(f"unterminated block: {marker}")


def compact(source: str) -> str:
    return "".join(source.split())


class SourceHealthWiringTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.play_source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")

    def test_extracted_health_and_counter_gates_execute(self):
        helpers = "\n".join(
            extract_method(self.play_source, marker)
            for marker in (
                "function sourceMissCounts(",
                "function applySourceMissHealth(",
                "function applySourceHitHealth(",
            )
        )
        sustain_chain = (ROOT / "source/PsychSustainChain.hx").read_text(encoding="utf-8")
        health_delta = (ROOT / "source/SourceHealthDelta.hx").read_text(encoding="utf-8")
        fixture = r'''
class Note {
  public var hitHealth:Null<Float> = null;
  public var missHealth:Null<Float> = null;
  public var isSustainNote:Bool = false;
  public var canMiss:Bool = false;
  public var blockHit:Bool = false;
  public var sourcePlayfieldIndex:Int = 0;
  public function new() {}
}
class SourceField { public var playerControls:Bool; public function new(value:Bool) playerControls = value; }
class SourceHealthWiringFixture {
  public var sourceScoreNightmare:Bool = false;
  public var healthGain:Float = 1;
  public var healthGainMultiplier:Float = 1;
  public var healthLoss:Float = 1;
  public var healthLossMultiplier:Float = 1;
  public var pressMissDamage:Null<Float> = null;
  public var holdSubdivisions:Int = 1;
  public var guitarHeroSustains:Bool = false;
  public var health:Float = 0;
  public var playerControls:Bool = true;
  public function new() {}
  function getNightmareVisionField(index:Int):SourceField return new SourceField(playerControls);
__HELPERS__

  static function near(actual:Float, expected:Float, message:String):Void {
    if (Math.abs(actual - expected) > 0.000001)
      throw message + ': ' + actual + ' != ' + expected;
  }

  static function main():Void {
    var psych = new SourceHealthWiringFixture();
    var note = new Note();
    psych.healthGain = 2;
    psych.healthGainMultiplier = 3;
    psych.applySourceHitHealth(note, true);
    near(psych.health, 0.12, 'Psych default hit composes owner and native modifiers');
    psych.health = 0;
    note.hitHealth = 0.04;
    psych.applySourceHitHealth(note, false);
    near(psych.health, -0.24, 'opponent Psych hit subtracts composed magnitude');
    note.isSustainNote = true;
    psych.guitarHeroSustains = true;
    psych.health = 0;
    psych.applySourceHitHealth(note, true);
    near(psych.health, 0, 'Psych GH sustain receives no hit-health gain');
    note.isSustainNote = false;
    psych.healthLoss = 2;
    psych.healthLossMultiplier = 3;
    psych.pressMissDamage = 0.05;
    psych.applySourceMissHealth(null, true, true);
    near(psych.health, -0.3, 'Psych empty-press miss uses authored press damage and both factors');
    psych.health = 0;
    psych.applySourceMissHealth(note, false, true);
    near(psych.health, 0.6, 'Psych note miss uses the source default and opponent sign');

    var nightmare = new SourceHealthWiringFixture();
    nightmare.sourceScoreNightmare = true;
    nightmare.healthLoss = 2;
    nightmare.healthLossMultiplier = 3;
    nightmare.healthGain = 2;
    nightmare.healthGainMultiplier = 3;
    nightmare.holdSubdivisions = 4;
    note.hitHealth = null;
    note.canMiss = true;
    note.isSustainNote = true;
    if (nightmare.sourceMissCounts(note))
      throw 'Nightmare canMiss note entered the score/miss ledger';
    nightmare.applySourceHitHealth(note, true);
    near(nightmare.health, 0.0345,
      'Nightmare canMiss state does not suppress hit health; sustain divides by hold subdivisions');
    nightmare.health = 0;
    nightmare.applySourceMissHealth(note, true, true);
    near(nightmare.health, -0.07125,
      'Nightmare sustain miss uses source default damage and hold subdivision');
    nightmare.health = 0;
    nightmare.applySourceMissHealth(null, true, true);
    near(nightmare.health, -0.3, 'Nightmare empty-press miss uses its default damage and owner factors');
    nightmare.health = 0;
    nightmare.applySourceMissHealth(null, true, false);
    near(nightmare.health, 0, 'stunned Nightmare empty press suppresses miss health reaction');
    nightmare.playerControls = false;
    nightmare.health = 0;
    nightmare.applySourceHitHealth(note, true);
    near(nightmare.health, 0, 'non-player-controlled Nightmare field receives no hit-health change');
    note.canMiss = false;
    note.blockHit = true;
    if (nightmare.sourceMissCounts(note))
      throw 'blocked Nightmare note entered the score/miss ledger';
    note.blockHit = false;
    if (nightmare.sourceMissCounts(null) != true)
      throw 'empty press should remain an eligible Nightmare miss';
    nightmare.playerControls = true;
    if (!nightmare.sourceMissCounts(note))
      throw 'ordinary player-controlled Nightmare note was excluded from miss counts';

    var unmatched:Dynamic = {parent:null, isSustainNote:true};
    if (PsychSustainChain.canHitSustain(unmatched, true))
      throw 'Psych GH sustain was allowed before a parent hit';
    unmatched.parent = {wasGoodHit:false};
    if (PsychSustainChain.canHitSustain(unmatched, true))
      throw 'Psych GH sustain was allowed with an unhit parent';
    unmatched.parent.wasGoodHit = true;
    if (!PsychSustainChain.canHitSustain(unmatched, true))
      throw 'Psych GH sustain remained blocked after its parent hit';
  }
}
'''.replace("__HELPERS__", helpers)

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            (work / "SourceHealthDelta.hx").write_text(health_delta, encoding="utf-8", newline="\n")
            (work / "PsychSustainChain.hx").write_text(sustain_chain, encoding="utf-8", newline="\n")
            (work / "SourceHealthWiringFixture.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "SourceHealthWiringFixture", "--interp"],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_nightmare_can_miss_skips_ledger_but_keeps_common_health_and_callbacks(self):
        miss_method = extract_method(self.play_source, "function noteMiss(")
        common = extract_block(miss_method, "if (sourceCommon) {")
        compact_method = compact(miss_method)
        compact_common = compact(common)

        self.assertIn(
            "if(authoredLine!=null||sourceScoreLedgerActive()||!actingOn.stunned)",
            compact_method,
        )
        self.assertIn(
            "varsourceCommon=!sourceScoreLedgerActive()||sourceScoreNightmare||PsychSustainChain.prepareMiss(note,guitarHeroSustains);",
            compact_method,
        )
        self.assertIn("varcountsMiss=!sourceScoreLedgerActive()||sourceMissCounts(note);", compact_method)
        self.assertIn(
            "varmissReaction=!(sourceScoreNightmare&&note==null&&actingOn.stunned);",
            compact_method,
        )
        self.assertIn("if(sourceScoreLedgerActive()){if(countsMiss)applySourceMiss();}", compact_common)
        # Health remains outside the countsMiss guard: NMV canMiss suppresses
        # the ledger while preserving PlayField.noteMiss damage. Reaction
        # suppression applies only to a stunned empty Nightmare press.
        self.assertIn("if(sourceScoreLedgerActive())applySourceMissHealth(note,playerOne,missReaction);", compact_common)
        self.assertIn("if(playMissSound&&missReaction)", compact_common)
        self.assertIn("if(missReaction&&(note==null||note.allowsAnimation(true)))", compact_common)
        self.assertIn("if(countsMiss)applySourceMiss();", compact_common)
        for callback in (
            'callAllHScript("playerOneMiss", []);',
            "dispatchPsychCompiledStage('noteMissPress', [direction]);",
            'callAllHScript("noteMiss", [note, playerOne, direction, hxcMissEvent], true);',
        ):
            self.assertIn(callback, miss_method)
            self.assertNotIn(callback, common)
            self.assertGreater(miss_method.index(callback), miss_method.index(common))

    def test_sustain_links_are_established_before_notes_enter_spawn_callback_queue(self):
        generation = extract_method(self.play_source, "private function generateSong(")
        self.assertLess(generation.index("sustainNote.parent = swagNote;"),
                        generation.index("unspawnNotes.push(sustainNote);"))
        self.assertLess(generation.index("swagNote.tail.push(sustainNote);"),
                        generation.index("unspawnNotes.push(sustainNote);"))

        create = extract_method(self.play_source, "override public function create()")
        update = extract_method(self.play_source, "override public function update(")
        self.assertIn("generateSong(SONG.song);", create)
        self.assertLess(update.index("var dunceNote:Note = unspawnNotes[0];"),
                        update.index("nightmareVisionNoteTypes.spawnNote(dunceNote)"))
        self.assertLess(update.index("nightmareVisionNoteTypes.spawnNote(dunceNote)"),
                        update.index("dispatchPsychNoteSpawn(dunceNote)"))


if __name__ == "__main__":
    unittest.main()
