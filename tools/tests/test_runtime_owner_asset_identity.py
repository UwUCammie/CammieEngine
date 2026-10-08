"""Receipt-bound Lime identity lookup stays inside one committed owner."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class RuntimeOwnerAssetIdentityTest(unittest.TestCase):
    @unittest.skipUnless(HAXE.is_file(), "portable Haxe interpreter is unavailable")
    def test_owner_index_validation_resolution_type_and_epoch_retry(self):
        fixture = r'''package;
import haxe.crypto.Sha256;
import haxe.io.Bytes;
import lime.utils.AssetLibrary;
import sys.FileSystem;
import sys.io.File;

@:access(lime.utils.AssetLibrary)
class CachedAssetLibrary extends AssetLibrary {
 public function new() super();
 public function cacheText(id:String,value:String):Void cachedText.set(id,value);
 public function hasText(id:String):Bool return cachedText.exists(id);
}

class Main {
 static function fail(message:String):Void throw message;
 static function check(value:Bool,message:String):Void if(!value)fail(message);
 static function eq(actual:Dynamic,expected:Dynamic,message:String):Void
  if(actual!=expected)fail(message+': expected '+Std.string(expected)+', got '+Std.string(actual));
 static function hash(bytes:Bytes):String return Sha256.make(bytes).toHex();
 static function write(path:String,bytes:Bytes):Void {
  FileSystem.createDirectory(haxe.io.Path.directory(path)); File.saveBytes(path,bytes);
 }
 static function entry(library:String,id:String,type:String,path:String,bytes:Bytes):Dynamic
  return {library:library,id:id,type:type,ownerRelative:path,size:bytes.length,sha256:hash(bytes),candidateOrder:0};
 static function main():Void {
  var owner='assets/imported_mods/owner';
  FileSystem.createDirectory(owner);
  var image=Bytes.ofString('indexed image');
  var text=Bytes.ofString('indexed text');
  write(owner+'/images/sprite.png',image);
  write(owner+'/data/message.txt',text);
  var indexPath=owner+'/.cammie-asset-identities/psych.json';
  var index:Dynamic={version:1,owner:owner,engine:'Psych Engine',scope:'package',namespace:'owner',
   snapshotId:StringTools.lpad('','0',64),rootRelative:'content',projectSha256:StringTools.lpad('','1',64),
   complete:true,libraries:['default','named'],librariesComplete:true,
   entries:[entry('default','plain-id','IMAGE','images/sprite.png',image),
    entry('named','portrait:small','TEXT','data/message.txt',text)]};
  var indexBytes=Bytes.ofString(haxe.Json.stringify(index));
  write(indexPath,indexBytes);
  ImportRefreshManager.generation=2;
  ImportRefreshManager.revision=3;
  ImportRefreshManager.binding={generation:2,revision:3,transactionId:'tx-1',owner:owner,
   engine:'Psych Engine',scope:'package',namespace:'owner',snapshotId:index.snapshotId,
   rootRelative:'content',projectSha256:index.projectSha256,indexPath:indexPath,
   indexSha256:hash(indexBytes),indexSize:null,files:[
    {path:indexPath,sha256:hash(indexBytes)},
    {path:owner+'/images/sprite.png',sha256:hash(image)},
    {path:owner+'/data/message.txt',sha256:hash(text)}]};

  var view=RuntimeOwnerAssetIdentity.acquire(owner,'Psych Engine','package');
  eq(view.bindingState,'ready','validated binding state');
  eq(view.resolve('plain-id','IMAGE').state,'found','default library ID');
  eq(view.resolve('named:portrait:small','TEXT').state,'found','first-colon named library ID');
  eq(view.resolve('named:portrait:small','IMAGE').state,'type-mismatch','wrong type blocks lookup');
  eq(view.resolve('named:missing','TEXT').state,'missing','declared library miss is owned');
  eq(view.resolve('other:missing','TEXT').state,'unclaimed','complete unclaimed library allows fallback');
  eq(view.libraryState('named'),'declared','owner declared library');
  eq(view.libraryState('other'),'unclaimed','complete catalog proves unclaimed library');
  eq(view.list('named','TEXT').join(','),'portrait:small','typed list keeps raw Lime ID');

  ImportRefreshManager.generation++;
  ImportRefreshManager.revision++;
  eq(RuntimeOwnerAssetIdentity.acquire(owner,'Psych Engine','package')==view,true,
   'unrelated global generation and availability epoch changes retain the freshly revalidated owner identity');
  eq(view.resolve('plain-id','IMAGE').state,'found',
   'a retained identity remains usable after same-proof revalidation');

  ImportRefreshManager.revision++;
  ImportRefreshManager.binding=null;
  eq(RuntimeOwnerAssetIdentity.acquire(owner,'Psych Engine','package').bindingState,'unverified',
   'a physical sidecar without a current manager binding is not trusted');
  ImportRefreshManager.revision++;
  ImportRefreshManager.binding={generation:2,revision:ImportRefreshManager.revision,transactionId:'tx-2',
   owner:owner,engine:'Psych Engine',scope:'package',namespace:'owner',snapshotId:index.snapshotId,
   rootRelative:'content',projectSha256:index.projectSha256,indexPath:indexPath,indexSha256:'0',
   indexSize:null,files:[]};
  eq(RuntimeOwnerAssetIdentity.acquire(owner,'Psych Engine','package').bindingState,'invalid',
   'uncommitted or tampered sidecar cannot be used');

  ImportRefreshManager.revision++;
  ImportRefreshManager.binding={generation:2,revision:ImportRefreshManager.revision,transactionId:'tx-3',
   owner:owner,engine:'Psych Engine',scope:'package',namespace:'owner',snapshotId:index.snapshotId,
   rootRelative:'content',projectSha256:index.projectSha256,indexPath:indexPath,
   indexSha256:hash(indexBytes),indexSize:null,files:[{path:indexPath,sha256:hash(indexBytes)},
    {path:owner+'/images/sprite.png',sha256:hash(image)},{path:owner+'/data/message.txt',sha256:hash(text)}]};
  var current=RuntimeOwnerAssetIdentity.acquire(owner,'Psych Engine','package');
  eq(current.bindingState,'ready','new committed transaction can replace an invalidated view');
  view.release();
  eq(RuntimeOwnerAssetIdentity.acquire(owner,'Psych Engine','package')==current,true,
   'releasing an old identity removed a newer owner binding');

  var delegate=new CachedAssetLibrary();
  var detached=new PsychOwnerAssetLibraryView(delegate,function()
   return RuntimeOwnerAssetIdentity.acquire(owner,'Psych Engine','package')==current);
  current.trackAssetLibraryView(detached);
  detached.unload();
  delegate.cacheText('repopulated','detached text');
  eq(detached.getText('repopulated'),'detached text',
   'source unload leaves a detached view usable while its proof remains current');
  RuntimeOwnerAssetIdentity.releaseOwner(owner);
  eq(delegate.hasText('repopulated'),false,
   'owner release retires detached views and clears caches they refilled');
  var detachedRejected=false;
  try detached.getText('repopulated') catch (_:Dynamic) detachedRejected=true;
  check(detachedRejected,'owner release makes the detached handle unusable');

  var receiver='assets/imported_mods/family-receiver';
  var coreBytes=Bytes.ofString('provider core text');
  write(receiver+'/__nmv_core/data/core.txt',coreBytes);
  var coreHandoff:Dynamic={version:1,providerNamespace:'provider-game',providerRootRelative:'',
   providerProjectSha256:StringTools.lpad('','2',64),receiverRootRelative:'content/alpha',
   receiverNamespace:'family-receiver',catalogVersion:3};
  var coreIndex:Dynamic={version:2,owner:receiver,engine:'Nightmare Vision',scope:'core',
   namespace:'family-receiver',snapshotId:StringTools.lpad('','3',64),rootRelative:'',
   projectSha256:coreHandoff.providerProjectSha256,complete:true,libraries:['default'],
   librariesComplete:true,loadTarget:null,loadProfileComplete:false,
   libraryLoadProfiles:[{library:'default',state:'unknown',projectOrder:-1,
    projectPreloadState:'unresolved',projectPreload:null,projectEmbedState:'unresolved',
    projectEmbed:null,diagnostic:'Fixture has no source target.'}],
   entries:[{library:'default',id:'core-id',type:'TEXT',ownerRelative:'__nmv_core/data/core.txt',
    size:coreBytes.length,sha256:hash(coreBytes),candidateOrder:0,preloadState:'unresolved'}],
   handoff:{version:1,providerNamespace:coreHandoff.providerNamespace,
    providerRootRelative:coreHandoff.providerRootRelative,
    providerProjectSha256:coreHandoff.providerProjectSha256,
    receiverRootRelative:coreHandoff.receiverRootRelative,catalogVersion:3}};
  var coreIndexPath=receiver+'/.cammie-asset-identities/nightmare-vision-core.json';
  var coreIndexBytes=Bytes.ofString(haxe.Json.stringify(coreIndex));
  write(coreIndexPath,coreIndexBytes);
  var coreFiles=[{path:coreIndexPath,sha256:hash(coreIndexBytes)},
   {path:receiver+'/__nmv_core/data/core.txt',sha256:hash(coreBytes)}];
  var coreBinding:Dynamic={generation:ImportRefreshManager.generation,
   revision:ImportRefreshManager.revision+1,transactionId:'family-core-tx',owner:receiver,
   engine:'Nightmare Vision',scope:'core',namespace:'family-receiver',
   snapshotId:coreIndex.snapshotId,rootRelative:'',projectSha256:coreIndex.projectSha256,
   handoff:coreHandoff,indexPath:coreIndexPath,indexSha256:hash(coreIndexBytes),indexSize:null,
   files:coreFiles};
  ImportRefreshManager.revision++;
  ImportRefreshManager.binding=coreBinding;
  var receiverCore=RuntimeOwnerAssetIdentity.acquire(receiver,'Nightmare Vision','core');
  eq(receiverCore.bindingState,'ready','catalog-bound provider core is authenticated under the receiver owner');
  eq(receiverCore.resolve('core-id','TEXT').state,'found','provider core entry is readable through receiver-owned files');
  check(receiverCore.handoff!=null && receiverCore.handoff.providerNamespace=='provider-game'
   && receiverCore.handoff.receiverRootRelative=='content/alpha',
   'runtime identity retains the matched provider-to-receiver proof');
  var wrongEdge:Dynamic=Reflect.copy(coreBinding);
  wrongEdge.handoff=Reflect.copy(coreHandoff);
  wrongEdge.handoff.receiverRootRelative='content/beta';
  ImportRefreshManager.revision++;
  wrongEdge.revision=ImportRefreshManager.revision;
  ImportRefreshManager.binding=wrongEdge;
  eq(RuntimeOwnerAssetIdentity.acquire(receiver,'Nightmare Vision','core').bindingState,'invalid',
   'manager binding cannot redirect the receiver index to a different family member');
  var missingEdge:Dynamic=Reflect.copy(coreBinding);
  missingEdge.revision=ImportRefreshManager.revision+1;
  Reflect.setField(missingEdge,'handoff',null);
  ImportRefreshManager.revision++;
  ImportRefreshManager.binding=missingEdge;
  eq(RuntimeOwnerAssetIdentity.acquire(receiver,'Nightmare Vision','core').bindingState,'invalid',
   'a v3 receiver sidecar cannot be trusted without its manager catalog edge');
  ImportRefreshManager.revision++;
  coreBinding.revision=ImportRefreshManager.revision;
  ImportRefreshManager.binding=coreBinding;
  eq(RuntimeOwnerAssetIdentity.acquire(receiver,'Nightmare Vision','core').bindingState,'ready',
   'restoring the exact committed edge reactivates the receiver core index');

  var legacyOwner='assets/imported_mods/legacy';
  FileSystem.createDirectory(legacyOwner);
  ImportRefreshManager.binding=null;
  eq(RuntimeOwnerAssetIdentity.acquire(legacyOwner,'Psych Engine','package').bindingState,'no-index',
   'legacy owner with no sidecar keeps existing native fallback behavior');
 }
}'''
        stubs = {
            "ImportRefreshManager.hx": '''package;
class ImportRefreshManager {
 public static var generation:Int=1;
 public static var revision:Int=1;
 public static var binding:Dynamic;
 public static function availabilityRevision():Int return revision;
 public static function ownerAssetIndexBinding(owner:String,engine:String,scope:String):Dynamic return binding;
}''',
            "CompatScriptManifest.hx": '''package;
class CompatScriptManifest { public static inline var ROOT_PREFIX:String='assets/imported_mods'; }''',
            "PsychOwnerAssetPath.hx": '''package;
import haxe.io.Path;
using StringTools;
class PsychOwnerAssetPath {
 public static function normalizeOwner(value:String):String {
  if(value==null || !value.startsWith('assets/imported_mods/'))return '';
  return sys.FileSystem.isDirectory(value)?Path.normalize(value):'';
 }
 public static function withinOwner(owner:String,path:String):Bool {
  if(owner==null||path==null||!sys.FileSystem.exists(owner)||!sys.FileSystem.exists(path))return false;
  var base=Path.normalize(sys.FileSystem.fullPath(owner));
  var file=Path.normalize(sys.FileSystem.fullPath(path));
  return file.startsWith(base+'/');
 }
 public static function pathInScope(owner:String,path:String,pathRoot:String,excludedSubtree:String=''):Bool {
  var normalizedOwner=normalizeOwner(owner);
  if(normalizedOwner==''||path==null||path=='')return false;
  var normalizedRoot=Path.normalize(pathRoot==null||pathRoot==''?normalizedOwner:pathRoot);
  if(!pathIsWithin(normalizedOwner,normalizedRoot)||!pathIsWithin(normalizedOwner,path))return false;
  if(excludedSubtree!=null&&excludedSubtree!=''
   &&pathIsWithin(Path.normalize(Path.join([normalizedOwner,excludedSubtree])),path))return false;
  return withinOwner(normalizedOwner,path)&&withinOwner(normalizedRoot,path);
 }
 static function pathIsWithin(root:String,path:String):Bool {
  if(root==null||root==''||path==null||path=='')return false;
  var rootKey=Path.normalize(root).toLowerCase();
  var pathKey=Path.normalize(path).toLowerCase();
  return pathKey==rootKey||pathKey.startsWith(rootKey.endsWith('/')?rootKey:rootKey+'/');
 }
}''',
            "FNFAssets.hx": '''package;
class FNFAssets {
 public static function resolveCaseInsensitivePath(path:String):String return sys.FileSystem.exists(path)?path:null;
}''',
            "tjson/TJSON.hx": '''package tjson;
class TJSON {}
enum EncodeStyle { Full; }
class TJSONEncoder {
 public function new(){}
 public function doEncode(value:Dynamic,?style:String):String return haxe.Json.stringify(value);
 public function encodeValue(value:Dynamic,style:EncodeStyle,depth:Int):String return haxe.Json.stringify(value);
}''',
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            for name, content in stubs.items():
                path = work / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
            (work / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            env = dict(os.environ)
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
            env["PATH"] = os.pathsep.join(
                [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
            )
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "-lib", "lime", "-lib", "openfl", "--main", "Main", "--interp"], cwd=work, env=env,
                capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
