"""Owner-scoped Psych audio facade and compiled identity behavior."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]


def haxe_env():
    env = dict(os.environ)
    env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
    env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
    env["PATH"] = os.pathsep.join(
        [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
    )
    return env


def extract_haxe_braced(source, marker):
    start = source.index(marker)
    opening = source.index("{", start)
    if source[start:opening].rstrip().endswith(":"):
        opening = source.index("{", source.index("}", opening) + 1)
    depth = 0
    quote = None
    escaped = False
    line_comment = False
    block_comment = False
    for position in range(opening, len(source)):
        char = source[position]
        following = source[position + 1] if position + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
            continue
        if block_comment:
            if char == "*" and following == "/":
                block_comment = False
            continue
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char == "/" and following == "/":
            line_comment = True
            continue
        if char == "/" and following == "*":
            block_comment = True
            continue
        if char in {"'", '"'}:
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : position + 1], position
    raise AssertionError(f"Unclosed Haxe block: {marker}")


def extract_haxe_block(source, marker):
    block, end = extract_haxe_braced(source, marker)
    return block + source[end + 1 : source.index(");", end) + 2]


def extract_haxe_method(source, marker):
    return extract_haxe_braced(source, marker)[0]


class PsychOwnerAudioTest(unittest.TestCase):
    def test_source_sound_cache_identity_and_optional_arguments(self):
        source = (ROOT / "source/PsychOwnerPaths.hx").read_text(encoding="utf-8")
        self.assertIn("RuntimeOwnerAssetIdentity.acquire(owner, 'Psych Engine', 'package')", source)
        self.assertIn("identity.resolveAssetId(sourceId, 'SOUND')", source)
        self.assertIn("function(song:String, ?modsAllowed:Bool = true):Sound", source)
        self.assertIn("function(song:String, ?postfix:String = null", source)
        self.assertIn("cache.returnMissing(file, beepOnNull, key, path)", source)
        self.assertIn("public static function bindFileTranslation", source)

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            shutil.copyfile(ROOT / "source/PsychOwnerSoundCache.hx", work / "PsychOwnerSoundCache.hx")
            shutil.copyfile(ROOT / "source/PsychSongNameCompat.hx", work / "PsychSongNameCompat.hx")
            (work / "CompatScriptManifest.hx").write_text(
                'package; class CompatScriptManifest { public static inline var ROOT_PREFIX = "assets/imported_mods"; '
                'public static function destinationKey(path:String):String return path; }',
                encoding="utf-8",
            )
            (work / "PsychOwnerAssetPath.hx").write_text(r'''package;
import haxe.io.Path;
import sys.FileSystem;
using StringTools;
typedef PsychOwnerAssetPathResult = { var path:String; var owned:Bool; var blocked:Bool; var unavailable:Bool; }
class PsychOwnerAssetPath {
 public static function normalizeOwner(value:String):String return value;
 public static function cleanId(value:String):String {
  if (value == null) return null;
  var clean = StringTools.replace(StringTools.trim(value), "\\", "/");
  while (clean.startsWith("./")) clean = clean.substr(2);
  if (clean == "" || clean.indexOf(":") >= 0 || clean.startsWith("/") || clean.split("/").indexOf("..") >= 0) return null;
  return clean;
 }
 public static function resolve(owner:String, id:String):PsychOwnerAssetPathResult {
  var clean = cleanId(id);
  if (clean == null) return {path:null, owned:false, blocked:true, unavailable:false};
  var relative = clean.toLowerCase().startsWith("assets/") ? clean.substr(7) : clean;
  var candidate = Path.normalize(Path.join([owner, relative]));
  if (candidate != owner && candidate.startsWith(owner + "/") && FileSystem.exists(candidate))
   return {path:candidate, owned:true, blocked:false, unavailable:false};
  return {path:null, owned:false, blocked:false, unavailable:false};
 }
}''', encoding="utf-8")
            (work / "RuntimeOwnerAssetIdentity.hx").write_text(r'''package;
class RuntimeOwnerAssetIdentity {
 public static var results:Map<String, Dynamic> = new Map();
 public static var requests:Array<String> = [];
 public static function acquire(owner:String, engine:String, scope:String):RuntimeOwnerAssetIdentity return new RuntimeOwnerAssetIdentity();
 public function new() {}
 public function resolveAssetId(id:String, ?expectedType:String):Dynamic {
  requests.push(id + "|" + expectedType);
  return results.exists(id) ? results.get(id) : {state:"no-index", path:null};
 }
}''', encoding="utf-8")
            (work / "openfl/media").mkdir(parents=True)
            (work / "openfl/media/Sound.hx").write_text(r'''package openfl.media;
class Sound { public final id:String; public function new(id:String) this.id = id; }''', encoding="utf-8")
            (work / "flixel/system").mkdir(parents=True)
            (work / "flixel/system/FlxAssets.hx").write_text(r'''package flixel.system;
import openfl.media.Sound;
class FlxAssets { public static function getSound(id:String):Sound return new Sound(id); }''', encoding="utf-8")
            (work / "flixel").mkdir(parents=True, exist_ok=True)
            (work / "flixel/FlxG.hx").write_text(r'''package flixel;
class FlxLog { public function new() {} public function error(message:String):Void {} }
class FlxRandom { public function new() {} public function int(min:Int, max:Int):Int return min; }
class FlxG { public static var log:FlxLog = new FlxLog(); public static var random:FlxRandom = new FlxRandom(); }''', encoding="utf-8")
            (work / "FNFAssets.hx").write_text(r'''package;
import openfl.media.Sound;
import sys.FileSystem;
class FNFAssets {
 public static var files:Map<String, Bool> = new Map();
 public static var loads:Int = 0;
 public static function exists(path:String):Bool return (files.exists(path) && files.get(path)) || (path.indexOf(":") < 0 && FileSystem.exists(path));
 public static function getSound(path:String, ?useCache:Bool = true):Sound { loads++; return new Sound(path); }
}''', encoding="utf-8")
            (work / "Paths.hx").write_text(r'''package;
class Paths {
 public static inline var SOUND_EXT = "ogg";
 public static function file(file:String, ?type:Dynamic, ?library:String):String {
  var folder = library == null || library == "" ? "preload" : library;
  return folder + ":assets/" + folder + "/" + file;
 }
}''', encoding="utf-8")

            owner_path = work / "assets/imported_mods/audio-owner"
            relative_files = [
                "sounds/tone.ogg", "music/theme.ogg", "weekend1/sounds/legacy.ogg",
                "songs/explicit.ogg", "sounds/translated.ogg", "sounds/baseOnly.ogg",
                "sounds/random2.ogg", "compiled/shared/sounds/baseOnly.ogg",
                "compiled/songs/explicit.ogg", "songs/my-song/Inst.ogg",
                "songs/my-song/Voices.ogg", "compiled/weekend1/sounds/levelOnly.ogg",
                "compiled/songs/my-song/Inst.ogg",
                "compiled/songs/my-song/Voices-P2.ogg",
            ]
            for relative in relative_files:
                path = owner_path / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"fixture")

            audio_source = source
            proxy_blocks = "\n".join(
                extract_haxe_block(audio_source, marker)
                for marker in (
                    "Reflect.setField(proxy, 'sound',", "Reflect.setField(proxy, 'soundRandom',",
                    "Reflect.setField(proxy, 'music',", "Reflect.setField(proxy, 'inst',",
                    "Reflect.setField(proxy, 'voices',", "Reflect.setField(proxy, 'returnSound',",
                )
            )
            audio_methods = "\n".join(
                extract_haxe_method(audio_source, marker)
                for marker in (
                    "\tstatic function sound(owner:", "\tstatic function music(owner:",
                    "\tstatic function inst(owner:", "\tstatic function voices(owner:",
                    "\tstatic function audioOptions(", "\tstatic function returnSound(owner:",
                    "\tstatic function soundPath(", "\tstatic function ownerOverridePath(",
                    "\tstatic function indexedSoundResolution(", "\tstatic function sourceAudioAssetId(",
                    "public static function formatToSongPath(path:String):String",
                )
            )
            (work / "PsychOwnerPathsAudioProbe.hx").write_text(
                "package;\nimport haxe.io.Path;\nimport openfl.media.Sound;\nimport flixel.FlxG;\nusing StringTools;\n"
                + r'''class PsychOwnerPathsAudioProbe {
 static inline var SOUND:Dynamic = "sound";
 static function makePaths(owner:String, currentLevel:String, translate:String->String):Dynamic {
  var soundCache = PsychOwnerSoundCache.forOwner(owner);
  var fileTranslation = translate;
  var proxy:Dynamic = {};
'''
                + proxy_blocks
                + r'''
  return proxy;
 }
'''
                + audio_methods
                + r'''
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function id(sound:Dynamic):String return sound == null ? null : Reflect.field(sound, "id");
 static function main():Void {
  var owner = "assets/imported_mods/audio-owner";
  var paths = makePaths(owner, "weekend1", function(key:String):String {
   return key == "sounds/translatedAlias" ? "sounds/translated" : key;
  });
  var sound = Reflect.callMethod(paths, Reflect.field(paths, "sound"), ["tone"]);
  check(id(sound) == owner + "/sounds/tone.ogg", "sound did not resolve owner override to decoded Sound");
  check(Reflect.callMethod(paths, Reflect.field(paths, "sound"), ["tone"]) == sound,
   "sound did not reuse the owner decode");
  var music = Reflect.callMethod(paths, Reflect.field(paths, "music"), ["theme"]);
  check(id(music) == owner + "/music/theme.ogg", "music did not decode its owner override");
  var explicit = Reflect.callMethod(paths, Reflect.field(paths, "returnSound"), ["explicit", "songs", true, false]);
  check(id(explicit) == owner + "/songs/explicit.ogg", "returnSound did not honor its explicit mod folder");
  var legacy = Reflect.callMethod(paths, Reflect.field(paths, "sound"), ["legacy", "weekend1"]);
  check(id(legacy) == owner + "/weekend1/sounds/legacy.ogg", "legacy library-string form was not preserved");
  var compiledBase = owner + "/compiled/shared/sounds/baseOnly.ogg";
  RuntimeOwnerAssetIdentity.results.set("assets/weekend1/sounds/baseOnly.ogg", {state:"missing", path:null});
  RuntimeOwnerAssetIdentity.results.set("assets/shared/sounds/baseOnly.ogg", {state:"found", path:compiledBase});
  var baseOverride = Reflect.callMethod(paths, Reflect.field(paths, "sound"), ["baseOnly", true]);
  check(id(baseOverride) == owner + "/sounds/baseOnly.ogg", "modsAllowed=true did not prefer the direct mod override");
  var base = Reflect.callMethod(paths, Reflect.field(paths, "sound"), ["baseOnly", false]);
  check(id(base) == compiledBase, "modsAllowed=false did not resolve the selected owner's compiled base asset");
  check(RuntimeOwnerAssetIdentity.requests.indexOf("assets/shared/sounds/baseOnly.ogg|SOUND") >= 0,
   "compiled default-library lookup did not use the donor's unqualified assets ID");
  var baseFromReturn = Reflect.callMethod(paths, Reflect.field(paths, "returnSound"), ["sounds/baseOnly", false]);
  check(id(baseFromReturn) == compiledBase, "returnSound boolean did not resolve the compiled owner asset");
  var compiledExplicit = owner + "/compiled/songs/explicit.ogg";
  RuntimeOwnerAssetIdentity.results.set("assets/songs/explicit.ogg", {state:"found", path:compiledExplicit});
  var explicitBase = Reflect.callMethod(paths, Reflect.field(paths, "returnSound"), ["explicit", "songs", false, false]);
  check(id(explicitBase) == compiledExplicit, "modsAllowed=false did not bypass the explicit mod override");
  FNFAssets.files.set("shared:assets/shared/sounds/coreOnly.ogg", true);
  var nativeFallback = Reflect.callMethod(paths, Reflect.field(paths, "sound"), ["coreOnly", false]);
  check(id(nativeFallback) == "shared:assets/shared/sounds/coreOnly.ogg", "no-index native fallback was not preserved");
  var levelSound = owner + "/compiled/weekend1/sounds/levelOnly.ogg";
  RuntimeOwnerAssetIdentity.results.set("assets/weekend1/sounds/levelOnly.ogg", {state:"found", path:levelSound});
  RuntimeOwnerAssetIdentity.results.set("assets/shared/sounds/levelOnly.ogg", {state:"found", path:owner + "/compiled/shared/sounds/levelOnly.ogg"});
  var levelFirst = Reflect.callMethod(paths, Reflect.field(paths, "sound"), ["levelOnly", false]);
  check(id(levelFirst) == levelSound, "current-level owner identity did not precede shared owner identity");
  RuntimeOwnerAssetIdentity.results.set("assets/weekend1/sounds/blockedOnly.ogg", {state:"unverified", path:null});
  FNFAssets.files.set("shared:assets/shared/sounds/blockedOnly.ogg", true);
  var blockedFallback = Reflect.callMethod(paths, Reflect.field(paths, "sound"), ["blockedOnly", false]);
  check(id(blockedFallback) == "flixel/sounds/beep", "unverified owner identity fell through to a core sound");
  RuntimeOwnerAssetIdentity.results.set("assets/weekend1/sounds/missingSound.ogg", {state:"missing", path:null});
  RuntimeOwnerAssetIdentity.results.set("assets/shared/sounds/missingSound.ogg", {state:"missing", path:null});
  FNFAssets.files.set("shared:assets/shared/sounds/missingSound.ogg", true);
  var missingSound = Reflect.callMethod(paths, Reflect.field(paths, "sound"), ["missingSound"]);
  check(id(missingSound) == "flixel/sounds/beep",
   "claimed-but-missing compiled Sound threw or borrowed a core Sound instead of beeping");
  var translated = Reflect.callMethod(paths, Reflect.field(paths, "sound"), ["translatedAlias"]);
  check(id(translated) == owner + "/sounds/translated.ogg", "translation did not run before extension lookup");
  var random = Reflect.callMethod(paths, Reflect.field(paths, "soundRandom"), ["random", 2, 4]);
  check(id(random) == owner + "/sounds/random2.ogg", "soundRandom did not return a decoded Sound");
  var compiledInst = owner + "/compiled/songs/my-song/Inst.ogg";
  RuntimeOwnerAssetIdentity.results.set("assets/songs/my-song/Inst.ogg", {state:"found", path:compiledInst});
  var inst = Reflect.callMethod(paths, Reflect.field(paths, "inst"), ["My Song", false]);
  check(id(inst) == compiledInst, "inst did not format the song name and resolve its compiled identity");
  var compiledVoices = owner + "/compiled/songs/my-song/Voices-P2.ogg";
  RuntimeOwnerAssetIdentity.results.set("assets/songs/my-song/Voices-P2.ogg", {state:"found", path:compiledVoices});
  var voices = Reflect.callMethod(paths, Reflect.field(paths, "voices"), ["My Song", "P2", false]);
  check(id(voices) == compiledVoices, "voices did not preserve postfix and resolve its compiled identity");
  RuntimeOwnerAssetIdentity.results.set("assets/songs/missing-song/Voices.ogg", {state:"missing", path:null});
  var quietVoices = Reflect.callMethod(paths, Reflect.field(paths, "voices"), ["Missing Song", null, false]);
  check(quietVoices == null, "claimed-but-missing voices did not preserve beepOnNull=false");
  RuntimeOwnerAssetIdentity.results.set("assets/songs/missingReturn.ogg", {state:"missing", path:null});
  var quietMissing = Reflect.callMethod(paths, Reflect.field(paths, "returnSound"), ["missingReturn", "songs", false, false]);
  check(quietMissing == null, "claimed-but-missing returnSound did not preserve beepOnNull=false");
  var beep = Reflect.callMethod(paths, Reflect.field(paths, "returnSound"), ["sounds/missing"]);
  check(id(beep) == "flixel/sounds/beep", "missing returnSound did not return donor beep");
 }
}''',
                encoding="utf-8",
            )
            (work / "PsychOwnerSoundCacheProbe.hx").write_text(r'''package;
import openfl.media.Sound;
class PsychOwnerSoundCacheProbe {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  FNFAssets.files.set("owner/a.ogg", true);
  FNFAssets.files.set("other/a.ogg", true);
  var owner = PsychOwnerSoundCache.forOwner("owner");
  check(owner.dumpExclusions.indexOf("assets/shared/music/freakyMenu.ogg") >= 0,
   "donor shared menu music exclusion did not use the target sound extension");
  var first:Sound = owner.returnSound("owner/a.ogg", false);
  var same = owner.returnSound("owner/a.ogg", false);
  check(first == same && FNFAssets.loads == 1, "owner did not reuse decoded Sound");
  check(owner.localTrackedAssets.length == 2, "owner-local use tracking failed");
  owner.clearStoredMemory();
  check(owner.currentTrackedSounds.exists("owner/a.ogg") && owner.localTrackedAssets.length == 0,
   "first memory clear did not keep current-state Sound");
  owner.clearStoredMemory();
  check(!owner.currentTrackedSounds.exists("owner/a.ogg"), "stale Sound reference was retained");
  var quietMissing = owner.returnMissing("owner/missing.ogg", false);
  check(quietMissing == null, "quiet missing Sound did not return null");
  var missing = owner.returnMissing("owner/missing.ogg", true, "sounds/missing", "shared");
  check(missing != null && missing.id == "flixel/sounds/beep", "missing Sound did not use donor beep");
  var other = PsychOwnerSoundCache.forOwner("other");
  var distinct = other.returnSound("other/a.ogg", false);
  check(distinct != first && distinct.id == "other/a.ogg" && FNFAssets.loads == 2,
   "separate owners shared a decoded Sound");
  PsychOwnerSoundCache.releaseOwner("owner");
  check(owner.isReleased() && !other.isReleased(), "owner release crossed cache boundaries");
  var rejected = false;
  try owner.returnSound("owner/a.ogg", false) catch (_:Dynamic) rejected = true;
  check(rejected, "released cache remained usable through old facade");
  var fresh = PsychOwnerSoundCache.forOwner("owner");
  var reloaded = fresh.returnSound("owner/a.ogg", false);
  check(reloaded != first && FNFAssets.loads == 3, "new owner runtime did not decode after release");
  check(other.returnSound("other/a.ogg", false) == distinct && FNFAssets.loads == 3,
   "releasing one owner evicted another owner's cache");
 }
}''', encoding="utf-8")
            (work / "DonorOptionalProbe.hx").write_text(r'''package;
class DonorOptionalProbe {
 static function returnSound(key:String, ?path:String, ?modsAllowed:Bool=true, ?beepOnNull:Bool=true):String
  return Std.string(path) + ":" + modsAllowed + ":" + beepOnNull;
 static function sound(key:String, ?modsAllowed:Bool=true):String return returnSound('sounds/$key', modsAllowed);
 static function music(key:String, ?modsAllowed:Bool=true):String return returnSound('music/$key', modsAllowed);
 static function inst(song:String, ?modsAllowed:Bool=true):String return returnSound(song + "/Inst", "songs", modsAllowed);
 static function voices(song:String, postfix:String = null, ?modsAllowed:Bool=true):String {
  var songKey = song + "/Voices";
  if (postfix != null) songKey += "-" + postfix;
  return returnSound(songKey, "songs", modsAllowed, false);
 }
 static function main():Void {
  if (sound("click", false) != "null:false:true") throw "sound bool shifted optional args";
  if (music("menu", false) != "null:false:true") throw "music bool shifted optional args";
  if (inst("song", false) != "songs:false:true") throw "inst bool shifted optional args";
  if (voices("song", "Player", false) != "songs:false:false") throw "voices optional args shifted";
  if (returnSound("song/Inst", "songs", false, false) != "songs:false:false") throw "explicit folder args shifted";
 }
}''', encoding="utf-8")

            for main in ("PsychOwnerSoundCacheProbe", "PsychOwnerPathsAudioProbe", "DonorOptionalProbe"):
                result = subprocess.run(
                    [*HAXE_COMMAND, "-cp", str(work), "--run", main],
                    cwd=work, env=haxe_env(), text=True, capture_output=True, timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
