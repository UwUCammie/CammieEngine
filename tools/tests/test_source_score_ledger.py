"""Exercise stateless score deltas and snapshots against donor logic."""
from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
PSYCH_DONOR = (Path(r"C:\Users\uwucammie\Documents\coding\FNF\fnf_sources\FNF-PsychEngine")
               / "source/states/PlayState.hx")
NV_DONOR = (Path(r"C:\Users\uwucammie\Documents\coding\FNF\fnf_sources\NightmareVision")
            / "source/funkin/states/PlayState.hx")


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


def extract_block(source: str, marker: str) -> str:
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
    raise AssertionError(f"Unclosed block: {marker}")


def between(source: str, start_marker: str, end_marker: str) -> str:
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


def psych_donor_fragments():
    play_state = PSYCH_DONOR.read_text(encoding="utf-8")
    popup = extract_method(play_state, "private function popUpScore(")
    hit_prefix = between(popup, "totalNotesHit += daRating.ratingMod;", "if(daRating.noteSplash")
    hit_gate = extract_block(popup, "if(!cpuControlled) {")
    hit_gate = hit_gate.replace("RecalculateRating(false);", "recalculations++;")

    miss = extract_method(play_state, "function noteMissCommon(")
    miss_body = between(miss, "songScore -= 10;", "// play character anims")
    miss_body = miss_body.replace("RecalculateRating(true);", "recalculations++;")

    recalculate = extract_method(play_state, "public function RecalculateRating(")
    rating_logic = between(recalculate, "ratingName = '?';", "fullComboFunction();") + "fullComboFunction();"
    full_combo = extract_method(play_state, "public dynamic function fullComboFunction()")
    return hit_prefix, hit_gate, miss_body, rating_logic, full_combo


def nightmare_donor_fragments():
    play_state = NV_DONOR.read_text(encoding="utf-8")
    popup = extract_method(play_state, "function popUpScore(")
    hit_prefix = between(popup, "totalNotesHit += daRating.ratingMod;",
                         "if (!practiceMode && !cpuControlled && !(field?.autoPlayed ?? false))")
    hit_prefix = hit_prefix.replace("var field:PlayField", "var field:Dynamic")
    hit_gate = extract_block(popup, "if (!practiceMode && !cpuControlled && !(field?.autoPlayed ?? false))")
    hit_gate = hit_gate.replace("RecalculateRating(false);", "recalculations++;")

    actual_miss = between(play_state, "inline function actualMiss()", "strums.onNoteMiss.add")
    miss_body = between(actual_miss, "songMisses++;", "\n\t\t\t}")
    miss_body = miss_body.replace("RecalculateRating(true);", "recalculations++;")

    recalculate = extract_method(play_state, "public function RecalculateRating(")
    rating_logic = between(recalculate, "if (totalPlayed < 1)", "updateRatingFC();") + "updateRatingFC();"
    full_combo = extract_method(play_state, "public dynamic function updateRatingFC()")
    return hit_prefix, hit_gate, miss_body, rating_logic, full_combo


