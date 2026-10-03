"""Nightmare Vision charts keep character and stage visuals with their owner."""
from haxe_test_support import HAXE_COMMAND

import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

from tools.tests.test_psych_character_scope import extract_method


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class NightmareVisionVisualOwnerTest(unittest.TestCase):
    def test_chart_visuals_resolve_only_from_selected_nmv_owner(self):
        song = (ROOT / "source/Song.hx").read_text()
        typedef_start = song.index("typedef CharacterVisualResolution = {")
        typedef_end = song.index("\n}\n", typedef_start) + 2
        fields_start = song.index("static var gameplayFields:Array<String> = [")
        fields_end = song.index("static var registryCache", fields_start)
        methods = "\n".join(
            extract_method(song, marker)
            for marker in (
                "static function chartHasValue",
                "static function registryKey",
                "public static function resolveCharacterVisualFromData",
                "public static function resolveCharacterVisualInManifest",
                "static function isVSliceBaseCharacterReference",
                "static function readCharacterRegistryInManifest",
                "public static function characterRootForSong",
                "public static function characterOwnerEngineForSong",
                "static function safeCharacterManifestRoot",
                "public static function resolveChartData",
                "static function visualValueIsValid",
                "static function chartVisualValidity",
            )
        )

        fixture = f'''import haxe.Json;
using StringTools;

{song[typedef_start:typedef_end]}
class ImportEngine {{
  public static inline var PSYCH:String = "Psych Engine";
  public static inline var CODENAME:String = "Codename Engine";
  public static inline var MODDING_PLUS:String = "Modding Plus";
  public static inline var NIGHTMARE_VISION:String = "Nightmare Vision";
  public static inline var V_SLICE:String = "V-Slice";
}}
class CompatScriptManifest {{
  public static inline var ROOT_PREFIX:String = "assets/imported_mods";
  public static inline var FILE_NAME:String = "compatScripts.json";
  public static function parse(raw:String):Dynamic return Json.parse(raw);
  public static function selectedRoot(value:Dynamic):String return value.selectedRoot;
  public static function rootsInPrecedence(value:Dynamic):Array<Dynamic> return value.roots;
}}
class EngineCompat {{
  public static function isVSliceBaseCharacterId(value:String):Bool return value == "bf";
}}
class FNFAssets {{
  public static var files:Map<String, String> = new Map<String, String>();
  public static function exists(path:String):Bool return files.exists(path);
  public static function getText(path:String):String return files.get(path);
}}
class CoolUtil {{ public static function parseJson(raw:String):Dynamic return Json.parse(raw); }}
class NightmareVisionCharacterData {{
  public static var definitions:Map<String, Dynamic> = new Map<String, Dynamic>();
  public static var loadCalls:Array<String> = [];
  static function key(root:String, name:String):String return root + "|" + name;
  public static function load(root:String, name:String):Dynamic {{
    loadCalls.push(key(root, name));
    return definitions.get(key(root, name));
  }}
  public static function imageRoot(root:String, definition:Dynamic):String
    return definition == null ? null : Reflect.field(definition, "imageRoot");
  public static function definitionPath(root:String, name:String):String
    return definitions.exists(key(root, name)) ? root + "/data/characters/" + name + ".json" : null;
}}
class NightmareVisionStageData {{
  public static var stages:Map<String, Dynamic> = new Map<String, Dynamic>();
  public static var lookups:Array<String> = [];
  public static function getStageFile(root:String, name:String):Dynamic {{
    lookups.push(root + "|" + name);
    return stages.get(root + "|" + name);
  }}
}}
class Song {{
{song[fields_start:fields_end]}
{methods}
  static function isValidVisualValue(field:String, value:Dynamic):Bool {{
    return switch (field) {{
      case "player1" | "player2" | "gf": value == "bf" || value == "dad" || value == "gf";
      case "stage": value == "base-stage";
      case "stageID": value != null && value >= 0;
      case "arrowSkin" | "splashSkin": value is String;
      case "disableNoteRGB" | "isMoody" | "isSpooky" | "isHey" | "isCheer": value == true || value == false;
      default: false;
    }};
  }}
  static function validImportedPsychStage(name:String, folder:String):Bool return false;
  static function ownedStageEntry(folder:String, name:String):Dynamic return null;
  static function ownedCutsceneEntry(folder:String, name:String):Dynamic return null;
  static function resolveCharacterVisual(name:String):CharacterVisualResolution {{
    if (name == "bf" || name == "dad" || name == "gf") return {{
      requested:name, registryName:name, selectedRegistryName:name, likeName:name,
      implementationName:name, assetName:name,
      implementationPath:"assets/images/custom_chars/" + name + ".hscript",
      assetPath:"assets/images/custom_chars/" + name + "/char.png",
      assetRootPath:"assets/images/custom_chars/" + name,
      complete:true, diagnosticCode:"", diagnostic:""
    }};
    return resolveCharacterVisualFromData(name, null,
      function(_path:String):Bool return false);
  }}
  static function main() {{
    var owner = "assets/imported_mods/nmv-dusk-owner";
    var foreign = "assets/imported_mods/nmv-foreign-owner";
    var emptyOwner = "assets/imported_mods/nmv-empty-owner";
    var codenameOwner = "assets/imported_mods/codename-owner";
    FNFAssets.files.set("assets/data/dusk/compatScripts.json", Json.stringify({{
      selectedRoot:owner,
      roots:[{{engine:ImportEngine.NIGHTMARE_VISION, path:foreign}},
        {{engine:ImportEngine.NIGHTMARE_VISION, path:owner}}]
    }}));
    FNFAssets.files.set("assets/data/dusk-foreign/compatScripts.json", Json.stringify({{
      selectedRoot:emptyOwner,
      roots:[{{engine:ImportEngine.NIGHTMARE_VISION, path:foreign}},
        {{engine:ImportEngine.NIGHTMARE_VISION, path:emptyOwner}}]
    }}));
    FNFAssets.files.set("assets/data/codename-fixture/compatScripts.json", Json.stringify({{
      selectedRoot:codenameOwner,
      roots:[{{engine:ImportEngine.CODENAME, path:codenameOwner}}]
    }}));

    NightmareVisionCharacterData.definitions.set(owner + "|dusk", {{imageRoot:owner + "/images/characters/dusk"}});
    NightmareVisionCharacterData.definitions.set(owner + "|gf-dusk", {{imageRoot:owner + "/images/characters/gf-dusk"}});
    NightmareVisionCharacterData.definitions.set(foreign + "|dusk", {{imageRoot:foreign + "/images/characters/dusk"}});
    NightmareVisionCharacterData.definitions.set(foreign + "|foreign-only", {{imageRoot:foreign + "/images/characters/foreign-only"}});
    NightmareVisionStageData.stages.set(owner + "|dusk", {{defaultZoom:0.8}});
    NightmareVisionStageData.stages.set(foreign + "|dusk", {{defaultZoom:0.9}});

    var root = Song.characterRootForSong("dusk");
    if (root != owner || Song.characterOwnerEngineForSong("dusk") != ImportEngine.NIGHTMARE_VISION)
      throw "selected Nightmare Vision owner was not accepted";
    var authored:Dynamic = {{player1:"bf", player2:"dusk", gf:"gf-dusk", stage:"dusk"}};
    var validity = Song.chartVisualValidity("dusk", authored, [], null);
    var merged = Song.resolveChartData(authored, [],
      {{player1:"dad", player2:"dad", gf:"gf", stage:"base-stage"}}, validity, true);
    if (merged.player1 != "bf" || merged.player2 != "dusk" || merged.gf != "gf-dusk" || merged.stage != "dusk")
      throw "selected owner chart characters or stage were not retained";
    if (NightmareVisionStageData.lookups.indexOf(owner + "|dusk") < 0
        || NightmareVisionStageData.lookups.indexOf(foreign + "|dusk") >= 0)
      throw "stage validity was not scoped to the selected owner";

    var dusk = Song.resolveCharacterVisualInManifest("dusk", root, true, ImportEngine.NIGHTMARE_VISION);
    if (!dusk.complete || dusk.assetRootPath != owner + "/images/characters/dusk"
        || dusk.implementationPath != owner + "/data/characters/dusk.json")
      throw "selected owner's Dusk definition and image root did not resolve";
    var girlfriend = Song.resolveCharacterVisualInManifest("gf-dusk", root, true, ImportEngine.NIGHTMARE_VISION);
    if (!girlfriend.complete || girlfriend.assetRootPath != owner + "/images/characters/gf-dusk")
      throw "selected owner's girlfriend definition did not resolve";
    var nativeBase = Song.resolveCharacterVisualInManifest("bf", root, true, ImportEngine.NIGHTMARE_VISION);
    if (!nativeBase.complete || nativeBase.assetRootPath != "assets/images/custom_chars/bf")
      throw "missing source base actor did not fall back to the exact native base actor";

    var emptyRoot = Song.characterRootForSong("dusk-foreign");
    if (emptyRoot != emptyOwner) throw "foreign-collision fixture selected the wrong owner";
    var foreignLookupsBefore = NightmareVisionCharacterData.loadCalls.length;
    var blocked = Song.resolveCharacterVisualInManifest("dusk", emptyRoot, true,
      ImportEngine.NIGHTMARE_VISION);
    if (blocked.complete || blocked.diagnosticCode != "nightmare-vision-character-missing")
      throw "Dusk borrowed a same-named definition from another owner";
    for (call in NightmareVisionCharacterData.loadCalls.slice(foreignLookupsBefore))
      if (call.indexOf(foreign + "|") == 0)
        throw "selected owner resolution loaded a foreign package definition";
    var blockedValidity = Song.chartVisualValidity("dusk-foreign", {{player2:"dusk"}}, [], null);
    if (blockedValidity.exists("player2=dusk"))
      throw "a foreign-only character was marked valid for the selected owner";

    var callsBeforeCodename = NightmareVisionCharacterData.loadCalls.length;
    FNFAssets.files.set(codenameOwner + "/images/custom_chars/custom_chars.jsonc",
      '{{"codenameFox":{{"like":"codenameFox"}}}}');
    FNFAssets.files.set(codenameOwner + "/images/custom_chars/codenameFox.hscript", "init();");
    FNFAssets.files.set(codenameOwner + "/images/custom_chars/codenameFox/char.png", "png");
    var codename = Song.resolveCharacterVisualInManifest("codenameFox", codenameOwner, true,
      ImportEngine.CODENAME);
    if (!codename.complete || codename.assetRootPath != codenameOwner + "/images/custom_chars/codenameFox")
      throw "non-Nightmare Vision owner stopped using the generic custom character resolver";
    if (NightmareVisionCharacterData.loadCalls.length != callsBeforeCodename)
      throw "non-Nightmare Vision resolution called the Nightmare Vision helper";
  }}
}}
'''

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            work = Path(scratch)
            (work / "Song.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "--run", "Song"],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
