"""Linux path coverage for case conventions used by imported legacy engines."""

from pathlib import Path
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
                return source[start : index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class LegacyAssetCasePathTest(unittest.TestCase):
    def test_paths_resolve_windows_case_spelling_on_native_disk(self):
        source = (ROOT / "source/Paths.hx").read_text()
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "inline static function getPreloadPath",
                "static function resolveCaseInsensitivePath",
            )
        )
        fixture = f'''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
class OpenFlAssets {{
    public static function exists(path:String, ?type:Dynamic):Bool return false;
}}
class PathsCaseFixture {{
    static var caseResolvedPaths:Map<String, String> = new Map();
{methods}
    static function main() {{
        var preload = getPreloadPath("images/ALLEY/WHITTYBACK.png");
        if (preload != "assets/images/alley/whittyBack.png")
            throw "preload path did not use the resolver: " + preload;
        var back = resolveCaseInsensitivePath("assets/IMAGES/ALLEY/WHITTYBACK.PNG");
        if (back != "assets/images/alley/whittyBack.png")
            throw "wrong case-resolved path: " + back;
        var front = resolveCaseInsensitivePath("assets/images/alley/whittyfront.png");
        if (Path.withoutDirectory(front) != "whittyFront.png")
            throw "nested case mismatch was not resolved: " + front;
        var exact = resolveCaseInsensitivePath("assets/images/alley/whittyBack.png");
        if (exact != "assets/images/alley/whittyBack.png")
            throw "exact path was changed: " + exact;
        var missing = resolveCaseInsensitivePath("assets/images/alley/not-present.png");
        if (missing != "assets/images/alley/not-present.png")
            throw "missing path should remain authored: " + missing;
        File.saveContent("assets/images/alley/Not-Present.png", "late import");
        var importedLater = resolveCaseInsensitivePath("assets/images/alley/not-present.png");
        if (importedLater != "assets/images/alley/Not-Present.png")
            throw "a previously missing path was cached across import: " + importedLater;
        var ambiguous = resolveCaseInsensitivePath("assets/images/alley/icon.png");
        if (ambiguous != "assets/images/alley/icon.png")
            throw "ambiguous case-folded path should not be guessed: " + ambiguous;
        FileSystem.deleteFile("assets/images/alley/whittyBack.png");
        var removed = resolveCaseInsensitivePath("assets/images/alley/WHITTYBACK.png");
        if (removed != "assets/images/alley/WHITTYBACK.png")
            throw "stale successful resolution remained cached: " + removed;
    }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "assets/images/alley").mkdir(parents=True)
            (root / "assets/images/alley/whittyBack.png").write_bytes(b"back")
            (root / "assets/images/alley/whittyFront.png").write_bytes(b"front")
            (root / "assets/images/alley/Icon.png").write_bytes(b"first")
            (root / "assets/images/alley/iCON.png").write_bytes(b"second")
            (root / "PathsCaseFixture.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder,
                 "-main", "PathsCaseFixture", "--interp"],
                cwd=folder,
                capture_output=True,
                text=True,
                timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_fps_plus_stage_keeps_windows_case_convention(self):
        donor = Path("/run/media/cammie/External Storage/FNF-Example-Mods/whitty")
        script = donor / "data/stages/alley.hxc"
        if not script.is_file():
            self.skipTest(f"mounted FPS Plus fixture unavailable: {script}")
        source = script.read_text()
        self.assertIn('Paths.image("alley/whittyback")', source)
        self.assertIn('Paths.image("alley/whittyfront")', source)
        self.assertTrue((donor / "images/alley/whittyBack.png").is_file())
        self.assertTrue((donor / "images/alley/whittyFront.png").is_file())
        self.assertFalse((donor / "images/alley/whittyback.png").exists())
        self.assertFalse((donor / "images/alley/whittyfront.png").exists())


if __name__ == "__main__":
    unittest.main()
