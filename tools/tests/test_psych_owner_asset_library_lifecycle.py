"""Actual Lime/OpenFL owner libraries stay receipt-bound and owner-local."""

from haxe_test_support import HAXE_COMMAND, TEST_TMP

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe.exe"


FIXTURE = r'''package;
import haxe.crypto.Sha256;
import haxe.io.Bytes;
import haxe.io.Path;
import lime.app.Future;
import lime.text.Font as LimeFont;
import lime.utils.AssetCache as LimeAssetCache;
import lime.utils.AssetLibrary;
import lime.utils.Assets as LimeAssets;
import openfl.display.BitmapData;
import openfl.media.Sound;
import openfl.text.Font as OpenFlFont;
import openfl.utils.Assets as OpenFlAssets;
import openfl.utils.AssetCache as OpenFlAssetCache;
import PsychAssetProfile.PsychAssetProfileBuild;
import sys.FileSystem;
import sys.io.File;
import hscript.Interp;
import hscript.Parser;

@:access(lime.utils.AssetLibrary)
@:access(openfl.utils.AssetLibrary)
@:access(PsychOwnerAssetLibraryCache)
class Main {
 static function fail(message:String):Void throw message;
 static function check(value:Bool,message:String):Void if(!value)fail(message);
 static function eq(actual:Dynamic,expected:Dynamic,message:String):Void
  if(actual!=expected)fail(message+': expected '+Std.string(expected)+', got '+Std.string(actual));
 static function hash(bytes:Bytes):String return Sha256.make(bytes).toHex().toLowerCase();
 static function write(path:String,content:String):Void {
  var folder=Path.directory(path); if(folder!=''&&!FileSystem.exists(folder))FileSystem.createDirectory(folder);
  File.saveContent(path,content);
 }
 static function replaceIndex(binding:Dynamic,index:Dynamic):Void {
  var bytes=Bytes.ofString(SourceLimeAssetIdentity.serialize(cast index));
  var path=Std.string(Reflect.field(binding,'indexPath'));
  File.saveBytes(path,bytes);
  var digest=hash(bytes);
  Reflect.setField(binding,'indexSha256',digest);
  for(file in (cast Reflect.field(binding,'files'):Array<Dynamic>))
   if(file.path==path) file.sha256=digest;
 }
 static function project(sharedName:String,lazyName:String):String return '<project>'
  + '<library name="'+sharedName+'" preload="true" embed="false" />'
  + '<library name="'+lazyName+'" preload="false" embed="false" />'
  + '<assets path="assets/payload" rename="assets/warm" library="'+sharedName+'">'
  + '<asset path="warm.txt" rename="warm.txt" id="shared-id" type="text" embed="false" />'
  + '<asset path="font.otf" rename="font.otf" id="font-id" type="font" embed="false" />'
  + '<asset path="pixel.png" rename="pixel.png" id="image-id" type="image" embed="false" />'
  + '</assets>'
  + '<assets path="assets/payload" rename="assets/lazy" library="'+lazyName+'">'
  + '<asset path="lazy.txt" rename="lazy.txt" id="shared-id" type="text" embed="false" />'
  + '</assets></project>';
 static function scriptValue(facade:Dynamic, expression:String):Dynamic {
  var interp=new Interp(); interp.variables.set('Assets',facade);
  var parser=new Parser();
  return interp.execute(parser.parseString(expression));
 }
 static function main():Void {
  var libraryToken='owner-lifecycle-'+Std.string(Std.int(Sys.time()*100000));
  var sharedName=libraryToken+'-shared'; var lazyName=libraryToken+'-lazy';
  var source='source';
  for(ownerName in ['owner-alpha','owner-beta']) {
   write(source+'/'+ownerName+'/Project.xml',project(sharedName,lazyName));
   write(source+'/'+ownerName+'/source/psychlua/Marker.hx','class Marker {}\n');
   write(source+'/'+ownerName+'/assets/payload/warm.txt',ownerName+' warm original');
   write(source+'/'+ownerName+'/assets/payload/font.otf',ownerName+' fixture font bytes');
   write(source+'/'+ownerName+'/assets/payload/pixel.png',ownerName+' fixture image bytes');
   write(source+'/'+ownerName+'/assets/payload/lazy.txt',ownerName+' lazy original');
  }
  var snapshot=ImportSourceSnapshot.capture(source,'cache','Psych Engine','library-lifecycle-test',
   {workerCount:1});
  check(snapshot.complete && snapshot.status=='complete','source snapshot must be receipt-complete: '+snapshot.error);
  var content=snapshot.snapshotRoot+'/content';
  var build:PsychAssetProfileBuild={target:'html5',command:'',flags:[],values:[],flagsComplete:true};
  var bindings:Map<String,Dynamic>=new Map();
  function prepare(ownerName:String):Dynamic {
   var profile=PsychAssetProfile.resolveRetained(content,snapshot.snapshotId,ownerName,
    'Psych Engine',ownerName,build);
   check(profile.provenance=='receipt-bound'&&profile.complete&&profile.librariesComplete,
    ownerName+' Project profile was not fully resolved: '+profile.diagnostics.join('\n'));
   var events:Array<Dynamic>=[];
   var walk=PsychAssetProfile.walkMappedFiles(profile,content,function(event) {
    var destination='assets/imported_mods/'+ownerName+'/'+event.ownerRelative;
    var bytes=File.getBytes(event.sourcePath);
    FileSystem.createDirectory(Path.directory(destination));
    File.saveBytes(destination,bytes);
    events.push({event:event,ownerRelative:event.ownerRelative});
   });
   check(walk.status=='complete'&&walk.files==4,ownerName+' mapped walk incomplete: '+walk.diagnostics);
   var owner='assets/imported_mods/'+ownerName;
   var publication=SourceLimeAssetIdentity.preparePublication(profile,owner,'Psych Engine','package',
    events,[],false,true,true);
   check(!publication.failed,ownerName+' identity publication failed: '+publication.diagnostics.join('\n'));
   check(publication.index.version==2&&publication.index.loadProfileComplete
    &&publication.index.loadTarget=='html5',ownerName+' did not publish a complete HTML5 load profile');
   FileSystem.createDirectory(Path.directory(publication.path));
   File.saveContent(publication.path,publication.content);
   var files:Array<Dynamic>=[{path:publication.path,sha256:hash(File.getBytes(publication.path))}];
   for(entry in publication.index.entries) {
    var file=owner+'/'+entry.ownerRelative;
    files.push({path:file,sha256:hash(File.getBytes(file))});
   }
   var binding:Dynamic={generation:1,revision:1,transactionId:'tx-'+ownerName,owner:owner,
    engine:'Psych Engine',scope:'package',namespace:ownerName,snapshotId:snapshot.snapshotId,
    rootRelative:ownerName,projectSha256:profile.projectSha256,indexPath:publication.path,
    indexSha256:hash(File.getBytes(publication.path)),indexSize:null,files:files};
   bindings.set(owner+'|Psych Engine|package',binding);
   return {owner:owner,profile:profile,index:publication.index,files:files};
  }
  var alpha=prepare('owner-alpha');
  var beta=prepare('owner-beta');
  ImportRefreshManager.bindings=new Map();
  ImportRefreshManager.generation=1; ImportRefreshManager.revision=1;
  var limeAlpha=PsychOwnerLimeAssets.create(alpha.owner);
  var openAlpha=PsychOwnerOpenFlAssets.create(alpha.owner);
  var pendingLimeCache:LimeAssetCache=cast Reflect.field(limeAlpha,'cache');
  var pendingOpenFlCache:OpenFlAssetCache=cast Reflect.field(openAlpha,'cache');
  var qualifiedFontId=sharedName+':font-id';
  var hostLimeFont=new LimeFont('host sentinel');
  var hostOpenFlFont=new OpenFlFont('host sentinel');
  var pendingOwnerLimeFont=new LimeFont('pending owner sentinel');
  var pendingOwnerOpenFlFont=new OpenFlFont('pending owner sentinel');
  LimeAssets.cache.font.set(qualifiedFontId,hostLimeFont);
  var hostOpenFlFonts:Map<String,OpenFlFont>=cast Reflect.field(OpenFlAssets.cache,'font');
  hostOpenFlFonts.set(qualifiedFontId,hostOpenFlFont);
  pendingLimeCache.font.set(qualifiedFontId,pendingOwnerLimeFont);
  pendingOpenFlCache.setFont(qualifiedFontId,pendingOwnerOpenFlFont);
  check(pendingLimeCache!=LimeAssets.cache&&pendingOpenFlCache!=OpenFlAssets.cache,
   'a pending owner facade must never capture either process-global cache');

  ImportRefreshManager.bindings=bindings;
  ImportRefreshManager.generation=2; ImportRefreshManager.revision=2;
  var alphaIdentity=RuntimeOwnerAssetIdentity.acquire(alpha.owner,'Psych Engine','package');
  var betaIdentity=RuntimeOwnerAssetIdentity.acquire(beta.owner,'Psych Engine','package');
  check(alphaIdentity.bindingState=='ready'&&betaIdentity.bindingState=='ready',
   'both actual sidecars must validate against the committed file bindings');
  check(alphaIdentity.indexVersion==2&&alphaIdentity.loadProfileComplete&&alphaIdentity.loadTarget=='html5',
   'runtime identity did not retain the v2 load contract');

  var initialLimeRead=Reflect.callMethod(limeAlpha,Reflect.field(limeAlpha,'getFont'),[qualifiedFontId]);
  var initialOpenFlRead=Reflect.callMethod(openAlpha,Reflect.field(openAlpha,'getFont'),[qualifiedFontId]);
  check(initialLimeRead!=hostLimeFont&&initialLimeRead!=pendingOwnerLimeFont
   &&initialOpenFlRead!=hostOpenFlFont&&initialOpenFlRead!=pendingOwnerOpenFlFont,
   'a facade created before publication must read the later ready owner, not a same-ID pending or host cache entry');
  check(LimeAssets.cache.font.get(qualifiedFontId)==hostLimeFont
   &&hostOpenFlFonts.get(qualifiedFontId)==hostOpenFlFont,
   'late-bound owner reads leave both host cache sentinels untouched');
  var ownerLimeFont=new LimeFont('owner sentinel');
  var ownerOpenFlFont=new OpenFlFont('owner sentinel');
  pendingLimeCache.font.set(qualifiedFontId,ownerLimeFont);
  pendingOpenFlCache.setFont(qualifiedFontId,ownerOpenFlFont);
  var loadedLime:Future<LimeFont>=cast Reflect.callMethod(limeAlpha,
   Reflect.field(limeAlpha,'loadFont'),[qualifiedFontId]);
  var loadedOpenFl:Future<OpenFlFont>=cast Reflect.callMethod(openAlpha,
   Reflect.field(openAlpha,'loadFont'),[qualifiedFontId]);
  check(loadedLime.isComplete&&loadedLime.value==ownerLimeFont
   &&loadedOpenFl.isComplete&&loadedOpenFl.value==ownerOpenFlFont,
   'sync get and async load cache hits use the stable owner cache after publication');
  check(pendingLimeCache==PsychOwnerAssetLibraryCache.limeAssetCache(alphaIdentity)
   &&pendingOpenFlCache==PsychOwnerAssetLibraryCache.openFlAssetCache(alphaIdentity),
   'the cache objects exposed before publication rebind to the verified owner identity');

  var hostBefore:Dynamic=LimeAssets.getLibrary(sharedName);
  check(hostBefore==null,'unique fixture library name unexpectedly exists globally');
  var hostOpenFl=new openfl.utils.AssetLibrary();
  OpenFlAssets.registerLibrary(sharedName,hostOpenFl);
  var limeBeta=PsychOwnerLimeAssets.create(beta.owner);
  var alphaLimeCache:LimeAssetCache=cast Reflect.field(limeAlpha,'cache');
  var betaLimeCache:LimeAssetCache=cast Reflect.field(limeBeta,'cache');
  var alphaOpenFlCache:OpenFlAssetCache=cast Reflect.field(openAlpha,'cache');
  check(alphaLimeCache!=LimeAssets.cache&&betaLimeCache!=LimeAssets.cache
   &&alphaOpenFlCache!=OpenFlAssets.cache,
   'selected-owner facades expose private Lime/OpenFL cache objects');
  check(alphaLimeCache!=betaLimeCache&&alphaOpenFlCache!=Reflect.field(
   PsychOwnerOpenFlAssets.create(beta.owner),'cache'),
   'separate owners must not share facade caches');

  var qualifiedCacheId=sharedName+':cache-sentinel';
  var ownerAudio:Dynamic={owner:'alpha'};
  var hostAudio:Dynamic={owner:'host'};
  var ownerSound:Dynamic={owner:'alpha-sound'};
  alphaLimeCache.audio.set(qualifiedCacheId,cast ownerAudio);
  LimeAssets.cache.audio.set(qualifiedCacheId,cast hostAudio);
  alphaOpenFlCache.setSound(qualifiedCacheId,cast ownerSound);
  check(alphaOpenFlCache.removeSound(qualifiedCacheId),
   'OpenFL owner cache removes its own sound entry');
  check(!alphaLimeCache.audio.exists(qualifiedCacheId),
   'OpenFL owner sound removal mirrors the same ID into its Lime owner cache');
  check(LimeAssets.cache.audio.get(qualifiedCacheId)==hostAudio,
   'OpenFL owner cache removal leaves a same-ID host Lime cache entry untouched');

  var ownerImageId=sharedName+':image-sentinel';
  var ownerImage:Dynamic={owner:'alpha-image'};
  var hostImage:Dynamic={owner:'host-image'};
  alphaLimeCache.image.set(ownerImageId,cast ownerImage);
  LimeAssets.cache.image.set(ownerImageId,cast hostImage);
  alphaOpenFlCache.setBitmapData(ownerImageId,cast {owner:'bitmap'});
  check(alphaOpenFlCache.removeBitmapData(ownerImageId),
   'OpenFL owner cache removes its own bitmap entry');
  check(!alphaLimeCache.image.exists(ownerImageId)
   &&LimeAssets.cache.image.get(ownerImageId)==hostImage,
   'bitmap removal clears only the matching owner Lime cache entry');

  var ownerFontId=sharedName+':font-sentinel';
  var ownerFont:Dynamic={owner:'alpha-font'};
  var hostFont:Dynamic={owner:'host-font'};
  alphaLimeCache.font.set(ownerFontId,ownerFont);
  LimeAssets.cache.font.set(ownerFontId,hostFont);
  alphaOpenFlCache.setFont(ownerFontId,cast {owner:'openfl-font'});
  check(alphaOpenFlCache.removeFont(ownerFontId),
   'OpenFL owner cache removes its own font entry');
  check(!alphaLimeCache.font.exists(ownerFontId)
   &&LimeAssets.cache.font.get(ownerFontId)==hostFont,
   'font removal clears only the matching owner Lime cache entry');

  var prefixKeep:Dynamic={owner:'alpha-keep'};
  alphaLimeCache.audio.set(sharedName+':prefix-remove',cast ownerAudio);
  alphaLimeCache.audio.set(lazyName+':prefix-keep',cast prefixKeep);
  alphaOpenFlCache.setSound(sharedName+':prefix-remove',cast ownerSound);
  alphaOpenFlCache.setSound(lazyName+':prefix-keep',cast prefixKeep);
  alphaOpenFlCache.clear(sharedName+':');
  check(!alphaOpenFlCache.hasSound(sharedName+':prefix-remove')
   &&!alphaLimeCache.audio.exists(sharedName+':prefix-remove'),
   'OpenFL prefix clear uses owner-scoped removal hooks');
  check(alphaOpenFlCache.hasSound(lazyName+':prefix-keep')
   &&alphaLimeCache.audio.get(lazyName+':prefix-keep')==prefixKeep,
   'prefix clear leaves another library namespace in the same owner intact');
  alphaLimeCache.enabled=false;
  check(LimeAssets.cache.enabled,'owner cache enabled flag does not alter host cache state');
  alphaLimeCache.enabled=true;
  check(alphaLimeCache==PsychOwnerAssetLibraryCache.limeAssetCache(alphaIdentity)
   &&alphaOpenFlCache==PsychOwnerAssetLibraryCache.openFlAssetCache(alphaIdentity),
   'facade cache properties expose the cache objects associated with their owner identity');
  eq(Reflect.callMethod(limeAlpha,Reflect.field(limeAlpha,'getLibrary'),[sharedName])
   ==Reflect.callMethod(limeAlpha,Reflect.field(limeAlpha,'getLibrary'),[sharedName]),true,
   'repeated Lime getLibrary must reuse one local view');
  var alphaView:AssetLibrary=cast Reflect.callMethod(limeAlpha,Reflect.field(limeAlpha,'getLibrary'),[sharedName]);
  var lazyView:AssetLibrary=cast Reflect.callMethod(limeAlpha,Reflect.field(limeAlpha,'getLibrary'),[lazyName]);
  var betaView:AssetLibrary=cast Reflect.callMethod(limeBeta,Reflect.field(limeBeta,'getLibrary'),[sharedName]);
  var openView:Dynamic=Reflect.callMethod(openAlpha,Reflect.field(openAlpha,'getLibrary'),[sharedName]);
  var alphaEntry=PsychOwnerAssetLibraryCache.entries.get(alpha.owner.toLowerCase()+'|Psych Engine|package|'+sharedName);
  var lazyEntry=PsychOwnerAssetLibraryCache.entries.get(alpha.owner.toLowerCase()+'|Psych Engine|package|'+lazyName);
  check(alphaView!=betaView,'same library name in two owners must not share a library instance');
  check(Reflect.field(openView,'__proxy')==alphaView,'OpenFL owner library must wrap the same Lime view');
  check(alphaEntry!=null&&lazyEntry!=null,'owner libraries retain their actual Lime delegates');
  eq(alphaEntry.sourceLibrary.preload.get('shared-id'),true,'HTML5 named-library preload=true must reach Lime');
  eq(lazyEntry.sourceLibrary.preload.get('shared-id'),false,'HTML5 named-library preload=false must reach Lime');
  eq(Reflect.callMethod(limeAlpha,Reflect.field(limeAlpha,'hasLibrary'),[sharedName]),true,
   'receipt-owned named library is visible through the owner facade');

  var alphaFuture:Dynamic=Reflect.callMethod(limeAlpha,Reflect.field(limeAlpha,'loadLibrary'),[sharedName]);
  var repeatedAlphaFuture:Dynamic=Reflect.callMethod(limeAlpha,Reflect.field(limeAlpha,'loadLibrary'),[sharedName]);
  check(alphaFuture==repeatedAlphaFuture,'same-owner repeated loadLibrary must share the in-flight/completed Future');
  var betaFuture:Dynamic=Reflect.callMethod(limeBeta,Reflect.field(limeBeta,'loadLibrary'),[sharedName]);
  var openFuture:Dynamic=Reflect.callMethod(openAlpha,Reflect.field(openAlpha,'loadLibrary'),[sharedName]);
  var repeatedOpenFuture:Dynamic=Reflect.callMethod(openAlpha,Reflect.field(openAlpha,'loadLibrary'),[sharedName]);
  check(openFuture==repeatedOpenFuture,'OpenFL repeated load must share its Future');
  #if !lime_cffi
  // Lime's synchronous file reader returns null on eval without CFFI. Seed
  // the actual AssetLibrary cache to verify both facades preserve its values;
  // the private native probe exercises real file loading and Future completion.
  alphaEntry.sourceLibrary.cachedText.set('shared-id','owner-alpha warm original');
  PsychOwnerAssetLibraryCache.entries.get(beta.owner.toLowerCase()+'|Psych Engine|package|'+sharedName)
   .sourceLibrary.cachedText.set('shared-id','owner-beta warm original');
  #end
  eq(Reflect.callMethod(limeAlpha,Reflect.field(limeAlpha,'getText'),[sharedName+':shared-id']),
   'owner-alpha warm original','qualified facade lookup resolves the selected owner');
  eq(Reflect.callMethod(limeBeta,Reflect.field(limeBeta,'getText'),[sharedName+':shared-id']),
   'owner-beta warm original','the second owner resolves its own same-named ID');
  eq(scriptValue(limeAlpha,'Assets.getText("'+sharedName+':shared-id")'),'owner-alpha warm original',
   'HScript facade call stays in its selected owner');
  eq(scriptValue(openAlpha,'Assets.getText("'+sharedName+':shared-id")'),'owner-alpha warm original',
   'HScript OpenFL facade call stays in its selected owner');
  var warmPath=alpha.owner+'/'+alpha.index.entries[0].ownerRelative;
  if(alpha.index.entries[0].library!='shared') {
   for(entry in alpha.index.entries) if(entry.library=='shared') warmPath=alpha.owner+'/'+entry.ownerRelative;
  }
  var originalWarmBytes=File.getBytes(warmPath);
  try {
   File.saveContent(warmPath,'owner-alpha warm changed on disk');
   eq(Reflect.callMethod(limeAlpha,Reflect.field(limeAlpha,'getText'),[sharedName+':shared-id']),
    'owner-alpha warm original','preloaded ordinary facade reads reuse Lime typed cache');
   eq(Reflect.callMethod(openAlpha,Reflect.field(openAlpha,'getText'),[sharedName+':shared-id']),
    'owner-alpha warm original','OpenFL ordinary facade reads reuse the same typed cache');
  } catch(error:Dynamic) {
   File.saveBytes(warmPath,originalWarmBytes);
   throw error;
  }
  File.saveBytes(warmPath,originalWarmBytes);
  eq(LimeAssets.getLibrary(sharedName),hostOpenFl,'owner-local load did not replace Lime global library');
  eq(OpenFlAssets.getLibrary(sharedName),hostOpenFl,'owner-local load did not replace OpenFL global library');

  Reflect.callMethod(limeAlpha,Reflect.field(limeAlpha,'unloadLibrary'),[sharedName]);
  var reloadedView:AssetLibrary=cast Reflect.callMethod(limeAlpha,Reflect.field(limeAlpha,'getLibrary'),[sharedName]);
  check(reloadedView!=alphaView,'owner unload evicts only its cached library view');
  eq(reloadedView.getPath('shared-id'),warmPath,'reloaded library keeps the exact owner file path');
  var reloadedEntry=PsychOwnerAssetLibraryCache.entries.get(alpha.owner.toLowerCase()+'|Psych Engine|package|'+sharedName);
  reloadedEntry.sourceLibrary.cachedText.set('shared-id','owner-alpha warm original');
  check(Reflect.callMethod(limeBeta,Reflect.field(limeBeta,'getLibrary'),[sharedName])==betaView,
   'unloading alpha does not evict beta');

  var epochFutureBefore:Dynamic=Reflect.callMethod(limeAlpha,Reflect.field(limeAlpha,'loadLibrary'),[sharedName]);
  ImportRefreshManager.revision=2;
  var sameEpochIdentity=RuntimeOwnerAssetIdentity.acquire(alpha.owner,'Psych Engine','package');
  check(sameEpochIdentity==alphaIdentity,'unrelated global epoch change preserves the exact owner proof');
  var sameEpochView:AssetLibrary=cast Reflect.callMethod(limeAlpha,Reflect.field(limeAlpha,'getLibrary'),[sharedName]);
  var epochFutureAfter:Dynamic=Reflect.callMethod(limeAlpha,Reflect.field(limeAlpha,'loadLibrary'),[sharedName]);
  check(sameEpochView==reloadedView,'unrelated global epoch change preserves the local library view');
  check(epochFutureAfter==epochFutureBefore,'unrelated global epoch change preserves the local load Future');
  eq(Reflect.callMethod(limeAlpha,Reflect.field(limeAlpha,'getText'),[sharedName+':shared-id']),
   'owner-alpha warm original','unrelated owner publication leaves this owner cache readable');

  var alphaBinding:Dynamic=bindings.get(alpha.owner+'|Psych Engine|package');
  var unknownIndex:Dynamic=haxe.Json.parse(SourceLimeAssetIdentity.serialize(alpha.index));
  Reflect.setField(unknownIndex,'loadTarget',null);
  Reflect.setField(unknownIndex,'loadProfileComplete',false);
  for(profile in (cast Reflect.field(unknownIndex,'libraryLoadProfiles'):Array<Dynamic>)) {
   profile.state='unknown';
   profile.diagnostic='fixture target does not establish a standard file-backed library';
  }
  replaceIndex(alphaBinding,unknownIndex);
  ImportRefreshManager.revision=3;
  var unknownIdentity=RuntimeOwnerAssetIdentity.acquire(alpha.owner,'Psych Engine','package');
  check(unknownIdentity.bindingState=='ready'&&unknownIdentity.indexVersion==2
   &&!unknownIdentity.loadProfileComplete&&unknownIdentity.loadTarget==null,
   'identity-valid v2 metadata with unknown load semantics remains available');
  PsychOwnerAssetLibraryCache.limeAssetCache(unknownIdentity);
  PsychOwnerAssetLibraryCache.openFlAssetCache(unknownIdentity);
  eq(Reflect.callMethod(limeAlpha,Reflect.field(limeAlpha,'getText'),[sharedName+':shared-id']),
   'owner-alpha warm original','unknown v2 load metadata still permits receipt-bound physical text reads');
  eq(Reflect.callMethod(openAlpha,Reflect.field(openAlpha,'getText'),[sharedName+':shared-id']),
   'owner-alpha warm original','unknown v2 metadata stays selected-owner scoped through OpenFL');
  var unknownLibraryFailed=false;
  try Reflect.callMethod(limeAlpha,Reflect.field(limeAlpha,'getLibrary'),[sharedName])
  catch (_:Dynamic) unknownLibraryFailed=true;
  check(unknownLibraryFailed,'unknown v2 load semantics do not construct a guessed Lime library');
  var unknownLoadError:Dynamic=null;
  Reflect.callMethod(limeAlpha,Reflect.field(limeAlpha,'loadLibrary'),[sharedName])
   .onError(function(error:Dynamic) unknownLoadError=error);
  check(unknownLoadError!=null,'explicit library loading reports unknown v2 load metadata');
  var fontId=sharedName+':font-id';
  var ownerFont:Dynamic={owner:'alpha-font-cache'};
  alphaLimeCache.font.set(fontId,ownerFont);
  alphaOpenFlCache.setFont(fontId,cast ownerFont);
  eq(Reflect.callMethod(limeAlpha,Reflect.field(limeAlpha,'getFont'),[fontId]),ownerFont,
   'unknown v2 indexed reads consult the selected owner Lime cache before library resolution');
  eq(Reflect.callMethod(openAlpha,Reflect.field(openAlpha,'getFont'),[fontId]),ownerFont,
   'unknown v2 OpenFL reads consult the selected owner cache before library resolution');
  var imageId=sharedName+':image-id';
  var unknownBitmap:Dynamic=Reflect.callMethod(openAlpha,
   Reflect.field(openAlpha,'getBitmapData'),[imageId]);
  check(unknownBitmap!=null&&alphaOpenFlCache.hasBitmapData(imageId),
   'unknown v2 receipt entries decode through the selected owner cache');
  check(Reflect.callMethod(openAlpha,Reflect.field(openAlpha,'getBitmapData'),[imageId])==unknownBitmap,
   'the selected owner OpenFL cache serves its image before unsupported library resolution');
  check(!OpenFlAssets.cache.hasBitmapData(imageId),
   'unknown v2 image reads do not populate the same-named host cache');

  var legacyIndex:Dynamic=haxe.Json.parse(SourceLimeAssetIdentity.serialize(cast unknownIndex));
  Reflect.setField(legacyIndex,'version',1);
  Reflect.deleteField(legacyIndex,'loadTarget');
  Reflect.deleteField(legacyIndex,'loadProfileComplete');
  Reflect.deleteField(legacyIndex,'libraryLoadProfiles');
  for(entry in (cast Reflect.field(legacyIndex,'entries'):Array<Dynamic>))
   Reflect.deleteField(entry,'preloadState');
  replaceIndex(alphaBinding,legacyIndex);
  ImportRefreshManager.revision=4;
  var legacyIdentity=RuntimeOwnerAssetIdentity.acquire(alpha.owner,'Psych Engine','package');
  check(legacyIdentity.bindingState=='ready'&&legacyIdentity.indexVersion==1,
   'v1 identity sidecars remain valid for physical getters');
  PsychOwnerAssetLibraryCache.limeAssetCache(legacyIdentity);
  PsychOwnerAssetLibraryCache.openFlAssetCache(legacyIdentity);
  eq(Reflect.callMethod(limeAlpha,Reflect.field(limeAlpha,'getText'),[sharedName+':shared-id']),
   'owner-alpha warm original','v1 identity entries fall back to receipt-bound physical reads');
  eq(Reflect.callMethod(openAlpha,Reflect.field(openAlpha,'getText'),[sharedName+':shared-id']),
   'owner-alpha warm original','v1 OpenFL identity entries keep their physical owner path');
  var legacyFont:Dynamic={owner:'alpha-v1-font-cache'};
  alphaLimeCache.font.set(fontId,legacyFont);
  alphaOpenFlCache.setFont(fontId,cast legacyFont);
  eq(Reflect.callMethod(limeAlpha,Reflect.field(limeAlpha,'getFont'),[fontId]),legacyFont,
   'v1 Lime reads reuse the facade cache without needing a library view');
  eq(Reflect.callMethod(openAlpha,Reflect.field(openAlpha,'getFont'),[fontId]),legacyFont,
   'v1 OpenFL reads reuse the facade cache without needing a library view');
  var legacyBitmap:Dynamic=Reflect.callMethod(openAlpha,
   Reflect.field(openAlpha,'getBitmapData'),[imageId]);
  check(legacyBitmap!=null,
   'v1 physical image read returns a decoded owner bitmap');
  check(alphaOpenFlCache.hasBitmapData(imageId),
   'v1 physical image reads repopulate the owner cache after proof replacement');
  check(Reflect.callMethod(openAlpha,Reflect.field(openAlpha,'getBitmapData'),[imageId])==legacyBitmap,
   'v1 OpenFL image reads reuse the receipt-scoped cache entry');
  var legacyLoadError:Dynamic=null;
  Reflect.callMethod(openAlpha,Reflect.field(openAlpha,'loadLibrary'),[sharedName])
   .onError(function(error:Dynamic) legacyLoadError=error);
  check(legacyLoadError!=null,'v1 identity compatibility does not invent library load metadata');

  alpha.index.snapshotId=StringTools.lpad('','d',64);
  var changedSidecar=Bytes.ofString(SourceLimeAssetIdentity.serialize(alpha.index));
  var sidecarPath=Std.string(alphaBinding.indexPath);
  File.saveBytes(sidecarPath,changedSidecar);
  var changedHash=hash(changedSidecar);
  Reflect.setField(alphaBinding,'snapshotId',alpha.index.snapshotId);
  Reflect.setField(alphaBinding,'indexSha256',changedHash);
  Reflect.setField(alphaBinding,'transactionId','tx-owner-alpha-refreshed');
  for(file in (cast Reflect.field(alphaBinding,'files'):Array<Dynamic>))
   if(file.path==sidecarPath) file.sha256=changedHash;
  ImportRefreshManager.revision=5;
  var changedProofIdentity=RuntimeOwnerAssetIdentity.acquire(alpha.owner,'Psych Engine','package');
  check(changedProofIdentity!=sameEpochIdentity&&changedProofIdentity.bindingState=='ready',
   'a new owner receipt proof is revalidated as a new ready identity');
  check(Reflect.field(limeAlpha,'cache')==alphaLimeCache
   &&Reflect.field(openAlpha,'cache')==alphaOpenFlCache,
   'long-lived facade cache properties keep the stable owner cache objects after proof replacement');
  check(PsychOwnerAssetLibraryCache.limeAssetCache(changedProofIdentity)==alphaLimeCache
   &&PsychOwnerAssetLibraryCache.openFlAssetCache(changedProofIdentity)==alphaOpenFlCache,
   'proof replacement clears and rebinds cache objects instead of leaving a stale cache alias');
  var changedProofView:AssetLibrary=cast Reflect.callMethod(limeAlpha,Reflect.field(limeAlpha,'getLibrary'),[sharedName]);
  check(changedProofView!=reloadedView,'changed owner proof creates a fresh library view');
  var staleProofFailed=false;
  try reloadedView.getText('shared-id') catch (_:Dynamic) staleProofFailed=true;
  check(staleProofFailed,'old Lime view rejects sync reads after its owner proof changes');

  var betaBeforeRelease:AssetLibrary=cast Reflect.callMethod(limeBeta,Reflect.field(limeBeta,'getLibrary'),[sharedName]);
  PsychOwnerAssetPath.releaseOwner(alpha.owner);
  var betaAfterRelease:AssetLibrary=cast Reflect.callMethod(limeBeta,Reflect.field(limeBeta,'getLibrary'),[sharedName]);
  check(betaAfterRelease==betaBeforeRelease,'owner release leaves the other owner cache intact');
  var staleReleaseFailed=false;
  try changedProofView.getText('shared-id') catch (_:Dynamic) staleReleaseFailed=true;
  check(staleReleaseFailed,'owner release invalidates its retained Lime handle');
  eq(LimeAssets.getLibrary(sharedName),hostOpenFl,'owner release still cannot remove the same-named host library');
  eq(OpenFlAssets.getLibrary(sharedName),hostOpenFl,'owner release still cannot remove the OpenFL host library');

  LimeAssets.removeLibrary(sharedName);
 }
}'''


