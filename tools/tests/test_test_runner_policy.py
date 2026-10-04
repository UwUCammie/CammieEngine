import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import run_tests


class TestRunnerPolicyTests(unittest.TestCase):
    def test_default_uses_available_logical_cpus_up_to_sixteen(self):
        with patch.object(run_tests.os, "cpu_count", return_value=16):
            self.assertEqual(run_tests.default_jobs(), 16)
        with patch.object(run_tests.os, "cpu_count", return_value=32):
            self.assertEqual(run_tests.default_jobs(), 16)

    def test_default_scales_down_on_small_or_unknown_hosts(self):
        with patch.object(run_tests.os, "cpu_count", return_value=4):
            self.assertEqual(run_tests.default_jobs(), 4)
        with patch.object(run_tests.os, "cpu_count", return_value=None):
            self.assertEqual(run_tests.default_jobs(), 1)


if __name__ == "__main__":
    unittest.main()
