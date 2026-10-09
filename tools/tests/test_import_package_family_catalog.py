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
import PsychAssetProfile;
import PsychAssetProfile.PsychAssetProfileBuild;
import SourceMappedAssetPublisher;
import SourceMappedMediaPolicy;
import SourceMappedMediaPublisher;
import SourceLimeAssetIdentity;
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
  write(Path.join([source,"Project.xml"]),'<project><app packageName="com.nmvteam.nightmareengine" />'
   +'<assets path="assets/images" rename="assets/images" /></project>');
  write(Path.join([source,"assets","data","base-game","base.json"]),'{"song":{"bpm":100}}');
  write(Path.join([source,"assets","images","core.png"]),"provider core image");
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
    var id=Std.string(Reflect.field(planned.record,"id"));
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
   case "v3-core-handoff", "v3-container-only", "v3-legacy-runtime":
    var source=makeAssetGame("v3-core-handoff-source");
    if(mode=="v3-legacy-runtime") {
     for(label in ["alpha","beta"]) {
      FileSystem.deleteFile(Path.join([source,"content",label,"meta.json"]));
      var nested=Path.join([source,"content",label,"assets"]);
      for(name in FileSystem.readDirectory(nested))
       FileSystem.rename(Path.join([nested,name]),Path.join([source,"content",label,name]));
      FileSystem.deleteDirectory(nested);
     }
    }
    var planned=plannerRecord(source);
    var content=Path.join([planned.snapshot.snapshotRoot,"content"]);
    var providerNamespace:String=null;
    for(root in (cast planned.roots:Array<Dynamic>))
     if(root.engine=="Nightmare Vision"&&root.relative=="") providerNamespace=Std.string(root.namespace);
    if(providerNamespace==null) throw "retained scanner did not record the authenticated outer game root";
    var build:PsychAssetProfileBuild=cast {target:"html5",command:"",flags:[],values:[],flagsComplete:true};
    var providerProfile=PsychAssetProfile.resolveRetained(content,planned.snapshot.snapshotId,"",
     "Nightmare Vision",providerNamespace,build);
    if(providerProfile==null||providerProfile.provenance!="receipt-bound"||!providerProfile.complete)
     throw "outer core Project profile was not resolved from the retained snapshot: "+
      (providerProfile==null?"null":providerProfile.diagnostics.join("; "))+
      " content="+content+" project="+FileSystem.exists(Path.join([content,"Project.xml"]));
    planned.record.sourceAssetProfiles={version:1,snapshotId:planned.snapshot.snapshotId,roots:[
     {engine:"Nightmare Vision",rootRelative:"",namespace:providerNamespace,profile:providerProfile}]};
    var stage=Path.join([cache,"staging","v3-core-handoff"]);
    ensure(stage);
    var io=ImportIO.begin(install,stage);
    io.setNamespace(content,"Nightmare Vision",providerNamespace);
    io.recordResolvedNamespace(content,"Nightmare Vision",providerNamespace);
    io.setAssetProfile(content,content,planned.snapshot.snapshotId,"","Nightmare Vision",
     providerNamespace,providerProfile);
    var members=ImportPackageFamilyCatalog.sourceRoots(planned.snapshot.snapshotRoot,planned.record);
    if(members.length<2) throw "retained outer source did not prove two family packages";
    var packageNamespaces:Array<String>=[];
    for(member in members) {
     var relative=StringTools.replace(Path.normalize(member),"\\","/");
     var normalizedContent=StringTools.replace(Path.normalize(content),"\\","/");
     var memberRelative=relative.substr(normalizedContent.length+1);
     var namespace:String=null;
     for(root in (cast planned.roots:Array<Dynamic>))
      if(root.engine=="Nightmare Vision"&&(root.relative==memberRelative||root.relative==memberRelative+"/assets"))
       namespace=Std.string(root.namespace);
     if(namespace==null && mode=="v3-legacy-runtime") namespace="legacy-package-"+packageNamespaces.length;
     if(namespace==null) throw "family member has no scanner-owned namespace: "+memberRelative;
     io.setNamespace(member,"Nightmare Vision",namespace);
     io.recordResolvedNamespace(member,"Nightmare Vision",namespace);
     packageNamespaces.push(namespace);
     if(mode!="v3-legacy-runtime")
      File.saveContent(io.writePath("assets/imported_mods/"+namespace+"/meta.json"),Json.stringify({name:namespace}));
     File.saveContent(io.writePath("assets/imported_mods/"+namespace+"/.cammie-owner.json"),'{"engine":"Nightmare Vision","version":1}');
     if(mode!="v3-legacy-runtime")
      File.saveContent(io.writePath("assets/imported_mods/"+namespace+"/scripts/state.hxs"),"class State {} ");
    }
    var handoffs=ImportPackageFamilyCatalog.bindCoreAssetHandoffs(
     planned.snapshot.snapshotRoot,planned.record,io);
    if(handoffs==null||handoffs.length!=members.length)
     throw "catalog-authorized provider did not bind every family receiver";
    for(handoff in handoffs) {
     var corePlan=SourceMappedMediaPublisher.prepare(handoff.sourceRoot,"Nightmare Vision",
      handoff.destinationRoot,SourceMappedMediaPolicy.CORE_SCOPE,function():Bool return false);
     if(corePlan.failed||corePlan.cancelled||corePlan.identityPublication==null)
      throw "receiver core identity plan failed: "+corePlan.diagnostics.join("; ");
     SourceMappedMediaPublisher.publish(corePlan,function(sourcePath:String,destinationPath:String):Void {
      io.copy(sourcePath,destinationPath);
     },function():Bool return false,function(path:String,text:String):Void {
      File.saveContent(io.writePath(path),text);
     });
     if(corePlan.failed||corePlan.cancelled)
      throw "receiver core sidecar publication failed: "+corePlan.diagnostics.join("; ");
    }
    if(mode=="v3-container-only" || mode=="v3-legacy-runtime") {
     var oldRoots:Array<Dynamic>=cast planned.record.roots;
     planned.record.roots=oldRoots.filter(function(root) return root.relative=="");
    }
    if(mode=="v3-legacy-runtime") {
     if(ImportPackageFamilyCatalog.capturePublished(planned.snapshot.snapshotRoot,planned.record,io)!=null)
      throw "owner markers and core sidecars alone enrolled an empty package";
     for(namespace in packageNamespaces)
      File.saveContent(io.writePath("assets/imported_mods/"+namespace+"/scripts/state.hxs"),"class State {} ");
    }
    var published=ImportPackageFamilyCatalog.capturePublished(planned.snapshot.snapshotRoot,planned.record,io);
    if(published==null||published.version!=3||published.coreProvider==null)
     throw "transaction did not capture the authenticated v3 provider-core family";
    var badCatalog:Dynamic=haxe.Json.parse(Json.stringify(published));
    Reflect.setField(Reflect.field(badCatalog,"coreProvider"),"projectSha256",hash("wrong provider profile"));
    var tamperedRejected=false;
    try ImportRefreshTransaction.validatePackageFamilyCatalog(badCatalog,planned.record)
     catch(_:Dynamic) tamperedRejected=true;
    if(!tamperedRejected) throw "v3 catalog accepted a provider Project hash that disagreed with the retained profile";
    if(mode=="v3-container-only" || mode=="v3-legacy-runtime") {
     var migratedRoots:Array<Dynamic>=cast planned.record.roots;
     if(migratedRoots.length!=3) throw "container-only receipt did not retain its two proven receivers";
     var retained:Map<String,String>=new Map();
     for(root in migratedRoots) retained.set(Path.join([content,root.relative]),root.engine);
     var priorRoots=ImportRootScanner.setRetainedSourceRoots(retained);
     var priorEngines=ImportRootScanner.setRetainedSourceEngines(retained);
     var rescanned=ImportRootScanner.scan(content,"Nightmare Vision");
     ImportRootScanner.setRetainedSourceRoots(priorRoots);
     ImportRootScanner.setRetainedSourceEngines(priorEngines);
     planned.record.packageFamilyCatalog=published;
     for(root in migratedRoots) {
      var found=false;
      for(candidate in rescanned) if(Path.normalize(candidate.root)==Path.normalize(Path.join([content,root.relative]))) found=true;
      if(!found) found=ImportPackageFamilyCatalog.scanCoversMaterializedRoot(
       planned.snapshot.snapshotRoot,planned.record,root,rescanned);
      if(!found) throw "next retained rescan lost migrated root: "+root.relative;
     }
     var conflicting:Dynamic=haxe.Json.parse(Json.stringify(planned.record));
     conflicting.roots[1].namespace="conflicting-receiver";
     var before=Json.stringify(conflicting);
     if(ImportPackageFamilyCatalog.capturePublished(planned.snapshot.snapshotRoot,conflicting,io)!=null)
      throw "conflicting retained receiver namespace was accepted";
     if(Json.stringify(conflicting)!=before) throw "failed migration mutated its input receipt";
    }
    planned.record.packageFamilyCatalog=published;
    var invalidRefreshRecord:Dynamic=Reflect.copy(planned.record);
    var changedProfileCatalog:Dynamic=Reflect.copy(planned.record.sourceAssetProfiles);
    var changedProfileRoots:Array<Dynamic>=cast planned.record.sourceAssetProfiles.roots;
    var changedProfileRoot:Dynamic=Reflect.copy(changedProfileRoots[0]);
    var changedProviderProfile:Dynamic=Reflect.copy(changedProfileRoot.profile);
    changedProviderProfile.provenance="legacy-unverified";
    changedProfileRoot.profile=changedProviderProfile;
    Reflect.setField(changedProfileCatalog,"roots",[changedProfileRoot]);
    Reflect.setField(invalidRefreshRecord,"sourceAssetProfiles",changedProfileCatalog);
    var missingProviderRejected=false;
    try ImportPackageFamilyCatalog.bindCoreAssetHandoffs(
     planned.snapshot.snapshotRoot,invalidRefreshRecord,io) catch(_:Dynamic) missingProviderRejected=true;
    if(!missingProviderRejected)
     throw "refresh downgraded a previously published v3 core catalog after its provider profile became unprovable";
    ImportIO.end();
    var outputs:Array<ImportRefreshStagedOutput>=[];
    for(path in io.writtenPaths()) outputs.push({path:path,stagedPath:path});
    var id=Std.string(Reflect.field(planned.record,"id"));
    ensure(Path.join([cache,"records"]));
    write(Path.join([cache,"records",id+".json"]),Json.stringify({id:id}));
    var owner="retained-import:"+id;
    var applied=ImportRefreshTransaction.apply(install,stage,Path.join([cache,"state"]),owner,
     ["assets"],outputs,{importRecord:planned.record,registries:[]});
    if(applied.status!=ImportRefreshTransaction.STATUS_APPLIED)
     throw "v3 provider-core family transaction did not commit: "+applied.status;
    var committed=ImportRefreshTransaction.loadManifest(Path.join([cache,"state"]),owner);
    if(committed.packageFamilyCatalog==null||committed.packageFamilyCatalog.version!=3)
     throw "v3 core handoff catalog was not preserved by the committed manifest";
    var coreSidecars:Array<String>=[];
    for(namespace in packageNamespaces) {
     var sidecar="assets/imported_mods/"+namespace+"/"+
      SourceLimeAssetIdentity.sidecarRelativePath("Nightmare Vision","core");
     coreSidecars.push(sidecar);
     var found=false;
     for(file in committed.files) if(file.path==sidecar) found=true;
     if(!found) throw "committed owner manifest omitted its receiver core index: "+sidecar;
     var parsed:Dynamic=Json.parse(File.getContent(Path.join([install,sidecar])));
     var entries:Dynamic=Reflect.field(parsed,"entries");
     var mapped=false;
     if(Std.isOfType(entries,Array)) for(entry in (cast entries:Array<Dynamic>))
      if(Reflect.field(entry,"id")=="assets/images/core.png"
       && Reflect.field(entry,"ownerRelative")=="__nmv_core/images/core.png") mapped=true;
     if(!mapped) throw "receiver sidecar did not preserve the provider Lime ID and receiver core path";
     if(File.getContent(Path.join([install,"assets/imported_mods/"+namespace+"/__nmv_core/images/core.png"]))
      !="provider core image") throw "mapped core bytes were not staged below the receiver namespace";
    }
    var installedFamily=ImportPackageFamilyCatalog.forOwner("assets/imported_mods/"+packageNamespaces[0]);
    if(installedFamily.length!=2) throw "committed family did not resolve its installed runtime members";
    if(mode=="v3-legacy-runtime") {
     for(namespace in packageNamespaces)
      FileSystem.deleteFile(Path.join([install,"assets/imported_mods/"+namespace+"/scripts/state.hxs"]));
     if(ImportPackageFamilyCatalog.forOwner("assets/imported_mods/"+packageNamespaces[0]).length!=0)
      throw "owner markers and core outputs kept a payload-free family available";
    }
    report({version:committed.packageFamilyCatalog.version,providerNamespace:providerNamespace,
     providerProjectSha256:providerProfile.projectSha256,receiverNamespaces:packageNamespaces,
     coreSidecars:coreSidecars});
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

    def test_retained_provider_core_is_published_and_committed_under_each_receiver(self):
        result = self.run_fixture("v3-core-handoff")
        self.assertEqual(result["version"], 3)
        self.assertTrue(result["providerNamespace"])
        self.assertEqual(len(result["receiverNamespaces"]), 2)
        self.assertEqual(len(result["coreSidecars"]), 2)

    def test_container_only_receipt_retains_newly_published_core_receivers(self):
        result = self.run_fixture("v3-container-only")
        self.assertEqual(result["version"], 3)
        self.assertEqual(len(result["receiverNamespaces"]), 2)
        self.assertEqual(len(result["coreSidecars"]), 2)

    def test_legacy_metadata_free_packages_require_owned_noncore_payload(self):
        result = self.run_fixture("v3-legacy-runtime")
        self.assertEqual(result["version"], 3)
        self.assertEqual(len(result["receiverNamespaces"]), 2)


if __name__ == "__main__":
    unittest.main()
