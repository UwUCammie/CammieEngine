"""Read-only removal planning must preserve surviving owners and shared state."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
ROOT = Path(__file__).resolve().parents[2]

FIXTURE = r'''import haxe.Json;
import ImportRefreshTransaction.ImportRefreshManifest;
class Main {
 static function check(ok:Bool, why:String):Void if (!ok) throw why;
 static function hash(letter:String):String return StringTools.lpad(letter,letter,64);
 static function root(name:String):String return "assets/imported_mods/"+name;
 static var registry = "assets/data/freeplaySongJson.jsonc";
 static function manifest(id:String, roots:Array<String>, paths:Array<String>, snap:String, ?deps:Array<String>):ImportRefreshManifest {
  var owner="retained-import:"+hash(id);
  return {schemaVersion:1,owner:owner,transactionId:"transaction-"+id,ownedRoots:["assets"],
   revision:{importRecord:{schemaVersion:1,id:hash(id),snapshotId:hash(snap),source:"sources/"+hash(snap)+"/content",
    roots:[for(r in roots){namespace:r}],runtimeDependencyOwners:deps==null?[]:deps},
    registries:[{path:registry,before:"[]",generated:"[]"}]},
   files:[for(p in paths){path:p,sha256:hash("f"),owner:owner}]};
 }
 static function assess(roots:Array<String>, records:Array<ImportRefreshManifest>, ?active:Array<String>)
  return ImportRemovalPlan.assess([for(r in roots)root(r)],records,true,active);
 static function main() {
  var a=manifest("a",["alpha"],[root("alpha")+"/sprite.png","assets/shared.png",registry],"c");
  var b=manifest("b",["beta"],[root("beta")+"/sprite.png","assets/shared.png",registry],"c");
  check(ImportIO.isRegistry(registry.toUpperCase()) && ImportIO.isFreeplayRegistry(registry.toLowerCase()),
   "registry classification changes with case");
  check(!ImportIO.isRegistry("assets/data/ordinary/song.json") && !ImportIO.isRegistry(null), "ordinary asset is registry");
  var before=Json.stringify([a,b]);
  var plan=assess(["alpha"],[a,b]);
  check(plan.inventoryComplete && plan.blockers.length==0,"valid singleton rejected: "+plan.blockers.join("; "));
  check(plan.candidateFiles.length==1 && plan.candidateFiles[0].path==root("alpha")+"/sprite.png","exclusive candidates wrong");
  check(plan.sharedFiles.length==1 && plan.sharedFiles[0].retainedBy[0]==b.owner,"shared file would be removed");
  check(plan.registryPaths.length==1 && plan.registryPaths[0]==registry,"registry must be reconciled separately");
  check(plan.sharedSnapshots.length==1 && plan.candidateSnapshots.length==0,"shared snapshot would be removed");
  check(Json.stringify([a,b])==before,"assessment mutated input");
  var reverse=assess(["alpha"],[b,a]);
  check(Json.stringify(plan.candidateFiles)==Json.stringify(reverse.candidateFiles),"input order changed plan");
  var both=assess(["beta","alpha","alpha"],[b,a]);
  check(both.blockers.length==0 && both.candidateFiles.length==3 && both.sharedFiles.length==0,"multi-owner accounting wrong");
  check(both.candidateSnapshots.length==1 && both.sharedSnapshots.length==0,"snapshot not deduplicated");
  check(both.candidateFiles[2].transactions.length==2,"shared selected file lacks both claims");

  var aggregate=manifest("d",["alpha","gamma"],[root("alpha")+"/a.png",root("gamma")+"/g.png"],"d");
  var partial=assess(["alpha"],[aggregate,b]);
  check(partial.blockers.length>0 && partial.affectedOwners.length==2 && partial.selectedOwners.length==1,"aggregate silently expanded selection");
  check(assess(["alpha","gamma"],[aggregate,b]).blockers.length==0,"explicit aggregate selection rejected");
  b.revision.importRecord.runtimeDependencyOwners=[root("alpha")];
  var dependency=assess(["alpha"],[a,b]);
  check(dependency.dependents.join(",")==root("beta") && dependency.blockers.length>0,"surviving dependency not protected");
  check(assess(["alpha","beta"],[a,b]).dependents.length==0,"selected dependent treated as survivor");
  check(dependency.relink().join(",")==root("beta"),"relink lost a real dependent");
  dependency.markLinked([root("alpha")]);check(dependency.linkedOwners.length==0,"request reported as its own link");
  var widened=assess(["alpha","beta"],[a,b]);widened.markLinked([root("alpha")]);
  check(widened.linkedOwners.join(",")==root("beta") && widened.blockers.length==0,"added package not reported as linked");
  b.revision.importRecord.runtimeDependencyOwners=[];
  check(assess(["alpha"],[a,b],[root("alpha")]).blockers.length>0,"active selected owner ignored");
  check(assess(["alpha"],[a,b],[root("beta")]).blockers.length==0,"unrelated active owner blocked inventory");
  check(assess(["unknown"],[a,b]).blockers.length>0,"unknown owner accepted");
  check(!ImportRemovalPlan.assess([root("alpha")],[a],false).inventoryComplete,"partial inventory accepted");
  check(!assess(["alpha"],[a,a]).inventoryComplete,"duplicate transaction accepted");
  var overlap=manifest("e",["alpha"],[],"e");
  check(!assess(["alpha"],[a,overlap]).inventoryComplete,"ambiguous owner accepted");
  Reflect.deleteField(b.revision.importRecord,"runtimeDependencyOwners");
  check(assess(["alpha"],[a,b]).blockers.length>0,"missing dependency proof accepted");
  b.revision.importRecord.runtimeDependencyOwners=[];
  b.revision.importRecord.source="../../external-mod";
  check(!assess(["alpha"],[a,b]).inventoryComplete,"external snapshot accepted");
  b.revision.importRecord.source="sources/"+hash("c")+"/content";
  a.revision.registries=[];
  check(assess(["alpha"],[a,b]).blockers.length>0,"missing registry baseline accepted");
  a.revision.registries=[{path:registry,before:"[]",generated:"[]"}];
  for(path in ["assets/data/options.json","assets/../external.txt","C:/external.txt","assets/NUL.txt","assets/folder./x.png"]) {
   var bad=manifest("a",["alpha"],[path],"c");
   var rejected=assess(["alpha"],[bad]);
   check(!rejected.inventoryComplete && rejected.candidateFiles.length==0,"unsafe candidate path accepted: "+path);
  }
  var cancelled=ImportRemovalPlan.assess([root("alpha")],[a,b],true,[],function() throw "cancelled");
  check(!cancelled.inventoryComplete && cancelled.candidateFiles.length==0,"cancelled inventory exposed candidates");
  // Returned lists are detached from original manifests.
  plan.candidateFiles[0].path="changed"; plan.transactionOwners.push("changed");
  check(Json.stringify([a,b])==before,"returned plan mutated source manifests");
  Sys.println("removal plan contracts passed");
 }
}'''

class ImportRemovalPlanTest(unittest.TestCase):
    def test_shared_files_dependencies_aggregate_selection_and_invalid_inventory(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            (Path(folder)/'Main.hx').write_text(FIXTURE, encoding='utf-8')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/tjson/1,4,0'),'-cp',folder,'--run','Main'],cwd=folder,text=True,capture_output=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('removal plan contracts passed',result.stdout)

if __name__ == '__main__':
    unittest.main()
