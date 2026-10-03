"""Pin character-owner selection to the selected chart's storage identity."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for position in range(opening, len(source)):
        if source[position] == "{":
            depth += 1
        elif source[position] == "}":
            depth -= 1
            if depth == 0:
                return source[start : position + 1]
    raise AssertionError(marker)


class CharacterOwnerSongStorageIdentityTest(unittest.TestCase):
    def test_character_reads_codename_metadata_from_selected_chart_folder(self):
        character_source = (ROOT / "source/Character.hx").read_text()
        constructor = character_source[character_source.index("\tpublic function new("):]
        self.assertRegex(
            constructor,
            r"Song\.characterRootForSong\(Song\.storageFolder\(PlayState\.SONG\),\s*"
            r"ImportEngine\.CODENAME\)",
        )
        self.assertNotIn(
            "Song.characterRootForSong(PlayState.SONG.song, ImportEngine.CODENAME)",
            constructor,
        )

        mapped_anims = method(character_source, "\tpublic function loadMappedAnims(")
        self.assertIn("var songFolder = Song.storageFolder(PlayState.SONG);", mapped_anims)
        self.assertIn("Song.loadFromJson(curCharacter, songFolder)", mapped_anims)
        self.assertNotIn("PlayState.SONG.song.toLowerCase()", mapped_anims)

        song_source = (ROOT / "source/Song.hx").read_text()
        storage_folder = method(song_source, "\tpublic static function storageFolder(")
        valid_storage_key = method(song_source, "\tstatic function validStorageKey(")
        safe_root = method(song_source, "\tstatic function safeCharacterManifestRoot(")
        character_root = method(song_source, "\tpublic static function characterRootForSong(")
        fixture = '''
import haxe.Json;
using StringTools;

class ImportEngine {
 public static inline var CODENAME:String = "Codename Engine";
 public static inline var NIGHTMARE_VISION:String = "Nightmare Vision";
 public static inline var PSYCH:String = "Psych Engine";
 public static inline var MODDING_PLUS:String = "Modding Plus";
 public static inline var V_SLICE:String = "V-Slice";
}
class FNFAssets {
 public static var files:Map<String,String> = new Map();
 public static function exists(path:String):Bool return files.exists(path);
 public static function getText(path:String):String return files.get(path);
}
class CompatScriptManifest {
 public static inline var FILE_NAME:String = "compatScripts.json";
 public static inline var ROOT_PREFIX:String = "assets/imported_mods";
 public static function parse(raw:String):Dynamic return Json.parse(raw);
 public static function selectedRoot(manifest:Dynamic):String
  return manifest == null || manifest.selectedRoot == null ? "" : Std.string(manifest.selectedRoot);
 public static function rootsInPrecedence(manifest:Dynamic):Array<Dynamic>
  return manifest == null || manifest.roots == null ? [] : cast manifest.roots;
}
class Song {
__STORAGE_FOLDER__
__VALID_STORAGE_KEY__
__SAFE_ROOT__
__CHARACTER_ROOT__
}
class Main {
 static function check(ok:Bool,label:String):Void if(!ok)throw label;
 static function manifest(engine:String,root:String):String
  return Json.stringify({selectedRoot:root,roots:[{engine:engine,path:root}]});
 static function main():Void {
  var codenameRoot="assets/imported_mods/codename-dusk-owner";
  var nightmareRoot="assets/imported_mods/nightmare-vision-dusk-owner";
  // An unqualified legacy folder collides with the authored display name.
  FNFAssets.files.set("assets/data/dusk/compatScripts.json",
   manifest(ImportEngine.CODENAME,codenameRoot));
  FNFAssets.files.set("assets/data/dusk--nightmare-vision-7a949ff139/compatScripts.json",
   manifest(ImportEngine.NIGHTMARE_VISION,nightmareRoot));
  var selectedChart:Dynamic={song:"Dusk",compatStorageFolder:"dusk--nightmare-vision-7a949ff139"};
  check(Song.characterRootForSong(selectedChart.song,ImportEngine.CODENAME)==codenameRoot,
   "fixture must reproduce the display-name collision against the legacy Codename folder");
  var storage=Song.storageFolder(selectedChart);
  check(storage=="dusk--nightmare-vision-7a949ff139","selected storage folder must win over display title");
  check(Song.characterRootForSong(storage,ImportEngine.CODENAME)=="",
   "a Nightmare Vision chart must not read Codename orientation metadata from colliding Dusk");
  check(Song.characterRootForSong(storage,ImportEngine.NIGHTMARE_VISION)==nightmareRoot,
   "owner-qualified chart must still resolve its selected Nightmare Vision character owner");
  Sys.println("character-owner-song-storage-identity-ok");
 }
}
'''.replace("__STORAGE_FOLDER__", storage_folder).replace(
            "__VALID_STORAGE_KEY__", valid_storage_key
        ).replace("__SAFE_ROOT__", safe_root).replace("__CHARACTER_ROOT__", character_root)

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            (work / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "--run", "Main"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("character-owner-song-storage-identity-ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
