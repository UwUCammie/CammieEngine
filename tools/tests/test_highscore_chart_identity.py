"""Gameplay score writes use the selected chart folder identity when needed."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
import re


ROOT = Path(__file__).resolve().parents[2]


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


class HighscoreChartIdentityTest(unittest.TestCase):
    def test_gameplay_saves_round_trip_at_the_real_freeplay_row_id(self):
        highscore_source = (ROOT / "source/Highscore.hx").read_text()
        song_source = (ROOT / "source/Song.hx").read_text()
        playstate_source = (ROOT / "source/PlayState.hx").read_text()
        freeplay_source = (ROOT / "source/FreeplayState.hx").read_text()
        charting_source = (ROOT / "source/ChartingState.hx").read_text()
        end_for_real = method(playstate_source, "function endForReal()")
        self.assertIn("Highscore.saveScore(Highscore.scoreSongIdForChart(SONG)", end_for_real)
        self.assertIn("Song.attachFreeplayScoreSongId(PlayState.SONG, songName);", freeplay_source)
        self.assertIn("Song.attachFreeplayScoreSongId(PlayState.SONG, songs[daSelection].songName);", freeplay_source)
        self.assertIn("Reflect.deleteField(data, 'compatScoreSongId');", charting_source)
        self.assertLess(
            song_source.index("Reflect.deleteField(parsedJson, 'compatScoreSongId');"),
            song_source.index("Reflect.setField(parsedJson, 'compatStorageFolder', folderLower);"),
        )

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            highscore_methods = [
                method(highscore_source, marker)
                for marker in (
                    "public static function scoreSongIdForChart(",
                    "public static function saveScore(",
                    "static function setScore(",
                    "public static function setAccuracy(",
                    "static function setFCLevel(",
                    "static function setJudge(",
                    "static function setOptionsUsed(",
                    "static function setModifiersUsed(",
                    "static function songFlush(",
                    "public static function formatSong(",
                    "public static function getScore(",
                    "public static function getAccuracy(",
                    "public static function load(",
                )
            ]
            highscore_methods = [
                re.sub(r"\bFCLevel\b", "Int", snippet)
                .replace("Jury", "Int")
                .replace("TOptions", "Dynamic")
                for snippet in highscore_methods
            ]
            highscore_fixture = "\n".join([
                "class Highscore {",
                " public static var songScores:Map<String,Int> = new Map();",
                " public static var songAccuracy:Map<String,Float> = new Map();",
                " public static var songCompletions:Map<String,Bool> = new Map();",
                " public static var songFCLevels:Map<String,Int> = new Map();",
                " public static var songJudge:Map<String,Int> = new Map();",
                " public static var songOptionsUsed:Map<String,Dynamic> = new Map();",
                " public static var songModifiersUsed:Map<String,Dynamic> = new Map();",
                " static var saveCategories = ['best-score', 'recent', 'best-accuracy', 'best-fullcombo', 'best'];",
                *highscore_methods,
                "}",
            ])
            (work / "Song.hx").write_text("\n".join([
                "class Song {",
                method(song_source, "public static function storageFolder("),
                method(song_source, "public static function attachFreeplayScoreSongId("),
                method(song_source, "static function validStorageKey("),
                "}",
            ]), newline="\n")
            (work / "Highscore.hx").write_text(highscore_fixture, newline="\n")
            (work / "DifficultyIcons.hx").write_text("""
class DifficultyIcons {
 public static function getEndingFP(diff:Int):String
  return diff == 2 ? '-hard' : diff == 1 ? '' : '-easy';
}
""", newline="\n")
            (work / "OptionsHandler.hx").write_text("""
class OptionsHandler {
 public static var options:Dynamic = {fixture:true};
}
""", newline="\n")
            (work / "ModifierState.hx").write_text("""
class ModifierState {
 public static var namedModifiers:Dynamic = {fixture:true};
}
""", newline="\n")
            (work / "Save.hx").write_text("""
class Save {
 public var data:Dynamic = {};
 public var flushCount:Int = 0;
 public function new() {}
 static function copyMap(source:Dynamic):Dynamic {
  if (source == null) return null;
  var from:Map<String,Dynamic> = cast source;
  var to:Map<String,Dynamic> = new Map();
  for (key in from.keys()) to.set(key, from.get(key));
  return to;
 }
 public function flush():Void {
  flushCount++;
  for (field in ['songScores','songCompletions','songAccuracy','songFCLevels',
    'songJudge','songOptionsUsed','songModifiersUsed'])
   Reflect.setField(data, field, copyMap(Reflect.field(data, field)));
 }
}
""", newline="\n")
            (work / "FlxG.hx").write_text("""
class FlxG {
 public static var save:Save = new Save();
}
""", newline="\n")
            (work / "Main.hx").write_text("""
