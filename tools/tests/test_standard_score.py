"""Standardised scoring (source/StandardScore.hx) agrees with an independent reference.

The Python reference below is the one the multiplayer server re-judge uses, so
these vectors also pin engine and server to the same arithmetic.
"""
from pathlib import Path
import json, math, random, subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]
BASE = {4: 300, 3: 200, 2: 100, 1: 50, 0: 0}
LOG4_CAP = math.log(400) / math.log(4)


def combo_factor(combo):
    if combo <= 1:
        return 0.5
    return min(max(0.5, math.log(combo) / math.log(4)), LOG4_CAP)


def reference_score(judgements, total, multiplier=1.0):
    maximum = sum(300 * combo_factor(i) for i in range(1, total + 1))
    combo = portion = base_sum = 0
    for judgement in judgements:
        base_sum += BASE[judgement]
        if judgement == 0:
            combo = 0
            continue
        combo += 1
        portion += BASE[judgement] * combo_factor(combo)
    judged = len(judgements)
    accuracy = 1.0 if judged == 0 else base_sum / (300.0 * judged)
    curve = 0 if accuracy <= 0 else (1 if accuracy >= 1 else accuracy ** (2 + 2 * accuracy))
    combo_progress = 0 if maximum <= 0 else min(1, portion / maximum)
    progress = 0 if total <= 0 else (1.0 if judged >= total else judged / total)
    return math.floor((150000 * combo_progress + 850000 * curve * progress) * multiplier + 0.5)


def run_haxe(main):
    with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
        Path(temp, 'Main.hx').write_text(main)
        result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', temp, '--run', 'Main'],
                                cwd=ROOT, capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return result.stdout


class StandardScoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = random.Random(20261020)
        cls.cases = []
        for total in (1, 2, 7, 64, 399, 400, 401, 1500):
            for _ in range(3):
                judged = rng.randint(0, total)
                weights = rng.choice([(90, 6, 2, 1, 1), (40, 25, 15, 10, 10), (0, 0, 0, 0, 1)])
                seq = rng.choices([4, 3, 2, 1, 0], weights=weights, k=judged)
                multiplier = rng.choice([1.0, 1.06, 1.04 * 1.06, 0.5])
                cls.cases.append((seq, total, multiplier))
        for total in (1, 10, 500):
            cls.cases.append(([4] * total, total, 1.0))
            cls.cases.append(([3] * total, total, 1.0))
        payload = json.dumps([[seq, total, multiplier] for seq, total, multiplier in cls.cases])
        main = '''class Main { static function main() {
            var cases:Array<Array<Dynamic>> = haxe.Json.parse(sys.io.File.getContent("%s"));
            var out = [];
            for (c in cases) {
                var seq:Array<Int> = c[0];
                out.push(StandardScore.scoreForJudgements(seq, c[1], c[2]));
            }
            Sys.println(haxe.Json.stringify(out));
        } }'''
        with tempfile.NamedTemporaryFile('w', suffix='.json', dir=ROOT / 'tmp', delete=False) as handle:
            handle.write(payload)
            path = Path(handle.name)
        try:
            cls.engine = json.loads(run_haxe(main % path.as_posix()).strip().splitlines()[-1])
        finally:
            path.unlink()

    def test_engine_matches_reference_vectors(self):
        for (seq, total, multiplier), engine in zip(self.cases, self.engine):
            self.assertEqual(engine, reference_score(seq, total, multiplier), (len(seq), total, multiplier))

    def test_full_sick_combo_is_one_million(self):
        for (seq, total, multiplier), engine in zip(self.cases, self.engine):
            if seq == [4] * total and multiplier == 1.0:
                self.assertEqual(engine, 1000000)

    def test_lazer_reference_points(self):
        # Full combo progress, complete run: 150000 + 850000 * acc^(2 + 2 acc).
        for accuracy in (0.95, 0.90, 0.80, 0.50):
            expected = math.floor(150000 + 850000 * accuracy ** (2 + 2 * accuracy) + 0.5)
            self.assertAlmostEqual(expected, {0.95: 845891, 0.90: 719561, 0.80: 530665, 0.50: 256250}[accuracy], delta=1)

    def test_ranks_multipliers_and_migration(self):
        main = '''import StandardScore;
        class Main { static function check(v:Bool, s:String) if (!v) throw s;
        static function main() {
            check(StandardScore.rankFromSums(300, 300) == "SS", "ss");
            check(StandardScore.rankFromSums(95, 100) == "S" && StandardScore.rankFromSums(94, 100) == "A", "s edge");
            check(StandardScore.rankFromSums(90, 100) == "A" && StandardScore.rankFromSums(80, 100) == "B", "a b");
            check(StandardScore.rankFromSums(70, 100) == "C" && StandardScore.rankFromSums(69, 100) == "D", "c d");
            check(StandardScore.rankFromSums(300, 300, true) == "SSH" && StandardScore.rankFromSums(96, 100, true) == "SH", "silver");
            check(StandardScore.rankFromSums(90, 100, true) == "A", "no silver A");
            check(StandardScore.rankFromSums(300, 300, false, true) == "F", "failed");
            check(StandardScore.rankFromSums(0, 0) == "N/A", "nothing judged");
            check(StandardScore.rankFromPercent(95.0) == "S" && StandardScore.rankFromPercent(94.99) == "A", "percent edge");
            check(StandardScore.rankFromPercent(100.0) == "SS", "percent ss");
            check(Math.abs(StandardScore.multiplierFor(["invis", "vanish"]) - 1.04 * 1.06) < 1e-12, "visual product");
            check(StandardScore.multiplierFor(["healthloss", "healthgain", "regen"]) == 0.5, "health group once");
            check(StandardScore.multiplierFor(["fc", "mfc", "loop"]) == 1.0, "fail conditions neutral");
            check(StandardScore.isUnranked(["practice"]) && StandardScore.isUnranked(["duo"]) && !StandardScore.isUnranked(["invis"]), "unranked");
            check(StandardScore.estimateComboProportion(100, 0, 100) == 1.0, "no misses");
            var est = StandardScore.estimateComboProportion(100, 3, 60);
            check(est > 0 && est < 1, "partial estimate " + est);
            check(StandardScore.estimateComboProportion(0, 0, 0) == -1, "no record");
            check(StandardScore.migratedRank(1.0, 3, false) == "S", "ss needs sick fc");
            check(StandardScore.migratedRank(1.0, 5, false) == "SS", "sick fc keeps ss");

            var t = new StandardTracker(4);
            check(t.score() == 0 && t.rank() == "N/A", "empty tracker");
            t.judge(StandardScore.SICK); t.judge(StandardScore.MISS);
            check(t.combo == 0 && t.maxCombo == 1 && t.misses == 1, "miss resets combo");
            t.judge(StandardScore.SHIT);
            check(t.combo == 1, "shit keeps combo");

            var input = {
                scores: ["a" => 900000, "a-best-score" => 900000, "b" => 1234, "week-w" => 5000, "z" => 0],
                accuracy: ["a" => 1.0, "a-best-score" => 1.0, "b" => 0.9, "week-w" => 90.0, "z" => 0.0],
                fcLevels: ["a" => 5, "a-best-score" => 5, "b" => 0, "week-w" => 0, "z" => 0],
                performance: new Map<String, PlayPerformance.PlayPerformanceRecord>(),
                modifiers: new Map<String, Dynamic>(),
                legacy: new Map<String, Int>(),
                details: new Map<String, StandardScore.ScoreDetail>()
            };
            input.modifiers.set("b", {invis: {value: true}, fc: {value: false}});
            var first = ScoreMigration.migrate(input);
            check(first.scores.get("a") == 1000000 && first.scores.get("a-best-score") == 1000000, "sick fc migrates to max");
            check(first.legacy.get("a") == 900000 && first.legacy.get("b") == 1234, "legacy kept");
            var expectedB = StandardScore.migratedScore(0.9, 0.5, 1.06);
            check(first.scores.get("b") == expectedB, "modifier multiplier applied " + first.scores.get("b"));
            check(first.scores.get("week-w") == StandardScore.migratedScore(0.9, 0.5, 1.0), "week percent");
            check(first.scores.get("z") == 0, "unplayed stays zero");
            check(input.scores.get("a") == 900000, "input untouched");
            var again = ScoreMigration.migrate({scores: first.scores, accuracy: input.accuracy, fcLevels: input.fcLevels,
                performance: input.performance, modifiers: input.modifiers, legacy: first.legacy, details: first.details});
            check(again.migrated == 0, "second run converts nothing");
            for (k in first.scores.keys()) check(again.scores.get(k) == first.scores.get(k), "idempotent " + k);
            Sys.println("ok");
        } }'''
        self.assertIn('ok', run_haxe(main))


if __name__ == '__main__':
    unittest.main()
