"""Exercise the host-mapped snapshot used for Psych score-facing globals.

The current inputs include native configurable accuracy; these checks pin the
adapter contract and do not claim donor-equivalent rating math.
"""
from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"Unclosed method: {marker}")


FIXTURE = r'''
class PsychScoreScriptGlobalsTest {
    static function fail(message:String):Void throw message;

    static function check(value:Bool, message:String):Void {
        if (!value) fail(message);
    }

    static function near(actual:Float, expected:Float, message:String):Void {
        if (Math.isNaN(actual) || Math.abs(actual - expected) > 0.000001)
            fail(message + ': ' + actual + ' != ' + expected);
    }

    static function field(snapshot:Dynamic, name:String):Dynamic {
        if (snapshot == null || !Reflect.hasField(snapshot, name))
            fail('snapshot is missing field ' + name);
        return Reflect.field(snapshot, name);
    }

    static function checkRating(accuracy:Float, expected:String):Void {
        // One miss keeps zero-accuracy boundary checks distinct from the
        // special no-judgments ratingName of '?'.
        var result = PsychScoreScriptGlobals.snapshot(0, 1, 0, 0, 0, 0, accuracy);
        var actual:Dynamic = field(result, 'ratingName');
        check(actual == expected,
            'ratingName for accuracy ' + accuracy + ' was ' + actual + ', expected ' + expected);
    }

    static function main():Void {
        var empty = PsychScoreScriptGlobals.snapshot(731, 0, 0, 0, 0, 0, 0);
        check(field(empty, 'score') == 731, 'score snapshot');
        check(field(empty, 'misses') == 0, 'misses snapshot');
        check(field(empty, 'hits') == 0, 'empty hit count');
        check(field(empty, 'ratingFC') == '', 'empty full-combo label');
        check(field(empty, 'ratingName') == '?', 'empty rating name');
        near(field(empty, 'rating'), 0, 'empty bounded rating');
        check(!Reflect.hasField(empty, 'combo'), 'snapshot must not include combo');

        var mixed = PsychScoreScriptGlobals.snapshot(1234, 2, 10, 3, 4, 5, 85.25);
        check(field(mixed, 'score') == 1234, 'mixed score snapshot');
        check(field(mixed, 'misses') == 2, 'mixed misses snapshot');
        check(field(mixed, 'hits') == 22, 'judgement counts sum into hits');
        near(field(mixed, 'rating'), 0.8525, 'accuracy becomes bounded ratio');
        check(field(mixed, 'ratingName') == 'Great', 'Great rating tier');
        check(field(mixed, 'ratingFC') == 'SDCB', 'misses take precedence in ratingFC');

        var sick = PsychScoreScriptGlobals.snapshot(0, 0, 1, 0, 0, 0, 100);
        check(field(sick, 'ratingFC') == 'SFC', 'sick full combo');
        var good = PsychScoreScriptGlobals.snapshot(0, 0, 8, 1, 0, 0, 80);
        check(field(good, 'ratingFC') == 'GFC', 'good full combo takes precedence over sicks');
        var bad = PsychScoreScriptGlobals.snapshot(0, 0, 8, 1, 1, 0, 70);
        check(field(bad, 'ratingFC') == 'FC', 'bad judgement takes precedence over good');
        var shit = PsychScoreScriptGlobals.snapshot(0, 0, 0, 0, 0, 1, 0);
        check(field(shit, 'ratingFC') == 'FC', 'shit judgement full combo');
        var oneMiss = PsychScoreScriptGlobals.snapshot(0, 1, 1, 0, 0, 0, 90);
        check(field(oneMiss, 'ratingFC') == 'SDCB', 'one miss is SDCB');
        var tenMisses = PsychScoreScriptGlobals.snapshot(0, 10, 1, 1, 1, 1, 50);
        check(field(tenMisses, 'ratingFC') == 'Clear', 'ten misses is Clear');

        checkRating(-1, 'You Suck!');
        checkRating(19.999, 'You Suck!');
        checkRating(20, 'Shit');
        checkRating(39.999, 'Shit');
        checkRating(40, 'Bad');
        checkRating(49.999, 'Bad');
        checkRating(50, 'Bruh');
        checkRating(59.999, 'Bruh');
        checkRating(60, 'Meh');
        checkRating(68.999, 'Meh');
        checkRating(69, 'Nice');
        checkRating(69.999, 'Nice');
        checkRating(70, 'Good');
        checkRating(79.999, 'Good');
        checkRating(80, 'Great');
        checkRating(89.999, 'Great');
        checkRating(90, 'Sick!');
        checkRating(99.999, 'Sick!');
        checkRating(100, 'Perfect!!');

        var under = PsychScoreScriptGlobals.snapshot(0, 1, 0, 0, 0, 0, -50);
        near(field(under, 'rating'), 0, 'negative accuracy clamps at zero');
        var over = PsychScoreScriptGlobals.snapshot(0, 1, 0, 0, 0, 0, 125);
        near(field(over, 'rating'), 1, 'accuracy over one hundred clamps at one');
        check(field(over, 'ratingName') == 'Perfect!!', 'clamped perfect rating name');

        var overrides:Map<String,Dynamic> = ['rating'=>0.123, 'ratingName'=>'Custom', 'ratingFC'=>'Custom FC'];
        var custom = PsychScoreScriptGlobals.apply(PsychScoreScriptGlobals.snapshot(9, 1, 3, 2, 0, 0, 90), 17, overrides);
        check(field(custom, 'hits') == 22, 'script hits adjustment is independent of judgement counts');
        near(field(custom, 'rating'), 0.123, 'custom percentage');
        check(field(custom, 'ratingName') == 'Custom' && field(custom, 'ratingFC') == 'Custom FC', 'custom rating fields');
        var previous = PsychScoreScriptGlobals.snapshot(0, 0, 1, 0, 0, 0, 100);
        var stopped = PsychScoreScriptGlobals.apply(PsychScoreScriptGlobals.snapshot(7, 1, 1, 0, 0, 0, 50), 0, [], previous);
        check(field(stopped, 'score') == 7 && field(stopped, 'misses') == 1, 'stopped rating still publishes new counters');
        near(field(stopped, 'rating'), 1, 'stopped rating preserves previous percentage');
        check(field(stopped, 'ratingName') == 'Perfect!!' && field(stopped, 'ratingFC') == 'SFC', 'stopped rating keeps previous fields');

        // The function is a value snapshot: repeated calls cannot retain counts
        // or alter the caller's inputs.
        var score = 44;
        var misses = 0;
        var sicks = 1;
        var goods = 0;
        var bads = 0;
        var shits = 0;
        var accuracy = 100.0;
        var first = PsychScoreScriptGlobals.snapshot(score, misses, sicks, goods, bads, shits, accuracy);
        var second = PsychScoreScriptGlobals.snapshot(0, 1, 0, 0, 0, 0, 0);
        check(field(first, 'hits') == 1 && field(second, 'hits') == 0,
            'snapshots retain only their own judgement counts');
        check(score == 44 && misses == 0 && sicks == 1 && goods == 0 && bads == 0 && shits == 0
            && accuracy == 100, 'snapshot changed caller inputs');
    }
}
'''


