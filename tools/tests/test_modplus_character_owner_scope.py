"""Selected Modding Plus characters remain tied to their importing owner."""

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

from tools.tests.test_psych_character_scope import extract_method


ROOT = Path(__file__).resolve().parents[2]
DONOR_ROOT = Path(
    "/run/media/cammie/External Storage/FNF-Example-Mods/modding-plus/vsfreddy_1_9_5"
)
HAXE = ROOT / ".tools/haxe/haxe"


def _importer_fixture(module_source: str, song_source: str) -> str:
    module_markers = (
        "static function importPathKey",
        "static function importPathIsWithin",
        "static function validImportEntryName",
        "static function existingImportChild",
        "static function ensureDirectory",
        "static function findChildDirectory",
        "static function mergeTreeNonOverwriting",
        "static function normalizedImportFileName",
        "static function findImportFile",
        "static function isImportFile",
        "static function validModuleName",
        "static function readImportJson",
        "static function copyImportFileNonOverwriting",
        "static function writeImportContentNonOverwriting",
        "static function modPlusCharactersUsedByImportedSongs",
        "static function mergeModPlusCharacterAssets",
    )
    methods = "\n".join(
        extract_method(module_source, marker) for marker in module_markers
    )
    song_methods = "\n".join(
        extract_method(song_source, marker)
        for marker in (
            "static function registryKey",
            "public static function resolveCharacterVisualFromData",
            "public static function resolveCharacterVisualInManifest",
            "static function isVSliceBaseCharacterReference",
            "static function safeCharacterManifestRoot",
            "static function readCharacterRegistryInManifest",
            "public static function characterVisualRegistryEntryInManifest",
            "public static function characterRootForSong",
        )
    )
    typedef_start = song_source.index("typedef CharacterVisualResolution = {")
    typedef_end = song_source.index("\n}\n", typedef_start) + 2
    return f'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

