"""Exercise release selection and the bundled Windows updater handoff."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class UpdateCheckerTest(unittest.TestCase):
    def test_batch_helper_codegen_selects_urlmon_not_sys_http(self):
        batch = (ROOT / "run.bat").read_text(encoding="utf-8")
        marker = batch.index("\n:build_update_helper")
        helper_section = batch[marker:].splitlines()
        command_line = next(
            line.strip() for line in helper_section
            if line.strip().lower().startswith("call haxe ")
        )
        self.assertRegex(
            command_line,
            r"(?:^|\s)-D\s+windows(?:\s|$)",
            "the standalone Windows helper must compile with Haxe's windows define",
        )
        defines = re.findall(r"(?:^|\s)-D\s+([A-Za-z_][A-Za-z0-9_-]*)", command_line)
        self.assertIn("no-compilation", defines, "helper probe should only generate C++")

        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="windows-updater-codegen-", dir=ROOT / "tmp") as folder:
            generated = Path(folder) / "cpp"
            command = [
                *HAXE_COMMAND,
                "-cp", str(ROOT / "tools/updater"),
                "-cp", str(ROOT / "source"),
                "-main", "CammieUpdateHelper",
                "-cpp", str(generated),
            ]
            for define in defines:
                command.extend(("-D", define))
            env = os.environ.copy()
            env["HAXEPATH"] = str(ROOT / ".tools/haxe")
            env["NEKOPATH"] = str(ROOT / ".tools/neko")
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["PATH"] = os.pathsep.join(
                (env["HAXEPATH"], env["NEKOPATH"], env.get("PATH", ""))
            )
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                (env["NEKOPATH"], env.get("LD_LIBRARY_PATH", ""))
            )
            result = subprocess.run(
                command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=90,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            transport = (generated / "src/WindowsUpdateDownload.cpp").read_text(encoding="utf-8")
            self.assertIn("URLDownloadToFileW", transport)
            self.assertNotIn("sys::Http", transport)
            self.assertNotIn("customRequest", transport)
            self.assertIn("urlmon.h", transport)
            build_xml = (generated / "Build.xml").read_text(encoding="utf-8")
            self.assertIn("urlmon", build_xml.lower(), "URLMon library is not linked")

    def test_progress_reads_persistent_job_and_downloaded_bytes(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        fixture = r'''
import UpdateChecker;
import sys.io.File;
@:access(UpdateChecker)
class Main {
 static function main():Void {
  var root = Sys.getEnv("UPDATER_PROGRESS_FIXTURE");
  var status = root + "/status.txt";
  UpdateChecker.activeStatusPath = status;
  UpdateChecker.activeRelease = {
   tag:"v0.0.1-alpha.8", archiveName:"release.zip", archiveUrl:"", checksumUrl:"",
   sha256:"", sizeBytes:100
  };
  File.saveContent(status, "downloading");
  File.saveContent(root + "/release.zip", StringTools.lpad("", "x", 50));
  var progress = UpdateChecker.installProgress();
  if (progress == null || progress.fraction != 0.5 || !StringTools.contains(progress.label, "50%"))
   throw "download byte progress was not shown";
  for (phase in ["verifying", "extracting", "installing", "rolling-back"]) {
   File.saveContent(status, phase);
   File.saveContent(root + "/progress.json", haxe.Json.stringify({phase:phase,
    completed:25, total:100, files:12, elapsed:10, updatedAt:Date.now().getTime()}));
   progress = UpdateChecker.installProgress();
   if (progress.fraction != 0.25 || progress.indeterminate == true
    || !StringTools.contains(progress.label, "25%")
    || !StringTools.contains(progress.detail, "30s left")
    || !StringTools.contains(progress.detail, "12 files"))
    throw "post-download phase progress was missing: " + phase;
  }
  File.saveContent(status, "extracting");
  File.saveContent(root + "/progress.json", haxe.Json.stringify({phase:"verifying",
   completed:100, total:100}));
  progress = UpdateChecker.installProgress();
  if (progress.fraction != 0 || progress.indeterminate != true)
   throw "previous phase appeared complete while extraction started";
  File.saveContent(root + "/progress.json", "{partial write");
  progress = UpdateChecker.installProgress();
  if (progress.indeterminate != true) throw "partial progress JSON was not tolerated";
  File.saveContent(root + "/progress.json", haxe.Json.stringify({phase:"extracting",
   completed:40, total:100, elapsed:10, updatedAt:Date.now().getTime() - 10000}));
  progress = UpdateChecker.installProgress();
  if (!StringTools.contains(progress.detail, "waiting for progress"))
   throw "stale preparation progress looked active";
  File.saveContent(status, "ready");
  progress = UpdateChecker.installProgress();
  if (progress == null || progress.fraction != 1 || progress.status != "ready")
   throw "ready status did not persist";
  File.saveContent(status, "error:bad archive");
  progress = UpdateChecker.installProgress();
  if (progress == null || progress.label != "bad archive") throw "helper error was hidden";
  UpdateChecker.clearInstallProgress();
  if (UpdateChecker.installProgress() != null) throw "dismissed progress remained visible";
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-D", "windows", "-cp", str(ROOT / "source"),
                 "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT, env={**__import__("os").environ,
                               "UPDATER_PROGRESS_FIXTURE": folder},
                capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_release_selection_and_windows_helper(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        fixture = r'''
import UpdateChecker;
class Main {
 static function check(ok:Bool, message:String):Void {
  if (!ok) throw message;
 }
 static function main():Void {
  var digest = "sha256:" + StringTools.lpad("", "0", 64);
  check(UpdateChecker.compareTags("v0.0.1-alpha.9", "v0.0.1-alpha.10") == -1,
   "legacy numeric prerelease comparison failed");
  check(UpdateChecker.compareTags("v0.0.1-alpha.10", "v0.0.1") == -1,
   "legacy stable release must sort after prerelease");
  check(UpdateChecker.versionFromTag("v0.0.9") != null,
   "numeric release version was rejected");
  check(UpdateChecker.compareTags("v0.0.1-alpha.8", "v0.0.9") == -1,
   "an alpha.8 install must sort below the numeric v0.0.9 release");
  check(UpdateChecker.isNewerTag("v0.0.1-alpha.8", "v0.0.9"),
   "an alpha.8 install must be offered the numeric v0.0.9 release");
  check(UpdateChecker.compareTags("v0.0.9", "v0.0.10") == -1,
   "numeric patch versions must sort numerically across digit widths");
  check(UpdateChecker.isNewerTag("v0.0.9", "v0.0.10"),
   "v0.0.10 must be offered to a v0.0.9 install");
  check(UpdateChecker.archiveFileName("v0.0.10") == "CammieEngine-v0.0.10-windows-x64.zip",
   "numeric release archive name failed");
  check(UpdateChecker.isNewerTag("unknown", "v0.0.9"),
   "unknown installs must be offered the release");
  check(UpdateChecker.archiveFileName("../escape") == null,
   "unsafe release tags must not form an archive name");
  check(UpdateChecker.parseSha256(digest) == StringTools.lpad("", "0", 64),
   "GitHub SHA-256 digest parsing failed");
  check(UpdateChecker.parseSha256("not-a-hash") == null,
   "malformed SHA-256 digest was accepted");
  check(UpdateChecker.formatSize(1073741824) == "1 GB", "release size format failed");

  var releases:Array<Dynamic> = [
   {tag_name:"v0.0.1-alpha.11", draft:true, assets:[
    {name:"CammieEngine-v0.0.1-alpha.11-windows-x64.zip", digest:digest, size:10},
    {name:"SHA256SUMS.txt"}]},
   {tag_name:"v0.0.12", draft:false, prerelease:true, assets:[
    {name:"CammieEngine-v0.0.12-linux-x64.zip", digest:digest, size:10},
    {name:"SHA256SUMS.txt"}]},
   {tag_name:"v0.0.10", draft:false, prerelease:true, assets:[
    {name:"CammieEngine-v0.0.10-windows-x64.zip", digest:digest, size:1073741824},
    {name:"SHA256SUMS.txt"}]},
   {tag_name:"v0.0.9", draft:false, prerelease:true, assets:[
    {name:"CammieEngine-v0.0.9-windows-x64.zip", digest:digest, size:50},
    {name:"SHA256SUMS.txt"}]},
   {tag_name:"v0.0.1-alpha.8", draft:false, prerelease:true, assets:[
    {name:"CammieEngine-v0.0.1-alpha.8-windows-x64.zip", digest:digest, size:30},
    {name:"SHA256SUMS.txt"}]},
   {tag_name:"v0.0.13", draft:false, prerelease:true, assets:[
    {name:"CammieEngine-v0.0.13-windows-x64.zip", size:50},
    {name:"SHA256SUMS.txt"}]}
  ];
  var selected = UpdateChecker.parseLatestRelease(haxe.Json.stringify(releases));
  check(selected != null && selected.tag == "v0.0.10",
   "release selection did not accept numeric prereleases or filter draft, platform, and checksum metadata");
  check(UpdateChecker.isNewerTag("v0.0.1-alpha.8", selected.tag),
   "the selected numeric prerelease was not newer than a legacy alpha.8 install");
  check(selected.sizeBytes == 1073741824, "release asset size was lost");

 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-D", "windows", "-cp", str(ROOT / "source"),
                 "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        source = (ROOT / "source/UpdateChecker.hx").read_text()
        for required in (
            "CammieUpdateHelper.exe",
            "File.copy(helperSource, helperPath)",
            "new sys.io.Process(helperPath",
            "Std.string(gamePid())",
            "WindowsUpdateDownload.getText(RELEASES_API)",
        ):
            self.assertIn(required, source)
        self.assertNotIn("powershell.exe", source.lower())
        self.assertNotIn("install-update.ps1", source.lower())
        transport = (ROOT / "source/WindowsUpdateDownload.hx").read_text()
        self.assertIn("URLDownloadToFileW", transport)
        self.assertIn("-lurlmon", transport)

    def test_settings_warn_about_preserved_assets_and_dismiss_stale_check(self):
        settings = (ROOT / "source/SaveDataState.hx").read_text(encoding="utf-8")
        self.assertIn("Existing asset files stay in place", settings)
        self.assertIn("static asset changes require a manual clean install", settings)
        self.assertIn("if (updateCheckRequestId < 0) return;", settings)
        self.assertIn("if (updateDialogMode == 'checking') updateCheckRequestId = -1;", settings)
        self.assertIn("updateDialogMode == 'progress' || updateDialogMode == 'ready'", settings)


if __name__ == "__main__":
    unittest.main()
