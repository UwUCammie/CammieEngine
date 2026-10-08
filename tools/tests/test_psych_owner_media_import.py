"""Psych mapped media stays with each selected compiled-stage owner."""
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
                return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class PsychOwnerMediaImportTest(unittest.TestCase):
    def test_mapped_media_is_owner_scoped_non_overwriting_and_repeatable(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text(encoding="utf-8")
        methods = "\n".join(
            extract_method(module, marker)
            for marker in (
                "static function importPathKey",
                "static function importPathIsWithin",
                "static function validImportEntryName",
                "static function ensureDirectory",
                "static function existingImportChild",
                "static function mergeTreeNonOverwriting",
                "static function psychDestinationAssetRoot",
                "static function mergePsychRuntimeMedia",
                "static function mergePsychMediaTree",
            )
        )

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            (work / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            donor_a = work / "donor-a/assets/base_game"
            donor_b = work / "donor-b/assets/base_game"
            shared_a = work / "donor-a/assets/shared"
            owner_a = "assets/imported_mods/owner-a"
            owner_b = "assets/imported_mods/owner-b"

            def write(root: Path, relative: str, value: str) -> Path:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(value, encoding="utf-8", newline='\n')
                return path

            source_a = write(donor_a, "weekend1/images/philly/Animation.json", "owner-a-stage")
            write(donor_a, "weekend1/images/philly/spritemap1.png", "owner-a-atlas")
            write(donor_a, "weekend1/shaders/PhillyGlow.frag", "shader")
            write(donor_a, "weekend1/videos/intro.mp4", "video")
            write(donor_a, "weekend1/fonts/title.otf", "font")
            write(donor_a, "weekend1/animations/timeline.json", "animation folder")
            write(donor_a, "weekend1/sounds/train_passes.ogg", "owner-a-train")
            write(donor_a, "data/weekend1/weekend1.json", "chart")
            write(donor_a, "songs/weekend1/Inst.ogg", "song audio")
            write(donor_b, "weekend1/images/philly/Animation.json", "owner-b-stage")
            write(donor_b, "weekend1/sounds/train_passes.ogg", "owner-b-train")
            write(shared_a, "images/common/atlas.png", "shared-atlas")
            write(work, f"{owner_a}/weekend1/shaders/PhillyGlow.frag", "owner override")
            # Bundled Python packages exceed the media discovery depth, but
            # remain intact in the donor and are not runtime library roots.
            bundled = donor_a / "utility/runtime/python/lib"
            write(bundled, "os.py", "stdlib")
            write(bundled, "site.py", "stdlib")
            write(bundled, "encodings/__init__.py", "stdlib")
            write(bundled, "site-packages/pkg/a/b/c/d/e/f/images/tool.png", "tool only")
            # Folder names alone are not enough to suppress authored media.
            write(donor_a, "python/lib/images/art.png", "authored art")
            external_media = work / "external-media"
            write(external_media, "leak.png", "outside donor")
            escaped_link = donor_a / "weekend1/images/external"
            try:
                escaped_link.symlink_to(external_media, target_is_directory=True)
                has_escape_link = True
            except (NotImplementedError, OSError):
                has_escape_link = False

            (work / "Main.hx").write_text(r'''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;

@:access(ModuleFunctions)
class Main {
 static function check(value:Bool, message:String):Void
  if (!value) throw message;
 static function main():Void {
  var baseA = Sys.args()[0];
  var baseB = Sys.args()[1];
  var sharedA = Sys.args()[2];
  var ownerA = "assets/imported_mods/owner-a";
  var ownerB = "assets/imported_mods/owner-b";
  var expectedEscapeRejects = Sys.args()[3] == "1" ? 1 : 0;
  var mainA = ModuleFunctions.mergePsychRuntimeMedia(baseA, "", ownerA);
  var shared = ModuleFunctions.mergePsychRuntimeMedia(sharedA, "shared", ownerA);
  var mainB = ModuleFunctions.mergePsychRuntimeMedia(baseB, "", ownerB);
  check(mainA.failed == expectedEscapeRejects && shared.failed == 0 && mainB.failed == 0,
   "fixture media copy failure or escaped link was not rejected");
  check(File.getContent(ownerA + "/weekend1/images/philly/Animation.json") == "owner-a-stage",
   "mapped stage image tree was not retained under owner A");
  check(File.getContent(ownerA + "/weekend1/images/philly/spritemap1.png") == "owner-a-atlas",
   "animation atlas pair was not retained under owner A");
  check(File.getContent(ownerA + "/weekend1/shaders/PhillyGlow.frag") == "owner override",
   "an existing owner shader was replaced");
  check(File.getContent(ownerA + "/weekend1/videos/intro.mp4") == "video",
   "mapped video tree was not retained under owner A");
  check(File.getContent(ownerA + "/weekend1/fonts/title.otf") == "font",
   "mapped font tree was not retained under owner A");
  check(File.getContent(ownerA + "/weekend1/animations/timeline.json") == "animation folder",
   "mapped animation tree was not retained under owner A");
  check(File.getContent(ownerA + "/weekend1/sounds/train_passes.ogg") == "owner-a-train",
   "mapped library sound was not retained under owner A");
  check(File.getContent(ownerA + "/shared/images/common/atlas.png") == "shared-atlas",
   "supplemental Project.xml root lost its shared prefix");
  check(File.getContent(ownerB + "/weekend1/images/philly/Animation.json") == "owner-b-stage",
   "second owner media was not copied");
  check(File.getContent(ownerB + "/weekend1/sounds/train_passes.ogg") == "owner-b-train",
   "second owner library sound was not copied");
  check(File.getContent(ownerA + "/weekend1/images/philly/Animation.json") !=
    File.getContent(ownerB + "/weekend1/images/philly/Animation.json"), "owners collided");
  check(!FileSystem.exists(ownerA + "/data/weekend1/weekend1.json"), "chart tree was copied");
  check(!FileSystem.exists(ownerA + "/songs/weekend1/Inst.ogg"), "song tree was copied");
  check(!FileSystem.exists(ownerA + "/weekend1/images/external/leak.png"),
   "symlinked media escaped the selected donor root");
  check(FileSystem.exists(baseA + "/weekend1/images/philly/Animation.json"), "donor file was changed");
  check(File.getContent(ownerA + "/python/lib/images/art.png") == "authored art",
   "a directory name alone suppressed authored media");
  check(!FileSystem.exists(ownerA + "/utility"), "bundled Python was copied as FNF media");
  check(File.getContent(baseA + "/utility/runtime/python/lib/site-packages/pkg/a/b/c/d/e/f/images/tool.png") == "tool only",
   "runtime exclusion removed retained donor content");
  var repeat = ModuleFunctions.mergePsychRuntimeMedia(baseA, "", ownerA);
  check(repeat.failed == expectedEscapeRejects && repeat.copied == 0 && repeat.skipped >= 6,
   "repeat import must skip existing owner media");
 }
}''', encoding="utf-8", newline='\n')

            (work / "CompatScriptManifest.hx").write_text(r'''class CompatScriptManifest {
 public static inline var ROOT_PREFIX:String = "assets/imported_mods";
}''', encoding="utf-8", newline='\n')
            (work / "ImportSettings.hx").write_text(r'''import haxe.io.Path;
using StringTools;
class ImportSettings {
 public static function normalizeSourcePath(path:String):String
  return path == null ? "" : Path.normalize(StringTools.replace(StringTools.trim(path), "\\", "/"));
}''', encoding="utf-8", newline='\n')
            (work / "ModuleFunctions.hx").write_text(r'''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

typedef ImportAssetMergeResult = {
 var copied:Int;
 var skipped:Int;
 var failed:Int;
 @:optional var errors:Array<String>;
}
typedef SourceMappedAssetPlan = { var failed:Bool; var cancelled:Bool; var diagnostics:Array<String>; }
typedef PreparedMappedAssetOwner = { var sourceRoot:String; var engine:String; var scope:String;
 var destinationRoot:String; var plan:SourceMappedAssetPlan; }

class ModuleFunctions {
 static function skipMappedOwnerMediaFile(owner:PreparedMappedAssetOwner,
     _source:String, _destination:String):Bool {
  if (owner != null) throw "owner-media fixture is only for the profile-unavailable legacy path";
  return false;
 }
''' + methods + r'''
 static function importWorkCancelled():Bool return false;
 static function reportImportProgress(phase:String, current:String, completed:Int = 0, total:Int = 0,
     copied:Int = 0, skipped:Int = 0, failed:Int = 0, work:Int = 0):Void {}
}''', encoding="utf-8", newline='\n')

            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "--run", "Main",
                 str(donor_a), str(donor_b), str(shared_a), "1" if has_escape_link else "0"],
                cwd=work, capture_output=True, text=True, timeout=60,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
