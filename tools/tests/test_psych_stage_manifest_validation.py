"""Psych stage references are valid only through the song's import manifest."""
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


class PsychStageManifestValidationTest(unittest.TestCase):
    def test_stage_validation_is_manifest_scoped_and_difficulty_scoped(self):
        source = (ROOT / "source/Song.hx").read_text()
        fields_start = source.index("\tstatic var gameplayFields")
        fields_end = source.index("\tstatic var registryCache", fields_start)
        fields = source[fields_start:fields_end]
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "\tstatic function chartHasValue(",
                "\tpublic static function resolveChartData(",
                "\tstatic function visualValueIsValid(",
                "\tstatic function validImportedPsychStage(",
                "\tstatic function chartVisualValidity(",
            )
        )
        fixture = """import CompatScriptManifest.CompatScriptManifestData;
import sys.FileSystem;
using StringTools;

class FNFAssets {
  public static function exists(path:String):Bool return FileSystem.exists(path);
  public static function getText(path:String):String return sys.io.File.getContent(path);
}
class NightmareVisionCharacterData {
  public static function load(_root:String, _name:String):Dynamic return null;
}
class NightmareVisionStageData {
  public static function getStageFile(_root:String, _name:String):Dynamic return null;
}

class PsychStageManifestValidationTest {
""" + fields + methods + """
  static function isValidVisualValue(field:String, value:Dynamic):Bool return false;
  static function characterRootForSong(_folder:String):String return '';
  static function characterOwnerEngineForSong(_folder:String):String return '';
  static function ownedStageEntry(_folder:String,_name:String):Dynamic return null;
  static function ownedCutsceneEntry(_folder:String,_name:String):Dynamic return null;
  static function readCharacterRegistryInManifest(_root:String):Dynamic return null;
  static function registryKey(_registry:Dynamic,_name:String):String return null;

  static function main() {
    if (!validImportedPsychStage('Haven', 'song'))
      throw 'the manifest-owned Psych stage was rejected';
    if (validImportedPsychStage('NestedOnly', 'song'))
      throw 'an inactive nested stage script was accepted';
    if (validImportedPsychStage('Foreign', 'song'))
      throw 'a stage under a non-Psych root was accepted';
    if (validImportedPsychStage('../Haven', 'song'))
      throw 'a traversal stage id was accepted';

    var request:Dynamic = {song:'song', notes:[], bpm:120};
    var sibling:Dynamic = {stage:'Haven'};
    var siblingValidity = chartVisualValidity('song', request, [sibling], null);
    if (siblingValidity.exists('stage=Haven'))
      throw 'an imported stage from an arbitrary sibling chart was accepted';
    var siblingResult = resolveChartData(request, [sibling], null, siblingValidity);
    if (Reflect.hasField(siblingResult, 'stage'))
      throw 'an imported stage leaked from an arbitrary sibling chart';
    if (Reflect.field(siblingResult, 'compatStageAuthored') != false)
      throw 'an absent chart stage was marked as authored from sibling metadata';

    var spoofed = resolveChartData({song:'song', notes:[], bpm:120,
      compatStageAuthored:true}, [], null);
    if (Reflect.field(spoofed, 'compatStageAuthored') != false)
      throw 'serialized stage provenance must be overwritten by the chart merge';

    var defaultChart:Dynamic = {stage:'Haven'};
    var defaultValidity = chartVisualValidity('song', request, [], defaultChart);
    if (!defaultValidity.exists('stage=Haven'))
      throw 'the imported stage on the selected default chart was rejected';
    var resolved = resolveChartData(request, [], defaultChart, defaultValidity);
    if (resolved.stage != 'Haven')
      throw 'the validated default Psych stage was not retained';
    if (Reflect.field(resolved, 'compatStageAuthored') != true)
      throw 'a selected default chart stage must retain its authored provenance';
    var explicit = resolveChartData({song:'song', notes:[], bpm:120, stage:'Haven'},
      [], defaultChart, defaultValidity);
    if (Reflect.field(explicit, 'compatStageAuthored') != true)
      throw 'a selected chart stage must retain its authored provenance';
  }
}
"""

        with tempfile.TemporaryDirectory(prefix="psych-stage-manifest-") as folder:
            temp = Path(folder)
            (temp / "assets/data/song").mkdir(parents=True)
            (temp / "assets/imported_mods/psych-root/stages").mkdir(parents=True)
            (temp / "assets/imported_mods/psych-root/stages/Unused").mkdir()
            (temp / "assets/imported_mods/vslice-root/stages").mkdir(parents=True)
            (temp / "assets/imported_mods/psych-root/stages/Haven.lua").write_text("", newline='\n')
            (temp / "assets/imported_mods/psych-root/stages/Unused/NestedOnly.lua").write_text("", newline='\n')
            (temp / "assets/imported_mods/vslice-root/stages/Foreign.lua").write_text("", newline='\n')
            (temp / "assets/data/song/compatScripts.json").write_text(
                '{"roots":['
                '{"engine":"Psych Engine","path":"assets/imported_mods/psych-root"},'
                '{"engine":"V-Slice","path":"assets/imported_mods/vslice-root"}'
                '],"selectedRoot":"assets/imported_mods/psych-root"}'
            , newline='\n')
            (temp / "PsychStageManifestValidationTest.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(temp), "-cp", str(ROOT / "source"),
                 "-main", "PsychStageManifestValidationTest", "--interp"],
                cwd=temp,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        self.assertIn("var validity = chartVisualValidity(folderLower, requestedJson, fallbackCharts, baseChart);", source)
        self.assertIn("!visualValueIsValid('stage', parsedJson.stage, validity)", source)


if __name__ == "__main__":
    unittest.main()
