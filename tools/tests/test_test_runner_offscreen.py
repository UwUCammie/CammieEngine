"""The parallel test runner must not inherit the user's desktop display."""

import importlib.util
import io
from pathlib import Path
from haxe_test_support import FixturePath as Path
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
            self.assertEqual(Path(environment[name]), ROOT / "tmp")
        for name in ("DISPLAY", "WAYLAND_DISPLAY", "WAYLAND_SOCKET",
                     "XAUTHORITY", "XDG_RUNTIME_DIR"):
            self.assertNotIn(name, environment)
        self.assertEqual(parent["DISPLAY"], ":0")

    def test_timing_hints_reorder_without_omitting_new_modules(self):
        modules = [Path('test_short.py'), Path('test_new.py'), Path('test_native.py')]
        scheduled = RUN_TESTS.schedule_modules(modules, {'test_native.py': 60, 'test_short.py': 1})
        self.assertEqual(scheduled, [modules[2], modules[0], modules[1]])
        self.assertCountEqual(scheduled, modules)

    def test_missing_corrupt_or_unwritable_timing_hints_do_not_fail_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            hints = Path(directory) / 'timings.json'
            with patch.object(RUN_TESTS, 'timing_path', return_value=hints):
                self.assertEqual(RUN_TESTS.load_timings(), {})
                hints.write_text('broken json')
                self.assertEqual(RUN_TESTS.load_timings(), {})
                RUN_TESTS.save_timings({'test_fixture.py': 3})
                self.assertEqual(RUN_TESTS.load_timings(), {'test_fixture.py': 3})
                with patch.object(RUN_TESTS.os, 'replace', side_effect=PermissionError):
                    RUN_TESTS.save_timings({'test_fixture.py': 10})
                self.assertEqual(RUN_TESTS.load_timings(), {'test_fixture.py': 3})

    def test_empty_test_module_fails_the_suite(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "test_empty.py").write_text("# No test cases here.\n", newline='\n')
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
