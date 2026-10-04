"""Executable constructor contracts for the Psych and NV rating APIs."""

from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath
from tools.tests.test_psych_character_scope import extract_method


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"


class SourceRatingApiTest(unittest.TestCase):
    def test_psych_constructor_defaults_and_nv_factory_are_distinct(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        fixture = r'''
import PsychRatingCompat;
import PsychClientPrefsCompat;
import SourceRating;

class Main {
 static function fail(message:String):Void throw message;
 static function check(value:Bool, message:String):Void if (!value) fail(message);
 static function eq(actual:Dynamic, expected:Dynamic, message:String):Void
  if (actual != expected) fail(message + ': expected ' + expected + ', got ' + actual);

 static function main():Void {
  var psychGood = new PsychRatingCompat('good');
  eq(psychGood.name, 'good', 'Psych constructor keeps the requested name');
  eq(psychGood.image, 'good', 'Psych constructor uses the name as its image');
  eq(psychGood.hitWindow, 90, 'Psych constructor reads the current Psych window');
  eq(psychGood.ratingMod, 1, 'bare Psych constructor does not apply the NV good modifier');
  eq(psychGood.score, 350, 'bare Psych constructor keeps its generic score');
  eq(psychGood.noteSplash, true, 'bare Psych constructor keeps its generic splash flag');
  eq(psychGood.hits, 0, 'Psych descriptor starts with zero hits');

  var customPsych = new PsychRatingCompat('custom');
  var nullableWindow:Null<Float> = customPsych.hitWindow;
  check(nullableWindow == null, 'missing Psych windows stay nullable');
  eq(customPsych.ratingMod, 1, 'unknown Psych names retain constructor defaults');
  eq(customPsych.score, 350, 'unknown Psych names retain generic score');
  eq(customPsych.noteSplash, true, 'unknown Psych names retain generic splash flag');
  var shitPsych = new PsychRatingCompat('shit');
  check(shitPsych.hitWindow == null, 'Psych shit window remains null when source prefs omit it');

  var psychDefaults:Array<SourceRating> = PsychRatingCompat.loadDefault();
  eq(psychDefaults.length, 4, 'Psych default list has four ordered descriptors');
  eq(psychDefaults[0].name, 'sick', 'Psych default list begins with sick');
  eq(psychDefaults[1].name, 'good', 'Psych default list puts good second');
  eq(psychDefaults[2].name, 'bad', 'Psych default list puts bad third');
  eq(psychDefaults[3].name, 'shit', 'Psych default list ends with shit');
  eq(psychDefaults[1].ratingMod, 0.67, 'Psych good list override matches donor');
  eq(psychDefaults[1].score, 200, 'Psych good score override matches donor');
  eq(psychDefaults[1].noteSplash, false, 'Psych good splash override matches donor');
  eq(psychDefaults[2].ratingMod, 0.34, 'Psych bad list override matches donor');
  eq(psychDefaults[2].score, 100, 'Psych bad score override matches donor');
  check(SourceRating.judge(psychDefaults, 45) == psychDefaults[0],
    'Psych first window is inclusive');
  check(SourceRating.judge(psychDefaults, 45.01) == psychDefaults[1],
    'Psych proceeds to the next ordered window');
  check(SourceRating.judge(psychDefaults, 135) == psychDefaults[2],
    'Psych bad window is inclusive');
  check(SourceRating.judge(psychDefaults, 135.01) == psychDefaults[3],
    'Psych final descriptor catches later hits');

  var nvGood = SourceRating.nightmareConstructor('good', {goodWindow:81});
  eq(nvGood.hitWindow, 81, 'NV constructor uses the supplied preference view');
  eq(nvGood.ratingMod, 0.7, 'NV good constructor applies the source modifier');
  eq(nvGood.score, 200, 'NV good constructor applies the source score');
  eq(nvGood.noteSplash, false, 'NV good constructor disables note splashes');
  eq(nvGood.counter, 'goods', 'NV constructor derives its source counter');
  var nestedNv = SourceRating.nightmareConstructor('bad', {data:{badWindow:127}});
  eq(nestedNv.hitWindow, 127, 'NV constructor accepts a nested data preference view');
  var missingNv = SourceRating.nightmareConstructor('custom', {});
  eq(missingNv.hitWindow, 0, 'NV constructor maps a missing preference to zero');
  eq(missingNv.ratingMod, 1, 'custom NV names keep generic source modifier');
  eq(missingNv.score, 350, 'custom NV names keep generic source score');
  eq(missingNv.noteSplash, true, 'custom NV names keep generic splash default');
  eq(missingNv.toString(), '(name: custom | ratingMod: 1 | score: 350)',
    'NV debug string follows FlxStringUtil field ordering');
  nvGood.ratingMod = 0.712345;
  eq(nvGood.toString(), '(name: good | ratingMod: 0.712 | score: 200)',
    'NV debug string rounds floats to the default three decimal places');

  var existingNvDefaults = SourceRating.nightmareDefaults(null, false);
  eq(existingNvDefaults.length, 4, 'existing ledger factory keeps its no-Epic list');
  eq(existingNvDefaults[0].hitWindow, 45, 'existing ledger factory retains source defaults');
 }
}
'''

        with tempfile.TemporaryDirectory(prefix="source-rating-api-", dir=ROOT / "tmp") as scratch:
            scratch = FixturePath(scratch)
            (scratch / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(scratch),
                 "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_extracted_conductor_judges_the_caller_order_without_mutation(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        conductor_source = (ROOT / "source/Conductor.hx").read_text()
        method = extract_method(conductor_source, "@:keep public static function judgeNote(")
        self.assertIn("arr:Array<SourceRating>", method)
        self.assertIn("diff:Float = 0", method)
        self.assertIn("return SourceRating.judge(arr, diff);", method)
        fixture = r'''
import SourceRating;

class ExtractedConductor {
__HOST_JUDGE__
}

class Main {
 static function fail(message:String):Void throw message;
 static function check(value:Bool, message:String):Void if (!value) fail(message);
 static function main():Void {
  var sharp = new SourceRating('sharp', 20);
  var soft = new SourceRating('soft', 45);
  var fallback = new SourceRating('fallback', 90);
  sharp.ratingMod = 0.81;
  sharp.score = 41;
  var ratings:Array<SourceRating> = [sharp, soft, fallback];
  var original:Array<SourceRating> = ratings.copy();
  var originalWindow = sharp.hitWindow;
  var originalHits = sharp.hits;
  var originalMod = sharp.ratingMod;
  var originalScore = sharp.score;

  check(ExtractedConductor.judgeNote(ratings, 20) == sharp,
    'the first inclusive window returns the original descriptor');
  check(ExtractedConductor.judgeNote(ratings, 20.01) == soft,
    'ordered caller data selects the next descriptor after the first edge');
  check(ExtractedConductor.judgeNote(ratings, 45) == soft,
    'the second inclusive window returns the original descriptor');
  check(ExtractedConductor.judgeNote(ratings, 45.01) == fallback,
    'the ordered final descriptor catches later differences');
  check(ExtractedConductor.judgeNote(ratings) == sharp,
    'the extracted Conductor signature retains its zero-difference default');

  check(ratings.length == original.length
    && ratings[0] == original[0] && ratings[1] == original[1] && ratings[2] == original[2],
    'judgement preserves caller array order and descriptor identities');
  check(sharp.hitWindow == originalWindow && sharp.hits == originalHits
    && sharp.ratingMod == originalMod && sharp.score == originalScore,
    'judgement does not mutate descriptor state');

  var nullWindow = new SourceRating('nullable');
  nullWindow.hitWindow = null;
  var nullRatings:Array<SourceRating> = [nullWindow, fallback];
  check(ExtractedConductor.judgeNote(nullRatings, 0) == fallback,
    'a nullable first window fails the donor’s direct <= comparison and falls through');
  check(ExtractedConductor.judgeNote(nullRatings, 0.01) == fallback,
    'positive differences also fall through a nullable window');
 }
}
'''.replace("__HOST_JUDGE__", method)

        with tempfile.TemporaryDirectory(prefix="conductor-rating-", dir=ROOT / "tmp") as scratch:
            scratch = FixturePath(scratch)
            (scratch / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(scratch),
                 "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_psych_donor_conductor_signature_and_ordered_comparison(self):
        donor_path = Path(
            "C:/Users/uwucammie/Documents/coding/FNF/fnf_sources/"
            "FNF-PsychEngine/source/backend/Conductor.hx"
        )
        if not donor_path.is_file():
            self.skipTest("local Psych donor source is not mounted")
        donor_source = donor_path.read_text()
        donor_method = extract_method(donor_source, "public static function judgeNote(")
        self.assertIn("judgeNote(arr:Array<Rating>, diff:Float=0):Rating", donor_method)
        self.assertIn("for(i in 0...data.length-1)", donor_method)
        self.assertIn("if (diff <= data[i].hitWindow)", donor_method)
        self.assertIn("return data[data.length - 1];", donor_method)


if __name__ == "__main__":
    unittest.main()