REFRESH_FIXTURE = r'''
import haxe.ds.StringMap;

class Interp {
    public var variables:StringMap<Dynamic> = new StringMap();
    public function new() {}
}

class PsychScoreScriptGlobalsRefreshFixture {
    public var songScore:Int = 0;
    public var misses:Int = 0;
    public var sicks:Int = 0;
    public var goods:Int = 0;
    public var bads:Int = 0;
    public var shits:Int = 0;
    public var accuracy:Float = 0;
    public var totalPlayed:Int = 1;
    public var totalNotesHit:Float = 1;
    public var sourceAcceptedHits:Int = 0;
    public var epics:Int = 0;
    public var ratingStuff:Array<Dynamic> = [];
    var sourceOwner:Bool = false;
    var sourceScoreNightmare:Bool = false;
    var ratingsData:Array<SourceRating> = [];
    var psychScoreSnapshot:Dynamic = null;
    var psychHitsAdjustment:Int = 0;
    var psychRatingOverrides:Map<String,Dynamic> = [];
    var psychRatingRecalculating:Bool = false;
    var psychRatingPrevious:Dynamic = null;
    var psychScoreLastValues:Array<Float> = [];

    public function new() {}

__SOURCE_RATING_HITS_METHOD__

__SNAPSHOT_METHOD__

__REFRESH_METHOD__

    public function sourceScoreLedgerActive():Bool return sourceOwner;

    public function bumpSource(name:String):Void {
        switch (name) {
            case 'songScore': songScore++;
            case 'misses': misses++;
            case 'sicks': sicks++;
            case 'goods': goods++;
            case 'bads': bads++;
            case 'shits': shits++;
            case 'accuracy': accuracy += 1;
            default: throw 'unknown score source ' + name;
        }
    }

    static function fail(message:String):Void throw message;
    static function check(value:Bool, message:String):Void if (!value) fail(message);
    static function near(actual:Float, expected:Float, message:String):Void
        if (Math.isNaN(actual) || Math.abs(actual - expected) > 0.000001)
            fail(message + ': ' + actual + ' != ' + expected);
    static function field(interp:Interp, name:String):Dynamic {
        if (!interp.variables.exists(name)) fail('missing score global ' + name);
        return interp.variables.get(name);
    }
    static function allowPsych(interp:Interp):Void
        interp.variables.set('__psychScoreGlobals', true);

    static function main():Void {
        var state = new PsychScoreScriptGlobalsRefreshFixture();
        state.sourceOwner = true;
        var sourceSick = new SourceRating('sick');
        sourceSick.hits = 13;
        state.ratingsData = [sourceSick];
        check(state.sourceRatingHits(0, 1) == 13,
            'source Psych descriptor hits should be the FC counter');
        check(state.sourceRatingHits(1, 4) == 4,
            'missing source descriptors should preserve native counter fallback');
        state.sourceScoreNightmare = true;
        check(state.sourceRatingHits(0, 7) == 7,
            'Nightmare Vision keeps its separate state counter surface');
        state.sourceOwner = false;
        state.sourceScoreNightmare = false;
        state.songScore = 1234;
        state.misses = 2;
        state.sicks = 10;
        state.goods = 3;
        state.bads = 4;
        state.shits = 5;
        state.accuracy = 85.25;

        var first = new Interp();
        var second = new Interp();
        allowPsych(first);
        allowPsych(second);
        state.refreshPsychScoreGlobals(first);
        var firstSnapshot = first.variables.get('__psychScoreSnapshot');
        check(firstSnapshot != null, 'first Psych interpreter was not seeded');
        check(field(first, 'score') == 1234, 'score seed');
        check(field(first, 'misses') == 2, 'misses seed');
        check(field(first, 'hits') == 22, 'all judgement counters seed hits');
        near(field(first, 'rating'), 0.8525, 'rating seed');
        check(field(first, 'ratingName') == 'Great', 'ratingName seed');
        check(field(first, 'ratingFC') == 'SDCB', 'ratingFC seed');

        state.refreshPsychScoreGlobals(second);
        check(second.variables.get('__psychScoreSnapshot') == firstSnapshot,
            'interpreters did not share the cached score snapshot');
        check(field(second, 'score') == 1234 && field(second, 'hits') == 22,
            'second interpreter did not receive the shared snapshot');

        // Script-owned aliases survive callbacks while native score inputs and
        // the cached snapshot identity are unchanged.
        first.variables.set('score', 77);
        first.variables.set('misses', 88);
        first.variables.set('hits', 99);
        first.variables.set('rating', 0.25);
        first.variables.set('ratingName', 'script rating');
        first.variables.set('ratingFC', 'script FC');
        state.refreshPsychScoreGlobals(first);
        check(first.variables.get('__psychScoreSnapshot') == firstSnapshot,
            'unchanged score inputs rebuilt the snapshot');
        check(field(first, 'score') == 77 && field(first, 'misses') == 88
            && field(first, 'hits') == 99 && field(first, 'rating') == 0.25
            && field(first, 'ratingName') == 'script rating'
            && field(first, 'ratingFC') == 'script FC',
            'unchanged snapshot overwrote script-owned aliases');

        // Every native source field invalidates the cache. The selected
        // interpreter receives all fields from the new snapshot together.
        for (source in ['songScore', 'misses', 'sicks', 'goods', 'bads', 'shits', 'accuracy']) {
            var previous = first.variables.get('__psychScoreSnapshot');
            state.bumpSource(source);
            state.refreshPsychScoreGlobals(first);
            var updated = first.variables.get('__psychScoreSnapshot');
            check(updated != previous, source + ' change did not refresh the snapshot');
            check(field(first, 'score') == state.songScore, source + ' refreshed score');
            check(field(first, 'misses') == state.misses, source + ' refreshed misses');
            check(field(first, 'hits') == state.sicks + state.goods + state.bads + state.shits,
                source + ' refreshed summed hits');
            near(field(first, 'rating'), state.accuracy / 100, source + ' refreshed rating');
        }

        // Other interpreters keep their prior view until their next selected
        // callback, then receive the latest shared snapshot.
        check(second.variables.get('__psychScoreSnapshot') == firstSnapshot,
            'refreshing one interpreter eagerly changed another interpreter');
        state.refreshPsychScoreGlobals(second);
        check(second.variables.get('__psychScoreSnapshot') == first.variables.get('__psychScoreSnapshot'),
            'second interpreter did not refresh to the latest shared snapshot');
        check(field(second, 'score') == state.songScore && field(second, 'misses') == state.misses
            && field(second, 'hits') == state.sicks + state.goods + state.bads + state.shits,
            'second interpreter received stale score values');

        // Non-Psych HScript scopes opt out and keep their own variable values.
        var native = new Interp();
        native.variables.set('score', 456);
        native.variables.set('ratingName', 'native');
        state.refreshPsychScoreGlobals(native);
        check(native.variables.get('score') == 456 && native.variables.get('ratingName') == 'native'
            && !native.variables.exists('__psychScoreSnapshot'),
            'native interpreter received Psych score globals');
    }
}
'''


