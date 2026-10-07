"""Runtime route decisions for the receipt-bound Psych-family media policy."""
from haxe_test_support import HAXE_COMMAND, TEST_TMP

from pathlib import Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''import PsychAssetProfile.PsychAssetProfileMappedFile;
import PsychAssetProfile.PsychAssetProfileCandidate;
import SourceMappedAssetPublisher.SourceMappedAssetDecision;
import SourceMappedAssetPublisher.SourceMappedAssetPolicy;
using StringTools;

class Main {
  static function check(value:Bool, message:String):Void if (!value) throw message;

  static function event(path:String, ?library:String = "", ?type:String = "",
      ?assetId:String, assetIdOverride:Bool = false, ?embed:String = "false"):PsychAssetProfileMappedFile {
    var relative = path.startsWith("assets/") ? path.substr("assets/".length) : null;
    return {
      sourcePath:"source-file", sourceRelative:path, mappedPath:path,
      ownerRelative:relative, candidateOrder:0, size:1, sha256:StringTools.lpad("0", "0", 64),
      type:type, embed:embed, library:library,
      assetId:assetId == null ? path : assetId, assetIdOverride:assetIdOverride
    };
  }

  static function checkDecision(policy:SourceMappedAssetPolicy, item:PsychAssetProfileMappedFile,
      state:String, owner:String, label:String):Void {
    var decision = policy.classify(item);
    check(decision.state == state, label + " state: " + decision.state);
    if (owner != null) check(decision.ownerRelative == owner,
      label + " owner: " + Std.string(decision.ownerRelative));
  }

