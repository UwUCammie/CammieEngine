"""Regression coverage for display-name versus storage-key imports."""
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


class ImportStorageKeyTest(unittest.TestCase):
    def test_psych_and_codename_titles_survive_native_storage_key(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        valid = extract_method(source, "static function validModuleName")
        prepare = extract_method(source, "static function prepareImportedSongIdentity")
        fixture = f'''using StringTools;
typedef SongImport = {{ var engine:String; }};
class ImportEngine {{
 public static inline var PSYCH = 'Psych Engine';
 public static inline var CODENAME = 'Codename Engine';
 public static inline var NIGHTMARE_VISION = 'Nightmare Vision';
}}
class ImportCompat {{
{valid}
{prepare}
 static function main() {{
  var psych:SongImport = {{engine:ImportEngine.PSYCH}};
  var chart:Dynamic = {{song:'Ballistic (HQ)'}};
  prepareImportedSongIdentity(chart, psych, 'ballistic-(hq)');
  if (chart.song != 'Ballistic (HQ)' || chart.compatPreserveSongTitle != true)
   throw 'authored Psych title was replaced';
  var codename:SongImport = {{engine:ImportEngine.CODENAME}};
  var codenameChart:Dynamic = {{song:'Blammed'}};
  prepareImportedSongIdentity(codenameChart, codename, 'blammed', true);
  if (codenameChart.song != 'Blammed' || codenameChart.compatPreserveSongTitle != true)
   throw 'authored Codename title was replaced';
  var unsafeCodename:Dynamic = {{song:'../wrong'}};
  prepareImportedSongIdentity(unsafeCodename, codename, 'safe-folder', true);
  if (unsafeCodename.song != 'safe-folder'
   || Reflect.hasField(unsafeCodename,'compatPreserveSongTitle'))
   throw 'unsafe Codename title was retained';
  var generatedCodename:Dynamic = {{song:'Display From Meta'}};
  prepareImportedSongIdentity(generatedCodename, codename, 'safe-folder');
  if (generatedCodename.song != 'safe-folder'
   || Reflect.hasField(generatedCodename,'compatPreserveSongTitle'))
   throw 'generated Codename chart title became an audio key';
  var unsafe:Dynamic = {{song:'../wrong'}};
  prepareImportedSongIdentity(unsafe, psych, 'safe-folder');
  if (unsafe.song != 'safe-folder' || Reflect.hasField(unsafe,'compatPreserveSongTitle'))
   throw 'unsafe Psych title was retained';
  var legacy:SongImport = {{engine:'Modding Plus'}};
  var legacyChart:Dynamic = {{song:'Legacy Display'}};
  prepareImportedSongIdentity(legacyChart, legacy, 'legacy-folder');
  if (legacyChart.song != 'legacy-folder') throw 'legacy storage behavior changed';
  var collision:Dynamic = {{song:'Shared Name'}};
  Reflect.setField(legacy, 'ownerQualifiedCollision', true);
  prepareImportedSongIdentity(collision, legacy, 'qualified-folder');
  if (collision.song != 'Shared Name') throw 'qualified source identity changed';
 }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "ImportCompat.hx").write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", folder, "--run", "ImportCompat"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_source_folder_id_wins_over_display_name(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        helper = extract_method(source, "static function importSongFolderName")
        fixture = f'''using StringTools;
typedef SongImport = {{ var name:String; }};
class ImportCompat {{
  static function validModuleName(name:String):Bool {{
    if (name == null) return false;
    var trimmed = StringTools.trim(name);
    return trimmed != '' && trimmed != '.' && trimmed != '..'
      && trimmed.indexOf('/') < 0 && trimmed.indexOf('\\\\') < 0
      && trimmed.indexOf(':') < 0 && trimmed.indexOf('\\u0000') < 0;
  }}
{helper.replace('static function importSongFolderName', 'static function importSongFolderName')}
  static function main() {{
    var song:SongImport = {{name:'Dad Battle'}};
    Reflect.setField(song, 'sourceFolder', 'dad-battle');
    if (importSongFolderName(song) != 'dad-battle') throw 'source folder id was lost';
    var fallback:SongImport = {{name:'Pretty Song'}};
    if (importSongFolderName(fallback) != 'pretty song') throw 'legacy fallback changed';
    trace('OK');
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "ImportCompat.hx"
            fixture_path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "ImportCompat"],
                cwd=folder,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_writer_registers_storage_key_and_preserves_display_alias(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("var freeplayEntry:Dynamic = {name: targetFolder", source)
        self.assertIn("Reflect.setField(freeplayEntry, 'display', targetName)", source)
        self.assertIn("DifficultyManager.addSongSupport(targetFolder)", source)
        self.assertIn("var storageKey = importSongFolderName(songData)", source)
        self.assertIn("songTargetExists(songData.name, storageKey)", source)
        self.assertIn("Reflect.setField(songData, 'destinationFolder', ownerFolder)", source)
        self.assertIn("Reflect.setField(songData, 'ownerQualifiedCollision', true)", source)
