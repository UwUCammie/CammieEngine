"""The private input driver acts only on the requested native marker."""

import importlib.util
import json
import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "drive_offscreen_input", ROOT / "tools/drive_offscreen_input.py")
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


class OffscreenInputTest(unittest.TestCase):
    def test_key_delivery_uses_the_private_display_for_every_xdotool_call(self):
        private = {"DISPLAY": ":317", "PATH": "/usr/bin"}
        responses = [SimpleNamespace(returncode=0, stdout="42\n", stderr="")]
        responses += [SimpleNamespace(returncode=0, stdout="", stderr="") for _ in range(3)]
        with patch.object(driver.subprocess, "run", side_effect=responses) as run, \
             patch.object(driver.time, "sleep"):
            delivered, window, error = driver.send_key("space", 123, private)
        self.assertTrue(delivered, error)
        self.assertEqual(window, "42")
        self.assertEqual(run.call_count, 4)
        self.assertTrue(all(call.kwargs.get("env") is private for call in run.call_args_list))

    def test_marker_requires_exact_event(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "markers.jsonl"
            self.assertFalse(driver.marker_seen(path, "playstate_ready"))
            path.write_text("noise\nRUNTIME_SMOKE|" + json.dumps({"event": "playstate_start"})
                            + "\nRUNTIME_SMOKE|bad-json\n", encoding="utf-8", newline='\n')
            self.assertFalse(driver.marker_seen(path, "playstate_ready"))
            with path.open("a", encoding="utf-8") as stream:
                stream.write("RUNTIME_SMOKE|" + json.dumps({"event": "playstate_ready"}) + "\n")
            self.assertTrue(driver.marker_seen(path, "playstate_ready"))

    @unittest.skipIf(os.name == 'nt', 'uses POSIX shell executable and X11 fixtures')
    def test_game_diagnostics_stream_before_outer_timeout_without_line_corruption(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            scratch = Path(folder)
            fake_bin = scratch / "bin"
            fake_bin.mkdir()
            xdotool = fake_bin / "xdotool"
            xdotool.write_text("#!/bin/sh\nif [ \"$1\" = search ]; then echo 123; fi\nexit 0\n",
                               encoding="utf-8", newline='\n')
            xdotool.chmod(0o755)
            marker_log = scratch / "markers.jsonl"
            child = scratch / "fake_game.py"
            child.write_text('''import json, sys, time
from pathlib import Path
marker = Path(sys.argv[1])
sys.stdout.write("RUNTIME_SMOKE|")
sys.stdout.flush()
time.sleep(0.15)
marker.write_text("RUNTIME_SMOKE|" + json.dumps({"event": "playstate_ready"}) + "\\n")
time.sleep(0.5)
sys.stdout.write(json.dumps({"event": "playstate_ready"}) + "\\n")
sys.stdout.flush()
sys.stdout.write("[hscript-null-access] captured before timeout\\n")
sys.stdout.flush()
time.sleep(30)
''', encoding="utf-8", newline='\n')
            command = [
                sys.executable, str(driver.__file__), "--marker-log", str(marker_log),
                "--key", "Escape", "--delay-seconds", "0", "--",
                sys.executable, str(child), str(marker_log),
            ]
            environment = os.environ.copy()
            environment["DISPLAY"] = ":offscreen-test"
            environment["PATH"] = str(fake_bin) + os.pathsep + environment.get("PATH", "")
            process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True,
                                       encoding="utf-8", errors="replace", env=environment,
                                       start_new_session=True)
            try:
                with self.assertRaises(subprocess.TimeoutExpired):
                    process.communicate(timeout=1.5)
                os.killpg(process.pid, signal.SIGKILL)
                output, _ = process.communicate(timeout=5)
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.communicate(timeout=5)

            self.assertEqual(process.returncode, -signal.SIGKILL)
            self.assertTrue(driver.marker_seen(marker_log, "playstate_ready"))
            lines = output.splitlines()
            input_lines = [line for line in lines if line.startswith("OFFSCREEN_INPUT|")]
            game_markers = [line for line in lines if line.startswith("RUNTIME_SMOKE|")]
            self.assertEqual(len(input_lines), 1, output)
            self.assertTrue(json.loads(input_lines[0].split("|", 1)[1])["delivered"], output)
            self.assertEqual(len(game_markers), 1, output)
            self.assertEqual(json.loads(game_markers[0].split("|", 1)[1])["event"],
                             "playstate_ready")
            self.assertLess(lines.index(input_lines[0]), lines.index(game_markers[0]), output)
            self.assertIn("[hscript-null-access] captured before timeout", output)

    @unittest.skipIf(os.name == 'nt', 'uses POSIX shell executable and X11 fixtures')
    def test_dialogue_repeat_and_post_song_input_have_separate_triggers(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            scratch = Path(folder)
            fake_bin = scratch / "bin"
            fake_bin.mkdir()
            xdotool = fake_bin / "xdotool"
            xdotool.write_text('#!/bin/sh\nif [ "$1" = search ]; then echo 123; fi\nexit 0\n', newline='\n')
            xdotool.chmod(0o755)
            marker_log = scratch / "markers.jsonl"
            child = scratch / "fake_game.py"
            child.write_text('''import json, sys, time
from pathlib import Path
marker = Path(sys.argv[1])
for event in ('playstate_ready', 'song_start', 'song_end'):
    with marker.open('a') as stream:
        stream.write('RUNTIME_SMOKE|' + json.dumps({'event': event}) + '\\n')
    time.sleep(0.4)
''', newline='\n')
            command = [sys.executable, str(driver.__file__), '--marker-log', str(marker_log),
                       '--repeat-key', 'Return', '--repeat-start-delay-seconds', '0',
                       '--repeat-interval-seconds', '0.25', '--post-key', 'Return',
                       '--post-delay-seconds', '0', '--', sys.executable, str(child),
                       str(marker_log)]
            environment = os.environ.copy()
            environment['DISPLAY'] = ':offscreen-test'
            environment['PATH'] = str(fake_bin) + os.pathsep + environment.get('PATH', '')
            result = subprocess.run(command, capture_output=True, text=True,
                                    env=environment, timeout=5)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            inputs = [json.loads(line.split('|', 1)[1]) for line in result.stdout.splitlines()
                      if line.startswith('OFFSCREEN_INPUT|')]
            self.assertTrue(any(item['trigger'] == 'repeat until song_start'
                                and item['delivered'] for item in inputs), inputs)
            self.assertEqual(sum(item['trigger'] == 'song_end' and item['delivered']
                                 for item in inputs), 1, inputs)


if __name__ == "__main__":
    unittest.main()
