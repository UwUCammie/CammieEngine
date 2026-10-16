"""V-Slice base-game stage ids resolve to the native stage unless the donor overrides them."""

from __future__ import annotations
from haxe_test_support import HAXE_COMMAND

import json
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"


def haxe_string(value: str) -> str:
    return json.dumps(str(value))


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
                return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class VSliceBaseStageIdsTest(unittest.TestCase):
    def test_sonic_jam_style_erect_stage_ids_select_native_variant(self):
        metadata = {
            "version": "2.2.4",
            "songName": "Erect Id Fixture",
            "playData": {
                "difficulties": ["normal"],
                "characters": {"player": "bf", "opponent": "dad"},
                "stage": "limoRideErect",
            },
            "timeChanges": [{"t": 0, "bpm": 120}],
        }
        chart = {
            "version": "2.0.0",
            "scrollSpeed": {"normal": 1.0},
            "notes": {"normal": [{"t": 100, "d": 0}]},
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            fixture = Path(folder)
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var ids:Array<Array<Dynamic>> = [["limoRideErect", "limo", 1], ["limoRide", "limo", 0], ["mallXmasErect", "mall", 1],
      ["tankmanBattlefieldErect", "tank", 1], ["mainStageErect", "stage", 1],
      ["spookyMansionErect", "spooky", 1], ["phillyTrainErect", "philly", 1]];
    for (entry in ids) {{
      var meta = Json.parse({haxe_string(json.dumps(metadata))});
      meta.playData.stage = entry[0];
      var song:Dynamic = VSliceImporter.convert(meta, Json.parse({haxe_string(json.dumps(chart))})).charts[0].chart.song;
      if (song.stage != entry[1] || song.stageID != entry[2])
        fail(entry[0] + " resolved to " + song.stage + "/" + song.stageID);
    }}
  }}
}}
'''
            Path(fixture, "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(HSCRIPT), "-cp", str(fixture),
                 "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_donor_definition_for_a_base_stage_id_keeps_the_donor_stage(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        methods = "\n".join(
            extract_method(module, marker)
            for marker in (
                "static function chartFieldString",
                "static function vSliceStageIsNative",
                "static function restoreVSliceDonorStage",
            )
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            fixture = Path(folder)
            main = f'''import haxe.Json;
import ImportRootScanner.ImportRoot;
typedef ConvertedSongChart = {{
  var difficulty:String; var fileName:String; var source:String; var chart:Dynamic;
}}
class ModuleFunctions {{
  public static var donorStages:Array<String> = [];
  static function findVSliceDefinition(root:ImportRoot, kind:String, reference:String):String
    return kind == 'stage' && donorStages.indexOf(reference) >= 0 ? 'data/stages/' + reference + '.json' : null;
{methods}
  public static function isNative(reference:String):Bool return vSliceStageIsNative(null, reference);
  public static function restore(playData:Dynamic, charts:Array<ConvertedSongChart>):Void
    restoreVSliceDonorStage(null, playData, charts);
}}
class Main {{
  static function fail(value:String):Void throw value;
  static function chart():ConvertedSongChart
    return {{difficulty:"normal", fileName:"a.json", source:"c.json", chart:{{song:{{stage:"limo", stageID:1}}}}}};
  static function main() {{
    // No donor definition: the base stage id stays native.
    if (!ModuleFunctions.isNative("limoRideErect")) fail("base stage id without a donor definition");
    var charts = [chart()];
    ModuleFunctions.restore({{stage:"limoRideErect"}}, charts);
    if (charts[0].chart.song.stage != "limo" || charts[0].chart.song.stageID != 1)
      fail("native stage was rewritten without a donor definition");
    // The donor ships its own limoRideErect: it replaces the base stage.
    ModuleFunctions.donorStages = ["limoRideErect"];
    if (ModuleFunctions.isNative("limoRideErect")) fail("donor override was ignored");
    ModuleFunctions.restore({{stage:"limoRideErect"}}, charts);
    if (charts[0].chart.song.stage != "limoRideErect" || charts[0].chart.song.stageID != 0)
      fail("donor stage identity was not restored: " + charts[0].chart.song.stage);
    // Native spellings and custom donor ids never change.
    ModuleFunctions.donorStages = ["limo", "limoRideSonic"];
    if (!ModuleFunctions.isNative("limo")) fail("native stage name became overridable");
    if (ModuleFunctions.isNative("limoRideSonic")) fail("custom stage reported as native");
  }}
}}
'''
            Path(fixture, "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(HSCRIPT), "-cp", str(fixture),
                 "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
