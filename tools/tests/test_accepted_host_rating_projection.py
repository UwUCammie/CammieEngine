"""Exercise the shared Psych/NMV popup projection against host timing tiers."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
import re


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


def method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for position in range(opening, len(source)):
        if source[position] == "{":
            depth += 1
        elif source[position] == "}":
            depth -= 1
            if depth == 0:
                return source[start : position + 1]
    raise AssertionError(marker)


class AcceptedHostRatingProjectionTest(unittest.TestCase):
    def test_actual_timing_tiers_project_only_accepted_host_strings(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe unavailable")

        ratings_source = (ROOT / "source/Ratings.hx").read_text()
        calculate_rating = method(ratings_source, "\tpublic static function CalculateRating(")
        fixture = '''
class Judge {
 public static var sickJudge:Float=45;
 public static var goodJudge:Float=90;
 public static var badJudge:Float=135;
 public static var shitJudge:Float=166;
 public static var wayoffJudge:Float=203;
}
class Conductor { public static var safeZoneOffset:Float=166; }
class ModifierState { public static var namedModifiers:Dynamic={demo:{value:false}}; }
class OptionsHandler { public static var options:Dynamic={ignoreVile:false}; }
class Ratings {
__CALCULATE_RATING__
}
class Main {
 static function check(ok:Bool,label:String):Void if(!ok)throw label;
 static function hit(diff:Float,ignoreVile:Bool,host:String,source:String):Void {
  OptionsHandler.options.ignoreVile=ignoreVile;
  var actual=Ratings.CalculateRating(diff);
  check(actual==host,'host tier at '+diff+' expected '+host+' got '+actual);
  if(source!=null) {
   var projected=PsychRatingPresentationCommon.acceptedHostRating(actual);
   check(projected.name==source && projected.image==source,
    'source visual at '+diff+' expected '+source+' got '+projected.image);
  }
 }
 static function popupRating(sourceLedger:Bool,sourceRating:Dynamic,daRating:String):Dynamic return __POPUP_PROJECTION__;
 static function main():Void {
  var live={name:'good',image:'owner/good',ratingMod:0.7,score:200};
  check(popupRating(true,live,'good')==live,'source ledger preserves the live descriptor');
  check(popupRating(false,null,'wayoff').name=='shit','native fallback projects accepted host tiers');
  hit(0,false,'sick','sick');
  hit(45,false,'sick','sick');
  hit(45.001,false,'good','good');
  hit(90,false,'good','good');
  hit(90.001,false,'bad','bad');
  hit(135,false,'bad','bad');
  hit(135.001,false,'shit','shit');
  hit(166,false,'shit','shit');
  hit(166.001,false,'wayoff','shit');
  hit(202.999,false,'wayoff','shit');
  hit(203,false,'wayoff','shit');
  OptionsHandler.options.ignoreVile=true;
  hit(166.001,true,'miss','shit');
  hit(202.999,true,'miss','shit');
  check(Ratings.CalculateRating(203.001)=='miss',
   'a note outside the host hit window remains a genuine miss');

  // The projection is applied only at the explicit accepted-host boundary.
  var raw=PsychRatingPresentationCommon.sourceRating('wayoff');
  check(raw.name=='wayoff' && raw.image=='wayoff',
   'the generic source wrapper does not rewrite authored rating strings');
  var custom={name:'custom-rating',image:'owner/custom-rating.png',token:7};
  var untouched=PsychRatingPresentationCommon.sourceRating(custom);
  check(untouched==custom && untouched.image=='owner/custom-rating.png'
   && untouched.token==7,
   'custom rating objects and their authored image pass through unchanged');
  check(PsychRatingPresentationCommon.sourceRatingImage(custom)=='owner/custom-rating.png',
   'custom image selection is preserved without an asset-existence fallback');
  check(PsychRatingPresentationCommon.acceptedHostRating('custom-rating').image=='custom-rating',
   'unknown host strings are not silently replaced with a built-in image');
  check(Judge.sickJudge==45 && Judge.goodJudge==90 && Judge.badJudge==135
   && Judge.shitJudge==166 && Judge.wayoffJudge==203,
   'presentation projection leaves personal host judge windows unchanged');
  Sys.println('accepted-host-rating-projection-ok');
 }
}
'''.replace("__CALCULATE_RATING__", calculate_rating)

        play_state = (ROOT / "source/PlayState.hx").read_text()
        popup_start = play_state.index("\tprivate function popUpScore(")
        popup_end = play_state.index("\n\tfunction ", popup_start + 1)
        popup = play_state[popup_start:popup_end]
        projection = re.search(r"var sourcePopupRating:Dynamic = ([^;]+);", popup)
        self.assertIsNotNone(projection)
        fixture = fixture.replace("__POPUP_PROJECTION__", projection.group(1))
        self.assertIn("sourceLedger ? sourceRating", projection.group(1))
        self.assertIn("PsychRatingPresentationCommon.acceptedHostRating(daRating)", projection.group(1))
        self.assertIn("playHUD.popUpScore(sourcePopupRating, sourceLedger ? combo : combo + 1, daNote);", popup)
        self.assertLess(popup.index("playHUD.popUpScore(sourcePopupRating,"),
                        popup.index("RuntimeSmokeHarness.markRatingPopup(daRating, sourcePopupRating);"))
        miss_start = play_state.index("\tfunction noteMiss(")
        miss_end = play_state.index("\n\tfunction ", miss_start + 1)
        self.assertNotIn("playHUD.popUpScore(", play_state[miss_start:miss_end])

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            (work / "Main.hx").write_text(fixture, newline='\n')
            flixel = work / "flixel"
            flixel.mkdir()
            (flixel / "FlxSprite.hx").write_text(
                "package flixel; class FlxSprite { public var x:Float=0; public var y:Float=0; }\n"
            , newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "--main", "Main", "--interp"],
                cwd=work,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("accepted-host-rating-projection-ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
