"""Executable contracts for shared Psych/Nightmare Vision rating descriptors."""

from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"


class SourceRatingTest(unittest.TestCase):
    def test_defaults_windows_judgement_and_owner_counter(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        fixture = r'''
import SourceRating;

class Main {
 static function fail(message:String):Void throw message;
 static function check(value:Bool, message:String):Void if (!value) fail(message);
 static function eq(actual:Dynamic, expected:Dynamic, message:String):Void
  if (actual != expected) fail(message + ': expected ' + expected + ', got ' + actual);

 static function main():Void {
  var psych = SourceRating.psychDefaults({data:{sickWindow:40, goodWindow:80, badWindow:120}});
  eq(psych.length, 4, 'Psych defaults omit Epic');
  eq(psych[0].name, 'sick', 'Psych first rating');
  eq(psych[1].name, 'good', 'Psych second rating');
  eq(psych[2].name, 'bad', 'Psych third rating');
  eq(psych[3].name, 'shit', 'Psych final catch-all');
  eq(psych[0].hitWindow, 40, 'Psych reads nested saved sick window');
  eq(psych[1].hitWindow, 80, 'Psych reads saved good window');
  eq(psych[2].hitWindow, 120, 'Psych reads saved bad window');
  eq(psych[3].hitWindow, 0, 'missing shit window retains source zero');
  eq(psych[0].ratingMod, 1, 'Psych sick weight');
  eq(psych[1].ratingMod, 0.67, 'Psych good weight');
  eq(psych[2].ratingMod, 0.34, 'Psych bad weight');
  eq(psych[3].ratingMod, 0, 'Psych shit weight');
  eq(psych[0].score, 350, 'Psych sick score');
  eq(psych[1].score, 200, 'Psych good score');
  eq(psych[2].score, 100, 'Psych bad score');
  eq(psych[3].score, 50, 'Psych shit score');
  eq(psych[0].noteSplash, true, 'Psych sick splashes');
  eq(psych[1].noteSplash, false, 'Psych good does not splash');
  eq(psych[0].hits, 0, 'Psych rating starts with no hits');

  check(SourceRating.judge(psych, 40) == psych[0], 'Psych window edge is inclusive');
  check(SourceRating.judge(psych, 40.01) == psych[1], 'Psych proceeds to next ordered window');
  check(SourceRating.judge(psych, 80) == psych[1], 'Psych good edge is inclusive');
  check(SourceRating.judge(psych, 80.01) == psych[2], 'Psych proceeds to bad window');
  check(SourceRating.judge(psych, 120) == psych[2], 'Psych bad edge is inclusive');
  check(SourceRating.judge(psych, 120.01) == psych[3], 'Psych final rating catches later hits');
  check(SourceRating.judge([], 10) == null, 'empty rating list returns no result');

  var nightmare = SourceRating.nightmareDefaults({
   useEpicRankings:true, epicWindow:20, sickWindow:42, goodWindow:85, badWindow:130
  });
  eq(nightmare.length, 5, 'Nightmare defaults include Epic when enabled');
  eq(nightmare[0].name, 'epic', 'Epic is prepended');
  eq(nightmare[0].counter, 'epics', 'Epic maps to the owner counter');
  eq(nightmare[0].hitWindow, 20, 'Nightmare reads its own Epic window');
  eq(nightmare[0].ratingMod, 1, 'Nightmare Epic weight');
  eq(nightmare[0].score, 500, 'Nightmare Epic score');
  eq(nightmare[0].noteSplash, true, 'Nightmare Epic splashes');
  eq(nightmare[1].counter, 'sicks', 'sick maps to the owner counter');
  eq(nightmare[1].hitWindow, 42, 'Nightmare reads its own sick window');
  eq(nightmare[2].ratingMod, 0.7, 'Nightmare good weight');
  eq(nightmare[3].ratingMod, 0.4, 'Nightmare bad weight');
  eq(nightmare[4].ratingMod, 0, 'Nightmare shit weight');
  check(SourceRating.judge(nightmare, 20) == nightmare[0], 'Nightmare Epic edge is inclusive');
  check(SourceRating.judge(nightmare, 20.01) == nightmare[1], 'Nightmare falls through to sick');
  check(SourceRating.judge(nightmare, 42) == nightmare[1], 'Nightmare sick edge is inclusive');
  check(SourceRating.judge(nightmare, 42.01) == nightmare[2], 'Nightmare falls through to good');
  check(SourceRating.judge(nightmare, 130.01) == nightmare[4], 'Nightmare shit is final fallback');

  var noEpic = SourceRating.nightmareDefaults({useEpicRankings:true}, false);
  eq(noEpic.length, 4, 'explicit Epic preference overrides saved setting');
  eq(noEpic[0].name, 'sick', 'non-Epic list begins with sick');
  var prefsDisableEpic = SourceRating.nightmareDefaults({useEpicRankings:false});
  eq(prefsDisableEpic.length, 4, 'factory uses saved Epic preference when override omitted');
  eq(SourceRating.nightmareDefaults(null).length, 5, 'missing preferences use enabled Epic source default');

  var owner:Dynamic = {epics:0};
  nightmare[0].increase(2, owner);
  eq(nightmare[0].hits, 2, 'increase tracks descriptor hits');
  eq(owner.epics, 2, 'increase updates the NV owner counter');
  var callbackRating = nightmare[1];
  var changedName = '';
  var changedAmount = 0;
  var callbackOwner:Dynamic = {sicks:7};
  callbackRating.counterChanged = function(name:String, amount:Int):Void {
   changedName = name;
   changedAmount = amount;
  };
  callbackRating.increase(3, callbackOwner);
  eq(callbackRating.hits, 3, 'typed callback path still increments rating hits');
  eq(changedName, 'sicks', 'typed callback receives the source counter name');
  eq(changedAmount, 3, 'typed callback receives the increment amount');
  eq(callbackOwner.sicks, 7, 'typed callback takes precedence over reflection fallback');
  callbackRating.increase();
  eq(callbackRating.hits, 4, 'typed callback supports source-style increase without owner');
  eq(changedAmount, 1, 'source-style increase forwards its default increment');
  var direct:SourceRating = new SourceRating('bad');
  eq(direct.hitWindow, 135, 'NV name constructor uses source default window');
  eq(direct.ratingMod, 0.4, 'NV name constructor uses source default weight');
  eq(direct.score, 100, 'NV name constructor uses source default score');
 }
}
'''

        with tempfile.TemporaryDirectory(prefix="source-rating-", dir=ROOT / "tmp") as scratch:
            scratch = FixturePath(scratch)
            (scratch / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(scratch),
                 "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
