"""The parallel test runner must not inherit the user's desktop display."""

import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stderr, redirect_stdout


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("run_tests", ROOT / "tools/run_tests.py")
RUN_TESTS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUN_TESTS)


class TestRunnerOffscreen(unittest.TestCase):
    def test_module_launch_removes_desktop_display_variables(self):
        parent = {
            "DISPLAY": ":0",
            "WAYLAND_DISPLAY": "wayland-0",
            "WAYLAND_SOCKET": "4",
            "XAUTHORITY": "/tmp/desktop-auth",
            "XDG_RUNTIME_DIR": "/run/user/1000",
            "KEEP_ME": "yes",
        }
        with patch.dict(RUN_TESTS.os.environ, parent, clear=True):
            with patch.object(RUN_TESTS.subprocess, "run") as launch:
                launch.return_value.returncode = 0
                RUN_TESTS.run_module(Path("test_fake.py"))
        environment = launch.call_args.kwargs["env"]
        self.assertEqual(environment["KEEP_ME"], "yes")
        for name in ("TMPDIR", "TMP", "TEMP"):
            self.assertEqual(environment[name], str(ROOT / "tmp"))
        for name in ("DISPLAY", "WAYLAND_DISPLAY", "WAYLAND_SOCKET",
                     "XAUTHORITY", "XDG_RUNTIME_DIR"):
            self.assertNotIn(name, environment)
        self.assertEqual(parent["DISPLAY"], ":0")

    def test_empty_test_module_fails_the_suite(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "test_empty.py").write_text("# No test cases here.\n")
            output = io.StringIO()
            errors = io.StringIO()
            with patch.object(RUN_TESTS, "TESTS", folder), \
                 patch.object(RUN_TESTS.sys, "argv", ["run_tests.py", "--pattern", "test_empty.py"]), \
                 redirect_stdout(output), redirect_stderr(errors):
                code = RUN_TESTS.main()
        self.assertEqual(code, 1)
        self.assertIn("No tests were discovered", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