STUBS = {
    "ImportRefreshManager.hx": '''package;
class ImportRefreshManager {
 public static var generation:Int=1;
 public static var revision:Int=1;
 public static var bindings:Map<String,Dynamic>=new Map();
 public static function availabilityRevision():Int return revision;
 public static function ownerAssetIndexBinding(owner:String,engine:String,scope:String):Dynamic
  return bindings.get(owner+'|'+engine+'|'+scope);
}''',
    "CompatScriptManifest.hx": '''package;
class CompatScriptManifest { public static inline var ROOT_PREFIX:String='assets/imported_mods'; }''',
        "FNFAssets.hx": '''package;
import haxe.io.Bytes;
import haxe.io.Path;
import openfl.display.BitmapData;
import openfl.media.Sound;
import sys.FileSystem;
import sys.io.File;
class FNFAssets {
 public static function resolveCaseInsensitivePath(path:String):String
  return path!=null&&FileSystem.exists(path)?Path.normalize(path):null;
 public static function exists(path:String):Bool return path!=null&&FileSystem.exists(path);
 public static function getText(path:String):String return File.getContent(path);
 public static function getBytes(path:String):Bytes return File.getBytes(path);
 public static function getBitmapData(path:String,?useCache:Bool=true):BitmapData
  return new BitmapData(1,1,true,0xFF123456);
 public static function getSound(path:String,?useCache:Bool=true):Sound return null;
}''',
}


