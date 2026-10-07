"""Owner-local Nightmare Vision score persistence and API contracts."""
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionHighscoreTest(unittest.TestCase):
    def test_api_uses_owner_save_and_typed_path_callbacks(self):
        source = (ROOT / "source/NightmareVisionHighscore.hx").read_text(encoding="utf-8")
        for contract in (
            "public var weekScores:Map<String, Int>",
            "public var songScores:Map<String, Int>",
            "public var songRating:Map<String, Float>",
            "public function resetSong(",
            "public function resetWeek(",
            "public function saveScore(",
            "public function saveWeekScore(",
            "public function getScore(",
            "public function getRating(",
            "public function getWeekScore(",
            "public function formatSong(",
            "public function load():Void",
            "function setScore(",
            "function setWeekScore(",
            "function setRating(",
        ):
            self.assertIn(contract, source)
        self.assertIn("sanitizePath:String->String", source)
        self.assertIn("difficultyFilePath:Int->String", source)
        self.assertNotIn("FlxG", source)
        self.assertNotIn("Highscore.", source)

    def test_strict_scores_fractional_ratings_live_maps_and_json_restore(self):
        main = r'''
import haxe.ds.StringMap;

class OwnerSave {
 public var fields:Map<String,Dynamic> = new Map();
 public var writes:Array<String> = [];
 public var reads:Array<String> = [];
 public var flushes:Int = 0;
 public function new() {}
 public function getField(name:String):Dynamic {
  reads.push(name);
  var value = fields.get(name);
  return value == null ? null : haxe.Json.parse(haxe.Json.stringify(value));
 }
 public function setField(name:String, value:Dynamic):Dynamic {
  writes.push(name);
  fields.set(name, haxe.Json.parse(haxe.Json.stringify(value)));
  return value;
 }
 public function flush():Void flushes++;
}

class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var save = new OwnerSave();
  var callbackCalls:Array<String> = [];
  var highscore = new NightmareVisionHighscore(save,
   function(song:String):String {callbackCalls.push('sanitize:' + song); return StringTools.replace(song, '/', '_');},
   function(diff:Int):String {callbackCalls.push('difficulty:' + diff); return ['Easy', 'Normal', 'Hard'][diff];});

  check(highscore.formatSong('Pack/Song', 2) == 'Pack_Song-Hard',
   'formatSong must call Paths.sanitize then Difficulty.getDifficultyFilePath equivalents');
  check(callbackCalls.join(',') == 'sanitize:Pack/Song,difficulty:2',
   'formatSong must pass the raw song and requested difficulty to the typed callbacks');

  check(highscore.getScore('NewSong', 0) == 0 && save.fields.exists('songScores') && save.flushes == 1,
   'a missing score reads as zero and writes the owner score map immediately');
  check(highscore.getRating('NewSong', 0) == 0 && save.fields.exists('songRating') && save.flushes == 2,
   'a missing rating reads as zero and writes the owner rating map immediately');
  check(highscore.getWeekScore('NewWeek', 1) == 0 && save.fields.exists('weekScores') && save.flushes == 3,
   'a missing week score reads as zero and writes the owner week map immediately');
  check(save.writes.join(',') == 'songScores,songRating,weekScores',
   'score maps persist under the three source field names');
  check(Std.isOfType(highscore.songScores, StringMap)
   && Std.isOfType(highscore.weekScores, StringMap) && Std.isOfType(highscore.songRating, StringMap),
   'the public source maps must be live typed Haxe Maps');

  highscore.saveScore('Track', 100, 0, 0.735);
  check(highscore.getScore('Track', 0) == 100 && highscore.getRating('Track', 0) == 0.735,
   'a first score stores its fractional rating');
  var flushes = save.flushes;
  highscore.saveScore('Track', 100, 0, 0.99);
  highscore.saveScore('Track', 99, 0, 0.88);
  check(save.flushes == flushes && highscore.getRating('Track', 0) == 0.735,
   'equal and lower scores do not replace scores, ratings, or flush owner data');
  highscore.saveScore('Track', 150, 0);
  check(highscore.getScore('Track', 0) == 150 && highscore.getRating('Track', 0) == 0.735,
   'a strict improvement without a nonnegative rating preserves the prior rating');
  highscore.saveScore('Track', 151, 0, 0.875);
  check(highscore.getScore('Track', 0) == 151 && highscore.getRating('Track', 0) == 0.875,
   'a later strict improvement updates its fractional rating');

  highscore.saveWeekScore('StoryWeek', 80, 2);
  var weekFlushes = save.flushes;
  highscore.saveWeekScore('StoryWeek', 80, 2);
  highscore.saveWeekScore('StoryWeek', 79, 2);
  check(save.flushes == weekFlushes && highscore.getWeekScore('StoryWeek', 2) == 80,
   'week scores update only on a strict improvement');
  highscore.saveWeekScore('StoryWeek', 90, 2);
  check(highscore.getWeekScore('StoryWeek', 2) == 90,
   'a strict week score improvement replaces the owner value');

  var directMap = highscore.songScores;
  directMap.set('Direct-Hard', 7);
  check(highscore.getScore('Direct', 2) == 7 && highscore.songScores == directMap,
   'scripts see and can mutate the live source score map');

  var privateSetter:Dynamic = Reflect.field(highscore, 'setScore');
  check(privateSetter != null, 'source private setScore must remain available through reflection');
  var reflectedArgs:Array<Dynamic> = ['Reflected-Normal', 33];
  Reflect.callMethod(highscore, privateSetter, reflectedArgs);
  check(highscore.songScores.get('Reflected-Normal') == 33,
   'the reflected source private setter updates its live map');

  var songResetFlushes = save.flushes;
  highscore.resetSong('Track', 0);
  check(highscore.getScore('Track', 0) == 0 && highscore.getRating('Track', 0) == 0,
   'resetSong writes zero score then zero rating');
  check(save.flushes == songResetFlushes + 2,
   'resetSong persists score and rating through separate source setters');
  var weekResetFlushes = save.flushes;
  highscore.resetWeek('StoryWeek', 2);
  check(highscore.getWeekScore('StoryWeek', 2) == 0,
   'resetWeek writes a zero week score');
  check(save.flushes == weekResetFlushes + 1,
   'resetWeek persists through its single source setter');

  highscore.saveScore('Defaulted');
  check(highscore.songScores.get('Defaulted-Easy') == 0
   && !highscore.songRating.exists('Defaulted-Easy'),
   'saveScore defaults to score zero, difficulty zero, and no saved rating');
  highscore.saveWeekScore('DefaultWeek');
  check(highscore.weekScores.exists('DefaultWeek-Easy')
   && highscore.weekScores.get('DefaultWeek-Easy') == 0,
   'saveWeekScore defaults to score zero and difficulty zero');
  highscore.resetSong('Defaulted');
  check(highscore.getRating('Defaulted', 0) == 0,
   'resetSong defaults to difficulty zero and resets its rating too');
  highscore.resetWeek('DefaultWeek');
  check(highscore.getWeekScore('DefaultWeek', 0) == 0,
   'resetWeek defaults to difficulty zero');

  // JSON records reload as fresh, stable Map instances. A null field leaves
  // the current in-memory source map reference untouched.
  var beforeReload = highscore.songScores;
  var trackEntry:Array<Dynamic> = ['Track-Normal', 420];
  var importedEntry:Array<Dynamic> = ['Imported/Song-Hard', 99000];
  var ratingEntry:Array<Dynamic> = ['Track-Normal', 0.8125];
  save.fields.set('songScores', {__nightmareVisionHighscoreMap__:true,
   entries:[trackEntry, importedEntry]});
  save.fields.set('songRating', {__nightmareVisionHighscoreMap__:true,
   entries:[ratingEntry]});
  save.fields.remove('weekScores');
  var weekMapBefore = highscore.weekScores;
  var readsBeforeLoad = save.reads.length;
  var flushesBeforeLoad = save.flushes;
  highscore.load();
  check(highscore.songScores != beforeReload && Std.isOfType(highscore.songScores, StringMap)
   && highscore.songScores.get('Track-Normal') == 420
   && highscore.songScores.get('Imported/Song-Hard') == 99000,
   'load clones decoded JSON entries into a stable typed live Map');
  check(highscore.songRating.get('Track-Normal') == 0.8125
   && Std.isOfType(highscore.songRating, StringMap),
   'load restores fractional JSON ratings as a typed Float map');
  check(highscore.weekScores == weekMapBefore,
   'load leaves the existing map pointer in place when the save field is null');
  check(save.reads.slice(readsBeforeLoad).join(',') == 'weekScores,songScores,songRating'
   && save.flushes == flushesBeforeLoad,
   'load reads saved fields in donor order without writing or flushing');

  highscore.release();
  var released = false;
  try highscore.getScore('Track', 0) catch (_:Dynamic) released = true;
  check(released, 'released owner highscore views reject future reads');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(main, encoding="utf-8")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--main", "Main", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
