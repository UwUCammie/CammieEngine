"""Popipo's incomplete difficulty graphics must use sibling metadata."""
from haxe_test_support import HAXE_COMMAND

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


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


class PopipoVisualFallbackTest(unittest.TestCase):
    def test_chart_fixture_exposes_the_incomplete_alias(self):
        folder = ROOT / "assets/data/popipo"
        normal_fixture = folder / "popipo.json"
        hard_fixture = folder / "popipo-hard.json"
        if not normal_fixture.is_file() or not hard_fixture.is_file():
            self.skipTest(f"mounted Popipo chart fixtures unavailable: {normal_fixture}, {hard_fixture}")
        normal = json.loads(normal_fixture.read_text())["song"]
        hard = json.loads(hard_fixture.read_text())["song"]
        self.assertEqual(normal["player2"], "mikuv2")
        self.assertEqual(hard["player2"], "miku")
        self.assertNotEqual(normal["player2"], hard["player2"])

        registry = json.loads(
            (ROOT / "assets/images/custom_chars/custom_chars.jsonc").read_text()
        )
        self.assertEqual(registry["miku"]["like"], "dad")
        self.assertTrue((ROOT / "assets/images/custom_chars/miku.hscript").is_file())
        self.assertFalse((ROOT / "assets/images/custom_chars/miku").is_dir())
        self.assertTrue((ROOT / "assets/images/custom_chars/mikuv2").is_dir())

    def test_incomplete_named_character_falls_back_to_sibling(self):
        source = (ROOT / "source/Song.hx").read_text()
        fields_start = source.index("\tstatic var gameplayFields")
        fields_end = source.index(
            "\n\tpublic static function invalidateVisualRegistryCache", fields_start
        )
        fields = source[fields_start:fields_end]
        resolution_type = """typedef CharacterVisualResolution = {
    var requested:String;
    var registryName:String;
    var selectedRegistryName:String;
    var likeName:String;
    var implementationName:String;
    var assetName:String;
    var implementationPath:String;
    var assetPath:String;
    var assetRootPath:String;
    var complete:Bool;
    var diagnosticCode:String;
    var diagnostic:String;
}
"""
        chart_has_value = extract_method(source, "\tstatic function chartHasValue(")
        read_registry = extract_method(source, "\tstatic function readRegistry(")
        registry_key = extract_method(source, "\tstatic function registryKey(")
        resolver = extract_method(source, "\tpublic static function resolveCharacterVisualFromData(")
        valid_character = extract_method(source, "\tstatic function validCharacter(")
        resolve = extract_method(source, "\tpublic static function resolveChartData(")
        visual_valid = extract_method(source, "\tstatic function visualValueIsValid(")
        is_valid_visual = extract_method(source, "\tstatic function isValidVisualValue(")

        fixture = """import haxe.Json;
using StringTools;

enum Extensions { None; Json; Hscript; }

class FNFAssets {
\tpublic static function getJson(path:String):String {
\t\tif (path == 'assets/images/custom_chars/custom_chars')
\t\t\treturn haxe.Json.stringify({
\t\t\t\tbf: {like: 'bf'}, dad: {like: 'dad'}, gf: {like: 'gf'},
\t\t\t\tmiku: {like: 'dad'}, mikuv2: {like: 'miku'}
\t\t\t});
\t\treturn null;
\t}
\tpublic static function exists(path:String, ?extension:Extensions):Bool {
\t\tswitch (path) {
\t\t\tcase 'assets/images/custom_chars/miku.hscript':
\t\t\t\treturn true;
\t\t\tcase 'assets/images/custom_chars/mikuv2/char.png' | 'assets/images/custom_chars/mikuv2/char.xml':
\t\t\t\treturn true;
\t\t\tcase 'assets/images/custom_chars/miku.hscript':
\t\t\t\treturn true;
\t\t\tcase 'assets/images/custom_chars/bf/char.png' | 'assets/images/custom_chars/dad/char.png'
\t\t\t\t| 'assets/images/custom_chars/gf/char.png':
\t\t\t\treturn true;
\t\t\tcase 'assets/images/custom_chars/bf' | 'assets/images/custom_chars/dad'
\t\t\t\t| 'assets/images/custom_chars/gf':
\t\t\t\treturn true;
\t\t\tdefault:
\t\t\t\treturn false;
\t\t}
\t}
}

class CoolUtil {
\tpublic static function parseJson(raw:String):Dynamic return haxe.Json.parse(raw);
}

""" + resolution_type + """
class PopipoVisualFallbackTest {
""" + fields + """
""" + chart_has_value + """
""" + read_registry + """
""" + registry_key + """
\tstatic function resolveCharacterVisual(name:String):CharacterVisualResolution {
\t\treturn resolveCharacterVisualFromData(name, readRegistry('assets/images/custom_chars/custom_chars'),
\t\t\tfunction(path:String):Bool return FNFAssets.exists(path));
\t}
""" + resolver + """
\tstatic function assetExists(path:String, ?extension:Extensions):Bool return FNFAssets.exists(path, extension);
""" + valid_character + """
\tstatic function validStage(name:String):Bool return name == 'concert';
\tstatic function validUIType(name:String):Bool return name == 'normal';
\tstatic function validCutscene(name:String):Bool return name == 'none';
\tstatic function validLayout(name:String):Bool return name == 'none';
""" + is_valid_visual + """
""" + resolve + """
""" + visual_valid + """
\tstatic function main() {
\t\tvar miku = resolveCharacterVisual('miku');
\t\tif (!validCharacter('miku') || !miku.complete || miku.selectedRegistryName != 'mikuv2')
\t\t\tthrow 'miku did not select its complete sibling visual';
\t\tif (!validCharacter('mikuv2'))
\t\t\tthrow 'mikuv2 was rejected even though its atlas folder is complete';

\t\tvar requested:Dynamic = {
\t\t\tsong: 'popipo', notes: [1], bpm: 145, needsVoices: true, speed: 1,
\t\t\tplayer1: 'bf', player2: 'miku', gf: 'gf', stage: 'concert',
\t\t\tuiType: 'normal', cutsceneType: 'none', forceLayout: 'none',
\t\t\tuiLayoutType: 'none', stageID: 0
\t\t};
\t\tvar normal:Dynamic = {
\t\t\tplayer1: 'bf', player2: 'mikuv2', gf: 'gf', stage: 'concert',
\t\t\tuiType: 'normal', cutsceneType: 'none', forceLayout: 'none',
\t\t\tuiLayoutType: 'none', stageID: 0
\t\t};
\t\tvar resolved = resolveChartData(requested, [normal], normal);
\t\tif (resolved.player2 != 'miku')
\t\t\tthrow 'authored hard-chart character id was not preserved';
\t\tif (resolved.notes != requested.notes || resolved.bpm != requested.bpm)
\t\t\tthrow 'visual fallback replaced Popipo gameplay data';
\t}
}
"""

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "PopipoVisualFallbackTest.hx"
            path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder,
                 "-main", "PopipoVisualFallbackTest", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
