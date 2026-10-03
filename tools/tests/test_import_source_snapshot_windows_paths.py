"""Exercise the snapshot verifier's extracted platform path guards."""
from haxe_test_support import haxe_command

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source/ImportSourceSnapshot.hx"
HAXE = ROOT / ".tools/haxe/haxe"

FIXTURE = r'''import haxe.io.Path;
using StringTools;

class SnapshotPathGuards {
__NORMALIZE_ABSOLUTE__
__IS_WITHIN__

  static function directoryAllowed(directoryPath:String, directoryCanonical:String, contentRoot:String):Bool {
    if (__DIRECTORY_GUARD__) return false;
    return true;
  }

  static function fileAllowed(path:String, canonical:String, contentRoot:String):Bool {
    if (__FILE_GUARD__) return false;
    return true;
  }

  static function expect(actual:Bool, expected:Bool, label:String):Void {
    if (actual != expected) throw label + " guard result was " + actual;
  }

  static function main():Void {
    #if windows
    var root = "C:\\Snapshot\\Content";
    var path = "C:\\Snapshot\\Content\\Dependency.class";
    var canonical = "c:/snapshot/content/dependency.class";
    var normalizedRoot = normalizeAbsolute(root);
    expect(directoryAllowed(path, canonical, normalizedRoot), true,
      "Windows directory path with case-folded canonical path");
    expect(fileAllowed(path, canonical, normalizedRoot), true,
      "Windows file path with case-folded canonical path");
    expect(directoryAllowed("C:\\Alias\\Content", "C:/Resolved/Content",
      normalizeAbsolute("C:/Resolved")), false,
      "Windows directory resolved through a different path");
    expect(fileAllowed("C:\\Alias\\Content\\Dependency.class",
      "C:/Resolved/Content/Dependency.class", normalizeAbsolute("C:/Resolved/Content")), false,
      "Windows file resolved through a different path");
    expect(directoryAllowed("C:/Snapshot/Content-elsewhere", "c:/snapshot/content-elsewhere",
      normalizedRoot), false, "Windows sibling path sharing a textual prefix");
    expect(fileAllowed("C:/Snapshot/Outside/Dependency.class", "c:/snapshot/outside/dependency.class",
      "c:/snapshot/content"), false, "Windows path outside content root");
    if (normalizeAbsolute(path) != "c:/snapshot/content/dependency.class")
      throw "Windows normalizeAbsolute did not normalize separators and case";
    #else
    var root = "/tmp/Mixed/Content";
    var path = "/tmp/Mixed/Content/Dependency.class";
    expect(directoryAllowed(path, path, root), true, "POSIX exact directory path");
    expect(fileAllowed(path, path, root), true, "POSIX exact file path");
    expect(directoryAllowed(path, "/tmp/mixed/Content/Dependency.class", root), false,
      "POSIX directory case mismatch");
    expect(fileAllowed(path, "/tmp/Mixed/content/Dependency.class", root), false,
      "POSIX file case mismatch");
    expect(fileAllowed(path, "/tmp/Mixed/Outside/Dependency.class", root), false,
      "POSIX different resolved path");
    if (normalizeAbsolute("/tmp/Mixed/./Content/../Content") != root)
      throw "POSIX normalizeAbsolute did not collapse dot segments";
    if (normalizeAbsolute(root) == normalizeAbsolute("/tmp/mixed/Content"))
      throw "POSIX normalizeAbsolute erased a meaningful case distinction";
    #end
    Sys.println("snapshot-path-guards-ok");
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


def extract_guard(source: str, left: str, path_arg: str) -> str:
    pattern = re.compile(
        rf"if\s*\(\s*({left}\s*!=\s*normalizeAbsolute\({path_arg}\)"
        rf"\s*\|\|\s*!isWithin\({left},\s*contentRoot\))",
        re.MULTILINE,
    )
    match = pattern.search(source)
    if match is None:
        raise AssertionError(f"could not find production guard for {left}")
    return match.group(1)


class ImportSourceSnapshotWindowsPathTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HAXE.is_file():
            raise unittest.SkipTest("portable Haxe is unavailable")
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.normalize_method = extract_method(cls.source, "normalizeAbsolute")
        cls.within_method = extract_method(cls.source, "isWithin")
        cls.directory_guard = extract_guard(
            cls.source, "directoryCanonical", "directoryPath"
        )
        cls.file_guard = extract_guard(cls.source, "canonical", "path")

    def run_fixture(self, *, windows: bool):
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            source = FIXTURE.replace("__NORMALIZE_ABSOLUTE__", self.normalize_method)
            source = source.replace("__IS_WITHIN__", self.within_method)
            source = source.replace("__DIRECTORY_GUARD__", self.directory_guard)
            source = source.replace("__FILE_GUARD__", self.file_guard)
            fixture = work / "SnapshotPathGuards.hx"
            fixture.write_text(source, encoding="utf-8", newline='\n')
            command = haxe_command(windows=windows)
            command.extend(["-cp", str(work), "--run", "SnapshotPathGuards"])
            result = subprocess.run(
                command,
                cwd=work,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("snapshot-path-guards-ok", result.stdout)

    def test_production_path_guards_accept_windows_casefolded_paths_and_reject_escapes(self):
        self.run_fixture(windows=True)

    def test_production_path_guards_preserve_posix_case_and_reject_other_resolved_paths(self):
        self.run_fixture(windows=False)


if __name__ == "__main__":
    unittest.main()
