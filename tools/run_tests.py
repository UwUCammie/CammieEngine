#!/usr/bin/env python3
"""Run independent unittest modules in parallel without scanning game media."""

import argparse
import hashlib
import json
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tools" / "tests"


def offscreen_test_environment(parent=None):
    """Keep test modules detached from the user's desktop display.

    Native smoke helpers start their own Xvfb server when they need a screen.
    """
    environment = dict(os.environ if parent is None else parent)
    task_tmp = ROOT / "tmp"
    task_tmp.mkdir(exist_ok=True)
    for name in ("TMPDIR", "TMP", "TEMP"):
        environment[name] = str(task_tmp)
    for name in ("DISPLAY", "WAYLAND_DISPLAY", "WAYLAND_SOCKET",
                 "XAUTHORITY", "XDG_RUNTIME_DIR"):
        environment.pop(name, None)
    environment['PYTHONUTF8'] = '1'
    environment['PYTHONIOENCODING'] = 'utf-8'
    paths = [str(ROOT), str(ROOT / 'tools'), str(TESTS)]
    if environment.get('PYTHONPATH'):
        paths.append(environment['PYTHONPATH'])
    environment['PYTHONPATH'] = os.pathsep.join(paths)
    if os.name == 'nt':
        # Haxe eval has MAX_PATH limits even though the game's patched hxcpp
        # runtime supports long paths. Transaction fixtures need short roots.
        key = hashlib.sha256(str(ROOT).encode('utf-8')).hexdigest()[:8]
        short_tmp = Path(environment.get('CAMMIE_TEST_TMP', str(Path(ROOT.anchor) / 'tmp' / ('ce-' + key))))
        short_tmp.mkdir(parents=True, exist_ok=True)
        environment['CAMMIE_TEST_TMP'] = str(short_tmp)
    return environment


def run_module(path):
    start = time.monotonic()
    result = subprocess.run(
        [sys.executable, '-X', 'utf8', str(ROOT / 'tools/run_tests.py'),
         '--module', path.name],
        cwd=ROOT, text=True, capture_output=True,
        env=offscreen_test_environment(),
    )
    return path, result, time.monotonic() - start


class FixtureResult(unittest.TextTestResult):
    def addError(self, test, error):
        # Skip only a missing Windows symlink-fixture capability. Other
        # filesystem errors and all assertion failures remain failures.
        if os.name == 'nt' and isinstance(error[1], OSError) and getattr(error[1], 'winerror', None) == 1314:
            self.addSkip(test, 'symlink fixtures require Windows Developer Mode or elevation')
            return
        super().addError(test, error)


def run_single_module(name):
    sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(TESTS)]
    suite = unittest.defaultTestLoader.discover(str(TESTS), pattern=name)
    result = unittest.TextTestRunner(resultclass=FixtureResult).run(suite)
    for test, reason in result.skipped:
        print(f'SKIP {test.id()}: {reason}')
    return 0 if result.wasSuccessful() else 1


def default_jobs():
    # Each module keeps its own interpreter for fixture/global-state isolation.
    # Cap fanout so large workstations do not spawn an unbounded compiler herd.
    return min(16, max(1, os.cpu_count() or 1))


def timing_path():
    return ROOT / '.tools' / 'test-module-times.json'


def load_timings():
    try:
        data = json.loads(timing_path().read_text())
        return {name: float(seconds) for name, seconds in data.items()
                if isinstance(seconds, (int, float)) and 0 <= seconds < 86400}
    except (OSError, ValueError, TypeError, AttributeError):
        return {}


def schedule_modules(modules, timings):
    # Start expensive probes first, preventing a single late native compile
    # from holding up the completed suite. Timings never skip tests.
    return sorted(modules, key=lambda path: (-timings.get(path.name, 0), path.name))


def save_timings(timings):
    path = timing_path()
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as handle:
            temporary = handle.name
            json.dump(timings, handle)
        os.replace(temporary, path)
    except OSError:
        # Performance hints must never determine suite success.
        pass
    finally:
        if temporary:
            try:
                Path(temporary).unlink(missing_ok=True)
            except OSError:
                pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=default_jobs(),
                        help="modules at once (default: up to 16, limited by logical CPUs)")
    parser.add_argument("--pattern", default="test_*.py",
                        help="module filename glob (default: test_*.py)")
    parser.add_argument('--module', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.module:
        if Path(args.module).name != args.module or not args.module.startswith('test_') or not args.module.endswith('.py'):
            parser.error('--module must be a test module filename')
        return run_single_module(args.module)
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")
    modules = sorted(TESTS.glob(args.pattern))
    if not modules:
        parser.error("no test modules match --pattern")
    timings = load_timings()
    modules = schedule_modules(modules, timings)
    start = time.monotonic()
    failures = []
    tests_run = 0
    tests_skipped = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        pending = {pool.submit(run_module, path): path for path in modules}
        for future in as_completed(pending):
            path, result, elapsed = future.result()
            timings[path.name] = elapsed
            match = re.search(r"Ran (\d+) tests? in", result.stderr)
            module_tests = int(match.group(1)) if match else 0
            tests_run += module_tests
            skipped = re.search(r"skipped=(\d+)", result.stderr)
            if skipped:
                tests_skipped += int(skipped.group(1))
            if result.returncode or module_tests == 0:
                failures.append(path.name)
                print(f"FAIL {path.name} ({elapsed:.1f}s)", flush=True)
                if module_tests == 0:
                    print("No tests were discovered in this module.", file=sys.stderr)
                print(result.stdout, end="")
                print(result.stderr, end="", file=sys.stderr)
            else:
                print(f"OK   {path.name} ({elapsed:.1f}s)", flush=True)
                for line in result.stdout.splitlines():
                    if line.startswith('SKIP '):
                        print(line, flush=True)
    save_timings(timings)
    print(f"{tests_run} tests across {len(modules)} modules in "
          f"{time.monotonic() - start:.1f}s; {tests_skipped} skipped, "
          f"{len(failures)} failed")
    if failures:
        print("Failed modules: " + ", ".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
