"""Exercise retained-source import refresh with real staging/transaction helpers."""
from haxe_test_support import HAXE_COMMAND, TEST_TMP

import hashlib
import json
import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source"
HAXE = ROOT / ".tools/haxe/haxe"
TJSON = ROOT / ".haxelib/tjson/1,4,0"
REGISTRY = "assets/data/freeplaySongJson.json"


STUBS = {
    "EngineBranding.hx": r'''class EngineBranding {
 public static function version():String return "0.0.9";
}''',
    "ModuleFunctions.hx": r'''typedef SongImportBatchResult = {
 var found:Int;
 var imported:Int;
 var importedSongs:Array<String>;
 var skipped:Int;
 var failed:Int;
 var copiedAssets:Int;
 var skippedAssets:Int;
 var errors:Array<String>;
}
class ModuleFunctions {
 public static function setImportBackgroundMode(value:Bool):Void {}
 public static function setImportCancelCallback(value:Dynamic):Void {}
 public static function setImportProgressCallback(value:Dynamic):Void {}
 public static function completeImportOnMainThread(names:Array<String>):Void {}
}''',
    "ImportWorkflow.hx": r'''import ModuleFunctions.SongImportBatchResult;
typedef ImportScanResult = {
 var detectedRoots:Array<Dynamic>;
 var detectedEngines:Array<String>;
 var rootScanDiagnostics:Array<Dynamic>;
 var packageScanDiagnostics:Array<Dynamic>;
 var rootScanTruncated:Bool;
 var packageScanTruncated:Bool;
 var missingDependencies:Null<Int>;
 var errors:Array<String>;
 var songs:Array<ImportScanSong>;
}
typedef ImportScanSong = {
 var missing:Array<Dynamic>;
 @:optional var duplicate:Bool;
 @:optional var sourceDuplicate:Bool;
}
class ImportWorkflow {
 public static var rootTruncated:Bool=false;
 public static var packageTruncated:Bool=false;
 public static var overrideRoots:Null<Array<Dynamic>>=null;
 public static var rootDiagnostics:Array<Dynamic>=[];
 public static var packageDiagnostics:Array<Dynamic>=[];
 public static var scanErrors:Array<String>=[];
 public static var missing:Array<ImportScanSong>=[];
 public static var existingDuplicate:Bool=false;
 public static function scanNow(source:String,type:String):ImportScanResult {
  var songs=missing.copy();
  if(existingDuplicate) songs.push({missing:[],duplicate:true,sourceDuplicate:false});
  return {
   detectedRoots:overrideRoots==null?[{root:source,engine:type}]:overrideRoots.copy(), detectedEngines:[type],
   rootScanDiagnostics:rootDiagnostics.copy(), packageScanDiagnostics:packageDiagnostics.copy(),
   rootScanTruncated:rootTruncated, packageScanTruncated:packageTruncated,
   missingDependencies:missing.length, errors:scanErrors.copy(), songs:songs
  };
 }
 public static function convertRetainedSource(source:String,scan:ImportScanResult,
  names:Map<String,String>):SongImportBatchResult
  return ImportRefreshManagerFixture.convertRetainedSource(source,scan,names);
}''',
    "CompatScriptManifest.hx": r'''import haxe.crypto.Md5;
import haxe.io.Path;
class CompatScriptManifest {
 public static function namespaceFor(source:String,engine:String):String {
  var context=ImportIO.current();
  if(context!=null) {
   var retained=context.namespace(source,engine);
   if(retained!=null&&retained!="") return retained;
  }
  return StringTools.replace(engine.toLowerCase()," ","-")+"-"+Md5.encode(Path.normalize(source)).substr(0,12);
 }
}''',
    "ImportPackageNamePrompt.hx": r'''import haxe.io.Path;
import sys.FileSystem;
class ImportPackageNamePrompt {
 public static function rootKey(path:String):String return Path.normalize(FileSystem.absolutePath(path));
 public static function validName(value:String):Bool return value!=null&&StringTools.trim(value)!="";
}''',
    "ImportSongOwnership.hx": r'''class ImportSongOwnership {
 public static function invalidateOwnerIdentityIndex():Void {}
}''',
}