class PsychScoreScriptGlobalsTest(unittest.TestCase):
    def test_host_mapped_score_snapshot_and_rating_boundaries(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="psych-score-script-globals-", dir=TEST_TMP) as folder:
            Path(folder, "PsychScoreScriptGlobalsTest.hx").write_text(FIXTURE, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                 "-main", "PsychScoreScriptGlobalsTest", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_refresh_cache_seed_and_callback_ordering(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        snapshot = extract_method(play_state, "function sourceScoreSnapshot(")
        refresh = extract_method(play_state, "function refreshPsychScoreGlobals(")
        seed = extract_method(play_state, "function seedEngineCompat(")
        callback = extract_method(play_state, "function callHscript(")
        notify = extract_method(play_state, "function notifyPsychRatingChange(")

        score_gate = "interp.variables.set('__psychScoreGlobals', psychScriptOwner != null || Std.isOfType(interp, LuaCompatInterp));"
        self.assertIn(score_gate, seed)
        self.assertLess(seed.index(score_gate), seed.index("refreshPsychScoreGlobals(interp);"))
        self.assertLess(callback.index("var method = interp.variables.get(selectedName);"),
                        callback.index("refreshPsychScoreGlobals(interp);"))
        self.assertLess(callback.index("refreshPsychScoreGlobals(interp);"),
                        callback.index("returned = method();"))
        self.assertIn("interp.variables.get('__psychScoreGlobals') != true", refresh)
        self.assertIn("sourceScoreSnapshot();", refresh)
        self.assertIn("interp.variables.get('__psychScoreSnapshot') == psychScoreSnapshot", refresh)
        self.assertIn("interp.variables.get('__psychScoreGlobals') == true", notify)
        self.assertIn("callHscript('recalculateRating', [], key, true, returns);", notify)
        # This is intentionally the current host mapping, not a source score
        # ledger: native configurable accuracy remains one of its inputs.
        self.assertIn("PsychScoreScriptGlobals.snapshot(songScore, misses, sicks, goods, bads, shits, accuracy)",
                      snapshot)

        engine = (ROOT / "source/EngineCompat.hx").read_text(encoding="utf-8")
        callback_names = extract_method(engine, "public static function callbackNames(")
        self.assertIn("case 'recalculaterating':", callback_names)
        self.assertIn("appendName(result, 'onRecalculateRating');", callback_names)

        snapshot_method = snapshot.replace(
            "function sourceScoreSnapshot", "public function sourceScoreSnapshot", 1
        )
        rating_hits_method = extract_method(play_state, "function sourceRatingHits(")
        refresh_method = refresh.replace(
            "function refreshPsychScoreGlobals", "public function refreshPsychScoreGlobals", 1
        )
        fixture = REFRESH_FIXTURE.replace("__SOURCE_RATING_HITS_METHOD__", rating_hits_method)
        fixture = fixture.replace("__SNAPSHOT_METHOD__", snapshot_method)
        fixture = fixture.replace("__REFRESH_METHOD__", refresh_method)
        with tempfile.TemporaryDirectory(prefix="psych-score-refresh-", dir=TEST_TMP) as folder:
            Path(folder, "PsychScoreScriptGlobalsRefreshFixture.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                 "-main", "PsychScoreScriptGlobalsRefreshFixture", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
