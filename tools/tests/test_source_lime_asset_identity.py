"""Receipt-owned Lime identity sidecars preserve IDs and library boundaries."""
from haxe_test_support import HAXE_COMMAND, TEST_TMP

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


FIXTURE = r'''import PsychAssetProfile.PsychAssetProfileMappedFile;
import SourceLimeAssetIdentity;
import SourceLimeAssetIdentity.SourceLimeAssetIdentityEntry;
import SourceLimeAssetIdentity.SourceLimeAssetIdentityIndex;
import SourceLimeAssetIdentity.SourceLimeAssetIdentityKey;
import haxe.io.Bytes;
import sys.io.File;
using StringTools;

class Main {
 static function fail(message:String):Void throw message;
 static function check(value:Bool,message:String):Void if(!value)fail(message);
 static function eq(actual:Dynamic,expected:Dynamic,message:String):Void
  if(actual!=expected)fail(message+': expected '+Std.string(expected)+', got '+Std.string(actual));
 static function main():Void {
  var parsed=SourceLimeAssetIdentity.parseQualifiedId('named:portrait:small');
  eq(parsed.library,'named','first colon partitions library');
  eq(parsed.id,'portrait:small','remaining colons stay in the ID');
  eq(SourceLimeAssetIdentity.parseQualifiedId('plain').library,'default','unqualified symbol uses default');
  eq(SourceLimeAssetIdentity.canonicalLibrary(''),'default','empty library uses default');
  eq(SourceLimeAssetIdentity.canonicalLibrary('MiXeD'),'MiXeD','library names remain case-sensitive');
  check(SourceLimeAssetIdentity.typeMatches('SOUND','MUSIC'),'Lime native sound/music compatibility');
  check(SourceLimeAssetIdentity.typeMatches('BINARY','TEXT'),'native binary satisfies text lookup');
  check(SourceLimeAssetIdentity.typeMatches('IMAGE','BINARY'),'binary lookup accepts any native type');
  check(!SourceLimeAssetIdentity.typeMatches('TEXT','IMAGE'),'unrelated native types do not match');
  eq(SourceLimeAssetIdentity.inferType(null,'x.png',4),'IMAGE','Lime image inference');
  eq(SourceLimeAssetIdentity.inferType(null,'x.mp2',4),'MUSIC','Lime mp2 inference');
  eq(SourceLimeAssetIdentity.inferType(null,'x.ogg',1048576),'SOUND','audio threshold is strict greater-than one MiB');
  eq(SourceLimeAssetIdentity.inferType(null,'x.ogg',1048577),'MUSIC','large ogg infers music');
  eq(SourceLimeAssetIdentity.inferType(null,'x.m4a',1048577),'MUSIC','large m4a infers music');
  eq(SourceLimeAssetIdentity.inferType(null,'x.bundle',4),'MANIFEST','bundle infers manifest');
  eq(SourceLimeAssetIdentity.inferType(null,'x.custom',4),null,'unavailable build-tool text probe stays unresolved');
  var textProbe='probe.frag';
  File.saveContent(textProbe,StringTools.lpad('','x',64));
  var binaryProbe='probe.dat';
  File.saveBytes(binaryProbe,Bytes.alloc(64));
  var bomProbe='probe-bom.bin';
  var bomBytes=Bytes.alloc(8);
  bomBytes.set(0,0xEF); bomBytes.set(1,0xBB); bomBytes.set(2,0xBF); bomBytes.set(3,0);
  File.saveBytes(bomProbe,bomBytes);
  var shortUtf16Le='short-utf16le.unknown';
  var shortUtf16LeBytes=Bytes.alloc(3);
  shortUtf16LeBytes.set(0,0xFF); shortUtf16LeBytes.set(1,0xFE); shortUtf16LeBytes.set(2,0);
  File.saveBytes(shortUtf16Le,shortUtf16LeBytes);
  var shortUtf16Be='short-utf16be.unknown';
  var shortUtf16BeBytes=Bytes.alloc(3);
  shortUtf16BeBytes.set(0,0xFE); shortUtf16BeBytes.set(1,0xFF); shortUtf16BeBytes.set(2,0);
  File.saveBytes(shortUtf16Be,shortUtf16BeBytes);
  var fullUtf16Le='full-utf16le.unknown';
  var fullUtf16LeBytes=Bytes.alloc(4);
  fullUtf16LeBytes.set(0,0xFF); fullUtf16LeBytes.set(1,0xFE);
  fullUtf16LeBytes.set(2,0); fullUtf16LeBytes.set(3,65);
  File.saveBytes(fullUtf16Le,fullUtf16LeBytes);
  eq(SourceLimeAssetIdentity.inferType(null,'shader.frag',64,textProbe),'TEXT',
    'hxp.System.isText classifies a textual shader from the retained snapshot bytes');
  eq(SourceLimeAssetIdentity.inferType(null,'video.mp4',64,binaryProbe),'BINARY',
    'hxp.System.isText classifies binary unknown extensions instead of leaving supported media unresolved');
  eq(SourceLimeAssetIdentity.inferType(null,'probe.unknown',8,bomProbe),'TEXT',
    'hxp.System.isText honors UTF byte-order marks before the byte ratio');
  eq(SourceLimeAssetIdentity.inferType(null,'short-utf16le.unknown',3,shortUtf16Le),'BINARY',
    'a three-byte UTF-16LE prefix reaches EOF before hxp checks its BOM');
  eq(SourceLimeAssetIdentity.inferType(null,'short-utf16be.unknown',3,shortUtf16Be),'BINARY',
    'a three-byte UTF-16BE prefix reaches EOF before hxp checks its BOM');
  eq(SourceLimeAssetIdentity.inferType(null,'full-utf16le.unknown',4,fullUtf16Le),'TEXT',
    'a fourth byte lets hxp inspect the UTF-16LE BOM before the byte ratio');

  var owner='assets/imported_mods/identity-fixture';
  var projectHash=StringTools.lpad('','a',64);
  var snapshot=StringTools.lpad('','b',64);
  var profile:Dynamic={namespace:'identity-fixture',rootRelative:'nested/root',snapshotId:snapshot,
    projectSha256:projectHash,libraries:[{name:'empty-library',state:'enabled'}],
    candidates:[{library:'alternate',state:'enabled'}]};
  var bytesHash=StringTools.lpad('','c',64);
  function event(id:String,library:String,type:String,target:String,order:Int,?embed:String):Dynamic {
  var mapped='assets/'+target;
  var e:PsychAssetProfileMappedFile={sourcePath:'C:/retained/'+order,sourceRelative:'assets/source-'+order,
    mappedPath:mapped,ownerRelative:target,candidateOrder:order,size:12,sha256:bytesHash,
    type:type,library:library,assetId:id,assetIdOverride:true,embed:embed};
   return {event:e,ownerRelative:target};
  }
  var events:Array<Dynamic>=[
    event('same-id','default','text','data/first.txt',1),
    event('same-id','default','text','data/later.txt',2),
    event('same-id','Alternate','image','images/same.png',3),
    event('mod:🧪','named','text','data/astral.txt',4),
    event('with-conflict','default','binary','data/conflict-a.bin',5),
    event('with-conflict','default','binary','data/conflict-b.bin',5)
  ];
  var publication=SourceLimeAssetIdentity.preparePublication(profile,owner,'Psych Engine','package',
    events,[{library:'default',id:'blocked-id'}],false,true,true);
  check(!publication.failed,publication.diagnostics.join('\n'));
  eq(publication.path,owner+'/.cammie-asset-identities/psych.json','sidecar uses install-relative reserved path');
  var index=publication.index;
  check(!index.complete,'identity ambiguity prevents a complete table claim');
  check(index.librariesComplete,'valid explicit and candidate partitions remain complete');
  check(index.libraries.indexOf('default')>=0 && index.libraries.indexOf('Alternate')>=0
    && index.libraries.indexOf('named')>=0 && index.libraries.indexOf('empty-library')<0
    && index.libraries.indexOf('alternate')<0,
    'only effective asset-library partitions are claimed; native library config is retained separately');
  function find(library:String,id:String):SourceLimeAssetIdentityEntry {
   for(entry in index.entries) if(entry.library==library && entry.id==id)return entry;
   return null;
  }
  eq(find('default','same-id').ownerRelative,'data/later.txt','last declaration wins within one Lime library');
  eq(find('Alternate','same-id').ownerRelative,'images/same.png','same ID in another library stays distinct');
  eq(find('named','mod:🧪').ownerRelative,'data/astral.txt','Unicode ID bytes survive index preparation');
  eq(find('default','blocked-id'),null,'blocked unresolved key is withheld');
  eq(find('default','with-conflict'),null,'equal-order conflicting mappings are withheld');
  var serialized=SourceLimeAssetIdentity.serialize(index);
  var roundTrip:Dynamic=haxe.Json.parse(serialized);
  var validated=SourceLimeAssetIdentity.validate(roundTrip,owner,'Psych Engine','package','identity-fixture');
  check(validated!=null,'serialized sidecar validates against captured identity');
  check(validated.version==2 && !validated.loadProfileComplete && validated.loadTarget==null,
    'identity-only inputs publish v2 with explicit unavailable load metadata');
  check(validated.libraryLoadProfiles.length==validated.libraries.length,
    'every actual Lime namespace has a load-profile record');
  eq(findFrom(validated,'named','mod:🧪').ownerRelative,'data/astral.txt','astral identity survives standard JSON round-trip');
  check(SourceLimeAssetIdentity.validate(roundTrip,owner,'Psych Engine','core','identity-fixture')==null,
    'scope mismatch rejects a copied sidecar');
  check(SourceLimeAssetIdentity.isReservedOwnerPath('.cammie-asset-identities/psych.json'),
    'reserved sidecar destination is recognized');
  check(!SourceLimeAssetIdentity.isReservedOwnerPath('images/.cammie-asset-identities/icon.png'),
    'nested ordinary asset path is not confused with owner sidecar root');

  var loadProfile:Dynamic={namespace:'identity-fixture',rootRelative:'nested/root',snapshotId:snapshot,
    projectSha256:projectHash,buildTarget:'html5',complete:true,librariesComplete:true,
    libraries:[
      {order:0,name:'warm',state:'enabled',sourcePath:'',type:'',typeState:'known',embed:false,
        embedState:'known',preload:true,preloadState:'known',generate:false,generateState:'known',prefix:'',prefixState:'known'},
      {order:1,name:'lazy',state:'enabled',sourcePath:'',type:'',typeState:'known',embed:true,
        embedState:'known',preload:false,preloadState:'known',generate:false,generateState:'known',prefix:'',prefixState:'known'}
    ],candidates:[{library:'warm',state:'enabled'},{library:'lazy',state:'enabled'}]};
  var loadEvents:Array<Dynamic>=[
    event('assets/warm.txt','warm','text','warm/file.txt',10,'false'),
    event('assets/lazy.txt','lazy','text','lazy/file.txt',11,'false')
  ];
  var loadPublication=SourceLimeAssetIdentity.preparePublication(loadProfile,owner,'Psych Engine','package',
    loadEvents,[],false,true,true);
  check(!loadPublication.failed,loadPublication.diagnostics.join('\\n'));
  var loadIndex=loadPublication.index;
  check(loadIndex.loadProfileComplete && loadIndex.loadTarget=='html5',
    'complete retained HTML5 build context publishes a validated file-backed load profile');
  eq(findFrom(loadIndex,'warm','assets/warm.txt').preloadState,'enabled',
    'HTML5 explicit warm library preload applies to nonembedded entries');
  eq(findFrom(loadIndex,'lazy','assets/lazy.txt').preloadState,'disabled',
    'HTML5 explicit false preload keeps nonembedded entries lazy');
  var warmProfile:SourceLimeAssetIdentityLibraryLoadProfile=null;
  for(loadProfileEntry in loadIndex.libraryLoadProfiles)
    if(loadProfileEntry.library=='warm')warmProfile=loadProfileEntry;
  check(warmProfile!=null && warmProfile.projectPreload==true
    && warmProfile.projectEmbedState=='known' && warmProfile.projectEmbed==false,
    'library-level Project settings remain separate from effective asset preload');
  var lazyProfile:SourceLimeAssetIdentityLibraryLoadProfile=null;
  for(loadProfileEntry in loadIndex.libraryLoadProfiles)
    if(loadProfileEntry.library=='lazy')lazyProfile=loadProfileEntry;
  check(lazyProfile!=null && lazyProfile.projectEmbedState=='known' && lazyProfile.projectEmbed==true,
    'sidecar validation accepts explicit Project library embed settings');

  Reflect.deleteField(loadProfile,'buildTarget');
  var unknownTargetPublication=SourceLimeAssetIdentity.preparePublication(loadProfile,owner,
    'Psych Engine','package',loadEvents,[],false,true,true);
  check(!unknownTargetPublication.failed,'missing source target preserves ordinary identity publication');
  check(!unknownTargetPublication.index.loadProfileComplete
    && unknownTargetPublication.index.loadTarget==null,
    'target is never inferred from the runtime host');
  eq(findFrom(unknownTargetPublication.index,'warm','assets/warm.txt').preloadState,'unresolved',
    'target-dependent effective preload stays unresolved when Lime target was not captured');

  Reflect.setField(loadProfile,'buildTarget','html5');
  var loadRoundTrip:Dynamic=haxe.Json.parse(SourceLimeAssetIdentity.serialize(loadIndex));
  var legacy:Dynamic=haxe.Json.parse(SourceLimeAssetIdentity.serialize(loadIndex));
  Reflect.setField(legacy,'version',1);
  Reflect.deleteField(legacy,'loadTarget');
  Reflect.deleteField(legacy,'loadProfileComplete');
  Reflect.deleteField(legacy,'libraryLoadProfiles');
  for(legacyEntry in (cast Reflect.field(legacy,'entries'):Array<Dynamic>))
    Reflect.deleteField(legacyEntry,'preloadState');
  var legacyIndex=SourceLimeAssetIdentity.validate(legacy,owner,'Psych Engine','package','identity-fixture');
  check(legacyIndex!=null && legacyIndex.version==1 && !legacyIndex.loadProfileComplete,
    'v1 identity indexes stay readable with unavailable load semantics');
  eq(findFrom(legacyIndex,'warm','assets/warm.txt').preloadState,'unresolved',
    'v1 entries never acquire guessed preload claims');
  check(SourceLimeAssetIdentity.validate(loadRoundTrip,owner,'Psych Engine','package','identity-fixture')!=null,
    'strict v2 load metadata survives a round trip');
  var smuggledV1:Dynamic=haxe.Json.parse(SourceLimeAssetIdentity.serialize(loadIndex));
  Reflect.setField(smuggledV1,'version',1);
  check(SourceLimeAssetIdentity.validate(smuggledV1,owner,'Psych Engine','package','identity-fixture')==null,
    'v1 cannot claim v2 preload data');
  Reflect.setField(loadRoundTrip,'loadTarget','custom-unverified-host');
  check(SourceLimeAssetIdentity.validate(loadRoundTrip,owner,'Psych Engine','package','identity-fixture')==null,
    'v2 target values must belong to the pinned Lime Platform enum');

  var audioProfile:Dynamic=haxe.Json.parse(haxe.Json.stringify(loadProfile));
  (cast Reflect.field(audioProfile,'libraries'):Array<Dynamic>).push(
    {order:2,name:'audio',state:'enabled',sourcePath:'',type:'',typeState:'known',embed:null,
      embedState:'known',preload:true,preloadState:'known',generate:false,generateState:'known',prefix:'',prefixState:'known'});
  (cast Reflect.field(audioProfile,'candidates'):Array<Dynamic>).push({library:'audio',state:'enabled'});
  var audioEvents=loadEvents.copy();
  audioEvents.push(event('audio/ogg','audio','sound','audio/theme.ogg',12,'false'));
  audioEvents.push(event('audio/mp3','audio','music','audio/theme.mp3',13,'false'));
  var audioPublication=SourceLimeAssetIdentity.preparePublication(audioProfile,owner,
    'Psych Engine','package',audioEvents,[],false,true,true);
  check(!audioPublication.failed,audioPublication.diagnostics.join('\\n'));
  check(!audioPublication.index.loadProfileComplete,
    'HTML5 pathGroup conversion cannot be presented as an ordinary file-backed load profile');
  var audioLoadProfile:SourceLimeAssetIdentityLibraryLoadProfile=null;
  for(audioEntry in audioPublication.index.libraryLoadProfiles)
    if(audioEntry.library=='audio')audioLoadProfile=audioEntry;
  check(audioLoadProfile!=null && audioLoadProfile.state=='unsupported'
    && audioLoadProfile.diagnostic.indexOf('pathGroup')>=0,
    'same-stem HTML5 sound and music entries retain an explicit unsupported diagnostic: '
      +Std.string(audioLoadProfile)+' / '+Std.string(audioPublication.index.loadProfileComplete));

  var providerProfile:Dynamic={namespace:'provider-game',rootRelative:'',snapshotId:snapshot,
    projectSha256:projectHash,candidates:[{library:'default',state:'enabled'}]};
  var receiver='assets/imported_mods/family-receiver';
  var handoff:Dynamic={version:1,providerNamespace:'provider-game',providerRootRelative:'',
    providerProjectSha256:projectHash,receiverRootRelative:'content/alpha',
    receiverNamespace:'family-receiver',catalogVersion:3};
  var coreEvent=event('assets/core.txt','default','text','__nmv_core/data/core.txt',30,'false');
  var corePublication=SourceLimeAssetIdentity.preparePublication(providerProfile,receiver,
    'Nightmare Vision','core',[coreEvent],[],false,true,true,handoff);
  check(!corePublication.failed,corePublication.diagnostics.join('\\n'));
  eq(corePublication.path,receiver+'/.cammie-asset-identities/nightmare-vision-core.json',
    'provider core identity is staged at the receiver-owned core sidecar path');
  eq(corePublication.index.namespace,'family-receiver',
    'materialized core index uses the receiver namespace, not the provider profile namespace');
  eq(corePublication.index.rootRelative,'',
    'materialized core index keeps the exact provider profile root');
  check(corePublication.index.handoff!=null
    && corePublication.index.handoff.providerNamespace=='provider-game'
    && corePublication.index.handoff.receiverRootRelative=='content/alpha',
    'core sidecar preserves the catalog-authorized provider and receiver edge');
  var coreRoundTrip:Dynamic=haxe.Json.parse(SourceLimeAssetIdentity.serialize(corePublication.index));
  check(SourceLimeAssetIdentity.validate(coreRoundTrip,receiver,'Nightmare Vision','core',
    'family-receiver')!=null,
    'receiver-owned core sidecar validates while retaining the provider profile identity');
  check(SourceLimeAssetIdentity.validate(coreRoundTrip,receiver,'Nightmare Vision','core',
    'provider-game')==null,
    'provider namespace cannot be substituted for the receiver owner namespace');
  var badCore:Dynamic=haxe.Json.parse(haxe.Json.stringify(coreRoundTrip));
  Reflect.setField(Reflect.field(badCore,'handoff'),'providerProjectSha256',StringTools.lpad('','d',64));
  check(SourceLimeAssetIdentity.validate(badCore,receiver,'Nightmare Vision','core',
    'family-receiver')==null,
    'sidecar handoff cannot claim a Project hash different from its provider profile');
  check(SourceLimeAssetIdentity.preparePublication(providerProfile,receiver,'Nightmare Vision','package',
    [coreEvent],[],false,true,true,handoff).failed,
    'provider-core handoff metadata cannot be published as a package index');
 }
 static function findFrom(index:SourceLimeAssetIdentityIndex,library:String,id:String):SourceLimeAssetIdentityEntry {
  for(entry in index.entries) if(entry.library==library && entry.id==id)return entry;
  return null;
 }
}'''


class SourceLimeAssetIdentityTest(unittest.TestCase):
    def test_id_type_and_owner_sidecar_contract(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="lime-identity-", dir=TEST_TMP) as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(FIXTURE, encoding="utf-8", newline="\n")
            tjson = work / "tjson"
            tjson.mkdir()
            (tjson / "TJSON.hx").write_text('''package tjson;
class TJSON {}
enum EncodeStyle { Full; }
class TJSONEncoder {
 public function new() {}
 public function doEncode(value:Dynamic, ?style:String):String return haxe.Json.stringify(value);
 public function encodeValue(value:Dynamic, style:EncodeStyle, depth:Int):String return haxe.Json.stringify(value);
}''', encoding="utf-8", newline="\n")
            env = dict(os.environ)
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
            env["PATH"] = os.pathsep.join(
                [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
            )
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "--main", "Main", "--interp"], cwd=work, env=env,
                capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
