"""Executable checks for PlayState's source-scoring ledger adapters."""

from pathlib import Path
import subprocess
import tempfile
import unittest
import re

from haxe_test_support import HAXE_COMMAND, FixturePath


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"


def extract_method(source: str, marker: str) -> str:
    """Extract a Haxe method while ignoring braces in comments and strings."""
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


class PlayStateSourceScoringTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        markers = (
            "function initializeSourceRatings(",
            "function changeSourceRatingCounter(",
            "function judgeSourceNote(",
            "function applySourceScoredHit(",
            "function applySourceMiss(",
            "function refreshSourceAccuracy(",
            "function sourceRatingHits(",
        )
        cls.methods = "\n".join(
            extract_method(cls.play, marker).replace(marker, "public " + marker, 1)
            for marker in markers
        )

    def test_source_hit_miss_ledger_and_native_routing(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        fixture = r'''
import SourceRating;
import PsychRatingCompat;
import PsychClientPrefsCompat;
class Conductor {
 public static var songPosition:Float = 0;
}
class Note {
 public var isSustainNote:Bool = false;
 public var hitCausesMiss:Bool = false;
 public var canMiss:Bool = false;
 public var ratingDisabled:Bool = false;
 public var strumTime:Float = 0;
 public var rating:Dynamic = null;
 public var ratingMod:Float = 0;
 public function new(?sustain:Bool = false, ?hurt:Bool = false, ?missable:Bool = false,
  ?disabled:Bool = false) {
  isSustainNote = sustain;
  hitCausesMiss = hurt;
  canMiss = missable;
  ratingDisabled = disabled;
 }
}
class ScoringHost {
 public var sourceScoreOwner:Bool = false;
 public var sourceScoreNightmare:Bool = false;
 public var demoMode:Bool = false;
 public var practiceMode:Bool = false;
 public var defaultScoreAddition:Bool = true;
 public var endingSong:Bool = false;
 public var playbackRate:Float = 1;
 public var nightmareVisionPrefs:Dynamic = null;
 public var ratingsData:Array<SourceRating> = [];
 public var sourceAcceptedHits:Int = 0;
 public var totalNotesHit:Float = 0;
 public var totalPlayed:Int = 0;
 public var songScore:Int = 0;
 public var misses:Int = 0;
 public var epics:Int = 0;
 public var sicks:Int = 0;
 public var goods:Int = 0;
 public var bads:Int = 0;
 public var shits:Int = 0;
 public var accuracy:Float = 0;
 public var accuracyWrites:Int = 0;
 public var ratingNotifications:Int = 0;

 public function new(nightmare:Bool = false) sourceScoreNightmare = nightmare;
 public function notifyPsychRatingChange(?missed:Bool = false, ?scoreBop:Bool = true):Void
  ratingNotifications++;
 public function setAllHaxeVar(name:String, value:Dynamic):Void
  if (name == 'accuracy') accuracyWrites++;
 public function sourceScoreLedgerActive():Bool return sourceScoreOwner;

 __EXTRACTED_METHODS__
}

class PlayStateSourceScoringFixture {
 static function fail(message:String):Void throw message;
 static function check(value:Bool, message:String):Void if (!value) fail(message);
 static function eq(actual:Dynamic, expected:Dynamic, message:String):Void
  if (actual != expected) fail(message + ': expected ' + expected + ', got ' + actual);

 static function main():Void {
  PsychClientPrefsCompat.data = {useEpicRankings:false, sickWindow:45, goodWindow:90, badWindow:135};

  var psych = new ScoringHost(false);
  psych.sourceScoreOwner = true;
  psych.initializeSourceRatings(PsychClientPrefsCompat.data);
  check(Std.isOfType(psych.ratingsData[0], PsychRatingCompat),
   'Psych ledger uses descriptors from the bound Psych Rating class');
  var psychSick = psych.ratingsData[0];
  var psychHead = new Note();
  psychHead.strumTime = 100;
  Conductor.songPosition = 60;
  psych.practiceMode = true;
  PsychClientPrefsCompat.data.ratingOffset = 5;
  var psychJudgement = psych.judgeSourceNote(psychHead);
  check(psychJudgement == psych.ratingsData[0], 'Psych inclusive 45 ms boundary selects sick');
  eq(psychHead.rating, 'sick', 'Psych note rating remains the source string');
  eq(psychHead.ratingMod, 1, 'Psych note receives scalar ratingMod');
  PsychClientPrefsCompat.data.ratingOffset = 5.02;
  psych.playbackRate = 1;
  psychJudgement = psych.judgeSourceNote(psychHead);
  check(psychJudgement == psych.ratingsData[1], 'Psych rating offset moves the note past the sick edge');
  eq(psychHead.rating, 'good', 'Psych good judgment is a string');
  eq(psychHead.ratingMod, 0.67, 'Psych good note has scalar .67 ratingMod');
  PsychClientPrefsCompat.data.ratingOffset = 50;
  psych.playbackRate = 2;
  psychJudgement = psych.judgeSourceNote(psychHead);
  check(psychJudgement == psych.ratingsData[0], 'Psych playback rate divides adjusted hit difference');
  PsychClientPrefsCompat.data.ratingOffset = 5;
  psych.playbackRate = 1;
  check(psych.applySourceScoredHit(psychHead, psychSick), 'Psych head recalculates in practice');
  eq(psych.totalNotesHit, 1, 'Psych sick hit adds source weight');
  eq(psych.songScore, 350, 'Psych practice still awards source hit score');
  eq(psych.totalPlayed, 1, 'Psych head enters denominator');
  eq(psych.sourceAcceptedHits, 1, 'Psych accepted-hit tally advances');
  eq(psych.sicks, 1, 'Psych counter maps from descriptor name');
  eq(psychSick.hits, 1, 'Psych descriptor retains its per-rating hits');
  eq(psych.accuracy, 100, 'Psych accuracy refresh uses source numerator/denominator');
  eq(psych.ratingNotifications, 1, 'eligible Psych hit notifies score scripts');

  var psychSustain = new Note(true);
  check(!psych.applySourceScoredHit(psychSustain, psychSick), 'Psych sustain does not enter head ledger');
  var psychHurt = new Note(false, true);
  check(!psych.applySourceScoredHit(psychHurt, psychSick), 'Psych hurt note does not enter head ledger');
  eq(psych.totalPlayed, 1, 'sustain and hurt notes leave denominator unchanged');

  var disabled = new ScoringHost(false);
  disabled.sourceScoreOwner = true;
  disabled.initializeSourceRatings(PsychClientPrefsCompat.data);
  var disabledRating = disabled.ratingsData[0];
  var disabledHead = new Note(false, false, false, true);
  check(!disabled.applySourceScoredHit(disabledHead, disabledRating),
   'ratingDisabled hit skips tally/recalculation');
  eq(disabled.totalNotesHit, 1, 'ratingDisabled still contributes weighted numerator');
  eq(disabled.songScore, 350, 'ratingDisabled may still award score');
  eq(disabled.totalPlayed, 0, 'ratingDisabled skips denominator');
  eq(disabled.sourceAcceptedHits, 0, 'ratingDisabled skips accepted-hit count');
  eq(disabledRating.hits, 0, 'ratingDisabled skips Psych rating tally');
  eq(disabled.sicks, 0, 'ratingDisabled skips mapped counter');
  eq(disabled.accuracyWrites, 0, 'ratingDisabled does not refresh accuracy');
  eq(disabled.ratingNotifications, 0, 'ratingDisabled does not notify recalculation');

  PsychClientPrefsCompat.data = {useEpicRankings:false, sickWindow:45, goodWindow:90, badWindow:135};
  var nv = new ScoringHost(true);
  nv.sourceScoreOwner = true;
  nv.nightmareVisionPrefs = {view:{ratingOffset:5}};
  nv.initializeSourceRatings(PsychClientPrefsCompat.data);
  var nvSick = nv.ratingsData[0];
  var nvJudgementNote = new Note();
  nvJudgementNote.strumTime = 100;
  Conductor.songPosition = 60;
  PsychClientPrefsCompat.data.ratingOffset = -999;
  var nvJudgement = nv.judgeSourceNote(nvJudgementNote);
  check(nvJudgement == nv.ratingsData[0], 'NV uses view ratingOffset and inclusive sick edge');
  check(nvJudgementNote.rating == nvJudgement, 'NV note stores the live SourceRating descriptor');
  eq(nvJudgement.ratingMod, 1, 'NV descriptor keeps unit sick weight');
  nv.nightmareVisionPrefs.view.ratingOffset = 30;
  nvJudgement = nv.judgeSourceNote(nvJudgementNote);
  check(nvJudgement == nv.ratingsData[1], 'NV adjusted time selects good after sick');
  check(nvJudgementNote.rating == nv.ratingsData[1], 'NV note retains the selected descriptor reference');
  eq(nvJudgement.ratingMod, 0.7, 'NV good descriptor uses source .7 weight');
  PsychClientPrefsCompat.data.ratingOffset = 5;
  var descriptorReference = nv.ratingsData[0];
  check(nvSick.counterChanged != null, 'NV initialization installs a typed counter callback');
  check(nv.applySourceScoredHit(new Note(), nvSick), 'eligible NV hit recalculates');
  check(nv.ratingsData[0] == descriptorReference, 'ledger retains the descriptor used for scoring');
  eq(nvSick.hits, 1, 'NV descriptor increment is retained');
  eq(nv.sicks, 1, 'NV typed callback updates the owner counter');
  eq(nv.songScore, 350, 'NV normal hit awards descriptor score');
  eq(nv.totalNotesHit, 1, 'NV normal hit adds descriptor weight');
  eq(nv.totalPlayed, 1, 'NV normal hit enters denominator');
  eq(nv.sourceAcceptedHits, 1, 'NV normal hit increments accepted-hit count');
  check(!nv.applySourceScoredHit(new Note(false, false, true), nvSick),
   'NV canMiss note stays outside scored ledger');
  eq(nv.totalPlayed, 1, 'NV canMiss head leaves denominator unchanged');

  var psychCounters = new ScoringHost(false);
  psychCounters.sourceScoreOwner = true;
  psychCounters.sicks = 20;
  psychCounters.goods = 30;
  psychCounters.bads = 40;
  psychCounters.shits = 50;
  psychCounters.initializeSourceRatings(PsychClientPrefsCompat.data);
  check(Std.isOfType(psychCounters.ratingsData[0], PsychRatingCompat),
   'each Psych ledger initialization creates Psych-compatible rating instances');
  psychCounters.ratingsData[0].hits = 2;
  psychCounters.ratingsData[1].hits = 3;
  psychCounters.ratingsData[2].hits = 4;
  psychCounters.ratingsData[3].hits = 5;
  eq(psychCounters.sourceRatingHits(0, psychCounters.sicks), 2,
   'Psych source snapshot reads mutable sick descriptor hits');
  eq(psychCounters.sourceRatingHits(1, psychCounters.goods), 3,
   'Psych source snapshot reads mutable good descriptor hits');
  eq(psychCounters.sourceRatingHits(2, psychCounters.bads), 4,
   'Psych source snapshot reads mutable bad descriptor hits');
  eq(psychCounters.sourceRatingHits(3, psychCounters.shits), 5,
   'Psych source snapshot reads mutable shit descriptor hits');
  var nvCounters = new ScoringHost(true);
  nvCounters.sourceScoreOwner = true;
  nvCounters.sicks = 12;
  nvCounters.goods = 13;
  nvCounters.bads = 14;
  nvCounters.shits = 15;
  nvCounters.initializeSourceRatings(PsychClientPrefsCompat.data);
  nvCounters.ratingsData[0].hits = 99;
  nvCounters.ratingsData[1].hits = 98;
  nvCounters.ratingsData[2].hits = 97;
  nvCounters.ratingsData[3].hits = 96;
  eq(nvCounters.sourceRatingHits(0, nvCounters.sicks), 12,
   'NV source snapshot reads state counters instead of Psych Rating.hits');
  eq(nvCounters.sourceRatingHits(1, nvCounters.goods), 13, 'NV good FC counter comes from host state');
  eq(nvCounters.sourceRatingHits(2, nvCounters.bads), 14, 'NV bad FC counter comes from host state');
  eq(nvCounters.sourceRatingHits(3, nvCounters.shits), 15, 'NV shit FC counter comes from host state');
  nvCounters.sourceScoreOwner = false;
  eq(nvCounters.sourceRatingHits(0, 7), 7, 'native snapshot falls back to native counter');

  var cpu = new ScoringHost(true);
  cpu.sourceScoreOwner = true;
  cpu.demoMode = true;
  cpu.initializeSourceRatings(PsychClientPrefsCompat.data);
  var cpuSick = cpu.ratingsData[0];
  check(!cpu.applySourceScoredHit(new Note(), cpuSick), 'NV autoplay is excluded from judged denominator');
  eq(cpu.totalNotesHit, 1, 'NV autoplay still adds raw source weight');
  eq(cpu.sicks, 1, 'NV autoplay still increments rating counter before scoring gate');
  eq(cpu.songScore, 0, 'NV CPU path does not award score');
  eq(cpu.totalPlayed, 0, 'NV CPU path does not increment totalPlayed');
  eq(cpu.sourceAcceptedHits, 0, 'NV CPU path does not count a normal player hit');
  eq(cpu.accuracyWrites, 0, 'NV CPU path does not recalculate accuracy');

  var practice = new ScoringHost(true);
  practice.sourceScoreOwner = true;
  practice.practiceMode = true;
  practice.initializeSourceRatings(PsychClientPrefsCompat.data);
  var practiceSick = practice.ratingsData[0];
  check(!practice.applySourceScoredHit(new Note(), practiceSick),
   'NV practice hit stays outside denominator');
  eq(practice.songScore, 0, 'NV practice hit does not award score');
  eq(practice.totalNotesHit, 1, 'NV practice hit still updates numerator');
  eq(practice.sicks, 1, 'NV practice hit still updates source rating tally');

  var noDefaultScore = new ScoringHost(true);
  noDefaultScore.sourceScoreOwner = true;
  noDefaultScore.defaultScoreAddition = false;
  noDefaultScore.initializeSourceRatings(PsychClientPrefsCompat.data);
  var noDefaultSick = noDefaultScore.ratingsData[0];
  check(noDefaultScore.applySourceScoredHit(new Note(), noDefaultSick),
   'NV score-addition toggle does not suppress judgement bookkeeping');
  eq(noDefaultScore.songScore, 0, 'NV defaultScoreAddition suppresses only score delta');
  eq(noDefaultScore.sicks, 1, 'NV score-addition toggle retains rating tally');
  eq(noDefaultScore.totalPlayed, 1, 'NV score-addition toggle retains denominator');
  eq(noDefaultScore.sourceAcceptedHits, 1, 'NV score-addition toggle retains accepted-hit count');

  var fieldAuto = new ScoringHost(true);
  fieldAuto.sourceScoreOwner = true;
  fieldAuto.initializeSourceRatings(PsychClientPrefsCompat.data);
  var autoSick = fieldAuto.ratingsData[0];
  check(!fieldAuto.applySourceScoredHit(new Note(), autoSick, true),
   'NV field autoplay is excluded from denominator');
  eq(fieldAuto.songScore, 0, 'NV field autoplay does not award score');
  eq(fieldAuto.totalNotesHit, 1, 'NV field autoplay still contributes rating weight');
  eq(fieldAuto.sicks, 1, 'NV field autoplay still increments rating tally');

  var nvMiss = new ScoringHost(true);
  nvMiss.sourceScoreOwner = true;
  nvMiss.practiceMode = true;
  nvMiss.endingSong = true;
  nvMiss.totalNotesHit = 0.75;
  nvMiss.totalPlayed = 2;
  nvMiss.applySourceMiss();
  eq(nvMiss.misses, 1, 'NV miss is counted even when endingSong is true');
  eq(nvMiss.totalPlayed, 3, 'NV miss enters denominator');
  eq(nvMiss.totalNotesHit, 0.75, 'miss never subtracts from source numerator');
  eq(nvMiss.songScore, 0, 'NV practice miss does not remove score');
  eq(nvMiss.accuracy, 25, 'NV miss refreshes weighted accuracy');

  var psychMiss = new ScoringHost(false);
  psychMiss.sourceScoreOwner = true;
  psychMiss.endingSong = true;
  psychMiss.totalNotesHit = 0.5;
  psychMiss.totalPlayed = 1;
  psychMiss.applySourceMiss();
  eq(psychMiss.misses, 0, 'Psych ending miss does not increment the miss counter');
  eq(psychMiss.totalPlayed, 2, 'Psych ending miss still enters denominator');
  eq(psychMiss.totalNotesHit, 0.5, 'Psych miss never subtracts source numerator');
  eq(psychMiss.songScore, -10, 'Psych source miss keeps its score penalty');
  eq(psychMiss.accuracy, 25, 'Psych miss refreshes accuracy after denominator change');

  var native = new ScoringHost(false);
  check(!native.sourceScoreLedgerActive(), 'native host leaves source ledger inactive');
  native.sourceScoreOwner = true;
  check(native.sourceScoreLedgerActive(), 'source owner activates source ledger');
 }
}
'''.replace("__EXTRACTED_METHODS__", self.methods)

        pop_up = extract_method(self.play, "private function popUpScore(strumtime:Float, daNote:Note")
        self.assertIn("var sourceLedger = sourceScoreLedgerActive();", pop_up)
        self.assertRegex(pop_up,
            r"if\s*\(sourceLedger\s*&&\s*\(daNote\.isSustainNote\s*\|\|\s*"
            r"\(sourceScoreNightmare\s*&&\s*\(daNote\.hitCausesMiss\s*\|\|\s*"
            r"daNote\.canMiss\)\)\)\)\s*return;")
        self.assertEqual(pop_up.count("applySourceScoredHit("), 1)
        source_branch = pop_up.index("if (sourceLedger) {")
        source_apply = pop_up.index("applySourceScoredHit(", source_branch)
        native_branch = pop_up.index("} else {", source_branch)
        self.assertLess(source_branch, source_apply)
        self.assertLess(source_apply, native_branch)
        self.assertRegex(self.play,
            r"public function sourceScoreLedgerActive\(\):Bool return sourceScoreOwner;")

        note_miss = extract_method(self.play, "function noteMissCore(direction:Int = 1,")
        self.assertRegex(note_miss,
            r"if\s*\(sourceScoreLedgerActive\(\)\)\s*\{\s*if\s*\(countsMiss\)\s*"
            r"applySourceMiss\(\);\s*\}\s*else\s*misses \+= 1;")
        self.assertIn("if (!sourceScoreLedgerActive()) updateAccuracy();", note_miss)
        note_miss_wrapper = extract_method(self.play, "function noteMiss(direction:Int = 1,")
        self.assertIn("field.onNoteMiss.dispatch(note, field)", note_miss_wrapper)
        self.assertIn("noteMissCore(direction, playerOne, note, playMissSound, sourceLine);", note_miss_wrapper)

        with tempfile.TemporaryDirectory(prefix="playstate-source-scoring-", dir=ROOT / "tmp") as scratch:
            scratch = FixturePath(scratch)
            (scratch / "PsychClientPrefsCompat.hx").write_text(r'''
class PsychClientPrefsCompat {
 public static var data:Dynamic = {
  noteSkin:'Default', ratingOffset:0.0, sickWindow:45.0, goodWindow:90.0,
  badWindow:135.0, safeFrames:10.0, lowQuality:false, scoreZoom:true,
  antialiasing:true, shaders:true
 };
}
''', encoding="utf-8", newline="\n")
            for module in ("SourceRating", "SourceScoreLedger", "PsychRatingCompat", "SourceNoteTiming"):
                (scratch / f"{module}.hx").write_text(
                    (ROOT / f"source/{module}.hx").read_text(encoding="utf-8"),
                    encoding="utf-8", newline="\n")
            (scratch / "PlayStateSourceScoringFixture.hx").write_text(
                fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(scratch),
                 "--main", "PlayStateSourceScoringFixture", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
