"""Verify that retained sibling roots require one committed source family."""
from haxe_test_support import HAXE_COMMAND, TEST_TMP

import json
import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source"
TJSON = ROOT / ".haxelib/tjson/1,4,0"
HAXE = ROOT / ".tools/haxe" / ("haxe.exe" if os.name == "nt" else "haxe")


FIXTURE = r'''import haxe.Json;
import haxe.crypto.Sha256;
import haxe.io.Bytes;
import haxe.io.Path;
import ImportRefreshTransaction.ImportRefreshPackageFamilyCatalog;
import ImportRefreshTransaction.ImportRefreshStagedOutput;
import sys.FileSystem;
import sys.io.File;

class ImportPackageFamilyCatalogFixture {
 static var install:String;
 static var cache:String;

 static function hash(value:String):String return Sha256.make(Bytes.ofString(value)).toHex();

 static function ensure(path:String):Void {
  if(FileSystem.exists(path)) return;
  var parent=Path.directory(path);
  if(parent!=null&&parent!=""&&parent!=path&&!FileSystem.exists(parent)) ensure(parent);
  FileSystem.createDirectory(path);
 }

 static function write(path:String,text:String):Void {
  ensure(Path.directory(path));
  File.saveContent(path,text);
 }

 static function makeDonor(name:String,foreign:Bool=false):Dynamic {
  var source=Path.join([install,"donors",name]);
  write(Path.join([source,"Project.xml"]),'<project><app packageName="com.nmvteam.nightmareengine" /></project>');
  for(label in ["old-dsides","new-dsides"]) {
   var song=label=="old-dsides"?"old-song":"new-song";
   write(Path.join([source,"content",label,"songs",song,"data",song+".json"]),'{"format":"nmv2"}');
  }
  if(foreign) write(Path.join([source,"content","separate.txt"]),"different retained source snapshot");
  var snapshot=ImportSourceSnapshot.capture(source,Path.join([cache,"sources"]),
   "Nightmare Vision","0.0.16",{workerCount:1});
  if(!snapshot.complete) throw "fixture source snapshot did not complete: "+snapshot.error;
  return snapshot;
 }

 static function makeAssetGame(name:String):String {
  var source=Path.join([install,"donors",name]);
  // This outer-root proof intentionally comes from the compiled executable
  // marker, not Project.xml, as in a native packaged game distribution.
  write(Path.join([source,"NightmareVision.exe"]),"com.nmvTeam.nightmareEngine");
  write(Path.join([source,"assets","data","base-game","base.json"]),'{"song":{"bpm":100}}');
  write(Path.join([source,"assets","songs","base-game","Inst.ogg"]),"base audio");
  write(Path.join([source,"content","alpha","meta.json"]),'{"name":"alpha"}');
  write(Path.join([source,"content","alpha","assets","songs","alpha","data","alpha.json"]),'{"format":"nmv2"}');
  write(Path.join([source,"content","alpha","assets","songs","alpha","audio","Inst.ogg"]),"alpha audio");
  write(Path.join([source,"content","beta","meta.json"]),'{"name":"beta"}');
  write(Path.join([source,"content","beta","assets","scripts","states","Fixture.hx"]),"class Fixture {}");
  write(Path.join([source,"content","beta","assets","images","placeholder.txt"]),"image marker");
  return source;
 }

 static function plannerRecord(source:String):Dynamic {
  var scan=ImportRootScanner.scanDetailed(source,ImportEngine.NIGHTMARE_VISION);
  var normalizedSource=StringTools.replace(Path.normalize(FileSystem.fullPath(source)),"\\","/");
  var roots:Array<Dynamic>=[];
  var index=0;
  for(root in scan.roots) {
   var normalizedRoot=StringTools.replace(Path.normalize(root.root),"\\","/");
   var relative=normalizedRoot==normalizedSource?"":normalizedRoot.substr(normalizedSource.length+1);
   roots.push({relative:relative,engine:root.engine,namespace:"scan-root-"+index++,
    label:Path.withoutDirectory(root.root),evidence:root.evidence.copy()});
  }
  var engines:Array<String>=[];
  for(root in roots) if(engines.indexOf(root.engine)<0) engines.push(root.engine);
  var snapshot=ImportSourceSnapshot.capture(source,Path.join([cache,"sources"]),
   "Nightmare Vision","0.0.16",{workerCount:1});
  if(!snapshot.complete) throw "planner source snapshot did not complete: "+snapshot.error;
  return {snapshot:snapshot,record:{schemaVersion:1,id:hash("asset-game-import"),
   snapshotId:snapshot.snapshotId,source:"sources/"+snapshot.snapshotId+"/content",
   type:"Nightmare Vision",engines:engines,roots:roots,label:"native-game",
   exclusions:[],dependencyDiagnostics:[],revisions:[]},roots:roots};
 }

 static function record(snapshot:Dynamic,id:String,directory:String,namespace:String):Dynamic {
  return {
   schemaVersion:1,id:id,snapshotId:snapshot.snapshotId,
   source:"sources/"+snapshot.snapshotId+"/content",type:"Nightmare Vision",
   engines:["Nightmare Vision"],
   roots:[{relative:"content/"+directory,engine:"Nightmare Vision",namespace:namespace,label:directory}],
   label:"fixture",exclusions:[],dependencyDiagnostics:[],revisions:[]
  };
 }

 static function publish(snapshot:Dynamic,id:String,directory:String,namespace:String,withCatalog:Bool):Dynamic {
  var retained=record(snapshot,id,directory,namespace);
  if(withCatalog) {
   var catalog=ImportPackageFamilyCatalog.capture(snapshot.snapshotRoot,retained);
   if(catalog==null) throw "expected a structurally detected two-member catalog";
   retained.packageFamilyCatalog=catalog;
  }
  var records=Path.join([cache,"records"]);
  ensure(records);
  write(Path.join([records,id+".json"]),Json.stringify({id:id}));
  var outputPath="assets/imported_mods/"+namespace+"/meta.json";
  var runtimePath="assets/imported_mods/"+namespace+"/scripts/owned.hxs";
  var stage=Path.join([cache,"staging",id]);
  write(Path.join([stage,outputPath]),"fixture owner="+namespace);
  write(Path.join([stage,runtimePath]),"fixture runtime="+namespace);
  var result=ImportRefreshTransaction.apply(install,stage,Path.join([cache,"state"]),
   "retained-import:"+id,["assets"],[{path:outputPath,stagedPath:outputPath},
    {path:runtimePath,stagedPath:runtimePath}],
   {importRecord:retained,registries:[]});
  if(result.status!=ImportRefreshTransaction.STATUS_APPLIED) throw "fixture publication failed: "+result.status;
  return {record:retained,result:result};
 }

 static function family(snapshot:Dynamic,prefix:String,withCatalog:Bool=true):Array<Dynamic> {
  var oldId=hash(prefix+"-old");
  var newId=hash(prefix+"-new");
  var oldNamespace="nightmare-vision-"+prefix+"-old";
  var newNamespace="nightmare-vision-"+prefix+"-new";
  return [
   publish(snapshot,oldId,"old-dsides",oldNamespace,withCatalog),
   publish(snapshot,newId,"new-dsides",newNamespace,withCatalog)
  ];
 }

 static function memberRoots(members:Array<NightmareVisionModFamilyMember>):Array<String> {
  var result:Array<String>=[];
  for(member in members) result.push(member.root);
  result.sort(Reflect.compare);
  return result;
 }

 static function scannerMapPreserved(owner:String):Bool {
  var sentinel:Map<String,String>=new Map();
  sentinel.set("keep", "Psych Engine");
  var prior=ImportRootScanner.setRetainedSourceEngines(sentinel);
  ImportPackageFamilyCatalog.forOwner(owner);
  var after=ImportRootScanner.setRetainedSourceEngines(prior);
  var unchanged=after==sentinel;
  ImportRootScanner.setRetainedSourceEngines(after);
  return unchanged;
 }

 static function assertCatalogRejected(value:Dynamic,recordValue:Dynamic):Bool {
  try {
   ImportRefreshTransaction.validatePackageFamilyCatalog(value,recordValue);
   return false;
  } catch(_:Dynamic) return true;
 }

 static function tamperManifest(path:String):Void {
  var raw:Dynamic=Json.parse(File.getContent(path));
  Reflect.setField(raw,"packageFamilyCatalog",{version:1,engine:"Nightmare Vision",
   snapshotId:"0000000000000000000000000000000000000000000000000000000000000000",
   containerRelative:"content",members:[]});
  File.saveContent(path,Json.stringify(raw));
 }

 static function report(value:Dynamic):Void Sys.println(Json.stringify(value));

 static function main():Void {
  var args=Sys.args();
  var mode=args[0];
  install=Path.normalize(FileSystem.fullPath(args[1]));
  cache=Path.join([install,"import-cache"]);
  ensure(cache);
  Sys.setCwd(install);
  switch(mode) {
   case "positive":
    var snapshot=makeDonor("source");
    var pair=family(snapshot,"shared",true);
    var owner="assets/imported_mods/nightmare-vision-shared-old";
    var members=ImportPackageFamilyCatalog.forOwner(owner);
    report({members:members,roots:memberRoots(members),scannerMapPreserved:scannerMapPreserved(owner),
     snapshotId:snapshot.snapshotId,manifestCatalog:ImportRefreshTransaction.loadManifest(
      Path.join([cache,"state"]),"retained-import:"+pair[0].record.id).packageFamilyCatalog});
   case "legacy-reconstruction":
    var snapshot=makeDonor("legacy-source");
    family(snapshot,"legacy",false);
    var members=ImportPackageFamilyCatalog.forOwner("assets/imported_mods/nightmare-vision-legacy-old");
    report({members:members,roots:memberRoots(members),scannerMapPreserved:scannerMapPreserved("assets/imported_mods/missing")});
   case "tampered":
    var snapshot=makeDonor("tamper-source");
    var pair=family(snapshot,"tamper",true);
    tamperManifest(pair[1].result.manifestPath);
    var afterSiblingTamper=ImportPackageFamilyCatalog.forOwner("assets/imported_mods/nightmare-vision-tamper-old");
    tamperManifest(pair[0].result.manifestPath);
    var afterOwnerTamper=ImportPackageFamilyCatalog.forOwner("assets/imported_mods/nightmare-vision-tamper-old");
    report({afterSiblingTamper:memberRoots(afterSiblingTamper),afterOwnerTamper:memberRoots(afterOwnerTamper)});
   case "foreign-snapshot":
    var selected=makeDonor("selected-source");
    family(selected,"selected",true);
    var foreign=makeDonor("foreign-source",true);
    publish(foreign,hash("foreign-old"),"old-dsides","nightmare-vision-foreign-old",true);
    var members=ImportPackageFamilyCatalog.forOwner("assets/imported_mods/nightmare-vision-selected-old");
    report({roots:memberRoots(members),selectedSnapshot:selected.snapshotId,foreignSnapshot:foreign.snapshotId});
   case "duplicate-label":
    var snapshot=makeDonor("duplicate-source");
    family(snapshot,"duplicate",true);
    publish(snapshot,hash("duplicate-old-copy"),"old-dsides","nightmare-vision-duplicate-old-copy",true);
    var members=ImportPackageFamilyCatalog.forOwner("assets/imported_mods/nightmare-vision-duplicate-old");
    report({roots:memberRoots(members)});
   case "invalid-catalog":
    var snapshot=makeDonor("invalid-source");
    var committed=record(snapshot,hash("invalid-old"),"old-dsides","nightmare-vision-invalid-old");
    var valid=ImportPackageFamilyCatalog.capture(snapshot.snapshotRoot,committed);
    if(valid==null) throw "missing baseline catalog";
    var otherSnapshot=Reflect.copy(valid);
    otherSnapshot.snapshotId=hash("foreign-snapshot");
    var foreignSnapshotRejected=assertCatalogRejected(otherSnapshot,committed);
    var otherContainer=Reflect.copy(valid);
    otherContainer.containerRelative="content/nested";
    var foreignContainerRejected=assertCatalogRejected(otherContainer,committed);
    report({foreignSnapshotRejected:foreignSnapshotRejected,foreignContainerRejected:foreignContainerRejected});
   case "planner-assets":
    var source=makeAssetGame("planner-assets-source");
    var planned=plannerRecord(source);
    var members=ImportPackageFamilyCatalog.sourceRoots(planned.snapshot.snapshotRoot,planned.record);
    var relativeMembers:Array<String>=[];
    for(member in members) {
     var normalized=StringTools.replace(Path.normalize(member),"\\","/");
     var normalizedContent=StringTools.replace(Path.normalize(Path.join([planned.snapshot.snapshotRoot,"content"])),"\\","/");
     relativeMembers.push(normalized.substr(normalizedContent.length+1));
    }
   relativeMembers.sort(Reflect.compare);
    var scanRoots:Array<String>=[];
    for(root in (cast planned.roots:Array<Dynamic>)) scanRoots.push(Std.string(root.relative));
    var stage=Path.join([cache,"staging","planner-assets-publish"]);
    ensure(stage);
    var io=ImportIO.begin(install,stage);
    var published:ImportRefreshTransaction.ImportRefreshPackageFamilyCatalog=null;
    try {
     for(member in members) {
      var directory=Path.withoutDirectory(member);
      var assetRelative="content/"+directory+"/assets";
      var namespace:String=null;
      for(root in (cast planned.roots:Array<Dynamic>))
       if(root.relative==assetRelative) namespace=Std.string(root.namespace);
      if(namespace==null) throw "catalog member did not come from a scanned assets root: "+assetRelative;
      io.recordResolvedNamespace(member,"Nightmare Vision",namespace);
      write(io.writePath("assets/imported_mods/"+namespace+"/meta.json"),"config="+directory);
      write(io.writePath("assets/imported_mods/"+namespace+"/scripts/state.hxs"),"runtime="+directory);
     }
     published=ImportPackageFamilyCatalog.capturePublished(planned.snapshot.snapshotRoot,planned.record,io);
    } catch(error:Dynamic) {
     ImportIO.end();
     throw error;
    }
    ImportIO.end();
    if(published==null) throw "scanned assets-root package family was not captured after publication";
    var publishedNamespaces:Array<String>=[];
    for(member in published.members) publishedNamespaces.push(member.namespace);
    publishedNamespaces.sort(Reflect.compare);
    planned.record.packageFamilyCatalog=published;
    var id=Std.string(planned.record.id);
    var records=Path.join([cache,"records"]);
    ensure(records);
    write(Path.join([records,id+".json"]),Json.stringify({id:id}));
    var outputs:Array<ImportRefreshStagedOutput>=[];
    for(path in io.writtenPaths()) outputs.push({path:path,stagedPath:path});
    var owner="retained-import:"+id;
    var applied=ImportRefreshTransaction.apply(install,stage,Path.join([cache,"state"]),owner,
     ["assets"],outputs,{importRecord:planned.record,registries:[]});
    if(applied.status!=ImportRefreshTransaction.STATUS_APPLIED)
     throw "scanned assets-root package family transaction did not commit: "+applied.status;
    var previous=ImportRefreshTransaction.loadManifest(Path.join([cache,"state"]),owner);
    write(Path.join([source,"content","alpha","revision-marker.txt"]),"changed source bytes");
    var changed=ImportSourceSnapshot.capture(source,Path.join([cache,"sources"]),
     "Nightmare Vision","0.0.16",{workerCount:1});
    if(!changed.complete || changed.snapshotId==planned.snapshot.snapshotId)
     throw "source-family migration fixture did not create a changed authenticated snapshot";
    var nextRecord:Dynamic=Reflect.copy(cast planned.record);
    Reflect.setField(nextRecord,"snapshotId",changed.snapshotId);
    Reflect.setField(nextRecord,"source","sources/"+changed.snapshotId+"/content");
    var reusable=ImportPackageFamilyCatalog.reusableNamespaces(install,previous,changed.snapshotRoot,nextRecord);
    var reusedNamespaces:Array<String>=[];
    for(namespace in reusable) reusedNamespaces.push(namespace);
    reusedNamespaces.sort(Reflect.compare);
    report({scanRoots:scanRoots,members:relativeMembers,publishedNamespaces:publishedNamespaces,
     reusedNamespaces:reusedNamespaces,
     executableProof:ImportPackageFamilyCatalog.isAuthenticatedNightmareVisionContainer(
      Path.join([planned.snapshot.snapshotRoot,"content"]))});
   case "rebase":
    var first=makeDonor("rebase-before");
    var id=hash("stable-family-import");
    var oldRecord:Dynamic={schemaVersion:1,id:id,snapshotId:first.snapshotId,
     source:"sources/"+first.snapshotId+"/content",type:"Nightmare Vision",engines:["Nightmare Vision"],
     roots:[{relative:"",engine:"Nightmare Vision",namespace:"nightmare-vision-container-root",
      label:"rebase-before",evidence:["Nightmare Vision Haxe project package: com.nmvTeam.nightmareEngine"]}],
     label:"rebase-before",exclusions:[],dependencyDiagnostics:[],revisions:[]};
    var oldCatalog:ImportRefreshPackageFamilyCatalog={version:2,engine:"Nightmare Vision",snapshotId:first.snapshotId,
     containerRelative:"content",members:[
      {directory:"old-dsides",sourceRelative:"content/old-dsides",namespace:"nightmare-vision-family-old"},
      {directory:"new-dsides",sourceRelative:"content/new-dsides",namespace:"nightmare-vision-family-new"}]};
    oldRecord.packageFamilyCatalog=oldCatalog;
    var recordDirectory=Path.join([cache,"records"]);
    ensure(recordDirectory);
    write(Path.join([recordDirectory,id+".json"]),Json.stringify({id:id}));
    var stage=Path.join([cache,"staging",id]);
    var outputs:Array<ImportRefreshStagedOutput>=[];
    for(member in oldCatalog.members) {
     var prefix="assets/imported_mods/"+member.namespace+"/";
     var configPath=prefix+"meta.json";
     var runtimePath=prefix+"scripts/owned.hxs";
     write(Path.join([stage,configPath]),"config="+member.directory);
     write(Path.join([stage,runtimePath]),"runtime="+member.directory);
     outputs.push({path:configPath,stagedPath:configPath});
     outputs.push({path:runtimePath,stagedPath:runtimePath});
    }
    var applied=ImportRefreshTransaction.apply(install,stage,Path.join([cache,"state"]),
     "retained-import:"+id,["assets"],outputs,{importRecord:oldRecord,registries:[]});
    if(applied.status!=ImportRefreshTransaction.STATUS_APPLIED) throw "old family publication failed: "+applied.status;
    var previous=ImportRefreshTransaction.loadManifest(Path.join([cache,"state"]),"retained-import:"+id);
    var changed=makeDonor("rebase-after",true);
    var nextRecord:Dynamic={schemaVersion:1,id:id,snapshotId:changed.snapshotId,
     source:"sources/"+changed.snapshotId+"/content",type:"Nightmare Vision",engines:["Nightmare Vision"],
     roots:[{relative:"",engine:"Nightmare Vision",namespace:"nightmare-vision-container-root",
      label:"rebase-after",evidence:["Nightmare Vision Haxe project package: com.nmvTeam.nightmareEngine"]}],
     label:"rebase-after",exclusions:[],dependencyDiagnostics:[],revisions:[]};
    var reused=ImportPackageFamilyCatalog.reusableNamespaces(install,previous,changed.snapshotRoot,nextRecord);
    report({oldSnapshot:first.snapshotId,newSnapshot:changed.snapshotId,
     namespaces:[reused.get("content/new-dsides"),reused.get("content/old-dsides")]});
   default: throw "unknown fixture mode: "+mode;
  }
 }
}'''


class ImportPackageFamilyCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HAXE.is_file():
            raise unittest.SkipTest("portable Haxe is unavailable")

    def setUp(self):
        temp_root = str(TEST_TMP) if os.environ.get("CAMMIE_TEST_TMP") else None
        self.temp = tempfile.TemporaryDirectory(dir=temp_root)
        self.addCleanup(self.temp.cleanup)
        self.install = Path(self.temp.name) / "install"
        self.install.mkdir()
        self.fixture_dir = Path(self.temp.name) / "haxe"
        self.fixture_dir.mkdir()
        (self.fixture_dir / "ImportPackageFamilyCatalogFixture.hx").write_text(
            FIXTURE, encoding="utf-8", newline="\n"
        )

    def run_fixture(self, mode: str) -> dict:
        result = subprocess.run(
            [*HAXE_COMMAND, "-cp", str(SOURCE), "-cp", str(TJSON), "-cp", str(self.fixture_dir),
             "--run", "ImportPackageFamilyCatalogFixture", mode, str(self.install)],
            cwd=ROOT,
            env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = [line for line in result.stdout.splitlines() if line.startswith("{")]
        self.assertTrue(lines, result.stdout + result.stderr)
        return json.loads(lines[-1])

    def test_same_snapshot_committed_siblings_are_returned_and_map_is_restored(self):
        result = self.run_fixture("positive")
        self.assertEqual(result["roots"], [
            "assets/imported_mods/nightmare-vision-shared-new",
            "assets/imported_mods/nightmare-vision-shared-old",
        ])
        self.assertEqual(len(result["manifestCatalog"]["members"]), 2)
        self.assertTrue(result["scannerMapPreserved"])

    def test_legacy_manifests_reconstruct_only_from_their_retained_snapshot(self):
        result = self.run_fixture("legacy-reconstruction")
        self.assertEqual(result["roots"], [
            "assets/imported_mods/nightmare-vision-legacy-new",
            "assets/imported_mods/nightmare-vision-legacy-old",
        ])
        self.assertTrue(result["scannerMapPreserved"])

    def test_tampered_manifest_receipts_remove_family_authority(self):
        result = self.run_fixture("tampered")
        self.assertEqual(result["afterSiblingTamper"], ["assets/imported_mods/nightmare-vision-tamper-old"])
        self.assertEqual(result["afterOwnerTamper"], [])

    def test_foreign_snapshot_with_equal_labels_is_not_joined(self):
        result = self.run_fixture("foreign-snapshot")
        self.assertNotEqual(result["selectedSnapshot"], result["foreignSnapshot"])
        self.assertEqual(result["roots"], [
            "assets/imported_mods/nightmare-vision-selected-new",
            "assets/imported_mods/nightmare-vision-selected-old",
        ])

    def test_duplicate_label_to_distinct_installed_roots_is_ambiguous(self):
        result = self.run_fixture("duplicate-label")
        self.assertEqual(result["roots"], [])

    def test_catalog_rejects_foreign_snapshot_and_container(self):
        result = self.run_fixture("invalid-catalog")
        self.assertTrue(result["foreignSnapshotRejected"])
        self.assertTrue(result["foreignContainerRejected"])

    def test_changed_source_snapshot_reuses_exact_owned_family_namespaces(self):
        result = self.run_fixture("rebase")
        self.assertNotEqual(result["oldSnapshot"], result["newSnapshot"])
        self.assertEqual(result["namespaces"], [
            "nightmare-vision-family-new",
            "nightmare-vision-family-old",
        ])

    def test_planner_recorded_assets_roots_canonicalize_to_authenticated_package_metadata(self):
        result = self.run_fixture("planner-assets")
        self.assertIn("", result["scanRoots"])
        self.assertIn("content/alpha/assets", result["scanRoots"])
        self.assertIn("content/beta/assets", result["scanRoots"])
        self.assertTrue(result["executableProof"])
        self.assertEqual(result["members"], ["content/alpha", "content/beta"])
        self.assertEqual(result["publishedNamespaces"], ["scan-root-1", "scan-root-2"])
        self.assertEqual(result["reusedNamespaces"], ["scan-root-1", "scan-root-2"])


if __name__ == "__main__":
    unittest.main()