class PsychOwnerAssetLibraryLifecycleTest(unittest.TestCase):
    def test_verified_library_font_methods_decode_bytes_instead_of_retaining_managed_paths(self):
        source = (ROOT / "source/PsychOwnerAssetLibraryCache.hx").read_text(encoding="utf-8")
        start = source.index("private class PsychOwnerFileAssetLibrary")
        end = source.index("/** OpenFL's standard removal methods", start)
        font_library = source[start:end]
        self.assertIn("class PsychOwnerFileAssetLibrary extends AssetLibrary", font_library)
        self.assertIn("__fromManifest(manifest)", font_library)
        self.assertIn("LimeFont.fromBytes(getBytes(id))", font_library)
        self.assertIn("LimeFont.loadFromBytes(bytes)", font_library)
        self.assertIn('Future.withError("")', font_library)
        getter = font_library[font_library.index("public override function getFont"):
                              font_library.index("public override function loadFont")]
        self.assertNotIn("cachedFonts.set", getter,
                         "Lime getFont must not cache a non-preloaded decode")
        self.assertNotIn("Font.fromFile", font_library)
        self.assertNotIn("Font.loadFromFile", font_library)

    @unittest.skipUnless(HAXE.is_file(), "portable Haxe interpreter is unavailable")
    def test_receipt_bound_lime_openfl_lifecycle_and_owner_isolation(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(FIXTURE, encoding="utf-8", newline="\n")
            for name, content in STUBS.items():
                path = work / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
            env = dict(os.environ)
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
            env["PATH"] = os.pathsep.join(
                [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
            )
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "-lib", "lime", "-lib", "openfl", "-lib", "hscript", "-lib", "tjson",
                 "--main", "Main", "--interp"],
                cwd=work, env=env, capture_output=True, text=True, timeout=90,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
