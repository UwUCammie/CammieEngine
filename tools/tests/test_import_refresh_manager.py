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
    "ModuleFunctions.hx": r'''import haxe.io.Path;
import ImportIO;
import ImportFile;
typedef SongImportBatchResult = {
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
 public static var handoffCalls=0;
 public static var handoffNames:Array<Array<String>>=[];
 public static var handoffFailure:Dynamic=null;
 public static var familyPublishGeneration=0;
 public static var publishedFamilyRoots:Array<String>=[];
 public static var publishedFamilyNamespaces:Array<String>=[];
 public static function setImportBackgroundMode(value:Bool):Void {}
 public static function setImportCancelCallback(value:Dynamic):Void {}
 public static function setImportProgressCallback(value:Dynamic):Void {}
 public static function publishNightmareVisionFamilyMemberRoots(roots:Array<String>):Dynamic {
  familyPublishGeneration++;
  publishedFamilyRoots=roots==null?[]:roots.copy();
  publishedFamilyNamespaces=[];
  var context=ImportIO.current();
  if(context!=null&&roots!=null) for(root in roots) {
   var namespace=context.namespace(root, "Nightmare Vision");
   var assets=Path.join([root,"assets"]);
   if(namespace==null||namespace=="") {
    if(familyPublishGeneration==1) namespace="family-"+Path.withoutDirectory(root);
    else namespace=context.namespace(assets, "Nightmare Vision");
   }
   if(namespace==null||namespace=="") continue;
   context.setNamespace(root,"Nightmare Vision",namespace);
   context.recordResolvedNamespace(root,"Nightmare Vision",namespace);
   publishedFamilyNamespaces.push(namespace);
   ImportFile.saveContent("assets/imported_mods/"+namespace+"/meta.json", "{\"name\":\""+Path.withoutDirectory(root)+"\"}");
   ImportFile.saveContent("assets/imported_mods/"+namespace+"/scripts/states/FixtureState.hx", "class FixtureState {}");
  }
  return {copied:0,skipped:0,failed:0,errors:[]};
 }
 public static function completeImportOnMainThread(names:Array<String>):Void {
  if(handoffFailure!=null)throw handoffFailure;
  handoffCalls++;handoffNames.push(names.copy());
 }
}''',
    "flixel/FlxG.hx": r'''package flixel;
class FlxG { public static var state:Dynamic=null; }''',
    "PlayState.hx": r'''class PlayState { public function new() {} }''',
    "RuntimeImportSmokeState.hx": r'''class RuntimeImportSmokeState { public function new() {} }''',
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
 @:optional var name:String;
 @:optional var source:String;
 @:optional var sourceFolder:String;
 @:optional var destinationFolder:String;
 @:optional var willImport:Bool;
 @:optional var charts:Array<String>;
}
class ImportWorkflow {
 public static var rootTruncated:Bool=false;
 public static var packageTruncated:Bool=false;
 public static var overrideRoots:Null<Array<Dynamic>>=null;
 public static var overrideRootRelatives:Null<Array<String>>=null;
 public static var rootDiagnostics:Array<Dynamic>=[];
 public static var packageDiagnostics:Array<Dynamic>=[];
 public static var scanErrors:Array<String>=[];
 public static var missing:Array<ImportScanSong>=[];
 public static var existingDuplicate:Bool=false;
 public static function scanNow(source:String,type:String):ImportScanResult {
  var songs=missing.copy();
  var packagePath=haxe.io.Path.join([source,"package.json"]);
  if(sys.FileSystem.exists(packagePath)) {
   try {
    var spec:Dynamic=haxe.Json.parse(sys.io.File.getContent(packagePath));
    var names:Array<String>=cast Reflect.field(spec,"initialSongs");
    if(names!=null) for(name in names) songs.push({name:name,source:source,sourceFolder:name,
     destinationFolder:name,willImport:true,charts:[haxe.io.Path.join([source,"data",name,name+".json"])],missing:[]});
   } catch(_:Dynamic) {}
  }
  if(existingDuplicate) songs.push({missing:[],duplicate:true,sourceDuplicate:false});
  var detected=overrideRoots==null?[{root:source,engine:type}]:overrideRoots.copy();
  if(overrideRoots!=null&&overrideRootRelatives!=null&&overrideRootRelatives.length==overrideRoots.length)
   for(index in 0...detected.length) {
    var relative=overrideRootRelatives[index];
    detected[index]={root:relative==""?source:haxe.io.Path.join([source,relative]),
     engine:Reflect.field(overrideRoots[index],"engine"),
     evidence:Reflect.field(overrideRoots[index],"evidence")};
   }
  return {
   detectedRoots:detected, detectedEngines:[type],
   rootScanDiagnostics:rootDiagnostics.copy(), packageScanDiagnostics:packageDiagnostics.copy(),
   rootScanTruncated:rootTruncated, packageScanTruncated:packageTruncated,
   missingDependencies:missing.length, errors:scanErrors.copy(), songs:songs
  };
 }
 public static function convertRetainedSource(source:String,scan:ImportScanResult,
  names:Map<String,String>):SongImportBatchResult
  return ImportRefreshManagerFixture.convertRetainedSource(source,scan,names);
}''',
    "CompatScriptManifest.hx": r'''import haxe.Json;
import haxe.crypto.Md5;
import haxe.io.Path;
typedef CompatScriptRoot={var engine:String;var path:String;@:optional var dependency:Bool;}
typedef CompatScriptManifestData={var version:Int;var roots:Array<CompatScriptRoot>;@:optional var selectedRoot:String;}
class CompatScriptManifest {
 public static inline var FILE_NAME:String="compatScripts.json";
 public static function namespaceFor(source:String,engine:String):String {
  var context=ImportIO.current();
  if(context!=null) {
   var retained=context.namespace(source,engine);
   if(retained!=null&&retained!="") return retained;
  }
  return StringTools.replace(engine.toLowerCase()," ","-")+"-"+Md5.encode(Path.normalize(source)).substr(0,12);
 }
 public static function parse(raw:String):CompatScriptManifestData return cast Json.parse(raw);
 public static function selectedRoot(data:CompatScriptManifestData):String
  return data==null||data.selectedRoot==null?"":data.selectedRoot;
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
import flixel.FlxG;
import PlayState;
import ImportWorkflow.ImportScanResult;
import ImportWorkflow.ImportScanSong;
import ModuleFunctions.SongImportBatchResult;
import ImportRefreshAvailabilitySnapshot.ImportRefreshPendingSong;
import sys.FileSystem;
import sys.io.File;

@:access(ImportRefreshManager)
class ImportRefreshManagerFixture {
 static inline var REGISTRY:String="assets/data/freeplaySongJson.json";
 static var cancelAfterWrite:Bool=false;
 static var delayOwner:String="";
 static var delayMillis:Int=0;
 static var compatDependencyRoot:String="";

