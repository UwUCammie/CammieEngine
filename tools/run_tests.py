#!/usr/bin/env python3
"""Run independent unittest modules in parallel without scanning game media."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path
import re
import subprocess
import sys
import time


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
    return environment


def run_module(path):
    start = time.monotonic()
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(TESTS),
         "-p", path.name],
        cwd=ROOT, text=True, capture_output=True,
        env=offscreen_test_environment(),
    )
    return path, result, time.monotonic() - start


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=4,
                        help="test modules to run at once (default: 4)")
    parser.add_argument("--pattern", default="test_*.py",
                        help="module filename glob (default: test_*.py)")
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")
    modules = sorted(TESTS.glob(args.pattern))
    if not modules:
        parser.error("no test modules match --pattern")
    start = time.monotonic()
    failures = []
    tests_run = 0
    tests_skipped = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        pending = {pool.submit(run_module, path): path for path in modules}
        for future in as_completed(pending):
            path, result, elapsed = future.result()
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
    print(f"{tests_run} tests across {len(modules)} modules in "
          f"{time.monotonic() - start:.1f}s; {tests_skipped} skipped, "
          f"{len(failures)} failed")
    if failures:
        print("Failed modules: " + ", ".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