{song_source[typedef_start:typedef_end]}
typedef SongImportSource = {{ var song:String; var data:String; var destination:String; }};
typedef ImportAssetMergeResult = {{ var copied:Int; var skipped:Int; var failed:Int; @:optional var errors:Array<String>; }};
class ImportSettings {{
  public static function normalizeSourcePath(value:Dynamic):String
    return Path.normalize(StringTools.replace(StringTools.trim(Std.string(value)), '\\\\', '/'));
}}
class ImportEngine {{
  public static inline var PSYCH:String = 'Psych Engine';
  public static inline var CODENAME:String = 'Codename Engine';
  public static inline var MODDING_PLUS:String = 'Modding Plus';
  public static inline var V_SLICE:String = 'V-Slice';
}}
class EngineCompat {{ public static function isVSliceBaseCharacterId(value:String):Bool return value == 'bf'; }}
class CompatScriptManifest {{
  public static inline var ROOT_PREFIX:String = 'assets/imported_mods';
  public static inline var FILE_NAME:String = 'compatScripts.json';
  public static function destinationRoot(sourceRoot:String, engine:String):String
    return ROOT_PREFIX + '/' + Path.withoutDirectory(sourceRoot);
  public static function parse(raw:String):Dynamic return Json.parse(raw);
  public static function selectedRoot(manifest:Dynamic):String return manifest.selectedRoot;
  public static function rootsInPrecedence(manifest:Dynamic):Array<Dynamic> return manifest.roots;
  public static function create(sourceRoot:String, engine:String):Dynamic {{
    var path = destinationRoot(sourceRoot, engine);
    return {{version:1, selectedRoot:path, roots:[{{engine:engine,path:path}}]}};
  }}
  public static function stringify(manifest:Dynamic):String return Json.stringify(manifest);
}}
class FNFAssets {{
  public static function exists(path:String):Bool return FileSystem.exists(path);
  public static function getText(path:String):String return File.getContent(path);
}}
class CoolUtil {{
  public static function parseJson(raw:String):Dynamic return Json.parse(raw);
  public static function stringifyJson(value:Dynamic):String return Json.stringify(value);
}}
class ModuleFunctions {{
  static function importWorkCancelled():Bool return false;
  static function reportImportProgress(phase:String, current:String, completed:Int = 0,
      total:Int = 0, copied:Int = 0, skipped:Int = 0, failed:Int = 0, work:Int = 0):Void {{}}
{methods}
  public static function usedCharacters(root:String, names:Map<String, Bool>,
      sources:Map<String, SongImportSource>):Array<String>
    return modPlusCharactersUsedByImportedSongs(root, names, sources);
  public static function mergeCharacters(source:String, owner:String, ids:Array<String>,
      result:ImportAssetMergeResult):Void
    mergeModPlusCharacterAssets(source, owner, ids, result);
}}
class Song {{
{song_methods}
  public static var globalRegistry:Dynamic;
  public static function resolveCharacterVisual(name:String):CharacterVisualResolution
    return resolveCharacterVisualFromData(name, globalRegistry,
      function(path:String):Bool return FileSystem.exists(path));
}}
class Main {{
  static function fail(message:String):Void throw message;
  static function has(values:Array<String>, wanted:String):Bool {{
    for (value in values) if (value.toLowerCase() == wanted.toLowerCase()) return true;
    return false;
  }}
  static function main():Void {{
    var donor = Sys.args()[0];
    var alternate = Sys.args()[1];
    var donorAssets = Path.join([donor, 'assets']);
    var names:Map<String, Bool> = new Map<String, Bool>();
    var sources:Map<String, SongImportSource> = new Map<String, SongImportSource>();
    for (song in ['let-us-in', 'slaughter']) {{
      names.set(song, true);
      sources.set(song, {{song:'', data:Path.join([donorAssets, 'data', song]), destination:song}});
    }}
    var ids = ModuleFunctions.usedCharacters(donorAssets, names, sources);
    for (character in ['bf-dark', 'gf-dark', 'Freddy', 'Freddy-angry'])
      if (!has(ids, character)) fail('selected charts did not retain ' + character);
    if (has(ids, 'Golden-freddy')) fail('unimported Fired chart leaked a character');

    var ownerA = CompatScriptManifest.destinationRoot(donor, ImportEngine.MODDING_PLUS);
    var ownerB = CompatScriptManifest.destinationRoot(alternate, ImportEngine.MODDING_PLUS);
    if (ownerA == ownerB) fail('distinct donor roots share an owner namespace');
    var merge:ImportAssetMergeResult = {{copied:0, skipped:0, failed:0, errors:[]}};
    ModuleFunctions.mergeCharacters(Path.join([donorAssets, 'images', 'custom_chars']), ownerA, ids, merge);
    ModuleFunctions.mergeCharacters(Path.join([alternate, 'images', 'custom_chars']), ownerB,
      ['bf-dark', 'gf-dark'], merge);
    // A changed donor may repair missing files, but never replaces this owner's
    // existing atlas/script bytes or merges the second donor into the first.
    ModuleFunctions.mergeCharacters(Path.join([alternate, 'images', 'custom_chars']), ownerA,
      ['bf-dark', 'gf-dark'], merge);
    if (merge.failed != 0) fail('character merge errors=' + merge.failed);

    FileSystem.createDirectory('assets/images/custom_chars/bf-dark');
    FileSystem.createDirectory('assets/images/custom_chars/gf-dark');
    File.saveContent('assets/images/custom_chars/bf-dark/char.png', 'foreign global BF');
    File.saveContent('assets/images/custom_chars/gf-dark/char.png', 'foreign global GF');
    Song.globalRegistry = Json.parse('{{"bf-dark":{{"like":"bf","icons":[0,1,2],"colors":["#FFFFFF"]}},'
      + '"gf-dark":{{"like":"gf","icons":[0,0,1],"colors":["#FFFFFF"]}}}}');
    FileSystem.createDirectory('assets/data/let-us-in');
    FileSystem.createDirectory('assets/data/slaughter');
    File.saveContent('assets/data/let-us-in/compatScripts.json',
      CompatScriptManifest.stringify(CompatScriptManifest.create(donor, ImportEngine.MODDING_PLUS)));
    File.saveContent('assets/data/slaughter/compatScripts.json',
      CompatScriptManifest.stringify(CompatScriptManifest.create(alternate, ImportEngine.MODDING_PLUS)));

    var selectedA = Song.characterRootForSong('let-us-in');
    var selectedB = Song.characterRootForSong('slaughter');
    if (selectedA != ownerA || selectedB != ownerB)
      fail('song did not select its own MPlus character root: ' + selectedA + ' / ' + selectedB);
    if (Song.characterRootForSong('let-us-in', ImportEngine.PSYCH) != '')
      fail('MPlus root leaked into explicit Psych resolution');
    var resolvedA = Song.resolveCharacterVisualInManifest('bf-dark', selectedA, true);
    var resolvedB = Song.resolveCharacterVisualInManifest('bf-dark', selectedB, true);
    if (!resolvedA.complete || resolvedA.assetRootPath != ownerA + '/images/custom_chars/bf-dark'
        || resolvedA.implementationName != 'bf') fail('owner A BF alias/atlas did not resolve');
    if (!resolvedB.complete || resolvedB.assetRootPath != ownerB + '/images/custom_chars/bf-dark'
        || resolvedB.implementationName != 'bf') fail('owner B BF alias/atlas did not resolve');
    if (resolvedA.assetRootPath == resolvedB.assetRootPath)
      fail('same-id character owners collapsed to one atlas path');
    var bfPng = ownerB + '/images/custom_chars/bf-dark/char.png';
    var bfXml = ownerB + '/images/custom_chars/bf-dark/char.xml';
    var savedPng = File.getBytes(bfPng);
    var savedXml = File.getBytes(bfXml);
    FileSystem.deleteFile(bfPng);
    FileSystem.deleteFile(bfXml);
    FileSystem.deleteDirectory(ownerB + '/images/custom_chars/bf-dark');
    var missingOwner = Song.resolveCharacterVisualInManifest('bf-dark', ownerB, true);
    if (missingOwner.complete || missingOwner.diagnosticCode != 'character-asset-missing')
      fail('a foreign global atlas hid a missing owner atlas');
    FileSystem.createDirectory(ownerB + '/images/custom_chars/bf-dark');
    File.saveBytes(bfPng, savedPng);
    File.saveBytes(bfXml, savedXml);
    trace('IDS=' + ids.join(',') + '|A=' + ownerA + '|B=' + ownerB);
  }}
}}
'''


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(
    DONOR_ROOT.is_dir() and HAXE.is_file(),
    "mounted Modding Plus donor or portable Haxe is unavailable",
)
class ModPlusCharacterOwnerScopeTest(unittest.TestCase):
    def test_importer_and_runtime_keep_same_id_character_owners_separate(self):
        module_source = (ROOT / "source/ModuleFunctions.hx").read_text()
        song_source = (ROOT / "source/Song.hx").read_text()
        self.assertIn(
            "modPlusCharactersUsedByImportedSongs(characterChartRoot, importedNames, importedSources)",
            module_source,
        )
        self.assertIn("mergeModPlusCharacterAssets(characterRoot, destination", module_source)

        donor_chars = DONOR_ROOT / "assets/images/custom_chars"
        donor_assets = DONOR_ROOT / "assets"
        self.assertTrue((donor_chars / "bf-dark/char.png").is_file())
        self.assertTrue((donor_chars / "gf-dark/char.png").is_file())
        self.assertTrue((donor_chars / "bf.hscript").is_file())
        self.assertTrue((donor_chars / "gf.hscript").is_file())

        with tempfile.TemporaryDirectory(prefix="mplus-char-owner-", dir=ROOT / "tmp") as folder:
            work = Path(folder)
            (work / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            )
            alternate = work / "alternate-donor"
            alternate_chars = alternate / "images/custom_chars"
            (alternate_chars / "bf-dark").mkdir(parents=True)
            (alternate_chars / "gf-dark").mkdir(parents=True)
            (alternate_chars / "bf-dark/char.png").write_bytes(b"alternate BF atlas")
            (alternate_chars / "gf-dark/char.png").write_bytes(b"alternate GF atlas")
            (alternate_chars / "bf-dark/char.xml").write_text(
                '<TextureAtlas><SubTexture name="alternate BF idle0000"/></TextureAtlas>'
            )
            (alternate_chars / "gf-dark/char.xml").write_text(
                '<TextureAtlas><SubTexture name="alternate GF dance0000"/></TextureAtlas>'
            )
            (alternate_chars / "custom_chars.jsonc").write_text(
                json.dumps(
                    {
                        "bf-dark": {"like": "bf", "icons": [0, 1, 2], "colors": ["#112233"]},
                        "gf-dark": {"like": "gf", "icons": [0, 0, 1], "colors": ["#445566"]},
                    }
                )
            )
            (alternate_chars / "bf.hscript").write_text("// alternate bf implementation\n")
            (alternate_chars / "gf.hscript").write_text("// alternate gf implementation\n")

            global_chars = work / "assets/images/custom_chars"
            (global_chars / "bf-dark").mkdir(parents=True)
            (global_chars / "gf-dark").mkdir(parents=True)
            (global_chars / "bf-dark/char.png").write_bytes(b"foreign global BF")
            (global_chars / "gf-dark/char.png").write_bytes(b"foreign global GF")
            global_before = {
                path: _hash(global_chars / path)
                for path in (
                    "bf-dark/char.png",
                    "gf-dark/char.png",
                )
            }

            fixture = _importer_fixture(module_source, song_source)
            (work / "Main.hx").write_text(fixture)
            (work / "CompatScriptManifest.hx").write_text(
                (ROOT / "source/CompatScriptManifest.hx").read_text()
            )
            result = subprocess.run(
                [
                    str(HAXE),
                    "-cp",
                    str(work),
                    "--run",
                    "Main",
                    str(DONOR_ROOT),
                    str(alternate),
                ],
                cwd=work,
                capture_output=True,
                text=True,
                timeout=60,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertRegex(output, r"IDS=.*bf-dark.*gf-dark.*\|A=assets/imported_mods/.*\|B=assets/imported_mods/")

            owner_a = work / "assets/imported_mods" / DONOR_ROOT.name
            owner_b = work / "assets/imported_mods" / alternate.name
            for character in ("bf-dark", "gf-dark"):
                self.assertEqual(_hash(owner_a / "images/custom_chars" / character / "char.png"),
                                 _hash(donor_chars / character / "char.png"))
                self.assertEqual(_hash(owner_a / "images/custom_chars" / character / "char.xml"),
                                 _hash(donor_chars / character / "char.xml"))
                self.assertEqual(_hash(owner_b / "images/custom_chars" / character / "char.png"),
                                 _hash(alternate_chars / character / "char.png"))
                self.assertEqual(_hash(owner_b / "images/custom_chars" / character / "char.xml"),
                                 _hash(alternate_chars / character / "char.xml"))
            for implementation in ("bf", "gf"):
                self.assertEqual(_hash(owner_a / "images/custom_chars" / f"{implementation}.hscript"),
                                 _hash(donor_chars / f"{implementation}.hscript"))
                self.assertEqual(_hash(owner_b / "images/custom_chars" / f"{implementation}.hscript"),
                                 _hash(alternate_chars / f"{implementation}.hscript"))
            owner_a_registry = json.loads(
                (owner_a / "images/custom_chars/custom_chars.jsonc").read_text()
            )
            self.assertEqual(owner_a_registry["bf-dark"], json.loads(
                (donor_chars / "custom_chars.jsonc").read_text())["bf-dark"])
            self.assertNotIn("Golden-freddy", owner_a_registry)
            self.assertEqual(global_before, {
                path: _hash(global_chars / path) for path in global_before
            })

            donor_xml = ET.parse(donor_chars / "bf-dark/char.xml").getroot()
            imported_xml = ET.parse(owner_a / "images/custom_chars/bf-dark/char.xml").getroot()
            frame_names = lambda root: sorted(node.attrib["name"] for node in root if "name" in node.attrib)
            self.assertEqual(frame_names(imported_xml), frame_names(donor_xml))
            self.assertGreater(len(frame_names(imported_xml)), 1)


if __name__ == "__main__":
    unittest.main()
