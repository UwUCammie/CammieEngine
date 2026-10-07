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
  function event(id:String,library:String,type:String,target:String,order:Int):Dynamic {
   var mapped='assets/'+target;
   var e:PsychAssetProfileMappedFile={sourcePath:'C:/retained/'+order,sourceRelative:'assets/source-'+order,
    mappedPath:mapped,ownerRelative:target,candidateOrder:order,size:12,sha256:bytesHash,
    type:type,library:library,assetId:id,assetIdOverride:true};
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
  eq(findFrom(validated,'named','mod:🧪').ownerRelative,'data/astral.txt','astral identity survives standard JSON round-trip');
  check(SourceLimeAssetIdentity.validate(roundTrip,owner,'Psych Engine','core','identity-fixture')==null,
    'scope mismatch rejects a copied sidecar');
  check(SourceLimeAssetIdentity.isReservedOwnerPath('.cammie-asset-identities/psych.json'),
    'reserved sidecar destination is recognized');
  check(!SourceLimeAssetIdentity.isReservedOwnerPath('images/.cammie-asset-identities/icon.png'),
    'nested ordinary asset path is not confused with owner sidecar root');
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
