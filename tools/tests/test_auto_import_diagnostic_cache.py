"""The compiled donor scanner cache must follow its generated source."""

import importlib.util
from pathlib import Path
from haxe_test_support import FixturePath as Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "diagnose_example_auto_import", ROOT / "tools/diagnose_example_auto_import.py"
)
DIAGNOSTIC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DIAGNOSTIC)
PATCHER_SPEC = importlib.util.spec_from_file_location(
    "patch_hxcpp_large_free", ROOT / "tools/patch_hxcpp_large_free.py"
)
HXCPP_PATCHER = importlib.util.module_from_spec(PATCHER_SPEC)
PATCHER_SPEC.loader.exec_module(HXCPP_PATCHER)


def immix_base_source_variants():
    """Return exact pristine and installed run.sh-patched sources in memory."""
    installed = (ROOT / ".haxelib/hxcpp/4,3,2/src/hx/gc/Immix.cpp").read_bytes()
    actual_hash = hashlib.sha256(installed).hexdigest()
    if actual_hash == DIAGNOSTIC.HXCPP_IMMIX_SOURCE_SHA256:
        return [("pristine", installed)]
    if actual_hash == DIAGNOSTIC.HXCPP_IMMIX_MANAGED_SOURCE_SHA256:
        if DIAGNOSTIC.HXCPP_IMMIX_MANAGED_SOURCE_SHA256 != HXCPP_PATCHER.PATCHED_SHA256:
            raise AssertionError("diagnostic managed-source pin differs from run.sh patch pin")
        if installed.count(HXCPP_PATCHER.NEW_SITE) != 1:
            raise AssertionError("installed managed Immix.cpp lacks the exact run.sh patch")
        pristine = installed.replace(HXCPP_PATCHER.NEW_SITE, HXCPP_PATCHER.OLD_SITE, 1)
        if hashlib.sha256(pristine).hexdigest() != DIAGNOSTIC.HXCPP_IMMIX_SOURCE_SHA256:
            raise AssertionError("run.sh patch did not reconstruct the pinned pristine Immix.cpp")
        return [("pristine", pristine), ("run.sh-patched", installed)]
    raise AssertionError(f"installed Immix.cpp has an unknown test source hash: {actual_hash}")


