"""V-Slice character IDs resolve through the selected package owner."""
from pathlib import Path
import json
import os
import subprocess
import tempfile
import unittest

from tools.tests.test_psych_character_scope import extract_method


ROOT = Path(__file__).resolve().parents[2]


class VSliceCharacterOwnerScopeTest(unittest.TestCase):
    def test_gameplay_prefers_selected_vslice_owner_and_blocks_foreign_global_rows(self):
        song = (ROOT / "source/Song.hx").read_text()
        methods = "\n".join(
            extract_method(song, marker)
            for marker in (
                "static function registryKey",
                "public static function resolveCharacterVisualFromData",
                "public static function resolveCharacterVisualInManifest",
                "static function isVSliceBaseCharacterReference",
                "static function safeCharacterManifestRoot",
                "static function readCharacterRegistryInManifest",
                "static function validStorageKey",
                "public static function storageFolder",
                "public static function characterRootForSong",
                "public static function currentCharacterRoot",
                "public static function characterOwnerEngineForSong",
                "public static function resolveCharacterVisualForCurrentSong",
            )
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            work = Path(scratch)
            owner = "assets/imported_mods/vslice-selected-owner"
            owner_chars = work / owner / "images/custom_chars"
            global_chars = work / "assets/images/custom_chars"
            manifest = work / "assets/data/test-song/compatScripts.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(json.dumps({
                "selectedRoot": owner,
                "roots": [{"engine": "V-Slice", "path": owner}],
            }))

            (owner_chars / "our-harmony").mkdir(parents=True)
            (owner_chars / "our-harmony/char.png").write_bytes(b"selected atlas")
            (owner_chars / "our-harmony.hscript").write_text("function init(char) {}")
            (owner_chars / "custom_chars.jsonc").write_text(
                '{"our-harmony":{"like":"our-harmony"}}'
            )

            for name in ("our-harmony", "private-likely", "bf"):
                (global_chars / name).mkdir(parents=True)
                (global_chars / name / "char.png").write_bytes(b"global atlas")
                (global_chars / (name + ".hscript")).write_text("function init(char) {}")
            (global_chars / "custom_chars.jsonc").write_text(
                '{"our-harmony":{"like":"our-harmony"},'
                '"private-likely":{"like":"private-likely"},'
                '"bf":{"like":"bf"}}'
            )

            fixture = '''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

typedef CharacterVisualResolution = {
  var requested:String; var registryName:String; var selectedRegistryName:String;
  var likeName:String; var implementationName:String; var assetName:String;
  var implementationPath:String; var assetPath:String; var assetRootPath:String;
  var complete:Bool; var diagnosticCode:String; var diagnostic:String;
}
class ImportEngine {
  public static inline var V_SLICE="V-Slice"; public static inline var PSYCH="Psych Engine";
  public static inline var CODENAME="Codename Engine"; public static inline var MODDING_PLUS="Modding Plus";
}
class CompatScriptManifest {
  public static inline var FILE_NAME="compatScripts.json";
  public static inline var ROOT_PREFIX="assets/imported_mods";
  public static function parse(source:String):Dynamic return Json.parse(source);
  public static function selectedRoot(value:Dynamic):String return value.selectedRoot;
  public static function rootsInPrecedence(value:Dynamic):Array<Dynamic> return value.roots;
}
class EngineCompat {
  public static function isVSliceBaseCharacterId(value:String):Bool
    return ["bf", "boyfriend", "dad", "daddy", "gf", "girlfriend"].indexOf(value.toLowerCase()) >= 0;
}
class PlayState { public static var instance:Dynamic; public static var SONG:Dynamic; }
class FlxG { public static var state:Dynamic; }
class FNFAssets {
  public static function exists(path:String):Bool return FileSystem.exists(path);
  public static function getText(path:String):String return File.getContent(path);
}
class CoolUtil { public static function parseJson(value:String):Dynamic return Json.parse(value); }
class Song {
  static var globalRegistry:Dynamic;
  static function readRegistry(path:String):Dynamic return globalRegistry;
  static function resolveCharacterVisual(name:String):CharacterVisualResolution
    return resolveCharacterVisualFromData(name, globalRegistry,
      function(path:String):Bool return FileSystem.exists(path));
''' + methods + '''
  static function main() {
    Sys.setCwd(Sys.args()[0]);
    globalRegistry = Json.parse(File.getContent("assets/images/custom_chars/custom_chars.jsonc"));
    var state = {};
    PlayState.instance = state;
    PlayState.SONG = {song:"test-song"};
    FlxG.state = state;
    var selected = resolveCharacterVisualForCurrentSong("our-harmony");
    if (!selected.complete || selected.assetRootPath != "assets/imported_mods/vslice-selected-owner/images/custom_chars/our-harmony")
      throw "gameplay did not prefer the selected V-Slice owner";
    var collision = resolveCharacterVisualForCurrentSong("private-likely");
    if (collision.complete || collision.diagnosticCode != "character-registry-entry-missing")
      throw "owner-missing ID borrowed a global custom character";
    var native = resolveCharacterVisualForCurrentSong("bf");
    if (!native.complete || native.assetRootPath != "assets/images/custom_chars/bf")
      throw "exact destination-native base character fallback failed";
    if (currentCharacterRoot() != "assets/imported_mods/vslice-selected-owner")
      throw "V-Slice selected owner was not eligible for gameplay resolution";
  }
}
'''
            (work / "Song.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(work), "--run", "Song", str(work)],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