class Main {
 static function check(ok:Bool, label:String):Void if (!ok) throw label;
 static function main():Void {
  // These are the actual exported Freeplay row ids. Both use Hard (difficulty index 2).
  var dsidesId = 'darnell--nightmare-vision-d1cec24a23';
  var dsidesChart:Dynamic = {song:'Darnell', compatStorageFolder:dsidesId};
  check(Song.attachFreeplayScoreSongId(dsidesChart, dsidesId),
   'D-Sides Freeplay row id should attach to its matching chart folder');
  check(Highscore.scoreSongIdForChart(dsidesChart) == dsidesId,
   'D-Sides chart must use its owner-qualified row id');
  Highscore.saveScore(Highscore.scoreSongIdForChart(dsidesChart), 93000, 2, 0.97, 5, 0);
  check(Highscore.getScore(dsidesId, 2) == 93000, 'D-Sides Freeplay row must read the gameplay score');

  // The ordinary base row remains title-keyed, so it cannot alias D-Sides Darnell.
  var baseChart:Dynamic = {song:'Darnell', compatStorageFolder:'darnell'};
  check(Song.attachFreeplayScoreSongId(baseChart, 'Darnell'),
   'base Freeplay row casing should attach to its matching chart folder');
  check(Highscore.scoreSongIdForChart(baseChart) == 'Darnell',
   'ordinary Darnell must keep its legacy title key');
  Highscore.saveScore(Highscore.scoreSongIdForChart(baseChart), 12000, 2, 0.85, 3, 0);
  check(Highscore.getScore('Darnell', 2) == 12000, 'base Darnell must retain a separate score');

  var tryHarderId = 'try-harder';
  var tryHarderChart:Dynamic = {song:'Try Harder', compatStorageFolder:tryHarderId};
  check(Song.attachFreeplayScoreSongId(tryHarderChart, tryHarderId),
   'Try Harder Freeplay row id should attach to its chart folder');
  check(Highscore.scoreSongIdForChart(tryHarderChart) == tryHarderId,
   'Try Harder must use its slugged Freeplay row id');
  Highscore.saveScore(Highscore.scoreSongIdForChart(tryHarderChart), 71000, 2, 0.91, 4, 0);
  check(Highscore.getScore(tryHarderId, 2) == 71000, 'Try Harder Freeplay row must read the gameplay score');

  // A case-only mismatch is not enough to infer Freeplay's key from SONG.song.
  var camelCaseId = 'camelcase';
  var camelCaseChart:Dynamic = {song:'CamelCase', compatStorageFolder:camelCaseId};
  check(Song.attachFreeplayScoreSongId(camelCaseChart, camelCaseId),
   'case-only Freeplay row id should attach after storage validation');
  check(Highscore.scoreSongIdForChart(camelCaseChart) == camelCaseId,
   'trusted exact row id should take precedence over authored title casing');
  Highscore.saveScore(Highscore.scoreSongIdForChart(camelCaseChart), 44000, 2, 0.89, 3, 0);
  check(Highscore.getScore(camelCaseId, 2) == 44000,
   'case-only imported Freeplay row must read the gameplay score');
  var mismatchedChart:Dynamic = {song:'CamelCase', compatStorageFolder:camelCaseId};
  check(!Song.attachFreeplayScoreSongId(mismatchedChart, 'different-row'),
   'unrelated Freeplay ids must not attach to a chart');

  var legacyChart:Dynamic = {song:'Legacy Song'};
  check(Highscore.scoreSongIdForChart(legacyChart) == 'Legacy Song',
   'charts without storage metadata must keep the title fallback');
  var unsafeChart:Dynamic = {song:'Try Harder', compatStorageFolder:'../try-harder'};
  check(Highscore.scoreSongIdForChart(unsafeChart) == 'Try Harder',
   'unsafe folder metadata must not become a score key');

  check(FlxG.save.flushCount == 4, 'each score save should flush the stub store');
  Highscore.songScores = new Map();
  Highscore.songAccuracy = new Map();
  Highscore.songFCLevels = new Map();
  Highscore.songJudge = new Map();
  Highscore.songOptionsUsed = new Map();
  Highscore.songModifiersUsed = new Map();
  Highscore.load();
  check(Highscore.getScore(dsidesId, 2) == 93000, 'D-Sides score must survive flush/load');
  check(Highscore.getScore('Darnell', 2) == 12000, 'base Darnell score must survive flush/load');
  check(Highscore.getScore(tryHarderId, 2) == 71000, 'Try Harder score must survive flush/load');
  check(Highscore.getScore(camelCaseId, 2) == 44000, 'case-only imported score must survive flush/load');
  check(Highscore.getAccuracy(dsidesId, 2) == 0.97, 'accuracy must survive flush/load at the row id');
 }
}
""", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "--run", "Main"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
