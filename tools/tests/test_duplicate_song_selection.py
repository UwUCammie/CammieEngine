"""Distinct same-name packages survive while duplicate source views collapse."""

from pathlib import Path
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


class DuplicateSongSelectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        cls.selection_methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "static function songCandidateChartCount",
                "static function songCandidateCompleteness",
                "static function compareSongCandidates",
                "static function songCandidateOrigin",
                "static function selectSongCandidates",
            )
        )

    def test_later_complete_root_wins_and_loser_keeps_donor_chart(self):
        fixture = f'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

typedef ConvertedSongChart = {{
  var difficulty:String; var fileName:String; var source:String; var chart:Dynamic;
  @:optional var authoredSongTitle:Bool;
}};
typedef SongImport = {{
  var name:String;
  @:optional var inst:String;
  @:optional var voices:String;
  @:optional var dialog:String;
  @:optional var modchart:String;
  @:optional var generatedModchart:String;
  @:optional var diffFiles:Array<String>;
  @:optional var convertedCharts:Array<ConvertedSongChart>;
  @:optional var noteDefinitions:Array<Dynamic>;
  @:optional var convertedCharacters:Array<Dynamic>;
  @:optional var convertedStage:Dynamic;
  @:optional var engine:String;
  @:optional var diagnostics:Array<String>;
  @:optional var sourceRoot:String;
  @:optional var sourceDuplicate:Bool;
  @:optional var sourceDuplicateOf:String;
  @:optional var importSourceInfo:SongImportSource;
}};
typedef SongImportSource = {{ var song:String; var data:String; var destination:String; }};
typedef SongImportCandidate = {{
  var song:SongImport; var root:String; var engine:String;
  @:optional var source:SongImportSource;
}};

class ModuleFunctions {{
  static function validImportPath(path:String):Bool
    return path != null && FileSystem.exists(path) && !FileSystem.isDirectory(path);
  static function readSongChart(path:String):Dynamic {{
    if (!validImportPath(path)) return null;
    var parsed:Dynamic = Json.parse(File.getContent(path));
    return parsed != null && Reflect.field(parsed, 'song') != null ? parsed : null;
  }}
  static function importPathKey(path:String):String return Path.normalize(path).toLowerCase();
{self.selection_methods}
  public static function choose(candidates:Array<SongImportCandidate>):Array<SongImportCandidate>
    return selectSongCandidates(candidates);
}}

class Main {{
  static function fail(message:String):Void throw message;
  static function touch(path:String, contents:String):Void {{
    File.saveContent(path, contents);
  }}
  static function song(name:String, inst:String, charts:Array<String>, voices:String,
      dialog:String, modchart:String):SongImport return {{
    name:name, inst:inst, diffFiles:charts, voices:voices, dialog:dialog, modchart:modchart
  }};
  static function main() {{
    var base = Sys.args()[0];
    var weakRoot = Path.join([base, 'root-z-incomplete']);
    var strongRoot = Path.join([base, 'root-a-complete']);
    FileSystem.createDirectory(weakRoot);
    FileSystem.createDirectory(strongRoot);
    var weakChart = Path.join([weakRoot, 'mix.json']);
    var strongChart = Path.join([strongRoot, 'mix.json']);
    var strongHard = Path.join([strongRoot, 'mix-hard.json']);
    var weakInst = Path.join([weakRoot, 'Inst.ogg']);
    var strongInst = Path.join([strongRoot, 'Inst.ogg']);
    var voices = Path.join([strongRoot, 'Voices.ogg']);
    var dialog = Path.join([strongRoot, 'dialog.txt']);
    var modchart = Path.join([strongRoot, 'modchart.hscript']);
    for (path in [weakInst, strongInst, voices]) File.saveContent(path, 'audio');
    touch(dialog, 'dialog');
    touch(modchart, 'function onCreate() {{}}');
    touch(weakChart, '{{"song":{{"song":"Mixed"}}}}');
    touch(strongChart, '{{"song":{{"song":"Mixed"}}}}');
    touch(strongHard, '{{"song":{{"song":"Mixed"}}}}');

    // Independent packages with the same song title must both be importable.
    var candidates:Array<SongImportCandidate> = [
      {{song:song('Mixed', weakInst, [weakChart], null, null, null), root:weakRoot, engine:'Legacy',
        source:{{song:weakRoot, data:weakRoot, destination:'mixed'}}}},
      {{song:song('mixed', strongInst, [strongChart, strongHard], voices, dialog, modchart), root:strongRoot, engine:'Psych',
        source:{{song:strongRoot, data:strongRoot, destination:'mixed'}}}}
    ];
    var selected = ModuleFunctions.choose(candidates);
    if (selected.length != 2 || selected[0].song.sourceDuplicate || selected[1].song.sourceDuplicate)
      fail('independent packages sharing a title were collapsed');
    if (selected[0].song.importSourceInfo.data != weakRoot || selected[1].song.importSourceInfo.data != strongRoot)
      fail('candidate source folders were crossed');

    // Two scanner views of the same physical chart directory are one source.
    var aliases = ModuleFunctions.choose([
      {{song:song('Mixed', weakInst, [weakChart], null, null, null), root:weakRoot, engine:'Legacy',
        source:{{song:weakRoot, data:strongRoot, destination:'mixed'}}}},
      {{song:song('mixed', strongInst, [strongChart, strongHard], voices, dialog, modchart), root:strongRoot, engine:'Psych',
        source:{{song:strongRoot, data:strongRoot, destination:'mixed'}}}}
    ]);
    if (aliases.length != 2 || aliases[0].song.sourceRoot != strongRoot || aliases[0].song.sourceDuplicate)
      fail('more complete source alias did not win');
    if (!aliases[1].song.sourceDuplicate || aliases[1].song.sourceDuplicateOf != strongRoot)
      fail('less complete source alias was not marked duplicate');
    if (aliases[1].song.diffFiles[0] != weakChart || File.getContent(weakChart) != '{{"song":{{"song":"Mixed"}}}}')
      fail('duplicate donor chart was changed');
    trace('DUPLICATE_SELECTION_OK');
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            temp_path = Path(folder)
            fixture_path = temp_path / "Main.hx"
            fixture_path.write_text(fixture)
            donor = temp_path / "donor"
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "--run", "Main", str(donor)],
                cwd=folder,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("DUPLICATE_SELECTION_OK", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
