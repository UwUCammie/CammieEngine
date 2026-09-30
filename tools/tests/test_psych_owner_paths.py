"""Psych source Paths calls resolve through the selected import owner."""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
PSYCH = (
    ROOT
    / "tmp/psych-archive-real-import-v3/runtime/assets/imported_mods/"
    "psych-engine-fnf-psychengine-main-d942d5457b"
)


def haxe_env():
    env = dict(os.environ)
    env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
    env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
    env["PATH"] = os.pathsep.join(
        [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
    )
    return env


class PsychOwnerPathsTest(unittest.TestCase):
    def test_school_dialogue_and_stage_media_paths_are_owner_scoped(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            owner = work / "assets/imported_mods/psych-owner"
            sibling = work / "assets/imported_mods/other-owner"
            dialogue = owner / "weekend1/data/roses/rosesDialogue_en.txt"
            atlas = owner / "base_game/weekend1/images/abot/systemEyes/Animation.json"
            image = owner / "base_game/weekend1/images/phillyStreets/phillySkybox.png"
            results_image = owner / "images/results.png"
            results_xml = owner / "images/results.xml"
            results_sound = owner / "sounds/tickleFight.ogg"
            results_music = owner / "music/resultsPERFECT.ogg"
            video = owner / "weekend1/videos/intro.mp4"
            dialogue.parent.mkdir(parents=True)
            atlas.parent.mkdir(parents=True)
            image.parent.mkdir(parents=True)
            results_image.parent.mkdir(parents=True, exist_ok=True)
            results_sound.parent.mkdir(parents=True)
            results_music.parent.mkdir(parents=True)
            video.parent.mkdir(parents=True)
            sibling.mkdir(parents=True)
            sibling_image = sibling / "images/leak.png"
            sibling_image.parent.mkdir(parents=True)
            sibling_image.write_bytes(b"sibling image")
            dialogue.write_text("owner dialogue\n", encoding="utf-8")
            atlas.write_text("owner animation metadata", encoding="utf-8")
            import base64
            image.write_bytes(base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/c+sAAAAASUVORK5CYII="
            ))
            results_image.write_bytes(b"fixture image")
            results_xml.write_text(
                '<TextureAtlas imagePath="results.png"><SubTexture name="default0000" '
                'x="0" y="0" width="1" height="1" /></TextureAtlas>', encoding="utf-8"
            )
            results_sound.write_bytes(b"fixture sound")
            results_music.write_bytes(b"fixture music")
            video.write_bytes(b"fixture")
            # A similarly named base asset must not satisfy an owner Animate lookup.
            native_atlas = work / "assets/images/missing/Animation.json"
            native_atlas.parent.mkdir(parents=True)
            native_atlas.write_text("native animation metadata", encoding="utf-8")
            (work / "FNFAssets.hx").write_text(
                r'''package;
import haxe.io.Bytes;
import haxe.io.Path;
import openfl.display.BitmapData;
import openfl.media.Sound;
import sys.FileSystem;
import sys.io.File;
class FNFAssets {
 public static var lastBitmapPath:String;
 static function resolve(id:String):String return Path.normalize(id);
 public static function exists(id:String, ?ext:Dynamic):Bool return id != null && FileSystem.exists(resolve(id));
 public static function resolveCaseInsensitivePath(id:String):String return exists(id) ? resolve(id) : null;
 public static function getText(id:String):String return File.getContent(resolve(id));
 public static function getBytes(id:String):Bytes return File.getBytes(resolve(id));
 public static function getBitmapData(id:String, ?useCache:Bool = true):BitmapData {
  lastBitmapPath = resolve(id);
  return new BitmapData(1, 1, true, 0);
 }
 public static function getSound(id:String, ?useCache:Bool = true):Sound return null;
}''',
                encoding="utf-8",
            )
            (work / "CompatScriptManifest.hx").write_text(
                'package; class CompatScriptManifest { public static inline var ROOT_PREFIX = "assets/imported_mods"; }',
                encoding="utf-8",
            )
            (work / "PsychOwnerPathsProbe.hx").write_text(
                r'''package;
@:access(PsychOwnerPaths)
class PsychOwnerPathsProbe {
 static function main():Void {
  var owner = "assets/imported_mods/psych-owner";
  var paths:Dynamic = PsychOwnerPaths.create(owner, "weekend1");
  var dialogue = Reflect.callMethod(paths, Reflect.field(paths, "txt"), ["roses/rosesDialogue_en"]);
  var expected = owner + "/weekend1/data/roses/rosesDialogue_en.txt";
  if (dialogue != expected) throw "Paths.txt did not resolve the selected weekend library: " + dialogue;
  if (FNFAssets.getText(dialogue) != "owner dialogue\n")
   throw "CoolUtil's FNFAssets-backed read did not consume the resolved owner path";
  var openfl:Dynamic = PsychOwnerOpenFlAssets.create(owner);
  if (!Reflect.callMethod(openfl, Reflect.field(openfl, "exists"), [dialogue]))
   throw "OpenFL Assets.exists did not see the selected owner's physical dialogue path";

  var atlas = PsychOwnerPaths.ownerAsset(owner, "images/abot/systemEyes/Animation.json", null, "weekend1");
  var expectedAtlas = owner + "/base_game/weekend1/images/abot/systemEyes/Animation.json";
  if (atlas != expectedAtlas) throw "owner base-game library fallback failed: " + atlas;
  if (!FNFAssets.exists("assets/images/missing/Animation.json")) throw "native fallback fixture was not created";
  if (PsychOwnerPaths.ownerAsset(owner, "images/missing/Animation.json", null, "weekend1") != null)
   throw "native atlas content leaked into the selected-owner path lookup";
  var image:Dynamic = Reflect.callMethod(paths, Reflect.field(paths, "image"), ["phillyStreets/phillySkybox"]);
  if (image == null || image.width != 1 || image.height != 1)
   throw "Psych Paths.image did not return the loaded owner FlxGraphic with dimensions";
  if (FNFAssets.lastBitmapPath != expectedAtlas.substr(0, expectedAtlas.indexOf("abot/")) + "phillyStreets/phillySkybox.png")
   throw "Psych Paths.image loaded pixels outside the selected owner: " + FNFAssets.lastBitmapPath;
  var resultSound = Reflect.callMethod(paths, Reflect.field(paths, "sound"), ["tickleFight"]);
  if (resultSound != owner + "/sounds/tickleFight.ogg")
   throw "Paths.sound did not resolve results audio from the selected owner: " + resultSound;
  var resultMusic = Reflect.callMethod(paths, Reflect.field(paths, "music"), ["resultsPERFECT"]);
  if (resultMusic != owner + "/music/resultsPERFECT.ogg")
   throw "Paths.music did not resolve results music from the selected owner: " + resultMusic;
  var resultAtlas = Reflect.callMethod(paths, Reflect.field(paths, "getAtlas"), ["results"]);
  if (resultAtlas == null || FNFAssets.lastBitmapPath != owner + "/images/results.png")
   throw "Paths.getAtlas did not load a paired owner image and Sparrow metadata";
  if (!PsychOwnerAssetPath.ownerReferenceAllowed(owner, "results"))
   throw "ordinary Psych image ids should remain eligible for shared fallback";
  if (!PsychOwnerAssetPath.ownerReferenceAllowed(owner, owner + "/images/results.png"))
   throw "an explicit path to the calling owner's file should remain allowed";
  if (PsychOwnerAssetPath.ownerReferenceAllowed(owner,
   "assets/imported_mods/other-owner/images/leak.png"))
   throw "an explicit sibling import path must be blocked before shared fallback";
  if (PsychOwnerAssetPath.ownerReferenceAllowed(owner, "../other-owner/images/leak.png"))
   throw "traversal paths must be blocked before shared fallback";
  var videoPaths:Dynamic = PsychOwnerPaths.create(owner, "weekend1");
  var videoPath = Reflect.callMethod(videoPaths, Reflect.field(videoPaths, "video"), ["intro"]);
  if (videoPath != "assets/imported_mods/psych-owner/weekend1/videos/intro.mp4")
   throw "Paths.video did not return the selected owner path: " + videoPath;
  var loadFailedExplicitly = false;
  try {
   Reflect.callMethod(paths, Reflect.field(paths, "loadAnimateAtlas"), [{}, "missing"]);
  } catch (error:Dynamic) {
   loadFailedExplicitly = Std.string(error).indexOf("unavailable in selected owner") >= 0;
  }
  if (!loadFailedExplicitly) throw "missing owner Animate atlas did not fail explicitly";
 }
}''',
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    str(ROOT / ".tools/haxe/haxe"),
                    "-cp",
                    str(ROOT / "source"),
                    "-cp",
                    str(work),
                    "-lib",
                    "lime",
                    "-lib",
                    "openfl",
                    "-lib",
                    "flixel",
                    "-lib",
                    "flixel-addons",
                    "-lib",
                    "flixel-animate",
                    "-D",
                    "FLX_STANDARD_ASSETS_DIRECTORY",
                    "-D",
                    "FLX_SOUND_SYSTEM",
                    "--run",
                    "PsychOwnerPathsProbe",
                ],
                cwd=work,
                env=haxe_env(),
                text=True,
                capture_output=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        school = (PSYCH / "source/states/stages/School.hx").read_text(encoding="utf-8")
        cool_util = (ROOT / "source/CoolUtil.hx").read_text(encoding="utf-8")
        philly = (PSYCH / "source/states/stages/PhillyStreets.hx").read_text(encoding="utf-8")
        abot = (PSYCH / "source/states/stages/objects/ABotSpeaker.hx").read_text(encoding="utf-8")
        self.assertIn("Paths.txt('$songName/${songName}Dialogue_${ClientPrefs.data.language}')", school)
        self.assertIn("OpenFlAssets.exists(file)", school)
        self.assertIn("CoolUtil.coolTextFile(file)", school)
        self.assertIn("FNFAssets.getText(path)", cool_util)
        self.assertIn("Paths.image('phillyStreets/phillySkybox')", philly)
        self.assertIn("Paths.loadAnimateAtlas(eyes, 'abot/systemEyes')", abot)
        self.assertIn("FlxAnimateFrames.fromAnimate(Path.directory(animation))", (ROOT / "source/PsychOwnerPaths.hx").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
