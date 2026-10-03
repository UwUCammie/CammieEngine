"""Tests for package-name prompt selection and safe override wiring."""
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


class ImportPackageNamePromptTest(unittest.TestCase):
    def test_only_selected_unnamed_roots_are_prompted_and_names_are_keyed_by_root(self):
        source = (ROOT / "source/ImportPackageNamePrompt.hx").read_text()
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "public static function normalizeRoot",
                "public static function rootKey",
                "public static function collectUnnamedRoots",
                "public static function validName",
                "public static function createOverrides",
            )
        )
        fixture = f'''import haxe.io.Path;
using StringTools;

typedef ImportPackageNameRequest = {{
  var root:String;
  var suggestedName:String;
}}

class ImportSettings {{
  public static function normalizeSourcePath(value:Dynamic):String {{
    if (value == null) return '';
    var normalized = StringTools.replace(StringTools.trim(Std.string(value)), '\\\\', '/');
    normalized = Path.normalize(normalized);
    while (normalized.length > 1 && StringTools.endsWith(normalized, '/'))
      normalized = normalized.substr(0, normalized.length - 1);
    return normalized;
  }}
}}

class ImportSongOwnership {{
  public static function displayNameInfo(root:String):Dynamic {{
    return root.indexOf('Authored') >= 0
      ? {{name:'Authored Mod', authored:true}}
      : {{name:Path.withoutDirectory(root), authored:false}};
  }}
}}

class ImportPackageNamePrompt {{
{methods}
}}

class ImportPackageNamePromptFixture {{
  static function main() {{
    var songs:Array<Dynamic> = [
      {{source:'/mods/Authored', willImport:true}},
      {{source:'/mods/old-pack', willImport:true}},
      {{source:'/mods/old-pack/', willImport:true}},
      {{source:'/mods/skipped', willImport:false}},
      {{source:null, willImport:true}}
    ];
    var prompts = ImportPackageNamePrompt.collectUnnamedRoots(songs);
    if (prompts.length != 1 || prompts[0].root != '/mods/old-pack'
      || prompts[0].suggestedName != 'old-pack')
      throw 'prompt selection used the wrong roots: ' + prompts;
    var values = ImportPackageNamePrompt.createOverrides(prompts, ['  D-Sides REDUX  ']);
    if (values == null || values.get('/mods/old-pack') != 'D-Sides REDUX')
      throw 'explicit labels were not trimmed and keyed by normalized source root';
    if (ImportPackageNamePrompt.createOverrides(prompts, ['  ']) != null)
      throw 'blank package name was accepted';
    if (ImportPackageNamePrompt.createOverrides(prompts, []) != null)
      throw 'missing package name was accepted';
    if (!ImportPackageNamePrompt.validName('Nightmare: Encore 2'))
      throw 'ordinary punctuation was rejected';
    if (ImportPackageNamePrompt.validName('line\\nbreak'))
      throw 'multiline package name was accepted';
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            fixture_path = Path(folder) / "ImportPackageNamePromptFixture.hx"
            fixture_path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "ImportPackageNamePromptFixture"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_import_settings_and_worker_pass_explicit_names_without_changing_storage_keys(self):
        settings = (ROOT / "source/ImportSettingsState.hx").read_text()
        workflow = (ROOT / "source/ImportWorkflow.hx").read_text()
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        start_import = extract_method(settings, "function startImport():Void")
        self.assertIn("collectUnnamedRoots(cast scanResult.songs)", start_import)
        self.assertIn("openSubState(new ImportPackageNameSubState", start_import)
        self.assertIn("beginImport(packageNames)", start_import)
        self.assertIn("beginSongImport(sourcePath, scanResult, currentImportType(), packageNames)", settings)
        self.assertIn("ModuleFunctions.importSongsFromPath(this.sourcePath, this.importType,", workflow)
        self.assertIn("scan == null ? null : scan.overlayMounts, this.packageNames", workflow)
        self.assertIn("applyPackageDisplayNames(songs, packageNames)", module)
        self.assertIn("songData.sourceModNameSource = 'user'", module)
        self.assertIn("songData.sourceModNameSource = info.authored ? 'metadata' : 'inferred'", module)
        self.assertIn("writeImportProvenance(importedSong)", module)
        self.assertIn("songData.sourceModName, songData.sourceModNameSource", module)
        scan_loop = workflow[workflow.index("for (songData in discovered)"):]
        self.assertIn("if (!sourceDuplicate)", scan_loop)
        self.assertIn("ImportSongOwnership.planDestination(existingDataFolder, storageKey", scan_loop)
        self.assertIn("Reflect.setField(songData, 'destinationFolder', storageKey)", scan_loop)
        self.assertLess(scan_loop.index("planDestination(existingDataFolder"),
                        scan_loop.index("ModuleFunctions.songTargetExists(name, storageKey)"))
        # Labels stay presentation-only: the source/destination folder helpers
        # still derive keys from chart names and authored source folder IDs.
        folder_helper = extract_method(module, "static function importSongFolderName(songData:SongImport)")
        self.assertNotIn("sourceModName", folder_helper)

    def test_legacy_module_song_import_uses_prompt_and_shared_owner_aware_importer(self):
        source = (ROOT / "source/ModuleState.hx").read_text()
        import_song = extract_method(source, "function importSong(path:String")
        import_package = extract_method(source, "function importSongPackage(basePath:String")
        self.assertIn("ImportPackageNamePrompt.collectUnnamedRoots", import_song)
        self.assertIn("new ImportPackageNameSubState(requests", import_song)
        self.assertIn("importSongPackage(basePath, packageNames)", import_song)
        self.assertIn("ModuleFunctions.importSongsFromPath(basePath, ImportSettings.MODDING_PLUS", import_package)
        self.assertNotIn("ModuleFunctions.importSong(songData)", import_song)


if __name__ == "__main__":
    unittest.main()
