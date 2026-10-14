"""V-Slice data/levels definitions convert to native story weeks."""
from haxe_test_support import HAXE_COMMAND

import json
import subprocess
import tempfile
import unittest
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]


def run_level(level: dict, checks: str, title_png: bool = True) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
        root = Path(folder) / "mod"
        if title_png:
            (root / "images/storymenu/titles").mkdir(parents=True)
            (root / "images/storymenu/titles/test.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        else:
            root.mkdir()
        main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var names = new Map<String, String>();
    names.set("song-a", "Song A");
    var result = VSliceImporter.convertLevel(haxe.Json.parse({json.dumps(json.dumps(level))}), {json.dumps(str(root))}, "testweek", names);
    var week:Dynamic = result.week;
    var codes = [for (finding in result.diagnostics) finding.code];
{checks}
  }}
}}
'''
        (Path(folder) / "Main.hx").write_text(main, newline="\n")
        return subprocess.run(
            [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder, "-main", "Main", "--interp"],
            cwd=ROOT, capture_output=True, text=True,
        )


LEVEL = {
    "version": "1.0.1",
    "name": "TEST WEEK",
    "titleAsset": "storymenu/titles/test",
    "songs": ["song-a", "song-b"],
    "background": "#F9CF51",
    "visible": True,
    "props": [{"assetPath": "storymenu/props/dad", "scale": 1.0, "animations": []}],
}


class VSliceLevelImportTest(unittest.TestCase):
    def test_level_becomes_a_week_with_title_songs_and_colour(self):
        result = run_level(LEVEL, '''
    if (week == null) fail("no week");
    if (week.name != "testweek" || week.desc != "TEST WEEK") fail("week identity");
    var songs:Array<String> = cast week.songs;
    if (songs.length != 2 || songs[0] != "Song A" || songs[1] != "song-b") fail("ordered songs " + songs);
    if (week.color != 0xFFF9CF51) fail("background colour " + week.color);
    if (Reflect.hasField(week, "visibleFlags")) fail("visible week flagged");
    if (result.assets.length != 1 || !result.assets[0].supported
      || result.assets[0].destination != "assets/images/campaign-ui-week/testweek.png"
      || result.assets[0].source.indexOf("storymenu/titles/test.png") < 0) fail("title mapping");
    if (codes.indexOf("level-props-unmapped") < 0) fail("props diagnostic");
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hidden_level_is_debug_only_and_image_background_keeps_default_colour(self):
        level = dict(LEVEL, visible=False, background="storymenu/backgrounds/test", props=[])
        result = run_level(level, '''
    var flags:Array<String> = cast week.visibleFlags;
    if (flags == null || flags[0] != "debug") fail("hidden week");
    if (Reflect.hasField(week, "color")) fail("image background became a colour");
    if (codes.indexOf("level-background-image") < 0) fail("background diagnostic");
    if (codes.indexOf("level-props-unmapped") >= 0) fail("no props, no diagnostic");
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_songs_or_title_are_diagnosed_without_throwing(self):
        level = {key: value for key, value in LEVEL.items() if key != "songs"}
        result = run_level(level, '''
    if (week != null) fail("week without songs");
    if (codes.indexOf("level-missing-songs") < 0) fail("songs diagnostic");
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = run_level(LEVEL, '''
    if (week == null || result.assets[0].supported) fail("missing title should stay unsupported");
    if (codes.indexOf("missing-level-title") < 0) fail("title diagnostic");
''', title_png=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def run_folder(levels: dict, checks: str) -> subprocess.CompletedProcess:
    """Levels are written as data/levels/<id>.json under a generated content root."""
    with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
        root = Path(folder) / "mod"
        (root / "data/levels").mkdir(parents=True)
        (root / "images/storymenu/titles").mkdir(parents=True)
        (root / "images/storymenu/titles/test.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        for level_id, body in levels.items():
            text = body if isinstance(body, str) else json.dumps(body)
            (root / "data/levels" / (level_id + ".json")).write_text(text, newline="\n")
        main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var names = new Map<String, String>();
    names.set("song-a", "Song A");
    names.set("song-c", "Song C");
    var results = VSliceImporter.convertLevelFolder({json.dumps(str(root))}, null, names);
    var ids = [for (result in results) result.id];
{checks}
  }}
}}
'''
        (Path(folder) / "Main.hx").write_text(main, newline="\n")
        return subprocess.run(
            [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder, "-main", "Main", "--interp"],
            cwd=ROOT, capture_output=True, text=True,
        )


class VSliceLevelFolderTest(unittest.TestCase):
    def test_folder_is_ordered_filtered_to_imported_songs_and_survives_bad_files(self):
        levels = {
            "weekB": dict(LEVEL, songs=["song-c", "not-imported"], props=[{"assetPath": ""}]),
            "Weeka": LEVEL,
            "broken": "{ not json",
            "empty": dict(LEVEL, songs=["missing"]),
        }
        result = run_folder(levels, '''
    if (ids.join(",") != "broken,empty,Weeka,weekB") fail("order " + ids.join(","));
    if (results[0].week != null || results[0].diagnostics[0].code != "invalid-level") fail("bad file");
    if (results[1].week != null) fail("level with no imported songs made a week");
    var a:Array<String> = cast results[2].week.songs;
    if (a.join(",") != "Song A") fail("weeka songs " + a.join(","));
    var b:Array<String> = cast results[3].week.songs;
    if (b.join(",") != "Song C") fail("weekb songs " + b.join(","));
    var bCodes = [for (finding in results[3].diagnostics) finding.code];
    if (bCodes.indexOf("level-song-not-imported") < 0) fail("skipped song diagnostic");
    if (bCodes.indexOf("level-props-unmapped") >= 0) fail("blank placeholder prop reported");
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_merge_adds_new_weeks_and_never_replaces_existing_ones(self):
        levels = {"week1": LEVEL, "testweek": dict(LEVEL, songs=["song-c"])}
        result = run_folder(levels, '''
    var registry:Dynamic = haxe.Json.parse('{"weeks":[{"name":"Week1","desc":"native","animation":"","songs":["Bopeebo"]}]}');
    var added = VSliceImporter.mergeLevelWeeks(registry, results);
    if (added.join(",") != "testweek") fail("added " + added.join(","));
    var weeks:Array<Dynamic> = registry.weeks;
    if (weeks.length != 2 || weeks[0].desc != "native" || weeks[1].name != "testweek") fail("registry " + haxe.Json.stringify(registry));
    var existing = [for (finding in results[1].diagnostics) finding.code];
    if (existing.indexOf("level-week-exists") < 0) fail("existing week diagnostic");
    var empty:Dynamic = {};
    if (VSliceImporter.mergeLevelWeeks(empty, results).length != 2 || empty.weeks.length != 2) fail("registry without weeks");
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
