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
    "CategoryState.hx": r'''class CategoryState { public var categorySongs:Array<Array<String>>=[]; public function new() {} }''',
    "FreeplayState.hx": r'''class FreeplayState { public function new() {} }''',
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
 public static inline var ROOT_PREFIX:String="assets/imported_mods";
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
import ImportRefreshManager.ImportSourceBuildContext;
import PsychLanguagePublisher.PsychLanguagePublicationPlan;
import SourceMappedAssetPublisher.SourceMappedAssetPlan;
import SourceMappedMediaPublisher;
import ModuleFunctions.SongImportBatchResult;
import ImportRefreshAvailabilitySnapshot.ImportRefreshPendingSong;
import sys.FileSystem;
import sys.io.File;
import sys.thread.Lock;
import sys.thread.Thread;

@:access(ImportRefreshManager)
class ImportRefreshManagerFixture {
 static inline var REGISTRY:String="assets/data/freeplaySongJson.json";
 static var cancelAfterWrite:Bool=false;
 static var delayOwner:String="";
 static var delayMillis:Int=0;
 static var registryPauseSignal:Lock=null;
 static var registryPauseContinue:Lock=null;
 static var registryPauseAnnounced:Bool=false;
 static var compatDependencyRoot:String="";
 static var lastLanguagePlan:PsychLanguagePublicationPlan=null;
 static var lastLanguageProfile:Dynamic=null;
 static var languageCopyCalls:Int=0;
 static var lastLanguagePlans:Array<PsychLanguagePublicationPlan>=[];
 static var lastLanguageProfiles:Array<Dynamic>=[];
 static var lastMappedPlans:Array<SourceMappedAssetPlan>=[];
 static var mappedCopyCalls:Int=0;
 static var mappedLegacySkips:Array<Bool>=[];

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
   ImportFile.saveContent(REGISTRY,UnicodeSafeJson.stringify(registry));

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
    File.saveContent(livePath,UnicodeSafeJson.stringify(live));
   }
   if(mutateOwnedRegistryAfterWrite) {
    var livePath=Path.join([Sys.getCwd(),REGISTRY]);
    var live:Dynamic=Json.parse(File.getContent(livePath));
    var liveOwners:Dynamic=Reflect.field(live,"owners");
    Reflect.setField(liveOwners,Std.string(spec.ownerKey),"concurrent manual edit");
    Reflect.setField(live,"owners",liveOwners);
    File.saveContent(livePath,UnicodeSafeJson.stringify(live));
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

 static function languagePlanSummary():Dynamic {
  var plan=lastLanguagePlan;
  if(plan==null) return null;
 return {profileBound:plan.profileBound,authoritative:plan.authoritative,
   legacyAllowed:plan.legacyAllowed,blockAllLegacy:plan.blockAllLegacy,
   failed:plan.failed,cancelled:plan.cancelled,
   copyCalls:languageCopyCalls,
   files:[for(file in plan.files) {sourceRelative:file.sourceRelative,
    ownerRelative:file.ownerRelative,destinationPath:file.destinationPath}],
   diagnostics:plan.diagnostics};
 }

 static function languagePlanSummaries():Array<Dynamic> return [for(plan in lastLanguagePlans) {
  profileBound:plan.profileBound,authoritative:plan.authoritative,failed:plan.failed,
  cancelled:plan.cancelled,files:[for(file in plan.files) {sourceRelative:file.sourceRelative,
   ownerRelative:file.ownerRelative,destinationPath:file.destinationPath}],diagnostics:plan.diagnostics
 }];

 static function mappedPlanSummaries():Array<Dynamic> return [for(plan in lastMappedPlans) {
  profileBound:plan.profileBound,authoritative:plan.authoritative,failed:plan.failed,
  cancelled:plan.cancelled,files:[for(file in plan.files) {sourceRelative:file.sourceRelative,
   ownerRelative:file.ownerRelative,destinationPath:file.destinationPath,
   policyLabels:file.policyLabels}],diagnostics:plan.diagnostics
 }];

 static function mappedBuildContext(root:String, complete:Bool=true,
  flags:Array<Dynamic>=null):ImportSourceBuildContext {
 var selectedFlags=flags==null?[]:flags.copy();
  var build:Dynamic={target:"manager-mapped-assets-fixture",flags:selectedFlags,
   flagsComplete:complete};
  if(complete) Reflect.setField(build,"command","");
  return {sourceRoot:root,engine:"Psych Engine",build:cast build};
 }

 static function selectMappedRoots(source:String, nested:Bool):Array<ImportSourceBuildContext> {
  if(nested) {
   selectTwoLanguageRoots();
   return [mappedBuildContext(source),mappedBuildContext(Path.join([source,"nested"]))];
  }
  ImportWorkflow.overrideRoots=null;
  ImportWorkflow.overrideRootRelatives=null;
  return [mappedBuildContext(source)];
 }

 static function mappedAssetConverter(cancelAfterCopies:Int=0):
  (String,ImportScanResult,Map<String,String>)->SongImportBatchResult {
  return function(source:String,scanned:ImportScanResult,names:Map<String,String>):SongImportBatchResult {
   var result=converter(false)(source,scanned,names);
   lastMappedPlans=[];
   mappedLegacySkips=[];
   mappedCopyCalls=0;
   var io=ImportIO.current();
   if(io==null||scanned==null||scanned.detectedRoots==null)
    throw "mapped asset conversion did not receive its manager ImportIO scope and selected roots";
   for(root in scanned.detectedRoots) {
    var rootPath=Std.string(Reflect.field(root,"root"));
    var engine=Std.string(Reflect.field(root,"engine"));
    var binding=io.assetProfile(rootPath,engine);
    if(binding==null) throw "manager did not bind the exact retained mapped-asset profile";
    var profile:Dynamic=binding.profile;
    if(Reflect.field(profile,"provenance")!="receipt-bound"
      ||Reflect.field(profile,"namespace")!=io.namespace(rootPath,engine)
      ||Reflect.field(profile,"snapshotId")==null)
     throw "mapped-asset profile lost its receipt/root/namespace identity";
    var namespace=io.namespace(rootPath,engine);
    var owner="assets/imported_mods/"+namespace;
    var plan=SourceMappedMediaPublisher.prepare(rootPath,engine,owner,null,noCancel);
    lastMappedPlans.push(plan);
    if(plan.failed||plan.cancelled) {
     result.failed++;
     if(plan.diagnostics!=null) result.errors=result.errors.concat(plan.diagnostics);
     if(result.errors.length==0) result.errors.push("Combined mapped-asset planning failed.");
     return result;
    }
    var languageView=SourceMappedMediaPublisher.languageView(plan);
    var mediaView=SourceMappedAssetPublisher.policyView(plan,
     SourceMappedMediaPublisher.mediaLabel(engine,null));
    var mediaPolicy=SourceMappedMediaPublisher.mediaPolicy(engine,null);
    var testSource=Path.join([rootPath,"assets","media","icon.png"]);
    var globalSkip=SourceMappedMediaPublisher.skipLegacyGlobal(rootPath,engine,owner,
     mediaPolicy,mediaView,testSource,"assets/images/icon.png");
    mappedLegacySkips.push(globalSkip);
    SourceMappedMediaPublisher.publish(plan,function(sourcePath:String,destinationPath:String):Void {
     ImportFile.copy(sourcePath,destinationPath);
     mappedCopyCalls++;
     if(cancelAfterCopies>0&&mappedCopyCalls>=cancelAfterCopies) cancelAfterWrite=true;
    },noCancel,function(path:String,content:String):Void {
     if(!ImportGeneratedOutput.write(path,content,true)) throw "new identity sidecar unexpectedly existed";
     if(ImportGeneratedOutput.write(path,content,true)) throw "identical sidecar was rewritten";
     var conflict=false;
     try ImportGeneratedOutput.write(path,content+"changed",true) catch(_:Dynamic) conflict=true;
     if(!conflict||ImportFile.getContent(path)!=content) throw "sidecar conflict was not preserved";
    });
    if(plan.cancelled||noCancel()) {
     result.failed++;
     result.errors.push("Combined mapped-asset publication was cancelled.");
     return result;
    }
    // Keep the view and helper behavior attached to the manager-bound plan in
    // the report so disabled/deferred legacy suppression is observable.
    if(languageView==null||mediaView==null)
     throw "combined mapped-asset policy views were unavailable";
   }
   return result;
  };
 }

 static function mappedImport(source:String,nested:Bool=false,cancelAfterCopies:Int=0,
  contextMode:String="complete"):SongImportBatchResult {
  ImportRefreshManager.checked=true;
  ImportRefreshManager.inspectionPending=false;
  ImportRefreshManager.inspectionRunning=false;
  ImportRefreshManager.unresolvedRecovery=false;
  cancelAfterWrite=false;
  var contexts=selectMappedRoots(source,nested);
  if(contextMode=="partial") {
   contexts=[for(context in contexts) mappedBuildContext(context.sourceRoot,false)];
  } else if(contextMode=="disabled") {
   var disabledFlags:Array<Dynamic>=[{name:"DISABLED_MEDIA",state:"disabled",provenance:"caller-supplied"}];
   contexts=[for(context in contexts) mappedBuildContext(context.sourceRoot,true,disabledFlags)];
  } else if(contextMode=="enabled") {
   var enabledFlags:Array<Dynamic>=[{name:"DISABLED_MEDIA",state:"enabled",provenance:"caller-supplied"}];
   contexts=[for(context in contexts) mappedBuildContext(context.sourceRoot,true,enabledFlags)];
  }
  return ImportRefreshManager.importOnce(source,"Psych Engine",scan(source),new Map(),
   mappedAssetConverter(cancelAfterCopies),noCancel,progress,contexts);
 }

 static function mappedRefresh(id:String,nested:Bool=false,cancelAfterCopies:Int=0):Dynamic {
  cancelAfterWrite=false;
  lastMappedPlans=[];
  mappedCopyCalls=0;
  if(nested) selectTwoLanguageRoots();
  else {ImportWorkflow.overrideRoots=null;ImportWorkflow.overrideRootRelatives=null;}
  var record=findRecord(id);
  try {
   var result=ImportRefreshManager.refreshNow(Sys.getCwd(),record,
    mappedAssetConverter(cancelAfterCopies),noCancel,progress);
   return {status:"ok",failed:result.failed,plans:mappedPlanSummaries(),
    legacySkips:mappedLegacySkips,
    records:ImportRefreshManager.cachedRecords(Sys.getCwd())};
  } catch(error:Dynamic) return {status:"error",error:Std.string(error),
   plans:mappedPlanSummaries(),legacySkips:mappedLegacySkips,
   records:ImportRefreshManager.cachedRecords(Sys.getCwd())};
 }

 static function languageBuildContext(source:String, complete:Bool=true):ImportSourceBuildContext {
  var build:Dynamic={target:"explicit-language-fixture 🌙",flags:[{name:"EXPLICIT_BUILD_CONTEXT",
   state:"enabled",provenance:"caller-supplied"}]};
  if(complete) {
   Reflect.setField(build,"flagsComplete",true);
   Reflect.setField(build,"command","");
  }
  return {sourceRoot:source,engine:"Psych Engine",build:cast build};
 }

 static function selectTwoLanguageRoots():Void {
  ImportWorkflow.overrideRoots=[{engine:"Psych Engine",evidence:[]},{engine:"Psych Engine",evidence:[]}];
  ImportWorkflow.overrideRootRelatives=["","nested"];
 }

 static function valuesForLanguageRoot(source:String, nested:Bool):ImportSourceBuildContext {
  var build:Dynamic={target:nested?"secondary-language-target":"primary-language-target",
   flags:[{name:"TRANSLATIONS_ALLOWED",state:"enabled",provenance:"caller-supplied"}],
   values:nested?[
    {name:"SOURCE_AREA",value:"alternate-translations",provenance:"caller-supplied"},
    {name:"TARGET_AREA",value:"alt-languages",provenance:"caller-supplied"},
    {name:"BUILD_NOTE",value:" secondary source 🌙 ",provenance:"caller-supplied"},
    {name:"LITERAL_FALSE_VALUE",value:"false",provenance:"caller-supplied"}
   ]:[
    {name:"SOURCE_AREA",value:"translations",provenance:"caller-supplied"},
    {name:"TARGET_AREA",value:"languages",provenance:"caller-supplied"},
    {name:"BUILD_NOTE",value:" primary source 🌙 ",provenance:"caller-supplied"},
    {name:"LITERAL_FALSE_VALUE",value:"false",provenance:"caller-supplied"}
   ]};
  if(!nested) {
   Reflect.setField(build,"flagsComplete",true);
   Reflect.setField(build,"command","");
  }
  return {sourceRoot:nested?Path.join([source,"nested"]):source,
   engine:"Psych Engine",build:cast build};
 }

 static function assertValueProfile(sourceRoot:String, expectedRelative:String,
  expectedSource:String, expectedTarget:String):Dynamic {
  var io=ImportIO.current();
  var binding=io==null?null:io.assetProfile(sourceRoot,"Psych Engine");
  if(binding==null) throw "manager did not bind a receipt profile for each selected root";
  var profile:Dynamic=binding.profile;
  var relative=Std.string(Reflect.field(profile,"rootRelative"));
  var namespace=Std.string(Reflect.field(profile,"namespace"));
  if(relative!=expectedRelative||namespace!=io.namespace(sourceRoot,"Psych Engine")
    ||Reflect.field(profile,"provenance")!="receipt-bound")
   throw "per-root profile identity did not match the manager-selected source root";
  var candidates:Array<Dynamic>=cast Reflect.field(profile,"candidates");
  var mapped:Dynamic=null;
  var absentCondition:Dynamic=null;
  var falseValue:Dynamic=null;
  if(candidates!=null) for(candidate in candidates) {
   var source=Std.string(Reflect.field(candidate,"sourceRelative"));
   if(source=="assets/"+expectedSource+"/data") mapped=candidate;
   else if(source=="assets/optional-translations") absentCondition=candidate;
   else if(source=="assets/false-value-assets") falseValue=candidate;
  }
  if(mapped==null||Reflect.field(mapped,"targetRelative")!="assets/"+expectedTarget+"/data")
   throw "literal or chained values did not produce the included Project mapping";
  var expectedComplete=expectedRelative=="";
  if(Reflect.field(profile,"flagsComplete")!=expectedComplete
    ||absentCondition==null||Reflect.field(absentCondition,"state")!=(expectedComplete?"disabled":"unresolved")
    ||falseValue==null||Reflect.field(falseValue,"state")!="enabled")
   throw "complete flag inventory, unknown flags, or literal false value semantics changed";
  var profileValues:Array<Dynamic>=cast Reflect.field(profile,"values");
  var buildNote:Dynamic=null;
  var literalFalse:Dynamic=null;
  if(profileValues!=null) for(value in profileValues) {
   if(Reflect.field(value,"name")=="BUILD_NOTE") buildNote=Reflect.field(value,"value");
   if(Reflect.field(value,"name")=="LITERAL_FALSE_VALUE") literalFalse=Reflect.field(value,"value");
  }
  var expectedNote=expectedRelative==""?" primary source 🌙 ":" secondary source 🌙 ";
  if(buildNote!=expectedNote||literalFalse!="false")
   throw "explicit build values lost their exact text before profile resolution";
  var inputs:Array<Dynamic>=cast Reflect.field(profile,"inputFiles");
  var includePath=(expectedRelative==""?"":"nested/")+"project/includes/language-assets.xml";
  var includeFound=false;
  if(inputs!=null) for(input in inputs)
   if(Reflect.field(input,"path")==includePath&&Reflect.field(input,"size")>0
    &&Std.string(Reflect.field(input,"sha256")).length==64) includeFound=true;
  if(!includeFound) throw "local Project include was not bound to the verified snapshot receipt";
  var fingerprint=Std.string(Reflect.field(profile,"contextFingerprint"));
  if(fingerprint=="") throw "explicit values were not bound to a profile context fingerprint";
  var buildTarget=Reflect.field(profile,"buildTarget");
  return {snapshotId:Reflect.field(profile,"snapshotId"),rootRelative:relative,namespace:namespace,
   engine:Reflect.field(profile,"sourceEngine"),sourceRelative:Reflect.field(mapped,"sourceRelative"),
   targetRelative:Reflect.field(mapped,"targetRelative"),inputFiles:inputs,
   contextFingerprint:fingerprint,buildTarget:buildTarget,flagsComplete:expectedComplete,
   buildCommand:Reflect.field(profile,"buildCommand"),
   buildNote:buildNote,literalFalseValue:literalFalse,
   absentCondition:Reflect.field(absentCondition,"state"),falseValueCondition:Reflect.field(falseValue,"state")};
 }

 static function languageValuesConverter():(String,ImportScanResult,Map<String,String>)->SongImportBatchResult {
  return function(source:String,scan:ImportScanResult,names:Map<String,String>):SongImportBatchResult {
   var result=converter(false)(source,scan,names);
   lastLanguagePlan=null;
   lastLanguageProfile=null;
   lastLanguagePlans=[];
   lastLanguageProfiles=[];
   languageCopyCalls=0;
   var io=ImportIO.current();
   if(io==null||scan==null||scan.detectedRoots==null)
    throw "receipt-bound multi-root language conversion did not receive its manager scan";
   for(root in scan.detectedRoots) {
    var rootPath=Std.string(Reflect.field(root,"root"));
    var engine=Std.string(Reflect.field(root,"engine"));
    var binding=io.assetProfile(rootPath,engine);
    if(binding==null) throw "a selected language root had no profile binding";
    var profile:Dynamic=binding.profile;
    var relative=Std.string(Reflect.field(profile,"rootRelative"));
    var sourceArea=relative==""?"translations":"alternate-translations";
    var targetArea=relative==""?"languages":"alt-languages";
    lastLanguageProfiles.push(assertValueProfile(rootPath,relative,sourceArea,targetArea));
    var namespace=io.namespace(rootPath,engine);
    var plan=PsychLanguagePublisher.prepare(rootPath,engine,"assets/imported_mods/"+namespace,noCancel);
    lastLanguagePlans.push(plan);
    lastLanguagePlan=plan;
    if(plan.failed||plan.cancelled) {
     var errors=plan.diagnostics==null?[]:plan.diagnostics.copy();
     if(errors.length==0) errors.push("Receipt-bound language planning did not complete.");
     return {found:result.found,imported:result.imported,importedSongs:result.importedSongs,
      skipped:result.skipped,failed:1,copiedAssets:result.copiedAssets,
      skippedAssets:result.skippedAssets,errors:errors};
    }
    PsychLanguagePublisher.publish(plan,function(sourcePath:String,destinationPath:String):Void {
     ImportFile.copy(sourcePath,destinationPath);
     languageCopyCalls++;
    },noCancel);
    if(plan.cancelled) {
     result.failed=1;
     result.errors.push("Receipt-bound language publication was cancelled.");
     return result;
    }
   }
   lastLanguageProfile=lastLanguageProfiles.length==0?null:lastLanguageProfiles[0];
   return result;
  };
 }

 static function importLanguageValues(source:String):SongImportBatchResult {
  ImportRefreshManager.checked=true;
  ImportRefreshManager.inspectionPending=false;
  ImportRefreshManager.inspectionRunning=false;
  ImportRefreshManager.unresolvedRecovery=false;
  cancelAfterWrite=false;
  selectTwoLanguageRoots();
  return ImportRefreshManager.importOnce(source,"Psych Engine",scan(source),new Map(),
   languageValuesConverter(),noCancel,progress,[
    valuesForLanguageRoot(source,false),valuesForLanguageRoot(source,true)]);
 }

 static function refreshLanguageValues(id:String):Dynamic {
  cancelAfterWrite=false;
  lastLanguagePlans=[];
  lastLanguageProfiles=[];
  lastLanguagePlan=null;
  lastLanguageProfile=null;
  languageCopyCalls=0;
  selectTwoLanguageRoots();
  var record=findRecord(id);
  try {
   var result=ImportRefreshManager.refreshNow(Sys.getCwd(),record,
    languageValuesConverter(),noCancel,progress);
   return {status:"ok",failed:result.failed,plans:languagePlanSummaries(),
    profiles:lastLanguageProfiles,records:ImportRefreshManager.cachedRecords(Sys.getCwd())};
  } catch(error:Dynamic) return {status:"error",error:Std.string(error),
   plans:languagePlanSummaries(),profiles:lastLanguageProfiles,
   records:ImportRefreshManager.cachedRecords(Sys.getCwd())};
 }

 static function languageConverter(cancelAfterCopies:Int=0, expectedFlagsComplete:Bool=true):((String,ImportScanResult,
  Map<String,String>)->SongImportBatchResult) {
  return function(source:String,scan:ImportScanResult,names:Map<String,String>):SongImportBatchResult {
   var result=converter(false)(source,scan,names);
   lastLanguagePlan=null;
   lastLanguageProfile=assertCurrentSourceProfile(source,expectedFlagsComplete);
   languageCopyCalls=0;
   var io=ImportIO.current();
   var namespace=io==null?null:io.namespace(source,"Psych Engine");
   if(namespace==null||namespace=="") throw "manager did not bind the selected language owner namespace";
   lastLanguagePlan=PsychLanguagePublisher.prepare(source,"Psych Engine",
    "assets/imported_mods/"+namespace,noCancel);
   if(lastLanguagePlan.failed||lastLanguagePlan.cancelled) {
    var errors=lastLanguagePlan.diagnostics==null?[]:lastLanguagePlan.diagnostics.copy();
    if(errors.length==0) errors.push("Receipt-bound language planning did not complete.");
    return {found:result.found,imported:result.imported,importedSongs:result.importedSongs,
     skipped:result.skipped,failed:1,copiedAssets:result.copiedAssets,
     skippedAssets:result.skippedAssets,errors:errors};
   }
   PsychLanguagePublisher.publish(lastLanguagePlan,function(sourcePath:String,destinationPath:String):Void {
    ImportFile.copy(sourcePath,destinationPath);
    languageCopyCalls++;
    if(cancelAfterCopies>0&&languageCopyCalls>=cancelAfterCopies) cancelAfterWrite=true;
   },noCancel);
   if(lastLanguagePlan.cancelled) {
    result.failed=1;
    result.errors.push("Receipt-bound language publication was cancelled.");
   }
   return result;
  };
 }

 static function importLanguage(source:String,cancelAfterCopies:Int=0,
  completeBuildContext:Bool=true):SongImportBatchResult {
  ImportRefreshManager.checked=true;
  ImportRefreshManager.inspectionPending=false;
  ImportRefreshManager.inspectionRunning=false;
  ImportRefreshManager.unresolvedRecovery=false;
  cancelAfterWrite=false;
  return ImportRefreshManager.importOnce(source,"Psych Engine",scan(source),new Map(),
   languageConverter(cancelAfterCopies,completeBuildContext),noCancel,progress,
   [languageBuildContext(source,completeBuildContext)]);
 }

 static function importLegacyLanguageWithoutProject(source:String):Dynamic {
  ImportRefreshManager.checked=true;
  ImportRefreshManager.inspectionPending=false;
  ImportRefreshManager.inspectionRunning=false;
  ImportRefreshManager.unresolvedRecovery=false;
  lastLanguagePlan=null;
  lastLanguageProfile=null;
  cancelAfterWrite=false;
  var legacyConverter=function(retained:String,scanned:ImportScanResult,
   names:Map<String,String>):SongImportBatchResult {
   var result=converter(false)(retained,scanned,names);
   var io=ImportIO.current();
   if(io==null) throw "legacy language fixture has no import scope";
   var namespace=io.namespace(retained,"Psych Engine");
   if(namespace==null||namespace=="") throw "legacy language fixture has no selected owner namespace";
   var destinationRoot="assets/imported_mods/"+namespace;
   lastLanguagePlan=PsychLanguagePublisher.prepare(retained,"Psych Engine",destinationRoot,noCancel);
   if(lastLanguagePlan.profileBound||!lastLanguagePlan.legacyAllowed
    ||lastLanguagePlan.blockAllLegacy||lastLanguagePlan.failed)
    throw "An absent Project.xml did not leave the existing language collector enabled.";
   var sourcePath=Path.join([retained,"assets","data","languages","en-US.lang"]);
   var destination=Path.join([destinationRoot,"data","languages","en-US.lang"]);
   if(PsychLanguagePublisher.skipLegacy(lastLanguagePlan,sourcePath,destination))
    throw "An absent Project.xml unexpectedly suppressed an ordinary legacy language file.";
   ImportFile.copy(sourcePath,destination);
   return result;
  };
  var result=ImportRefreshManager.importOnce(source,"Psych Engine",scan(source),new Map(),
   legacyConverter,noCancel,progress);
  return {status:"ok",failed:result.failed,plan:languagePlanSummary(),
   records:ImportRefreshManager.cachedRecords(Sys.getCwd())};
 }

 static function refreshLanguage(id:String,cancelAfterCopies:Int=0):Dynamic {
  cancelAfterWrite=false;
  lastLanguagePlan=null;
  lastLanguageProfile=null;
  languageCopyCalls=0;
  var record=findRecord(id);
  try {
   var result=ImportRefreshManager.refreshNow(Sys.getCwd(),record,
    languageConverter(cancelAfterCopies),noCancel,progress);
   return {status:"ok",failed:result.failed,plan:languagePlanSummary(),
    profile:lastLanguageProfile,records:ImportRefreshManager.cachedRecords(Sys.getCwd())};
  } catch(error:Dynamic) return {status:"error",error:Std.string(error),
   plan:languagePlanSummary(),profile:lastLanguageProfile,
   records:ImportRefreshManager.cachedRecords(Sys.getCwd())};
 }

 static function progress(value:Dynamic):Void {
  if(registryPauseSignal!=null&&!registryPauseAnnounced
    &&Reflect.field(value,"phase")=="reconciling-import-registries") {
   registryPauseAnnounced=true;
   registryPauseSignal.release();
   registryPauseContinue.wait();
  }
 }
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

 static function assertCurrentSourceProfile(source:String, expectedFlagsComplete:Bool=true):Dynamic {
  var io=ImportIO.current();
  if(io==null) throw "retained profile converter did not have an ImportIO scope";
  var binding=io.assetProfile(source,"Psych Engine");
  if(binding==null) throw "verified source profile was not bound before conversion";
  var profile:Dynamic=binding.profile;
  var snapshot=Std.string(Reflect.field(profile,"snapshotId"));
  var rootRelative=Std.string(Reflect.field(profile,"rootRelative"));
 var engine=Std.string(Reflect.field(profile,"sourceEngine"));
 var namespace=Std.string(Reflect.field(profile,"namespace"));
 if(binding.contentRoot!=source||snapshot==""||rootRelative!=""||engine!="Psych Engine"
   ||namespace!=io.namespace(source,engine)||Reflect.field(profile,"provenance")!="receipt-bound"
   ||Reflect.field(profile,"flagsComplete")!=expectedFlagsComplete)
  throw "bound profile did not retain the selected root provenance";
  var flags:Array<Dynamic>=cast Reflect.field(profile,"flags");
  var explicitFound=false;
  if(flags!=null) for(flag in flags)
   if(Reflect.field(flag,"name")=="EXPLICIT_BUILD_CONTEXT"
    &&Reflect.field(flag,"state")=="enabled"
    &&Reflect.field(flag,"provenance")=="caller-supplied") explicitFound=true;
  if(!explicitFound) throw "explicit source build flag did not reach the resolver";
  return {snapshotId:snapshot,rootRelative:rootRelative,engine:engine,namespace:namespace,
   contentRoot:binding.contentRoot,provenance:Reflect.field(profile,"provenance"),
   buildTarget:Reflect.field(profile,"buildTarget"),flags:flags,
   flagsComplete:Reflect.field(profile,"flagsComplete"),
   buildCommand:Reflect.field(profile,"buildCommand")};
 }

 static function assertCurrentSourceProfileWithoutExplicitContext(source:String):Dynamic {
  var io=ImportIO.current();
  var binding=io==null?null:io.assetProfile(source,"Psych Engine");
  if(binding==null) throw "recaptured source did not receive a freshly resolved profile";
  var profile:Dynamic=binding.profile;
  if(Reflect.field(profile,"flagsComplete")!=false)
   throw "recaptured source unexpectedly retained complete build flags";
  var flags:Array<Dynamic>=cast Reflect.field(profile,"flags");
  if(flags!=null) for(flag in flags)
   if(Reflect.field(flag,"name")=="EXPLICIT_BUILD_CONTEXT")
    throw "build context from an older snapshot was rebound to a changed source";
  return {snapshotId:Reflect.field(profile,"snapshotId"),provenance:Reflect.field(profile,"provenance"),
   flagsComplete:Reflect.field(profile,"flagsComplete"),
   buildCommand:Reflect.field(profile,"buildCommand")};
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

 static function report(value:Dynamic):Void Sys.println(UnicodeSafeJson.stringifyStandard(value));

 static function main():Void {
  var args=Sys.args();
  var mode=args[0];
  var install=args[1];
  Sys.setCwd(install);
  switch(mode) {
   case "cleanup-scheduler":
    ImportWorkScheduler.bindForegroundThread();
    var stage=Path.join([install,"import-cache","staging","cleanup-checkpoint"]);
    FileSystem.createDirectory(stage);
    for(index in 0...64)
     File.saveContent(Path.join([stage,"file-"+index+".tmp"]),"staged-"+index);
    var gameplay=ImportWorkScheduler.beginGameplay();
    var started=new Lock();
    var finished=new Lock();
    var workerFailure:Dynamic=null;
    Thread.create(function() {
     started.release();
     try ImportRefreshManager.deleteStage(stage) catch(error:Dynamic) workerFailure=error;
     finished.release();
    });
    if(!started.wait(2)) throw "staging cleanup worker did not start";
    Sys.sleep(0.08);
    var completedWhileGameplay=finished.wait(0.01);
    var treePreserved=FileSystem.exists(stage)&&FileSystem.readDirectory(stage).length==64;
    var foregroundStage=Path.join([install,"import-cache","staging","foreground-cleanup"]);
    FileSystem.createDirectory(foregroundStage);
    File.saveContent(Path.join([foregroundStage,"foreground.tmp"]),"foreground");
    ImportRefreshManager.deleteStage(foregroundStage);
    var foregroundRemoved=!FileSystem.exists(foregroundStage);
    ImportWorkScheduler.endGameplay(gameplay);
    var completed=completedWhileGameplay||finished.wait(2);
    if(!completed) throw "staging cleanup did not resume after gameplay";
    if(workerFailure!=null) throw "staging cleanup failed: "+Std.string(workerFailure);
    report({completedWhileGameplay:completedWhileGameplay,treePreserved:treePreserved,
     foregroundRemoved:foregroundRemoved,removed:!FileSystem.exists(stage)});
   case "inspection-scheduler":
    ImportWorkScheduler.bindForegroundThread();
    var imported=importPackage(args[2],false);
    if(imported.failed>0) throw "inspection fixture import failed";
    ImportRefreshManager.checked=false;
    ImportRefreshManager.inspectionPending=false;
    ImportRefreshManager.inspectionRunning=false;
    ImportRefreshManager.active=false;
    ImportRefreshManager.queue=[];
    var gameplay=ImportWorkScheduler.beginGameplay();
    ImportRefreshManager.ensureQueueInspection();
    Sys.sleep(0.08);
    var paused=ImportRefreshManager.inspectionRunning&&ImportRefreshManager.active;
    var foregroundProgress=ImportWorkScheduler.cooperate();
    ImportWorkScheduler.endGameplay(gameplay);
    var deadline=haxe.Timer.stamp()+5;
    while(ImportRefreshManager.inspectionRunning&&haxe.Timer.stamp()<deadline) Sys.sleep(0.01);
    var snapshot=ImportRefreshManager.availabilitySnapshot();
    report({paused:paused,foregroundProgress:foregroundProgress,
     resumed:!ImportRefreshManager.inspectionRunning,
     committedRoots:snapshot.committedOwnerRoots});
   case "registry-scheduler":
    ImportWorkScheduler.bindForegroundThread();
    var record=findRecord(args[2]);
    var registryPath=Path.join([install,REGISTRY]);
    var registryBefore=File.getContent(registryPath);
    var signal=new Lock();
    var resumeProgress=new Lock();
    var started=new Lock();
    var finished=new Lock();
    var workerResult:SongImportBatchResult=null;
    var workerFailure:Dynamic=null;
    registryPauseSignal=signal;
    registryPauseContinue=resumeProgress;
    registryPauseAnnounced=false;
    Thread.create(function() {
     started.release();
     try workerResult=ImportRefreshManager.refreshNow(install,record,
      converter(true),noCancel,progress)
     catch(error:Dynamic) workerFailure=error;
     finished.release();
    });
    if(!started.wait(2)) throw "registry refresh worker did not start";
    if(!signal.wait(10)) throw "refresh did not reach registry reconciliation";
    var gameplay=ImportWorkScheduler.beginGameplay();
    resumeProgress.release();
    Sys.sleep(0.08);
    var completedWhileGameplay=finished.wait(0.01);
    var registryUnchangedWhilePaused=File.getContent(registryPath)==registryBefore;
    var foregroundProgress=ImportWorkScheduler.cooperate();
    ImportWorkScheduler.endGameplay(gameplay);
    var completed=completedWhileGameplay||finished.wait(10);
    registryPauseSignal=null;
    registryPauseContinue=null;
    if(!completed) throw "registry refresh did not resume after gameplay";
    if(workerFailure!=null) throw "registry refresh failed: "+Std.string(workerFailure);
    var registry:Dynamic=Json.parse(File.getContent(registryPath));
    var ownerVersion=Reflect.field(Reflect.field(registry,"owners"),Std.string(record.label));
    report({status:workerResult==null?"error":"ok",paused:!completedWhileGameplay,
     registryUnchangedWhilePaused:registryUnchangedWhilePaused,
     foregroundProgress:foregroundProgress,resumed:completed,
     ownerVersion:ownerVersion});
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
    ImportRefreshManager.mutex.acquire();
    ImportRefreshManager.scopedUnavailableOwnersByToken.set("refresh:prior",["assets/imported_mods/prior-owner"]);
    ImportRefreshManager.bumpAvailabilityLocked();
    ImportRefreshManager.mutex.release();
    var failedDuring=ImportRefreshManager.availabilitySnapshot();
    ImportRefreshManager.finishQueueInspection(["assets/imported_mods/partial-owner"],false);
    var failedAfter=ImportRefreshManager.availabilitySnapshot();
    report({during:during.committedOwnerRoots,duringInspection:during.inspectionPending,
     after:after.committedOwnerRoots,afterInspection:after.inspectionPending,
     failedDuring:failedDuring.committedOwnerRoots,failedAfter:failedAfter.committedOwnerRoots,
     unresolvedAfterFailure:failedAfter.inspectionPending,
     priorScopeAfterFailure:ImportRefreshManager.scopedUnavailableOwnersByToken.exists("refresh:prior")});
   case "scoped-recheck":
    ImportRefreshManager.checked=true;
    ImportRefreshManager.inspectionPending=false;
    ImportRefreshManager.inspectionRunning=false;
    ImportRefreshManager.availabilityRecheckRequested=false;
    ImportRefreshManager.active=false;
    ImportRefreshManager.unresolvedRecovery=false;
    ImportRefreshManager.scopedUnavailableOwnersByToken=new Map();
    ImportRefreshManager.scopedUnavailablePathsByToken=new Map();
    ImportRefreshManager.reservations=new Map();
    ImportRefreshManager.pendingHandoffs=[];
    ImportRefreshManager.queue=[];
    ImportRefreshManager.committedOwnerRoots=new Map();
    var blocked="assets/imported_mods/scoped-owner";
    var unrelated=args[2];
    ImportRefreshManager.mutex.acquire();
    ImportRefreshManager.scopedUnavailableOwnersByToken.set("refresh:scoped",[blocked]);
    ImportRefreshManager.scopedUnavailablePathsByToken.set("refresh:scoped",["assets/data/scoped-owner/chart.json"]);
    ImportRefreshManager.committedOwnerRoots.set(unrelated,true);
    var reservation=ImportRefreshManager.reserveLocked("refresh:scoped", "retained-import:scoped",
     [blocked], null, false);
    reservation.recoveryBlocked=true;
    ImportRefreshManager.bumpAvailabilityLocked();
    ImportRefreshManager.mutex.release();
    var before=ImportRefreshManager.availabilitySnapshot();
    var unrelatedReady=FreeplaySongAvailability.ownerReadiness(before,unrelated).ready;
    var accepted=ImportRefreshManager.requestAvailabilityRecheck();
    var startRevision=ImportRefreshManager.availabilityRevision();
    var deadline=Sys.time()+5;
    while(ImportRefreshManager.inspectionRunning&&Sys.time()<deadline) Sys.sleep(0.005);
    var after=ImportRefreshManager.availabilitySnapshot();
    var scopedAfterAuthoritative=ImportRefreshManager.scopedUnavailableOwnersByToken.keys().hasNext();
    var scopedPathsAfterAuthoritative=ImportRefreshManager.scopedUnavailablePathsByToken.keys().hasNext();
    var recordDirectory=Path.join([install,ImportRefreshManager.CACHE_ROOT,"records"]);
    if(FileSystem.exists(recordDirectory)) for(name in FileSystem.readDirectory(recordDirectory))
     if(~/^[a-f0-9]{64}\.json$/.match(name)) FileSystem.deleteFile(Path.join([recordDirectory,name]));
    ImportRefreshManager.mutex.acquire();
    ImportRefreshManager.unresolvedRecovery=true;
    ImportRefreshManager.scopedUnavailableOwnersByToken.set("refresh:empty-scan",["assets/imported_mods/empty-scan-owner"]);
    ImportRefreshManager.scopedUnavailablePathsByToken.set("refresh:empty-scan",["assets/data/empty-scan-owner/chart.json"]);
    ImportRefreshManager.bumpAvailabilityLocked();
    ImportRefreshManager.mutex.release();
    var ownerlessAccepted=ImportRefreshManager.requestAvailabilityRecheck();
    deadline=Sys.time()+5;
    while(ImportRefreshManager.inspectionRunning&&Sys.time()<deadline) Sys.sleep(0.005);
    var ownerlessAfter=ImportRefreshManager.availabilitySnapshot();
    report({accepted:accepted,unrelatedReady:unrelatedReady,beforeRevision:before.revision,
     startRevision:startRevision,afterRevision:after.revision,pendingBefore:before.pendingOwnerRoots,
     pendingAfter:after.pendingOwnerRoots,scopedAfter:scopedAfterAuthoritative,
     scopedPathsAfter:scopedPathsAfterAuthoritative,
     inspectionPending:after.inspectionPending,inspectionRunning:ImportRefreshManager.inspectionRunning,
     active:ImportRefreshManager.active,ownerlessAccepted:ownerlessAccepted,
     ownerlessInspectionPending:ownerlessAfter.inspectionPending,
     emptyScopedPreserved:ImportRefreshManager.scopedUnavailableOwnersByToken.exists("refresh:empty-scan"),
     emptyPathsPreserved:ImportRefreshManager.scopedUnavailablePathsByToken.exists("refresh:empty-scan"),
     emptyCommittedPreserved:ownerlessAfter.committedOwnerRoots.indexOf(unrelated)>=0});
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
   case "category-handoff":
    ImportRefreshManager.checked=true;
    ImportRefreshManager.inspectionPending=false;
    ImportRefreshManager.inspectionRunning=false;
    ImportRefreshManager.active=false;
    ImportRefreshManager.queue=[];
    ImportRefreshManager.reservations=new Map();
    ImportRefreshManager.pendingHandoffs=[];
    ImportRefreshManager.handoffInProgress=new Map();
    ImportRefreshManager.committedOwnerRoots=new Map();
    FlxG.state=new CategoryState();
    var categorySnapshot=["old-chart"];
    var beforeSelectionGeneration=ImportRefreshManager.generation;
    ImportRefreshManager.mutex.acquire();
    var reservation=ImportRefreshManager.reserveLocked("category-refresh", "", ["assets/imported_mods/category-owner"], null, false);
    ImportRefreshManager.setReservationCommittedRootsLocked(reservation,["assets/imported_mods/category-owner"]);
    ImportRefreshManager.queueHandoffLocked("category-refresh",["old-chart"]);
    ImportRefreshManager.mutex.release();
    var categoryStatus=ImportRefreshManager.browseTick();
    var deferred=ImportRefreshManager.generation==beforeSelectionGeneration
     &&ImportRefreshManager.pendingHandoffs.length==1;
    var selectedList=categorySnapshot.copy();
    var selectedGeneration=ImportRefreshManager.generation;
    FlxG.state=new FreeplayState();
    var freeplayStatus=ImportRefreshManager.browseTick();
    var refreshSelection=FreeplaySongAvailability.songListNeedsRegistryRefresh(false,
     selectedList.length,selectedGeneration,ImportRefreshManager.generation);
    if(refreshSelection) selectedList=[];
    if(selectedList.length==0) selectedList=["new-chart"];
    report({deferred:deferred,categoryBusy:categoryStatus.busy,
     freeplayBusy:freeplayStatus.busy,generation:ImportRefreshManager.generation,
     refreshed:refreshSelection,selected:selectedList});
   case "fresh":
    var source=args[2];
    var result=importPackage(source,false);
    report({failed:result.failed, importedSongs:result.importedSongs,
     records:ImportRefreshManager.cachedRecords(install)});
   case "fresh-language":
    var source=args[2];
    try {
     var result=importLanguage(source);
     report({status:"ok",failed:result.failed,plan:languagePlanSummary(),
      profile:lastLanguageProfile,records:ImportRefreshManager.cachedRecords(install)});
    } catch(error:Dynamic) report({status:"error",error:Std.string(error),
     plan:languagePlanSummary(),profile:lastLanguageProfile,
     records:ImportRefreshManager.cachedRecords(install)});
   case "fresh-language-values":
    var source=args[2];
    try {
     var result=importLanguageValues(source);
     report({status:"ok",failed:result.failed,plans:languagePlanSummaries(),
      profiles:lastLanguageProfiles,records:ImportRefreshManager.cachedRecords(install)});
    } catch(error:Dynamic) report({status:"error",error:Std.string(error),
     plans:languagePlanSummaries(),profiles:lastLanguageProfiles,
     records:ImportRefreshManager.cachedRecords(install)});
   case "mapped-assets-initial", "mapped-assets-enabled-initial", "mapped-assets-two-owner", "mapped-assets-cancel", "mapped-assets-binding",
    "mapped-assets-reimport", "mapped-assets-disabled-reimport", "mapped-assets-deferred-reimport":
    var source=args[2];
    var nested=mode=="mapped-assets-two-owner";
    var cancelCopies=mode=="mapped-assets-cancel"?1:0;
    var contextMode=mode=="mapped-assets-enabled-initial"?"enabled"
     :mode=="mapped-assets-disabled-reimport"?"disabled"
     :mode=="mapped-assets-deferred-reimport"?"partial":"complete";
    try {
     var result=mappedImport(source,nested,cancelCopies,contextMode);
     var bindings:Array<Dynamic>=[];
     var detached=true;
     if(mode=="mapped-assets-binding") for(record in ImportRefreshManager.cachedRecords(install))
      for(root in (cast record.roots:Array<Dynamic>)) {
       var owner="assets/imported_mods/"+Std.string(root.namespace);
       var binding=ImportRefreshManager.ownerAssetIndexBinding(owner,"Psych Engine","package");
       if(binding!=null) {
        bindings.push(binding);
        var second=ImportRefreshManager.ownerAssetIndexBinding(owner,"Psych Engine","package");
        if(second.files.length>0) second.files[0].sha256="mutated";
        var third=ImportRefreshManager.ownerAssetIndexBinding(owner,"Psych Engine","package");
        if(third.files.length>0&&third.files[0].sha256=="mutated") detached=false;
       }
      }
     report({status:"ok",failed:result.failed,errors:result.errors,
      bindings:bindings,detached:detached,
      plans:mappedPlanSummaries(),copyCalls:mappedCopyCalls,
      legacySkips:mappedLegacySkips,records:ImportRefreshManager.cachedRecords(install)});
    } catch(error:Dynamic) report({status:"error",error:Std.string(error),
     plans:mappedPlanSummaries(),copyCalls:mappedCopyCalls,
     legacySkips:mappedLegacySkips,records:ImportRefreshManager.cachedRecords(install)});
   case "mapped-assets-refresh", "mapped-assets-two-owner-refresh", "mapped-assets-refresh-cancel":
    var nested=mode=="mapped-assets-two-owner-refresh";
    var cancelCopies=mode=="mapped-assets-refresh-cancel"?1:0;
    report(mappedRefresh(args[2],nested,cancelCopies));
   case "language-values-refresh":
    report(refreshLanguageValues(args[2]));
   case "legacy-language-no-project":
    try report(importLegacyLanguageWithoutProject(args[2])) catch(error:Dynamic)
     report({status:"error",error:Std.string(error),plan:languagePlanSummary(),
      records:ImportRefreshManager.cachedRecords(install)});
   case "language-refresh":
    report(refreshLanguage(args[2]));
   case "language-refresh-cancel":
    report(refreshLanguage(args[2],1));
   case "language-reimport":
    var source=args[2];
    try {
     var result=importLanguage(source,0,args.length<=3||args[3]!="partial");
     report({status:"ok",failed:result.failed,plan:languagePlanSummary(),
      profile:lastLanguageProfile,records:ImportRefreshManager.cachedRecords(install)});
    } catch(error:Dynamic) report({status:"error",error:Std.string(error),
     plan:languagePlanSummary(),profile:lastLanguageProfile,
     records:ImportRefreshManager.cachedRecords(install)});
   case "source-build-context":
    var source=args[2];
    ImportRefreshManager.checked=true;
    ImportRefreshManager.inspectionPending=false;
    ImportRefreshManager.inspectionRunning=false;
    ImportRefreshManager.unresolvedRecovery=false;
    cancelAfterWrite=false;
    var profileChecks:Array<Dynamic>=[];
    var profileConverter=function(retained:String,scanned:ImportScanResult,
     names:Map<String,String>):SongImportBatchResult {
     profileChecks.push(assertCurrentSourceProfile(retained));
     return converter(profileChecks.length>1)(retained,scanned,names);
    };
    var buildContext:ImportSourceBuildContext={sourceRoot:source,engine:"Psych Engine",
     build:{target:"explicit-fixture-target",flagsComplete:true,command:"build",flags:[{name:"EXPLICIT_BUILD_CONTEXT",
      state:"enabled",provenance:"caller-supplied"}]}};
    var first=ImportRefreshManager.importOnce(source,"Psych Engine",scan(source),new Map(),
     profileConverter,noCancel,progress,[buildContext]);
    if(first.failed>0) throw "initial explicit source build context import failed";
    var record=findRecord(Std.string(ImportRefreshManager.cachedRecords(install)[0].id));
    var contexts:Dynamic=Reflect.field(record,"sourceBuildContexts");
    if(contexts==null||Reflect.field(contexts,"version")!=1
      ||Reflect.field(contexts,"snapshotId")!=Reflect.field(record,"snapshotId"))
     throw "explicit source build context was not committed with the retained snapshot";
    var contextRoots:Array<Dynamic>=cast Reflect.field(contexts,"roots");
    if(contextRoots==null||contextRoots.length!=1||Reflect.field(contextRoots[0],"rootRelative")!=""
      ||Reflect.field(contextRoots[0],"sourceRoot")!=null)
     throw "persisted source build context was not root-relative";
    Reflect.setField(record,"sourceAssetProfiles",{version:99,snapshotId:"stale",roots:[]});
    var second=ImportRefreshManager.refreshNow(install,record,profileConverter,noCancel,progress);
    if(second.failed>0) throw "retained refresh lost the explicit source build context";
    var refreshed=findRecord(Std.string(record.id));
    var profiles:Dynamic=Reflect.field(refreshed,"sourceAssetProfiles");
    var profileRoots:Array<Dynamic>=profiles==null?null:cast Reflect.field(profiles,"roots");
    if(profiles==null||Reflect.field(profiles,"version")!=1
      ||Reflect.field(profiles,"snapshotId")!=Reflect.field(refreshed,"snapshotId")
      ||profileRoots==null||profileRoots.length!=1)
     throw "derived source profile metadata was not regenerated from the verified retained snapshot";
    var storedProfile:Dynamic=Reflect.field(profileRoots[0],"profile");
    var priorSnapshot=Std.string(Reflect.field(refreshed,"snapshotId"));
    File.saveContent(Path.join([source,"changed-after-explicit-context.txt"]),"new snapshot input");
    var noContextObservation:Dynamic=null;
    var noContextConverter=function(retained:String,scanned:ImportScanResult,
     nextNames:Map<String,String>):SongImportBatchResult {
     noContextObservation=assertCurrentSourceProfileWithoutExplicitContext(retained);
     return converter(true)(retained,scanned,nextNames);
    };
    var recaptured=ImportRefreshManager.importOnce(source,"Psych Engine",scan(source),new Map(),
     noContextConverter,noCancel,progress);
    if(recaptured.failed>0) throw "changed-source recapture without explicit context failed";
    var recapturedRecord=findRecord(Std.string(refreshed.id));
    if(Reflect.field(recapturedRecord,"sourceBuildContexts")!=null
      ||Std.string(Reflect.field(recapturedRecord,"snapshotId"))==priorSnapshot)
     throw "changed-source recapture reused prior explicit build context or snapshot";
    report({failed:first.failed+second.failed+recaptured.failed,profileChecks:profileChecks,
     sourceBuildContexts:contexts,sourceAssetProfiles:profiles,
     committedProfile:storedProfile,priorSnapshot:priorSnapshot,
     recapturedSnapshot:recapturedRecord.snapshotId,noContextObservation:noContextObservation,
     recapturedHasBuildContexts:Reflect.field(recapturedRecord,"sourceBuildContexts")!=null,
     recapturedProfileMetadata:Reflect.field(recapturedRecord,"sourceAssetProfiles"),
     records:ImportRefreshManager.cachedRecords(install)});
  case "source-build-context-invalid":
    var source=args[2];
    ImportRefreshManager.checked=true;
    ImportRefreshManager.inspectionPending=false;
    ImportRefreshManager.inspectionRunning=false;
    ImportRefreshManager.unresolvedRecovery=false;
    var base:ImportSourceBuildContext={sourceRoot:source,engine:"Psych Engine",
     build:{flags:[{name:"EXPLICIT_BUILD_CONTEXT",state:"enabled"}]}};
    var manyValues:Array<Dynamic>=[];
    for(index in 0...16385) manyValues.push({name:"VALUE_"+index,value:"x"});
    var largeValues:Array<Dynamic>=[];
    var largeValue=StringTools.lpad("x","x",4096);
    for(index in 0...1025) largeValues.push({name:"TEXT_"+index,value:largeValue});
    var attempts:Array<Array<ImportSourceBuildContext>>=[
     [{sourceRoot:Path.join([source,"unselected"]),engine:"Psych Engine",build:{flags:[]}}],
     [base,base],
     [{sourceRoot:source,engine:"Psych Engine",build:{flags:[{name:"BAD_STATE",state:"windows"}]}}],
     [{sourceRoot:source,engine:"Psych Engine",build:cast {values:cast [
      {name:"DUPLICATE",value:"first"},{name:"DUPLICATE",value:"second"}]}}],
     [{sourceRoot:source,engine:"Psych Engine",build:cast {flags:[{name:"KNOWN",state:"disabled"}],
      values:cast [{name:"KNOWN",value:"literal"}]}}],
     [{sourceRoot:source,engine:"Psych Engine",build:cast {flags:[{name:"KNOWN",state:"unresolved"}],
      values:cast [{name:"KNOWN",value:"literal"}]}}],
     [{sourceRoot:source,engine:"Psych Engine",build:cast {values:cast [{name:"KNOWN",value:17}]}}],
     [{sourceRoot:source,engine:"Psych Engine",build:cast {values:cast [{name:"KNOWN",value:"x",provenance:17}]}}],
     [{sourceRoot:source,engine:"Psych Engine",build:cast {values:cast [
      {name:"KNOWN",value:"x",provenance:null}]}}],
     [{sourceRoot:source,engine:"Psych Engine",build:cast {values:cast [
      {name:"KNOWN",value:"x",provenance:" "}]}}],
     [{sourceRoot:source,engine:"Psych Engine",build:cast {values:cast [
      {name:"KNOWN",value:StringTools.lpad("x","x",4097)}]}}],
     [{sourceRoot:source,engine:"Psych Engine",build:cast {flagsComplete:"true"}}],
     [{sourceRoot:source,engine:"Psych Engine",build:cast {flagsComplete:null}}],
     [{sourceRoot:source,engine:"Psych Engine",build:cast {command:null}}],
     [{sourceRoot:source,engine:"Psych Engine",build:cast {command:17}}],
     [{sourceRoot:source,engine:"Psych Engine",build:cast {command:StringTools.lpad("x","x",129)}}],
     [{sourceRoot:source,engine:"Psych Engine",build:cast {command:"bad\ncommand"}}],
     [{sourceRoot:source,engine:"Psych Engine",build:cast {flags:null}}],
     [{sourceRoot:source,engine:"Psych Engine",build:cast {values:null}}],
     [{sourceRoot:source,engine:"Psych Engine",build:cast {values:manyValues}}],
     [{sourceRoot:source,engine:"Psych Engine",build:cast {values:largeValues}}]
    ];
    var errors:Array<String>=[];
    for(contexts in attempts) {
     var failed=false;
     try ImportRefreshManager.importOnce(source,"Psych Engine",scan(source),new Map(),
      converter(false),noCancel,progress,contexts) catch(error:Dynamic) {failed=true;errors.push(Std.string(error));}
     if(!failed) throw "invalid source build context unexpectedly reached capture";
     if(FileSystem.exists(Path.join([install,"import-cache","sources"])))
      throw "invalid source build context created a retained snapshot";
    }
    report({rejected:errors.length,errors:errors,records:ImportRefreshManager.cachedRecords(install)});
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


def native_manager_fixture_command(executable: Path, mode: str, install: Path,
                                  *args: object) -> list[str]:
    """Build the shared native fixture argv without shell quoting or reordering."""
    return [str(executable), "manager-fixture", mode, str(install), *map(str, args)]


def eval_manager_fixture_command(mode: str, install: Path, fixture_dir: Path,
                                 *args: object) -> list[str]:
    """Preserve the existing portable Haxe eval invocation."""
    return [*HAXE_COMMAND, "-cp", str(SOURCE), "-cp", str(TJSON), "-cp", str(fixture_dir),
            "--run", "ImportRefreshManagerFixture", mode, str(install), *map(str, args)]


def manager_fixture_command(native_fixture, mode: str, install: Path,
                            fixture_dir: Path, *args: object) -> list[str]:
    if native_fixture is None:
        return eval_manager_fixture_command(mode, install, fixture_dir, *args)
    return native_manager_fixture_command(native_fixture.executable, mode, install, *args)


class NativeManagerFixtureRouteTest(unittest.TestCase):
    def test_native_route_preserves_manager_mode_and_path_arguments(self):
        command = native_manager_fixture_command(
            Path("C:/fixture/NativeImportFilesystemFixture.exe"),
            "refresh-concurrent-owned",
            Path("C:/long install/owner"),
            "retained-owner-id",
            Path("C:/long donor path"),
        )
        self.assertEqual(command, [
            "C:/fixture/NativeImportFilesystemFixture.exe",
            "manager-fixture",
            "refresh-concurrent-owned",
            "C:/long install/owner",
            "retained-owner-id",
            "C:/long donor path",
        ])

    def test_eval_fallback_preserves_portable_haxe_invocation(self):
        command = manager_fixture_command(
            None,
            "refresh",
            Path("C:/install"),
            Path("C:/scratch/haxe"),
            "retained-owner-id",
        )
        self.assertEqual(command, [
            *HAXE_COMMAND,
            "-cp", str(SOURCE),
            "-cp", str(TJSON),
            "-cp", "C:/scratch/haxe",
            "--run", "ImportRefreshManagerFixture", "refresh", "C:/install",
            "retained-owner-id",
        ])

    def test_native_dispatch_and_argument_guard_are_present(self):
        from windows_native_import_fixture import MAIN, native_fixture_source

        self.assertIn('case "manager-fixture":', MAIN)
        self.assertIn("ImportRefreshManagerFixture.main();", MAIN)
        self.assertIn(
            'if(args.length>0 && args[0]=="manager-fixture") args.shift();',
            native_fixture_source(),
        )


class ImportRefreshManagerTest(unittest.TestCase):
    @staticmethod
    def scalar_unicode(value: str) -> str:
        """Normalize Haxe's UTF-16 code-unit representation for Python checks."""
        result = []
        index = 0
        while index < len(value):
            code = ord(value[index])
            if 0xD800 <= code <= 0xDBFF and index + 1 < len(value):
                low = ord(value[index + 1])
                if 0xDC00 <= low <= 0xDFFF:
                    result.append(chr(0x10000 + ((code - 0xD800) << 10) + (low - 0xDC00)))
                    index += 2
                    continue
            result.append(value[index])
            index += 1
        return "".join(result)

    @classmethod
    def setUpClass(cls):
        if not HAXE.is_file() or not TJSON.is_dir():
            raise unittest.SkipTest("portable Haxe or pinned TJSON is unavailable")
        cls.native_fixture = None
        if os.name == "nt" and os.environ.get("CAMMIE_FORCE_EVAL") != "1":
            from windows_native_import_fixture import NativeFixtureUnavailable, get_native_fixture
            try:
                cls.native_fixture = get_native_fixture()
            except NativeFixtureUnavailable:
                # Keep the portable eval path on machines without the optional
                # native compiler. Windows runs with the toolchain use the
                # shared C++ fixture for every manager mode.
                cls.native_fixture = None

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
        if self.native_fixture is None:
            self.fixture_dir = self.scratch / "haxe"
            self.fixture_dir.mkdir()
            for relative, content in STUBS.items():
                target = self.fixture_dir / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8", newline='\n')
            (self.fixture_dir / "ImportRefreshManagerFixture.hx").write_text(FIXTURE, encoding="utf-8", newline='\n')

    def use_eval_fixture(self):
        """Compile current production Haxe sources through eval even on Windows."""
        self.native_fixture = None
        if not hasattr(self, "fixture_dir"):
            self.fixture_dir = self.scratch / "haxe"
            self.fixture_dir.mkdir()
            for relative, content in STUBS.items():
                target = self.fixture_dir / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8", newline="\n")
            (self.fixture_dir / "ImportRefreshManagerFixture.hx").write_text(
                FIXTURE, encoding="utf-8", newline="\n")

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

    def make_language_source(self, name: str) -> Path:
        source = self.make_source(name, initial_songs=["language-fixture"],
                                  next_songs=["language-fixture"])
        (source / "Project.xml").write_text(
            '<project><assets path="assets/translations" rename="assets/languages" '
            'if="EXPLICIT_BUILD_CONTEXT" /></project>',
            encoding="utf-8", newline="\n")
        for locale, phrase in (("en-US", "Hello from the retained source"),
                               ("fr-FR", "Bonjour depuis la source retenue")):
            language = source / "assets/translations/data" / (locale + ".lang")
            language.parent.mkdir(parents=True, exist_ok=True)
            language.write_text("English (US)\nmessage: \"" + phrase + "\"\n",
                                encoding="utf-8", newline="\n")
        return source

    def make_mapped_assets_source(self, name: str, *, nested: bool = False,
                                 project: str | None = None,
                                 enabled: bool = False) -> Path:
        fixture_song = "mapped-assets-fixture-" + name
        source = self.make_source(name, initial_songs=[fixture_song],
                                  next_songs=[fixture_song])
        if project is None:
            condition = ' if="DISABLED_MEDIA"' if enabled else ""
            project = (
                '<project>'
                '<assets path="assets/media" rename="assets/images/primary"' + condition + ' />'
                '<assets path="assets/media" rename="assets/images/secondary"' + condition + ' />'
                '<assets path="assets/translations" rename="assets/translations" />'
                '</project>'
            )
        roots = [source]
        if nested:
            roots.append(source / "nested")
        for index, root in enumerate(roots):
            root.mkdir(parents=True, exist_ok=True)
            (root / "Project.xml").write_text(project, encoding="utf-8", newline="\n")
            marker = "owner-" + str(index) + "-" + name
            media = root / "assets/media/icon.png"
            media.parent.mkdir(parents=True, exist_ok=True)
            media.write_bytes((marker + "-media").encode("utf-8"))
            language = root / "assets/translations/data/en-US.lang"
            language.parent.mkdir(parents=True, exist_ok=True)
            language.write_text("English (US)\nowner: \"" + marker + "\"\n",
                                encoding="utf-8", newline="\n")
        return source

    def mapped_owner_path(self, record: dict, relative: str = "") -> Path:
        root = next(item for item in record["roots"] if item["relative"] == relative)
        return self.install / "assets/imported_mods" / root["namespace"]

    def make_language_values_source(self, name: str) -> Path:
        source = self.make_source(name, initial_songs=["language-values-fixture"],
                                  next_songs=["language-values-fixture"])
        project = (
            '<project><set name="SOURCE_PREFIX" value="assets/${SOURCE_AREA}" />'
            '<set name="TARGET_PREFIX" value="assets/${TARGET_AREA}" />'
            '<include path="project/includes/language-assets.xml" /></project>'
        )
        included = (
            '<project><set name="LANGUAGE_SOURCE" value="${SOURCE_PREFIX}/data" />'
            '<set name="LANGUAGE_TARGET" value="${TARGET_PREFIX}/data" />'
            '<assets path="../../${LANGUAGE_SOURCE}" rename="${LANGUAGE_TARGET}" '
            'if="TRANSLATIONS_ALLOWED" />'
            '<assets path="../../assets/optional-translations" rename="assets/optional-output" '
            'if="UNLISTED_OPTIONAL_FLAG" />'
            '<assets path="../../assets/false-value-assets" rename="assets/false-value-output" '
            'if="LITERAL_FALSE_VALUE" /></project>'
        )
        roots = [
            (source, "translations", "Hello from the primary root"),
            (source / "nested", "alternate-translations", "Hello from the secondary root"),
        ]
        for root, source_area, phrase in roots:
            root.mkdir(parents=True, exist_ok=True)
            (root / "Project.xml").write_text(project, encoding="utf-8", newline="\n")
            include_path = root / "project/includes/language-assets.xml"
            include_path.parent.mkdir(parents=True, exist_ok=True)
            include_path.write_text(included, encoding="utf-8", newline="\n")
            language = root / "assets" / source_area / "data/en-US.lang"
            language.parent.mkdir(parents=True, exist_ok=True)
            language.write_text("English (US)\nmessage: \"" + phrase + "\"\n",
                                encoding="utf-8", newline="\n")
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
        command = manager_fixture_command(
            self.native_fixture, mode, self.install,
            getattr(self, "fixture_dir", Path(".")), *args,
        )
        if self.native_fixture is not None:
            environment = self.native_fixture.environment
        else:
            environment = {**os.environ, "TMPDIR": str(ROOT / "tmp")}
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout.strip().splitlines()[-1])

    def test_disposable_staging_cleanup_pauses_during_gameplay_and_resumes(self):
        result = self.run_fixture("cleanup-scheduler")
        self.assertFalse(result["completedWhileGameplay"], result)
        self.assertTrue(result["treePreserved"], result)
        self.assertTrue(result["foregroundRemoved"], result)
        self.assertTrue(result["removed"], result)

    def test_real_receipt_inspection_pauses_during_gameplay_and_resumes(self):
        source = self.make_source("receipt-inspection-scheduler")
        result = self.run_fixture("inspection-scheduler", str(source))
        self.assertTrue(result["paused"], result)
        self.assertTrue(result["foregroundProgress"], result)
        self.assertTrue(result["resumed"], result)
        self.assertEqual(len(result["committedRoots"]), 1, result)

    def test_registry_reconciliation_pauses_before_staging_and_resumes(self):
        source = self.make_source("registry-reconciliation-scheduler")
        initial = self.run_fixture("fresh", str(source))
        self.assertEqual(initial["failed"], 0, initial)
        record = next(record for record in initial["records"]
                      if record["label"] == source.name)
        before = (self.install / REGISTRY).read_bytes()
        self.mark_record_stale(record)

        result = self.run_fixture("registry-scheduler", record["id"])

        self.assertEqual(result["status"], "ok", result)
        self.assertTrue(result["paused"], result)
        self.assertTrue(result["registryUnchangedWhilePaused"], result)
        self.assertTrue(result["foregroundProgress"], result)
        self.assertTrue(result["resumed"], result)
        self.assertEqual(result["ownerVersion"], "v2-" + source.name)
        self.assertEqual((self.install / REGISTRY).read_bytes(), before.replace(
            ("v1-" + source.name).encode(), ("v2-" + source.name).encode()))

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
        self.assertEqual(result["failedDuring"], ["assets/imported_mods/staged-owner"])
        self.assertEqual(result["failedAfter"], ["assets/imported_mods/staged-owner"])
        self.assertTrue(result["unresolvedAfterFailure"])
        self.assertTrue(result["priorScopeAfterFailure"])

    def test_scoped_uncertainty_rechecks_without_gating_other_packages_or_dropping_reservations(self):
        donor = self.make_source("donor-availability-recheck")
        record = self.initial_import(donor)
        unrelated = "assets/imported_mods/" + record["roots"][0]["namespace"]
        result = self.run_fixture("scoped-recheck", unrelated)
        blocked = "assets/imported_mods/scoped-owner"
        self.assertTrue(result["accepted"], result)
        self.assertTrue(result["unrelatedReady"], result)
        self.assertEqual(result["pendingBefore"], [blocked], result)
        self.assertEqual(result["pendingAfter"], [blocked], result)
        self.assertFalse(result["scopedAfter"], result)
        self.assertFalse(result["scopedPathsAfter"], result)
        self.assertFalse(result["inspectionPending"], result)
        self.assertFalse(result["inspectionRunning"], result)
        self.assertFalse(result["active"], result)
        self.assertGreater(result["startRevision"], result["beforeRevision"], result)
        self.assertGreaterEqual(result["afterRevision"], result["startRevision"], result)
        self.assertTrue(result["ownerlessAccepted"], result)
        self.assertTrue(result["ownerlessInspectionPending"], result)
        self.assertTrue(result["emptyScopedPreserved"], result)
        self.assertTrue(result["emptyPathsPreserved"], result)
        self.assertTrue(result["emptyCommittedPreserved"], result)

    def test_committed_cyclic_dependencies_drain_handoffs_without_deadlock(self):
        result = self.run_fixture("handoff-cycle")
        self.assertTrue(result["first"] and result["second"], result)
        self.assertEqual(result["generation"], 2, result)
        self.assertEqual(result["pending"], [], result)
        self.assertEqual(result["committed"], sorted([
            "assets/imported_mods/cycle-a", "assets/imported_mods/cycle-b"]))

    def test_category_snapshot_waits_for_safe_freeplay_handoff_then_refreshes(self):
        result = self.run_fixture("category-handoff")
        self.assertTrue(result["deferred"], result)
        self.assertTrue(result["categoryBusy"], result)
        self.assertFalse(result["freeplayBusy"], result)
        self.assertEqual(result["generation"], 1, result)
        self.assertTrue(result["refreshed"], result)
        self.assertEqual(result["selected"], ["new-chart"], result)

    def test_explicit_build_context_binds_to_verified_root_and_regenerates_profiles_on_refresh(self):
        source = self.make_source("donor-build-context")
        (source / "Project.xml").write_text(
            '<project><define name="PROJECT_CONTEXT_FLAG" /></project>',
            encoding="utf-8", newline="\n")

        result = self.run_fixture("source-build-context", source)

        self.assertEqual(result["failed"], 0, result)
        self.assertEqual(len(result["profileChecks"]), 2, result)
        first, refreshed = result["profileChecks"]
        self.assertEqual(first["snapshotId"], refreshed["snapshotId"], result)
        self.assertEqual(first["rootRelative"], "", result)
        self.assertEqual(first["provenance"], "receipt-bound", result)
        self.assertEqual(first["contentRoot"].replace("\\", "/").split("/")[-1], "content", result)
        saved_context = result["sourceBuildContexts"]
        self.assertEqual(saved_context["version"], 1, result)
        self.assertEqual(saved_context["snapshotId"], first["snapshotId"], result)
        self.assertTrue(saved_context["roots"][0]["build"]["flagsComplete"], result)
        self.assertEqual(saved_context["roots"][0]["build"]["command"], "build", result)
        self.assertTrue(first["flagsComplete"], result)
        self.assertEqual(first["buildCommand"], "build", result)
        self.assertEqual(len(saved_context["roots"]), 1, result)
        self.assertNotIn("sourceRoot", saved_context["roots"][0], result)
        profile_metadata = result["sourceAssetProfiles"]
        self.assertEqual(profile_metadata["version"], 1, result)
        self.assertEqual(profile_metadata["snapshotId"], refreshed["snapshotId"], result)
        self.assertEqual(len(profile_metadata["roots"]), 1, result)
        self.assertEqual(profile_metadata["roots"][0]["profile"]["provenance"], "receipt-bound", result)
        self.assertTrue(any(flag["name"] == "EXPLICIT_BUILD_CONTEXT"
                            and flag["state"] == "enabled"
                            and flag["provenance"] == "caller-supplied"
                            for flag in profile_metadata["roots"][0]["profile"]["flags"]), result)
        self.assertNotEqual(result["recapturedSnapshot"], result["priorSnapshot"], result)
        self.assertFalse(result["recapturedHasBuildContexts"], result)
        self.assertEqual(result["noContextObservation"]["snapshotId"], result["recapturedSnapshot"], result)
        self.assertEqual(result["noContextObservation"]["provenance"], "receipt-bound", result)
        self.assertFalse(result["noContextObservation"]["flagsComplete"], result)
        self.assertIsNone(result["noContextObservation"]["buildCommand"], result)
        recaptured_profiles = result["recapturedProfileMetadata"]
        self.assertEqual(recaptured_profiles["snapshotId"], result["recapturedSnapshot"], result)
        self.assertFalse(any(flag["name"] == "EXPLICIT_BUILD_CONTEXT"
                             for flag in recaptured_profiles["roots"][0]["profile"]["flags"]), result)

    def test_unselected_duplicate_and_malformed_build_contexts_reject_before_snapshot_capture(self):
        source = self.make_source("donor-invalid-build-context")

        result = self.run_fixture("source-build-context-invalid", source)

        self.assertEqual(result["rejected"], 21, result)
        self.assertEqual(result["records"], [], result)
        self.assertTrue(any("exact selected root" in error for error in result["errors"]), result)
        self.assertTrue(any("duplicate" in error for error in result["errors"]), result)
        self.assertTrue(any("state" in error for error in result["errors"]), result)
        self.assertTrue(any("conflicts with a disabled or unresolved flag" in error
                            for error in result["errors"]), result)
        self.assertTrue(any("too many values" in error for error in result["errors"]), result)
        self.assertTrue(any("aggregate text limit" in error for error in result["errors"]), result)
        self.assertTrue(any("flagsComplete must be a boolean" in error
                            for error in result["errors"]), result)
        self.assertTrue(any("command must be text" in error
                            for error in result["errors"]), result)
        self.assertTrue(any("command has an invalid length" in error
                            for error in result["errors"]), result)
        self.assertTrue(any("command contains a control character" in error
                            for error in result["errors"]), result)
        self.assertTrue(any("must be an array when present" in error
                            for error in result["errors"]), result)

    def language_output_path(self, record: dict, locale: str = "en-US") -> Path:
        namespace = record["roots"][0]["namespace"]
        return self.install / "assets/imported_mods" / namespace / "languages/data" / (locale + ".lang")

    def language_values_output_path(self, record: dict, root_relative: str) -> Path:
        root = next(item for item in record["roots"] if item["relative"] == root_relative)
        target = "languages" if root_relative == "" else "alt-languages"
        return (self.install / "assets/imported_mods" / root["namespace"]
                / target / "data/en-US.lang")

    def test_manager_publishes_retained_language_mapping_and_rebuilds_tampered_profile_after_donor_removal(self):
        source = self.make_language_source("donor-language-retained")
        initial = self.run_fixture("fresh-language", source)

        self.assertEqual(initial["status"], "ok", initial)
        self.assertEqual(initial["failed"], 0, initial)
        self.assertTrue(initial["plan"]["profileBound"], initial)
        self.assertTrue(initial["plan"]["authoritative"], initial)
        self.assertEqual(len(initial["plan"]["files"]), 2, initial)
        record = initial["records"][0]
        destination_prefix = "assets/imported_mods/" + record["roots"][0]["namespace"]
        self.assertEqual(
            {item["destinationPath"] for item in initial["plan"]["files"]},
            {destination_prefix + "/languages/data/en-US.lang",
             destination_prefix + "/languages/data/fr-FR.lang"},
        )
        self.assertEqual(self.language_output_path(record).read_text(encoding="utf-8"),
                         "English (US)\nmessage: \"Hello from the retained source\"\n")
        self.assertEqual(record["sourceAssetProfiles"]["version"], 1)
        self.assertEqual(record["sourceAssetProfiles"]["roots"][0]["profile"]["provenance"],
                         "receipt-bound")
        self.assertEqual(record["sourceBuildContexts"]["snapshotId"], record["snapshotId"])
        expected_target = "explicit-language-fixture 🌙"
        self.assertEqual(self.scalar_unicode(record["sourceBuildContexts"]["roots"][0]["build"]["target"]),
                         expected_target)
        self.assertEqual(self.scalar_unicode(initial["profile"]["buildTarget"]), expected_target)
        previous_snapshot = record["snapshotId"]
        previous_profile = record["sourceAssetProfiles"]

        shutil_rmtree(source)
        self.mark_record_stale(record, common_revision=None, record_updates={
            "sourceAssetProfiles": {"version": 999, "snapshotId": "tampered", "roots": []},
        })
        refreshed = self.run_fixture("language-refresh", record["id"])

        self.assertEqual(refreshed["status"], "ok", refreshed)
        self.assertTrue(refreshed["plan"]["profileBound"], refreshed)
        self.assertEqual(refreshed["profile"]["snapshotId"], previous_snapshot, refreshed)
        self.assertFalse(source.exists())
        refreshed_record = refreshed["records"][0]
        self.assertEqual(refreshed_record["snapshotId"], previous_snapshot, refreshed)
        self.assertEqual(refreshed_record["sourceBuildContexts"]["snapshotId"], previous_snapshot,
                         refreshed)
        self.assertEqual(
            self.scalar_unicode(refreshed_record["sourceBuildContexts"]["roots"][0]["build"]["target"]),
            expected_target, refreshed)
        self.assertEqual(self.scalar_unicode(refreshed["profile"]["buildTarget"]), expected_target,
                         refreshed)
        self.assertEqual(refreshed_record["sourceAssetProfiles"]["version"], 1, refreshed)
        self.assertEqual(refreshed_record["sourceAssetProfiles"]["roots"][0]["profile"]["provenance"],
                         "receipt-bound", refreshed)
        self.assertNotEqual(refreshed_record["sourceAssetProfiles"],
                            {"version": 999, "snapshotId": "tampered", "roots": []}, refreshed)
        self.assertNotEqual(previous_profile, {"version": 999, "snapshotId": "tampered", "roots": []})
        self.assertEqual(self.language_output_path(refreshed_record).read_text(encoding="utf-8"),
                         "English (US)\nmessage: \"Hello from the retained source\"\n")

    def test_absent_project_keeps_legacy_psych_language_collection_enabled(self):
        source = self.make_source("donor-language-no-project", initial_songs=["legacy-language"],
                                  next_songs=["legacy-language"])
        self.assertFalse((source / "Project.xml").exists())
        legacy_source = source / "assets/data/languages/en-US.lang"
        legacy_source.parent.mkdir(parents=True)
        legacy_source.write_text("English (US)\nmessage: \"Legacy language remains available\"\n",
                                 encoding="utf-8", newline="\n")

        result = self.run_fixture("legacy-language-no-project", source)

        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(result["failed"], 0, result)
        plan = result["plan"]
        self.assertFalse(plan["profileBound"], result)
        self.assertTrue(plan["legacyAllowed"], result)
        self.assertFalse(plan["blockAllLegacy"], result)
        record = result["records"][0]
        profile = record["sourceAssetProfiles"]["roots"][0]["profile"]
        self.assertEqual(profile["provenance"], "invalid", result)
        self.assertTrue(any(item.startswith("project-xml-missing:")
                            for item in profile["diagnostics"]), result)
        destination = (self.install / "assets/imported_mods" / record["roots"][0]["namespace"]
                       / "data/languages/en-US.lang")
        self.assertEqual(destination.read_text(encoding="utf-8"), legacy_source.read_text(encoding="utf-8"))

    def test_present_malformed_project_stops_language_reimport_before_replacing_prior_output(self):
        source = self.make_language_source("donor-language-malformed-project")
        initial = self.run_fixture("fresh-language", source)
        self.assertEqual(initial["status"], "ok", initial)
        record = initial["records"][0]
        target = self.language_output_path(record)
        prior_bytes = target.read_bytes()
        prior_manifest = self.manifest_bytes(record)
        prior_profile = record["sourceAssetProfiles"]
        (source / "Project.xml").write_text(
            '<project><assets path="assets/translations" rename="assets/languages"></project>',
            encoding="utf-8", newline="\n")

        rejected = self.run_fixture("language-reimport", source)

        self.assertEqual(rejected["status"], "error", rejected)
        self.assertIn("source profile validation failed", rejected["error"].lower(), rejected)
        self.assertIn("project-xml-invalid", rejected["error"].lower(), rejected)
        self.assertIsNone(rejected["profile"], rejected)
        self.assertEqual(target.read_bytes(), prior_bytes)
        self.assertEqual(self.manifest_bytes(record), prior_manifest)
        self.assertEqual(rejected["records"][0]["snapshotId"], record["snapshotId"], rejected)
        self.assertEqual(rejected["records"][0]["sourceAssetProfiles"], prior_profile, rejected)

    def test_manager_refresh_conflict_preserves_edited_language_bytes_and_profile_metadata(self):
        source = self.make_language_source("donor-language-local-edit")
        initial = self.run_fixture("fresh-language", source)
        self.assertEqual(initial["status"], "ok", initial)
        record = initial["records"][0]
        target = self.language_output_path(record)
        profile_before = record["sourceAssetProfiles"]
        target.write_text("locally edited language\n", encoding="utf-8", newline="\n")

        refreshed = self.run_fixture("language-refresh", record["id"])

        self.assertEqual(refreshed["status"], "error", refreshed)
        self.assertIn("local edits are preserved", refreshed["error"].lower(), refreshed)
        self.assertEqual(target.read_text(encoding="utf-8"), "locally edited language\n")
        self.assertEqual(refreshed["records"][0]["sourceAssetProfiles"], profile_before, refreshed)

    def assert_language_reimport_conflict_preserves_previous_owner(self, name: str,
            project: str, extra_files: dict[str, str], expected_diagnostics: tuple[str, ...],
            complete_build_context: bool = True) -> None:
        source = self.make_language_source(name)
        initial = self.run_fixture("fresh-language", source)
        self.assertEqual(initial["status"], "ok", initial)
        record = initial["records"][0]
        target = self.language_output_path(record)
        prior_bytes = target.read_bytes()
        prior_profile_metadata = record["sourceAssetProfiles"]
        (source / "Project.xml").write_text(project, encoding="utf-8", newline="\n")
        for relative, text in extra_files.items():
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")

        rejected = self.run_fixture("language-reimport", source,
                                    *([] if complete_build_context else ["partial"]))

        self.assertEqual(rejected["status"], "error", rejected)
        for expected_diagnostic in expected_diagnostics:
            self.assertIn(expected_diagnostic, rejected["error"], rejected)
        self.assertEqual(target.read_bytes(), prior_bytes)
        self.assertEqual(rejected["records"][0]["snapshotId"], record["snapshotId"], rejected)
        self.assertEqual(rejected["records"][0]["sourceAssetProfiles"], prior_profile_metadata, rejected)

    def test_ambiguous_language_mapping_over_prior_owner_output_stops_reimport(self):
        self.assert_language_reimport_conflict_preserves_previous_owner(
            "donor-language-ambiguous",
            '<project><assets path="assets/translations" rename="assets/languages" '
            'if="EXPLICIT_BUILD_CONTEXT" /><assets path="assets/alternate-translations" '
            'rename="assets/languages" if="EXPLICIT_BUILD_CONTEXT" /></project>',
            {"assets/alternate-translations/data/en-US.lang":
             "English (US)\nmessage: \"Ambiguous alternate\"\n"},
            (
                "Distinct mapped sources target the same owner asset path",
                "Distinct sources map to a previously managed psych-language output; refresh stopped to preserve it",
            ),
        )

    def test_unresolved_language_mapping_over_prior_owner_output_stops_reimport(self):
        self.assert_language_reimport_conflict_preserves_previous_owner(
            "donor-language-unresolved",
            '<project><assets path="assets/translations" rename="assets/languages" '
            'if="EXPLICIT_BUILD_CONTEXT" /><assets path="assets/unresolved-translations" '
            'rename="assets/languages" if="MISSING_LANGUAGE_FLAG" /></project>',
            {"assets/unresolved-translations/data/en-US.lang":
             "English (US)\nmessage: \"Unresolved alternate\"\n"},
            (
                "Skipped unresolved Project.xml asset mapping at declaration 1",
                "An unresolved psych-language mapping overlaps prior managed output; refresh stopped to preserve it",
            ),
            complete_build_context=False,
        )

    def test_language_publication_cancellation_does_not_commit_staged_bytes_or_metadata(self):
        source = self.make_language_source("donor-language-cancel")
        initial = self.run_fixture("fresh-language", source)
        self.assertEqual(initial["status"], "ok", initial)
        record = initial["records"][0]
        previous_files = {
            locale: self.language_output_path(record, locale).read_bytes()
            for locale in ("en-US", "fr-FR")
        }
        previous_profile = record["sourceAssetProfiles"]

        cancelled = self.run_fixture("language-refresh-cancel", record["id"])

        self.assertEqual(cancelled["status"], "error", cancelled)
        self.assertTrue(cancelled["plan"]["cancelled"], cancelled)
        self.assertEqual(cancelled["plan"]["copyCalls"], 1, cancelled)
        self.assertEqual(cancelled["records"][0]["sourceAssetProfiles"], previous_profile, cancelled)
        for locale, expected in previous_files.items():
            self.assertEqual(self.language_output_path(record, locale).read_bytes(), expected)

    def test_committed_asset_index_binding_is_owner_receipt_scoped_and_detached(self):
        source = self.make_mapped_assets_source("donor-identity-binding")
        imported = self.run_fixture("mapped-assets-binding", source)
        self.assertEqual(imported["status"], "ok", imported)
        self.assertEqual(imported["failed"], 0, imported)
        self.assertTrue(imported["detached"], imported)
        self.assertEqual(len(imported["bindings"]), 1, imported)
        binding = imported["bindings"][0]
        record = imported["records"][0]
        namespace = record["roots"][0]["namespace"]
        self.assertEqual(binding["owner"], "assets/imported_mods/" + namespace)
        self.assertEqual(binding["namespace"], namespace)
        self.assertEqual(binding["engine"], "Psych Engine")
        self.assertEqual(binding["scope"], "package")
        self.assertEqual(binding["snapshotId"], record["snapshotId"])
        self.assertEqual(binding["rootRelative"], "")
        self.assertEqual(binding["transactionId"], json.loads(self.manifest_bytes(record))["transactionId"])
        expected_path = binding["owner"] + "/.cammie-asset-identities/psych.json"
        self.assertEqual(binding["indexPath"], expected_path)
        digest = hashlib.sha256((self.install / expected_path).read_bytes()).hexdigest()
        self.assertEqual(binding["indexSha256"], digest)
        proof = {entry["path"]: entry["sha256"] for entry in binding["files"]}
        self.assertEqual(proof[expected_path], digest)
        self.assertTrue(all(path.startswith(binding["owner"] + "/") for path in proof))

    def test_manager_combines_mapped_media_and_language_for_each_owner_and_refreshes_after_donor_removal(self):
        source = self.make_mapped_assets_source("donor-mapped-two-owner", nested=True)
        initial = self.run_fixture("mapped-assets-two-owner", source)

        self.assertEqual(initial["status"], "ok", initial)
        self.assertEqual(initial["failed"], 0, initial)
        self.assertEqual(len(initial["plans"]), 2, initial)
        self.assertTrue(all(plan["profileBound"] and not plan["failed"] for plan in initial["plans"]), initial)
        for plan in initial["plans"]:
            media_outputs = {item["ownerRelative"] for item in plan["files"]
                             if "psych-media" in item["policyLabels"]}
            self.assertEqual(media_outputs,
                             {"images/primary/icon.png", "images/secondary/icon.png"}, plan)
        record = initial["records"][0]
        self.assertEqual({root["relative"] for root in record["roots"]}, {"", "nested"})
        self.assertEqual(len({root["namespace"] for root in record["roots"]}), 2)
        profiles_by_root = {root["rootRelative"]: root for root in record["sourceAssetProfiles"]["roots"]}
        self.assertEqual(set(profiles_by_root), {"", "nested"})
        self.assertTrue(all(root["profile"]["provenance"] == "receipt-bound"
                            and root["profile"]["snapshotId"] == record["snapshotId"]
                            for root in profiles_by_root.values()))
        for index, relative in enumerate(("", "nested")):
            owner = self.mapped_owner_path(record, relative)
            for target in ("images/primary/icon.png", "images/secondary/icon.png"):
                output = owner / target
                self.assertEqual(output.read_bytes(), f"owner-{index}-donor-mapped-two-owner-media".encode())
            self.assertTrue((owner / "translations/data/en-US.lang").is_file())
        self.assertTrue(all(initial["legacySkips"]), initial)
        first_snapshot = record["snapshotId"]

        shutil_rmtree(source)
        self.mark_record_stale(record)
        refreshed = self.run_fixture("mapped-assets-two-owner-refresh", record["id"])

        self.assertEqual(refreshed["status"], "ok", refreshed)
        self.assertEqual(refreshed["failed"], 0, refreshed)
        self.assertFalse(source.exists())
        refreshed_record = refreshed["records"][0]
        self.assertEqual(refreshed_record["snapshotId"], first_snapshot)
        self.assertEqual(len(refreshed["plans"]), 2, refreshed)
        self.assertTrue(all(plan["profileBound"] and not plan["failed"] for plan in refreshed["plans"]), refreshed)
        for index, relative in enumerate(("", "nested")):
            owner = self.mapped_owner_path(refreshed_record, relative)
            for target in ("images/primary/icon.png", "images/secondary/icon.png"):
                self.assertEqual((owner / target).read_bytes(),
                                 f"owner-{index}-donor-mapped-two-owner-media".encode())
        self.assertEqual(refreshed_record["sourceAssetProfiles"]["version"], 1)
        self.assertEqual(refreshed_record["sourceAssetProfiles"]["snapshotId"], first_snapshot)

    def test_mapped_media_refresh_preserves_local_edit_and_profile_metadata(self):
        source = self.make_mapped_assets_source("donor-mapped-local-edit")
        initial = self.run_fixture("mapped-assets-initial", source)
        self.assertEqual(initial["status"], "ok", initial)
        self.assertEqual(initial["failed"], 0, initial)
        record = initial["records"][0]
        owner = self.mapped_owner_path(record)
        target = owner / "images/primary/icon.png"
        target.write_bytes(b"local media edit")
        profile_before = record["sourceAssetProfiles"]
        self.mark_record_stale(record)
        manifest_before = self.manifest_bytes(record)

        refreshed = self.run_fixture("mapped-assets-refresh", record["id"])

        self.assertEqual(refreshed["status"], "error", refreshed)
        self.assertIn("local edits are preserved", refreshed["error"].lower(), refreshed)
        self.assertEqual(target.read_bytes(), b"local media edit")
        self.assertEqual(refreshed["records"][0]["sourceAssetProfiles"], profile_before, refreshed)
        self.assertEqual(self.manifest_bytes(record), manifest_before)

    def test_mapped_media_deferred_or_colliding_reimport_preserves_prior_outputs(self):
        cases = (
            ("deferred", '<project><assets path="assets/media" rename="assets/images/primary" '
             'if="MISSING_MEDIA_FLAG" /><assets path="assets/media" rename="assets/images/secondary" '
             'if="MISSING_MEDIA_FLAG" /></project>', "mapped-assets-deferred-reimport"),
            ("collision", '<project><assets path="assets/media" rename="assets/images/primary" />'
             '<assets path="assets/media-other" rename="assets/images/primary" /></project>',
             "mapped-assets-reimport"),
        )
        for kind, project, mode in cases:
            with self.subTest(kind=kind):
                source = self.make_mapped_assets_source("donor-mapped-" + kind)
                initial = self.run_fixture("mapped-assets-initial", source)
                self.assertEqual(initial["status"], "ok", initial)
                record = initial["records"][0]
                owner = self.mapped_owner_path(record)
                before = {relative: (owner / relative).read_bytes() for relative in (
                    "images/primary/icon.png", "images/secondary/icon.png")}
                profile_before = record["sourceAssetProfiles"]
                manifest_before = self.manifest_bytes(record)
                (source / "Project.xml").write_text(project, encoding="utf-8", newline="\n")
                if kind == "collision":
                    extra = source / "assets/media-other/icon.png"
                    extra.parent.mkdir(parents=True)
                    extra.write_bytes(b"distinct competing media")

                rejected = self.run_fixture(mode, source)

                self.assertEqual(rejected["status"], "error", rejected)
                self.assertTrue(any(plan["failed"] for plan in rejected["plans"]), rejected)
                for relative, expected in before.items():
                    self.assertEqual((owner / relative).read_bytes(), expected)
                self.assertEqual(rejected["records"][0]["sourceAssetProfiles"], profile_before, rejected)
                self.assertEqual(self.manifest_bytes(record), manifest_before)

    def test_disabled_mapped_media_is_not_reintroduced_by_legacy_copy_and_is_pruned(self):
        source = self.make_mapped_assets_source("donor-mapped-disabled", enabled=True)
        initial = self.run_fixture("mapped-assets-enabled-initial", source)
        self.assertEqual(initial["status"], "ok", initial)
        self.assertEqual(initial["failed"], 0, initial)
        record = initial["records"][0]
        owner = self.mapped_owner_path(record)
        prior = [owner / "images/primary/icon.png", owner / "images/secondary/icon.png"]
        self.assertTrue(all(path.is_file() for path in prior))
        self.mark_record_stale(record)

        refreshed = self.run_fixture("mapped-assets-disabled-reimport", source)

        self.assertEqual(refreshed["status"], "ok", refreshed)
        self.assertEqual(refreshed["failed"], 0, refreshed)
        self.assertTrue(all(refreshed["legacySkips"]), refreshed)
        self.assertTrue(all(not path.exists() for path in prior), refreshed)
        self.assertEqual(refreshed["records"][0]["sourceAssetProfiles"]["snapshotId"],
                         refreshed["records"][0]["snapshotId"])

    def test_mapped_media_refresh_cancellation_leaves_bytes_manifest_and_profile_unchanged(self):
        source = self.make_mapped_assets_source("donor-mapped-cancel")
        initial = self.run_fixture("mapped-assets-initial", source)
        self.assertEqual(initial["status"], "ok", initial)
        record = initial["records"][0]
        owner = self.mapped_owner_path(record)
        prior = {relative: (owner / relative).read_bytes() for relative in (
            "images/primary/icon.png", "images/secondary/icon.png")}
        profile_before = record["sourceAssetProfiles"]
        self.mark_record_stale(record)
        manifest_before = self.manifest_bytes(record)

        cancelled = self.run_fixture("mapped-assets-refresh-cancel", record["id"])

        self.assertEqual(cancelled["status"], "error", cancelled)
        self.assertEqual(cancelled["records"][0]["sourceAssetProfiles"], profile_before, cancelled)
        self.assertEqual(self.manifest_bytes(record), manifest_before)
        for relative, expected in prior.items():
            self.assertEqual((owner / relative).read_bytes(), expected)

    def test_manager_retains_per_root_build_values_and_local_include_mappings_after_donor_removal(self):
        source = self.make_language_values_source("donor-language-values-retained")
        initial = self.run_fixture("fresh-language-values", source)

        self.assertEqual(initial["status"], "ok", initial)
        self.assertEqual(initial["failed"], 0, initial)
        record = initial["records"][0]
        self.assertEqual({root["relative"] for root in record["roots"]}, {"", "nested"})
        contexts = {root["rootRelative"]: root for root in record["sourceBuildContexts"]["roots"]}
        expected = {
            "": ("translations", "languages", " primary source 🌙 "),
            "nested": ("alternate-translations", "alt-languages", " secondary source 🌙 "),
        }
        for relative, (source_area, target_area, note) in expected.items():
            context = contexts[relative]
            self.assertEqual(context["build"]["flagsComplete"], relative == "", initial)
            if relative == "":
                self.assertEqual(context["build"]["command"], "", initial)
            else:
                self.assertNotIn("command", context["build"], initial)
            values = {item["name"]: self.scalar_unicode(item["value"])
                      for item in context["build"]["values"]}
            self.assertEqual(values["SOURCE_AREA"], source_area)
            self.assertEqual(values["TARGET_AREA"], target_area)
            self.assertEqual(values["BUILD_NOTE"], note)
            self.assertTrue(all(item["provenance"] == "caller-supplied"
                                for item in context["build"]["values"]))

            output = self.language_values_output_path(record, relative)
            self.assertTrue(output.is_file(), output)
            self.assertIn(target_area, output.parts)

        self.assertEqual(len(initial["profiles"]), 2, initial)
        profiles = {profile["rootRelative"]: profile for profile in initial["profiles"]}
        self.assertNotEqual(profiles[""]["namespace"], profiles["nested"]["namespace"])
        self.assertNotEqual(profiles[""]["contextFingerprint"], profiles["nested"]["contextFingerprint"])
        self.assertEqual(profiles[""]["targetRelative"], "assets/languages/data")
        self.assertEqual(profiles["nested"]["targetRelative"], "assets/alt-languages/data")
        self.assertTrue(profiles[""]["flagsComplete"], initial)
        self.assertFalse(profiles["nested"]["flagsComplete"], initial)
        self.assertEqual(profiles[""]["absentCondition"], "disabled", initial)
        self.assertEqual(profiles["nested"]["absentCondition"], "unresolved", initial)
        self.assertEqual(profiles[""]["falseValueCondition"], "enabled", initial)
        self.assertEqual(profiles["nested"]["falseValueCondition"], "enabled", initial)
        self.assertEqual(profiles[""]["buildNote"], " primary source 🌙 ", initial)
        self.assertEqual(profiles["nested"]["buildNote"], " secondary source 🌙 ", initial)
        self.assertEqual(profiles[""]["literalFalseValue"], "false", initial)
        self.assertEqual(profiles["nested"]["literalFalseValue"], "false", initial)
        self.assertEqual(profiles[""]["buildCommand"], "", initial)
        self.assertIsNone(profiles["nested"]["buildCommand"], initial)
        self.assertEqual({plan["files"][0]["ownerRelative"] for plan in initial["plans"]},
                         {"languages/data/en-US.lang", "alt-languages/data/en-US.lang"})
        profile_roots = {root["rootRelative"]: root
                         for root in record["sourceAssetProfiles"]["roots"]}
        for relative in ("", "nested"):
            profile = profile_roots[relative]["profile"]
            self.assertTrue(any(item["path"].endswith("project/includes/language-assets.xml")
                                and len(item["sha256"]) == 64
                                for item in profile["inputFiles"]))

        previous_snapshot = record["snapshotId"]
        previous_values = record["sourceBuildContexts"]
        shutil_rmtree(source)
        self.mark_record_stale(record, common_revision=None, record_updates={
            "sourceAssetProfiles": {"version": 999, "snapshotId": "tampered", "roots": []},
        })
        refreshed = self.run_fixture("language-values-refresh", record["id"])

        self.assertEqual(refreshed["status"], "ok", refreshed)
        refreshed_record = refreshed["records"][0]
        self.assertEqual(refreshed_record["snapshotId"], previous_snapshot, refreshed)
        self.assertEqual(refreshed_record["sourceBuildContexts"], previous_values, refreshed)
        self.assertEqual(refreshed_record["sourceAssetProfiles"]["version"], 1, refreshed)
        self.assertEqual(len(refreshed["plans"]), 2, refreshed)
        refreshed_profiles = {profile["rootRelative"]: profile for profile in refreshed["profiles"]}
        self.assertTrue(refreshed_profiles[""]["flagsComplete"], refreshed)
        self.assertFalse(refreshed_profiles["nested"]["flagsComplete"], refreshed)
        self.assertEqual(refreshed_profiles[""]["absentCondition"], "disabled", refreshed)
        self.assertEqual(refreshed_profiles["nested"]["absentCondition"], "unresolved", refreshed)
        self.assertEqual(refreshed_profiles[""]["falseValueCondition"], "enabled", refreshed)
        self.assertEqual(refreshed_profiles["nested"]["falseValueCondition"], "enabled", refreshed)
        self.assertEqual(refreshed_profiles[""]["buildNote"], " primary source 🌙 ", refreshed)
        self.assertEqual(refreshed_profiles["nested"]["buildNote"], " secondary source 🌙 ", refreshed)
        self.assertEqual(refreshed_profiles[""]["literalFalseValue"], "false", refreshed)
        self.assertEqual(refreshed_profiles["nested"]["literalFalseValue"], "false", refreshed)
        self.assertEqual(refreshed_profiles[""]["buildCommand"], "", refreshed)
        self.assertIsNone(refreshed_profiles["nested"]["buildCommand"], refreshed)
        for relative in ("", "nested"):
            output = self.language_values_output_path(refreshed_record, relative)
            self.assertTrue(output.is_file(), output)
            self.assertEqual(output.read_text(encoding="utf-8").splitlines()[0], "English (US)")

    def test_tampered_retained_local_include_fails_manager_refresh_without_changing_outputs(self):
        source = self.make_language_values_source("donor-language-values-tampered-include")
        initial = self.run_fixture("fresh-language-values", source)
        self.assertEqual(initial["status"], "ok", initial)
        record = initial["records"][0]
        outputs = {relative: self.language_values_output_path(record, relative).read_bytes()
                   for relative in ("", "nested")}
        manifest_before = self.manifest_bytes(record)
        retained = self.install / "import-cache/sources" / record["snapshotId"] / "content"
        include_path = retained / "project/includes/language-assets.xml"
        self.assertTrue(include_path.is_file())
        include_path.write_text(include_path.read_text(encoding="utf-8")
                                .replace("LANGUAGE_TARGET", "TAMPERED_TARGET"),
                                encoding="utf-8", newline="\n")
        shutil_rmtree(source)

        refreshed = self.run_fixture("language-values-refresh", record["id"])

        self.assertEqual(refreshed["status"], "error", refreshed)
        self.assertRegex(refreshed["error"].lower(), r"snapshot|integrity|checksum|changed|receipt")
        self.assertEqual(self.manifest_bytes(record), manifest_before)
        for relative, expected in outputs.items():
            self.assertEqual(self.language_values_output_path(record, relative).read_bytes(), expected)

    def mark_record_stale(self, record: dict, common_revision: int | None = 0,
                          runtime_dependency_owners=None,
                          legacy_runtime_dependencies: bool = False,
                          record_updates: dict | None = None) -> None:
        owner = "retained-import:" + record["id"]
        owner_hash = hashlib.sha256(owner.encode()).hexdigest()
        scope = self.install / "import-cache/state" / owner_hash
        manifest_path = scope / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if common_revision is not None:
            manifest["revision"]["importRecord"]["revisions"][0]["commonRevision"] = common_revision
        if record_updates is not None:
            manifest["revision"]["importRecord"].update(record_updates)
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

    def test_stale_persisted_record_is_automatically_queued_on_browse_tick(self):
        if os.name == "nt" and self.native_fixture is None:
            self.skipTest("Windows eval fallback can stall; native fixture is unavailable")
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

    def test_incomplete_legacy_compat_metadata_is_scoped_to_its_import_owner(self):
        provider_source = self.make_source("donor-scoped-provider", initial_songs=["scoped-provider"])
        dependent_source = self.make_source("donor-scoped-dependent", initial_songs=["scoped-dependent"])
        provider = self.initial_import(provider_source)
        provider_root = "assets/imported_mods/" + provider["roots"][0]["namespace"]
        dependent_report = self.run_fixture("fresh-compat-dependency", dependent_source, provider_root)
        dependent = next(record for record in dependent_report["records"]
            if record["label"] == dependent_source.name)
        dependent_root = "assets/imported_mods/" + dependent["roots"][0]["namespace"]
        sidecar = self.install / "assets/data/scoped-dependent/compatScripts.json"
        self.assertTrue(sidecar.is_file())
        self.mark_record_stale(dependent, common_revision=None, legacy_runtime_dependencies=True)
        sidecar.unlink()

        result = self.run_fixture("auto-refresh")
        availability = result["availability"]

        self.assertFalse(availability["inspectionPending"], result)
        self.assertEqual(availability["pendingOwnerRoots"], [dependent_root], result)
        self.assertIn("assets/data/scoped-dependent/compatScripts.json",
            availability["pendingTouchedPaths"], result)
        self.assertEqual(availability["committedOwnerRoots"], [provider_root], result)

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
