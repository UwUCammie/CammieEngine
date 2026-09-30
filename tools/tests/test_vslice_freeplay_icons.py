"""V-Slice Freeplay portraits resolve from the owning source image library."""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest

from tools.tests.test_psych_character_scope import extract_method


ROOT = Path(__file__).resolve().parents[2]


class VSliceFreeplayIconTest(unittest.TestCase):
    def test_selected_vslice_owner_reaches_menu_icon_without_changing_gameplay_default(self):
        song_source = (ROOT / "source/Song.hx").read_text()
        icon_source = (ROOT / "source/HealthIcon.hx").read_text()
        self.assertIn("Song.characterRootForSong(ownerSong, ImportEngine.V_SLICE)", icon_source)
        methods = "\n".join(extract_method(song_source, marker) for marker in (
            "public static function storageFolder(",
            "static function validStorageKey(",
            "public static function characterRootForSong(",
            "static function safeCharacterManifestRoot(",
        ))
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            temp = Path(scratch)
            owner = "assets/imported_mods/v-slice-miku-owner"
            manifest = temp / "assets/data/future-sound/compatScripts.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(json.dumps({"selectedRoot": owner,
                "roots": [{"engine": "V-Slice", "path": owner}]}))
            fixture = (
                "using StringTools;\n"
                "class PlayState { public static var SONG:Dynamic=null; }\n"
                "class FNFAssets { public static function exists(p:String):Bool return sys.FileSystem.exists(p); "
                "public static function getText(p:String):String return sys.io.File.getContent(p); }\n"
                "class ImportEngine { public static inline var V_SLICE='V-Slice'; "
                "public static inline var PSYCH='Psych'; public static inline var CODENAME='Codename Engine'; "
                "public static inline var MODDING_PLUS='Modding Plus'; }\n"
                "class CompatScriptManifest { public static inline var FILE_NAME='compatScripts.json'; "
                "public static inline var ROOT_PREFIX='assets/imported_mods'; "
                "public static function parse(s:String):Dynamic return haxe.Json.parse(s); "
                "public static function selectedRoot(m:Dynamic):String return m.selectedRoot; "
                "public static function rootsInPrecedence(m:Dynamic):Array<Dynamic> return m.roots; }\n"
                "class Song {\n" + methods + "\n}\n"
                "class Main { static function main() { "
                f"if (Song.characterRootForSong('future-sound', ImportEngine.V_SLICE) != {json.dumps(owner)}) "
                "throw 'V-Slice menu owner missing'; "
                f"if (Song.characterRootForSong('future-sound') != {json.dumps(owner)}) "
                "throw 'selected V-Slice character owner missing from default scope'; "
                "if (Song.characterRootForSong('../other', ImportEngine.V_SLICE) != '') "
                "throw 'unsafe song selected owner'; } }"
            )
            (temp / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", scratch, "-main", "Main", "--interp"],
                cwd=temp, text=True, capture_output=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_source_icon_resolution_uses_exact_character_and_owner(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        methods = "\n".join(extract_method(source, marker) for marker in (
            "static function findVSliceFreeplayIcon(",
            "static function existingImportChild(",
            "static function isImportFile(",
        ))
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            temp = Path(scratch)
            (temp / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            )
            selected = temp / "selected"
            outer = temp / "outer"
            selected_icon = selected / "images/freeplay/icons/no-gfpixel.png"
            older_icon = outer / "images/freeplay/icons/no-gfpixel.png"
            shared_icon = selected / "shared/images/freeplay/icons/M1kupixel.png"
            for icon in (selected_icon, older_icon, shared_icon):
                icon.parent.mkdir(parents=True, exist_ok=True)
                icon.write_bytes(b"source icon")
            (temp / "ImportRootScanner.hx").write_text(
                "package; typedef ImportRoot = { var root:String; var contentRoot:String; }\n"
            )
            main = (
                "import haxe.io.Path;\nimport sys.FileSystem;\nusing StringTools;\n"
                "class Main {\n" + methods + "\n"
                "static function main():Void {\n"
                f"var root:ImportRootScanner.ImportRoot = {{root:{json.dumps(str(outer))}, "
                f"contentRoot:{json.dumps(str(selected))}}};\n"
                f"if (findVSliceFreeplayIcon(root, 'no-gf') != {json.dumps(str(selected_icon))}) "
                "throw 'selected source icon lost precedence';\n"
                f"if (findVSliceFreeplayIcon(root, 'm1ku') != {json.dumps(str(shared_icon))}) "
                "throw 'shared source icon or case variant missing';\n"
                "if (findVSliceFreeplayIcon(root, '../other') != null "
                "|| findVSliceFreeplayIcon(root, 'missing') != null) "
                "throw 'invalid or absent source icon resolved';\n"
                "}\n}\n"
            )
            (temp / "Main.hx").write_text(main)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", scratch, "-main", "Main", "--interp"],
                cwd=ROOT, text=True, capture_output=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
