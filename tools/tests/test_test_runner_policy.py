import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import run_tests


class TestRunnerPolicyTests(unittest.TestCase):
    def test_default_reserves_two_nested_compiler_threads_per_worker(self):
        with patch.object(run_tests.os, "cpu_count", return_value=16):
            self.assertEqual(run_tests.default_jobs(), 8)
        with patch.object(run_tests.os, "cpu_count", return_value=32):
            self.assertEqual(run_tests.default_jobs(), 16)

    def test_default_scales_down_on_small_or_unknown_hosts(self):
        with patch.object(run_tests.os, "cpu_count", return_value=4):
            self.assertEqual(run_tests.default_jobs(), 2)
        with patch.object(run_tests.os, "cpu_count", return_value=1):
            self.assertEqual(run_tests.default_jobs(), 1)
        with patch.object(run_tests.os, "cpu_count", return_value=None):
            self.assertEqual(run_tests.default_jobs(), 1)

    def test_nested_compiler_threads_scale_with_actual_worker_count(self):
        with patch.object(run_tests.os, "cpu_count", return_value=16):
            self.assertEqual(run_tests.nested_hxcpp_compile_threads(8), 2)
            self.assertEqual(run_tests.nested_hxcpp_compile_threads(16), 1)
        with patch.object(run_tests.os, "cpu_count", return_value=1):
            self.assertEqual(run_tests.nested_hxcpp_compile_threads(1), 1)

    def test_environment_applies_budget_and_preserves_explicit_compiler_threads(self):
        with tempfile.TemporaryDirectory() as short_tmp:
            parent = {"CAMMIE_TEST_TMP": short_tmp}
            with patch.object(run_tests.os, "cpu_count", return_value=16):
                environment = run_tests.offscreen_test_environment(parent, jobs=8)
                self.assertEqual(environment["HXCPP_COMPILE_THREADS"], "2")
                parent["HXCPP_COMPILE_THREADS"] = "5"
                environment = run_tests.offscreen_test_environment(parent, jobs=16)
                self.assertEqual(environment["HXCPP_COMPILE_THREADS"], "5")

    def test_runner_passes_actual_worker_count_to_each_module(self):
        with tempfile.TemporaryDirectory() as directory:
            tests = Path(directory)
            (tests / "test_first.py").write_text("# fixture\n", newline="\n")
            (tests / "test_second.py").write_text("# fixture\n", newline="\n")
            received_jobs = []
            successful_result = SimpleNamespace(
                returncode=0, stderr="Ran 1 test in 0.0s\n", stdout="")

            def run_fake_module(path, jobs):
                received_jobs.append(jobs)
                return path, successful_result, 0.0

            output = io.StringIO()
            errors = io.StringIO()
            with patch.object(run_tests, "TESTS", tests), \
                 patch.object(run_tests, "load_timings", return_value={}), \
                 patch.object(run_tests, "save_timings"), \
                 patch.object(run_tests, "run_module", side_effect=run_fake_module), \
                 patch.object(run_tests.sys, "argv", ["run_tests.py", "--jobs", "16"]), \
                 redirect_stdout(output), redirect_stderr(errors):
                code = run_tests.main()

        self.assertEqual(code, 0, errors.getvalue())
        self.assertEqual(received_jobs, [2, 2])
        self.assertIn("2 tests across 2 modules", output.getvalue())


if __name__ == "__main__":
    unittest.main()