FIXTURE = r'''import haxe.Json;
import haxe.io.Path;
import ImportWorkflow.ImportScanResult;
import ModuleFunctions.SongImportBatchResult;
import sys.FileSystem;
import sys.io.File;

@:access(ImportRefreshManager)
class ImportRefreshManagerFixture {
 static inline var REGISTRY:String="assets/data/freeplaySongJson.json";
 static var cancelAfterWrite:Bool=false;

 static function scan(source:String):ImportScanResult return ImportWorkflow.scanNow(source,"Psych Engine");

 static function converter(useNextSongs:Bool, failAfterWrite:Bool=false,
  cancelAfterWriteRequested:Bool=false, mutateRegistryAfterWrite:Bool=false):((String,ImportScanResult,Map<String,String>)->SongImportBatchResult) {
  return function(source:String,scan:ImportScanResult,names:Map<String,String>):SongImportBatchResult {
   var spec:Dynamic=Json.parse(File.getContent(Path.join([source,"package.json"])));
   var songNames:Array<String>=cast (useNextSongs ? spec.nextSongs : spec.initialSongs);
   var version:String=Std.string(useNextSongs ? spec.nextVersion : spec.initialVersion);

   var registry:Dynamic={};
   if(ImportFileSystem.exists(REGISTRY)) {
    try registry=Json.parse(ImportFile.getContent(REGISTRY)) catch(_:Dynamic) registry={};
   }
   if(Reflect.field(registry,"owners")==null) Reflect.setField(registry,"owners",{});
   var owners:Dynamic=Reflect.field(registry,"owners");
   Reflect.setField(owners,Std.string(spec.ownerKey),version);
   Reflect.setField(registry,"owners",owners);
   ImportFile.saveContent(REGISTRY,Json.stringify(registry));

   for(song in songNames) {
    ImportFile.saveContent("assets/data/"+song+"/"+song+".json",
     Json.stringify({song:song,version:version,marker:spec.marker}));
    ImportFile.saveContent("assets/songs/"+song+"/Inst.ogg",version+":"+Std.string(spec.marker));
   }
   if(mutateRegistryAfterWrite) {
    var livePath=Path.join([Sys.getCwd(),REGISTRY]);
    var live:Dynamic=Json.parse(File.getContent(livePath));
    Reflect.setField(live,"concurrentEdit","keep during conversion");
    File.saveContent(livePath,Json.stringify(live));
   }
   if(cancelAfterWriteRequested) cancelAfterWrite=true;
   return {found:songNames.length, imported:songNames.length, importedSongs:songNames.copy(),
    skipped:0, failed:failAfterWrite?1:0, copiedAssets:songNames.length, skippedAssets:0,
    errors:failAfterWrite?["fixture conversion failure"]:[]};
  };
 }

 public static function convertRetainedSource(source:String,scan:ImportScanResult,
  names:Map<String,String>):SongImportBatchResult {
  return converter(true)(source,scan,names);
 }

 static function progress(value:Dynamic):Void {}
 static function noCancel():Bool return cancelAfterWrite;

 static function importPackage(source:String,useNextSongs:Bool,failAfterWrite:Bool=false,
  cancelAfterWriteRequested:Bool=false):Dynamic {
  cancelAfterWrite=false;
  var type="Psych Engine";
  var result=ImportRefreshManager.importOnce(source,type,scan(source),new Map(),
   converter(useNextSongs,failAfterWrite,cancelAfterWriteRequested),noCancel,progress);
  return result;
 }

 static function findRecord(id:String):Dynamic {
  for(record in ImportRefreshManager.cachedRecords(Sys.getCwd()))
   if(Std.string(record.id)==id) return record;
  throw "retained record not found: "+id;
 }

 static function report(value:Dynamic):Void Sys.println(Json.stringify(value));

 static function main():Void {
  var args=Sys.args();
  var mode=args[0];
  var install=args[1];
  Sys.setCwd(install);
  switch(mode) {
   case "fresh":
    var source=args[2];
    var result=importPackage(source,false);
    report({failed:result.failed, importedSongs:result.importedSongs,
     records:ImportRefreshManager.cachedRecords(install)});
   case "fresh-diagnostic":
    ImportWorkflow.missing=[{missing:[{kind:"character",reference:"unshipped-character",found:false,
     searched:["characters/unshipped-character.json"]}]}];
    var result=importPackage(args[2],false);
    report({failed:result.failed, records:ImportRefreshManager.cachedRecords(install)});
   case "multi-fresh":
    var first=importPackage(args[2],false);
    var second=importPackage(args[3],false);
    report({failed:first.failed+second.failed, records:ImportRefreshManager.cachedRecords(install)});
   case "refresh", "refresh-fail", "refresh-cancel", "refresh-concurrent-registry", "refresh-scan-errors":
    var id=args[2];
    var record=findRecord(id);
    if(mode=="refresh-scan-errors") ImportWorkflow.scanErrors=["fixture: chart could not be parsed"];
    // This also verifies that the persisted manifest and its receipt/journal
    // still agree after the Python fixture marks its revision stale.
    var owner="retained-import:"+id;
    var manifest=ImportRefreshTransaction.loadManifest(Path.join([install,"import-cache/state"]),owner);
    cancelAfterWrite=false;
    try {
     var result=ImportRefreshManager.refreshNow(install,record,
      converter(true,mode=="refresh-fail",mode=="refresh-cancel",mode=="refresh-concurrent-registry"),noCancel,progress);
     report({status:"ok",failed:result.failed, importedSongs:result.importedSongs,
      files:manifest.files.length, records:ImportRefreshManager.cachedRecords(install)});
    } catch(error:Dynamic) {
     report({status:"error",error:Std.string(error),files:manifest.files.length,
     records:ImportRefreshManager.cachedRecords(install)});
    }
   case "refresh-root-truncated", "refresh-package-truncated":
    if(mode=="refresh-root-truncated") ImportWorkflow.rootTruncated=true;
    else ImportWorkflow.packageTruncated=true;
    var record=findRecord(args[2]);
    try {
     ImportRefreshManager.refreshNow(install,record,converter(true),noCancel,progress);
     report({status:"unexpected-success"});
    } catch(error:Dynamic) report({status:"error",error:Std.string(error)});
   case "refresh-empty-roots", "refresh-missing-roots":
    var record=findRecord(args[2]);
    if(mode=="refresh-empty-roots") ImportWorkflow.overrideRoots=[];
    else ImportWorkflow.overrideRoots=[{root:Sys.getCwd(),engine:"Psych Engine"}];
    try {
     ImportRefreshManager.refreshNow(install,record,converter(true),noCancel,progress);
     report({status:"unexpected-success"});
    } catch(error:Dynamic) report({status:"error",error:Std.string(error)});
   case "auto-refresh":
    // Each test runs in a fresh process, but explicitly reset the one-shot
    // startup queue so this fixture also documents its expected lifecycle.
    ImportRefreshManager.checked=false;
    ImportRefreshManager.active=false;
    ImportRefreshManager.queue=[];
    ImportRefreshManager.handedOff=false;
    ImportRefreshManager.completedNames=[];
    ImportRefreshManager.status={busy:false,label:"",fraction:0.0,complete:false,changed:false,blocked:false};
    var deadline=Sys.time()+20;
    var status:Dynamic=null;
    while(Sys.time()<deadline) {
     status=ImportRefreshManager.browseTick();
     if(status.complete&& !status.busy) break;
     if(status.blocked&& !status.busy) break;
     Sys.sleep(0.005);
    }
    report({status:status, generation:ImportRefreshManager.generation,
     records:ImportRefreshManager.cachedRecords(install)});
   case "legacy-collision":
    var source=args[2];
    try {
     importPackage(source,false);
     report({status:"unexpected-success"});
    } catch(error:Dynamic) report({status:"blocked",error:Std.string(error)});
   case "legacy-namespace":
    var source=args[2];
    var namespace=CompatScriptManifest.namespaceFor(source,"Psych Engine");
    var namespaces=Path.join([install,"assets","imported_mods"]);
    FileSystem.createDirectory(namespaces);
    var oldRoot=Path.join([namespaces,namespace]);
    FileSystem.createDirectory(oldRoot);
    File.saveContent(Path.join([oldRoot,"old-import.hscript"]),"legacy bytes");
    try {
     importPackage(source,false);
     report({status:"unexpected-success",records:ImportRefreshManager.cachedRecords(install)});
    } catch(error:Dynamic) report({status:"blocked",error:Std.string(error),records:ImportRefreshManager.cachedRecords(install)});
   case "legacy-duplicate-song":
    ImportWorkflow.existingDuplicate=true;
    try {
     importPackage(args[2],false);
     report({status:"unexpected-success",records:ImportRefreshManager.cachedRecords(install)});
    } catch(error:Dynamic) report({status:"blocked",error:Std.string(error),records:ImportRefreshManager.cachedRecords(install)});
   default: throw "unknown fixture mode: "+mode;
  }
 }
}'''


class ImportRefreshManagerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HAXE.is_file() or not TJSON.is_dir():
            raise unittest.SkipTest("portable Haxe or pinned TJSON is unavailable")

    def setUp(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=TEST_TMP)
        self.addCleanup(self.temp.cleanup)
        self.scratch = Path(self.temp.name)
        self.install = self.scratch / "install"
        self.install.mkdir()
        (self.install / "import-cache/staging").mkdir(parents=True)
        registry = self.install / REGISTRY
        registry.parent.mkdir(parents=True)
        registry.write_text(json.dumps({"base": {"keep": True}, "owners": {}}), encoding="utf-8", newline='\n')
        self.fixture_dir = self.scratch / "haxe"
        self.fixture_dir.mkdir()
        for relative, content in STUBS.items():
            (self.fixture_dir / relative).write_text(content, encoding="utf-8", newline='\n')
        (self.fixture_dir / "ImportRefreshManagerFixture.hx").write_text(FIXTURE, encoding="utf-8", newline='\n')

    def make_source(self, name: str, *, initial_songs=None, next_songs=None) -> Path:
        source = self.scratch / name
        source.mkdir()
        package = {
            "ownerKey": name,
            "marker": "retained:" + name,
            "initialVersion": "v1-" + name,
            "nextVersion": "v2-" + name,
            "initialSongs": initial_songs or ["song-" + name],
            "nextSongs": next_songs or ["song-" + name, "song-" + name + "-new"],
        }
        (source / "package.json").write_text(json.dumps(package), encoding="utf-8", newline='\n')
        return source

    def run_fixture(self, mode: str, *args: str) -> dict:
        result = subprocess.run(
            [*HAXE_COMMAND, "-cp", str(SOURCE), "-cp", str(TJSON), "-cp", str(self.fixture_dir),
             "--run", "ImportRefreshManagerFixture", mode, str(self.install), *map(str, args)],
            cwd=ROOT,
            env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
            capture_output=True,
            text=True,
            timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout.strip().splitlines()[-1])

    def mark_record_stale(self, record: dict) -> None:
        owner = "retained-import:" + record["id"]
        owner_hash = hashlib.sha256(owner.encode()).hexdigest()
        scope = self.install / "import-cache/state" / owner_hash
        manifest_path = scope / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["revision"]["importRecord"]["revisions"][0]["commonRevision"] = 0
        manifest_bytes = (json.dumps(manifest, separators=(",", ":")) + "\n").encode()
        manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
        manifest_path.write_bytes(manifest_bytes)

        transaction = scope / "transactions" / manifest["transactionId"]
        journals = sorted(transaction.glob("journal-*.json"))
        self.assertTrue(journals, "committed import must have a recoverable transaction journal")
        journal_path = journals[-1]
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        journal["manifestAfterSha256"] = manifest_hash
        journal_path.write_text(json.dumps(journal) + "\n", encoding="utf-8", newline='\n')

        receipt_path = transaction / "receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["manifestSha256"] = manifest_hash
        receipt_path.write_text(json.dumps(receipt) + "\n", encoding="utf-8", newline='\n')

    def initial_import(self, source: Path) -> dict:
        report = self.run_fixture("fresh", source)
        self.assertEqual(report["failed"], 0)
        self.assertEqual(len(report["records"]), 1)
        return report["records"][0]

    def test_refresh_after_donor_removal_uses_retained_source_and_publishes_new_song(self):
        donor = self.make_source("donor-a", initial_songs=["alpha"], next_songs=["alpha", "beta"])
        record = self.initial_import(donor)
        self.assertEqual((self.install / "assets/songs/alpha/Inst.ogg").read_text(), "v1-donor-a:retained:donor-a")
        shutil_rmtree(donor)
        self.mark_record_stale(record)

        refreshed = self.run_fixture("refresh", record["id"])

        self.assertEqual(refreshed["status"], "ok", refreshed)
        self.assertEqual((self.install / "assets/songs/alpha/Inst.ogg").read_text(), "v2-donor-a:retained:donor-a")
        self.assertEqual((self.install / "assets/songs/beta/Inst.ogg").read_text(), "v2-donor-a:retained:donor-a")
        self.assertTrue((self.install / "assets/data/beta/beta.json").is_file())
        self.assertTrue(any(stamp["commonRevision"] == 1 for stamp in refreshed["records"][0]["revisions"]))
        self.assertFalse(donor.exists())

    def test_stale_persisted_record_is_automatically_queued_on_browse_tick(self):
        donor = self.make_source("donor-auto", initial_songs=["auto-song"], next_songs=["auto-song", "auto-new"])
        record = self.initial_import(donor)
        shutil_rmtree(donor)
        self.mark_record_stale(record)

        result = self.run_fixture("auto-refresh")

        self.assertFalse(result["status"]["busy"], result)
        self.assertTrue(result["status"]["complete"], result)
        self.assertFalse(result["status"]["blocked"], result)
        self.assertTrue(result["status"]["changed"], result)
        self.assertEqual(result["generation"], 1)
        self.assertTrue((self.install / "assets/songs/auto-new/Inst.ogg").is_file())
        self.assertFalse(donor.exists())

    def test_known_missing_dependencies_are_persisted_with_the_retained_record(self):
        donor = self.make_source("donor-diagnostics")

        result = self.run_fixture("fresh-diagnostic", donor)

        self.assertEqual(result["failed"], 0)
        diagnostics = result["records"][0]["dependencyDiagnostics"]
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0]["kind"], "character")
        self.assertEqual(diagnostics[0]["reference"], "unshipped-character")

    def test_truncated_rescans_fail_closed_without_changing_installed_assets(self):
        donor = self.make_source("donor-truncated", initial_songs=["stable"], next_songs=["stable", "new"])
        record = self.initial_import(donor)
        shutil_rmtree(donor)
        self.mark_record_stale(record)
        before_assets = tree_bytes(self.install / "assets")

        for mode in ("refresh-root-truncated", "refresh-package-truncated"):
            with self.subTest(mode=mode):
                result = self.run_fixture(mode, record["id"])
                self.assertEqual(result["status"], "error")
                self.assertIn("incomplete", result["error"].lower())
                self.assertEqual(tree_bytes(self.install / "assets"), before_assets)

    def test_empty_or_missing_expected_roots_fail_closed(self):
        donor = self.make_source("donor-missing-root", initial_songs=["stable"], next_songs=["stable", "new"])
        record = self.initial_import(donor)
        shutil_rmtree(donor)
        self.mark_record_stale(record)
        before_assets = tree_bytes(self.install / "assets")

        for mode in ("refresh-empty-roots", "refresh-missing-roots"):
            with self.subTest(mode=mode):
                result = self.run_fixture(mode, record["id"])
                self.assertEqual(result["status"], "error", result)
                self.assertIn("root", result["error"].lower())
                self.assertEqual(tree_bytes(self.install / "assets"), before_assets)

    def test_scan_errors_during_refresh_preserve_previous_imported_outputs(self):
        donor = self.make_source("donor-scan-error", initial_songs=["stable"], next_songs=["stable", "new"])
        record = self.initial_import(donor)
        shutil_rmtree(donor)
        self.mark_record_stale(record)
        before_assets = tree_bytes(self.install / "assets")

        result = self.run_fixture("refresh-scan-errors", record["id"])

        self.assertEqual(result["status"], "error", result)
        self.assertIn("chart could not be parsed", result["error"].lower())
        self.assertEqual(tree_bytes(self.install / "assets"), before_assets)

    def test_retained_source_tampering_blocks_refresh_without_touching_installed_files(self):
        donor = self.make_source("donor-tampered", initial_songs=["stable"], next_songs=["stable", "new"])
        record = self.initial_import(donor)
        shutil_rmtree(donor)
        self.mark_record_stale(record)
        before_assets = tree_bytes(self.install / "assets")
        retained_spec = self.install / "import-cache" / record["source"] / "package.json"
        self.assertTrue(retained_spec.is_file())
        source_spec = json.loads(retained_spec.read_text(encoding="utf-8"))
        source_spec["marker"] = "tampered-after-capture"
        retained_spec.write_text(json.dumps(source_spec), encoding="utf-8", newline='\n')

        result = self.run_fixture("refresh", record["id"])

        self.assertEqual(result["status"], "error", result)
        self.assertRegex(result["error"].lower(), r"snapshot|integrity|checksum|changed")
        self.assertEqual(tree_bytes(self.install / "assets"), before_assets)
        self.assertFalse((self.install / "assets/songs/new/Inst.ogg").exists())

    def test_unrelated_registry_edit_during_conversion_is_merged_and_preserved(self):
        donor = self.make_source("donor-concurrent-registry", initial_songs=["stable"], next_songs=["stable", "new"])
        record = self.initial_import(donor)
        shutil_rmtree(donor)
        self.mark_record_stale(record)

        result = self.run_fixture("refresh-concurrent-registry", record["id"])

        self.assertEqual(result["status"], "ok", result)
        registry = json.loads((self.install / REGISTRY).read_text(encoding="utf-8"))
        self.assertEqual(registry["concurrentEdit"], "keep during conversion")
        self.assertEqual(registry["owners"]["donor-concurrent-registry"], "v2-donor-concurrent-registry")
        self.assertTrue((self.install / "assets/songs/new/Inst.ogg").is_file())

    def test_unicode_shared_registry_baseline_survives_refresh(self):
        registry_path = self.install / REGISTRY
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["base"]["display"] = "Café 🎵"
        registry_path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8", newline='\n')
        donor = self.make_source("donor-unicode", initial_songs=["unicode-song"],
                                 next_songs=["unicode-song", "unicode-new"])
        record = self.initial_import(donor)
        shutil_rmtree(donor)
        self.mark_record_stale(record)

        result = self.run_fixture("refresh", record["id"])

        self.assertEqual(result["status"], "ok", result)
        refreshed_registry = json.loads(registry_path.read_text(encoding="utf-8"))
        self.assertEqual(refreshed_registry["base"]["display"], "Café 🎵")
        self.assertEqual(refreshed_registry["owners"]["donor-unicode"], "v2-donor-unicode")
        self.assertTrue((self.install / "assets/songs/unicode-new/Inst.ogg").is_file())

    def test_local_edit_conflict_preserves_user_bytes_and_does_not_publish_new_song(self):
        donor = self.make_source("donor-local", initial_songs=["local-song"], next_songs=["local-song", "new-song"])
        record = self.initial_import(donor)
        shutil_rmtree(donor)
        local_file = self.install / "assets/data/local-song/local-song.json"
        local_file.write_text('{"user":"edit"}', encoding="utf-8", newline='\n')
        self.mark_record_stale(record)

        result = self.run_fixture("refresh", record["id"])

        self.assertEqual(result["status"], "error")
        self.assertIn("conflict", result["error"].lower())
        self.assertEqual(local_file.read_text(encoding="utf-8"), '{"user":"edit"}')
        self.assertFalse((self.install / "assets/songs/new-song/Inst.ogg").exists())

    def test_failed_conversion_and_cancellation_leave_installed_files_unchanged(self):
        donor = self.make_source("donor-failures", initial_songs=["stable"], next_songs=["stable", "new"])
        record = self.initial_import(donor)
        shutil_rmtree(donor)
        self.mark_record_stale(record)
        before_assets = tree_bytes(self.install / "assets")
        before_manifest = self.manifest_bytes(record)

        for mode in ("refresh-fail", "refresh-cancel"):
            with self.subTest(mode=mode):
                result = self.run_fixture(mode, record["id"])

                self.assertEqual(result["status"], "error", result)
                self.assertEqual(tree_bytes(self.install / "assets"), before_assets)
                self.assertEqual(self.manifest_bytes(record), before_manifest)
                staging = self.install / "import-cache/staging"
                self.assertEqual(list(staging.iterdir()), [])

    def test_two_import_owners_preserve_registry_baseline_and_each_other(self):
        first = self.make_source("owner-a", initial_songs=["a-song"], next_songs=["a-song", "a-new"])
        second = self.make_source("owner-b", initial_songs=["b-song"], next_songs=["b-song", "b-new"])
        result = self.run_fixture("multi-fresh", first, second)
        self.assertEqual(result["failed"], 0)
        records = {entry["label"]: entry for entry in result["records"]}
        record_a = records["owner-a"]
        shutil_rmtree(first)
        shutil_rmtree(second)
        self.mark_record_stale(record_a)

        refreshed = self.run_fixture("refresh", record_a["id"])

        self.assertEqual(refreshed["status"], "ok", refreshed)
        registry = json.loads((self.install / REGISTRY).read_text(encoding="utf-8"))
        self.assertEqual(registry["base"], {"keep": True})
        self.assertEqual(registry["owners"]["owner-a"], "v2-owner-a")
        self.assertEqual(registry["owners"]["owner-b"], "v1-owner-b")
        self.assertTrue((self.install / "assets/songs/a-new/Inst.ogg").is_file())

    def test_first_retained_import_refuses_unowned_legacy_output_collision(self):
        donor = self.make_source("legacy-donor", initial_songs=["legacy-song"])
        target = self.install / "assets/data/legacy-song/legacy-song.json"
        target.parent.mkdir(parents=True)
        target.write_text("legacy installed bytes", encoding="utf-8", newline='\n')

        result = self.run_fixture("legacy-collision", donor)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("untracked", result["error"].lower())
        self.assertEqual(target.read_text(encoding="utf-8"), "legacy installed bytes")
        self.assertFalse((self.install / "assets/songs/legacy-song/Inst.ogg").exists())

    def test_first_enrollment_refuses_existing_legacy_namespace_without_owner_manifest(self):
        donor = self.make_source("legacy-namespace-donor")

        result = self.run_fixture("legacy-namespace", donor)

        self.assertEqual(result["status"], "blocked", result)
        self.assertIn("baseline", result["error"].lower())
        self.assertEqual(result["records"], [])
        namespace_root = self.install / "assets/imported_mods"
        legacy_files = list(namespace_root.rglob("old-import.hscript"))
        self.assertEqual(len(legacy_files), 1)
        self.assertEqual(legacy_files[0].read_text(encoding="utf-8"), "legacy bytes")
        self.assertFalse((self.install / "assets/songs/song-legacy-namespace-donor/Inst.ogg").exists())

    def test_first_enrollment_refuses_existing_duplicate_song_without_owner_baseline(self):
        donor = self.make_source("legacy-song-duplicate")

        result = self.run_fixture("legacy-duplicate-song", donor)

        self.assertEqual(result["status"], "blocked", result)
        self.assertIn("baseline", result["error"].lower())
        self.assertEqual(result["records"], [])
        self.assertFalse((self.install / "assets/songs/song-legacy-song-duplicate/Inst.ogg").exists())
        self.assertTrue(donor.is_dir())

    def manifest_bytes(self, record: dict) -> bytes:
        owner_hash = hashlib.sha256(("retained-import:" + record["id"]).encode()).hexdigest()
        return (self.install / "import-cache/state" / owner_hash / "manifest.json").read_bytes()


def tree_bytes(root: Path) -> dict:
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file()}


def shutil_rmtree(path: Path) -> None:
    import shutil
    shutil.rmtree(path)


if __name__ == "__main__":
    unittest.main()
