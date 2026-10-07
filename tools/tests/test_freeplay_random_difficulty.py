"""Tests for difficulty fallback when Freeplay's random entry chooses a song."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class FreeplayRandomDifficultyTest(unittest.TestCase):
    @unittest.skipUnless(HAXE.is_file(), "portable Haxe interpreter is unavailable")
    def test_valid_difficulty_resolution_uses_selected_songs_supported_charts(self):
        method = extract_method(
            (ROOT / "source/DifficultyManager.hx").read_text(),
            "public static function getValidDiff(",
        )
        fixture = f'''class DifficultyManager {{
  static var diffJson:Dynamic = {{defaultDiff: 1}};
  public static var supported:Map<String, Array<Int>> = new Map();
  static function getSupportedDiffs(song:String):Array<Int> {{
    return supported.exists(song) ? supported.get(song) : [];
  }}
  static function changeDifficulty(diff:Int):Dynamic {{ return {{difficulty: diffJson.defaultDiff}}; }}
{method}
}}
class Main {{
  static function fail(message:String):Void throw message;
  static function main() {{
    DifficultyManager.supported.set("default-available", [0, 1]);
    DifficultyManager.supported.set("hardest-only", [3]);
    DifficultyManager.supported.set("selected-present", [1, 2, 3]);
    if (DifficultyManager.getValidDiff(3, "default-available") != 1)
      fail("unsupported random-song difficulty did not prefer the configured default");
    if (DifficultyManager.getValidDiff(0, "hardest-only") != 3)
      fail("song without the default difficulty did not select a supported fallback");
    if (DifficultyManager.getValidDiff(2, "selected-present") != 2)
      fail("valid selected difficulty was changed");
    if (DifficultyManager.getValidDiff(3, "missing-support") != 1)
      fail("empty chart support did not use the manager fallback");
    Sys.println("freeplay-random-difficulty-ok");
  }}
}}'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "Main"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("freeplay-random-difficulty-ok", result.stdout + result.stderr)

    @unittest.skipUnless(HAXE.is_file(), "portable Haxe interpreter is unavailable")
    def test_random_entry_uses_shared_availability_and_difficulty_rules(self):
        source = (ROOT / "source/FreeplayState.hx").read_text()
        selector = extract_method(source, "function randomPlayableSelection()")
        provisional = extract_method(source, "function isProvisionalSelection(")
        allowed_selection = extract_method(source, "function availabilityAllowsSelection(")
        allowed_launch = extract_method(source, "function availabilityAllowsLaunch(")

        self.assertIn("isProvisionalSelection(index)", selector)
        self.assertIn("DifficultyManager.getValidDiff(curDifficulty, songs[index].songName)", selector)
        self.assertIn("availabilityAllowsLaunch(index, difficulty)", selector)
        self.assertNotIn("expurgation", selector.lower())
        self.assertNotIn("case 'test'", selector.lower())

        update = extract_method(source, "override function update(")
        random_entry = update[update.index("if (songs[curSelected].songName.toLowerCase() == 'random-song')") :]
        self.assertIn("daSelection = randomPlayableSelection();", random_entry)
        self.assertIn("curDifficulty = DifficultyManager.getValidDiff(curDifficulty,", random_entry)
        self.assertIn("if (!availabilityAllowsLaunch(daSelection, curDifficulty))", random_entry)

        manager = (ROOT / "source/DifficultyManager.hx").read_text()
        valid_diff = extract_method(manager, "public static function getValidDiff(")
        methods = "\n".join([
            provisional,
            allowed_selection,
            allowed_launch,
            selector.replace("function randomPlayableSelection()", "public function randomPlayableSelection()"),
        ])
        fixture = f'''typedef FreeplayAvailabilityDecision = {{ready:Bool,state:String,reason:String}};
class SongMetadata {{
  public var songName:String;
  public var isProvisional:Bool;
  public function new(name:String, provisional:Bool=false) {{ songName=name; isProvisional=provisional; }}
}}
class RandomStub {{
  public var chooseLast:Bool=false;
  public var lastMin:Int=-1;
  public var lastMax:Int=-1;
  public function new() {{}}
  public function int(min:Int,max:Int):Int {{ lastMin=min; lastMax=max; return chooseLast ? max : min; }}
}}
class FlxG {{ public static var random:RandomStub = new RandomStub(); }}
class DifficultyManager {{
  public static var diffJson:Dynamic = {{defaultDiff:1,difficulties:[{{name:"easy"}},{{name:"normal"}},{{name:"hard"}},{{name:"expert"}}]}};
  public static var supported:Map<String,Array<Int>> = new Map();
  public static function getSupportedDiffs(song:String):Array<Int> return supported.exists(song) ? supported.get(song) : [];
  public static function changeDifficulty(diff:Int,change:Int=0):Dynamic {{
    var count:Int=cast diffJson.difficulties.length; var result:Int=(diff+change)%count; if(result<0) result+=count;
    return {{difficulty:result}};
  }}
{valid_diff}
}}
class Harness {{
  public var songs:Array<SongMetadata>=[];
  public var curDifficulty:Int=3;
  public var soundTest:Bool=false;
  public var ready:Map<String,Bool>=new Map();
  public var matches:Map<String,Bool>=new Map();
  public var launchChecks:Array<String>=[];
  public var availabilityChecks:Array<String>=[];
  public function new() {{}}
  function songMatches(index:Int):Bool return !matches.exists(songs[index].songName) || matches.get(songs[index].songName);
  function refreshAvailabilityForInteraction():Void {{}}
  function songAvailability(index:Int):FreeplayAvailabilityDecision {{
    var name=songs[index].songName;
    availabilityChecks.push(name);
    return {{ready:ready.exists(name) && ready.get(name),state:"fixture",reason:""}};
  }}
  function selectionHasChart(name:String,difficulty:Int):Bool {{
    launchChecks.push(name+":"+difficulty);
    return DifficultyManager.getSupportedDiffs(name).contains(difficulty);
  }}
  {methods}
}}
class Main {{
  static function fail(message:String):Void throw message;
  static function main() {{
    DifficultyManager.supported.set("ready-hard-only", [3]);
    DifficultyManager.supported.set("pending-provisional", [1]);
    DifficultyManager.supported.set("pending-refresh", [1]);
    DifficultyManager.supported.set("expurgation", [0,2]);
    DifficultyManager.supported.set("test", [1]);
    DifficultyManager.supported.set("missing-chart", []);
    DifficultyManager.supported.set("search-hidden", [1]);
    DifficultyManager.supported.set("random-song", [1]);
    var freeplay=new Harness();
    freeplay.songs=[
      new SongMetadata("ready-hard-only"),
      new SongMetadata("pending-provisional", true),
      new SongMetadata("pending-refresh"),
      new SongMetadata("expurgation"),
      new SongMetadata("test"),
      new SongMetadata("missing-chart"),
      new SongMetadata("search-hidden"),
      new SongMetadata("random-song")
    ];
    for (name in ["ready-hard-only","pending-provisional","expurgation","test","missing-chart","search-hidden","random-song"])
      freeplay.ready.set(name,true);
    freeplay.ready.set("pending-refresh",false);
    freeplay.matches.set("search-hidden",false);
    var first=freeplay.randomPlayableSelection();
    if(first!=0) fail("random selection included pending, missing-chart, search-hidden, or random rows");
    if(FlxG.random.lastMin!=0 || FlxG.random.lastMax!=2)
      fail("random selection did not choose only from the three launch-ready songs");
    if(freeplay.availabilityChecks.indexOf("pending-refresh")<0)
      fail("pending committed row was not checked through the shared launch gate");
    if(freeplay.availabilityChecks.indexOf("pending-provisional")>=0)
      fail("provisional row reached the availability gate");
    if(freeplay.launchChecks.indexOf("expurgation:2")<0 || freeplay.launchChecks.indexOf("test:1")<0)
      fail("song-named cases did not use common supported-difficulty resolution");
    FlxG.random.chooseLast=true;
    var last=freeplay.randomPlayableSelection();
    if(last!=4) fail("random selection's last eligible result was not the ordinary ready song");
    Sys.println("freeplay-random-availability-ok");
  }}
}}'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "Main.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "Main"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("freeplay-random-availability-ok", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