FIXTURE = r'''
class SourceScoreLedgerTest {
    static function fail(message:String):Void throw message;
    static function check(value:Bool, message:String):Void if (!value) fail(message);
    static function near(actual:Float, expected:Float, message:String):Void
        if (Math.isNaN(actual) || Math.abs(actual - expected) > 0.000001)
            fail(message + ': ' + actual + ' != ' + expected);
    static function field(value:Dynamic, name:String):Dynamic {
        if (value == null || !Reflect.hasField(value, name)) fail('missing field ' + name);
        return Reflect.field(value, name);
    }

    static function psychRating(weight:Float, score:Int, name:String):Dynamic
        return {ratingMod:weight, score:score, name:name, hits:0};

    static function nvRating(weight:Float, score:Int, name:String):Dynamic {
        var value:Dynamic = {ratingMod:weight, score:score, name:name, counter:name + 's', hits:0};
        Reflect.setField(value, 'increase', function():Void {
            Reflect.setField(value, 'hits', Std.int(Reflect.field(value, 'hits')) + 1);
        });
        return value;
    }

    static function psychTier(name:String, threshold:Float):Array<Dynamic>
        return [name, threshold];

    static function donorPsychHit(rating:Dynamic, disabled:Bool, cpu:Bool):Dynamic {
        var daRating = rating;
        var note:Dynamic = {ratingDisabled:disabled};
        var cpuControlled = cpu;
        var totalNotesHit:Float = 0;
        var score:Int = 0;
        var songScore:Int = 0;
        var songHits:Int = 0;
        var totalPlayed:Int = 0;
        var recalculations:Int = 0;
        __PSYCH_HIT_PREFIX__
        __PSYCH_HIT_GATE__
        return {weight:totalNotesHit, ratedCounter:daRating.hits, score:songScore,
            hits:songHits, played:totalPlayed, recalculate:recalculations > 0};
    }

    static function donorNvHit(rating:Dynamic, disabled:Bool, cpu:Bool, practice:Bool,
        fieldAuto:Bool, defaultScoreAddition:Bool):Dynamic {
        var daRating = rating;
        var note:Dynamic = {ratingDisabled:disabled, playField:{autoPlayed:fieldAuto}};
        var cpuControlled = cpu;
        var practiceMode = practice;
        var judgeScore:Int = Std.int(daRating.score);
        var totalNotesHit:Float = 0;
        var songScore:Int = 0;
        var songHits:Int = 0;
        var totalPlayed:Int = 0;
        var recalculations:Int = 0;
        __NV_HIT_PREFIX__
        __NV_HIT_GATE__
        return {weight:totalNotesHit, ratedCounter:daRating.hits, score:songScore,
            hits:songHits, played:totalPlayed, recalculate:recalculations > 0};
    }

    static function checkHit(actual:Dynamic, donor:Dynamic, label:String):Void {
        near(field(actual, 'weight'), field(donor, 'weight'), label + ' weight');
        check(field(actual, 'ratedCounter') == field(donor, 'ratedCounter'), label + ' rating counter');
        check(field(actual, 'score') == field(donor, 'score'), label + ' score');
        check(field(actual, 'hits') == field(donor, 'hits'), label + ' hits');
        check(field(actual, 'played') == field(donor, 'played'), label + ' played');
        check(field(actual, 'recalculate') == field(donor, 'recalculate'), label + ' recalculate');
    }

    static function checkHitDeltas():Void {
        var weights = [1.0, 0.67, 0.34, 0.0, 1.0];
        var scores = [350, 200, 100, 50, 500];
        var names = ['sick', 'good', 'bad', 'shit', 'epic'];
        for (mask in 0...32) {
            var index = mask % weights.length;
            var disabled = (mask & 1) != 0;
            var cpu = (mask & 2) != 0;
            var practice = (mask & 4) != 0;
            var fieldAuto = (mask & 8) != 0;
            var defaultAddition = (mask & 16) != 0;
            var rating = psychRating(weights[index], scores[index], names[index]);
            var psych = SourceScoreLedger.hit(rating, disabled, cpu, false,
                practice, fieldAuto, defaultAddition);
            checkHit(psych, donorPsychHit(rating, disabled, cpu), 'Psych mask ' + mask);
            check(field(psych, 'counterName') == names[index] + 's', 'Psych counter name');

            rating = nvRating(weights[index], scores[index], names[index]);
            var nightmare = SourceScoreLedger.hit(rating, disabled, cpu, true,
                practice, fieldAuto, defaultAddition);
            checkHit(nightmare, donorNvHit(rating, disabled, cpu, practice,
                fieldAuto, defaultAddition), 'Nightmare Vision mask ' + mask);
            check(field(nightmare, 'counterName') == names[index] + 's', 'Nightmare Vision counter name');
        }

        var psyBot = SourceScoreLedger.hit(psychRating(0.67, 200, 'good'), false, true,
            false, true, true, false);
        check(field(psyBot, 'weight') == 0.67 && field(psyBot, 'ratedCounter') == 1
            && field(psyBot, 'score') == 0 && field(psyBot, 'played') == 0,
            'Psych botplay retains unconditional numerator/rating bucket only');
        var nvPractice = SourceScoreLedger.hit(nvRating(1, 500, 'epic'), false, false,
            true, true, false, true);
        check(field(nvPractice, 'weight') == 1 && field(nvPractice, 'ratedCounter') == 1
            && field(nvPractice, 'score') == 0 && field(nvPractice, 'played') == 0,
            'Nightmare Vision practice retains numerator/rating bucket only');
        var nvNoDefault = SourceScoreLedger.hit(nvRating(0.4, 100, 'bad'), false,
            false, true, false, false, false);
        check(field(nvNoDefault, 'score') == 0 && field(nvNoDefault, 'hits') == 1
            && field(nvNoDefault, 'played') == 1 && field(nvNoDefault, 'recalculate') == true,
            'Nightmare Vision defaultScoreAddition gates score only');
    }

    static function donorPsychMiss(practice:Bool, ending:Bool):Dynamic {
        var songScore:Int = 17;
        var songMisses:Int = 2;
        var totalPlayed:Int = 5;
        var recalculations:Int = 0;
        var practiceMode = practice;
        var endingSong = ending;
        var beforeScore = songScore;
        var beforeMisses = songMisses;
        var beforePlayed = totalPlayed;
        __PSYCH_MISS__
        return {score:songScore - beforeScore, missDelta:songMisses - beforeMisses,
            played:totalPlayed - beforePlayed, recalculate:recalculations > 0};
    }

    static function donorNvMiss(practice:Bool, ending:Bool):Dynamic {
        var songScore:Int = 17;
        var songMisses:Int = 2;
        var totalPlayed:Int = 5;
        var recalculations:Int = 0;
        var practiceMode = practice;
        var beforeScore = songScore;
        var beforeMisses = songMisses;
        var beforePlayed = totalPlayed;
        __NV_MISS__
        return {score:songScore - beforeScore, missDelta:songMisses - beforeMisses,
            played:totalPlayed - beforePlayed, recalculate:recalculations > 0};
    }

    static function checkMiss(actual:Dynamic, donor:Dynamic, label:String):Void {
        check(field(actual, 'score') == field(donor, 'score'), label + ' score');
        check(field(actual, 'missDelta') == field(donor, 'missDelta'), label + ' misses');
        check(field(actual, 'played') == field(donor, 'played'), label + ' played');
        check(field(actual, 'recalculate') == field(donor, 'recalculate'), label + ' recalculate');
    }

    static function checkMissDeltas():Void {
        for (practice in [false, true]) for (ending in [false, true]) {
            checkMiss(SourceScoreLedger.miss(false, practice, ending),
                donorPsychMiss(practice, ending), 'Psych miss practice=' + practice + ' ending=' + ending);
            checkMiss(SourceScoreLedger.miss(true, practice, ending),
                donorNvMiss(practice, ending), 'Nightmare Vision miss practice=' + practice + ' ending=' + ending);
        }
    }

    static function checkSnapshot(actual:Dynamic, donor:Dynamic, label:String):Void {
        for (name in ['score', 'misses', 'hits', 'totalPlayed', 'totalNotesHit',
                'sicks', 'goods', 'bads', 'shits', 'epics', 'ratingName', 'ratingFC'])
            check(field(actual, name) == field(donor, name), label + ' ' + name);
        near(field(actual, 'rating'), field(donor, 'ratingPercent'), label + ' rating');
        near(field(actual, 'ratingPercent'), field(donor, 'ratingPercent'), label + ' ratingPercent');
    }

    static function main():Void {
        checkHitDeltas();
        checkMissDeltas();
        __SNAPSHOT_CASES__
    }
}

class PsychDonorSnapshot {
    public var totalPlayed:Int;
    public var totalNotesHit:Float;
    public var ratingPercent:Float = 0;
    public var ratingName:String = '?';
    public var ratingFC:String = '';
    public var ratingStuff:Array<Dynamic>;
    public var songMisses:Int;
    public var ratingsData:Array<Dynamic>;
    public function new(totalPlayed:Int, totalNotesHit:Float, songMisses:Int,
        sicks:Int, goods:Int, bads:Int, shits:Int, ratingStuff:Array<Dynamic>) {
        this.totalPlayed = totalPlayed;
        this.totalNotesHit = totalNotesHit;
        this.songMisses = songMisses;
        this.ratingsData = [{hits:sicks}, {hits:goods}, {hits:bads}, {hits:shits}];
        this.ratingStuff = ratingStuff;
    }
    public function recalculate():Dynamic {
        __PSYCH_RATING_LOGIC__
        return {ratingPercent:ratingPercent, ratingName:ratingName, ratingFC:ratingFC};
    }
    __PSYCH_FC_METHOD__
}

class NvDonorSnapshot {
    public var totalPlayed:Int;
    public var totalNotesHit:Float;
    public var ratingPercent:Float = 0;
    public var ratingName:String = '?';
    public var ratingFC:String = '';
    public var ratingStuff:Array<Dynamic>;
    public var songMisses:Int;
    public var sicks:Int;
    public var goods:Int;
    public var bads:Int;
    public var shits:Int;
    public var epics:Int;
    public function new(totalPlayed:Int, totalNotesHit:Float, songMisses:Int,
        sicks:Int, goods:Int, bads:Int, shits:Int, epics:Int, ratingStuff:Array<Dynamic>) {
        this.totalPlayed = totalPlayed;
        this.totalNotesHit = totalNotesHit;
        this.songMisses = songMisses;
        this.sicks = sicks;
        this.goods = goods;
        this.bads = bads;
        this.shits = shits;
        this.epics = epics;
        this.ratingStuff = ratingStuff;
    }
    public function recalculate():Dynamic {
        __NV_RATING_LOGIC__
        return {ratingPercent:ratingPercent, ratingName:ratingName, ratingFC:ratingFC};
    }
    __NV_FC_METHOD__
}
'''


