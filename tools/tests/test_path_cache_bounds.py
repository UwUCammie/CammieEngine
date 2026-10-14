"""Session-wide path and diagnostic caches stay bounded."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath
from test_nv_hit_order import extract_method

ROOT = Path(__file__).resolve().parents[2]


def run_haxe(test, files, main, extra_cp=()):
    with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
        work = FixturePath(folder)
        for name, text in files.items():
            (work / (name + ".hx")).write_text(text, encoding="utf-8", newline="\n")
        command = [*HAXE_COMMAND, "-cp", str(work)]
        for path in extra_cp:
            command.extend(("-cp", str(path)))
        result = subprocess.run([*command, "-main", main, "--interp"],
            cwd=folder, capture_output=True, text=True, timeout=120)
    test.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    test.assertIn("OK", result.stdout)


class PathCacheBoundsTest(unittest.TestCase):
    def test_case_resolved_paths_are_capped_and_dropped_on_import_refresh(self):
        source = (ROOT / "source/Paths.hx").read_text(encoding="utf-8")
        start = source.index("\tstatic var caseResolvedPaths")
        fields = source[start:source.index("static var caseResolvedGeneration:Int = 0;") + len("static var caseResolvedGeneration:Int = 0;")]
        methods = "\n".join(extract_method(source, marker) for marker in (
            "static function resolveCaseInsensitivePath",
            "static function rememberCaseResolvedPath",
            "static function clearCaseResolvedPaths",
        ))
        paths = "class PathsFixture {\n" + fields + "\n" + methods + r'''
 static function check(b:Bool, s:String) if (!b) throw s;
 static function count():Int { var n = 0; for (_ in caseResolvedPaths.keys()) n++; return n; }
 static function main() {
  // Filling past the cap starts the cache over instead of growing.
  for (i in 0...MAX_CASE_RESOLVED_PATHS) rememberCaseResolvedPath('assets/a' + i, 'assets/A' + i);
  check(count() == MAX_CASE_RESOLVED_PATHS && caseResolvedCount == MAX_CASE_RESOLVED_PATHS, 'cache did not fill to the cap');
  rememberCaseResolvedPath('assets/last', 'assets/Last');
  check(count() == 1 && caseResolvedCount == 1 && caseResolvedPaths.get('assets/last') == 'assets/Last', 'cache grew past the cap');

  // A stale entry is dropped and stops counting.
  rememberCaseResolvedPath('missing/gone.png', 'missing/Gone.png');
  check(resolveCaseInsensitivePath('missing/gone.png') == 'missing/gone.png', 'stale entry was returned');
  check(!caseResolvedPaths.exists('missing/gone.png') && caseResolvedCount == count(), 'stale entry was not uncounted');

  // An import refresh drops everything resolved before it.
  ImportRefreshManager.generation++;
  resolveCaseInsensitivePath('missing/other.png');
  check(count() == 0 && caseResolvedCount == 0, 'cache survived an import refresh');
  check(caseResolvedGeneration == ImportRefreshManager.generation, 'generation was not recorded');
  rememberCaseResolvedPath('assets/b', 'assets/B');
  resolveCaseInsensitivePath('missing/other.png');
  check(count() == 1, 'cache was cleared without a refresh');
  Sys.println('OK');
 }
}
'''
        run_haxe(self, {
            "PathsFixture": paths,
            "OpenFlAssets": "class OpenFlAssets { public static function exists(path:String, ?type:Dynamic):Bool return false; }",
            "ImportRefreshManager": "class ImportRefreshManager { public static var generation:Int = 0; }",
        }, "PathsFixture")

    def test_overlay_diagnostics_deduplicate_by_map_and_cap(self):
        main = r'''
@:access(ImportOverlayResolver)
class OverlayFixture {
 static function check(b:Bool, s:String) if (!b) throw s;
 static function main() {
  ImportOverlayResolver.invalidate();
  ImportOverlayResolver.recordDiagnostic('one');
  ImportOverlayResolver.recordDiagnostic('two');
  ImportOverlayResolver.recordDiagnostic('one');
  check(ImportOverlayResolver.getDiagnostics().join(',') == 'one,two', 'deduplication changed order or content');
  for (i in 0...ImportOverlayResolver.MAX_DIAGNOSTICS * 2) ImportOverlayResolver.recordDiagnostic('bad ' + i);
  check(ImportOverlayResolver.getDiagnostics().length <= ImportOverlayResolver.MAX_DIAGNOSTICS, 'diagnostics grew past the cap');
  ImportOverlayResolver.invalidate();
  check(ImportOverlayResolver.getDiagnostics().length == 0, 'invalidate kept diagnostics');
  ImportOverlayResolver.recordDiagnostic('one');
  check(ImportOverlayResolver.getDiagnostics().join(',') == 'one', 'invalidate kept the dedup set');
  Sys.println('OK');
 }
}
'''
        run_haxe(self, {"OverlayFixture": main}, "OverlayFixture", (ROOT / "source",))

    def test_character_resolution_diagnostics_deduplicate_by_map_and_cap(self):
        source = (ROOT / "source/Character.hx").read_text(encoding="utf-8")
        start = source.index("public static var resolutionDiagnostics:Array<String> = [];")
        fields = source[start:source.index("public static function reportResolution", start)]
        method = extract_method(source, "static function rememberResolutionDiagnostic(")
        fixture = "class CharacterFixture {\n" + fields + method + r'''
 static function check(b:Bool, s:String) if (!b) throw s;
 static function main() {
  check(rememberResolutionDiagnostic('a') && rememberResolutionDiagnostic('b') && !rememberResolutionDiagnostic('a'), 'dedup');
  check(resolutionDiagnostics.join(',') == 'a,b', 'list content');
  // Callers that reset or replace the public list keep working.
  resolutionDiagnostics = [];
  check(rememberResolutionDiagnostic('a'), 'reset list still deduplicated old messages');
  resolutionDiagnostics = ['x'];
  check(!rememberResolutionDiagnostic('x') && rememberResolutionDiagnostic('a'), 'replaced list was not followed');
  resolutionDiagnostics.splice(0, resolutionDiagnostics.length);
  check(rememberResolutionDiagnostic('x'), 'emptied list still deduplicated old messages');
  for (i in 0...MAX_RESOLUTION_DIAGNOSTICS * 2) rememberResolutionDiagnostic('m' + i);
  check(resolutionDiagnostics.length <= MAX_RESOLUTION_DIAGNOSTICS, 'diagnostics grew past the cap');
  Sys.println('OK');
 }
}
'''
        run_haxe(self, {"CharacterFixture": fixture}, "CharacterFixture")
        self.assertNotIn("resolutionDiagnostics.indexOf(", source)


if __name__ == "__main__":
    unittest.main()
