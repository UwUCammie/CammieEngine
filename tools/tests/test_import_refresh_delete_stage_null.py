"""The import staging cleanup must not treat a failed directory listing as empty."""
from haxe_test_support import HAXE_COMMAND

import json
import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
MANAGER = ROOT / "source/ImportRefreshManager.hx"

FIXTURE = r'''import haxe.Json;
import haxe.io.Path;
using StringTools;

class MockFileSystem {
  public static var readPaths:Array<String> = [];
  public static var deletedDirectories:Array<String> = [];
  public static var deletedFiles:Array<String> = [];

  public static function exists(path:String):Bool return true;
  public static function fullPath(path:String):String return path;
  public static function readDirectory(path:String):Array<String> {
    readPaths.push(path);
    return null;
  }
  public static function isDirectory(path:String):Bool return false;
  public static function deleteFile(path:String):Void deletedFiles.push(path);
  public static function deleteDirectory(path:String):Void deletedDirectories.push(path);
}

class ImportRefreshDeleteStageFixture {
  static function relativeTo(path:String, root:String):Null<String> {
    if (path == root) return "";
    var prefix = root.endsWith("/") ? root : root + "/";
    return StringTools.startsWith(path, prefix) ? path.substr(prefix.length) : null;
  }

__DELETE_STAGE__

  static function main():Void {
    var stage = "/tmp/refresh-stage-with-children";
    var error = "";
    try deleteStage(stage) catch (caught:Dynamic) error = Std.string(caught);
    Sys.println(Json.stringify({error:error, readPaths:MockFileSystem.readPaths,
      deletedDirectories:MockFileSystem.deletedDirectories, deletedFiles:MockFileSystem.deletedFiles}));
  }
}
'''


def extract_method(source: str, name: str) -> str:
    marker = f"static function {name}("
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated production method {name}")


class ImportRefreshDeleteStageNullTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HAXE.is_file():
            raise unittest.SkipTest("portable Haxe is unavailable")
        method = extract_method(MANAGER.read_text(encoding="utf-8"), "deleteStage")
        # Redirect the production method's filesystem calls to a deterministic fake.
        cls.method = method.replace("FileSystem.", "MockFileSystem.")

    def test_null_directory_listing_reports_path_and_does_not_delete(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            fixture = work / "ImportRefreshDeleteStageFixture.hx"
            fixture.write_text(FIXTURE.replace("__DELETE_STAGE__", self.method), encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "--run", "ImportRefreshDeleteStageFixture"],
                cwd=work,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=30,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(report["error"],
                         "Could not enumerate import staging directory: /tmp/refresh-stage-with-children")
        self.assertEqual(report["readPaths"], ["/tmp/refresh-stage-with-children"])
        self.assertEqual(report["deletedDirectories"], [])
        self.assertEqual(report["deletedFiles"], [])


if __name__ == "__main__":
    unittest.main()
