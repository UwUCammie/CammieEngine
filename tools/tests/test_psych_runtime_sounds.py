"""Psych owner sound copying preserves source identity and existing overrides."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "source/ModuleFunctions.hx").read_text()


def method(marker):
    start = SOURCE.index(marker)
    brace = SOURCE.index("{", start)
    depth = 0
    for index in range(brace, len(SOURCE)):
        if SOURCE[index] == "{":
            depth += 1
        elif SOURCE[index] == "}":
            depth -= 1
            if depth == 0:
                return SOURCE[start:index + 1]
    raise AssertionError(marker)


class PsychRuntimeSoundsTest(unittest.TestCase):
    def test_owner_sound_merge_repairs_only_missing_files(self):
        names = (
            "static function importPathKey",
            "static function importPathIsWithin",
            "static function findChildDirectory",
            "static function ensureDirectory",
            "static function existingImportChild",
            "static function validImportEntryName",
            "static function mergeTreeNonOverwriting",
            "static function mergePsychRuntimeSounds",
        )
        methods = "\n".join(method(name) for name in names)
        fixture = f'''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;
typedef ImportAssetMergeResult = {{var copied:Int; var skipped:Int; var failed:Int;
  @:optional var errors:Array<String>;}};
class ImportSettings {{
  public static function normalizeSourcePath(value:Dynamic):String
    return value == null ? '' : Path.normalize(StringTools.trim(Std.string(value)));
}}
class ModuleFunctions {{
  static function importWorkCancelled():Bool return false;
  static function reportImportProgress(phase:String, path:String, completed:Int = 0,
    total:Int = 0, copied:Int = 0, skipped:Int = 0, failed:Int = 0, work:Int = 0):Void {{}}
{methods}
  public static function merge(source:String, target:String):ImportAssetMergeResult
    return mergePsychRuntimeSounds(source, target);
}}
class Main {{
  static function fail(value:String):Void throw value;
  static function main():Void {{
    var source = Sys.args()[0]; var target = Sys.args()[1];
    var first = ModuleFunctions.merge(source, target);
    if (first.copied != 3 || first.failed != 0) fail('first sound copy');
    var soundRoot = Path.join([target, 'sounds']);
    if (File.getContent(Path.join([soundRoot, 'intro.ogg'])) != 'root-intro'
        || File.getContent(Path.join([soundRoot, 'nested', 'hit.ogg'])) != 'hit'
        || File.getContent(Path.join([soundRoot, 'shared.ogg'])) != 'root-shared')
      fail('source sound identity or root precedence');
    File.saveContent(Path.join([soundRoot, 'intro.ogg']), 'user-override');
    FileSystem.deleteFile(Path.join([soundRoot, 'nested', 'hit.ogg']));
    var repair = ModuleFunctions.merge(source, target);
    if (repair.copied != 1 || repair.failed != 0) fail('missing-only repair');
    if (File.getContent(Path.join([soundRoot, 'intro.ogg'])) != 'user-override'
        || File.getContent(Path.join([soundRoot, 'nested', 'hit.ogg'])) != 'hit')
      fail('existing override replaced or missing sound not repaired');
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            donor = work / "donor"
            target = work / "installed" / "psych-owner"
            (donor / "sounds" / "nested").mkdir(parents=True)
            (donor / "shared" / "sounds").mkdir(parents=True)
            (donor / "sounds" / "intro.ogg").write_text("root-intro", newline='\n')
            (donor / "sounds" / "nested" / "hit.ogg").write_text("hit", newline='\n')
            (donor / "sounds" / "shared.ogg").write_text("root-shared", newline='\n')
            (donor / "shared" / "sounds" / "shared.ogg").write_text("fallback-shared", newline='\n')
            (work / "Main.hx").write_text(fixture, newline='\n')
            (work / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "--run", "Main",
                 str(donor), str(target)],
                cwd=ROOT, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
