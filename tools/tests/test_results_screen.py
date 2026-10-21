"""Results screen: lazer-style model values, and the song end opening it without reloading characters."""
from pathlib import Path
import math, subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]


class ResultsScreenTest(unittest.TestCase):
    def test_model_values(self):
        main = r'''
import ResultsModel;
class Main {
 static function check(v:Bool, s:String) if (!v) throw s;
 static function player(id:String, score:Int, acc:Float, quit:Bool = false):ResultsPlayer
  return {id:id, name:id, score:score, accuracy:acc, maxCombo:1, rank:"S", sicks:0, goods:0, bads:0, shits:0, misses:0,
   modifiers:[], failed:false, quit:quit};
 static function main() {
  check(ResultsModel.formatScore(0) == "0" && ResultsModel.formatScore(999) == "999", "small");
  check(ResultsModel.formatScore(1000000) == "1,000,000" && ResultsModel.formatScore(845891) == "845,891", "commas");
  check(ResultsModel.formatAccuracy(1) == "100.00%" && ResultsModel.formatAccuracy(0.98364) == "98.36%", "acc");
  check(ResultsModel.formatAccuracy(0.99999) == "99.99%", "never rounds up to 100");
  check(ResultsModel.formatAccuracy(0.0505) == "5.05%" && ResultsModel.formatAccuracy(Math.NaN) == "0.00%", "acc edges");
  var ordered = ResultsModel.ordered([player("a", 10, 0.5), player("b", 20, 0.4), player("c", 20, 0.9), player("q", 99, 1, true)]);
  check([for (p in ordered) p.id].join(",") == "c,b,a,q", "order " + [for (p in ordered) p.id].join(","));
  var stats = ResultsModel.hitErrors([10.0, -10.0, 10.0, -10.0]);
  check(stats.count == 4 && stats.mean == 0 && Math.abs(stats.unstableRate - 100) < 1e-9, "ur");
  check(ResultsModel.hitErrors([]).count == 0, "empty");
  var bins = ResultsModel.histogram([-200.0, -1.0, 0.0, 1.0, 200.0], 4, 100);
  check(bins.join(",") == "1,1,2,1", "histogram " + bins.join(","));
  check(ResultsModel.meanLabel(3.24) == "3.2 ms late" && ResultsModel.meanLabel(-1) == "1.0 ms early", "mean");
  check(ResultsModel.meanLabel(0.01) == "on time", "on time");
  check(ResultsModel.fillEase(0) == 0 && ResultsModel.fillEase(1) == 1 && ResultsModel.fillEase(0.5) > 0.99, "ease");
  check(ResultsModel.musicFor(0.9) == "goodScore" && ResultsModel.musicFor(0.55) == "mehScore" && ResultsModel.musicFor(0.1) == "badScore", "music");
  check(ResultsModel.modifierNames([], new Map()) == "No modifiers", "no mods");
  check(ResultsModel.modifierNames(["invis", "x"], ["invis" => "Invisible Notes"]) == "Invisible Notes, x", "mods");
  for (seg in ResultsModel.SEGMENTS) check(ResultsModel.rankColor(seg[2]) != ResultsModel.rankColor("F") || seg[2] == "F", "colour " + seg[2]);
  Sys.println("ok");
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temp:
            Path(temp, "Main.hx").write_text(main, encoding="utf-8")
            Path(temp, "ResultsModel.hx").write_text((ROOT / "source/ResultsModel.hx").read_text(encoding="utf-8"), encoding="utf-8")
            result = subprocess.run([*HAXE_COMMAND, "-cp", temp, "--run", "Main"], cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok", result.stdout)

    def test_song_end_opens_results_without_characters(self):
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        self.assertNotIn("new VictoryLoopState(", play)
        self.assertIn("new ResultsState(results)", play)
        self.assertIn("new ResultsState(week)", play)
        # The best score is read before this play is saved, so NEW BEST compares with the old one.
        self.assertLess(play.index("var previousBest = Highscore.songScores.exists(bestKey)"),
                        play.index("Highscore.saveScore(Highscore.scoreSongIdForChart(SONG)"))
        self.assertIn("standardHitOffsets.push(noteDiffSigned);", play)
        results = (ROOT / "source/ResultsState.hx").read_text(encoding="utf-8")
        for slow in ("new Character(", "makeSongCharacter", "loadGraphic(Paths"):
            self.assertNotIn(slow, results)
        self.assertIn("RuntimeSmokeHarness.tick(elapsed)", results)


if __name__ == "__main__":
    unittest.main()