  static function main():Void {
    var psych = SourceMappedMediaPolicy.psych();
    check(psych.label == "psych-media", "Psych policy label changed");
    var psychImage = event("assets/shared/images/ui/atlas.PNG", "shared", "image", null, false, "true");
    check(psych.beforeHash(psychImage.sourceRelative, psychImage.mappedPath),
      "supported image was excluded before hashing");
    checkDecision(psych, psychImage, "accept", "shared/images/ui/atlas.PNG", "Psych image");
    check(psychImage.mappedPath == "assets/shared/images/ui/atlas.PNG"
      && psychImage.library == "shared" && psychImage.embed == "true",
      "Project target/library/embed metadata was rewritten");
    checkDecision(psych, event("assets/images/ui/atlas.xml"), "accept", "images/ui/atlas.xml",
      "Sparrow atlas metadata");
    checkDecision(psych, event("assets/images/animated/Animation.json"), "accept",
      "images/animated/Animation.json", "Animate manifest");
    checkDecision(psych, event("assets/custom/Animation.json"), "accept",
      "custom/Animation.json", "Animate manifest at an authored target");
    checkDecision(psych, event("assets/opaque/portrait.png"), "accept",
      "opaque/portrait.png", "runtime image at an authored target");
    checkDecision(psych, event("assets/opaque/cue.ogg"), "accept",
      "opaque/cue.ogg", "runtime sound at an authored target");
    checkDecision(psych, event("assets/opaque/typed-image.bin", "", "image"), "defer",
      "opaque/typed-image.bin", "typed image with an unsupported encoding");
    var renamedPng = event("assets/custom/mapped-pixels.bin", "", "image");
    renamedPng.sourceRelative = "assets/sheets/pixels.png";
    checkDecision(psych, renamedPng, "accept", "custom/mapped-pixels.bin",
      "typed PNG renamed to a nonstandard target extension");
    checkDecision(psych, event("assets/templates/layout.bin", "", "template"), "ignore", null,
      "non-media template is left to its existing consumer");
    var typedImage:PsychAssetProfileCandidate = {
      order:0, sourceRelative:"assets/typed-image", targetRelative:"assets/opaque",
      includePatterns:["*"], excludePatterns:[], conditions:[], state:"enabled",
      type:"image", embed:"false", library:""
    };
    var ordinaryAsset:PsychAssetProfileCandidate = {
      order:1, sourceRelative:"assets/ordinary", targetRelative:"assets/ordinary",
      includePatterns:["*"], excludePatterns:[], conditions:[], state:"enabled",
      type:"", embed:"false", library:""
    };
    var templateAsset:PsychAssetProfileCandidate = {
      order:2, sourceRelative:"assets/templates/layout", targetRelative:"assets/templates/layout.bin",
      includePatterns:["*"], excludePatterns:[], conditions:[], state:"enabled",
      type:"template", embed:"false", library:""
    };
    check(psych.beforeHashCandidate("assets/typed-image/picture.bin",
      "assets/opaque/picture.bin", typedImage),
      "explicit media type did not enable candidate-aware prehashing");
    var unresolvedTypedImage = typedImage;
    unresolvedTypedImage.state = "unresolved";
    var typedProjection = psych.classifyProjectionCandidate("assets/typed-image/picture.png",
      "opaque/picture.bin", unresolvedTypedImage);
    check(typedProjection.state == "defer" && typedProjection.ownerRelative == "opaque/picture.bin",
      "typed deferred projection did not protect a nonstandard target");
    var symbolicTarget = typedImage;
    symbolicTarget.targetRelative = "assets/${UNKNOWN_TARGET}";
    var symbolicProjection = psych.classifyProjectionCandidate("assets/typed-image/picture.png",
      null, symbolicTarget);
    check(symbolicProjection.state == "defer" && symbolicProjection.ownerRelative == "",
      "unresolved typed target was treated as a literal owner path");
    check(!psych.beforeHashCandidate("assets/ordinary/readme.txt",
      "assets/ordinary/readme.txt", ordinaryAsset),
      "ordinary text was selected for media hashing");
    check(!psych.beforeHashCandidate("assets/templates/layout.bin",
      "assets/templates/layout.bin", templateAsset),
      "template asset was selected for media hashing");
    var mediaTemplate:PsychAssetProfileCandidate = {
      order:3, sourceRelative:"assets/templates/icon.png", targetRelative:"assets/images/icon.png",
      includePatterns:["*"], excludePatterns:[], conditions:[], state:"enabled",
      type:"template", embed:"false", library:""
    };
    check(psych.beforeHashCandidate("assets/templates/icon.png",
      "assets/images/icon.png", mediaTemplate),
      "media-shaped template transition was omitted before hashing");
    checkDecision(psych, event("assets/images/icon.png", "", "template"), "defer",
      "images/icon.png", "media-shaped template transition preserves prior media output");
    checkDecision(psych, event("assets/music/freakyMenu.ogg", "shared", "music"),
      "accept", "music/freakyMenu.ogg", "Psych menu music");
    checkDecision(psych, event("assets/sounds/hit.mp3", "shared", "sound"),
      "accept", "sounds/hit.mp3", "Psych sound");
    checkDecision(psych, event("assets/fonts/ui.ttf", "", "font"),
      "accept", "fonts/ui.ttf", "Psych font");
    checkDecision(psych, event("assets/shaders/glow.frag"), "accept", "shaders/glow.frag",
      "Psych shader");
    checkDecision(psych, event("assets/videos/intro.mp4"), "accept", "videos/intro.mp4",
      "Psych video");
    checkDecision(psych, event("assets/sounds/hit.flac"), "defer", "sounds/hit.flac",
      "unsupported Psych audio extension");
    check(psych.managedOutputPredicate("sounds/hit.flac"),
      "unsupported media output was not protected as managed media");
    checkDecision(psych, event("assets/songs/test/Inst.ogg"), "ignore", null,
      "specialized song audio");
    var renamedSong = event("assets/custom/renamed-track.ogg", "", "sound");
    renamedSong.sourceRelative = "assets/songs/test/Inst.ogg";
    checkDecision(psych, renamedSong, "ignore", null,
      "specialized song source remains with its converter after rename");
    check(!psych.beforeHash("assets/songs/test/Inst.ogg", "assets/songs/test/Inst.ogg"),
      "song audio was hashed by the generic media policy");
    checkDecision(psych, event("assets/images/icon.png", "", "image",
      "legacy/icon-alias"), "defer", "images/icon.png", "custom Lime id");
    var psychWithIdentity = SourceMappedMediaPolicy.psych(true);
    checkDecision(psychWithIdentity, event("assets/images/icon.png", "", "image",
      "legacy/icon-alias"), "accept", "images/icon.png",
      "custom Lime id with the composite verified identity index");
    checkDecision(psych, event("assets/images/icon.png", "", "image",
      "assets/images/icon.png", true), "accept", "images/icon.png", "identity-preserving id");
    checkDecision(psych, event("assets/images/icon.png", "stage", "image"),
      "accept", "images/icon.png", "separate Lime library metadata");
    checkDecision(psych, event("assets/images/raw.bin"), "defer", "images/raw.bin",
      "unsupported image target");

    var nvPackage = SourceMappedMediaPolicy.nightmareVision("package");
    var nvCore = SourceMappedMediaPolicy.nightmareVision("core");
    var nvPackageWithIdentity = SourceMappedMediaPolicy.nightmareVision("package", true);
    checkDecision(nvPackage, event("assets/images/mod/icon.png"), "accept",
      "images/mod/icon.png", "NV package image");
    checkDecision(nvCore, event("assets/images/game/icon.png"), "accept",
      "__nmv_core/images/game/icon.png", "NV core image");
    checkDecision(nvCore, event("assets/videos/intro.webm"), "accept",
      "__nmv_core/videos/intro.webm", "NV core video");
    checkDecision(nvPackageWithIdentity, event("assets/images/mod/aliased.png", "mod", "image",
      "mod:portraits/hero"), "accept", "images/mod/aliased.png",
      "NV package ID alias with the composite verified identity index");
    checkDecision(nvCore, event("assets/music/menu.wav"), "accept",
      "__nmv_core/music/menu.wav", "NV core music");
    checkDecision(nvCore, event("assets/videos/intro.avi"), "defer",
      "__nmv_core/videos/intro.avi", "unsupported NV video extension");
    check(nvCore.managedOutputPredicate("__nmv_core/videos/intro.avi"),
      "NV core media output scope did not protect an unsupported extension");
    check(!nvPackage.managedOutputPredicate("__nmv_core/images/game/icon.png"),
      "package scope claimed the separate NV core namespace");
    check(nvPackage.managedOutputPredicate("images/mod/icon.png"),
      "NV package media output was not scoped");
    var coreProjection:SourceMappedAssetDecision = nvCore.classifyProjection(null, "images");
    check(coreProjection.state == "defer"
      && coreProjection.ownerRelative == "__nmv_core/images",
      "NV core deferred projection did not retain its separate physical root");
    var packageProjection:SourceMappedAssetDecision = nvPackage.classifyProjection(null, "images");
    check(packageProjection.state == "defer" && packageProjection.ownerRelative == "images",
      "NV package projection was not preserved");
    check(nvCore.classifyProjection("assets/music/menu.ogg", null).state == "defer",
      "source-only media projection was not protected");
    check(nvCore.classifyProjection("assets/data/chart.json", null).state == "ignore",
      "non-media source projection was overblocked");
    check(nvCore.classifyProjection("", null).state == "defer",
      "unknown source projection did not fail closed");
    check(SourceMappedMediaPolicy.nightmareVision("core").label
      != SourceMappedMediaPolicy.nightmareVision("package").label,
      "NV core and package policy scopes collided by label");
    var nvUnknown = SourceMappedMediaPolicy.nightmareVisionUnresolved();
    check(nvUnknown.label == "nightmare-vision-media-unresolved",
      "NV unresolved-scope policy label changed");
    checkDecision(nvUnknown, event("assets/images/game/icon.png"), "defer", "",
      "NV media with unproven package/core origin");
    check(nvUnknown.managedOutputPredicate("images/game/icon.png")
      && nvUnknown.managedOutputPredicate("__nmv_core/images/game/icon.png"),
      "unresolved NV scope did not protect both package and core outputs");
    check(nvUnknown.classifyProjection("assets/opaque/custom.asset", null).state == "defer",
      "unresolved NV scope did not preserve an arbitrary source projection");
    var unresolvedTypedProjection = nvUnknown.classifyProjectionCandidate(
      "assets/typed-image/picture.png", "opaque/picture.bin", unresolvedTypedImage);
    check(unresolvedTypedProjection.state == "defer" && unresolvedTypedProjection.ownerRelative == "",
      "unresolved NV typed projection guessed a package/core destination");
    Sys.println("ok");
  }
}'''


class SourceMappedMediaPolicyTest(unittest.TestCase):
    def test_exact_media_categories_and_owner_routing(self):
        Path(TEST_TMP).mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="mapped-media-policy-", dir=TEST_TMP) as temp:
            work = Path(temp)
            (work / "Main.hx").write_text(MAIN, encoding="utf-8", newline="\n")
            tjson = work / "tjson"
            tjson.mkdir()
            (tjson / "TJSON.hx").write_text('''package tjson;
class TJSON {}
interface EncodeStyle {}
class TJSONEncoder {
  public function new(?pretty:Bool = false) {}
  public function parse(input:String):Dynamic return haxe.Json.parse(input);
  public function encode(value:Dynamic):String return haxe.Json.stringify(value);
  public function doEncode(value:Dynamic, ?style:Dynamic):String return haxe.Json.stringify(value);
  public function encodeValue(value:Dynamic, style:EncodeStyle, depth:Int):String return haxe.Json.stringify(value);
}
''', encoding="utf-8", newline="\n")
            env = dict(os.environ)
            env["PYTHONUTF8"] = "1"
            process = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--run", "Main"],
                cwd=work, env=env, text=True, capture_output=True, timeout=90,
            )
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            self.assertIn("ok", process.stdout)


if __name__ == "__main__":
    unittest.main()
