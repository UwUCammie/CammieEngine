"""Verify importer filesystem staging with the portable Haxe interpreter."""
from haxe_test_support import HAXE_COMMAND

import hashlib
import json
import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
SOURCE = ROOT / "source"


FIXTURE = r'''import ImportFile as File;
import ImportFileSystem as FileSystem;
import haxe.Json;

class ImportIOFixture {
  static function main():Void {
    var args = Sys.args();
    var install = args[0];
    var stage = args[1];
    var donor = args[2];
    var existing = install + "/assets/data/freeplaySongJson.jsonc";
    var output = install + "/assets/data/songs/new/chart.json";
    var ctx = ImportIO.begin(install, stage, ["assets/data/freeplaySongJson.jsonc", "assets/data/songs/old"]);
    if (!ctx.hasOwnedPath("assets/data") || !ctx.hasOwnedPath("assets/data/songs/old"))
      throw "owned ancestor or exact path lookup failed";
    if (ctx.hasOwnedPath("assets/data/songs/older") || ctx.hasOwnedPath("assets/data/songs/new"))
      throw "ownership prefix confused unrelated sibling paths";
    if (File.getContent(donor) != "donor-cache") throw "absolute cached donor read was redirected";
    if (FileSystem.exists(existing)) throw "masked registry leaked from install fallback";
    var hiddenReadFailed = false;
    try File.getContent(existing) catch (_:Dynamic) hiddenReadFailed = true;
    if (!hiddenReadFailed) throw "masked registry remained readable";
    var listing = FileSystem.readDirectory(install + "/assets/data/songs");
    if (listing.indexOf("old") >= 0) throw "masked directory leaked into listing";
    if (listing.indexOf("new") >= 0) throw "missing staged directory appeared early";
    File.saveContent(existing, "{\"generated\":true}");
    File.saveContent(output, "new-chart");
    File.saveContent("assets/module/import/import-report.txt", "diagnostic");
    var append = File.append(install + "/assets/data/append.txt");
    append.writeString("+new");
    append.close();
    FileSystem.createDirectory(install + "/assets/images/generated-empty");
    if (File.getContent(existing) != "{\"generated\":true}") throw "staged file did not win over mask";
    if (File.getContent(install + "/assets/data/append.txt") != "old+new") throw "append did not seed staged output from live file";
    if (!FileSystem.exists(output) || !FileSystem.isDirectory(install + "/assets/images/generated-empty"))
      throw "staged paths are not visible";
    if (FileSystem.stat(existing).size <= 0
      || FileSystem.fullPath(output) != output
      || FileSystem.absolutePath("assets/data/append.txt") != install + "/assets/data/append.txt")
      throw "staged FileSystem metadata or logical paths are incorrect";
    File.saveBytes("assets/images/binary.bin", haxe.io.Bytes.ofString("binary\x00payload"));
    if (File.getBytes("assets/images/binary.bin").toString() != "binary\x00payload")
      throw "byte file API did not round-trip";
    var writer = File.write("assets/images/stream.txt");
    writer.writeString("streamed");
    writer.close();
    var reader = File.read("assets/images/stream.txt");
    var streamText = reader.readAll().toString();
    reader.close();
    if (streamText != "streamed") throw "file handle API did not round-trip";
    listing = FileSystem.readDirectory(install + "/assets/data/songs");
    if (listing.indexOf("new") < 0 || listing.indexOf("old") >= 0) throw "merged listing is incorrect";
    FileSystem.rename(output, install + "/assets/data/songs/new/renamed.json");
    if (!FileSystem.exists(install + "/assets/data/songs/new/renamed.json") || FileSystem.exists(output))
      throw "staged rename did not move the file in the virtual tree";
    FileSystem.deleteFile(install + "/assets/data/songs/new/renamed.json");
    if (FileSystem.exists(install + "/assets/data/songs/new/renamed.json"))
      throw "staged deleteFile did not hide the file";
    FileSystem.deleteDirectory(install + "/assets/images/generated-empty");
    if (FileSystem.exists(install + "/assets/images/generated-empty"))
      throw "staged deleteDirectory did not hide the directory";
    var symlinkRejected = false;
    try File.saveContent(stage + "/assets/images/link/escape.txt", "blocked")
      catch (_:Dynamic) symlinkRejected = true;
    if (!symlinkRejected) throw "staged write followed a symlink outside its root";
    var written = ctx.writtenPaths();
    if (written.indexOf("assets/data/freeplaySongJson.jsonc") < 0
      || written.indexOf("assets/data/songs/new/chart.json") < 0
      || written.indexOf("assets/data/append.txt") < 0)
      throw "touched outputs are missing";
    if (written.indexOf("assets/module/import/import-report.txt") >= 0)
      throw "diagnostic report was tracked as an install output";
    if (ctx.deletedPaths().indexOf("assets/data/songs/new/chart.json") < 0)
      throw "deleted output was not recorded";
    if (ctx.before("assets/data/freeplaySongJson.jsonc").text != "{\"old\":1}")
      throw "registry baseline text was not retained";
    if (ctx.before("assets/data/append.txt").text != null)
      throw "non-registry baseline retained unnecessary text";
    var blockedTraversal = false;
    try File.saveContent("assets/data/../../outside.txt", "blocked") catch (_:Dynamic) blockedTraversal = true;
    if (!blockedTraversal) throw "relative traversal write was allowed";
    var blockedExternalWrite = false;
    try File.saveContent(donor + "/escaped.txt", "blocked") catch (_:Dynamic) blockedExternalWrite = true;
    if (!blockedExternalWrite) throw "external write was allowed";
    var stagedAbsolute = stage + "/assets/images/absolute-stage.txt";
    File.saveContent(stagedAbsolute, "direct-stage");
    if (File.getContent(install + "/assets/images/absolute-stage.txt") != "direct-stage")
      throw "absolute stage write was not visible through install path";
    var result = {
      written: written,
      deleted: ctx.deletedPaths(),
      beforeRegistry: ctx.before("assets/data/freeplaySongJson.jsonc"),
      owned: ctx.hasOwnedPath("assets/data/songs/old/chart.json"),
      namespace: "",
      sourceLabel: ""
    };
    var sourceRoot = donor.substr(0, donor.lastIndexOf("/"));
    ctx.setNamespace(sourceRoot + "/", "Psych Engine", "stable-space");
    ctx.setSourceLabel(sourceRoot + "/", "fixture-source");
    Reflect.setField(result, "namespace", ctx.namespace(sourceRoot, "Psych Engine"));
    Reflect.setField(result, "sourceLabel", ctx.sourceLabel(sourceRoot));
    ImportIO.end();
    if (File.getContent(existing) != "{\"old\":1}") throw "install tree changed during staging";
    Sys.println(Json.stringify(result));
  }
}
'''


class ImportIOTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HAXE.is_file():
            raise unittest.SkipTest("portable Haxe interpreter is unavailable")

    def test_owned_refresh_defer_preserves_registry_baselines_and_ownership_boundaries(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temporary:
            base = Path(temporary)
            install = base / "install"
            stage = install / "import-cache/staging/session"
            (install / "assets/data").mkdir(parents=True)
            stage.mkdir(parents=True)
            (install / "assets/data/freeplaySongJson.json").write_text('{"old":1}', encoding="utf-8")
            (install / "assets/data/owned.bin").write_bytes(b"old media")
            (install / "assets/data/other.bin").write_bytes(b"unowned")
            (base / "Main.hx").write_text(r'''import ImportFile as File;
@:access(ImportIO)
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var args = Sys.args();
  var owned = "assets/data/owned.bin";
  var registry = "assets/data/freeplaySongJson.json";
  var io = ImportIO.begin(args[0], args[1], [owned,registry],true);
  File.saveContent(owned,"new media");
  File.saveContent(registry,"{}");
  File.saveContent("assets/data/other.bin","new unowned");
  check(!io.baselineChecked.exists(owned),"Owned media hash must be deferred to manifest validation");
  check(io.before(registry).text == '{"old":1}',"Shared registry prewrite baseline must remain");
  check(io.before("assets/data/other.bin").sha256 == haxe.crypto.Sha256.encode("unowned"),
   "Unowned prewrite baseline must remain");
  check(io.before(owned).sha256 == haxe.crypto.Sha256.encode("old media"),"Explicit baseline requests still hash live media");
  check(io.hasOwnedPath("assets") && io.hasOwnedPath("assets/data") && io.hasOwnedPath(owned),"Owned path boundaries");
  check(!io.hasOwnedPath("assets/dat") && !io.hasOwnedPath("assets/data/owned.bin2"),"Sibling prefixes must not become owned");
  ImportIO.end();
  Sys.println("OK");
 }
}''', encoding="utf-8")
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(SOURCE), "-cp", str(base),
                "--run", "Main", str(install), str(stage)], cwd=ROOT,
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("OK", result.stdout)

    def test_stages_outputs_masks_old_files_and_preserves_donor_reads(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temporary:
            base = Path(temporary)
            install = base / "install"
            stage = install / "import-cache/staging/session"
            donor = install / "import-cache/sources/donor/data.txt"
            (install / "assets/data/songs/old").mkdir(parents=True)
            (install / "assets/images").mkdir(parents=True)
            (install / "assets/data/freeplaySongJson.jsonc").write_text('{"old":1}', encoding="utf-8", newline='\n')
            (install / "assets/data/append.txt").write_text("old", encoding="utf-8", newline='\n')
            donor.parent.mkdir(parents=True)
            donor.write_text("donor-cache", encoding="utf-8", newline='\n')
            stage.mkdir(parents=True)
            (stage / "assets/images").mkdir(parents=True)
            outside = base / "outside"
            outside.mkdir()
            (stage / "assets/images/link").symlink_to(outside, target_is_directory=True)
            fixture = base / "ImportIOFixture.hx"
            fixture.write_text(FIXTURE, encoding="utf-8", newline='\n')
            process = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(base), "-cp", str(SOURCE), "--run", "ImportIOFixture",
                 str(install), str(stage), str(donor)],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            staged = json.loads(process.stdout.strip().splitlines()[-1])
            self.assertEqual(staged["beforeRegistry"]["sha256"], hashlib.sha256(b'{"old":1}').hexdigest())
            self.assertTrue(staged["owned"])
            self.assertEqual(staged["namespace"], "stable-space")
            self.assertEqual(staged["sourceLabel"], "fixture-source")
            self.assertEqual((install / "assets/data/freeplaySongJson.jsonc").read_text(), '{"old":1}')
            self.assertEqual((stage / "assets/data/freeplaySongJson.jsonc").read_text(), '{"generated":true}')
            self.assertEqual((stage / "assets/data/append.txt").read_text(), "old+new")
            self.assertTrue((stage / "assets/images/absolute-stage.txt").is_file())
            self.assertFalse((install / "assets/module/import/import-report.txt").exists())
            self.assertFalse((install / "outside.txt").exists())


if __name__ == "__main__":
    unittest.main()
