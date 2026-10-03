"""Clean-install and repeat-run coverage for the shared hscript patcher."""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
PATCHER = ROOT / "tools/patch_hscript_compat.py"
FIXTURE = ROOT / "tools/tests/fixtures/hscript-2.5.0-Interp.hx"


class HscriptCompatPatchTest(unittest.TestCase):
    def test_clean_pinned_source_gets_all_runtime_and_compile_helpers(self):
        original = FIXTURE.read_text(encoding="utf-8")
        self.assertNotIn("hscript-null-access", original)
        self.assertNotIn("dpFloatAwareArith", original)

        with tempfile.TemporaryDirectory(prefix="hscript-compat-") as folder:
            interp = Path(folder) / "hscript" / "Interp.hx"
            interp.parent.mkdir(parents=True)
            shutil.copyfile(FIXTURE, interp)

            command = [sys.executable, str(PATCHER), "--path", str(interp)]
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            patched = interp.read_text(encoding="utf-8")

            for marker in (
                "function nullAccessDiagnose",
                "function nullOperandDiagnose",
                "var nullOperandSeen : Bool;",
                "function dpFloatAwareArith",
                "hscript-null-iterator",
                "hscript-int-iterator",
                "hscript-null-fcall",
                "hscript-null-ecall",
                "hscript-null-earray",
                "hscript-null-assignop",
                "hscript-stop-safe-enum",
            ):
                with self.subTest(marker=marker):
                    self.assertIn(marker, patched)

            self.assertEqual(patched.count("function nullAccessDiagnose"), 1)
            self.assertEqual(patched.count("function nullOperandDiagnose"), 1)
            self.assertEqual(patched.count("function dpFloatAwareArith"), 1)

            # These are the inherited-code consumers that failed on Windows
            # before the pinned hscript source was patched during setup.
            self.assertIn("nullAccessDiagnose(\"index\"", patched)
            self.assertIn("me.nullOperandDiagnose(\"+\")", patched)
            self.assertIn("me.dpFloatAwareArith(\"%\", a, b)", patched)

            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertEqual(interp.read_text(encoding="utf-8"), patched)

    def test_both_build_scripts_run_the_shared_patcher_before_compile(self):
        linux = (ROOT / "run.sh").read_text(encoding="utf-8")
        windows = (ROOT / "run.bat").read_text(encoding="utf-8")
        self.assertIn("python3 tools/patch_hscript_compat.py", linux)
        self.assertIn("tools\\patch_hscript_compat.py", windows)


if __name__ == "__main__":
    unittest.main()
