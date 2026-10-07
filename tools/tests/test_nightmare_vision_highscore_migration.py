"""Exercise bounded NMV score migration with the real owner score services."""
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionHighscoreMigrationTest(unittest.TestCase):
    def test_paired_lazy_owner_scoped_migration_and_ambiguity_contracts(self):
        main = r'''
import CompatScriptManifest.CompatScriptManifestData;
import NightmareVisionHighscoreMigration.NightmareVisionHighscoreMigrationEntry;
class OwnerSave {
 public var fields:Map<String,Dynamic> = new Map();
 public var writes:Int = 0;
 public var failWrites:Bool = false;
 public function new() {}
 public function getField(name:String):Dynamic return fields.get(name);
 public function setField(name:String, value:Dynamic):Dynamic {
  writes++;
  if (failWrites) throw 'owner save write failed';
  fields.set(name, value);
  return value;
 }
 public function flush():Void {}
}

class Main {
 static var ownerA = 'assets/imported_mods/nmv-owner-a';
 static var ownerB = 'assets/imported_mods/nmv-owner-b';
 static var loads:Int = 0;
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function receipt(owner:String, folder:String):Dynamic return {
  version:1, sourceEngine:'Nightmare Vision', sourceOwner:owner,
  sourceFolder:'songs/' + folder, destinationFolder:folder,
  sourceSelectableDifficulties:['Normal', 'Erect', 'Hard']
 };
 static function manifest(owner:String):CompatScriptManifestData return {
  selectedRoot:owner, roots:[{engine:'Nightmare Vision', path:owner}]
 };
 static function chart(registered:String, title:String, stem:String):Dynamic return {
  song:title, compatStorageFolder:registered, compatChartFileName:stem,
  compatScoreSongId:registered
 };
 static function entry(registered:String, index:Int, owner:String, title:String,
  stem:String, ?path:String):NightmareVisionHighscoreMigrationEntry {
  var selectedPath = path == null ? 'assets/data/' + registered + '/' + stem + '.json' : path;
  return {
   registeredSong:registered, nativeDifficultyIndex:index,
   destinationChartPath:selectedPath, provenance:receipt(owner, registered),
   ownerManifest:manifest(owner),
   loadChart:function():Dynamic { loads++; return chart(registered, title, stem); }
  };
 }
 static function resetNative():Void {
  Highscore.songScores = new Map();
  Highscore.songAccuracy = new Map();
 }
 static function makeScores(owner:String, save:OwnerSave,
  adapter:NightmareVisionDifficultyAdapter):NightmareVisionHighscore {
  return new NightmareVisionHighscore(save,
   function(song:String):String return StringTools.replace(song.toLowerCase(), ' ', '-'),
   function(index:Int):String return adapter.getDifficultyFilePath(index));
 }
 static function addChartFile(path:String):Void {
  var directory = haxe.io.Path.directory(path);
  if (!sys.FileSystem.exists(directory)) sys.FileSystem.createDirectory(directory);
  sys.io.File.saveContent(path, '{}');
 }
 static function main():Void {
  addChartFile('assets/data/owner-song/owner-song-hard.json');
  addChartFile('assets/data/owner-normal/owner-normal.json');
  addChartFile('assets/data/owner-alias-a/owner-alias-a-hard.json');
  addChartFile('assets/data/owner-alias-b/owner-alias-b-hard.json');
  addChartFile('assets/data/owner-fail/owner-fail-hard.json');

  var adapter = new NightmareVisionDifficultyAdapter(ownerA, ['Easy', 'Normal', 'Hard'], 0);
  var scores = makeScores(ownerA, new OwnerSave(), adapter);

  // No score pair means no chart parse or native zero insertion.
  resetNative();
  var nativeScores = Highscore.songScores;
  var nativeAccuracy = Highscore.songAccuracy;
  loads = 0;
  var empty = NightmareVisionHighscoreMigration.migrate(
   [entry('owner-song', 2, ownerA, 'Dad Battle', 'owner-song-hard')],
   ownerA, [ownerA], scores, adapter);
  check(empty.skipped == 1 && loads == 0, 'empty score maps must skip before parsing');
  check(Highscore.songScores == nativeScores && Highscore.songAccuracy == nativeAccuracy
   && !nativeScores.exists('owner-song-hard-best-score'),
   'migration must preserve native map references and must not insert zero entries');

  // best-score accuracy stays paired; best-accuracy can describe another play.
  var scoreKey = Highscore.formatSong('owner-song', 2, 'best-score');
  var aggregateKey = Highscore.formatSong('owner-song', 2, 'best-accuracy');
  Highscore.songScores.set(scoreKey, 250);
  Highscore.songAccuracy.set(scoreKey, 0.82);
  Highscore.songScores.set(aggregateKey, 900);
  Highscore.songAccuracy.set(aggregateKey, 0.99);
  loads = 0;
  var imported = NightmareVisionHighscoreMigration.migrate(
   [entry('owner-song', 2, ownerA, 'Dad Battle', 'owner-song-hard')],
   ownerA, [ownerA], scores, adapter);
  check(imported.migrated == 1 && loads == 1, 'a paired candidate should load and migrate once: migrated='
   + imported.migrated + ', skipped=' + imported.skipped + ', loads=' + loads
   + ', diagnostics=' + imported.diagnostics.join('|'));
  check(scores.songScores.get('dad-battle-hard') == 250
   && scores.songRating.get('dad-battle-hard') == 0.82,
   'migration must use actual chart title and accuracy from the same native best-score key');
  check(adapter.difficulties.join(',') == 'Easy,Normal,Hard' && adapter.currentDifficultyIndex == 0,
   'the borrowed source difficulty list and index must be restored');
  check(Highscore.songScores == nativeScores && Highscore.songAccuracy == nativeAccuracy
   && nativeScores.get(scoreKey) == 250 && nativeAccuracy.get(scoreKey) == 0.82,
   'native maps and values must remain unchanged');

  var defaultKey = Highscore.formatSong('owner-normal', 1, 'best-score');
  Highscore.songScores.set(defaultKey, 75);
  Highscore.songAccuracy.set(defaultKey, 0.33);
  var defaultSlot = NightmareVisionHighscoreMigration.migrate(
   [entry('owner-normal', 1, ownerA, 'Normal Track', 'owner-normal')],
   ownerA, [ownerA], scores, adapter);
  check(defaultSlot.migrated == 1 && scores.songScores.get('normal-track-normal') == 75,
   'an unsuffixed native chart must map through its actual configured default difficulty name');

  // Strict source semantics preserve equal scores, then update a strict improvement.
  Highscore.songAccuracy.set(scoreKey, 0.91);
  var equal = NightmareVisionHighscoreMigration.migrate(
   [entry('owner-song', 2, ownerA, 'Dad Battle', 'owner-song-hard')],
   ownerA, [ownerA], scores, adapter);
  check(equal.unchanged == 1 && scores.songRating.get('dad-battle-hard') == 0.82,
   'equal private scores must preserve the existing rating');
  Highscore.songScores.set(scoreKey, 300);
  var improved = NightmareVisionHighscoreMigration.migrate(
   [entry('owner-song', 2, ownerA, 'Dad Battle', 'owner-song-hard')],
   ownerA, [ownerA], scores, adapter);
  check(improved.migrated == 1 && scores.songScores.get('dad-battle-hard') == 300
   && scores.songRating.get('dad-battle-hard') == 0.91,
   'strict improvement must update private score and paired rating');

  // Missing halves and foreign chart ownership are rejected before parse.
  resetNative();
  var partialKey = Highscore.formatSong('owner-song', 2, 'best-score');
  Highscore.songScores.set(partialKey, 10);
  loads = 0;
  var partial = NightmareVisionHighscoreMigration.migrate(
   [entry('owner-song', 2, ownerA, 'Dad Battle', 'owner-song-hard')],
   ownerA, [ownerA], scores, adapter);
  check(partial.skipped == 1 && partial.diagnostics.join(',').indexOf('native-pair-missing') >= 0
   && loads == 0, 'an unpaired score must be diagnosed without parsing');
  Highscore.songAccuracy.set(partialKey, 0.5);
  var wrongPath = entry('owner-song', 2, ownerA, 'Dad Battle', 'owner-song-hard',
   'assets/data/other/owner-song-hard.json');
  var pathResult = NightmareVisionHighscoreMigration.migrate(
   [wrongPath], ownerA, [ownerA], scores, adapter);
  check(pathResult.skipped == 1 && loads == 0
   && pathResult.diagnostics.join(',').indexOf('chart-path-missing') >= 0,
   'a path outside its registered chart folder must be rejected before parse');
  var foreign = entry('owner-song', 2, ownerA, 'Dad Battle', 'owner-song-hard');
  foreign.ownerManifest = manifest(ownerB);
  var ownerResult = NightmareVisionHighscoreMigration.migrate(
   [foreign], ownerA, [ownerA, ownerB], scores, adapter);
  check(ownerResult.skipped == 1 && loads == 0
   && ownerResult.diagnostics.join(',').indexOf('chart-owner-mismatch') >= 0,
   'the selected NMV manifest owner must match provenance before native score use');

  // Two owner-qualified records with the same source title cannot alias together.
  resetNative();
  var aKey = Highscore.formatSong('owner-alias-a', 2, 'best-score');
  var bKey = Highscore.formatSong('owner-alias-b', 2, 'best-score');
  Highscore.songScores.set(aKey, 100);
  Highscore.songAccuracy.set(aKey, 0.7);
  Highscore.songScores.set(bKey, 200);
  Highscore.songAccuracy.set(bKey, 0.8);
  var ambiguousScores = makeScores(ownerA, new OwnerSave(), adapter);
  loads = 0;
  var ambiguous = NightmareVisionHighscoreMigration.migrate([
   entry('owner-alias-a', 2, ownerA, 'Shared Title', 'owner-alias-a-hard'),
   entry('owner-alias-b', 2, ownerB, 'Shared Title', 'owner-alias-b-hard')
  ], ownerA, [ownerA, ownerB], ambiguousScores, adapter);
  check(ambiguous.ambiguous == 1 && ambiguous.skipped == 2 && loads == 2
   && !ambiguousScores.songScores.exists('shared-title-hard'),
   'colliding native identities must be skipped instead of merged into one owner key');

  // Even a failed owner save restores borrowed adapter state.
  resetNative();
  Highscore.songScores.set(scoreKey, 12);
  Highscore.songAccuracy.set(scoreKey, 0.4);
  var failingSave = new OwnerSave();
  failingSave.failWrites = true;
  var failingScores = makeScores(ownerA, failingSave, adapter);
  var failed = false;
  try NightmareVisionHighscoreMigration.migrate(
   [entry('owner-song', 2, ownerA, 'Dad Battle', 'owner-song-hard')],
   ownerA, [ownerA], failingScores, adapter) catch (_:Dynamic) failed = true;
  check(failed && adapter.difficulties.join(',') == 'Easy,Normal,Hard'
   && adapter.currentDifficultyIndex == 0,
   'adapter state must be restored after an owner-save failure');

  adapter.release();
  trace('nightmare vision score migration fixture passed');
 }
}
'''
        stubs = {
            "OptionsHandler.hx": "package; typedef TOptions = Dynamic; class OptionsHandler { public static var options:TOptions = {}; }\n",
            "Judge.hx": "package; enum abstract Jury(Int) from Int to Int { var Judge1; var Judge2; var Judge3; var Judge4; var Judge5; var Judge6; var Judge7; var Judge8; var Judge9; var Classic; var Hard; } class Judge {}\n",
            "ModifierState.hx": "package; class ModifierState { public static var namedModifiers:Dynamic = {}; }\n",
            "DifficultyIcons.hx": "package; class DifficultyIcons { public static function getEndingFP(diff:Int):String return switch (diff) { case 0: '-easy'; case 1: ''; case 2: '-hard'; default: ''; }; }\n",
            "DifficultyManager.hx": "package; class DifficultyManager { public static function getDiffEnding(diff:Int):String return switch (diff) { case 0: '-Easy'; case 1: ''; case 2: '-Hard'; default: throw 'bad difficulty'; }; public static function getDifficultyNames():Array<String> return ['Easy', 'Normal', 'Hard']; }\n",
            "Song.hx": "package; class Song { public static function storageFolder(chart:Dynamic):String { var value = Reflect.field(chart, 'compatStorageFolder'); return value == null ? '' : Std.string(value).toLowerCase(); } }\n",
            "FNFAssets.hx": "package; class FNFAssets { public static function exists(path:String):Bool return sys.FileSystem.exists(path); }\n",
            "CompatScriptManifest.hx": """package;
typedef CompatScriptRoot = { var engine:String; var path:String; @:optional var dependency:Bool; };
typedef CompatScriptManifestData = { var roots:Array<CompatScriptRoot>; @:optional var selectedRoot:String; };
class CompatScriptManifest {
 public static function selectedRoot(data:CompatScriptManifestData):String return data == null ? '' : data.selectedRoot;
 public static function destinationKey(value:String):String return StringTools.replace(StringTools.trim(value == null ? '' : value), '\\\\', '/');
}
""",
            "flixel/FlxG.hx": "package flixel; class FlxG { public static var save:DummySave = new DummySave(); }\nclass DummySave { public var data:Dynamic = {}; public function new() {} public function flush():Void {} }\n",
        }
        with tempfile.TemporaryDirectory(prefix="nmv-score-migration-", dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(main, encoding="utf-8", newline="\n")
            for relative, contents in stubs.items():
                target = work / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(contents, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
