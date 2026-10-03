"""Psych source defaults fill absent chart stages without donor-specific rules."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


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


class PsychStageInferenceTest(unittest.TestCase):
    def test_source_mapping_parser_reads_generic_switches_and_fallbacks(self):
        fixture = '''import PsychStageInference;
class Main {
  static function check(value:Bool, message:String):Void { if (!value) throw message; }
  static function main():Void {
    var source = [
      "class StageData {",
      "  // case 'comment-only': stage = 'fake';",
      "  public static function vanillaSongStage(songName:String):String {",
      "    var stage:String = 'stage';",
      "    switch (songName.toLowerCase()) {",
      "      case 'spookeez' | \\\"monster\\\" | 'south': stage = 'spooky';",
      "      case 'tutorial': stage = \\\"stage\\\";",
      "      default: stage = 'stage';",
      "    }",
      "    return stage;",
      "  }",
      "  public static function unrelated(songName:String):String return 'wrong';",
      "}"
    ].join("\\n");
    check(PsychStageInference.resolveFromSource(source, 'SPOOKEEZ') == 'spooky',
      'grouped case mapping was not resolved case-insensitively');
    check(PsychStageInference.resolveFromSource(source, 'monster') == 'spooky',
      'alternate quote style/case label was not resolved');
    check(PsychStageInference.resolveFromSource(source, 'tutorial') == 'stage',
      'single-case mapping was not resolved');
    check(PsychStageInference.resolveFromSource(source, 'unmapped-song') == 'stage',
      'literal function fallback was not retained');
    var noDefaultCase = "function vanillaSongStage(song:String):String { var stage='generic'; switch(song) { case 'alpha': stage='mapped'; } return stage; }";
    check(PsychStageInference.resolveFromSource(noDefaultCase, 'missing') == 'generic',
      'case assignment was incorrectly treated as the initializer fallback');
    check(PsychStageInference.resolveFromSource(noDefaultCase, 'alpha') == 'mapped',
      'case assignment was not resolved without a default branch');
    check(PsychStageInference.resolveFromSource(
      "function unrelated(song:String):String return 'fake';", 'comment-only') == null,
      'parser inferred from an unrelated function');
    var switchExpression = "function vanillaSongStage(song:String):String { return switch(song) { case 'alpha', 'beta': 'warehouse'; default: 'stage'; }; }";
    check(PsychStageInference.resolveFromSource(switchExpression, 'beta') == 'warehouse',
      'switch expression case value was not parsed');
    check(PsychStageInference.resolveFromSource(switchExpression, 'missing') == 'stage',
      'switch expression default was not parsed');
    var trailingFallback = "function vanillaSongStage(song:String):String { switch(song) { case 'alpha': return 'one'; } return 'generic'; }";
    check(PsychStageInference.resolveFromSource(trailingFallback, 'missing') == 'generic',
      'function-scope literal fallback after switch was not parsed');
    var assignmentAndTrailingReturn = "function vanillaSongStage(song:String):String { var stage='initial'; switch(song) { default: stage='branch'; } return 'literal'; }";
    check(PsychStageInference.resolveFromSource(assignmentAndTrailingReturn, 'missing') == 'literal',
      'function-scope return did not take precedence over switch assignments');
    var returningDefault = "function vanillaSongStage(song:String):String { switch(song) { default: return 'default'; } return 'literal'; }";
    check(PsychStageInference.resolveFromSource(returningDefault, 'missing') == 'default',
      'switch default return was overridden by an unreachable trailing return');
  }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                 "--run", "Main"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_stage_data_lookup_stays_inside_selected_source_root(self):
        fixture = '''import PsychStageInference;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
class Main {
  static function main():Void {
    var root = Sys.args()[0];
    var first = Path.join([root, 'owner-a']);
    var second = Path.join([root, 'owner-b']);
    FileSystem.createDirectory(Path.join([first, 'source/backend']));
    FileSystem.createDirectory(Path.join([second, 'source/backend']));
    File.saveContent(Path.join([first, 'source/backend/StageData.hx']),
      "function vanillaSongStage(song:String):String { var stage='stage'; switch(song) { case 'alpha': stage='one'; } return stage; }");
    File.saveContent(Path.join([second, 'source/backend/StageData.hx']),
      "function vanillaSongStage(song:String):String { var stage='stage'; switch(song) { case 'alpha': stage='two'; } return stage; }");
    if (PsychStageInference.resolve(first, 'alpha') != 'one')
      throw 'selected owner StageData mapping was not used';
    if (PsychStageInference.resolve(second, 'alpha') != 'two')
      throw 'source lookup leaked across import owners';
    if (PsychStageInference.resolve(root, 'alpha') != null)
      throw 'lookup recursively searched child or sibling owners';
  }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                 "--run", "Main", folder],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_import_helper_respects_chart_and_info_stage_values(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("if (engine == ImportEngine.PSYCH", module)
        self.assertIn("inferPsychStageForImport(songData,", module)
        method = extract_method(module, "static function inferPsychStageForImport(")
        fixture = f'''import haxe.io.Path;
using StringTools;
typedef SongImport = {{ var stage:String; }};
class PsychStageInference {{
  public static function resolve(_root:String, song:String):String
    return song.toLowerCase() == 'spookeez' ? 'spooky' : null;
}}
class ImportCompat {{
  static var info:Map<String, Dynamic> = new Map<String, Dynamic>();
  static function processInfo(_path:String):Map<String, Dynamic> return info;
  static function getInfoValue(values:Map<String, Dynamic>, key:String, fallback:String='null'):String {{
    var value = values == null ? null : values.get(key);
    return value == null || StringTools.trim(Std.string(value)) == '' ? fallback : StringTools.trim(Std.string(value));
  }}
  static function chartFieldString(chart:Dynamic, field:String, fallback:String):String {{
    if (chart != null) {{
      var value:Dynamic = Reflect.field(chart, field);
      if (value != null && StringTools.trim(Std.string(value)) != ''
          && Std.string(value).toLowerCase() != 'null') return StringTools.trim(Std.string(value));
    }}
    return fallback;
  }}
{method}
  static function main():Void {{
    var inferred:SongImport={{stage:'stage'}};
    inferPsychStageForImport(inferred, {{song:'spookeez'}}, 'owner', 'data/spookeez', 'fallback');
    if (inferred.stage != 'spooky') throw 'missing stage was not inferred from the chart song id';
    var explicitChart:SongImport={{stage:'stage'}};
    inferPsychStageForImport(explicitChart, {{song:'spookeez',stage:'authored'}}, 'owner', 'data/spookeez', 'fallback');
    if (explicitChart.stage != 'stage') throw 'explicit chart stage was replaced';
    info.set('stage', 'info-authored');
    var explicitInfo:SongImport={{stage:'stage'}};
    inferPsychStageForImport(explicitInfo, {{song:'spookeez'}}, 'owner', 'data/spookeez', 'fallback');
    if (explicitInfo.stage != 'stage') throw 'info.txt stage was replaced';
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "ImportCompat.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "ImportCompat"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
