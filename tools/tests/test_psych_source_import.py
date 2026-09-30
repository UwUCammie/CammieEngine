"""Psych compiled source is retained under its imported owner namespace."""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest

from tools.tests.test_psych_character_scope import extract_method


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class PsychSourceImportTest(unittest.TestCase):
    def test_haxe_source_is_copied_add_only_inside_the_import_owner(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("var ownerRuntimeRoot = CompatScriptManifest.destinationRoot(engineRoot.root, engineRoot.engine);", module)
        self.assertIn("mergePsychSourceModules(engineRoot.root, ownerRuntimeRoot)", module)
        self.assertIn("var readCapacity = Std.int(Math.min(sourceSize + 1, readLimit + 1));", module)
        self.assertIn("var boundedBytes = haxe.io.Bytes.alloc(readCapacity);", module)
        methods = "\n".join(
            extract_method(module, marker)
            for marker in (
                "static function importPathKey",
                "static function importPathIsWithin",
                "static function validImportEntryName",
                "static function ensureDirectory",
                "static function existingImportChild",
                "static function mergePsychSourceModules",
            )
        )
        fixture = '''import haxe.io.Path;
import sys.FileSystem;
using StringTools;

typedef ImportAssetMergeResult = { var copied:Int; var skipped:Int; var failed:Int;
  @:optional var errors:Array<String>; };
class ImportSettings {
  public static function normalizeSourcePath(path:Dynamic):String
    return path == null ? "" : Path.normalize(Std.string(path));
}
class CompatScriptManifest { public static inline var ROOT_PREFIX = "assets/imported_mods"; }
class File {
  public static function read(path:String, ?binary:Bool = false):sys.io.FileInput {
    if (path.indexOf("CannotOpen.hx") >= 0) throw "fixture read-open failure";
    return sys.io.File.read(path, binary);
  }
  public static function saveBytes(path:String, bytes:haxe.io.Bytes):Void
    sys.io.File.saveBytes(path, bytes);
}
class ModuleFunctions {
  static function importWorkCancelled():Bool return false;
  static function reportImportProgress(phase:String, current:String, completed:Int = 0,
      total:Int = 0, copied:Int = 0, skipped:Int = 0, failed:Int = 0, work:Int = 0):Void {}
''' + methods + '''
  public static function merge(source:String, owner:String):ImportAssetMergeResult
    return mergePsychSourceModules(source, owner);
}
class Main {
  static function fail(message:String):Void throw message;
  static function main():Void {
    var source = Sys.args()[0];
    var owner = "assets/imported_mods/psych-owner";
    var result = ModuleFunctions.merge(source, owner);
    if (result.copied != 2 || result.skipped != 1)
      fail("unexpected source import counts: " + result.copied + "/" + result.skipped + "/" + result.failed);
    var stage = owner + "/source/states/stages/StageWeek1.hx";
    var dependency = owner + "/source/backend/WeekData.hx";
    var overridePath = owner + "/source/backend/BaseStage.hx";
    if (!FileSystem.exists(stage) || sys.io.File.getContent(stage) != "class StageWeek1 {}")
      fail("stage module was not retained under its owner source tree");
    if (!FileSystem.exists(dependency) || sys.io.File.getContent(dependency) != "class WeekData {}")
      fail("source dependency was not retained with its relative path");
    if (sys.io.File.getContent(overridePath) != "owner-edited BaseStage")
      fail("an existing owner module was replaced");
    if (FileSystem.exists(owner + "/source/README.md"))
      fail("non-Haxe source content was copied");
    if (FileSystem.exists(owner + "/source/CannotOpen.hx"))
      fail("a source module that failed to open was copied");
    if (FileSystem.exists(owner + "/source/Fifo.hx"))
      fail("a non-regular source entry was copied");
    if (FileSystem.exists(owner + "/source/external-leak.hx"))
      fail("source symlink escaped the donor root");
    if (FileSystem.exists("outside-destination/Hidden.hx"))
      fail("destination symlink escaped the import owner");
    var diagnostics = result.errors == null ? "" : result.errors.join("\\n");
    var expectsFifo = Sys.args()[1] == "fifo";
    if (result.failed < (expectsFifo ? 5 : 4) || diagnostics.indexOf("[psych-source-reject]") < 0
        || diagnostics.indexOf("outside the selected Psych source tree") < 0
        || diagnostics.indexOf("outside its import owner") < 0
        || diagnostics.indexOf("file size exceeds") < 0
        || diagnostics.indexOf("could not open Haxe source") < 0
        || (expectsFifo && diagnostics.indexOf("empty or unsupported Haxe source entry") < 0))
      fail("rejected source entries were not diagnosed: " + diagnostics);
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp", prefix="psych-source-import-") as folder:
            work = Path(folder)
            (work / "Main.hx").write_text(fixture)
            (work / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            )
            donor = work / "psych-donor"
            source_root = donor / "source"
            (source_root / "states/stages").mkdir(parents=True)
            (source_root / "backend").mkdir()
            (source_root / "states/stages/StageWeek1.hx").write_text("class StageWeek1 {}")
            (source_root / "backend/WeekData.hx").write_text("class WeekData {}")
            (source_root / "backend/BaseStage.hx").write_text("class BaseStage {}")
            (source_root / "CannotOpen.hx").write_text("class CannotOpen {}")
            fifo_supported = False
            if hasattr(os, "mkfifo"):
                try:
                    os.mkfifo(source_root / "Fifo.hx")
                    fifo_supported = True
                except OSError:
                    pass
            (source_root / "README.md").write_text("source notes")
            (source_root / "Oversized.hx").write_bytes(b"x" * (4 * 1024 * 1024 + 1))
            outside = work / "outside-source"
            outside.mkdir()
            (outside / "External.hx").write_text("class External {}")
            try:
                (source_root / "external-leak.hx").symlink_to(outside / "External.hx")
            except (OSError, NotImplementedError) as error:
                self.skipTest("symlinks are unavailable in this test environment: " + str(error))

            owner_source = work / "assets/imported_mods/psych-owner/source"
            (owner_source / "backend").mkdir(parents=True)
            (owner_source / "backend/BaseStage.hx").write_text("owner-edited BaseStage")
            outside_destination = work / "outside-destination"
            outside_destination.mkdir()
            (owner_source / "External").symlink_to(outside_destination, target_is_directory=True)
            (source_root / "External").mkdir()
            (source_root / "External/Hidden.hx").write_text("class Hidden {}")

            result = subprocess.run(
                [str(HAXE), "-cp", str(work), "--run", "Main", str(donor),
                 "fifo" if fifo_supported else "no-fifo"],
                cwd=work,
                capture_output=True,
                text=True,
                timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
