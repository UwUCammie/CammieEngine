"""Tests for persistent native fixture cache coordination and recovery."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from native_fixture_cache import _replace_with_retry, fingerprint_key, get_or_build
from windows_native_import_fixture import _capture_engine_sources, _tree_identity


class NativeFixtureCacheTest(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt', 'Windows directory junctions')
    def test_junction_namespace_is_rejected_without_symlink_privilege(self):
        import _winapi
        outside = self.root / 'outside-junction-target'
        outside.mkdir()
        sentinel = outside / 'must-survive.bin'
        sentinel.write_bytes(b'unchanged target')
        self.cache.mkdir()
        _winapi.CreateJunction(str(outside), str(self.cache / 'import-windows'))
        with self.assertRaisesRegex(ValueError, 'namespace cannot'):
            get_or_build(self.cache, {'fixture': 'junction-namespace'}, 'fixture.exe',
                         self._builder(b'unused', []))
        self.assertEqual(sentinel.read_bytes(), b'unchanged target')

    @unittest.skipUnless(os.name == 'nt', 'Windows directory junctions')
    def test_junction_entry_and_stale_stage_do_not_delete_external_contents(self):
        import _winapi
        outside = self.root / 'outside-junction-target'
        outside.mkdir()
        sentinel = outside / 'must-survive.bin'
        sentinel.write_bytes(b'unchanged target')
        fingerprint = {'fixture': 'junction-entry'}
        key = fingerprint_key(fingerprint)
        namespace = self.cache / 'import-windows'
        namespace.mkdir(parents=True)
        _winapi.CreateJunction(str(outside), str(namespace / key))
        _winapi.CreateJunction(str(outside), str(namespace / ('.building-' + key + '-stale')))
        calls = []
        built = get_or_build(self.cache, fingerprint, 'cpp/fixture.exe',
                             self._builder(b'owned fixture', calls))
        self.assertFalse(built.reused)
        self.assertEqual(len(calls), 1)
        self.assertEqual(sentinel.read_bytes(), b'unchanged target')
        self.assertEqual(built.executable.read_bytes(), b'owned fixture')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cache = self.root / "cache"

    def tearDown(self):
        self.temp.cleanup()

    def _builder(self, output: bytes, calls: list[int]):
        def build(staging: Path) -> Path:
            calls.append(1)
            executable = staging / "cpp/fixture.exe"
            executable.parent.mkdir(parents=True)
            executable.write_bytes(output)
            return executable
        return build

    @staticmethod
    def _winerror(code: int) -> OSError:
        error = PermissionError(code, "simulated transient Windows rename lock")
        error.winerror = code
        return error

    def test_windows_rename_retries_transient_access_and_sharing_locks(self):
        source = self.root / "rename-source"
        destination = self.root / "rename-destination"
        source.write_bytes(b"owned cache entry")
        failures = [self._winerror(5), self._winerror(32), self._winerror(33)]
        calls = []
        elapsed = [0.0]

        def replace(source_path: Path, destination_path: Path) -> None:
            calls.append((source_path, destination_path))
            if failures:
                raise failures.pop(0)
            os.replace(source_path, destination_path)

        def sleep(seconds: float) -> None:
            elapsed[0] += seconds

        _replace_with_retry(source, destination, replace=replace, windows=True,
                            retry_window_seconds=1.0,
                            monotonic=lambda: elapsed[0], sleep=sleep)

        self.assertEqual(len(calls), 4)
        self.assertGreater(elapsed[0], 0)
        self.assertFalse(source.exists())
        self.assertEqual(destination.read_bytes(), b"owned cache entry")

    def test_windows_rename_preserves_permanent_and_expired_errors(self):
        source = self.root / "blocked-source"
        destination = self.root / "blocked-destination"
        source.write_bytes(b"still owned")
        permanent = self._winerror(5)
        calls = []
        elapsed = [0.0]

        def blocked_replace(source_path: Path, destination_path: Path) -> None:
            calls.append((source_path, destination_path))
            raise permanent

        def sleep(seconds: float) -> None:
            elapsed[0] += seconds

        with self.assertRaises(OSError) as raised:
            _replace_with_retry(source, destination, replace=blocked_replace, windows=True,
                                retry_window_seconds=0.06,
                                monotonic=lambda: elapsed[0], sleep=sleep)

        self.assertIs(raised.exception, permanent)
        self.assertGreater(len(calls), 1)
        self.assertLessEqual(elapsed[0], 0.061)
        self.assertTrue(source.exists())
        self.assertFalse(destination.exists())

    def test_non_windows_rename_does_not_retry_windows_errors(self):
        failure = self._winerror(32)
        calls = []

        def blocked_replace(source_path: Path, destination_path: Path) -> None:
            calls.append((source_path, destination_path))
            raise failure

        with self.assertRaises(OSError) as raised:
            _replace_with_retry(self.root / "source", self.root / "destination",
                                replace=blocked_replace, windows=False,
                                monotonic=lambda: 0.0, sleep=lambda _: self.fail("unexpected retry"))

        self.assertIs(raised.exception, failure)
        self.assertEqual(len(calls), 1)

    def test_unrecognized_windows_rename_error_is_propagated_immediately(self):
        failure = self._winerror(87)
        calls = []

        def blocked_replace(source_path: Path, destination_path: Path) -> None:
            calls.append((source_path, destination_path))
            raise failure

        with self.assertRaises(OSError) as raised:
            _replace_with_retry(self.root / "source", self.root / "destination",
                                replace=blocked_replace, windows=True,
                                monotonic=lambda: 0.0, sleep=lambda _: self.fail("unexpected retry"))

        self.assertIs(raised.exception, failure)
        self.assertEqual(len(calls), 1)

    def test_fingerprint_is_canonical_and_changes_with_build_inputs(self):
        self.assertEqual(fingerprint_key({"a": 1, "b": 2}), fingerprint_key({"b": 2, "a": 1}))
        self.assertNotEqual(fingerprint_key({"stubSha256": "one"}),
                            fingerprint_key({"stubSha256": "two"}))

        calls = []
        first = get_or_build(self.cache, {"stubSha256": "one"}, "cpp/fixture.exe",
                             self._builder(b"first source image", calls))
        second = get_or_build(self.cache, {"stubSha256": "two"}, "cpp/fixture.exe",
                              self._builder(b"changed source image", calls))
        self.assertNotEqual(first.key, second.key)
        self.assertEqual(len(calls), 2)

    def test_build_publishes_ready_manifest_and_hit_verifies_executable_hash(self):
        calls = []
        fingerprint = {"generatedSource": "source-hash", "toolchain": "toolchain-hash"}
        first = get_or_build(self.cache, fingerprint, "cpp/fixture.exe",
                             self._builder(b"real native behavior fixture", calls),
                             build_metadata={"command": ["haxe", "-cpp"]})
        self.assertFalse(first.reused)
        self.assertEqual(first.sha256, hashlib.sha256(b"real native behavior fixture").hexdigest())
        ready = json.loads((first.executable.parent.parent / "READY.json").read_text(encoding="utf-8"))
        self.assertEqual(ready["key"], first.key)
        self.assertEqual(ready["buildMetadata"]["command"], ["haxe", "-cpp"])

        second = get_or_build(self.cache, fingerprint, "cpp/fixture.exe",
                              self._builder(b"unused", calls))
        self.assertTrue(second.reused)
        self.assertEqual(first.executable, second.executable)
        self.assertEqual(len(calls), 1)

        second.executable.write_bytes(b"tampered native image")
        repaired = get_or_build(self.cache, fingerprint, "cpp/fixture.exe",
                                self._builder(b"restored native image", calls))
        self.assertFalse(repaired.reused)
        self.assertEqual(repaired.sha256, hashlib.sha256(b"restored native image").hexdigest())
        self.assertEqual(len(calls), 2)
        self.assertTrue(list((self.cache / "import-windows").glob(f".corrupt-{first.key}-*")))

    def test_malformed_marker_and_stale_staging_rebuild(self):
        fingerprint = {"fixture": "malformed-ready"}
        key = fingerprint_key(fingerprint)
        namespace = self.cache / "import-windows"
        entry = namespace / key
        calls = []
        first = get_or_build(self.cache, fingerprint, "cpp/fixture.exe",
                             self._builder(b"first image", calls))
        (entry / "READY.json").write_text("[]", encoding="utf-8")
        stale = namespace / f".building-{key}-dead-process"
        stale.mkdir()
        (stale / "partial.o").write_bytes(b"partial build")

        rebuilt = get_or_build(self.cache, fingerprint, "cpp/fixture.exe",
                               self._builder(b"second image", calls))
        self.assertFalse(rebuilt.reused)
        self.assertEqual(len(calls), 2)
        self.assertFalse(stale.exists())
        self.assertEqual(json.loads((entry / "READY.json").read_text(encoding="utf-8"))["sha256"],
                         rebuilt.sha256)

    def test_failed_build_leaves_no_ready_entry_and_next_call_recovers(self):
        fingerprint = {"fixture": "failure-recovery"}
        key = fingerprint_key(fingerprint)
        namespace = self.cache / "import-windows"

        def fail(staging: Path) -> Path:
            partial = staging / "cpp/fixture.exe"
            partial.parent.mkdir(parents=True)
            partial.write_bytes(b"truncated")
            raise RuntimeError("compiler failed")

        with self.assertRaisesRegex(RuntimeError, "compiler failed"):
            get_or_build(self.cache, fingerprint, "cpp/fixture.exe", fail)
        self.assertFalse((namespace / key).exists())
        self.assertEqual(list(namespace.glob(f".building-{key}-*")), [])

        calls = []
        recovered = get_or_build(self.cache, fingerprint, "cpp/fixture.exe",
                                 self._builder(b"complete image", calls))
        self.assertFalse(recovered.reused)
        self.assertEqual(len(calls), 1)

    def test_two_processes_share_one_atomic_build(self):
        fingerprint = {"fixture": "cross-process", "source": "sha256:abc"}
        key = fingerprint_key(fingerprint)
        namespace = self.cache / "import-windows"
        counter = self.root / "build-count.txt"
        started = self.root / "builder-started"
        tests_dir = Path(__file__).resolve().parent
        child = r'''
import json
import sys
import time
from pathlib import Path
from native_fixture_cache import get_or_build

cache = Path(sys.argv[1])
counter = Path(sys.argv[2])
started = Path(sys.argv[3])
fingerprint = {"fixture": "cross-process", "source": "sha256:abc"}

def build(staging):
    with counter.open("a", encoding="utf-8") as output:
        output.write("build\n")
        output.flush()
    started.write_text("started", encoding="utf-8")
    time.sleep(0.5)
    executable = staging / "cpp/fixture.exe"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"shared native fixture")
    return executable

result = get_or_build(cache, fingerprint, "cpp/fixture.exe", build)
print(json.dumps({"key": result.key, "sha256": result.sha256,
                  "reused": result.reused, "path": str(result.executable)}))
'''
        environment = {**os.environ,
                       "PYTHONPATH": os.pathsep.join([str(tests_dir), os.environ.get("PYTHONPATH", "")])}
        first = subprocess.Popen([sys.executable, "-c", child, str(self.cache), str(counter), str(started)],
                                 cwd=tests_dir.parents[1], env=environment,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        deadline = time.monotonic() + 10
        while not started.exists() and time.monotonic() < deadline:
            if first.poll() is not None:
                break
            time.sleep(0.02)
        self.assertTrue(started.exists(), "first process did not start its cache build")
        self.assertFalse((namespace / key).exists(), "entry became visible before its ready publication")

        second = subprocess.Popen([sys.executable, "-c", child, str(self.cache), str(counter), str(started)],
                                  cwd=tests_dir.parents[1], env=environment,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        first_out, first_err = first.communicate(timeout=15)
        second_out, second_err = second.communicate(timeout=15)
        self.assertEqual(first.returncode, 0, first_out + first_err)
        self.assertEqual(second.returncode, 0, second_out + second_err)
        first_result = json.loads(first_out.strip().splitlines()[-1])
        second_result = json.loads(second_out.strip().splitlines()[-1])
        self.assertEqual(first_result["key"], key)
        self.assertEqual(first_result["sha256"], second_result["sha256"])
        self.assertEqual(sorted([first_result["reused"], second_result["reused"]]), [False, True])
        self.assertEqual(counter.read_text(encoding="utf-8").splitlines(), ["build"])
        self.assertTrue((namespace / key / "READY.json").is_file())

    def test_symlinked_cache_entry_is_rebuilt_without_following_external_target(self):
        fingerprint = {"fixture": "entry-symlink"}
        key = fingerprint_key(fingerprint)
        namespace = self.cache / "import-windows"
        namespace.mkdir(parents=True)
        outside = self.root / "outside"
        outside.mkdir()
        sentinel = outside / "must-survive.bin"
        sentinel.write_bytes(b"external cache target")
        entry = namespace / key
        try:
            os.symlink(outside, entry, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"directory symlinks are unavailable: {error}")

        calls = []
        result = get_or_build(self.cache, fingerprint, "cpp/fixture.exe",
                              self._builder(b"owned fixture", calls))
        self.assertFalse(result.reused)
        self.assertEqual(len(calls), 1)
        self.assertEqual(sentinel.read_bytes(), b"external cache target")
        self.assertFalse(entry.is_symlink())

    def test_symlinked_namespace_and_lock_are_rejected_without_touching_target(self):
        outside = self.root / "outside-cache"
        outside.mkdir()
        sentinel = outside / "sentinel"
        sentinel.write_bytes(b"untouched")
        namespace_link = self.cache / "import-windows"
        namespace_link.parent.mkdir(parents=True)
        try:
            os.symlink(outside, namespace_link, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"directory symlinks are unavailable: {error}")
        with self.assertRaisesRegex(ValueError, "namespace cannot be a symlink"):
            get_or_build(self.cache, {"fixture": "namespace-symlink"}, "fixture.exe",
                         self._builder(b"unused", []))
        self.assertEqual(sentinel.read_bytes(), b"untouched")
        os.rmdir(namespace_link)

        namespace_link.mkdir()
        fingerprint = {"fixture": "lock-symlink"}
        key = fingerprint_key(fingerprint)
        outside_lock = outside / "outside.lock"
        outside_lock.write_bytes(b"do not overwrite")
        try:
            os.symlink(outside_lock, namespace_link / f"{key}.lock")
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"file symlinks are unavailable: {error}")
        with self.assertRaisesRegex(ValueError, "lock cannot be a symlink"):
            get_or_build(self.cache, fingerprint, "fixture.exe", self._builder(b"unused", []))
        self.assertEqual(outside_lock.read_bytes(), b"do not overwrite")

    def test_builder_cannot_return_executable_from_outside_staging(self):
        fingerprint = {"fixture": "outside-builder-output"}
        key = fingerprint_key(fingerprint)
        external = self.root / "external.exe"
        external.write_bytes(b"outside")

        def build(staging: Path) -> Path:
            link = staging / "cpp/fixture.exe"
            link.parent.mkdir(parents=True)
            try:
                os.symlink(external, link)
            except (OSError, NotImplementedError) as error:
                self.skipTest(f"file symlinks are unavailable: {error}")
            return link

        with self.assertRaisesRegex(ValueError, "outside its expected staging path"):
            get_or_build(self.cache, fingerprint, "cpp/fixture.exe", build)
        self.assertEqual(external.read_bytes(), b"outside")
        self.assertFalse((self.cache / "import-windows" / key).exists())

    def test_engine_source_change_before_capture_rejects_cache_miss_before_compile(self):
        source = self.root / "source"
        source.mkdir()
        module = source / "Fixture.hx"
        module.write_bytes(b"class Fixture { static var value = 1; }\n")
        expected = _tree_identity(source, suffix=".hx")
        module.write_bytes(b"class Fixture { static var value = 2; }\n")

        staging_source = self.root / "staging/engine-source"
        compile_calls = []
        with self.assertRaisesRegex(RuntimeError, "changed after native fixture fingerprinting"):
            _capture_engine_sources(source, staging_source, expected)
            compile_calls.append("compile")

        self.assertEqual(compile_calls, [])
        self.assertNotEqual(_tree_identity(source, suffix=".hx"), expected)

    def test_engine_source_change_after_capture_keeps_compiler_input_stable(self):
        source = self.root / "source"
        module = source / "nested/Fixture.hx"
        module.parent.mkdir(parents=True)
        before = b"class Fixture { static var value = 1; }\n"
        module.write_bytes(before)
        expected = _tree_identity(source, suffix=".hx")
        staging_source = self.root / "staging/engine-source"

        captured = _capture_engine_sources(source, staging_source, expected)
        module.write_bytes(b"class Fixture { static var value = 2; }\n")

        self.assertEqual(captured, expected)
        self.assertEqual((staging_source / "nested/Fixture.hx").read_bytes(), before)
        self.assertNotEqual(module.read_bytes(), (staging_source / "nested/Fixture.hx").read_bytes())


if __name__ == "__main__":
    unittest.main()
