"""Blocking native work must not hold up collections on other threads."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath

ROOT = Path(__file__).resolve().parents[2]


class UpdateDownloadGcZoneTest(unittest.TestCase):
    def test_urlmon_call_runs_inside_a_gc_free_zone_on_copied_strings(self):
        source = (ROOT / "source/WindowsUpdateDownload.hx").read_text(encoding="utf-8")
        native = source[source.index("namespace cammie_update_download"):source.index("@:buildXml(")]
        enter = native.index("hx::EnterGCFreeZone();")
        leave = native.index("hx::ExitGCFreeZone();")
        call = native.index("URLDownloadToFileW(")
        self.assertLess(enter, call)
        self.assertLess(call, leave)
        # Strings are copied before the zone; inside it only native locals are used.
        before = native[:enter]
        self.assertIn("std::wstring source(url.wchar_str(&urlBuffer));", before)
        self.assertIn("std::wstring target(destination.wchar_str(&destinationBuffer));", before)
        zone = native[enter + len("hx::EnterGCFreeZone();"):leave]
        self.assertEqual(zone.strip(), "HRESULT result=URLDownloadToFileW(NULL,source.c_str(),target.c_str(),0,NULL);")
        self.assertNotIn("__WCStr", source)
        self.assertEqual(source.count("URLDownloadToFileW("), 1)
        self.assertIn("cammie_update_download::toFile({0}, {1})", source)

    def test_dependency_hashes_are_chunked_and_match_the_whole_file_hash(self):
        source = (ROOT / "source/CodenameBaseCharacterDependency.hx").read_text(encoding="utf-8")
        self.assertNotIn("Sha256.make(", source)
        self.assertEqual(len(re.findall(r"fileDigest\((source|destination)\)", source)), 3)
        helper = source[source.index("static function fileDigest(path:String):String {"):]
        helper = helper[:helper.index("\n\t}\n") + 3]
        self.assertIn("File.read(path, true)", helper)
        self.assertIn("ImportWorkScheduler.cooperate();", helper)
        fixture = r'''
import haxe.crypto.Sha256;
import haxe.io.Bytes;
import sys.io.File;
@:access(CodenameBaseCharacterDependency)
class Main {
 static function check(b:Bool, s:String) if (!b) throw s;
 static function main() {
  var folder = Sys.args()[0];
  var sizes = [0, 1, 63, 64, 65, 65535, 65536, 65537, 200001];
  for (size in sizes) {
   var bytes = Bytes.alloc(size);
   for (i in 0...size) bytes.set(i, (i * 131 + size * 7) & 255);
   var path = folder + '/sample-' + size + '.bin';
   File.saveBytes(path, bytes);
   var expected = Sha256.make(File.getBytes(path)).toHex();
   var actual = CodenameBaseCharacterDependency.fileDigest(path);
   check(actual == expected, 'digest differs at ' + size + ': ' + actual + ' != ' + expected);
  }
  var missing = false;
  try CodenameBaseCharacterDependency.fileDigest(folder + '/missing.bin') catch (_:Dynamic) missing = true;
  check(missing, 'a missing file hashed');
  var directory = false;
  try CodenameBaseCharacterDependency.fileDigest(folder) catch (_:Dynamic) directory = true;
  check(directory, 'a directory hashed');
  Sys.println('OK');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = FixturePath(folder)
            (work / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--run", "Main", str(work)],
                cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
