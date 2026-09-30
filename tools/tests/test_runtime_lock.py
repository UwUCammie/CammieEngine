from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class RuntimeLockTest(unittest.TestCase):
    def test_build_waits_until_execed_game_exits(self):
        with tempfile.TemporaryDirectory() as folder:
            args = [str(ROOT / 'tools/runtime_lock.sh'), str(Path(folder) / 'runtime.lock')]
            holder = subprocess.Popen(
                ['bash', '-c', 'source "$1"; lock_runtime "$2"; '
                 'exec python3 -u -c \'import sys; print("running"); sys.stdin.read()\'',
                 'test', *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True)
            contender = None
            try:
                self.assertEqual(holder.stdout.readline().strip(), 'running')
                contender = subprocess.Popen(
                    ['bash', '-c', 'source "$1"; lock_runtime "$2"; echo acquired',
                     'test', *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                self.assertIn('waiting for the running game', contender.stdout.readline())
                self.assertIsNone(contender.poll())
                holder.stdin.close()
                self.assertEqual(holder.wait(timeout=5), 0)
                output, error = contender.communicate(timeout=5)
                self.assertEqual(contender.returncode, 0, error)
                self.assertEqual(output.strip(), 'acquired')
            finally:
                for process in [holder, contender]:
                    if process is None:
                        continue
                    if process.poll() is None:
                        process.kill()
                        process.wait()
                    for pipe in [process.stdin, process.stdout, process.stderr]:
                        if pipe is not None:
                            pipe.close()


if __name__ == '__main__':
    unittest.main()
