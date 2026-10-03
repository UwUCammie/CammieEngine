"""Psych owner metadata remains available alongside optional compiled stages."""
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
    quote = None
    escaped = False
    index = brace
    while index < len(source):
        char = source[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in ("'", '"'):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
        index += 1
    raise AssertionError(f"unterminated method: {marker}")


class PsychStageJsonOnlyMetadataTest(unittest.TestCase):
    @unittest.skipIf(os.name == 'nt', 'requires a case-sensitive filesystem fixture')
    def test_finds_owner_json_and_executes_compiled_source_when_resolved(self):
        play = (ROOT / "source/PlayState.hx").read_text()
        method = extract_method(play, "function psychStageMetadataPath(")
        self.assertIn("for (directory in ['stages', 'shared/stages'])", method)
        self.assertIn("entry.toLowerCase() != wanted", method)
        self.assertIn("if (match != null)\n\t\t\t\t\treturn null;", method)

        source_resolver = extract_method(play, "function psychCompiledStageSourceForCurrentSong(")
        self.assertIn("selectedPsychSkinRoot()", source_resolver)
        self.assertIn("PsychSourceStageCompat.resolve(ownerRoot, Std.string(SONG.stage))", source_resolver)

        stage_start = extract_method(play, "function startPsychCompiledStage(")
        self.assertIn("new PsychCompiledStageRuntime(ownerRoot, source.modulePath", stage_start)
        self.assertIn("if (!psychCompiledStageRuntime.create())", stage_start)
        self.assertIn("[psych-stage-runtime] executing", stage_start)

        stage_setup_start = play.index("var psychCompiledStageOwner = selectedPsychSkinRoot();")
        stage_setup_end = play.index("setAllHaxeVar('stage', curStage);", stage_setup_start)
        stage_setup = play[stage_setup_start:stage_setup_end]
        self.assertIn("psychCompiledStageOwner != null && psychCompiledStageSource != null", stage_setup)
        self.assertIn("psychCompiledStageCreated = startPsychCompiledStage", stage_setup)
        self.assertIn("if (psychCompiledStageCreated)", stage_setup)
        self.assertIn("applyOwnedPsychStageMetadataOnly(psychCompiledStageOwner)", stage_setup)
        self.assertIn("curStage.applyNativeFallback(SONG.stage, missingStageDiagnostic)", stage_setup)

        fixture = f'''import haxe.io.Path;
import sys.FileSystem;
using StringTools;
class Probe {{
{method}
  public function new() {{}}
  static function main():Void {{
    var root = Sys.args()[0];
    var probe = new Probe();
    var expected = Path.join([root, 'shared/stages/alphaStage.json']);
    if (probe.psychStageMetadataPath(root, 'ALPHASTAGE') != expected)
      throw 'shared stage JSON was not resolved case-insensitively';
    if (probe.psychStageMetadataPath(root, '../alphaStage') != null)
      throw 'unsafe stage ids must not become filesystem paths';
    if (probe.psychStageMetadataPath(root, 'no-stage') != null)
      throw 'an absent stage JSON was reported as present';
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            owner = work / "owner"
            stage_root = owner / "shared/stages"
            stage_root.mkdir(parents=True)
            (stage_root / "alphaStage.json").write_text('{"defaultZoom":0.77}', newline='\n')
            (work / "Probe.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "Probe", str(owner)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("applyOwnedPsychStageMetadataOnly();", play)


if __name__ == "__main__":
    unittest.main()
