"""Psych character visuals and icon metadata stay with the selected owner."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest
from tools.haxe_import_io_stubs import install_import_io_dependencies


ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "tmp"
TMP.mkdir(exist_ok=True)


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    quote = None
    escaped = False
    line_comment = False
    block_comment = False
    index = brace
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and following == "/":
                block_comment = False
                index += 1
        elif quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in ("'", '"'):
            quote = char
        elif char == "/" and following == "/":
            line_comment = True
            index += 1
        elif char == "/" and following == "*":
            block_comment = True
            index += 1
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
        index += 1
    raise AssertionError(f"unterminated method: {marker}")


class PsychCharacterScopeTest(unittest.TestCase):
    def test_selected_manifest_resolves_scoped_collision_and_keeps_native_fallback(self):
        song = (ROOT / "source/Song.hx").read_text()
        typedef_start = song.index("typedef CharacterVisualResolution = {")
        typedef_end = song.index("\n}\n", typedef_start) + 2
        methods = "\n".join(
            extract_method(song, marker)
            for marker in (
                "static function registryKey",
                "public static function resolveCharacterVisualFromData",
                "public static function resolveCharacterVisualInManifest",
                "static function isVSliceBaseCharacterReference",
                "static function safeCharacterManifestRoot",
                "public static function characterVisualRegistryEntryInManifest",
                "static function readCharacterRegistryInManifest",
            )
        )
        fixture = f'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

{song[typedef_start:typedef_end]}
class CompatScriptManifest {{
  public static inline var ROOT_PREFIX:String = 'assets/imported_mods';
}}
class ImportEngine {{ public static inline var NIGHTMARE_VISION:String = 'Nightmare Vision'; }}
class NightmareVisionCharacterData {{
  public static function load(_root:String, _name:String):Dynamic return null;
  public static function imageRoot(_root:String, _definition:Dynamic):String return null;
  public static function definitionPath(_root:String, _name:String):String return null;
}}
class FNFAssets {{
  public static function exists(path:String):Bool return FileSystem.exists(path);
  public static function getText(path:String):String return File.getContent(path);
}}
class CoolUtil {{ public static function parseJson(value:String):Dynamic return Json.parse(value); }}
class EngineCompat {{ public static function isVSliceBaseCharacterId(value:String):Bool return value == 'bf'; }}
class Song {{
{methods}
  public static var globalRegistry:Dynamic;
  public static function resolveCharacterVisual(name:String):CharacterVisualResolution
    return resolveCharacterVisualFromData(name, globalRegistry,
      function(path:String):Bool return FileSystem.exists(path));
}}
class Probe {{
  static function main() {{
    Sys.setCwd(Sys.args()[0]);
    Song.globalRegistry = Json.parse(File.getContent('assets/images/custom_chars/custom_chars.jsonc'));
    var owner = 'assets/imported_mods/psych-owner';
    var resolved = Song.resolveCharacterVisualInManifest('whitbonkers', owner, true);
    if (!resolved.complete || resolved.selectedRegistryName != 'whitbonkers'
      || resolved.assetRootPath != owner + '/images/custom_chars/whitbonkers')
      throw 'the selected Psych character did not win the colliding global registry entry';
    var entry = Song.characterVisualRegistryEntryInManifest('WHITBONKERS', owner);
    if (entry == null || entry.colors[0] != '#D70028')
      throw 'scoped health color metadata was not selected';
    var native = Song.resolveCharacterVisualInManifest('plain', owner, true);
    if (!native.complete || native.assetRootPath != 'assets/images/custom_chars/plain')
      throw 'a character absent from the Psych owner lost its native fallback';
    var incomplete = Song.resolveCharacterVisualInManifest('broken', owner, true);
    if (incomplete.complete || incomplete.diagnosticCode == '')
      throw 'an incomplete owner row impersonated the global character';
    var codename = Song.resolveCharacterVisualInManifest('plain',
      'assets/imported_mods/codename-owner', true);
    if (!codename.complete || codename.assetRootPath != 'assets/images/custom_chars/plain')
      throw 'an empty Codename base character folder hid the native visual';
    var invalid = Song.resolveCharacterVisualInManifest('whitbonkers', '../outside', true);
    if (invalid.complete || invalid.diagnosticCode != 'character-manifest-root-invalid')
      throw 'an unsafe manifest root was accepted';
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            work = Path(folder)
            install_import_io_dependencies(work)
            (work / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            owner = work / "assets/imported_mods/psych-owner/images/custom_chars"
            scoped_actor = owner / "whitbonkers"
            scoped_actor.mkdir(parents=True)
            (owner / "custom_chars.jsonc").write_text(
                '{"whitbonkers":{"like":"whitbonkers","icons":[0,1,2,3],'
                '"colors":["#D70028"]},"broken":{"like":"broken"}}'
            , newline='\n')
            (owner / "whitbonkers.hscript").write_text("function init(char) {}", newline='\n')
            (scoped_actor / "char.png").write_bytes(b"psych atlas")

            native_root = work / "assets/images/custom_chars"
            old_actor = native_root / "WhitBonkers"
            old_actor.mkdir(parents=True)
            (native_root / "custom_chars.jsonc").write_text(
                '{"WhitBonkers":{"like":"WhitBonkers","icons":[0,1,2,3],'
                '"colors":["#FFFFFF"]},"plain":{"like":"plain","icons":[0,1,2,3],'
                '"colors":["#FFFFFF"]},"broken":{"like":"broken","icons":[0,1,2,3],'
                '"colors":["#FFFFFF"]}}'
            , newline='\n')
            (native_root / "WhitBonkers.hscript").write_text("function init(char) {}", newline='\n')
            (old_actor / "char.png").write_bytes(b"fps atlas")
            plain = native_root / "plain"
            plain.mkdir()
            (native_root / "plain.hscript").write_text("function init(char) {}", newline='\n')
            (plain / "char.png").write_bytes(b"native atlas")

            codename = work / "assets/imported_mods/codename-owner/images/custom_chars"
            (codename / "plain").mkdir(parents=True)
            (codename / "custom_chars.jsonc").write_text(
                '{"plain":{"like":"plain","codenameCharacter":{"flipX":true}}}'
            , newline='\n')
            (codename / "plain.hscript").write_text("function init(char) {}", newline='\n')

            (work / "Probe.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "--run", "Probe", str(work)],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(TMP)},
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_converter_materializes_owner_media_and_both_icon_names(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        atlas_typedef_start = module.index("typedef PsychCharacterAtlasSource = {")
        atlas_typedef_end = module.index("\n}\n", atlas_typedef_start) + 2
        for fragment in (
            "importPsychCharacters(engineRoot.contentRoot,",
            "CompatScriptManifest.destinationRoot(engineRoot.root, engineRoot.engine)",
            "psychToDisAnimateChar(creation, animateFolder, assetRoot)",
            "psychToDisChar(creation, assetRoot)",
            "psychImageSources(assetsPath, imageValue",
            "psychImageReferences(image",
            "psychIconSource(assetsPath, healthIcon",
            "icons/icon-' + name + '.png",
            "icons/' + name + '.png",
        ):
            self.assertIn(fragment, module)

        methods = "\n".join(
            extract_method(module, marker)
            for marker in (
                "static function validModuleName",
                "static function psychDestinationAssetRoot",
                "static function psychImageReference",
                "static function psychImageReferences",
                "static function psychImageRoots",
                "static function psychImageSource",
                "static function psychImageSources",
                "static function psychIconSource",
                "static function existingImportChild",
                "static function findChildDirectory",
                "static function isImportFile",
                "static function ensureDirectory",
                "static function chooseVSliceRegistry",
                "static function registryHasVSliceKey",
                "static function ensurePsychCharacterRegistryEntry",
                "static public function psychToDisChar",
            )
        )
        fixture = f'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

typedef CharCreation = {{
  var path:String; var charjson:Dynamic; var ogname:String; var name:String;
  var like:String; var isPixel:Bool; var isBF:Bool; var isGF:Bool;
}}
{module[atlas_typedef_start:atlas_typedef_end]}
class CoolUtil {{
  public static function parseJson(value:String):Dynamic return Json.parse(value);
  public static function stringifyJson(value:Dynamic):String return Json.stringify(value);
}}
class FlxColor {{
  var value:Int;
  public function new(value:Int) this.value = value;
  public static function fromRGB(r:Int, g:Int, b:Int):FlxColor return new FlxColor((r << 16) | (g << 8) | b);
  public function toWebString():String return '#' + StringTools.hex(value, 6);
}}
class Song {{ public static function invalidateVisualRegistryCache():Void {{}} }}
class CompatScriptManifest {{ public static inline var ROOT_PREFIX:String = 'assets/imported_mods'; }}
class Probe {{
  static var importBackgroundMode:Bool = false;
{methods}
  static function convert(source:String, name:String, image:String, icon:String, colors:Array<Int>, destination:String):Void {{
    psychToDisChar({{path:source, charjson:{{image:image, healthicon:icon, healthbar_colors:colors,
      animations:[{{anim:'idle', name:'idle', indices:[], fps:24, loop:false, offsets:[0,0]}}],
      flip_x:false, scale:1, no_antialiasing:false, sing_duration:4}},
      ogname:name, name:name, like:name, isPixel:false, isBF:false, isGF:false}}, destination);
  }}
  static function main() {{
    var work = Sys.args()[0];
    Sys.setCwd(work);
    var source = Sys.args()[1];
    var ownerRoot = 'assets/imported_mods/psych-owner';
    var globalRegistry = Path.join(['assets/images/custom_chars/custom_chars.jsonc']);
    ensureDirectory(Path.directory(globalRegistry));
    File.saveContent(globalRegistry, '{{"WhitBonkers":{{"like":"WhitBonkers","icons":[0,1,2,3],"colors":["#FFFFFF"]}}}}');
    var preserved = File.getContent(globalRegistry);

    convert(source, 'whitbonkers', 'characters/WhittyCrazy', 'angor', [215,0,40], ownerRoot);
    convert(source, 'sharedwhit', 'characters/SharedWhitty', 'shared-icon', [1,2,3], ownerRoot);
    convert(source, 'pico-playable',
      'characters/Pico_FNF_assetss, characters/picoAnims/Pico_Intro, characters/picoAnims/Pico_Shooting',
      'pico', [183,216,85], ownerRoot);

    var scopedChars = Path.join([ownerRoot, 'images/custom_chars']);
    var actor = Path.join([scopedChars, 'whitbonkers']);
    if (File.getContent(Path.join([actor, 'char.png'])) != 'psych-atlas')
      throw 'scoped Psych image did not materialize';
    if (File.getContent(Path.join([actor, 'icons.png'])) != 'direct-icon')
      throw 'icons/<healthicon>.png was not accepted';
    if (!FileSystem.exists(Path.join([scopedChars, 'whitbonkers.hscript'])))
      throw 'scoped character implementation was not generated';
    var sharedActor = Path.join([scopedChars, 'sharedwhit']);
    if (File.getContent(Path.join([sharedActor, 'char.png'])) != 'shared-atlas'
      || File.getContent(Path.join([sharedActor, 'icons.png'])) != 'prefixed-shared-icon')
      throw 'shared/images Psych media was not resolved';
    var registry:Dynamic = Json.parse(File.getContent(Path.join([scopedChars, 'custom_chars.jsonc'])));
    if (registry.whitbonkers.colors[0] != '#D70028' || registry.sharedwhit == null)
      throw 'scoped registry or Psych healthbar color did not materialize';
    var pico = Path.join([scopedChars, 'pico-playable']);
    for (name in ['char', 'char-1', 'char-2']) {{
      if (File.getContent(Path.join([pico, name + '.png'])) != 'pico-' + name)
        throw 'multi-atlas sheet did not materialize: ' + name;
      if (!FileSystem.exists(Path.join([pico, name + '.xml'])))
        throw 'multi-atlas XML did not materialize: ' + name;
    }}
    if (File.getContent(Path.join([pico, 'icons.png'])) != 'pico-icon')
      throw 'multi-atlas Psych character health icon did not materialize';
    var picoScript = File.getContent(Path.join([scopedChars, 'pico-playable.hscript']));
    if (picoScript.indexOf("hscriptPath + 'char-1.png'") < 0
      || picoScript.indexOf("hscriptPath + 'char-2.png'") < 0
      || picoScript.indexOf('FlxAtlasFrames.combineSparrow') < 0)
      throw 'generated character script did not combine all Psych atlases';
    if (Reflect.field(registry, 'pico-playable') == null)
      throw 'multi-atlas Psych character registry entry did not materialize';
    if (File.getContent(globalRegistry) != preserved)
      throw 'scoped conversion rewrote the colliding global registry';
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            work = Path(folder)
            install_import_io_dependencies(work)
            (work / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            donor = work / "donor"
            (donor / "images/characters").mkdir(parents=True)
            (donor / "images/icons").mkdir(parents=True)
            (donor / "images/characters/WhittyCrazy.png").write_text("psych-atlas", newline='\n')
            (donor / "images/characters/WhittyCrazy.xml").write_text("<TextureAtlas/>", newline='\n')
            (donor / "images/icons/angor.png").write_text("direct-icon", newline='\n')
            (donor / "shared/images/characters").mkdir(parents=True)
            (donor / "shared/images/icons").mkdir(parents=True)
            (donor / "shared/images/characters/SharedWhitty.png").write_text("shared-atlas", newline='\n')
            (donor / "shared/images/characters/SharedWhitty.xml").write_text("<TextureAtlas/>", newline='\n')
            (donor / "shared/images/icons/icon-shared-icon.png").write_text("prefixed-shared-icon", newline='\n')
            (donor / "images/characters/picoAnims").mkdir(parents=True)
            for name in ("char", "char-1", "char-2"):
                source_name = {
                    "char": "Pico_FNF_assetss",
                    "char-1": "picoAnims/Pico_Intro",
                    "char-2": "picoAnims/Pico_Shooting",
                }[name]
                (donor / "images/characters" / (source_name + ".png")).write_text("pico-" + name, newline='\n')
                (donor / "images/characters" / (source_name + ".xml")).write_text("<TextureAtlas/>", newline='\n')
            (donor / "shared/images/icons/icon-pico.png").write_text("pico-icon", newline='\n')
            (work / "Probe.hx").write_text(fixture, newline='\n')
            (work / "PsychCharacterDanceCompat.hx").write_text(
                (ROOT / "source/PsychCharacterDanceCompat.hx").read_text(), newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "--run", "Probe", str(work), str(donor)],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(TMP)},
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_import_preserves_owner_character_json_for_position_resolution(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("preservePsychCharacterJson(Path.join([charactersRoot, entry]), scopedAssetRoot,", module)
        self.assertIn("rootInfo.shared);", module)
        methods = "\n".join(
            extract_method(module, marker)
            for marker in (
                "static function validModuleName",
                "static function isImportFile",
                "static function validImportPath",
                "static function ensureDirectory",
                "static function findChildDirectory",
                "static function psychDestinationAssetRoot",
                "static function preservePsychCharacterJson",
                "static function importPsychCharacters",
            )
        )
        position = (ROOT / "source/PsychCharacterPosition.hx").read_text()
        fixture = f'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

typedef CharCreation = {{
  var path:String; var charjson:Dynamic; var name:String;
}}
class CompatScriptManifest {{ public static inline var ROOT_PREFIX:String = 'assets/imported_mods'; }}
class Probe {{
{methods}
  static function importWorkCancelled():Bool return false;
  static function psychCharDecode(root:String, name:String):CharCreation return {{
    path:root, name:name,
    charjson:Json.parse(File.getContent(Path.join([root, 'characters', name + '.json'])))
  }};
  static function psychAnimateFolder(_root:String, _json:Dynamic):String return null;
  static function materializePsychCharacter(_creation:CharCreation, _animate:String,
    _destination:String):Void {{}}
  static function eq(actual:Array<Float>, x:Float, y:Float):Void
    if (actual[0] != x || actual[1] != y) throw 'position mismatch: ' + actual;
  static function main():Void {{
    var work = Sys.args()[0];
    Sys.setCwd(work);
    var donor = 'donor';
    var owner = 'assets/imported_mods/psych-owner';
    ensureDirectory(Path.join([donor, 'characters']));
    ensureDirectory(Path.join([donor, 'shared', 'characters']));
    ensureDirectory(Path.join([owner, 'characters']));
    File.saveContent(Path.join([donor, 'characters', 'whitbonkers.json']),
      '{{"position":[70,400],"camera_position":[-90,-400]}}');
    File.saveContent(Path.join([donor, 'characters', 'kept.json']), '{{"position":[90,90]}}');
    File.saveContent(Path.join([donor, 'shared', 'characters', 'sharedonly.json']),
      '{{"position":[30,40]}}');
    var preserved = '{{"position":[7,8]}}';
    File.saveContent(Path.join([owner, 'characters', 'kept.json']), preserved);

    importPsychCharacters(donor, owner);
    eq(PsychCharacterPosition.resolve('whitbonkers', owner), 70, 400);
    eq(PsychCharacterPosition.resolve('sharedonly', owner), 30, 40);
    eq(PsychCharacterPosition.resolve('kept', owner), 7, 8);
    if (File.getContent(Path.join([owner, 'characters', 'whitbonkers.json']))
      != File.getContent(Path.join([donor, 'characters', 'whitbonkers.json'])))
      throw 'the owner JSON was not copied byte-for-byte';
    if (File.getContent(Path.join([owner, 'characters', 'kept.json'])) != preserved)
      throw 're-import overwrote an existing owner JSON';
    if (File.getContent(Path.join([owner, 'shared', 'characters', 'sharedonly.json']))
      != File.getContent(Path.join([donor, 'shared', 'characters', 'sharedonly.json'])))
      throw 'the shared character JSON lost its original relative layout';
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            work = Path(folder)
            (work / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            (work / "PsychCharacterPosition.hx").write_text(position, newline='\n')
            (work / "FNFAssets.hx").write_text('''
class FNFAssets {
  public static function exists(path:String):Bool return sys.FileSystem.exists(path);
  public static function getText(path:String):String return sys.io.File.getContent(path);
}
''', newline='\n')
            (work / "CoolUtil.hx").write_text('''
class CoolUtil {
  public static function parseJson(source:String):Dynamic return haxe.Json.parse(source);
}
''', newline='\n')
            (work / "Probe.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "--run", "Probe", str(work)],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(TMP)},
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_gameplay_character_and_health_icon_use_active_psych_scope(self):
        song = (ROOT / "source/Song.hx").read_text()
        character = (ROOT / "source/Character.hx").read_text()
        icon = (ROOT / "source/HealthIcon.hx").read_text()
        self.assertIn("FlxG.state != PlayState.instance", song)
        self.assertIn("var engine = root.engine.toLowerCase();", song)
        self.assertIn("engine == ImportEngine.PSYCH.toLowerCase()", song)
        self.assertIn("characterRootForSong(songName, ImportEngine.PSYCH)", song)
        self.assertIn("Song.resolveCharacterVisualForCurrentSong(curCharacter)", character)
        self.assertIn("Song.characterVisualRegistryEntryForCurrentSong(lookup)", character)
        self.assertIn("Song.currentCharacterRoot()", icon)
        self.assertIn("return {path: iconPath, json: daChar, assetRoot: assetRoot};", icon)
        self.assertIn("final charPath = daData.assetRoot + daData.path + '/';", icon)

    def test_chart_normalization_keeps_the_selected_psych_registry_spelling(self):
        song = (ROOT / "source/Song.hx").read_text()
        methods = "\n".join(
            extract_method(song, marker)
            for marker in (
                "public static function storageFolder(",
                "static function validStorageKey(",
                "static function chartHasValue",
                "static function registryKey",
                "static function normalizeVisualFields",
                "static function chartVisualValidity",
                "public static function resolveChartData",
                "static function visualValueIsValid",
                "static function ownedStageEntry",
                "static function psychCharacterRootForSong",
                "static function characterRootForSong",
                "public static function currentCharacterRoot",
                "public static function currentPsychCharacterRoot",
                "static function safeCharacterManifestRoot",
                "static function readCharacterRegistryInManifest",
            )
        )
        fixture = f'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

class PlayState {{public static var instance:Dynamic;public static var SONG:Dynamic;}}
class FlxG {{public static var state:Dynamic;}}
class FNFAssets {{
  public static function exists(path:String):Bool return FileSystem.exists(path);
  public static function getText(path:String):String return File.getContent(path);
}}
class CoolUtil {{ public static function parseJson(source:String):Dynamic return Json.parse(source); }}
class NightmareVisionCharacterData {{
  public static function load(_root:String, _name:String):Dynamic return null;
  public static function imageRoot(_root:String, _definition:Dynamic):String return null;
  public static function definitionPath(_root:String, _name:String):String return null;
}}
class NightmareVisionStageData {{
  public static function getStageFile(_root:String, _name:String):Dynamic return null;
}}
class Song {{
  static var gameplayFields = ['song','notes','bpm'];
  static var visualFields = ['player1', 'player2', 'gf', 'stage', 'uiType', 'cutsceneType'];
  static var graphicFields = ['player1', 'player2', 'gf', 'stage'];
  public static var globalCharacters:Dynamic;
  static function readRegistry(path:String):Dynamic
    return path == 'assets/images/custom_chars/custom_chars' ? globalCharacters : {{}};
  static function isValidVisualValue(field:String,value:Dynamic):Bool return false;
  static function characterOwnerEngineForSong(_folder:String):String return '';
  static function validImportedPsychStage(name:String,folder:String):Bool return false;
  static function ownedCutsceneEntry(_folder:String,_name:String):Dynamic return null;
{methods}
  static function main() {{
    Sys.setCwd(Sys.args()[0]);
    globalCharacters = {{WhitBonkers:{{like:'WhitBonkers'}}, Plain:{{like:'Plain'}}}};
    var psychRoot = 'assets/imported_mods/psych-owner';
    var scopedRegistry = Path.join([psychRoot, 'images/custom_chars/custom_chars.jsonc']);
    ensureScope(scopedRegistry);
    File.saveContent(scopedRegistry, '{{"whitbonkers":{{"like":"whitbonkers"}}}}');
    File.saveContent('assets/data/ballistic/compatScripts.json',
      '{{"selectedRoot":"' + psychRoot + '","roots":[{{"engine":"Psych Engine","path":"' + psychRoot + '"}}]}}');
    var psychChart:Dynamic = {{player2:'whitbonkers'}};
    normalizeVisualFields(psychChart, 'ballistic');
    if (psychChart.player2 != 'whitbonkers')
      throw 'the global FPS spelling replaced the selected Psych character id';

    File.saveContent('assets/data/other/compatScripts.json',
      '{{"selectedRoot":"' + psychRoot + '","roots":[{{"engine":"FPS Plus","path":"' + psychRoot + '"}}]}}');
    var otherChart:Dynamic = {{player2:'whitbonkers'}};
    normalizeVisualFields(otherChart, 'other');
    if (otherChart.player2 != 'WhitBonkers')
      throw 'non-Psych charts lost normal global registry spelling';

    var fallbackChart:Dynamic = {{player2:'plain'}};
    normalizeVisualFields(fallbackChart, 'ballistic');
    if (fallbackChart.player2 != 'Plain')
      throw 'a missing scoped row lost its global native fallback';
    var codenameRoot='assets/imported_mods/codename-owner';
    var codenameRegistry=Path.join([codenameRoot,'images/custom_chars/custom_chars.jsonc']);
    ensureScope(codenameRegistry);
    File.saveContent(codenameRegistry,'{{"plain":{{"like":"plain"}}}}');
    File.saveContent('assets/data/other/compatScripts.json',
      '{{"selectedRoot":"'+codenameRoot+'","roots":[{{"engine":"Psych Engine","path":"'+psychRoot+'"}},{{"engine":"Codename Engine","path":"'+codenameRoot+'"}}]}}');
    var stageRegistry=Path.join([codenameRoot,'images/custom_stages/custom_stages.json']);
    ensureScope(stageRegistry);
    File.saveContent(stageRegistry,'{{"OwnedStage":"owned-stage"}}');
    File.saveContent(Path.join([codenameRoot,'images/custom_stages/owned-stage.hscript']),'// owned');
    var codenameChart:Dynamic={{player1:'PLAIN',gf:'PLAIN',stage:'OWNEDSTAGE'}};
    normalizeVisualFields(codenameChart,'other');
    if(codenameChart.player1!='plain' || codenameChart.gf!='plain')
      throw 'selected Codename spelling lost to another owner/global registry';
    var valid=chartVisualValidity('other',codenameChart,[],null);
    if(valid.get('player1=plain')!=true || valid.get('gf=plain')!=true)
      throw 'owned definitions disappeared during difficulty validity filtering';
    if(codenameChart.stage!='OwnedStage' || valid.get('stage=OwnedStage')!=true)
      throw 'owned stage was lost during chart normalization/difficulty filtering';
    FileSystem.deleteFile(Path.join([codenameRoot,'images/custom_stages/owned-stage.hscript']));
    var unavailable=ownedStageEntry('other','OwnedStage');
    if(unavailable==null || unavailable.unavailable!=true)
      throw 'missing owned stage script silently fell back';
    if(chartVisualValidity('other',codenameChart,[],null).get('stage=OwnedStage')!=true)
      throw 'missing owned stage lost identity before runtime could report dependency';
    File.saveContent(stageRegistry,'{{"OwnedStage":"owned-stage","HardStage":"hard-stage"}}');
    File.saveContent(Path.join([codenameRoot,'images/custom_stages/hard-stage.hscript']),'// hard');
    var lower:Dynamic={{song:'other',stage:'OwnedStage'}};
    var higher:Dynamic={{song:'other',stage:'HardStage'}};
    var stageValidity=chartVisualValidity('other',lower,[higher],higher);
    var merged=resolveChartData(lower,[higher],higher,stageValidity);
    normalizeVisualFields(merged,'other');
    if(merged.stage!='OwnedStage' || ownedStageEntry('other',merged.stage).unavailable!=true)
      throw 'missing declared stage borrowed a different difficulty implementation';
    PlayState.instance={{}};PlayState.SONG={{song:'other'}};FlxG.state=PlayState.instance;
    if(currentCharacterRoot()!=codenameRoot || currentPsychCharacterRoot()!='')
      throw 'Codename visual ownership leaked into Psych camera metadata';
    var qualified='improbable-outset--codename-engine-1234';
    var foreignRoot='assets/imported_mods/codename-foreign-owner';
    var qualifiedManifest='assets/data/'+qualified+'/compatScripts.json';
    var titleManifest='assets/data/Improbable Outset/compatScripts.json';
    ensureScope(qualifiedManifest);ensureScope(titleManifest);
    File.saveContent(qualifiedManifest,'{{"selectedRoot":"'+codenameRoot
      +'","roots":[{{"engine":"Codename Engine","path":"'+codenameRoot+'"}}]}}');
    File.saveContent(titleManifest,'{{"selectedRoot":"'+foreignRoot
      +'","roots":[{{"engine":"Codename Engine","path":"'+foreignRoot+'"}}]}}');
    PlayState.SONG={{song:'Improbable Outset',compatStorageFolder:qualified}};
    if(currentCharacterRoot()!=codenameRoot)
      throw 'presentation title selected a foreign manifest instead of the actual chart folder';
    FlxG.state={{}};
    if(currentCharacterRoot()!='')throw 'inactive PlayState leaked its owner';
  }}
  static function ensureScope(path:String):Void {{
    var parent = Path.directory(path);
    var segments = parent.split('/');
    var current = '';
    for (segment in segments) {{
      current = current == '' ? segment : current + '/' + segment;
      if (!FileSystem.exists(current)) FileSystem.createDirectory(current);
    }}
    var data = 'assets/data';
    if (!FileSystem.exists(data)) FileSystem.createDirectory(data);
    if (!FileSystem.exists(data + '/ballistic')) FileSystem.createDirectory(data + '/ballistic');
    if (!FileSystem.exists(data + '/other')) FileSystem.createDirectory(data + '/other');
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            work = Path(folder)
            (work / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            (work / "Song.hx").write_text(fixture, newline='\n')
            for module in ("ImportedStageRegistry", "CompatScriptManifest", "ImportSongOwnership", "ImportEngine"):
                (work / (module + ".hx")).write_text((ROOT / "source" / (module + ".hx")).read_text(), newline='\n')
            install_import_io_dependencies(work)
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "--run", "Song", str(work)],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(TMP)},
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    TMP.mkdir(exist_ok=True)
    unittest.main()
