"""Strict removal inventory reads real transaction receipts without repairing them."""
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
 static function state():String return root+"/import-cache/state";
 static function records():String return root+"/import-cache/records";
 static function inspect(?cancel:Void->Bool) return ImportRefreshTransaction.inspectRetainedManifests(root,state(),records(),cancel);
 static function seed(name:String):Dynamic {
  var id=hash(name);var owner="retained-import:"+id;var snapshot=hash("snapshot");
  var record={schemaVersion:1,id:id,snapshotId:snapshot,source:"sources/"+snapshot+"/content",
   roots:[{namespace:name}],runtimeDependencyOwners:[]};
  var staging=root+"/staging-"+name;FS.createDirectory(staging);File.saveContent(staging+"/file",name);
  var result=ImportRefreshTransaction.apply(root,staging,state(),owner,["assets"],
   [{path:"assets/imported_mods/"+name+"/file",stagedPath:"file"}],{importRecord:record});
  check(result.status=="applied","seed import failed");
  FS.createDirectory(records());var pointer=records()+"/"+id+".json";File.saveContent(pointer,Json.stringify({id:id}));
  return {owner:owner,id:id,record:record,pointer:pointer,manifest:result.manifestPath,transaction:result.transactionPath,receipt:result.receiptPath};
 }
 static function tree(path:String):String {
  var result:Array<String>=[];
  function visit(p:String):Void {
   if(FS.isDirectory(p)){var names=FS.readDirectory(p);names.sort(Reflect.compare);for(name in names)visit(p+"/"+name);}
   else result.push(p+":"+hash(File.getContent(p)));
  }
  visit(path);result.sort(Reflect.compare);return result.join("\n");
 }
 static function rejects(reason:String):Void {
  var before=tree(root);var failed=false;
  try inspect() catch(e:Dynamic) failed=true;
  check(failed,reason);check(tree(root)==before,"inspection mutated files after "+reason);
 }
 static function main() {
  var mode=Sys.args()[0];root=FS.fullPath(Sys.args()[1]);
  if(mode=="empty") {check(inspect().length==0,"empty install failed");check(!FS.exists(root+"/import-cache"),"read created cache");return;}
  var a=seed("alpha");var b=seed("beta");
  switch(mode) {
   case "valid":
    var before=tree(root);var all=inspect();check(all.length==2,"lost owner");
    var plan=ImportRemovalPlan.assess(["assets/imported_mods/alpha"],all,true,[]);
    check(plan.inventoryComplete && plan.blockers.length==0 && plan.candidateFiles.length==1,"valid plan failed");
    check(tree(root)==before,"inspection wrote metadata");
    var again=inspect();check(Json.stringify(all)==Json.stringify(again),"unstable ordering");
   case "orphan-pointer": FS.deleteFile(a.manifest);rejects("missing manifest accepted");
   case "hidden-owner": FS.deleteFile(b.pointer);rejects("owner absent from pointer index was skipped");
   case "missing-state": File.saveContent(records()+"/"+hash("lost")+".json",Json.stringify({id:hash("lost")}));rejects("orphan pointer skipped");
   case "bad-pointer": File.saveContent(a.pointer,"{}");rejects("corrupt pointer skipped");
   case "bad-receipt": File.saveContent(a.receipt,"{}");rejects("corrupt receipt accepted");
   case "missing-receipt": FS.deleteFile(a.receipt);rejects("unfinished transaction accepted");
   case "bad-manifest": File.saveContent(a.manifest,File.getContent(a.manifest)+" ");rejects("manifest digest ignored");
   case "unknown-state": FS.createDirectory(state()+"/unknown");rejects("unknown state skipped");
   case "unknown-record": File.saveContent(records()+"/unexpected.tmp","{}");rejects("uncommitted pointer skipped");
   case "newest-journal": File.saveContent(a.transaction+"/journal-99999999.json","broken");rejects("fell back past malformed newest journal");
   case "wrong-install":
    var names=FS.readDirectory(a.transaction);names=[for(n in names)if(StringTools.startsWith(n,"journal-"))n];names.sort(Reflect.compare);
    var path=a.transaction+"/"+names[names.length-1];var journal:Dynamic=Json.parse(File.getContent(path));journal.installRoot=root+"/elsewhere";File.saveContent(path,Json.stringify(journal));rejects("foreign install accepted");
   case "cancel":
    var before=tree(root);var cancelled=false;try inspect(function() return true) catch(e:Dynamic) cancelled=true;
    check(cancelled && tree(root)==before,"cancel did not preserve state");
   case "changed-pointer":
    var snapshot=new ImportMetadataInspection(root);snapshot.metadata(a.pointer);
    File.saveContent(a.pointer,File.getContent(a.pointer)+" ");
    var failed=false;try snapshot.verify() catch(e:Dynamic) failed=true;
    check(failed,"metadata changed after inspection was accepted");
   case "rolled-back":
    var id=hash("rolled");var owner="retained-import:"+id;var tx=state()+"/"+hash(owner)+"/transactions/txn-rolled";FS.createDirectory(tx);
    File.saveContent(tx+"/journal-00000001.json",Json.stringify({schemaVersion:1,owner:owner,transactionId:"txn-rolled",installRoot:root,phase:"rolled-back"}));
    var before=tree(root);check(inspect().length==2,"rolled back first import polluted owner inventory");check(tree(root)==before,"rolled back inspection mutated state");
   default: throw mode;
  }
  Sys.println("inventory contract passed: "+mode);
 }
}'''

class ImportRemovalInventoryTest(unittest.TestCase):
    def test_real_receipts_incomplete_inventory_and_read_only_failures(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            fixture=Path(folder)
            (fixture/'Main.hx').write_text(FIXTURE,encoding='utf-8')
            for mode in ('empty','valid','orphan-pointer','hidden-owner','missing-state','bad-pointer','bad-receipt','missing-receipt','bad-manifest','unknown-state','unknown-record','newest-journal','wrong-install','cancel','changed-pointer','rolled-back'):
                with self.subTest(mode=mode):
                    install=fixture/mode;install.mkdir()
                    result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/tjson/1,4,0'),'-cp',str(fixture),'--run','Main',mode,str(install)],cwd=fixture,text=True,capture_output=True,timeout=60)
                    self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__ == '__main__':
    unittest.main()
