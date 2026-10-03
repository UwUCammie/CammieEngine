"""Import-time classification for legacy absolute camera target intros."""
from haxe_test_support import HAXE_COMMAND

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
DONOR_ROOT = Path("/run/media/cammie/External Storage/modding-plus-fnf")


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    quote = None
    escaped = False
    for index in range(brace, len(source)):
        char = source[index]
        if quote is not None:
            if char == quote and not escaped:
                quote = None
            escaped = char == "\\" and not escaped
            if char != "\\":
                escaped = False
            continue
        if char in ("'", '"'):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class ImportedCameraZoomMetadataTest(unittest.TestCase):
    def _run(self, body: str) -> subprocess.CompletedProcess:
        source = (ROOT / "source/ModuleFunctions.hx").read_text(encoding="utf-8")
        methods = "\n".join(
            [
                extract_method(source, "public static function importedCameraZoomMode"),
                extract_method(source, "public static function repairImportedJsonSeparators"),
            ]
        )
        fixture = "using StringTools;\nclass CameraZoomMetadataTest {\n" + methods + body + "\n}\n"
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "CameraZoomMetadataTest.hx"
            path.write_text(fixture, encoding="utf-8", newline='\n')
            return subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "CameraZoomMetadataTest", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

    def test_target_sequence_is_distinct_from_additive_pulse(self):
        result = self._run(
            '''
\tstatic function main():Void {
\t\tvar locked:Dynamic = haxe.Json.parse('{"notes":[{"sectionNotes":[[12000,0,0]]}],'
\t\t\t+ '"events":[[0,[["Add Camera Zoom","0.5","0.5"]]],'
\t\t\t+ '[2500,[["AddCameraZoom","0.6","0.6"]]]]}');
\t\tif (importedCameraZoomMode(locked) != 'absolute-target-intro')
\t\t\tthrow 'absolute target intro was not classified';
\t\tvar pulse:Dynamic = haxe.Json.parse('{"notes":[{"sectionNotes":[[100,0,0]]}],'
\t\t\t+ '"events":[[0,[["Add Camera Zoom","0.060","0.030"]]]]}');
\t\tif (importedCameraZoomMode(pulse) != '')
\t\t\tthrow 'ordinary additive pulse was reclassified';
\t}
'''
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_locked_donor_is_classified_without_mutation(self):
        donor = DONOR_ROOT / "assets/data/locked/locked.json"
        if not donor.is_file():
            self.skipTest(f"read-only Locked donor unavailable: {donor}")
        before = donor.read_bytes()
        digest = hashlib.sha256(before).hexdigest()
        donor_literal = json.dumps(str(donor))
        result = self._run(
            f'''
\tstatic function main():Void {{
\t\tvar raw = sys.io.File.getContent({donor_literal});
\t\tvar parsed:Dynamic = haxe.Json.parse(repairImportedJsonSeparators(raw));
\t\tif (importedCameraZoomMode(parsed.song) != 'absolute-target-intro')
\t\t\tthrow 'Locked donor convention was not classified';
\t}}
'''
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(hashlib.sha256(donor.read_bytes()).hexdigest(), digest)

    def test_runtime_prefers_import_metadata_and_keeps_diagnostic_fallback(self):
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        start = play_state.index("\tfunction detectCameraZoomIntroTargets():Void")
        end = play_state.index("\n\tprivate static function sectionHasCrossFade", start)
        resolver = play_state[start:end]
        self.assertIn("Reflect.field(compatibilityMetadata, 'cameraZoomMode')", resolver)
        self.assertIn("mode == 'absolute-target-intro'", resolver)
        self.assertIn("cameraZoomIntroUsesTargets(", resolver)
        self.assertIn("[camera-zoom-mode-inferred]", resolver)


if __name__ == "__main__":
    unittest.main()