class AutoImportDiagnosticCacheTest(unittest.TestCase):
    def test_counts_only_compact_selection_matches_score_and_path_precedence(self):
        source = DIAGNOSTIC.COUNTS_ONLY_ACCUMULATOR + r'''class Main {
  static function main() {
    var accumulator = new DiagnosticCandidateAccumulator();
    var equalDiagnostics = ["[first-tie]"];
    accumulator.add(" Alpha ", "/z/root", "V-SLICE", 100, "/z/root", "/z/root",
      ["[lower-score]"], "/alpha-origin");
    accumulator.add("alpha", "/a/root", "PSYCH", 90, "/a/root", "/a/root",
      ["[alpha-low]"], "/alpha-origin");
    accumulator.add("ALPHA", "/b/root", "V-SLICE", 100, "/b/root", "/b/root",
      ["[alpha-winner]"], "/alpha-origin");
    accumulator.add("beta", "/case/a", "Kade", 60, "/same", "/case/a",
      ["[beta-later-path]"], "/beta-origin");
    accumulator.add(" Beta ", "/case/A", "FPS", 60, "/same", "/case/A", equalDiagnostics,
      "/beta-origin");
    equalDiagnostics[0] = "[mutated-after-add]";
    accumulator.add("BETA", "/case/A", "Legacy", 60, "/same", "/case/A",
      ["[equal-later]"], "/beta-origin");
    accumulator.add("alpha", "/other/root", "Psych", 10, "/other/root", "/other/root",
      ["[independent-origin]"], "/other-origin");
    if (accumulator.candidateCount != 7 || accumulator.uniqueCount() != 3)
      throw "candidate totals changed";
    var winners = new Map<String, DiagnosticCompactCandidate>();
    for (candidate in accumulator.winners())
      winners.set(StringTools.trim(candidate.name).toLowerCase() + "|" + candidate.origin, candidate);
    var alpha = winners.get("alpha|/alpha-origin");
    var beta = winners.get("beta|/beta-origin");
    if (alpha == null || alpha.root != "/b/root" || alpha.engine != "V-SLICE"
      || alpha.diagnostics.join(",") != "[alpha-winner]")
      throw "score precedence changed";
    if (beta == null || beta.root != "/case/A" || beta.engine != "FPS"
      || beta.diagnostics.join(",") != "[first-tie]")
      throw "root/stable-path or equal-order precedence changed";
    if (winners.get("alpha|/other-origin") == null)
      throw "independent physical origin collapsed";
    trace("CANDIDATES=" + accumulator.candidateCount + "|UNIQUE=" + accumulator.uniqueCount()
      + "|DUPLICATES=" + (accumulator.candidateCount - accumulator.uniqueCount()));
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            (Path(directory) / "Main.hx").write_text(source, newline='\n')
            result = subprocess.run(
                [str(DIAGNOSTIC.HAXE), "-cp", directory, "--run", "Main"],
                cwd=directory, capture_output=True, text=True, timeout=30,
            )
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("CANDIDATES=7|UNIQUE=3|DUPLICATES=4", output)
        self.assertIn("ModuleFunctions.diagnosticCompleteness(song)", DIAGNOSTIC.MAIN)
        self.assertIn("DependencyInspector.clearChartCache();", DIAGNOSTIC.MAIN)
        self.assertIn("found[songIndex] = cast null;", DIAGNOSTIC.MAIN)

    def test_cached_native_run_closes_without_asan_file_descriptor(self):
        key = "test-cached-cleanup-" + uuid.uuid4().hex
        cache_root = ROOT / "tmp/auto-import-diagnostic-cache" / key
        cache_root.mkdir(parents=True)
        executable = cache_root / "Main"
        executable.write_text("#!/bin/sh\nprintf 'CACHED_SCANNER_OK\\n'\n", newline='\n')
        executable.chmod(0o755)
        actual_scan = DIAGNOSTIC.run_bounded_native_scan
        seen_timeouts = []

        def capture_scan(command, cwd, env, timeout):
            seen_timeouts.append(timeout)
            return actual_scan(command, cwd, env, timeout)

        try:
            with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as donor:
                with mock.patch.object(DIAGNOSTIC, "native_scan_cache_key", return_value=key), \
                     mock.patch.object(DIAGNOSTIC, "run_bounded_native_scan", side_effect=capture_scan), \
                     mock.patch.object(sys, "argv", ["diagnose_example_auto_import.py", "--scan-timeout-seconds", "600", donor]), \
                     mock.patch("sys.stdout") as stdout:
                    result = DIAGNOSTIC.main()
            self.assertEqual(result, 0)
            self.assertEqual(seen_timeouts, [600.0])
            stdout.write.assert_any_call("CACHED_SCANNER_OK\n")
        finally:
            shutil.rmtree(cache_root)

    def test_cached_scanner_trace_flag_controls_runtime_only(self):
        key = "test-psych-trace-cache-" + uuid.uuid4().hex
        cache_root = ROOT / "tmp/auto-import-diagnostic-cache" / key
        cache_root.mkdir(parents=True)
        executable = cache_root / "Main"
        executable.write_text("#!/bin/sh\nprintf 'TRACE=%s\\n' \"${DISAPPOINTINGPLUS_PSYCH_DISCOVERY_TRACE-unset}\"\n", newline='\n')
        executable.chmod(0o755)
        trace_name = "DISAPPOINTINGPLUS_PSYCH_DISCOVERY_TRACE"
        try:
            with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as donor, \
                 mock.patch.object(DIAGNOSTIC, "native_scan_cache_key", return_value=key), \
                 mock.patch.dict(os.environ, {trace_name: "1"}):
                with mock.patch.object(sys, "argv", ["diagnose_example_auto_import.py", donor]), \
                     mock.patch("sys.stdout") as stdout:
                    self.assertEqual(DIAGNOSTIC.main(), 0)
                    stdout.write.assert_any_call("TRACE=unset\n")
                with mock.patch.object(sys, "argv", ["diagnose_example_auto_import.py", "--trace-psych-discovery", donor]), \
                     mock.patch("sys.stdout") as stdout:
                    self.assertEqual(DIAGNOSTIC.main(), 0)
                    stdout.write.assert_any_call("TRACE=1\n")
        finally:
            shutil.rmtree(cache_root)

    def test_cached_recycler_mode_uses_separate_binary_and_records_run(self):
        key = "test-recycler-cache-" + uuid.uuid4().hex
        cache_root = ROOT / "tmp/auto-import-diagnostic-recycle-cache" / key
        cache_root.mkdir(parents=True)
        executable = cache_root / "Main"
        executable.write_text("#!/bin/sh\nprintf 'RECYCLE_SCANNER_OK\\n'\n", newline='\n')
        executable.chmod(0o755)
        try:
            with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as donor:
                with mock.patch.object(DIAGNOSTIC, "native_scan_cache_key", return_value=key) as cache_key, \
                     mock.patch.object(sys, "argv", ["diagnose_example_auto_import.py", "--recycle-diagnostics", donor]), \
                     mock.patch("sys.stdout") as stdout:
                    result = DIAGNOSTIC.main()
            self.assertEqual(result, 0)
            self.assertTrue(cache_key.call_args.kwargs["recycle_diagnostics"])
            stdout.write.assert_any_call("RECYCLE_SCANNER_OK\n")
            run_json = next(cache_root.glob("run-*/run.json"))
            metadata = json.loads(run_json.read_text())
            self.assertEqual(metadata["mode"], "recycle")
            self.assertTrue(metadata["cached_binary"])
            self.assertEqual(metadata["returncode"], 0)
            self.assertIsNone(metadata["ASAN_OPTIONS"])
        finally:
            shutil.rmtree(cache_root)

    def test_bounded_scan_retains_partial_asan_report_on_timeout(self):
        command = ["/fake/scanner", "--counts-only"]
        partial = subprocess.TimeoutExpired(
            command, 3, output=b"ROOTS=2\n", stderr=b"==1==ERROR: AddressSanitizer\n"
        )
        with mock.patch.object(subprocess, "run", side_effect=partial):
            result, timed_out = DIAGNOSTIC.run_bounded_native_scan(
                command, ROOT, {"ASAN_OPTIONS": "test"}, 3
            )
        self.assertTrue(timed_out)
        self.assertEqual(result.returncode, 124)
        self.assertEqual(result.stdout, "ROOTS=2\n")
        self.assertEqual(result.stderr, "==1==ERROR: AddressSanitizer\n")

    def test_scan_timeout_default_and_invalid_values(self):
        self.assertEqual(DIAGNOSTIC.parse_arguments([]).scan_timeout_seconds, 300.0)
        self.assertEqual(
            DIAGNOSTIC.parse_arguments(["--scan-timeout-seconds", "600"]).scan_timeout_seconds,
            600.0,
        )
        for value in ("0", "-1", "nan", "inf", "garbage"):
            with self.subTest(value=value), self.assertRaises(SystemExit):
                DIAGNOSTIC.parse_arguments(["--scan-timeout-seconds", value])

    @unittest.skipIf(os.name == 'nt', 'uses Linux native scanner, shell wrappers or ELF cache fixtures')
    def test_fixture_source_changes_cache_key(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            source = Path(directory) / "Main.hx"
            source.write_text("class Main { static function main() {} }\n", newline='\n')
            first = DIAGNOSTIC.native_scan_cache_key(Path(directory))
            self.assertEqual(first, DIAGNOSTIC.native_scan_cache_key(Path(directory)))
            source.write_text("class Main { static function main() { trace(1); } }\n", newline='\n')
            self.assertNotEqual(first, DIAGNOSTIC.native_scan_cache_key(Path(directory)))

    @unittest.skipIf(os.name == 'nt', 'uses Linux native scanner, shell wrappers or ELF cache fixtures')
    def test_gc_debug_build_uses_isolated_cache_key(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            source = Path(directory) / "Main.hx"
            source.write_text("class Main { static function main() {} }\n", newline='\n')
            fixture = Path(directory)
            normal = DIAGNOSTIC.native_scan_cache_key(fixture)
            debug = DIAGNOSTIC.native_scan_cache_key(fixture, gc_debug_level_1=True)
            self.assertNotEqual(normal, debug)

    def test_gc_debug_define_is_opt_in_and_parsed(self):
        normal = DIAGNOSTIC.parse_arguments([])
        debug = DIAGNOSTIC.parse_arguments(["--gc-debug-level-1"])

        self.assertFalse(normal.gc_debug_level_1)
        self.assertEqual(
            DIAGNOSTIC.native_scan_build_args(normal.gc_debug_level_1),
            ["-DHXCPP_COMPILE_THREADS=4"],
        )
        self.assertTrue(debug.gc_debug_level_1)
        self.assertEqual(
            DIAGNOSTIC.native_scan_build_args(debug.gc_debug_level_1),
            ["-DHXCPP_COMPILE_THREADS=4", "-DHXCPP_GC_DEBUG_LEVEL=1"],
        )

    @unittest.skipIf(os.name == 'nt', 'uses Linux native scanner, shell wrappers or ELF cache fixtures')
    def test_asan_mode_has_isolated_cache_and_rejects_gc_debug_combo(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            fixture = Path(directory)
            (fixture / "Main.hx").write_text("class Main { static function main() {} }\n", newline='\n')
            normal = DIAGNOSTIC.native_scan_cache_key(fixture)
            gc_debug = DIAGNOSTIC.native_scan_cache_key(fixture, gc_debug_level_1=True)
            asan = DIAGNOSTIC.native_scan_cache_key(fixture, asan=True)
            recycle = DIAGNOSTIC.native_scan_cache_key(fixture, recycle_diagnostics=True)
            self.assertEqual(len({normal, gc_debug, asan, recycle}), 4)
            with self.assertRaises(ValueError):
                DIAGNOSTIC.native_scan_cache_key(
                    fixture, gc_debug_level_1=True, asan=True
                )
            with self.assertRaises(ValueError):
                DIAGNOSTIC.native_scan_build_args(gc_debug_level_1=True, asan=True)
            with self.assertRaises(ValueError):
                DIAGNOSTIC.native_scan_cache_key(fixture, asan=True, recycle_diagnostics=True)

    def test_asan_flags_are_opt_in_and_mutually_exclusive_with_gc_debug(self):
        normal = DIAGNOSTIC.parse_arguments([])
        asan = DIAGNOSTIC.parse_arguments(["--asan"])

        self.assertFalse(normal.asan)
        self.assertTrue(asan.asan)
        self.assertEqual(
            DIAGNOSTIC.native_scan_build_args(asan=True),
            ["-DHXCPP_COMPILE_THREADS=4", *DIAGNOSTIC.ASAN_HXCPP_BUILD_ARGS],
        )
        self.assertEqual(
            DIAGNOSTIC.native_scan_build_args(),
            ["-DHXCPP_COMPILE_THREADS=4"],
        )
        self.assertEqual(
            DIAGNOSTIC.native_scan_build_args(recycle_diagnostics=True),
            ["-DHXCPP_COMPILE_THREADS=4", "-DHXCPP_DEBUG_LINK"],
        )
        with self.assertRaises(ValueError):
            DIAGNOSTIC.native_scan_build_args(asan=True, recycle_diagnostics=True)
        with self.assertRaises(SystemExit):
            DIAGNOSTIC.parse_arguments(["--asan", "--gc-debug-level-1"])
        self.assertTrue(DIAGNOSTIC.parse_arguments(["--recycle-diagnostics"]).recycle_diagnostics)
        with self.assertRaises(SystemExit):
            DIAGNOSTIC.parse_arguments(["--recycle-diagnostics", "--asan"])
        with self.assertRaises(SystemExit):
            DIAGNOSTIC.parse_arguments(["--recycle-diagnostics", "--gc-debug-level-1"])

    def test_asan_runtime_environment_is_isolated_and_disables_fake_stack(self):
        base = {"PATH": "/bin", "TMPDIR": "/system/tmp"}
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            local_tmp = Path(directory)
            actual = DIAGNOSTIC.asan_runtime_env(base, local_tmp)

        self.assertEqual(actual["PATH"], "/bin")
        self.assertEqual(actual["TMPDIR"], str(local_tmp))
        self.assertEqual(
            actual["ASAN_OPTIONS"], DIAGNOSTIC.ASAN_RUNTIME_OPTIONS
        )
        self.assertIn("detect_stack_use_after_return=0", actual["ASAN_OPTIONS"])
        self.assertEqual(actual["SDL_AUDIODRIVER"], "dummy")
        self.assertEqual(base["TMPDIR"], "/system/tmp")

    def test_asan_build_environment_forces_default_gc_mode(self):
        base = {"HXCPP_GC_DEBUG_LEVEL": "1", "CXX": "host-tool"}
        actual = DIAGNOSTIC.asan_build_env(base)
        self.assertNotIn("HXCPP_GC_DEBUG_LEVEL", actual)
        self.assertEqual(actual["HXCPP_VERBOSE"], "1")
        self.assertEqual(actual["CXX"], "host-tool")
        self.assertEqual(base["HXCPP_GC_DEBUG_LEVEL"], "1")

    def test_haxelib_commands_force_private_repository_only_in_asan_mode(self):
        haxelib = Path("aliases/haxe/haxelib")
        self.assertEqual(
            DIAGNOSTIC.haxelib_path_command(haxelib, private_repo=True),
            [str(haxelib), "--global", "path", "hxcpp"],
        )
        self.assertEqual(
            DIAGNOSTIC.haxelib_path_command(haxelib),
            [str(haxelib), "path", "hxcpp"],
        )
        self.assertEqual(
            DIAGNOSTIC.hxcpp_build_command(
                haxelib, ["-DHXCPP_VERBOSE"], private_repo=True
            ),
            [str(haxelib), "--global", "run", "hxcpp", "Build.xml", "-DHXCPP_VERBOSE"],
        )

    def test_haxelib_preflight_rejects_any_path_outside_private_overlay(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            temp = Path(directory)
            private = temp / "private-haxelib"
            private_hxcpp = private / "hxcpp/4,3,2"
            private_hxcpp.mkdir(parents=True)
            valid = (
                str(private_hxcpp) + "/\n"
                "-D hxcpp=4.3.2\n"
            )
            mixed = valid + "/some/other/repo/hxcpp/4,3,2/\n"

            self.assertTrue(DIAGNOSTIC.haxelib_paths_are_private(valid, private))
            self.assertFalse(DIAGNOSTIC.haxelib_paths_are_private(mixed, private))
            self.assertFalse(DIAGNOSTIC.haxelib_paths_are_private("-D hxcpp=4.3.2\n", private))

    def test_asan_private_overlay_patches_only_private_hxcpp_copy(self):
        pinned_package = ROOT / ".haxelib/hxcpp"
        pinned_version = (pinned_package / ".current").read_text().strip()
        self.assertEqual(pinned_version, DIAGNOSTIC.HXCPP_PACKAGE_VERSION)
        pinned_version_dir = pinned_package / DIAGNOSTIC.HXCPP_PACKAGE_DIRECTORY
        self.assertTrue(pinned_version_dir.is_dir())
        self.assertFalse((pinned_package / pinned_version).exists())

        pinned = pinned_version_dir / "src/hx/gc/GcRegCapture.cpp"
        pinned_immix = pinned_version_dir / "src/hx/gc/Immix.cpp"
        self.assertFalse(pinned.is_symlink())
        self.assertFalse(pinned_immix.is_symlink())
        original_bytes = pinned.read_bytes()
        original_immix_bytes = pinned_immix.read_bytes()
        original_hash = hashlib.sha256(original_bytes).hexdigest()
        original_immix_hash = hashlib.sha256(original_immix_bytes).hexdigest()
        self.assertEqual(original_hash, DIAGNOSTIC.HXCPP_CAPTURE_SOURCE_SHA256)
        self.assertIn(original_immix_hash, (
            DIAGNOSTIC.HXCPP_IMMIX_SOURCE_SHA256,
            DIAGNOSTIC.HXCPP_IMMIX_MANAGED_SOURCE_SHA256,
        ))

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            temp = Path(directory)
            source = temp / "source-haxelib"
            destination = temp / "private-haxelib"
            hxcpp = source / "hxcpp"
            (hxcpp / DIAGNOSTIC.HXCPP_PACKAGE_DIRECTORY / "src/hx/gc").mkdir(parents=True)
            (hxcpp / ".current").write_text("4.3.2", newline='\n')
            (hxcpp / DIAGNOSTIC.HXCPP_PACKAGE_DIRECTORY / "src/hx/gc/GcRegCapture.cpp").write_bytes(original_bytes)
            (hxcpp / DIAGNOSTIC.HXCPP_PACKAGE_DIRECTORY / "src/hx/gc/Immix.cpp").write_bytes(original_immix_bytes)
            (source / "hscript").mkdir()

            DIAGNOSTIC.prepare_private_haxelib_overlay(source, destination)
            copied = destination / "hxcpp/4,3,2/src/hx/gc/GcRegCapture.cpp"
            patched = copied.read_bytes()
            copied_immix = destination / "hxcpp/4,3,2/src/hx/gc/Immix.cpp"
            patched_immix = copied_immix.read_bytes()

            self.assertFalse(copied.is_symlink())
            self.assertEqual(copied.resolve().relative_to(destination.resolve()).as_posix(),
                             "hxcpp/4,3,2/src/hx/gc/GcRegCapture.cpp")
            self.assertNotEqual(hashlib.sha256(patched).hexdigest(), original_hash)
            self.assertIn(b"hxcppCopyActiveStackWords", patched)
            self.assertLess(
                patched.index(b"static void hxcppCopyActiveStackWords"),
                patched.index(b"int RegisterCapture::Capture"),
            )
            self.assertIn(b"#else\r\n\t   memcpy(inBuf,inBottom,size*sizeof(void*));", patched)
            self.assertFalse(copied_immix.is_symlink())
            self.assertEqual(copied_immix.resolve().relative_to(destination.resolve()).as_posix(),
                             "hxcpp/4,3,2/src/hx/gc/Immix.cpp")
            self.assertNotEqual(hashlib.sha256(patched_immix).hexdigest(), original_immix_hash)
            self.assertIn(b"static void *hxcppReadConservativeRootWord", patched_immix)
            self.assertIn(b"void *vptr = hxcppReadConservativeRootWord(ptr);", patched_immix)
            self.assertIn(b"#else\n      void *vptr = *(void **)ptr;\n#endif", patched_immix)
            self.assertEqual(patched_immix.count(b"no_sanitize_address"), 1)
            self.assertLess(patched_immix.index(b"static void *hxcppReadConservativeRootWord"),
                            patched_immix.index(b"void MarkConservative("))
            self.assertIn(b"HXCPP_RECYCLE_VIOLATION|%s|ptr=%p|size=%u|index=%d", patched_immix)
            self.assertIn(b"backtrace(frames, 24)", patched_immix)
            self.assertIn(b"backtrace_symbols_fd(frames, count, 2)", patched_immix)
            self.assertIn(b'if (!mLargeList.qerase_val(blob))', patched_immix)
            self.assertIn(b'"missing-live-list"', patched_immix)
            self.assertIn(b'"duplicate-explicit"', patched_immix)
            self.assertIn(b'"duplicate-sweep"', patched_immix)
            self.assertEqual(patched_immix.count(b"hxcppRecycleIndex(blob)"), 2)
            for marker in (
                b'"push-corruption-explicit"', b'"push-corruption-sweep"',
                b'"candidate-observed"', b'"candidate-locked"', b'"reuse-corruption"',
                b'"duplicate-live-reuse"', b'hxcppRecycleExpectedQeraseFingerprint(i)',
                b'"duplicate-before-free"', b'"reset-corruption"',
                b'HXCPP_RECYCLE_EVENT|seq=', b'hxcppRecyclePrefixFingerprint(oldRecycleSize)',
            ):
                self.assertIn(marker, patched_immix)
            self.assertLess(patched_immix.index(b'hxcppRecycleCheckUnique("duplicate-before-free")'),
                            patched_immix.index(b'HxFree(blob);', patched_immix.index(b'// Sweep large')))
            self.assertNotIn(b'"candidate-changed"', patched_immix)
            self.assertIn(b'|truncated=%d|sync=large-list-lock-or-collector-stop', patched_immix)
            self.assertIn(b'a match is probabilistic evidence only', patched_immix)
            self.assertTrue((destination / "hscript").is_symlink())
            self.assertEqual((destination / "hscript").resolve(), (source / "hscript").resolve())
            self.assertEqual(hashlib.sha256(pinned.read_bytes()).hexdigest(), original_hash)
            self.assertEqual(hashlib.sha256(pinned_immix.read_bytes()).hexdigest(), original_immix_hash)

    def test_asan_stack_patch_refuses_unknown_hxcpp_source(self):
        pinned = ROOT / ".haxelib/hxcpp/4,3,2/src/hx/gc/GcRegCapture.cpp"
        changed = pinned.read_bytes() + b"// changed\n"
        with self.assertRaisesRegex(ValueError, "changed; refusing unreviewed ASan patch"):
            DIAGNOSTIC.patch_gc_stack_capture_source(changed)

    def test_asan_conservative_root_patch_refuses_unknown_hxcpp_source(self):
        pinned = ROOT / ".haxelib/hxcpp/4,3,2/src/hx/gc/Immix.cpp"
        changed = pinned.read_bytes() + b"// changed\n"
        with self.assertRaisesRegex(ValueError, "changed; refusing unreviewed ASan patch"):
            DIAGNOSTIC.patch_gc_conservative_root_source(changed)

    def test_recycler_patch_refuses_unknown_intermediate_source(self):
        expected_conservative_hashes = {
            DIAGNOSTIC.HXCPP_IMMIX_SOURCE_SHA256: DIAGNOSTIC.HXCPP_IMMIX_CONSERVATIVE_SHA256,
            DIAGNOSTIC.HXCPP_IMMIX_MANAGED_SOURCE_SHA256:
                DIAGNOSTIC.HXCPP_IMMIX_MANAGED_CONSERVATIVE_SHA256,
        }
        for variant, source in immix_base_source_variants():
            with self.subTest(variant=variant):
                conservative = DIAGNOSTIC.patch_gc_conservative_root_source(source)
                self.assertEqual(
                    hashlib.sha256(conservative).hexdigest(),
                    expected_conservative_hashes[hashlib.sha256(source).hexdigest()],
                )
                patched = DIAGNOSTIC.patch_gc_recycler_source(conservative)
                self.assertIn(b"HXCPP_RECYCLE_VIOLATION", patched)
                self.assertIn(b'"missing-live-list"', patched)
                if variant == "run.sh-patched":
                    self.assertIn(b"hxcppRecycleViolation(\"missing-live-list\", blob, 0, -1);", patched)
                with self.assertRaisesRegex(ValueError, "conservative patch changed; refusing"):
                    DIAGNOSTIC.patch_gc_recycler_source(conservative + b"// changed\n")

    @unittest.skipIf(os.name == 'nt', 'Linux row-mark probe requires execinfo.h')
    def test_row_mark_probe_checks_both_paths_and_block_boundary(self):
        compiler = shutil.which("g++")
        if compiler is None:
            self.skipTest("g++ is unavailable")
        pinned = ROOT / ".haxelib/hxcpp/4,3,2/src/hx/gc/Immix.cpp"
        patched = DIAGNOSTIC.patch_gc_recycler_source(
            DIAGNOSTIC.patch_gc_conservative_root_source(pinned.read_bytes())
        ).decode()
        for name in ("MarkAllocUnchecked", "MarkObjectAllocUnchecked"):
            method = patched.split("void " + name + "(", 1)[1].split("\nvoid ", 1)[0]
            self.assertLess(method.index("hxcppCheckMarkRows(ptr_i, flags);"),
                            method.index("*rowMark = 1;"))
        helper = patched.split("// Private diagnostic: validate the row table before marking it.\n", 1)[1].split(
            "// End private row-mark diagnostic.", 1)[0]
        source = """
#include <cstdio>
#include <cstdlib>
#include <execinfo.h>
#include <sys/resource.h>
#define IMMIX_ALLOC_ROW_COUNT 0xff
#define IMMIX_BLOCK_OFFSET_MASK 0x7fff
#define IMMIX_LINE_BITS 7
#define IMMIX_LINES 256
""" + helper + """
int main(int argc, char **argv) {
   struct rlimit noCore = {0, 0};
   if (setrlimit(RLIMIT_CORE, &noCore) != 0) return 8;
   hxcppCheckMarkRows(0x10000 + 255 * 128, 1); // Last row, exact boundary.
   hxcppCheckMarkRows(0x10000 + 2 * 128, 254); // Full available row table.
   hxcppCheckMarkRows(0x10000 + 255 * 128, 0); // Large allocation: no row marks.
   if (argc > 1) hxcppCheckMarkRows(0x10000 + 255 * 128, 2);
   return 0;
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            temp = Path(directory)
            cpp, executable = temp / "probe.cpp", temp / "probe"
            cpp.write_text(source, newline='\n')
            built = subprocess.run([compiler, str(cpp), "-o", str(executable)],
                                   capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            valid = subprocess.run([str(executable)], cwd=temp, capture_output=True, text=True)
            self.assertEqual(valid.returncode, 0, valid.stderr)
            invalid = subprocess.run([str(executable), "overflow"], cwd=temp,
                                     capture_output=True, text=True)
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn("HXCPP_ROW_MARK_VIOLATION|", invalid.stderr)
            self.assertIn("|start=255|rows=2", invalid.stderr)

    @unittest.skipIf(os.name == 'nt', 'Linux recycler probe requires execinfo.h')
    def test_recycler_private_helpers_compile_and_detect_transition_failures(self):
        compiler = shutil.which("g++")
        if compiler is None:
            self.skipTest("g++ is unavailable")
        pinned = ROOT / ".haxelib/hxcpp/4,3,2/src/hx/gc/Immix.cpp"
        patched = DIAGNOSTIC.patch_gc_recycler_source(
            DIAGNOSTIC.patch_gc_conservative_root_source(pinned.read_bytes())
        ).decode()
        report = patched.split("// Private diagnostic: stop at the first recycler invariant violation.\n", 1)[1].split("class GlobalAllocator\n{", 1)[0]
        members = patched.split("   struct RecycleEvent\n", 1)[1].split("   unsigned long long hxcppRecycleSequence;\n", 1)[0]
        helpers = patched.split("   void hxcppRecycleRecord(", 1)[1].split("   void FreeLarge(void *inLarge)", 1)[0]
        source = """
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <pthread.h>
#include <execinfo.h>
#include <sys/resource.h>
#include \"hx/QuickVec.h\"
""" + report + """
class Probe {
public:
   hx::QuickVec<unsigned int *> largeObjectRecycle;
   struct RecycleEvent
""" + members + "   unsigned long long hxcppRecycleSequence;\n" + """
   Probe() : hxcppRecycleSequence(0) {}
   void hxcppRecycleRecord(""" + helpers + """
   int run(int mode) {
      unsigned int a[2] = {16, 0};
      unsigned int b[2] = {16, 0};
      largeObjectRecycle.push(a);
      hxcppRecycleRecord("push", a, 0);
      if (mode == 1) {
         largeObjectRecycle.push(a);
         hxcppRecycleRecord("push", a, 1);
         hxcppRecycleCheckUnique("duplicate-before-free");
      }
      if (mode == 2) {
         int oldSize = largeObjectRecycle.size();
         unsigned long long prefix = hxcppRecyclePrefixFingerprint(oldSize);
         largeObjectRecycle[0] = b;
         largeObjectRecycle.push(b);
         hxcppRecycleRecord("push", b, oldSize);
         if (hxcppRecyclePrefixFingerprint(oldSize) != prefix)
            hxcppRecycleViolation("push-corruption-sweep", b, 16, oldSize);
      }
      if (mode == 3) {
         largeObjectRecycle.push(b);
         int oldSize = largeObjectRecycle.size();
         unsigned long long expectedAfterErase = hxcppRecycleExpectedQeraseFingerprint(0);
         unsigned int *result = largeObjectRecycle[0];
         largeObjectRecycle.qerase(0);
         hxcppRecycleRecord("reuse", result, 0);
         if (largeObjectRecycle.size() != oldSize - 1 || hxcppRecycleIndex(result) >= 0 ||
             hxcppRecyclePrefixFingerprint(oldSize - 1) != expectedAfterErase)
            hxcppRecycleViolation("reuse-corruption", result, 16, 0);
         if (largeObjectRecycle.size() != 1 || largeObjectRecycle[0] != b)
            return 7;
      }
      if (mode == 4) {
         largeObjectRecycle.push(a);
         int oldSize = largeObjectRecycle.size();
         unsigned long long expectedAfterErase = hxcppRecycleExpectedQeraseFingerprint(0);
         unsigned int *result = largeObjectRecycle[0];
         largeObjectRecycle.qerase(0);
         hxcppRecycleRecord("reuse", result, 0);
         if (largeObjectRecycle.size() != oldSize - 1 || hxcppRecycleIndex(result) >= 0 ||
             hxcppRecyclePrefixFingerprint(oldSize - 1) != expectedAfterErase)
            hxcppRecycleViolation("reuse-corruption", result, 16, 0);
      }
      return 0;
   }
};
int main(int argc, char **argv) {
   struct rlimit noCore = {0, 0};
   if (setrlimit(RLIMIT_CORE, &noCore) != 0) return 8;
   Probe probe;
   return probe.run(atoi(argv[1]));
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            temp = Path(directory)
            cpp = temp / "probe.cpp"
            executable = temp / "probe"
            cpp.write_text(source, newline='\n')
            built = subprocess.run(
                [compiler, "-std=c++11", "-pthread", "-I", str(ROOT / ".haxelib/hxcpp/4,3,2/include"),
                 str(cpp), "-o", str(executable)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(built.returncode, 0, built.stderr)
            for mode in (0, 3):
                result = subprocess.run([str(executable), str(mode)], cwd=temp, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            for mode, label in ((1, "duplicate-before-free"), (2, "push-corruption-sweep"),
                                (4, "reuse-corruption")):
                result = subprocess.run([str(executable), str(mode)], cwd=temp, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("HXCPP_RECYCLE_HISTORY|", result.stderr)
                self.assertIn("HXCPP_RECYCLE_EVENT|", result.stderr)
                self.assertIn("HXCPP_RECYCLE_VIOLATION|" + label, result.stderr)

    def test_asan_overlay_refuses_symlinked_capture_source(self):
        pinned = ROOT / ".haxelib/hxcpp/4,3,2/src/hx/gc/GcRegCapture.cpp"
        original_hash = hashlib.sha256(pinned.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            temp = Path(directory)
            source = temp / "source-haxelib"
            hxcpp = source / "hxcpp"
            capture_dir = hxcpp / DIAGNOSTIC.HXCPP_PACKAGE_DIRECTORY / "src/hx/gc"
            capture_dir.mkdir(parents=True)
            (hxcpp / ".current").write_text(DIAGNOSTIC.HXCPP_PACKAGE_VERSION, newline='\n')
            (capture_dir / "GcRegCapture.cpp").symlink_to(pinned)
            (capture_dir / "Immix.cpp").write_bytes(
                (ROOT / ".haxelib/hxcpp/4,3,2/src/hx/gc/Immix.cpp").read_bytes()
            )

            with self.assertRaisesRegex(ValueError, "must be a regular package file"):
                DIAGNOSTIC.prepare_private_haxelib_overlay(
                    source, temp / "private-haxelib"
                )

        self.assertEqual(hashlib.sha256(pinned.read_bytes()).hexdigest(), original_hash)

    def test_asan_overlay_refuses_symlinked_conservative_root_source(self):
        pinned_capture = ROOT / ".haxelib/hxcpp/4,3,2/src/hx/gc/GcRegCapture.cpp"
        pinned_immix = ROOT / ".haxelib/hxcpp/4,3,2/src/hx/gc/Immix.cpp"
        original_hash = hashlib.sha256(pinned_immix.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            temp = Path(directory)
            source = temp / "source-haxelib"
            hxcpp = source / "hxcpp"
            source_dir = hxcpp / DIAGNOSTIC.HXCPP_PACKAGE_DIRECTORY / "src/hx/gc"
            source_dir.mkdir(parents=True)
            (hxcpp / ".current").write_text(DIAGNOSTIC.HXCPP_PACKAGE_VERSION, newline='\n')
            (source_dir / "GcRegCapture.cpp").write_bytes(pinned_capture.read_bytes())
            (source_dir / "Immix.cpp").symlink_to(pinned_immix)

            with self.assertRaisesRegex(ValueError, "conservative-root source must be a regular"):
                DIAGNOSTIC.prepare_private_haxelib_overlay(
                    source, temp / "private-haxelib"
                )

        self.assertEqual(hashlib.sha256(pinned_immix.read_bytes()).hexdigest(), original_hash)

    @unittest.skipIf(os.name == 'nt', 'uses Linux native scanner, shell wrappers or ELF cache fixtures')
    def test_asan_cxx_wrapper_logs_and_applies_flags(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            temp = Path(directory)
            fake_compiler = temp / "fake-g++"
            capture = temp / "compiler-argv.txt"
            fake_compiler.write_text("#!/bin/sh\nprintf '%s\\n' \"$@\" > \"" + str(capture) + "\"\n", newline='\n')
            fake_compiler.chmod(0o755)
            argument_log = temp / "asan-arguments"
            wrapper = temp / "asan-cxx"
            wrapper.write_text(
                DIAGNOSTIC.asan_cxx_wrapper_text(fake_compiler, argument_log)
            , newline='\n')
            wrapper.chmod(0o755)
            result = subprocess.run(
                [str(wrapper), "-c", "source with spaces.cpp"],
                cwd=temp,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            argv = capture.read_text().splitlines()
            for flag in DIAGNOSTIC.ASAN_FLAGS:
                self.assertIn(flag, argv)
            self.assertEqual(argv[-2:], ["-c", "source with spaces.cpp"])
            log_files = list(argument_log.glob("*.tsv"))
            self.assertEqual(len(log_files), 1)
            trace = log_files[0].read_text()
            self.assertIn("compiler\t", trace)
            self.assertIn("arg\t-fsanitize=address", trace)
            self.assertIn("arg\tsource with spaces.cpp", trace)

    @unittest.skipIf(os.name == 'nt', 'uses Linux native scanner, shell wrappers or ELF cache fixtures')
    def test_asan_cxx_command_is_absolute_without_checkout_spaces(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            wrapper = Path(directory) / "asan-cxx"
            wrapper.write_text("#!/bin/sh\nexit 0\n", newline='\n')
            wrapper.chmod(0o755)
            root_fd = os.open(ROOT, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                command = DIAGNOSTIC.asan_cxx_command(wrapper, root_fd)
                self.assertTrue(command.startswith("/proc/"))
                self.assertNotIn(" ", command)
                self.assertEqual(Path(command).resolve(), wrapper.resolve())
            finally:
                os.close(root_fd)


if __name__ == "__main__":
    unittest.main()
