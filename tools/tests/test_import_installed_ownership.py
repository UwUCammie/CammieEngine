"""Installed ownership joins live metadata to committed import receipts."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, TEST_TMP
ROOT = Path(__file__).resolve().parents[2]
FIXTURE = r'''import haxe.Json;
import haxe.crypto.Sha256;
import haxe.io.Bytes;
import sys.io.File;
import sys.FileSystem as FS;
class Main {
 static function check(ok:Bool, why:String):Void if (!ok) throw why;
 static function hash(s:String):String return Sha256.make(Bytes.ofString(s)).toHex();
 static var root:String;
 static function write(path:String,value:Dynamic):Void { FS.createDirectory(haxe.io.Path.directory(path)); File.saveContent(path,Json.stringify(value)); }
 static function main() {
  var mode=Sys.args()[0];root=FS.fullPath(Sys.args()[1]);
  var ownerRoot="assets/imported_mods/alpha"; var engine=ImportEngine.PSYCH;
  var id=hash("alpha");var owner="retained-import:"+id;
  var provenance:Dynamic={version:1,destinationFolder:"song",sourceFolder:"song",sourceEngine:engine,sourceOwner:ownerRoot,sourceIdentity:"fixture",sourceFingerprint:"fixture"};
  var compat:Dynamic={version:1,selectedRoot:ownerRoot,roots:[{path:ownerRoot,engine:engine}]};
  var marker:Dynamic={version:1,engine:engine};
  if(mode=="engine") provenance.sourceEngine=ImportEngine.NIGHTMARE_VISION;
  if(mode=="compat-owner") compat.selectedRoot="assets/imported_mods/other";
  if(mode=="provider") compat.roots.push({path:"assets/imported_mods/other",engine:engine});
  if(mode=="marker") marker.engine=ImportEngine.NIGHTMARE_VISION;
  var stage=root+"/stage";FS.createDirectory(stage);
  write(stage+"/provenance",provenance);write(stage+"/compat",compat);write(stage+"/marker",marker);
  var outputs=[{path:"assets/data/song/importProvenance.json",stagedPath:"provenance"},
   {path:"assets/data/song/compatScripts.json",stagedPath:"compat"},{path:ownerRoot+"/.cammie-owner.json",stagedPath:"marker"}];
  var snapshot=hash("snapshot");
  var record={schemaVersion:1,id:id,snapshotId:snapshot,source:"sources/"+snapshot+"/content",roots:[{namespace:"alpha",engine:engine}],runtimeDependencyOwners:[]};
  var committed=ImportRefreshTransaction.apply(root,stage,root+"/import-cache/state",owner,["assets"],outputs,{importRecord:record});
  check(committed.status=="applied","commit failed");
  write(root+"/import-cache/records/"+id+".json",{id:id});
  var manifests=ImportRefreshTransaction.inspectRetainedManifests(root,root+"/import-cache/state",root+"/import-cache/records");
  var protectedRoots:Array<String>=[];
  switch(mode) {
   case "missing-provenance": FS.deleteFile(root+"/assets/data/song/importProvenance.json");
   case "missing-compat": FS.deleteFile(root+"/assets/data/song/compatScripts.json");
   case "missing-both": FS.deleteFile(root+"/assets/data/song/importProvenance.json");FS.deleteFile(root+"/assets/data/song/compatScripts.json");
   case "edited": File.saveContent(root+"/assets/data/song/importProvenance.json",Json.stringify(provenance)+" ");
   case "unknown": FS.createDirectory(root+"/assets/imported_mods/unknown");
   case "catalog": write(root+"/assets/data/codenameMods.json",{version:1,entries:[{root:"assets/imported_mods/unknown"}]});
   case "global": write(root+"/assets/imported_mods/globalResultsProvider.json",{version:1,defaultOwner:"assets/imported_mods/unknown"});
   case "protected": FS.createDirectory(root+"/assets/imported_mods/host");protectedRoots.push("assets/imported_mods/host");
   case "host-claim": protectedRoots.push(ownerRoot);
   default:
  }
  function tree(path:String):String {
   var entries:Array<String>=[];
   function visit(p:String):Void { if(FS.isDirectory(p)){for(n in FS.readDirectory(p))visit(p+"/"+n);}else entries.push(p+":"+hash(File.getContent(p))); }
   visit(path);entries.sort(Reflect.compare);return entries.join("\n");
  }
  var before=tree(root);
  var audit=ImportInstalledOwnership.inspect(root,manifests,protectedRoots,mode=="cancel"?function() return true:null);
  if(mode=="valid" || mode=="protected") check(audit.complete && audit.charts.length==1 && audit.charts[0].ownerRoot==ownerRoot,"valid audit failed: "+audit.blockers.join("; "));
  else check(!audit.complete && audit.charts.length==0 && audit.owners.length==0 && audit.blockers.length>0,"invalid audit accepted: "+mode);
  check(tree(root)==before,"audit changed files");
  Sys.println("ownership contract passed: "+mode);
 }
}'''
class InstalledOwnershipTest(unittest.TestCase):
    def test_committed_live_ownership_and_fail_closed_read_only_audit(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            fixture=Path(folder)
            (fixture/'Main.hx').write_text(FIXTURE,encoding='utf-8')
            for mode in ('valid','protected','missing-provenance','missing-compat','missing-both','edited','unknown','catalog','global','engine','compat-owner','provider','marker','host-claim','cancel'):
                with self.subTest(mode=mode):
                    install=fixture/mode;install.mkdir()
                    result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/tjson/1,4,0'),'-cp',str(fixture),'--run','Main',mode,str(install)],cwd=fixture,text=True,capture_output=True,timeout=60)
                    self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__ == '__main__':
    unittest.main()
