"""Exercise release selection and the generated Windows updater contract."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class UpdateCheckerTest(unittest.TestCase):
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

  var scriptFactory = Reflect.field(UpdateChecker, "installerScript");
  var script:String = cast Reflect.callMethod(UpdateChecker, scriptFactory, []);
  Sys.println("UPDATER_SCRIPT_BEGIN");
  Sys.println(script);
  Sys.println("UPDATER_SCRIPT_END");
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
        self.assertIn("UPDATER_SCRIPT_BEGIN", result.stdout)
        script = result.stdout.split("UPDATER_SCRIPT_BEGIN\n", 1)[1].split(
            "\nUPDATER_SCRIPT_END", 1
        )[0]
        for required in (
            '[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12',
            '$client.Headers.Add("User-Agent", "CammieEngine-Updater")',
            r"\s+\*?",
            "Get-FileHash -LiteralPath $archivePath -Algorithm SHA256",
            "ZipFile]::OpenRead($archivePath)",
            "contains an unsafe path",
            "contains a duplicate path",
            '$protectedRoots = @("assets", "mods", "imported_mods")',
            '$backupRoot = Join-Path $workRoot "backup"',
            "foreach ($savedFile in Get-ChildItem -LiteralPath $backupRoot -File -Recurse)",
        ):
            self.assertIn(required, script)
        self.assertLess(script.index('Copy-ReleaseFiles $payloadRoot $InstallRoot ""'),
                        script.index('Move-Item -LiteralPath $tagTemporaryPath'))
        self.assertLess(script.index('Set-UpdateStatus "complete"'),
                        script.index('Add-Type -AssemblyName System.Windows.Forms',
                                     script.index('Set-UpdateStatus "complete"')))
        self.assertLess(script.index('$script:installStarted = $false'),
                        script.index('Add-Type -AssemblyName System.Windows.Forms',
                                     script.index('Set-UpdateStatus "complete"')))

    def test_settings_warn_about_preserved_assets_and_dismiss_stale_check(self):
        settings = (ROOT / "source/SaveDataState.hx").read_text(encoding="utf-8")
        self.assertIn("Existing asset files stay in place", settings)
        self.assertIn("static asset changes require a manual clean install", settings)
        self.assertIn("if (updateCheckRequestId < 0) return;", settings)
        self.assertIn("if (updateDialogMode == 'checking') updateCheckRequestId = -1;", settings)
        self.assertIn("updateDialogMode == 'progress' || updateDialogMode == 'ready'", settings)


if __name__ == "__main__":
    unittest.main()
