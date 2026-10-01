"""Streaming and transactional tests for the standalone Windows updater helper."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
TAG = "v0.0.2-alpha.1"
ARCHIVE_NAME = f"CammieEngine-{TAG}-windows-x64.zip"
PREFIX = "CammieEngine-windows-x64/"


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
        (install_root / "Funkin.exe").write_text("old-game")
        (install_root / "CammieUpdateHelper.exe").write_text("old-helper")
        (install_root / "RELEASE_TAG").write_text("v0.0.1-alpha.5\n")
        (install_root / "assets/data").mkdir(parents=True)
        (install_root / "assets/data/options.json").write_text("user-settings")
        (install_root / "assets/imported_mods/user").mkdir(parents=True)
        (install_root / "assets/imported_mods/user/chart.json").write_text("imported-chart")

        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as package:
            package.writestr(PREFIX + "Funkin.exe", "new-game")
            package.writestr(PREFIX + "CammieUpdateHelper.exe", "new-helper")
            package.writestr(PREFIX + "lime.ndll", "new-runtime")
            package.writestr(PREFIX + "assets/data/options.json", "release-default-settings")
            package.writestr(PREFIX + "assets/data/engine-code.txt", "new-engine-asset")
            package.writestr(PREFIX + "assets/imported_mods/user/chart.json", "release-chart")
            package.writestr(PREFIX + "RELEASE_TAG", tag + "\n")

        digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        checksum_path.write_text(f"{digest} *{ARCHIVE_NAME}\n")
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
        fixture.write_text(FIXTURE.replace("@ARCHIVE@", ARCHIVE_NAME).replace("@TAG@", tag))
        result = subprocess.run(
            [str(HAXE), "-D", "updater_test", "-cp", str(ROOT / "tools/updater"),
             "-cp", str(ROOT / "source"),
             "-cp", str(directory), "-main", "Main", "--interp"],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
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


if __name__ == "__main__":
    unittest.main()