class SourceScoreLedgerTest(unittest.TestCase):
    def test_deltas_and_snapshot_match_pinned_donors(self):
        psych_hit_prefix, psych_hit_gate, psych_miss, psych_rating_logic, psych_fc = psych_donor_fragments()
        nv_hit_prefix, nv_hit_gate, nv_miss, nv_rating_logic, nv_fc = nightmare_donor_fragments()
        psych_hit_prefix = psych_hit_prefix.replace("\t\t", "        ")
        psych_hit_gate = psych_hit_gate.replace("\t\t", "        ")
        nv_hit_prefix = nv_hit_prefix.replace("\t\t", "        ")
        nv_hit_gate = nv_hit_gate.replace("\t\t", "        ")
        psych_miss = psych_miss.replace("\t\t", "        ")
        nv_miss = nv_miss.replace("\t\t", "        ")
        psych_rating_logic = psych_rating_logic.replace("\t\t", "        ")
        nv_rating_logic = nv_rating_logic.replace("\t\t", "        ")
        psych_fc = psych_fc.replace("public function fullComboFunction()", "public function fullComboFunction()", 1)
        nv_fc = nv_fc.replace("public dynamic function updateRatingFC()", "public function updateRatingFC()", 1)

        cases = r'''
        var psychTiers:Array<Dynamic> = [
            psychTier('You Suck!', 0.2), psychTier('Shit', 0.4), psychTier('Bad', 0.5),
            psychTier('Bruh', 0.6), psychTier('Meh', 0.69), psychTier('Nice', 0.7),
            psychTier('Good', 0.8), psychTier('Great', 0.9), psychTier('Sick!', 1.0),
            psychTier('Perfect!!', 1.0)
        ];
        var nvTiers:Array<Dynamic> = [
            cast {name:'You Suck!', percent:0.2}, cast {name:'Shit', percent:0.4},
            cast {name:'Bad', percent:0.5}, cast {name:'Bruh', percent:0.6},
            cast {name:'Meh', percent:0.69}, cast {name:'Nice', percent:0.7},
            cast {name:'Good', percent:0.8}, cast {name:'Great', percent:0.9},
            cast {name:'Sick!', percent:1.0}, cast {name:'Perfect!!', percent:1.0}
        ];
        var values:Array<Float> = [0.0, 0.19999, 0.2, 0.4, 0.5, 0.6, 0.69, 0.7, 0.8, 0.9, 1.0, 1.25];
        for (value in values) {
            var played = value == 0 ? 0 : 1;
            var numerator = value * played;
            for (misses in [0, 1, 9, 10]) for (sicks in [0, 1]) for (goods in [0, 1])
                for (bads in [0, 1]) for (shits in [0, 1]) {
                    var psychDonor = new PsychDonorSnapshot(played, numerator, misses,
                        sicks, goods, bads, shits, psychTiers).recalculate();
                    var psych = SourceScoreLedger.snapshot(77, misses, 19, played, numerator,
                        sicks, goods, bads, shits, 3, psychTiers);
                    var expectedPsych:Dynamic = {score:77, misses:misses, hits:19,
                        totalPlayed:played, totalNotesHit:numerator, sicks:sicks, goods:goods,
                        bads:bads, shits:shits, epics:3, ratingPercent:psychDonor.ratingPercent,
                        ratingName:psychDonor.ratingName, ratingFC:psychDonor.ratingFC};
                    checkSnapshot(psych, expectedPsych, 'Psych ratio=' + value + ' misses=' + misses);

                    var nvDonor = new NvDonorSnapshot(played, numerator, misses,
                        sicks, goods, bads, shits, 1, nvTiers).recalculate();
                    var nv = SourceScoreLedger.snapshot(77, misses, 19, played, numerator,
                        sicks, goods, bads, shits, 1, nvTiers);
                    var expectedNv:Dynamic = {score:77, misses:misses, hits:19,
                        totalPlayed:played, totalNotesHit:numerator, sicks:sicks, goods:goods,
                        bads:bads, shits:shits, epics:1, ratingPercent:nvDonor.ratingPercent,
                        ratingName:nvDonor.ratingName, ratingFC:nvDonor.ratingFC};
                    checkSnapshot(nv, expectedNv, 'Nightmare Vision ratio=' + value + ' misses=' + misses);
                }
        }
        var defaults = SourceScoreLedger.snapshot(0, 0, 0, 0, 0, 0, 0, 0, 0);
        check(field(defaults, 'ratingName') == '?', 'default empty rating name');
        check(field(defaults, 'ratingFC') == '', 'default empty FC');
        '''

        fixture = FIXTURE
        for marker, value in {
            "__PSYCH_HIT_PREFIX__": psych_hit_prefix,
            "__PSYCH_HIT_GATE__": psych_hit_gate,
            "__NV_HIT_PREFIX__": nv_hit_prefix,
            "__NV_HIT_GATE__": nv_hit_gate,
            "__PSYCH_MISS__": psych_miss,
            "__NV_MISS__": nv_miss,
            "__PSYCH_RATING_LOGIC__": psych_rating_logic,
            "__NV_RATING_LOGIC__": nv_rating_logic,
            "__PSYCH_FC_METHOD__": psych_fc,
            "__NV_FC_METHOD__": nv_fc,
            "__SNAPSHOT_CASES__": cases,
        }.items():
            fixture = fixture.replace(marker, value)

        self.assertNotIn("__", fixture, "an extracted donor fixture placeholder was missed")
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="source-score-ledger-", dir=TEST_TMP) as folder:
            Path(folder, "SourceScoreLedgerTest.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                 "-main", "SourceScoreLedgerTest", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
