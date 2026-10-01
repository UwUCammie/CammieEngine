"""Exercise release selection and the bundled Windows updater handoff."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class UpdateCheckerTest(unittest.TestCase):
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
            Path(folder, "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-D", "windows", "-cp", str(ROOT / "source"),
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
   "numeric prerelease comparison failed");
  check(UpdateChecker.compareTags("v0.0.1-alpha.10", "v0.0.1") == -1,
   "stable release must sort after prerelease");
  check(UpdateChecker.isNewerTag("unknown", "v0.0.1-alpha.10"),
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
   {tag_name:"v0.0.1-alpha.12", draft:false, assets:[
    {name:"CammieEngine-v0.0.1-alpha.12-linux-x64.zip", digest:digest, size:10},
    {name:"SHA256SUMS.txt"}]},
   {tag_name:"v0.0.1-alpha.10", draft:false, assets:[
    {name:"CammieEngine-v0.0.1-alpha.10-windows-x64.zip", digest:digest, size:1073741824},
    {name:"SHA256SUMS.txt"}]},
   {tag_name:"v0.0.1-alpha.9", draft:false, assets:[
    {name:"CammieEngine-v0.0.1-alpha.9-windows-x64.zip", digest:digest, size:50},
    {name:"SHA256SUMS.txt"}]},
   {tag_name:"v0.0.1-alpha.13", draft:false, assets:[
    {name:"CammieEngine-v0.0.1-alpha.13-windows-x64.zip", size:50},
    {name:"SHA256SUMS.txt"}]}
  ];
  var selected = UpdateChecker.parseLatestRelease(haxe.Json.stringify(releases));
  check(selected != null && selected.tag == "v0.0.1-alpha.10",
   "release selection did not filter draft, platform, and checksum metadata");
  check(selected.sizeBytes == 1073741824, "release asset size was lost");

 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-D", "windows", "-cp", str(ROOT / "source"),
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
