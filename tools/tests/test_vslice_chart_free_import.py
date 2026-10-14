"""A V-Slice package without songs still reports what it ships for import."""
from haxe_test_support import HAXE_COMMAND

import json
import subprocess
import tempfile
import unittest
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]

# Generated package shaped like a song-less V-Slice mod: character, stage and
# note style definitions, one level, scripted classes in both extensions, an
# import defaults file and a _merge patch.
SONGLESS = {
    "_polymod_meta.json": json.dumps({"title": "Fixture", "api_version": "0.8.0"}),
    "data/characters/fixture-char.json": json.dumps({"version": "1.0.0", "name": "Fixture"}),
    "data/characters/bad name.json": "{}",
    "data/stages/fixture-stage.json": json.dumps({"version": "1.0.0", "name": "Stage"}),
    "data/notestyles/fixture-style.json": json.dumps({"version": "1.0.0", "name": "Style"}),
    "data/levels/fixture-level.json": json.dumps({"name": "LEVEL", "songs": ["a"]}),
    "scripts/import.hx": "import flixel.FlxG;\n",
    "scripts/modules/FixtureModule.hxc": "class FixtureModule extends Module { public function new() { super('a'); } }\n",
    "scripts/modules/FixtureClass.hx": "class FixtureClass extends Module { public function new() { super('b'); } }\n",
    "scripts/modules/loose.hx": "function onCreate() {}\n",
    "_merge/data/fixture.json": "[]",
}


def run_inventory(files: dict, checks: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
        root = Path(folder) / "pack"
        root.mkdir()
        for relative, text in files.items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, newline="\n")
        main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var inventory = VSliceImporter.chartFreeInventory({json.dumps(str(root).replace(chr(92), "/"))});
    var scripts = [for (path in inventory.scripts) haxe.io.Path.withoutDirectory(path)];
    scripts.sort(Reflect.compare);
{checks}
  }}
}}
'''
        (Path(folder) / "Main.hx").write_text(main, newline="\n")
        return subprocess.run(
            [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder, "-main", "Main", "--interp"],
            cwd=ROOT, capture_output=True, text=True,
        )


class VSliceChartFreeImportTest(unittest.TestCase):
    def test_songless_package_lists_its_content(self):
        result = run_inventory(SONGLESS, '''
    if (inventory.songFolders != 0) fail("song folders " + inventory.songFolders);
    if (!inventory.hasContent) fail("content not seen");
    if (inventory.characters.join(",") != "fixture-char") fail("characters " + inventory.characters.join(","));
    if (inventory.stages.join(",") != "fixture-stage" || inventory.noteStyles.join(",") != "fixture-style"
      || inventory.levels.join(",") != "fixture-level") fail("definitions");
    if (scripts.join(",") != "FixtureClass.hx,FixtureModule.hxc") fail("scripts " + scripts.join(","));
    if (inventory.mergeFiles != 1) fail("merge files " + inventory.mergeFiles);
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_song_folders_are_counted_and_an_empty_root_has_nothing(self):
        files = dict(SONGLESS)
        files["data/songs/fixture-song/fixture-song-metadata.json"] = "{}"
        files["data/songs/no-meta/readme.txt"] = "x"
        result = run_inventory(files, '''
    if (inventory.songFolders != 1) fail("song folders " + inventory.songFolders);
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = run_inventory({"_polymod_meta.json": "{}"}, '''
    if (inventory.hasContent || inventory.songFolders != 0 || inventory.scripts.length != 0) fail("empty root");
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
