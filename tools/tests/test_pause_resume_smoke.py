"""Focused validation for the per-chart offscreen pause/resume runner."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"


def load_runner():
    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))
    spec = importlib.util.spec_from_file_location(
        "pause_resume_smoke_runner", TOOLS / "run_pause_resume_smoke.py"
    )
    if spec is None or spec.loader is None:
        raise AssertionError("could not load the pause/resume smoke runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PauseResumeSmokeTest(unittest.TestCase):
    def test_runner_requests_strict_script_diagnostics_for_each_chart(self):
        runner = load_runner()
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            isolated_root = Path(folder)
            (isolated_root / ".tools").mkdir()
            binary = isolated_root / "bin" / "Funkin"
            binary.parent.mkdir()
            output_path = isolated_root / "pause.json"
            output_path.write_text("{}", encoding="utf-8")

            def fake_run_case(*_args, **kwargs):
                self.assertIs(kwargs.get("strict_diagnostics"), True)
                self.assertEqual(kwargs.get("timeout_seconds"), 205)
                log = isolated_root / "tmp/runtime-smoke/logs/pause-resume.process.log"
                log.parent.mkdir(parents=True, exist_ok=True)
                log.write_text(
                    'OFFSCREEN_INPUT|{"key":"Escape","delivered":true}\n'
                    'OFFSCREEN_INPUT|{"key":"Return","delivered":true}\n'
                    'RUNTIME_SMOKE|{"event":"pause_open","musicPlaying":false,"musicTimeMs":5000}\n'
                    'RUNTIME_SMOKE|{"event":"pause_resume","musicPlaying":true,"musicTimeMs":5000}\n',
                    encoding="utf-8",
                )
                return {"status": "failed", "reason": "native script diagnostic"}

            with patch.object(runner, "ROOT", isolated_root), \
                    patch.object(runner, "DEFAULT_BINARY", binary), \
                    patch.object(runner, "run_case", side_effect=fake_run_case), \
                    patch.object(sys, "argv", [
                        "run_pause_resume_smoke.py", "owned-song", "owned-song-hard", "hard",
                        "--output", str(output_path),
                    ]):
                self.assertEqual(runner.main(), 1)

            receipt = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "failed")
            self.assertEqual(receipt["problems"], ["native script diagnostic"])


if __name__ == "__main__":
    unittest.main()
