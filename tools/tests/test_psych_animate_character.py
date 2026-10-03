"""Psych/Funkadelix Animate character assets stay importable on Linux."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
import os


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


class PsychAnimateCharacterTest(unittest.TestCase):
    def test_source_routes_animate_atlas_through_dis_sprite(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        workflow = (ROOT / "source/ImportWorkflow.hx").read_text()
        self.assertIn("psychAnimateFolder(psychRoot, creation.charjson)", module)
        self.assertIn("char.loadTextureAtlas", module)
        self.assertIn("addByTimelineIndices", module)
        self.assertIn("ensurePsychCharacterRegistryEntry(charcreation.name, charJson, assetRoot, true)", module)
        self.assertIn("assetPath, 'Animation.json'", workflow)
        self.assertIn("lower.endsWith('/animation.json')", workflow)

    def test_animate_folder_lookup_is_case_insensitive_and_read_only(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        methods = "\n".join(
            extract_method(module, marker)
            for marker in (
                "static function isImportFile",
                "static function findChildDirectory",
                "static function existingImportChild",
                "static function psychImageReference",
                "static function psychImageReferences",
                "static function psychImageRoots",
                "static function psychAnimateFolder",
            )
        )
        fixture = f'''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

class Main {{
{methods}
  static function main() {{
    var root = Sys.args()[0];
    var found = psychAnimateFolder(root, {{image:"characters/girlfriend/gf_week2"}});
    if (found == null || !found.toLowerCase().endsWith("characters/girlfriend/gf_week2"))
      throw "Animate folder was not resolved";
    if (!FileSystem.exists(Path.join([found, "Animation.json"])))
      throw "Animate metadata was not detected";
    trace("OK");
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            fixture_path = temp / "Main.hx"
            fixture_path.write_text(fixture, newline='\n')
            (temp / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            root = temp / "donor"
            animate = root / "IMAGES/Characters/Girlfriend/GF_WEEK2"
            animate.mkdir(parents=True)
            (animate / "Animation.json").write_text("{}", newline='\n')
            (animate / "spritemap1.json").write_text("{}", newline='\n')
            before = {path: path.read_bytes() for path in animate.iterdir()}
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "Main", str(root)],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
            )
            after = {path: path.read_bytes() for path in animate.iterdir()}
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
