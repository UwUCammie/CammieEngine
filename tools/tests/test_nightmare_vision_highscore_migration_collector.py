"""Exercise the actual bounded NMV legacy score candidate collector."""
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    quote = None
    escaped = False
    line_comment = False
    block_comment = False
    index = brace
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and following == "/":
                block_comment = False
                index += 1
        elif quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char == "/" and following == "/":
            line_comment = True
            index += 1
        elif char == "/" and following == "*":
            block_comment = True
            index += 1
        elif char in ("'", '"'):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
        index += 1
    raise AssertionError(f"unterminated Haxe method: {marker}")


class NightmareVisionHighscoreMigrationCollectorTest(unittest.TestCase):
    def test_filters_before_chart_reads_and_loads_exact_registered_jsonc_without_global_song_loader(self):
        source = (ROOT / "source/NightmareVisionStateSession.hx").read_text(encoding="utf-8")
        methods = "\n\n".join(
            extract_method(source, marker)
            for marker in (
                "function ensureAlive(",
                "public function loadHighscores():Void {",
                "function collectHighscoreMigrationEntries(",
                "function loadHighscoreMigrationChart(",
                "static function readBoundedScoreMetadata(",
                "static function safeScoreMigrationOwner(",
                "static function safeScoreMigrationSongId(",
                "static function scoreMigrationContainsDifficulty(",
            )
        )
        fixture = r'''package;
import NightmareVisionHighscoreMigration.NightmareVisionHighscoreMigrationEntry;

class SourceMods {
 public var ownerRoot:String = 'assets/imported_mods/family/root';
 public var released:Bool = false;
 public var family:Array<String> = ['assets/imported_mods/family/root', 'assets/imported_mods/family/child'];
 public function new() {}
 public function authorizedRoots():Array<String> return family;
}

class CollectorHarness {
 static inline var MAX_SCORE_MIGRATION_METADATA_BYTES:Int = 131072;
 public var released:Bool = false;
 public var mods:SourceMods = new SourceMods();
 public var highscores:NightmareVisionHighscore = new NightmareVisionHighscore();
 public var difficulty:NightmareVisionDifficultyAdapter = new NightmareVisionDifficultyAdapter();
 var highscoreMigrationAttempted:Bool = false;
 public function new() {}
 public function report(name:String, callback:String, error:Dynamic):Void
  FixtureLog.reports.push(name + ':' + callback);
 __METHODS__
 public function collect():Array<NightmareVisionHighscoreMigrationEntry>
  return collectHighscoreMigrationEntries();
 public function loadForTest():Void loadHighscores();
}

class FixtureLog {
 public static var reports:Array<String> = [];
 public static function check(ok:Bool, message:String):Void if (!ok) throw message;
 public static function metadataPath(name:String):String return 'assets/data/' + name + '/importProvenance.json';
 public static function manifestPath(name:String):String return 'assets/data/' + name + '/compatScripts.json';
 static function addMetadata(name:String, owner:String, ?roots:Dynamic):Void {
  var folder = 'assets/data/' + name + '/';
  FNFAssets.files.set(folder + 'importProvenance.json', haxe.Json.stringify({
   version:1, sourceEngine:'Nightmare Vision', destinationFolder:name,
   sourceOwner:owner, sourceFolder:'Songs/' + name,
   sourceSelectableDifficulties:['Normal'], sourceUnsupportedDifficulties:[]
  }));
  if (roots == null) roots = [{path:owner, engine:'Nightmare Vision', dependency:false}];
  FNFAssets.files.set(folder + 'compatScripts.json', haxe.Json.stringify({selectedRoot:owner, roots:roots}));
 }
 public static function run():Void {
  FNFAssets.reset(); Highscore.reset();
  FreeplayRegistry.rows = ['no-score', 'partial', 'foreign', 'invalid-manifest', 'registered'];
  Highscore.songScores.set('partial:0:best-score', 20);
  Highscore.songScores.set('foreign:0:best-score', 25);
  Highscore.songAccuracy.set('foreign:0:best-score', 0.8);
  Highscore.songScores.set('invalid-manifest:0:best-score', 30);
  Highscore.songAccuracy.set('invalid-manifest:0:best-score', 0.9);
  Highscore.songScores.set('registered:0:best-score', 40);
  Highscore.songAccuracy.set('registered:0:best-score', 0.95);
  addMetadata('partial', 'assets/imported_mods/family/child');
  addMetadata('foreign', 'assets/imported_mods/outside/mod');
  addMetadata('invalid-manifest', 'assets/imported_mods/family/child', null);
  FNFAssets.files.set(manifestPath('invalid-manifest'), haxe.Json.stringify({selectedRoot:'assets/imported_mods/family/child', roots:null}));
  addMetadata('registered', 'assets/imported_mods/family/child');
  FNFAssets.files.set('assets/data/registered/registered.jsonc', haxe.Json.stringify({song:{song:'Registered Display'}}));

  var harness = new CollectorHarness();
  var entries = harness.collect();
  check(entries.length == 1 && entries[0].registeredSong == 'registered',
   'only an authenticated family chart with a complete native pair should become a candidate');
  check(!FNFAssets.reads.exists('assets/data/no-score/importProvenance.json')
   && !FNFAssets.reads.exists('assets/data/partial/importProvenance.json'),
   'rows without a complete native pair must be filtered before provenance reads');
  check(FNFAssets.reads.exists('assets/data/foreign/importProvenance.json')
   && !FNFAssets.reads.exists('assets/data/foreign/foreign.json'),
   'foreign owner receipts may be checked but must never cause a chart body read');
  check(!FNFAssets.reads.exists('assets/data/invalid-manifest/invalid-manifest.json'),
   'a malformed owner roots value must skip the row without reading its chart');
  check(!FNFAssets.reads.exists('assets/data/registered/registered.jsonc'),
   'the registered chart body must remain lazy until the paired migration candidate requests it');

  var chart:Dynamic = entries[0].loadChart();
  check(FNFAssets.reads.exists('assets/data/registered/registered.jsonc'),
   'the lazy callback should read the selected JSONC chart when JSON is absent');
  check(Reflect.field(chart, 'song') == 'Registered Display'
   && Reflect.field(chart, 'compatStorageFolder') == 'registered'
   && Reflect.field(chart, 'compatChartFileName') == 'registered'
   && Reflect.field(chart, 'compatScoreSongId') == 'registered',
   'the chart callback must attach the actual registered folder identity to the raw chart');
  check(Song.loadFromJsonCalls == 0, 'migration chart inspection must not mutate global Song.loadFromJson state');

  harness.loadForTest(); harness.loadForTest();
  check(harness.highscores.loadCalls == 2,
   'each source Init visit must reload its private highscore save');
  check(NightmareVisionHighscoreMigration.migrateCalls == 1,
   'the bounded native migration should run once per captured owner session');
 }
}

class Main { static function main():Void FixtureLog.run(); }
'''.replace("__METHODS__", methods)

        migration_stub = r'''package;
import CompatScriptManifest.CompatScriptManifestData;
typedef NightmareVisionHighscoreMigrationEntry = {
 var registeredSong:String;
 var nativeDifficultyIndex:Int;
 var destinationChartPath:String;
 var provenance:Dynamic;
 var ownerManifest:CompatScriptManifestData;
 @:optional var chart:Dynamic;
 @:optional var loadChart:Void->Dynamic;
}
class NightmareVisionHighscoreMigration {
 public static var migrateCalls:Int = 0;
 public static function migrate(entries:Array<NightmareVisionHighscoreMigrationEntry>, owner:String,
  roots:Array<String>, scores:NightmareVisionHighscore, difficulty:NightmareVisionDifficultyAdapter,
  report:String->Void):Dynamic {migrateCalls++;return {diagnostics:[]};}
}
'''
        manifest_stub = r'''package;
typedef CompatRoot = { var path:String; var engine:String; @:optional var dependency:Bool; }
typedef CompatScriptManifestData = { var selectedRoot:String; var roots:Array<CompatRoot>; }
class CompatScriptManifest {
 public static inline var FILE_NAME:String = 'compatScripts.json';
 public static function parse(raw:String):CompatScriptManifestData return cast haxe.Json.parse(raw);
 public static function selectedRoot(data:CompatScriptManifestData):String return data == null ? null : data.selectedRoot;
 public static function destinationKey(path:String):String return path == null ? '' : StringTools.replace(StringTools.trim(path), '\\', '/').toLowerCase();
}
'''
        stubs = {
            "NightmareVisionHighscore.hx": "package; class NightmareVisionHighscore { public var loadCalls:Int=0; public function new() {} public function load():Void loadCalls++; }\n",
            "NightmareVisionDifficultyAdapter.hx": "package; class NightmareVisionDifficultyAdapter { public function new() {} }\n",
            "ImportEngine.hx": "package; class ImportEngine { public static inline var NIGHTMARE_VISION:String = 'Nightmare Vision'; }\n",
            "CoolUtil.hx": "package; class CoolUtil { public static function parseJson(raw:String):Dynamic return haxe.Json.parse(raw); }\n",
            "FreeplayRegistry.hx": "package; class FreeplayRegistry { public static var rows:Array<String>=[]; public static function getJson():Dynamic return [{songs:[for (name in rows) {name:name}]}]; }\n",
            "DifficultyManager.hx": "package; class DifficultyManager { public static function getDifficultyNames():Array<String> return ['Normal','Hard']; public static function getDiffEnding(index:Int):String return index == 0 ? '' : '-hard'; }\n",
            "Highscore.hx": r'''package;
class Highscore {
 public static var songScores:Map<String,Int> = new Map();
 public static var songAccuracy:Map<String,Float> = new Map();
 public static function reset():Void {songScores=new Map();songAccuracy=new Map();}
 public static function formatSong(song:String, diff:Int, kind:String):String return song + ':' + diff + ':' + kind;
}
''',
            "FNFAssets.hx": r'''package;
class FNFAssets {
 public static var files:Map<String,String> = new Map();
 public static var reads:Map<String,Bool> = new Map();
 public static function reset():Void {files=new Map();reads=new Map();}
 public static function exists(path:String):Bool return files.exists(path);
 public static function getText(path:String):String {reads.set(path,true);return files.get(path);}
 public static function resolveCaseInsensitivePath(path:String):Null<String> return null;
}
''',
            "Song.hx": r'''package;
class Song {
 public static var loadFromJsonCalls:Int = 0;
 public static function attachFreeplayScoreSongId(chart:Dynamic, songId:String):Bool {
  Reflect.setField(chart,'compatScoreSongId',songId); return true;
 }
 public static function loadFromJson(json:String, folder:String):Dynamic {loadFromJsonCalls++;return null;}
}
''',
            "CompatScriptManifest.hx": manifest_stub,
            "NightmareVisionHighscoreMigration.hx": migration_stub,
        }
        with tempfile.TemporaryDirectory(prefix="nmv-score-collector-", dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            for name, content in stubs.items():
                (work / name).write_text(content, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "--main", "Main", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
