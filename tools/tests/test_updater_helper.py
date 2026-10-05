"""Streaming and transactional tests for the standalone Windows updater helper."""

from __future__ import annotations
from haxe_test_support import HAXE_COMMAND

import hashlib
import json
import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import random
import subprocess
import tempfile
import unittest
import zipfile
import ctypes
from contextlib import contextmanager
from haxe_test_support import TEST_TMP


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
TAG = "v0.0.2-alpha.1"
ARCHIVE_NAME = f"CammieEngine-{TAG}-windows-x64.zip"
PREFIX = "CammieEngine-windows-x64/"


NATIVE_FIXTURE = r'''import CammieUpdateHelper;

class Main {
 static function main():Void {
  var args = Sys.args();
  try {
   switch args[0] {
    case "install":
     CammieUpdateHelper.runLocalInstallTest(args.slice(1));
    case "extract":
     var result = CammieUpdateHelper.extractArchive(args[1], args[2], args[3]);
     Sys.println("EXTRACTED:" + result);
    default: throw "unknown native updater test mode";
   }
  } catch (error:Dynamic) {
   Sys.println("error:" + Std.string(error));
   Sys.exit(1);
  }
 }
}'''


FIXTURE = r'''import CammieUpdateHelper;
import haxe.Json;
import sys.FileSystem;
import sys.io.File;

class Main {
 static function check(ok:Bool, message:String):Void {
  if (!ok) throw message;
 }

 static function main():Void {
  check(CammieUpdateHelper.safeEntryPath("CammieEngine-windows-x64/assets/data/a.json").relative
   == "assets/data/a.json", "valid payload path was rejected");
  check(CammieUpdateHelper.safeEntryPath("../escape") == null, "parent path was accepted");
  check(CammieUpdateHelper.safeEntryPath("CammieEngine-windows-x64/C:/escape") == null,
   "drive path was accepted");
  check(CammieUpdateHelper.isProtectedRelative("assets/data/options.json"), "assets were not protected");
  check(CammieUpdateHelper.isProtectedRelative("imported_mods/user/song.json"),
   "imported mods were not protected");
  check(!CammieUpdateHelper.isProtectedRelative("Funkin.exe"), "runtime files were incorrectly protected");

  var digest = Sys.getEnv("UPDATER_TEST_DIGEST");
  var archiveDigest = Sys.getEnv("UPDATER_TEST_ARCHIVE_DIGEST");
  var archive = Sys.getEnv("UPDATER_TEST_ARCHIVE");
  var installRoot = Sys.getEnv("UPDATER_TEST_INSTALL_ROOT");
  var checksumPath = Sys.getEnv("UPDATER_TEST_CHECKSUMS");
  var statusPath = Sys.getEnv("UPDATER_TEST_STATUS");
  var mode = Sys.getEnv("UPDATER_TEST_MODE");
  var args:Array<String> = cast Json.parse(Sys.getEnv("UPDATER_TEST_ARGS"));

  check(CammieUpdateHelper.sha256File(Sys.getEnv("UPDATER_TEST_HASH_INPUT")) == digest,
   "streaming SHA-256 did not match the expected digest");
  check(CammieUpdateHelper.parseSidecarHash(File.getContent(checksumPath), "@ARCHIVE@")
   == archiveDigest, "release sidecar failed verification");
  check(CammieUpdateHelper.parseSidecarHash(File.getContent(checksumPath) + archiveDigest + "  @ARCHIVE@\n",
   "@ARCHIVE@") == null, "duplicate checksum entries were accepted");
  CammieUpdateHelper.validateArguments("Funkin.exe", ".",
   "https://github.com/UwUCammie/CammieEngine/releases/download/@TAG@/@ARCHIVE@",
   "https://github.com/UwUCammie/CammieEngine/releases/download/@TAG@/SHA256SUMS.txt",
   "@ARCHIVE@", archiveDigest, "@TAG@");

  if (mode == "success") {
   CammieUpdateHelper.runLocalInstallTest(args);
   check(File.getContent(installRoot + "/Funkin.exe") == "new-game", "game executable was not updated");
   check(File.getContent(installRoot + "/CammieUpdateHelper.exe") == "new-helper",
    "the updater did not replace itself");
   check(File.getContent(installRoot + "/RELEASE_TAG") == "@TAG@\n", "release tag was not committed");
   check(File.getContent(installRoot + "/assets/data/options.json") == "user-settings",
    "the user's settings were overwritten");
   check(File.getContent(installRoot + "/assets/imported_mods/user/chart.json") == "imported-chart",
    "the user's imported content was overwritten");
   check(File.getContent(installRoot + "/import-cache/snapshot/source/mod.unknown") == "retained-source",
    "the user's standalone raw-source cache was overwritten");
   check(File.getContent(installRoot + "/assets/data/engine-code.txt") == "new-engine-asset",
    "a new release asset was not installed");
   check(StringTools.trim(File.getContent(statusPath)) == "complete", "success status was not written");
  } else {
   var failed = false;
   try CammieUpdateHelper.runLocalInstallTest(args) catch (_:Dynamic) failed = true;
   check(failed, "injected installation failure did not occur");
   check(File.getContent(installRoot + "/Funkin.exe") == "old-game", "rollback did not restore the game executable");
   check(File.getContent(installRoot + "/CammieUpdateHelper.exe") == "old-helper",
    "rollback did not restore the updater executable");
   check(File.getContent(installRoot + "/RELEASE_TAG") == "v0.0.1-alpha.5\n",
    "rollback changed the installed release tag");
   check(File.getContent(installRoot + "/assets/data/options.json") == "user-settings",
    "rollback changed user settings");
   check(File.getContent(installRoot + "/assets/imported_mods/user/chart.json") == "imported-chart",
    "rollback changed imported content");
   check(File.getContent(installRoot + "/import-cache/snapshot/source/mod.unknown") == "retained-source",
    "rollback changed the user's standalone raw-source cache");
   check(!FileSystem.exists(installRoot + "/assets/data/engine-code.txt"),
    "rollback left behind a newly installed file");
   check(StringTools.startsWith(StringTools.trim(File.getContent(statusPath)), "error:"),
    "failure status was not written");
  }
 }
}'''


class UpdaterHelperTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HAXE.is_file():
            raise unittest.SkipTest("portable Haxe toolchain is unavailable")

    def run_fixture(self, directory: Path, mode: str, fail_after: int | None = None):
        tag = TAG
        archive_path = directory / ARCHIVE_NAME
        checksum_path = directory / "SHA256SUMS.txt"
        install_root = directory / "install"
        install_root.mkdir()
        (install_root / "Funkin.exe").write_text("old-game", newline='\n')
        (install_root / "CammieUpdateHelper.exe").write_text("old-helper", newline='\n')
        (install_root / "RELEASE_TAG").write_text("v0.0.1-alpha.5\n", newline='\n')
        (install_root / "assets/data").mkdir(parents=True)
        (install_root / "assets/data/options.json").write_text("user-settings", newline='\n')
        (install_root / "assets/imported_mods/user").mkdir(parents=True)
        (install_root / "assets/imported_mods/user/chart.json").write_text("imported-chart", newline='\n')
        (install_root / "import-cache/snapshot/source").mkdir(parents=True)
        (install_root / "import-cache/snapshot/source/mod.unknown").write_text("retained-source", newline='\n')
        (install_root / "Templates").mkdir(parents=True)
        identical_font = install_root / "Templates/funkin.otf"
        identical_font.write_bytes(b"same-font")
        old_font_time = 1_650_000_000_000_000_000
        os.utime(identical_font, ns=(old_font_time, old_font_time))
        self._identical_font_time = identical_font.stat().st_mtime_ns

        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as package:
            package.writestr(PREFIX + "Funkin.exe", "new-game")
            package.writestr(PREFIX + "CammieUpdateHelper.exe", "new-helper")
            package.writestr(PREFIX + "lime.ndll", "new-runtime")
            package.writestr(PREFIX + "assets/data/options.json", "release-default-settings")
            package.writestr(PREFIX + "assets/data/engine-code.txt", "new-engine-asset")
            package.writestr(PREFIX + "Templates/funkin.otf", b"same-font")
            package.writestr(PREFIX + "assets/imported_mods/user/chart.json", "release-chart")
            package.writestr(PREFIX + "RELEASE_TAG", tag + "\n")

        digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        checksum_path.write_text(f"{digest} *{ARCHIVE_NAME}\n", newline='\n')
        status_path = directory / "status.txt"
        large_input = directory / "hash-input.bin"
        large_input.write_bytes((bytes(range(251)) * 9000) + b"sha256-stream-end")
        large_digest = hashlib.sha256(large_input.read_bytes()).hexdigest()
        args = [str(archive_path), str(checksum_path), str(install_root), tag, digest,
                str(status_path), str(fail_after) if fail_after is not None else "-1"]
        env = {
            **__import__("os").environ,
            "UPDATER_TEST_MODE": mode,
            "UPDATER_TEST_ARCHIVE": str(archive_path),
            "UPDATER_TEST_CHECKSUMS": str(checksum_path),
            "UPDATER_TEST_INSTALL_ROOT": str(install_root),
            "UPDATER_TEST_STATUS": str(status_path),
            "UPDATER_TEST_DIGEST": large_digest,
            "UPDATER_TEST_ARCHIVE_DIGEST": digest,
            "UPDATER_TEST_HASH_INPUT": str(large_input),
            "UPDATER_TEST_ARGS": json.dumps(args),
        }
        fixture = directory / "Main.hx"
        fixture.write_text(FIXTURE.replace("@ARCHIVE@", ARCHIVE_NAME).replace("@TAG@", tag), newline='\n')
        result = subprocess.run(
            [*HAXE_COMMAND, "-D", "updater_test", "-cp", str(ROOT / "tools/updater"),
             "-cp", str(ROOT / "source"),
             "-cp", str(directory), "-main", "Main", "--interp"],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((install_root / "Templates/funkin.otf").stat().st_mtime_ns,
                         self._identical_font_time, "an identical installed font was unnecessarily replaced")
        return install_root

    def test_streaming_verified_update_preserves_user_content_and_replaces_helper(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            install_root = self.run_fixture(Path(folder), "success")
            self.assertEqual((install_root / "Funkin.exe").read_text(), "new-game")

    def test_install_failure_rolls_back_files_and_keeps_user_data(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            install_root = self.run_fixture(Path(folder), "rollback", fail_after=4)
            self.assertEqual((install_root / "Funkin.exe").read_text(), "old-game")


@unittest.skipUnless(os.name == "nt", "native updater ZIP regression requires Windows")
class NativeUpdaterHelperTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = ROOT / ".tools/llvm-mingw-windows"
        hxcpp = ROOT / ".haxelib/hxcpp/4,3,2"
        if not HAXE.is_file() or not hxcpp.is_dir() \
                or not (compiler / "bin/x86_64-w64-mingw32-clang++.exe").is_file():
            raise unittest.SkipTest("native Windows hxcpp/zlib toolchain is unavailable")
        cls.build_temp = tempfile.TemporaryDirectory(prefix="updater-native-", dir=TEST_TMP)
        cls.work = Path(cls.build_temp.name)
        (cls.work / "Main.hx").write_text(NATIVE_FIXTURE, encoding="utf-8", newline="\n")
        cls.environment = {
            **os.environ,
            "HAXEPATH": str(HAXE.parent),
            "NEKOPATH": str(ROOT / ".tools/neko"),
            "HAXELIB_PATH": str(ROOT / ".haxelib"),
            "MINGW_ROOT": str(compiler),
            "HXCPP_MINGW_EXE": "x86_64-w64-mingw32-clang++.exe",
            "HXCPP_AR": "llvm-ar.exe",
            "HXCPP_RANLIB": "llvm-ranlib.exe",
            "HXCPP_STRIP": "llvm-strip.exe",
            "HXCPP_RC": "llvm-windres.exe",
            "PATH": os.pathsep.join((str(HAXE.parent), str(ROOT / ".tools/neko"),
                                      str(compiler / "bin"), os.environ.get("PATH", ""))),
        }
        cpp_dir = cls.work / "cpp"
        compile_result = subprocess.run(
            [str(HAXE), "-cp", str(ROOT / "tools/updater"), "-cp", str(ROOT / "source"),
             "-cp", str(cls.work), "-main", "Main", "-cpp", str(cpp_dir),
             "-D", "updater_test", "-D", "windows", "-D", "HXCPP_M64", "-D", "HXCPP_MINGW",
             "-D", "HXCPP_RC=llvm-windres.exe"],
            cwd=ROOT, env=cls.environment, capture_output=True, text=True, timeout=120)
        if compile_result.returncode:
            cls.build_temp.cleanup()
            raise AssertionError(compile_result.stdout + compile_result.stderr)
        cls.binary = cpp_dir / "Main.exe"
        if not cls.binary.is_file():
            cls.build_temp.cleanup()
            raise AssertionError("native updater fixture build did not produce Main.exe")
        runtime = ROOT / "export/release/windows/bin"
        for name in ("libc++.dll", "libunwind.dll", "libwinpthread-1.dll"):
            source = runtime / name
            if not source.is_file():
                cls.build_temp.cleanup()
                raise unittest.SkipTest(f"native Windows runtime dependency is unavailable: {name}")
            import shutil
            shutil.copy2(source, cpp_dir / name)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "build_temp"):
            cls.build_temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="updater-case-", dir=TEST_TMP)
        self.base = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def make_archive(self, name="native-package.zip", *, corrupt_crc=False, collision=False,
                     truncate_payload=False):
        archive = self.base / name
        tag = "v0.0.2-alpha.1"
        entries = [
            (PREFIX + "Funkin.exe", b"new-game" * 9000, zipfile.ZIP_STORED),
            (PREFIX + "CammieUpdateHelper.exe", b"new-helper", zipfile.ZIP_DEFLATED),
            (PREFIX + "lime.ndll", b"runtime-" + random.Random(4722).randbytes(220_000), zipfile.ZIP_DEFLATED),
            (PREFIX + "assets/data/engine-code.txt", b"new-engine-asset", zipfile.ZIP_DEFLATED),
            (PREFIX + "Templates/funkin.otf", b"same-font", zipfile.ZIP_STORED),
            (PREFIX + "RELEASE_TAG", (tag + "\n").encode(), zipfile.ZIP_DEFLATED),
        ]
        if collision:
            entries.extend([
                (PREFIX + "assets/collision", b"file", zipfile.ZIP_STORED),
                (PREFIX + "assets/collision/child.bin", b"child", zipfile.ZIP_STORED),
            ])
        with zipfile.ZipFile(archive, "w") as package:
            for path, contents, method in entries:
                package.writestr(path, contents, compress_type=method)
        if corrupt_crc or truncate_payload:
            with zipfile.ZipFile(archive) as package:
                info = package.getinfo(PREFIX + "lime.ndll" if truncate_payload else PREFIX + "assets/data/engine-code.txt")
                with archive.open("r+b") as stream:
                    stream.seek(info.header_offset + 14)
                    crc = stream.read(4)
                    if corrupt_crc:
                        stream.seek(info.header_offset + 14)
                        stream.write(bytes([crc[0] ^ 0x01]) + crc[1:])
                    if truncate_payload:
                        stream.seek(info.header_offset + 26)
                        name_len = int.from_bytes(stream.read(2), "little")
                        extra_len = int.from_bytes(stream.read(2), "little")
                        data_start = info.header_offset + 30 + name_len + extra_len
                        stream.seek(data_start + max(1, info.compress_size // 2))
                        stream.truncate()
        return archive, tag

    def extract(self, archive, tag):
        stage = self.base / "expanded"
        result = subprocess.run([str(self.binary), "extract", str(archive), str(stage), tag],
                                capture_output=True, text=True, timeout=60)
        return result, stage

    def test_native_zlib_extracts_large_deflated_and_stored_entries(self):
        archive, tag = self.make_archive()
        result, stage = self.extract(archive, tag)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = stage / "CammieEngine-windows-x64"
        self.assertEqual((payload / "Funkin.exe").read_bytes(), b"new-game" * 9000)
        self.assertEqual((payload / "lime.ndll").read_bytes()[8:], random.Random(4722).randbytes(220_000))
        self.assertEqual((payload / "assets/data/engine-code.txt").read_bytes(), b"new-engine-asset")

    def test_native_extractor_rejects_bad_crc_truncation_and_path_collision(self):
        for name, options, expected in (
            ("crc.zip", {"corrupt_crc": True}, "CRC"),
            ("truncated.zip", {"truncate_payload": True}, None),
            ("collision.zip", {"collision": True}, "collision"),
        ):
            with self.subTest(name=name):
                archive, tag = self.make_archive(name, **options)
                result, stage = self.extract(archive, tag)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                if expected:
                    self.assertIn(expected.lower(), result.stdout.lower() + result.stderr.lower())
                self.assertFalse(stage.exists(), "failed extraction left its partial stage tree")

    @contextmanager
    def deny_delete_lock(self, path):
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                                ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
        create_file.restype = ctypes.c_void_p
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [ctypes.c_void_p]
        close_handle.restype = ctypes.c_int
        handle = create_file(str(path), 0x80000000, 0x00000001, None, 3, 0x80, None)
        invalid = ctypes.c_void_p(-1).value
        self.assertNotIn(handle, (None, invalid), f"could not lock test file: {ctypes.get_last_error()}")
        try:
            yield
        finally:
            close_handle(handle)

    def install_args(self, archive, tag, install):
        checksum = self.base / "SHA256SUMS.txt"
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        checksum.write_text(f"{digest} *CammieEngine-{tag}-windows-x64.zip\n", newline="\n")
        status = self.base / "status.txt"
        return [str(archive), str(checksum), str(install), tag, digest, str(status), "-1"]

    def install(self, archive, tag, install):
        return subprocess.run([str(self.binary), "install", *self.install_args(archive, tag, install)],
                              capture_output=True, text=True, timeout=60)

    def test_native_update_keeps_locked_identical_font_untouched(self):
        archive, tag = self.make_archive()
        install = self.base / "install"
        install.mkdir()
        (install / "Funkin.exe").write_bytes(b"old-game")
        (install / "CammieUpdateHelper.exe").write_bytes(b"old-helper")
        (install / "RELEASE_TAG").write_text("v0.0.1-alpha.5\n")
        font = install / "Templates/funkin.otf"
        font.parent.mkdir(parents=True)
        font.write_bytes(b"same-font")
        old_time = 1_650_000_000_000_000_000
        os.utime(font, ns=(old_time, old_time))
        with self.deny_delete_lock(font):
            result = self.install(archive, tag, install)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(font.read_bytes(), b"same-font")
        self.assertEqual(font.stat().st_mtime_ns, old_time)
        self.assertEqual((install / "Funkin.exe").read_bytes(), b"new-game" * 9000)

    def test_native_locked_changed_font_fails_and_rolls_back_only_mutations(self):
        archive, tag = self.make_archive()
        install = self.base / "install"
        install.mkdir()
        game = install / "Funkin.exe"
        game.write_bytes(b"old-game")
        (install / "CammieUpdateHelper.exe").write_bytes(b"old-helper")
        (install / "RELEASE_TAG").write_text("v0.0.1-alpha.5\n")
        font = install / "Templates/funkin.otf"
        font.parent.mkdir(parents=True)
        font.write_bytes(b"locked-old-font")
        with self.deny_delete_lock(font):
            result = self.install(archive, tag, install)
        combined = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, combined)
        self.assertIn("Could not replace Templates/funkin.otf", combined)
        self.assertNotIn("Rollback also failed", combined)
        self.assertEqual(game.read_bytes(), b"old-game", "earlier executable mutation was not restored")
        self.assertEqual(font.read_bytes(), b"locked-old-font", "the locked file was changed")
        self.assertEqual((install / "CammieUpdateHelper.exe").read_bytes(), b"old-helper")
        self.assertFalse(list(install.rglob("*.cammie-update-tmp-*")), "install left a sibling temp file")
        self.assertFalse(list(install.rglob("*.cammie-rollback-tmp-*")), "rollback left a sibling temp file")


if __name__ == "__main__":
    unittest.main()
