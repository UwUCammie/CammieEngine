"""Tests for conservative, in-memory recovery of legacy chart JSON."""

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REGRESSION_DONOR_ROOT = Path(
    "/run/media/cammie/External Storage/modding-plus-fnf"
)


def repair_method() -> str:
    source = (ROOT / "source/ModuleFunctions.hx").read_text(encoding="utf-8")
    start = source.index("\tpublic static function repairImportedJsonSeparators(")
    end = source.index("\n\t#if sys", start)
    return source[start:end]


def run_fixture(body: str) -> subprocess.CompletedProcess:
    fixture = "class ImportJsonRepairTest {\n" + repair_method() + body + "\n}\n"
    with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
        path = Path(folder) / "ImportJsonRepairTest.hx"
        path.write_text(fixture, encoding="utf-8")
        return subprocess.run(
            [
                str(ROOT / ".tools/haxe/haxe"),
                "-cp",
                folder,
                "-main",
                "ImportJsonRepairTest",
                "--interp",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )


class ImportJsonRepairTest(unittest.TestCase):
    def test_only_missing_newline_property_separator_is_added(self):
        result = run_fixture(
            '''
\tstatic function main():Void {
\t\tvar broken = '{"song":{"notes":[],"cutsceneType":"fleetway"\\n"needsVoices":true}}';
\t\tvar repaired = repairImportedJsonSeparators(broken);
\t\tvar parsed:Dynamic = haxe.Json.parse(repaired);
\t\tif (parsed.song.cutsceneType != 'fleetway' || parsed.song.needsVoices != true)
\t\t\tthrow 'repaired fields were not preserved';
\t\tvar valid = '{"song":{"notes":[],"speed":3,\\n"needsVoices":true}}';
\t\tif (repairImportedJsonSeparators(valid) != valid)
\t\t\tthrow 'valid JSON was modified';
\t\tvar ambiguous = '{"song":{"notes":[] "needsVoices":true}}';
\t\tif (repairImportedJsonSeparators(ambiguous) != ambiguous)
\t\t\tthrow 'same-line ambiguous input must not be guessed';
\t}
'''
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_chaos_donor_repairs_in_memory_and_remains_unchanged(self):
        donor = REGRESSION_DONOR_ROOT / "assets/data/chaos/chaos.json"
        if not donor.is_file():
            self.skipTest(f"read-only Chaos donor unavailable: {donor}")
        before = donor.read_bytes()
        before_hash = hashlib.sha256(before).hexdigest()
        escaped = json.dumps(str(donor))
        result = run_fixture(
            f'''
\tstatic function main():Void {{
\t\tvar source = sys.io.File.getContent({escaped});
\t\tvar repaired = repairImportedJsonSeparators(source);
\t\tvar parsed:Dynamic = haxe.Json.parse(repaired);
\t\tif (parsed.song.song != "chaos" || parsed.song.cutsceneType != "fleetway"
\t\t\t|| parsed.song.needsVoices != true || parsed.song.notes.length == 0)
\t\t\tthrow "Chaos chart payload changed during repair";
\t}}
'''
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(hashlib.sha256(donor.read_bytes()).hexdigest(), before_hash)


if __name__ == "__main__":
    unittest.main()
