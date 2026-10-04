import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("ensure_lime_uncapped", ROOT / "tools/ensure_lime_uncapped.py")
ensure = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ensure
SPEC.loader.exec_module(ensure)


def completed(args, output="", code=0, error=""):
    return CompletedProcess(args, code, output, error)


def pe64(marker=b""):
    data = bytearray(160)
    data[0:2] = b"MZ"
    data[0x3C:0x40] = (64).to_bytes(4, "little")
    data[64:68] = b"PE\0\0"
    data[68:70] = (0x8664).to_bytes(2, "little")
    return bytes(data) + marker


class EnsureLimeUncappedTest(unittest.TestCase):
    def test_platform_mapping_uses_hxcpp_defines_and_native_output_folders(self):
        mingw = {"HXCPP_MINGW_EXE": "x86_64-w64-mingw32-clang++.exe"}
        windows = ensure.build_target("windows", "64", mingw)
        self.assertEqual("Windows64", windows.output_folder)
        self.assertEqual(("-Dwindows", "-DHXCPP_M64", "-DHXCPP_MINGW"), windows.hxcpp_flags)
        self.assertEqual(
            [str(Path("C:/tools/haxelib.exe")), "run", "hxcpp", "Build.xml", "-Dwindows", "-DHXCPP_M64", "-DHXCPP_MINGW"],
            ensure.build_command(Path("C:/tools/haxelib.exe"), windows),
        )
        self.assertEqual(("-Dwindows", "-DHXCPP_M32", "-DHXCPP_MINGW"), ensure.build_target("windows", "32", mingw).hxcpp_flags)
        self.assertEqual(("-Dlinux", "-DHXCPP_M64"), ensure.build_target("linux", "64").hxcpp_flags)
        self.assertEqual("Linux64", ensure.build_target("linux", "arm64").output_folder)
        self.assertEqual("MacArm64", ensure.build_target("mac", "arm64").output_folder)
        self.assertEqual(("-Dmac", "-DHXCPP_M32"), ensure.build_target("mac", "32").hxcpp_flags)

    def test_compiler_and_hxcpp_input_changes_invalidate_their_fingerprints(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            compiler = root / "clang++.exe"
            compiler.write_bytes(b"compiler build A")
            first_compiler = ensure._tool_record(str(compiler), {})
            compiler.write_bytes(b"compiler build B with a different size")
            self.assertNotEqual(first_compiler, ensure._tool_record(str(compiler), {}))

            hxcpp = root / "hxcpp"
            source = hxcpp / "src/BuildInput.hx"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"class BuildInput {}")
            first_hxcpp = ensure._tree_fingerprint(hxcpp)
            source.write_bytes(b"class BuildInput { static var changed = true; }")
            self.assertNotEqual(first_hxcpp, ensure._tree_fingerprint(hxcpp))

    def test_haxelib_validation_is_read_only_and_requires_the_repository_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            haxe = root / "portable-haxe"
            haxe.mkdir()
            (haxe / ("haxelib.exe" if os.name == "nt" else "haxelib")).write_bytes(b"stub")
            library_root = root / ".haxelib"
            lime = library_root / "lime" / "8,3,2"
            hxcpp = library_root / "hxcpp" / "4,3,2"
            lime.mkdir(parents=True)
            hxcpp.mkdir(parents=True)
            env = {"HAXEPATH": str(haxe), "HAXELIB_PATH": str(library_root)}
            calls = []

            def runner(args, **kwargs):
                calls.append(args)
                if args[1:] == ["config"]:
                    return completed(args, str(library_root) + os.sep + "\n")
                name = args[-1]
                package = lime if name == "lime" else hxcpp
                version = "8.3.2" if name == "lime" else "4.3.2"
                return completed(args, f"-L {package / 'ndll'}\n{package / 'src'}\n-D {name}={version}\n")

            selected = ensure.verify_haxelib_selection(env, runner)
            self.assertEqual(lime.resolve(), selected.lime_package)
            self.assertEqual(hxcpp.resolve(), selected.hxcpp_package)
            self.assertFalse(any("set" in call for call in calls))

            def wrong_lime(args, **kwargs):
                if args[1:] == ["path", "lime"]:
                    return completed(args, f"-L {library_root / 'lime' / '8,0,2' / 'ndll'}\n-D lime=8.0.2\n")
                return runner(args, **kwargs)

            with self.assertRaisesRegex(ensure.LimeUncappedError, "selected lime version is not 8.3.2"):
                ensure.verify_haxelib_selection(env, wrong_lime)

    def test_first_checkout_clones_tag_with_anonymous_shallow_pinned_submodules(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            calls = []

            def runner(args, **kwargs):
                calls.append((list(args), kwargs))
                if "clone" in args:
                    clone_path = Path(args[-1])
                    (clone_path / ".git").mkdir(parents=True)
                    return completed(args)
                if "rev-parse" in args:
                    return completed(args, ensure.LIME_COMMIT + "\n")
                if args[-3:] == ["submodule", "status", "--recursive"]:
                    return completed(args, "")
                if "status" in args:
                    return completed(args, "")
                raise AssertionError(args)

            source = ensure.ensure_source_checkout(root, env=os.environ, runner=runner)
            self.assertTrue((source / ".git").is_dir())
            clone_args, clone_kwargs = next(item for item in calls if "clone" in item[0])
            self.assertIn("--depth=1", clone_args)
            self.assertIn("--recurse-submodules", clone_args)
            self.assertIn("--shallow-submodules", clone_args)
            self.assertIn("--branch", clone_args)
            self.assertIn(ensure.LIME_TAG, clone_args)
            self.assertIn("credential.helper=", clone_args)
            self.assertEqual("0", clone_kwargs["env"]["GIT_TERMINAL_PROMPT"])
            self.assertIn(ensure.LIME_REPOSITORY, clone_args)

    def test_cached_library_hash_mismatch_rebuilds_and_replaces_package_atomically(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / ".tools/lime-8.3.2-source"
            package = root / ".haxelib/lime/8,3,2"
            source_binary = source / "ndll/Windows64/lime.ndll"
            package_binary = package / "ndll/Windows64/lime.ndll"
            source_binary.parent.mkdir(parents=True)
            package_binary.parent.mkdir(parents=True)
            source_binary.write_bytes(pe64(b"original"))
            package_binary.write_bytes(pe64(b"old-package"))
            target = ensure.build_target("windows", "64", {"HXCPP_MINGW_EXE": "clang++"})
            metadata_path = ensure._metadata_path(root, target)
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            metadata_path.write_text(json.dumps({
                "schema": ensure.CACHE_SCHEMA,
                "input_fingerprint": "same-inputs",
                "artifact_sha256": hashlib.sha256(source_binary.read_bytes()).hexdigest(),
            }), encoding="utf-8")
            # A checksum mismatch in the cached native artifact must rebuild,
            # even when the old bytes still form a structurally valid PE file.
            source_binary.write_bytes(pe64(b"tampered"))
            selection = ensure.HaxelibSelection(root / "haxelib.exe", root / ".haxelib", package, root / "hxcpp", "4.3.2")
            calls = []

            def runner(args, **kwargs):
                calls.append(args)
                source_binary.write_bytes(pe64(b"rebuilt"))
                return completed(args)

            with patch.object(ensure, "verify_haxelib_selection", return_value=selection):
                result, rebuilt = ensure._build_or_reuse(root, source, selection, target, "same-inputs", {}, runner)
            self.assertTrue(rebuilt)
            self.assertEqual(package_binary, result)
            self.assertEqual(pe64(b"rebuilt"), package_binary.read_bytes())
            self.assertEqual(1, len(calls))
            self.assertEqual([str(selection.haxelib), "run", "hxcpp", "Build.xml", "-Dwindows", "-DHXCPP_M64", "-DHXCPP_MINGW"], calls[0])
            saved = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(hashlib.sha256(package_binary.read_bytes()).hexdigest(), saved["artifact_sha256"])

    def test_valid_native_cache_repairs_tampered_haxelib_copy_without_recompiling(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / ".tools/lime-8.3.2-source"
            package = root / ".haxelib/lime/8,3,2"
            source_binary = source / "ndll/Windows64/lime.ndll"
            package_binary = package / "ndll/Windows64/lime.ndll"
            source_binary.parent.mkdir(parents=True)
            package_binary.parent.mkdir(parents=True)
            good = pe64(b"verified cache")
            source_binary.write_bytes(good)
            package_binary.write_bytes(pe64(b"modified package copy"))
            target = ensure.build_target("windows", "64")
            metadata_path = ensure._metadata_path(root, target)
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            metadata_path.write_text(json.dumps({
                "schema": ensure.CACHE_SCHEMA,
                "input_fingerprint": "current",
                "artifact_sha256": hashlib.sha256(good).hexdigest(),
            }), encoding="utf-8")
            selection = ensure.HaxelibSelection(root / "haxelib.exe", root / ".haxelib", package, root / "hxcpp", "4.3.2")

            def unexpected_build(*args, **kwargs):
                self.fail("valid checksum-pinned native cache should not rebuild")

            result, rebuilt = ensure._build_or_reuse(root, source, selection, target, "current", {}, unexpected_build)
            self.assertFalse(rebuilt)
            self.assertEqual(package_binary, result)
            self.assertEqual(good, package_binary.read_bytes())

    def test_failed_native_build_does_not_replace_installed_library_or_write_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / ".tools/lime-8.3.2-source"
            package = root / ".haxelib/lime/8,3,2"
            source_binary = source / "ndll/Windows64/lime.ndll"
            package_binary = package / "ndll/Windows64/lime.ndll"
            source_binary.parent.mkdir(parents=True)
            package_binary.parent.mkdir(parents=True)
            source_binary.write_bytes(b"partial linker output")
            previous = pe64(b"previous working library")
            package_binary.write_bytes(previous)
            target = ensure.build_target("windows", "64")
            selection = ensure.HaxelibSelection(root / "haxelib.exe", root / ".haxelib", package, root / "hxcpp", "4.3.2")
            metadata_path = ensure._metadata_path(root, target)

            def failed_build(args, **kwargs):
                return completed(args, "compiler error", code=1)

            with self.assertRaisesRegex(ensure.LimeUncappedError, "installed library was left unchanged"):
                ensure._build_or_reuse(root, source, selection, target, "new-inputs", {}, failed_build)
            self.assertEqual(previous, package_binary.read_bytes())
            self.assertFalse(metadata_path.exists())

    def test_source_identity_and_allowlist_reject_unexpected_library_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "lime"
            (source / ".git").mkdir(parents=True)
            path_a = "project/src/backend/sdl/SDLApplication.cpp"
            path_b = "project/src/text/Font.cpp"
            content_a, content_b = b"patched sdl", b"patched font"
            for name, data in ((path_a, content_a), (path_b, content_b)):
                destination = source / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)

            class FakePatcher:
                PATCHED_PATHS = (path_a, path_b)
                PATCHED_SHA256 = hashlib.sha256(content_a).hexdigest()
                FONT_PATCHED_SHA256 = hashlib.sha256(content_b).hexdigest()

                @staticmethod
                def patch_file(_root):
                    return False

            status = f" M {path_a}\n M {path_b}\n"

            def runner(args, **kwargs):
                if "rev-parse" in args:
                    return completed(args, ensure.LIME_COMMIT + "\n")
                if args[-3:] == ["submodule", "status", "--recursive"]:
                    return completed(args, "")
                if "status" in args:
                    return completed(args, status)
                raise AssertionError(args)

            with patch.object(ensure, "_normalized_hash", side_effect=lambda data: hashlib.sha256(data).hexdigest()):
                _, clean_status = ensure._verify_source_checkout(source, root, {}, runner, FakePatcher)
                self.assertIn(path_a, clean_status)
                status = f" M {path_a}\n M {path_b}\n M project/src/unexpected.cpp\n"
                with self.assertRaisesRegex(ensure.LimeUncappedError, "unexpected source modifications"):
                    ensure._verify_source_checkout(source, root, {}, runner, FakePatcher)


if __name__ == "__main__":
    unittest.main()
