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
    var profileRoot = args[3];
    var profileContent = args[4];
    var nestedStage = args[5];
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
	if (ImportGeneratedOutput.write(output, "new-chart", true))
		throw "identical generated output was rewritten";
	var generatedConflict = false;
	try ImportGeneratedOutput.write(output, "changed-chart", true)
		catch (_:Dynamic) generatedConflict = true;
	if (!generatedConflict || File.getContent(output) != "new-chart")
		throw "generated output conflict was not preserved";
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
    var profileSnapshot = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    ctx.setNamespace(profileRoot, "Psych Engine", "profile-space");
    var profile = {
      version: 1, provenance: "receipt-bound", complete: true,
      snapshotId: profileSnapshot, rootRelative: "maps", sourceEngine: "Psych Engine",
      namespace: "profile-space", projectRelative: "maps/Project.xml", projectSha256: "abc",
      buildTarget: "", flags: [], candidates: [], opaqueBuildInputs: [], diagnostics: []
    };
    ctx.setAssetProfile(profileRoot, profileContent, profileSnapshot, "maps/", "Psych Engine", "profile-space", profile);
    var retrieved = ctx.assetProfile(profileRoot, "psych");
    if (retrieved == null || retrieved.contentRoot != profileContent
      || Reflect.field(retrieved.profile, "namespace") != "profile-space")
      throw "receipt-bound profile was not available from its exact root";
    Reflect.setField(retrieved.profile, "namespace", "caller-mutation");
    if (Reflect.field(ctx.assetProfile(profileRoot, "Psych Engine").profile, "namespace") != "profile-space")
      throw "profile lookup exposed its mutable stored value";
    if (ctx.assetProfile(profileRoot + "/nested", "Psych Engine") != null
      || ctx.assetProfile(profileRoot, "Nightmare Vision") != null)
      throw "profile leaked to another source root or engine";
    var mismatchRejected = false;
    var badProfile = haxe.Json.parse(haxe.Json.stringify(profile));
    Reflect.setField(badProfile, "snapshotId", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb");
    try ctx.setAssetProfile(profileRoot, profileContent, profileSnapshot, "maps", "Psych Engine", "profile-space", badProfile)
      catch (_:Dynamic) mismatchRejected = true;
    if (!mismatchRejected) throw "profile with a different snapshot was accepted";
    var nested = ImportIO.begin(install, nestedStage);
    var nestedProfile = haxe.Json.parse(haxe.Json.stringify(profile));
    Reflect.setField(nestedProfile, "namespace", "nested-space");
    nested.setAssetProfile(profileRoot, profileContent, profileSnapshot, "maps", "Psych Engine", "nested-space", nestedProfile);
    if (Reflect.field(nested.assetProfile(profileRoot, "Psych Engine").profile, "namespace") != "nested-space")
      throw "nested scope did not use its own asset profile";
    ImportIO.end();
    if (nested.assetProfile(profileRoot, "Psych Engine") != null || ImportIO.current() != ctx)
      throw "ending a nested scope did not clear and restore the profile context";
    if (Reflect.field(ctx.assetProfile(profileRoot, "Psych Engine").profile, "namespace") != "profile-space")
      throw "nested profile scope changed its parent profile";
    ImportIO.end();
    if (ctx.assetProfile(profileRoot, "Psych Engine") != null || ImportIO.current() != null)
      throw "ending a scope did not clear its asset profile";
    if (File.getContent(existing) != "{\"old\":1}") throw "install tree changed during staging";
    Sys.println(Json.stringify(result));
  }
}
'''


PROFILE_FIXTURE = r'''class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function profile(snapshot:String, root:String, namespace:String):Dynamic return {
  provenance:"receipt-bound", snapshotId:snapshot, rootRelative:root,
  sourceEngine:"Psych Engine", namespace:namespace, unicodeNote:"Imported source 🌙"
 };
 static function main():Void {
  var args=Sys.args(); var install=args[0]; var stage=args[1]; var content=args[2];
  var root=args[3]; var nestedStage=args[4]; var snapshot=args[5];
  var outer=ImportIO.begin(install,stage,[
   "assets/imported_mods/profile-owner/lang/en-US.lang",
   "assets/imported_mods/profile-owner/lang/fr-FR.LANG",
   "assets/imported_mods/profile-owner/pack.json",
   "assets/imported_mods/sibling/lang/other.lang"]);
  var ownedLanguages=outer.ownedOutputPathsUnder("assets/imported_mods/profile-owner",".lang");
  check(ownedLanguages.length==2
   &&ownedLanguages[0]=="assets/imported_mods/profile-owner/lang/en-US.lang"
   &&ownedLanguages[1]=="assets/imported_mods/profile-owner/lang/fr-FR.LANG",
   "manifest-backed language path listing must be scoped, sorted, and case-insensitive by suffix");
  outer.setNamespace(root,"Psych Engine","owner-a");
  outer.setAssetProfile(root,content,snapshot,"maps","Psych Engine","owner-a",profile(snapshot,"maps","owner-a"));
  var first=outer.assetProfile(root,"psych");
  check(first!=null && first.contentRoot==content,"exact profile root lookup");
  check(Reflect.field(first.profile,"unicodeNote")=="Imported source 🌙","Unicode profile text must survive defensive copying");
  Reflect.setField(first.profile,"namespace","mutated");
  check(Reflect.field(outer.assetProfile(root,"Psych Engine").profile,"namespace")=="owner-a","defensive profile copy");
  check(outer.assetProfile(root+"/child","Psych Engine")==null,"sibling root isolation");
  check(outer.assetProfile(root,"Nightmare Vision")==null,"engine isolation");
  outer.setNamespace(root,"Psych Engine","replacement-owner");
  check(outer.assetProfile(root,"Psych Engine")==null,"changed namespace cannot reuse old profile");
  outer.setNamespace(root,"Psych Engine","owner-a");
  var rejected=false;
  try outer.setAssetProfile(root,content,snapshot,"maps","Psych Engine","owner-a",profile("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","maps","owner-a"))
  catch (_:Dynamic) rejected=true;
  check(rejected,"mismatched snapshot rejection");
  var inner=ImportIO.begin(install,nestedStage);
  inner.setNamespace(root,"Psych Engine","owner-b");
  inner.setAssetProfile(root,content,snapshot,"maps","Psych Engine","owner-b",profile(snapshot,"maps","owner-b"));
  check(Reflect.field(inner.assetProfile(root,"Psych Engine").profile,"namespace")=="owner-b","nested profile binding");
  ImportIO.end();
  check(inner.assetProfile(root,"Psych Engine")==null,"inner scope cleanup");
  check(ImportIO.current()==outer,"nested TLS restoration");
  check(Reflect.field(outer.assetProfile(root,"Psych Engine").profile,"namespace")=="owner-a","parent profile retained");
  ImportIO.end();
  check(outer.assetProfile(root,"Psych Engine")==null && ImportIO.current()==null,"outer scope cleanup");
  Sys.println("OK");
 }
}'''


IO_SCHEDULER_FIXTURE = r'''import ImportIO;
import ImportWorkScheduler;
import sys.FileSystem;
import sys.thread.Thread;
class Main {
 static var cancelHash:Bool=false;
 static function waitFor(done:Void->Bool, seconds:Float):Bool {
  var until=Sys.time()+seconds;
  while(Sys.time()<until) {
   if(done()) return true;
   Sys.sleep(0.002);
  }
  return done();
 }
 static function main():Void {
  var args=Sys.args(); var install=args[0]; var stage=args[1]; var source=args[2];
  var copyTarget=stage+"/assets/data/copied.bin";
  ImportWorkScheduler.bindForegroundThread();
  var copyState={done:false,error:""};
  Thread.create(function() {
   var io:ImportIO=null;
   try {
    io=ImportIO.begin(install,stage,[],false,function() return false);
    io.copy(source,"assets/data/copied.bin");
   } catch(error:Dynamic) copyState.error=Std.string(error);
   if(io!=null) ImportIO.end();
   copyState.done=true;
  });
  var started=waitFor(function() return FileSystem.exists(copyTarget)
   &&FileSystem.stat(copyTarget).size>=65536,10);
  if(!started) throw "background copy did not reach its first 64 KiB checkpoint";
  var lease=ImportWorkScheduler.beginGameplay();
  Sys.sleep(0.04);
  var pausedSize=FileSystem.stat(copyTarget).size;
  Sys.sleep(0.12);
  var copyPaused=!copyState.done&&FileSystem.stat(copyTarget).size==pausedSize;
  ImportWorkScheduler.endGameplay(lease);
  if(!waitFor(function() return copyState.done,20)) throw "background copy did not resume after gameplay";
  if(copyState.error!="") throw "background copy failed: "+copyState.error;
  if(!copyPaused) throw "background copy kept writing during gameplay";

  var hashState={done:false,error:"",cancelled:false};
  cancelHash=false;
  lease=ImportWorkScheduler.beginGameplay();
  Thread.create(function() {
   var io:ImportIO=null;
   try {
    io=ImportIO.begin(install,stage,["assets/data/hash.bin"],false,function() return cancelHash);
    io.before("assets/data/hash.bin");
   } catch(error:Dynamic) {
    hashState.error=Std.string(error);
    hashState.cancelled=Std.isOfType(error,ImportWorkCancelled);
   }
   if(io!=null) ImportIO.end();
   hashState.done=true;
  });
  Sys.sleep(0.08);
  var hashPaused=!hashState.done;
  cancelHash=true;
  if(!waitFor(function() return hashState.done,5)) throw "cancelled background hash did not wake";
  ImportWorkScheduler.endGameplay(lease);
  if(!hashPaused||!hashState.cancelled)
   throw "background prewrite hash did not pause and cancel at a chunk boundary: "+hashState.error;

  lease=ImportWorkScheduler.beginGameplay();
  var foreground=ImportIO.begin(install,stage,[],false,function() return false);
  foreground.copy(args[3],"assets/data/foreground.bin");
  ImportIO.end();
  ImportWorkScheduler.endGameplay(lease);

  var immediateState={done:false,cancelled:false};
  Thread.create(function() {
   var io:ImportIO=null;
   try {
    io=ImportIO.begin(install,stage,[],false,function() return true);
    io.copy(source,"assets/data/cancelled-background.bin");
   } catch(error:Dynamic) immediateState.cancelled=Std.isOfType(error,ImportWorkCancelled);
   if(io!=null) ImportIO.end();
   immediateState.done=true;
  });
  if(!waitFor(function() return immediateState.done,5)||!immediateState.cancelled)
   throw "background I/O ignored cancellation when gameplay was idle";

  var foregroundCancelled=false;
  var cancelledForeground=ImportIO.begin(install,stage,[],false,function() return true);
  try cancelledForeground.copy(args[3],"assets/data/cancelled-foreground.bin")
   catch(error:Dynamic) foregroundCancelled=Std.isOfType(error,ImportWorkCancelled);
  ImportIO.end();
  if(!foregroundCancelled) throw "foreground I/O ignored cancellation at its chunk checkpoint";
  Sys.println("OK");
 }
}'''


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
            profile_snapshot = "a" * 64
            profile_content = install / "import-cache/sources" / profile_snapshot / "content"
            profile_root = profile_content / "maps"
            profile_root.mkdir(parents=True)
            nested_stage = install / "import-cache/staging/nested"
            nested_stage.mkdir(parents=True)
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

    def test_asset_profiles_are_receipt_bound_root_scoped_and_cleared_with_nested_scopes(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temporary:
            base = Path(temporary)
            install = base / "install"
            snapshot = "a" * 64
            content = install / "import-cache/sources" / snapshot / "content"
            root = content / "maps"
            root.mkdir(parents=True)
            stage = install / "import-cache/staging/outer"
            nested_stage = install / "import-cache/staging/inner"
            stage.mkdir(parents=True)
            nested_stage.mkdir(parents=True)
            fixture = base / "Main.hx"
            fixture.write_text(PROFILE_FIXTURE, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(SOURCE), "-cp", str(base), "--run", "Main",
                 str(install), str(stage), str(content), str(root), str(nested_stage), snapshot],
                cwd=ROOT, env={**os.environ, "CAMMIE_TEST_TMP": str(ROOT / "tmp")},
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("OK", result.stdout)

    def test_background_staged_copy_and_prewrite_hash_pause_and_cancel_at_chunk_checkpoints(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temporary:
            base = Path(temporary)
            install = base / "install"
            (install / "assets/data").mkdir(parents=True)
            stage = install / "import-cache/staging/io-scheduler"
            stage.mkdir(parents=True)
            large = b"x" * (64 * 1024 * 1024)
            source = base / "large.bin"
            source.write_bytes(large)
            (install / "assets/data/hash.bin").write_bytes(large)
            foreground = base / "foreground.bin"
            foreground.write_bytes(b"foreground")
            fixture = base / "Main.hx"
            fixture.write_text(IO_SCHEDULER_FIXTURE, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(SOURCE), "-cp", str(base), "--run", "Main",
                 str(install), str(stage), str(source), str(foreground)],
                cwd=ROOT, env={**os.environ, "CAMMIE_TEST_TMP": str(ROOT / "tmp")},
                capture_output=True, text=True, timeout=45,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("OK", result.stdout)
            self.assertEqual((stage / "assets/data/copied.bin").stat().st_size, len(large))
            self.assertEqual((stage / "assets/data/foreground.bin").read_bytes(), b"foreground")

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
            profile_snapshot = "a" * 64
            profile_content = install / "import-cache/sources" / profile_snapshot / "content"
            profile_root = profile_content / "maps"
            profile_root.mkdir(parents=True)
            nested_stage = install / "import-cache/staging/nested"
            nested_stage.mkdir(parents=True)
            stage.mkdir(parents=True)
            (stage / "assets/images").mkdir(parents=True)
            outside = base / "outside"
            outside.mkdir()
            try:
                (stage / "assets/images/link").symlink_to(outside, target_is_directory=True)
            except OSError as error:
                if os.name == "nt" and getattr(error, "winerror", None) == 1314:
                    self.skipTest("Windows symlink privilege is unavailable for the staged-write escape fixture")
                raise
            fixture = base / "ImportIOFixture.hx"
            fixture.write_text(FIXTURE, encoding="utf-8", newline='\n')
            process = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(base), "-cp", str(SOURCE), "--run", "ImportIOFixture",
                 str(install), str(stage), str(donor), str(profile_root), str(profile_content), str(nested_stage)],
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