 static function scan(source:String):ImportScanResult {
  var result=ImportWorkflow.scanNow(source,"Psych Engine");
  var spec:Dynamic=Json.parse(File.getContent(Path.join([source,"package.json"])));
  var names:Array<String>=cast spec.initialSongs;
  var candidates:Array<ImportScanSong>=[for(song in names) {name:song,source:source,sourceFolder:song,
   destinationFolder:song,willImport:true,charts:[Path.join([source,"data",song,song+".json"])],
   missing:[],duplicate:false,sourceDuplicate:false}];
  result.songs=candidates.concat(result.songs);
  return result;
 }

 static function converter(useNextSongs:Bool, failAfterWrite:Bool=false,
  cancelAfterWriteRequested:Bool=false, mutateRegistryAfterWrite:Bool=false,
  mutateOwnedRegistryAfterWrite:Bool=false):((String,ImportScanResult,Map<String,String>)->SongImportBatchResult) {
  return function(source:String,scan:ImportScanResult,names:Map<String,String>):SongImportBatchResult {
   var spec:Dynamic=Json.parse(File.getContent(Path.join([source,"package.json"])));
   var songNames:Array<String>=cast (useNextSongs ? spec.nextSongs : spec.initialSongs);
   var version:String=Std.string(useNextSongs ? spec.nextVersion : spec.initialVersion);
   if(useNextSongs&&delayMillis>0&&Std.string(spec.ownerKey)==delayOwner)
    Sys.sleep(delayMillis/1000.0);

   var registry:Dynamic={};
   if(ImportFileSystem.exists(REGISTRY)) {
    try registry=Json.parse(ImportFile.getContent(REGISTRY)) catch(_:Dynamic) registry={};
   }
   if(Reflect.field(registry,"owners")==null) Reflect.setField(registry,"owners",{});
   var owners:Dynamic=Reflect.field(registry,"owners");
   Reflect.setField(owners,Std.string(spec.ownerKey),version);
   Reflect.setField(registry,"owners",owners);
   var labels:Dynamic=Reflect.field(registry,"labels");
   if(labels==null) labels={};
   Reflect.setField(labels,Std.string(spec.ownerKey),"stable-"+Std.string(spec.ownerKey));
   Reflect.setField(registry,"labels",labels);
   var groups:Array<Dynamic>=cast Reflect.field(registry,"groups");
   if(groups==null) groups=[];
   var sharedGroup:Dynamic=null;
   for(group in groups) if(Reflect.field(group,"name")=="shared-group") sharedGroup=group;
   if(sharedGroup==null) {
    sharedGroup={name:"shared-group",title:"Shared group",songs:[]};
    groups.push(sharedGroup);
   }
   var sharedSongs:Array<Dynamic>=cast Reflect.field(sharedGroup,"songs");
   if(sharedSongs==null) sharedSongs=[];
   var ownerSong:Dynamic=null;
   for(song in sharedSongs) if(Reflect.field(song,"name")==Std.string(spec.ownerKey)) ownerSong=song;
   if(ownerSong==null) sharedSongs.push({name:Std.string(spec.ownerKey),version:version});
   else Reflect.setField(ownerSong,"version",version);
   Reflect.setField(sharedGroup,"songs",sharedSongs);
   Reflect.setField(registry,"groups",groups);
   ImportFile.saveContent(REGISTRY,Json.stringify(registry));

   for(song in songNames) {
    ImportFile.saveContent("assets/data/"+song+"/"+song+".json",
     Json.stringify({song:song,version:version,marker:spec.marker}));
    if(compatDependencyRoot!="") {
     var selected="assets/imported_mods/"+CompatScriptManifest.namespaceFor(source,"Psych Engine");
     ImportFile.saveContent("assets/data/"+song+"/"+CompatScriptManifest.FILE_NAME,
      Json.stringify({version:1,selectedRoot:selected,roots:[
       {engine:"Psych Engine",path:selected},
       {engine:"Psych Engine",path:compatDependencyRoot,dependency:true}
      ]}));
    }
    ImportFile.saveContent("assets/songs/"+song+"/Inst.ogg",version+":"+Std.string(spec.marker));
   }
   if(mutateRegistryAfterWrite) {
    var livePath=Path.join([Sys.getCwd(),REGISTRY]);
    var live:Dynamic=Json.parse(File.getContent(livePath));
    Reflect.setField(live,"concurrentEdit","keep during conversion");
    var liveOwners:Dynamic=Reflect.field(live,"owners");
    Reflect.setField(liveOwners,"concurrent-owner","keep concurrent owner");
    Reflect.setField(live,"owners",liveOwners);
    var liveGroups:Array<Dynamic>=cast Reflect.field(live,"groups");
    var liveSongs:Array<Dynamic>=cast Reflect.field(liveGroups[0],"songs");
    liveSongs.push({name:"concurrent-song",version:"keep nested owner row"});
    Reflect.setField(liveGroups[0],"songs",liveSongs);
    Reflect.setField(live,"groups",liveGroups);
    File.saveContent(livePath,Json.stringify(live));
   }
   if(mutateOwnedRegistryAfterWrite) {
    var livePath=Path.join([Sys.getCwd(),REGISTRY]);
    var live:Dynamic=Json.parse(File.getContent(livePath));
    var liveOwners:Dynamic=Reflect.field(live,"owners");
    Reflect.setField(liveOwners,Std.string(spec.ownerKey),"concurrent manual edit");
    Reflect.setField(live,"owners",liveOwners);
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
  // The app finishes the receipt/recovery inspection from a browsing state's
  // browseTick before enabling the manual import action. This focused fixture
  // starts at that same boundary so it tests import publication, not startup.
  ImportRefreshManager.checked=true;
  ImportRefreshManager.inspectionPending=false;
  ImportRefreshManager.inspectionRunning=false;
  ImportRefreshManager.unresolvedRecovery=false;
  cancelAfterWrite=false;
  var type="Psych Engine";
  var result=ImportRefreshManager.importOnce(source,type,scan(source),new Map(),
   converter(useNextSongs,failAfterWrite,cancelAfterWriteRequested),noCancel,progress);
  return result;
 }

 static function importNmvFamilyPackage(source:String):Dynamic {
  ImportRefreshManager.checked=true;
  ImportRefreshManager.inspectionPending=false;
  ImportRefreshManager.inspectionRunning=false;
  ImportRefreshManager.unresolvedRecovery=false;
  cancelAfterWrite=false;
  var game=ImportRootScanner.inspectRoot(source,ImportEngine.AUTO);
  if(game==null||game.engine!=ImportEngine.NIGHTMARE_VISION)
   throw "Fixture outer game root did not retain its actual Nightmare Vision executable proof.";
  var roots:Array<Dynamic>=[game];
  var relatives:Array<String>=[""];
  for(name in ["alpha","beta"]) {
   roots.push({root:Path.join([source,"content",name,"assets"]),
    engine:ImportEngine.NIGHTMARE_VISION,evidence:[]});
   relatives.push("content/"+name+"/assets");
  }
  ImportWorkflow.overrideRoots=roots;
  ImportWorkflow.overrideRootRelatives=relatives;
  return ImportRefreshManager.importOnce(source,ImportEngine.NIGHTMARE_VISION,
   ImportWorkflow.scanNow(source,ImportEngine.NIGHTMARE_VISION),new Map(),
   converter(false),noCancel,progress);
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
   case "candidate-metadata":
    ImportRefreshManager.checked=true;
    ImportRefreshManager.inspectionPending=false;
    var owner="assets/imported_mods/candidate-owner";
    var candidate:ImportRefreshPendingSong={key:"pending:stable",name:"source-id",ownerRoot:owner,
     sourceRoot:"C:/donor/mod",sourceFolder:"songs",destinationFolder:"old-folder"};
    ImportRefreshManager.setReservationCandidates("candidate", "", [owner], [candidate]);
    var first=ImportRefreshManager.availabilitySnapshot();
    candidate.destinationFolder="new-folder";
    ImportRefreshManager.setReservationCandidates("candidate", "", [owner], [candidate]);
    var second=ImportRefreshManager.availabilitySnapshot();
    second.pendingSongs[0].destinationFolder="caller-mutated";
    var third=ImportRefreshManager.availabilitySnapshot();
    report({firstRevision:first.revision,secondRevision:second.revision,
     key:second.pendingSongs[0].key,destination:third.pendingSongs[0].destinationFolder});
   case "inspection-stage":
    ImportRefreshManager.checked=true;
    ImportRefreshManager.inspectionPending=true;
    ImportRefreshManager.inspectionRunning=true;
    ImportRefreshManager.active=true;
    ImportRefreshManager.unresolvedRecovery=false;
    ImportRefreshManager.committedOwnerRoots=new Map();
    var staged=["assets/imported_mods/staged-owner"];
    var during=ImportRefreshManager.availabilitySnapshot();
    ImportRefreshManager.finishQueueInspection(staged,true);
    var after=ImportRefreshManager.availabilitySnapshot();
    ImportRefreshManager.inspectionPending=true;
    ImportRefreshManager.inspectionRunning=true;
    ImportRefreshManager.active=true;
    ImportRefreshManager.unresolvedRecovery=false;
    ImportRefreshManager.committedOwnerRoots=new Map();
    ImportRefreshManager.mutex.acquire();
    ImportRefreshManager.bumpAvailabilityLocked();
    ImportRefreshManager.mutex.release();
    var failedDuring=ImportRefreshManager.availabilitySnapshot();
    ImportRefreshManager.finishQueueInspection(["assets/imported_mods/partial-owner"],false);
    var failedAfter=ImportRefreshManager.availabilitySnapshot();
    report({during:during.committedOwnerRoots,duringInspection:during.inspectionPending,
     after:after.committedOwnerRoots,afterInspection:after.inspectionPending,
     failedDuring:failedDuring.committedOwnerRoots,failedAfter:failedAfter.committedOwnerRoots,
     unresolvedAfterFailure:failedAfter.inspectionPending});
   case "handoff-cycle":
    ImportRefreshManager.checked=true;
    ImportRefreshManager.active=false;
    ImportRefreshManager.queue=[];
    ImportRefreshManager.reservations=new Map();
    ImportRefreshManager.pendingHandoffs=[];
    ImportRefreshManager.handoffInProgress=new Map();
    ImportRefreshManager.committedOwnerRoots=new Map();
    var ownerA="assets/imported_mods/cycle-a";
    var ownerB="assets/imported_mods/cycle-b";
    ImportRefreshManager.mutex.acquire();
    var reservationA=ImportRefreshManager.reserveLocked("cycle-a", "", [ownerA], null, false);
    var reservationB=ImportRefreshManager.reserveLocked("cycle-b", "", [ownerB], null, false);
    ImportRefreshManager.setReservationCommittedRootsLocked(reservationA,[ownerA]);
    ImportRefreshManager.setReservationCommittedRootsLocked(reservationB,[ownerB]);
    ImportRefreshManager.setReservationDependenciesLocked(reservationA,[ownerB]);
    ImportRefreshManager.setReservationDependenciesLocked(reservationB,[ownerA]);
    ImportRefreshManager.queueHandoffLocked("cycle-a",["song-a"]);
    ImportRefreshManager.queueHandoffLocked("cycle-b",["song-b"]);
    ImportRefreshManager.mutex.release();
    var first=ImportRefreshManager.tryHandoff("cycle-a");
    var second=ImportRefreshManager.tryHandoff("cycle-b");
    var snapshot=ImportRefreshManager.availabilitySnapshot();
    report({first:first,second:second,generation:ImportRefreshManager.generation,
     pending:snapshot.pendingOwnerRoots,committed:snapshot.committedOwnerRoots});
   case "fresh":
    var source=args[2];
    var result=importPackage(source,false);
    report({failed:result.failed, importedSongs:result.importedSongs,
     records:ImportRefreshManager.cachedRecords(install)});
   case "fresh-nmv-family":
    var source=args[2];
    var initial=importNmvFamilyPackage(source);
    if(initial.failed>0) throw "NMV family fixture initial import failed.";
    var record=findRecord(Std.string(ImportRefreshManager.cachedRecords(install)[0].id));
    var initialCatalog=Reflect.field(record,"packageFamilyCatalog");
    var initialRoots=ModuleFunctions.publishedFamilyRoots.copy();
    var initialNamespaces=ModuleFunctions.publishedFamilyNamespaces.copy();
    if(initialCatalog==null||Reflect.field(initialCatalog,"version")!=2)
     throw "Real retained generate route did not publish an authenticated v2 family catalog.";
    Reflect.setField(record,"packageFamilyCatalog",null);
    for(root in (cast Reflect.field(record,"roots"):Array<Dynamic>)) {
     var relative=Std.string(Reflect.field(root,"relative"));
     if(relative=="content/alpha/assets") Reflect.setField(root,"namespace","changed-alpha-assets");
     if(relative=="content/beta/assets") Reflect.setField(root,"namespace","changed-beta-assets");
    }
    var refreshed=ImportRefreshManager.refreshNow(install,record,converter(true),noCancel,progress);
    if(refreshed.failed>0) throw "NMV family fixture retained refresh failed.";
    var refreshedCatalog=Reflect.field(record,"packageFamilyCatalog");
    report({initialRoots:initialRoots,initialNamespaces:initialNamespaces,
     initialCatalog:initialCatalog,refreshedRoots:ModuleFunctions.publishedFamilyRoots,
     refreshedNamespaces:ModuleFunctions.publishedFamilyNamespaces,
     refreshedCatalog:refreshedCatalog,records:ImportRefreshManager.cachedRecords(install)});
   case "fresh-compat-dependency":
    compatDependencyRoot=args[3];
    var result=importPackage(args[2],false);
    report({failed:result.failed, importedSongs:result.importedSongs,
     records:ImportRefreshManager.cachedRecords(install)});
   case "fresh-availability":
    ImportRefreshManager.checked=true;
    var source=args[2];
    var result=importPackage(source,false);
    var before=ImportRefreshManager.availabilitySnapshot();
    var beforeView={revision:before.revision,pending:before.pendingOwnerRoots,
     handoff:before.handoffPendingOwnerRoots,committed:before.committedOwnerRoots,
     touched:before.pendingTouchedPaths,songs:before.pendingSongs};
    var status=ImportRefreshManager.browseTick();
    var after=ImportRefreshManager.availabilitySnapshot();
    var accepted=ImportRefreshManager.completeInitialImportHandoff(result.importedSongs);
    var done=ImportRefreshManager.availabilitySnapshot();
    report({failed:result.failed,before:beforeView,status:status,accepted:accepted,
     afterPending:after.pendingOwnerRoots,donePending:done.pendingOwnerRoots,
     doneCommitted:done.committedOwnerRoots,generation:ImportRefreshManager.generation,
     handoffCalls:ModuleFunctions.handoffCalls,records:ImportRefreshManager.cachedRecords(install)});
   case "fresh-diagnostic":
    ImportWorkflow.missing=[{missing:[{kind:"character",reference:"unshipped-character",found:false,
     searched:["characters/unshipped-character.json"]}]}];
    var result=importPackage(args[2],false);
    report({failed:result.failed, records:ImportRefreshManager.cachedRecords(install)});
   case "multi-fresh":
    var first=importPackage(args[2],false);
    var second=importPackage(args[3],false);
    report({failed:first.failed+second.failed, records:ImportRefreshManager.cachedRecords(install)});
   case "refresh", "refresh-fail", "refresh-cancel", "refresh-concurrent-registry",
    "refresh-concurrent-owned", "refresh-scan-errors":
    var id=args[2];
    var record=findRecord(id);
    if(mode=="refresh-scan-errors") ImportWorkflow.scanErrors=["fixture: chart could not be parsed"];
    // This also verifies that the persisted manifest and its receipt/journal
    // still agree after the Python fixture marks its revision stale.
    var owner="retained-import:"+id;
    var manifest=ImportRefreshTransaction.loadManifest(Path.join([install,"import-cache/state"]),owner);
    cancelAfterWrite=false;
    try {
     ImportRefreshManager.checked=true;
     var result=ImportRefreshManager.refreshNow(install,record,
      converter(true,mode=="refresh-fail",mode=="refresh-cancel",mode=="refresh-concurrent-registry",
       mode=="refresh-concurrent-owned"),noCancel,progress);
     var snapshot=ImportRefreshManager.availabilitySnapshot();
     report({status:"ok",failed:result.failed, importedSongs:result.importedSongs,
      pending:snapshot.pendingOwnerRoots,handoff:snapshot.handoffPendingOwnerRoots,
      committed:snapshot.committedOwnerRoots,files:manifest.files.length,
      records:ImportRefreshManager.cachedRecords(install)});
    } catch(error:Dynamic) {
     ImportRefreshManager.checked=true;
     var snapshot=ImportRefreshManager.availabilitySnapshot();
     report({status:"error",error:Std.string(error),files:manifest.files.length,
      pending:snapshot.pendingOwnerRoots,handoff:snapshot.handoffPendingOwnerRoots,
      committed:snapshot.committedOwnerRoots,records:ImportRefreshManager.cachedRecords(install)});
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
   ImportRefreshManager.inspectionPending=false;
   ImportRefreshManager.inspectionRunning=false;
   ImportRefreshManager.active=false;
   ImportRefreshManager.queue=[];
   ImportRefreshManager.reservations=new Map();
   ImportRefreshManager.pendingHandoffs=[];
   ImportRefreshManager.handoffInProgress=new Map();
   ImportRefreshManager.committedOwnerRoots=new Map();
   ImportRefreshManager.availabilityEpoch=1;
   ImportRefreshManager.availabilityCache=null;
    ImportRefreshManager.status={busy:false,label:"",fraction:0.0,complete:false,changed:false,blocked:false};
    var deadline=Sys.time()+20;
    var status:Dynamic=null;
    while(Sys.time()<deadline) {
     status=ImportRefreshManager.browseTick();
     if(status.complete&& !status.busy) break;
     if(status.blocked&& !status.busy) break;
     Sys.sleep(0.005);
    }
    var availability=ImportRefreshManager.availabilitySnapshot();
    report({status:status, generation:ImportRefreshManager.generation,
     availability:availability,records:ImportRefreshManager.cachedRecords(install)});
   case "auto-refresh-sequence", "auto-refresh-in-game", "auto-refresh-in-smoke", "auto-refresh-dependency":
    ImportRefreshManager.checked=false;
    ImportRefreshManager.inspectionPending=false;
    ImportRefreshManager.inspectionRunning=false;
    ImportRefreshManager.active=false;
    ImportRefreshManager.queue=[];
    ImportRefreshManager.reservations=new Map();
    ImportRefreshManager.pendingHandoffs=[];
    ImportRefreshManager.handoffInProgress=new Map();
    ImportRefreshManager.committedOwnerRoots=new Map();
    ImportRefreshManager.availabilityEpoch=1;
    ImportRefreshManager.availabilityCache=null;
    ImportRefreshManager.status={busy:false,label:"",fraction:0.0,complete:false,changed:false,blocked:false};
    delayOwner=(mode=="auto-refresh-sequence"||mode=="auto-refresh-dependency")?args[2]:"";
    delayMillis=(mode=="auto-refresh-sequence"||mode=="auto-refresh-dependency")?1200:0;
    if(mode=="auto-refresh-in-game"||mode=="auto-refresh-in-smoke") FlxG.state=new PlayState();
    var deadline=Sys.time()+20;
    var split:Dynamic=null;
    var status:Dynamic=null;
    while(Sys.time()<deadline) {
     status=ImportRefreshManager.browseTick();
     var view=ImportRefreshManager.availabilitySnapshot();
     if(mode=="auto-refresh-sequence"&&ImportRefreshManager.generation>=1&&ImportRefreshManager.active) {
      if(split==null) split={pending:view.pendingOwnerRoots,handoff:view.handoffPendingOwnerRoots,
       committed:view.committedOwnerRoots,revision:view.revision};
     }
     if(mode=="auto-refresh-dependency"&&ImportRefreshManager.active
      &&StringTools.startsWith(status.label,"Refreshing import:")) {
      split={pending:view.pendingOwnerRoots,handoff:view.handoffPendingOwnerRoots,
       committed:view.committedOwnerRoots,revision:view.revision};
      break;
     }
     if((mode=="auto-refresh-in-game"||mode=="auto-refresh-in-smoke")&&!ImportRefreshManager.active
      &&ImportRefreshManager.pendingHandoffs.length>0) {
      split={pending:view.pendingOwnerRoots,handoff:view.handoffPendingOwnerRoots,
       generation:ImportRefreshManager.generation};
      break;
     }
     if(status.complete&&!status.busy&&ImportRefreshManager.pendingHandoffs.length==0
      &&ImportRefreshManager.queue.length==0) break;
     Sys.sleep(0.005);
    }
    if(mode=="auto-refresh-in-game"&&split!=null) {
     FlxG.state=null;
     status=ImportRefreshManager.browseTick();
    }
    if(mode=="auto-refresh-in-smoke"&&split!=null) {
     FlxG.state=new RuntimeImportSmokeState();
     status=ImportRefreshManager.browseTick();
    }
    report({status:status,generation:ImportRefreshManager.generation,split:split,
     pending:ImportRefreshManager.availabilitySnapshot().pendingOwnerRoots,
     handoffCalls:ModuleFunctions.handoffCalls,records:ImportRefreshManager.cachedRecords(install)});
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
            target = self.fixture_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline='\n')
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

    def make_nmv_family_source(self) -> Path:
        source = self.scratch / "native-nmv-family"
        source.mkdir()
        (source / "package.json").write_text(json.dumps({
            "ownerKey": "native-nmv-family", "marker": "retained:native-nmv-family",
            "initialVersion": "v1-native-nmv-family", "nextVersion": "v2-native-nmv-family",
            "initialSongs": ["base-song"], "nextSongs": ["base-song", "base-song-new"],
        }), encoding="utf-8", newline='\n')
        (source / "NightmareVision.exe").write_bytes(b"MZ\x00com.nmvTeam.nightmareEngine\x00")
        base_data = source / "assets/data/base-song"
        base_audio = source / "assets/songs/base-song"
        base_data.mkdir(parents=True)
        base_audio.mkdir(parents=True)
        (base_data / "base-song.json").write_text(
            '{"song":{"song":"base-song","format":"nmv2","notes":[]}}',
            encoding="utf-8", newline='\n')
        (base_audio / "Inst.ogg").write_bytes(b"OggS-native-base")
        for name in ("alpha", "beta"):
            package = source / "content" / name
            assets = package / "assets/scripts/states"
            assets.mkdir(parents=True)
            (package / "meta.json").write_text(
                json.dumps({"name": name}), encoding="utf-8", newline='\n')
            (assets / "FixtureState.hx").write_text(
                "class FixtureState {}", encoding="utf-8", newline='\n')
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

    def test_same_candidate_key_refreshes_destination_metadata_and_snapshots_are_copies(self):
        result = self.run_fixture("candidate-metadata")
        self.assertGreater(result["secondRevision"], result["firstRevision"])
        self.assertEqual(result["key"], "pending:stable")
        self.assertEqual(result["destination"], "new-folder")

    def test_startup_withholds_staged_receipt_owners_until_full_inspection(self):
        result = self.run_fixture("inspection-stage")
        self.assertEqual(result["during"], [])
        self.assertTrue(result["duringInspection"])
        self.assertEqual(result["after"], ["assets/imported_mods/staged-owner"])
        self.assertFalse(result["afterInspection"])
        self.assertEqual(result["failedDuring"], [])
        self.assertEqual(result["failedAfter"], [])
        self.assertTrue(result["unresolvedAfterFailure"])

    def test_committed_cyclic_dependencies_drain_handoffs_without_deadlock(self):
        result = self.run_fixture("handoff-cycle")
        self.assertTrue(result["first"] and result["second"], result)
        self.assertEqual(result["generation"], 2, result)
        self.assertEqual(result["pending"], [], result)
        self.assertEqual(result["committed"], sorted([
            "assets/imported_mods/cycle-a", "assets/imported_mods/cycle-b"]))

    def mark_record_stale(self, record: dict, common_revision: int | None = 0,
                          runtime_dependency_owners=None,
                          legacy_runtime_dependencies: bool = False) -> None:
        owner = "retained-import:" + record["id"]
        owner_hash = hashlib.sha256(owner.encode()).hexdigest()
        scope = self.install / "import-cache/state" / owner_hash
        manifest_path = scope / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if common_revision is not None:
            manifest["revision"]["importRecord"]["revisions"][0]["commonRevision"] = common_revision
        if runtime_dependency_owners is not None:
            manifest["revision"]["importRecord"]["runtimeDependencyOwners"] = runtime_dependency_owners
        if legacy_runtime_dependencies:
            manifest["revision"]["importRecord"].pop("runtimeDependencyOwners", None)
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
        matching = [record for record in report["records"] if record["label"] == source.name]
        self.assertEqual(len(matching), 1)
        return matching[0]

    def test_refresh_after_donor_removal_uses_retained_source_and_publishes_new_song(self):
        donor = self.make_source("donor-a", initial_songs=["alpha"], next_songs=["alpha", "beta"])
        record = self.initial_import(donor)
        self.assertEqual((self.install / "assets/songs/alpha/Inst.ogg").read_text(), "v1-donor-a:retained:donor-a")
        shutil_rmtree(donor)
        self.mark_record_stale(record, common_revision=2)

        refreshed = self.run_fixture("refresh", record["id"])

        self.assertEqual(refreshed["status"], "ok", refreshed)
        self.assertEqual((self.install / "assets/songs/alpha/Inst.ogg").read_text(), "v2-donor-a:retained:donor-a")
        self.assertEqual((self.install / "assets/songs/beta/Inst.ogg").read_text(), "v2-donor-a:retained:donor-a")
        self.assertTrue((self.install / "assets/data/beta/beta.json").is_file())
        self.assertTrue(any(stamp["commonRevision"] == 3 for stamp in refreshed["records"][0]["revisions"]))
        self.assertFalse(donor.exists())

    def test_regenerate_uses_snapshot_root_for_package_family_catalog_apis(self):
        manager = (SOURCE / "ImportRefreshManager.hx").read_text(encoding="utf-8")
        self.assertIn(
            "ImportPackageFamilyCatalog.reusableNamespaces(install, previous, Path.directory(source), record)",
            manager)
        self.assertIn(
            "ImportPackageFamilyCatalog.sourceRoots(Path.directory(source), record)", manager)
        self.assertIn(
            "ImportPackageFamilyCatalog.capturePublished(Path.directory(source), record, io)", manager)

        source = self.make_nmv_family_source()
        result = self.run_fixture("fresh-nmv-family", source)

        self.assertEqual([Path(root).name for root in result["initialRoots"]], ["alpha", "beta"])
        initial = result["initialCatalog"]
        self.assertEqual(initial["version"], 2)
        self.assertEqual(initial["containerRelative"], "content")
        self.assertEqual([member["sourceRelative"] for member in initial["members"]],
                         ["content/alpha", "content/beta"])
        initial_namespaces = [member["namespace"] for member in initial["members"]]
        self.assertEqual(initial_namespaces, ["family-alpha", "family-beta"])
        self.assertEqual(result["initialNamespaces"], initial_namespaces)
        # The fixture removes the record's in-memory catalog and changes its
        # scanned assets namespaces before refresh. The only way these original
        # names survive is for reusableNamespaces to validate the snapshot root,
        # read its receipt, and reuse the committed v2 package mapping.
        self.assertEqual(result["refreshedNamespaces"], initial_namespaces)
        self.assertEqual([member["sourceRelative"] for member in result["refreshedCatalog"]["members"]],
                         ["content/alpha", "content/beta"])

    @unittest.skipIf(os.name == 'nt', 'Windows eval worker can stall under parallel probes; covered by native Windows refresh test')
    def test_stale_persisted_record_is_automatically_queued_on_browse_tick(self):
        donor = self.make_source("donor-auto", initial_songs=["auto-song"], next_songs=["auto-song", "auto-new"])
        record = self.initial_import(donor)
        shutil_rmtree(donor)
        self.mark_record_stale(record, common_revision=2)

        result = self.run_fixture("auto-refresh")

        self.assertFalse(result["status"]["busy"], result)
        self.assertTrue(result["status"]["complete"], result)
        self.assertFalse(result["status"]["blocked"], result)
        self.assertTrue(result["status"]["changed"], result)
        self.assertEqual(result["generation"], 1)
        self.assertTrue((self.install / "assets/songs/auto-new/Inst.ogg").is_file())
        self.assertFalse(donor.exists())

    def test_initial_import_exposes_provisional_owner_until_manager_handoff(self):
        donor = self.make_source("donor-availability", initial_songs=["visible-later"])
        result = self.run_fixture("fresh-availability", donor)
        owner = "assets/imported_mods/" + result["records"][0]["roots"][0]["namespace"]

        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["before"]["pending"], [owner])
        self.assertEqual(result["before"]["handoff"], [owner])
        self.assertEqual(result["before"]["committed"], [owner])
        self.assertEqual(result["before"]["songs"][0]["name"], "visible-later")
        self.assertEqual(result["before"]["songs"][0]["sourceFolder"], "visible-later")
        self.assertEqual(result["before"]["songs"][0]["destinationFolder"], "visible-later")
        self.assertTrue(result["before"]["songs"][0]["key"].startswith("pending:"))
        self.assertIn("assets/data/visible-later/visible-later.json", result["before"]["touched"])
        self.assertEqual(result["afterPending"], [])
        self.assertEqual(result["donePending"], [])
        self.assertEqual(result["doneCommitted"], [owner])
        self.assertTrue(result["accepted"])
        self.assertEqual(result["handoffCalls"], 1, "poll bridge must not repeat a manager-owned handoff")
        self.assertEqual(result["generation"], 1)

    def test_refresh_failure_and_cancel_release_reservations_after_recovery(self):
        for mode in ("refresh-fail", "refresh-cancel"):
            with self.subTest(mode=mode):
                stable_song = "stable-" + mode
                donor = self.make_source("donor-recover-" + mode,
                    initial_songs=[stable_song], next_songs=[stable_song, "new-" + mode])
                record = self.initial_import(donor)
                shutil_rmtree(donor)
                self.mark_record_stale(record, common_revision=2)

                result = self.run_fixture(mode, record["id"])

                owner = "assets/imported_mods/" + record["roots"][0]["namespace"]
                self.assertEqual(result["status"], "error")
                self.assertEqual(result["pending"], [])
                self.assertEqual(result["handoff"], [])
                self.assertEqual(result["committed"], [owner])
                self.assertEqual((self.install / "assets/songs" / stable_song / "Inst.ogg").read_text(),
                    "v1-donor-recover-" + mode + ":retained:donor-recover-" + mode)

    def test_completed_owner_handoff_runs_while_next_refresh_is_active(self):
        if os.name == "nt":
            from test_import_windows_native_filesystem import run_native_handoff_overlap_case

            run_native_handoff_overlap_case()
            return

        first_source = self.make_source("donor-queue-a", initial_songs=["queue-a"],
            next_songs=["queue-a", "queue-a-new"])
        second_source = self.make_source("donor-queue-b", initial_songs=["queue-b"],
            next_songs=["queue-b", "queue-b-new"])
        first_record = self.initial_import(first_source)
        second_record = self.initial_import(second_source)
        ordered = sorted([first_record, second_record], key=lambda record: record["id"])
        self.mark_record_stale(ordered[0], common_revision=2)
        self.mark_record_stale(ordered[1], common_revision=2)

        result = self.run_fixture("auto-refresh-sequence", ordered[1]["label"])

        first_owner = "assets/imported_mods/" + ordered[0]["roots"][0]["namespace"]
        second_owner = "assets/imported_mods/" + ordered[1]["roots"][0]["namespace"]
        self.assertEqual(result["split"]["pending"], [second_owner], result)
        self.assertEqual(result["split"]["handoff"], [], result)
        self.assertEqual(result["split"]["committed"], sorted([first_owner, second_owner]))
        self.assertEqual(result["pending"], [])
        self.assertEqual(result["generation"], 2)
        self.assertEqual(result["handoffCalls"], 2)
        self.assertTrue((self.install / "assets/songs/queue-a-new/Inst.ogg").is_file())
        self.assertTrue((self.install / "assets/songs/queue-b-new/Inst.ogg").is_file())

    def test_handoff_waits_until_gameplay_has_left_playstate(self):
        donor = self.make_source("donor-in-game", initial_songs=["game-song"],
            next_songs=["game-song", "game-new"])
        record = self.initial_import(donor)
        shutil_rmtree(donor)
        self.mark_record_stale(record, common_revision=2)

        result = self.run_fixture("auto-refresh-in-game")

        owner = "assets/imported_mods/" + record["roots"][0]["namespace"]
        self.assertEqual(result["split"]["pending"], [owner])
        self.assertEqual(result["split"]["handoff"], [owner])
        self.assertEqual(result["split"]["generation"], 0)
        self.assertEqual(result["pending"], [])
        self.assertEqual(result["generation"], 1)
        self.assertEqual(result["handoffCalls"], 1)

    def test_import_smoke_preparation_state_can_complete_deferred_handoff(self):
        donor = self.make_source("donor-smoke-handoff", initial_songs=["smoke-song"],
            next_songs=["smoke-song", "smoke-new"])
        record = self.initial_import(donor)
        shutil_rmtree(donor)
        self.mark_record_stale(record, common_revision=2)

        result = self.run_fixture("auto-refresh-in-smoke")

        owner = "assets/imported_mods/" + record["roots"][0]["namespace"]
        self.assertEqual(result["split"]["pending"], [owner])
        self.assertEqual(result["split"]["handoff"], [owner])
        self.assertEqual(result["split"]["generation"], 0)
        self.assertEqual(result["pending"], [])
        self.assertEqual(result["generation"], 1)
        self.assertEqual(result["handoffCalls"], 1)

    def test_cold_start_reserves_dependent_owners_before_queued_refresh_starts(self):
        source_a = self.make_source("donor-dependency-a", initial_songs=["dependency-a"],
            next_songs=["dependency-a", "dependency-a-new"])
        source_b = self.make_source("donor-dependency-b", initial_songs=["dependency-b"],
            next_songs=["dependency-b", "dependency-b-new"])
        imported = self.run_fixture("multi-fresh", source_a, source_b)
        by_label = {record["label"]: record for record in imported["records"]}
        provider = by_label[source_a.name]
        dependent = by_label[source_b.name]
        provider_root = "assets/imported_mods/" + provider["roots"][0]["namespace"]
        dependent_root = "assets/imported_mods/" + dependent["roots"][0]["namespace"]
        ordered = sorted([provider, dependent], key=lambda record: record["id"])
        self.mark_record_stale(provider, common_revision=2)
        self.mark_record_stale(dependent, common_revision=2, runtime_dependency_owners=[provider_root])

        result = self.run_fixture("auto-refresh-dependency", ordered[0]["label"])

        self.assertIsNotNone(result["split"], result)
        self.assertEqual(result["split"]["pending"], sorted([provider_root, dependent_root]), result)
        self.assertEqual(result["split"]["handoff"], [], result)
        self.assertEqual(result["split"]["committed"], sorted([provider_root, dependent_root]))

    def test_legacy_receipt_reads_only_receipt_verified_compat_dependency_metadata(self):
        provider_source = self.make_source("donor-legacy-provider", initial_songs=["legacy-provider"],
            next_songs=["legacy-provider", "legacy-provider-new"])
        dependent_source = self.make_source("donor-legacy-dependent", initial_songs=["legacy-dependent"])
        provider = self.initial_import(provider_source)
        provider_root = "assets/imported_mods/" + provider["roots"][0]["namespace"]
        dependent_report = self.run_fixture("fresh-compat-dependency", dependent_source, provider_root)
        dependent = next(record for record in dependent_report["records"]
            if record["label"] == dependent_source.name)
        dependent_root = "assets/imported_mods/" + dependent["roots"][0]["namespace"]
        sidecar = self.install / "assets/data/legacy-dependent/compatScripts.json"
        self.assertTrue(sidecar.is_file())
        self.mark_record_stale(provider, common_revision=2)
        self.mark_record_stale(dependent, common_revision=None, legacy_runtime_dependencies=True)

        result = self.run_fixture("auto-refresh-dependency", provider["label"])

        self.assertIsNotNone(result["split"], result)
        self.assertEqual(result["split"]["pending"], sorted([provider_root, dependent_root]), result)
        self.assertEqual(result["split"]["handoff"], [], result)
        self.assertEqual(result["split"]["committed"], sorted([provider_root, dependent_root]))

    def test_receiptless_recovery_reserves_only_exact_journal_owner_paths(self):
        source_a = self.make_source("donor-recovery-unknown", initial_songs=["unknown-recovery"])
        source_b = self.make_source("donor-recovery-known", initial_songs=["known-ready"])
        imported = self.run_fixture("multi-fresh", source_a, source_b)
        by_label = {record["label"]: record for record in imported["records"]}
        unknown = by_label[source_a.name]
        known = by_label[source_b.name]
        unknown_root = "assets/imported_mods/" + unknown["roots"][0]["namespace"]
        known_root = "assets/imported_mods/" + known["roots"][0]["namespace"]

        owner = "retained-import:" + unknown["id"]
        scope = self.install / "import-cache/state" / hashlib.sha256(owner.encode()).hexdigest()
        (scope / "manifest.json").unlink()
        transaction_id = "txn-recovery-unknown"
        transaction = scope / "transactions" / transaction_id
        transaction.mkdir()
        target_relative = unknown_root + "/recovery-pending.hscript"
        target = self.install / target_relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"local bytes changed after interruption")
        journal = {
            "schemaVersion": 1,
            "owner": owner,
            "transactionId": transaction_id,
            "installRoot": str(self.install),
            "ownedRoots": ["assets"],
            "phase": "publishing",
            "journalSequence": 1,
            "operations": [{
                "path": target_relative,
                "target": str(target),
                "beforeExists": False,
                "beforeSha256": "",
                "afterExists": True,
                "afterSha256": hashlib.sha256(b"expected published bytes").hexdigest(),
                "stagedPath": "",
                "backupPath": "",
            }],
            "manifestBeforeExists": False,
            "manifestBeforeSha256": "",
            "manifestAfterSha256": "0" * 64,
            "manifestBackupPath": "",
        }
        (transaction / "journal-00000001.json").write_text(json.dumps(journal) + "\n", encoding="utf-8")

        result = self.run_fixture("auto-refresh")

        self.assertFalse(result["availability"]["inspectionPending"], result)
        self.assertEqual(result["availability"]["pendingOwnerRoots"], [unknown_root], result)
        self.assertIn(target_relative, result["availability"]["pendingTouchedPaths"])
        self.assertEqual(result["availability"]["committedOwnerRoots"], [known_root], result)
        self.assertTrue(target.exists(), "recovery conflict must preserve the changed installed bytes")

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
        self.assertEqual(registry["owners"]["concurrent-owner"], "keep concurrent owner")
        group = next(group for group in registry["groups"] if group["name"] == "shared-group")
        self.assertIn({"name": "concurrent-song", "version": "keep nested owner row"}, group["songs"])
        self.assertTrue((self.install / "assets/songs/new/Inst.ogg").is_file())

    def test_already_regenerated_registry_value_is_accepted_and_other_owners_survive(self):
        donor = self.make_source("donor-registry-already-fresh", initial_songs=["stable"], next_songs=["stable", "new"])
        record = self.initial_import(donor)
        shutil_rmtree(donor)
        self.mark_record_stale(record)

        registry_path = self.install / REGISTRY
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        # The source label output is already at the exact value this conversion
        # will produce, even though the retained manifest still records v1.
        registry["owners"]["donor-registry-already-fresh"] = "v2-donor-registry-already-fresh"
        registry["owners"]["other-owner"] = "v1-other-owner"
        registry["labels"]["other-owner"] = "stable-other-owner"
        registry["base"]["display"] = "local display edit"
        registry["localSetting"] = {"keep": True}
        registry_path.write_text(json.dumps(registry), encoding="utf-8", newline='\n')

        result = self.run_fixture("refresh", record["id"])

        self.assertEqual(result["status"], "ok", result)
        refreshed = json.loads(registry_path.read_text(encoding="utf-8"))
        self.assertEqual(refreshed["owners"]["donor-registry-already-fresh"], "v2-donor-registry-already-fresh")
        self.assertEqual(refreshed["owners"]["other-owner"], "v1-other-owner")
        self.assertEqual(refreshed["labels"]["other-owner"], "stable-other-owner")
        self.assertEqual(refreshed["base"]["display"], "local display edit")
        self.assertEqual(refreshed["localSetting"], {"keep": True})
        self.assertTrue((self.install / "assets/songs/new/Inst.ogg").is_file())

    def test_divergent_changed_registry_value_rejects_refresh_and_keeps_live_edit(self):
        donor = self.make_source("donor-registry-diverged", initial_songs=["stable"], next_songs=["stable", "new"])
        record = self.initial_import(donor)
        shutil_rmtree(donor)
        self.mark_record_stale(record)

        registry_path = self.install / REGISTRY
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["owners"]["donor-registry-diverged"] = "manual edit"
        registry_path.write_text(json.dumps(registry), encoding="utf-8", newline='\n')
        before_registry = registry_path.read_bytes()
        before_manifest = self.manifest_bytes(record)

        result = self.run_fixture("refresh", record["id"])

        self.assertEqual(result["status"], "error", result)
        self.assertIn("registry", result["error"].lower())
        self.assertEqual(registry_path.read_bytes(), before_registry)
        self.assertEqual(self.manifest_bytes(record), before_manifest)
        self.assertFalse((self.install / "assets/songs/new/Inst.ogg").exists())

    def test_divergent_unchanged_generated_registry_value_rejects_refresh(self):
        donor = self.make_source("donor-registry-unchanged-edit", initial_songs=["stable"], next_songs=["stable", "new"])
        record = self.initial_import(donor)
        shutil_rmtree(donor)
        self.mark_record_stale(record)

        registry_path = self.install / REGISTRY
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        # labels.<owner> is generated identically by both conversions. Generic
        # merge treats it as unchanged, so final owner validation must catch it.
        registry["labels"]["donor-registry-unchanged-edit"] = "manual stable-label edit"
        registry_path.write_text(json.dumps(registry), encoding="utf-8", newline='\n')
        before_registry = registry_path.read_bytes()
        before_manifest = self.manifest_bytes(record)

        result = self.run_fixture("refresh", record["id"])

        self.assertEqual(result["status"], "error", result)
        self.assertIn("local registry edits preserved", result["error"].lower())
        self.assertEqual(registry_path.read_bytes(), before_registry)
        self.assertEqual(self.manifest_bytes(record), before_manifest)
        self.assertFalse((self.install / "assets/songs/new/Inst.ogg").exists())

    def test_concurrent_owned_registry_edit_is_preserved_and_blocks_refresh(self):
        donor = self.make_source("donor-concurrent-owned", initial_songs=["stable"], next_songs=["stable", "new"])
        record = self.initial_import(donor)
        shutil_rmtree(donor)
        self.mark_record_stale(record)

        registry_path = self.install / REGISTRY
        before_manifest = self.manifest_bytes(record)

        result = self.run_fixture("refresh-concurrent-owned", record["id"])

        self.assertEqual(result["status"], "error", result)
        self.assertIn("registry", result["error"].lower())
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        self.assertEqual(registry["owners"]["donor-concurrent-owned"], "concurrent manual edit")
        self.assertEqual(self.manifest_bytes(record), before_manifest)
        self.assertFalse((self.install / "assets/songs/new/Inst.ogg").exists())

    def test_regenerated_refresh_preserves_unrelated_owner_added_during_conversion(self):
        donor = self.make_source("donor-regenerated-concurrent-row", initial_songs=["stable"], next_songs=["stable", "new"])
        record = self.initial_import(donor)
        shutil_rmtree(donor)
        self.mark_record_stale(record)

        registry_path = self.install / REGISTRY
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        # Force the seed fallback with the already-regenerated owned value.
        registry["owners"]["donor-regenerated-concurrent-row"] = "v2-donor-regenerated-concurrent-row"
        registry_path.write_text(json.dumps(registry), encoding="utf-8", newline='\n')

        result = self.run_fixture("refresh-concurrent-registry", record["id"])

        self.assertEqual(result["status"], "ok", result)
        refreshed = json.loads(registry_path.read_text(encoding="utf-8"))
        self.assertEqual(refreshed["owners"]["donor-regenerated-concurrent-row"],
                         "v2-donor-regenerated-concurrent-row")
        self.assertEqual(refreshed["owners"]["concurrent-owner"], "keep concurrent owner")
        self.assertEqual(refreshed["concurrentEdit"], "keep during conversion")
        group = next(group for group in refreshed["groups"] if group["name"] == "shared-group")
        self.assertIn({"name": "concurrent-song", "version": "keep nested owner row"}, group["songs"])
        self.assertTrue((self.install / "assets/songs/new/Inst.ogg").is_file())

    def test_regenerated_refresh_does_not_claim_or_later_remove_foreign_nested_row(self):
        donor = self.make_source("donor-nested-owner-row", initial_songs=["stable"], next_songs=["stable", "new"])
        record = self.initial_import(donor)
        shutil_rmtree(donor)
        self.mark_record_stale(record)

        registry_path = self.install / REGISTRY
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["owners"]["donor-nested-owner-row"] = "v2-donor-nested-owner-row"
        group = next(group for group in registry["groups"] if group["name"] == "shared-group")
        group["songs"].append({"name": "foreign-song", "version": "foreign owner"})
        registry_path.write_text(json.dumps(registry), encoding="utf-8", newline='\n')

        first = self.run_fixture("refresh", record["id"])

        self.assertEqual(first["status"], "ok", first)
        first_registry = json.loads(registry_path.read_text(encoding="utf-8"))
        first_group = next(group for group in first_registry["groups"] if group["name"] == "shared-group")
        self.assertIn({"name": "foreign-song", "version": "foreign owner"}, first_group["songs"])

        refreshed_record = first["records"][0]
        self.mark_record_stale(refreshed_record)
        second = self.run_fixture("refresh", refreshed_record["id"])

        self.assertEqual(second["status"], "ok", second)
        second_registry = json.loads(registry_path.read_text(encoding="utf-8"))
        second_group = next(group for group in second_registry["groups"] if group["name"] == "shared-group")
        self.assertIn({"name": "foreign-song", "version": "foreign owner"}, second_group["songs"])

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
