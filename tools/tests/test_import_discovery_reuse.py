"""Execute one-use discovery isolation, source verification and invalidation."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]

class ImportDiscoveryReuseTest(unittest.TestCase):
    def test_transaction_snapshot_contract(self):
        fixture = r'''class Main {
 static function check(v:Bool, why:String):Void { if(!v) throw why; }
 static function main():Void {
  var key:Null<String>="ownerA/roots/namespaces";
  var cancel=false;var changed=false;var verified=0;
  var make=function() return new ImportDiscoveryReuse("snapshot/content","Auto",function() return key,
   function() {verified++;if(changed)throw "source hash mismatch";},function() return cancel);
  var shared:Dynamic={pixels:[1,2],name:"same"};
  var origins:Map<String,String>=["same"=>"root/a"];
  var d:Dynamic={songs:[{name:"same",authoredFreeplayOrder:3,destinationFolder:"original",diagnostics:[],convertedCharts:[{chart:{notes:[[1,2,3]]}}],visual:shared,sourceDuplicate:false,importSourceInfo:{dataFolder:"root/a"}},
    {name:"same",sourceDuplicate:false,visual:shared,importSourceInfo:{dataFolder:"root/b"}},
    {name:"same",sourceDuplicate:true,visual:shared,importSourceInfo:{dataFolder:"root/alias"}}],
    packageDiscovery:{truncated:false,cancelled:false},sources:origins};
  var p=make();p.capture("snapshot/content","Auto",d);
  d.songs[0].authoredFreeplayOrder=99;d.songs[0].destinationFolder="owner-qualified";d.songs[0].diagnostics.push("changed");
  d.songs[0].convertedCharts[0].chart.notes[0][1]=77;shared.pixels[0]=9;origins.set("same","changed");
  p.accept();var v=p.take("snapshot/content","Auto");
  check(v.songs[0].authoredFreeplayOrder==3,"authored menu rank did not survive isolated discovery reuse");
  check(verified==1,"verify on use");check(v.songs.length==3,"same-named rows retained");
  check(v.songs[0].destinationFolder=="original" && v.songs[0].diagnostics.length==0,"pre-mutation isolation");
  check(v.songs[0].convertedCharts[0].chart.notes[0][1]==2,"nested chart isolation");
  check(v.songs[0].visual.pixels[0]==1 && v.songs[0].visual==v.songs[1].visual,"internal aliases preserved");
  check((cast v.sources:Map<String,String>).get("same")=="root/a","maps preserved");
  check(v.songs[2].sourceDuplicate && v.songs[1].importSourceInfo.dataFolder=="root/b","source routing preserved");
  check(p.take("snapshot/content","Auto")==null && verified==1,"one use");
  p=make();p.capture("snapshot/content","Auto",d);check(p.take("snapshot/content","Auto")==null,"scan must be accepted");
  p=make();p.capture("snapshot/content","Auto",d);p.accept();check(p.take("different","Auto")==null,"source scope");
  p=make();p.capture("snapshot/content","Auto",d);p.accept();check(p.take("snapshot/content","Psych Engine")==null,"selector scope");
  p=make();p.capture("snapshot/content","Auto",d);p.accept();key="ownerB";check(p.take("snapshot/content","Auto")==null,"owner/context scope");
  key="ownerA/roots/namespaces";p=make();p.capture("snapshot/content","Auto",d);p.accept();key=null;check(p.take("snapshot/content","Auto")==null,"nested scope");
  key="ownerA/roots/namespaces";p=make();p.capture("snapshot/content","Auto",d);p.accept();cancel=true;check(p.take("snapshot/content","Auto")==null,"cancelled scan");cancel=false;
  for(field in ["truncated","cancelled"]) {
   Reflect.setField(d.packageDiscovery,field,true);p=make();p.capture("snapshot/content","Auto",d);p.accept();check(p.take("snapshot/content","Auto")==null,"incomplete discovery");Reflect.setField(d.packageDiscovery,field,false);
  }
  p=make();p.capture("snapshot/content","Auto",d);p.accept();changed=true;var failed=false;
  try p.take("snapshot/content","Auto") catch(e:Dynamic) {failed=Std.string(e)=="source hash mismatch";}
  check(failed,"changed source must abort");changed=false;check(p.take("snapshot/content","Auto")==null,"verification failure consumes data");
  p=make();p.capture("snapshot/content","Auto",d);p.accept();p.close();check(p.take("snapshot/content","Auto")==null,"scope cleanup");
  p=make();var unsupported:Dynamic={songs:[],packageDiscovery:{truncated:false},fn:function(){}};p.capture("snapshot/content","Auto",unsupported);p.accept();check(p.take("snapshot/content","Auto")==null,"unsupported objects fall back");
  p=new ImportDiscoveryReuse("snapshot/content","Auto",function() return key,function(){cancel=true;},function()return cancel);
  p.capture("snapshot/content","Auto",d);p.accept();failed=false;try p.take("snapshot/content","Auto") catch(e:Dynamic) failed=true;check(failed,"cancel during verification");cancel=false;
  p=new ImportDiscoveryReuse("snapshot/content","Auto",function() return key,function(){key="changed";},function()return false);
  p.capture("snapshot/content","Auto",d);p.accept();check(p.take("snapshot/content","Auto")==null,"context changed during verification");
 }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            (temp / "Main.hx").write_text(fixture, encoding="utf-8")
            (temp / "ImportDiscoveryReuse.hx").write_text((ROOT / "source/ImportDiscoveryReuse.hx").read_text(), encoding="utf-8")
            run = subprocess.run([*HAXE_COMMAND,"-cp",str(temp),"-main","Main","--interp"],cwd=ROOT,text=True,capture_output=True)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)

    def test_live_planning_and_transaction_verification_remain_in_place(self):
        workflow=(ROOT/"source/ImportWorkflow.hx").read_text()
        manager=(ROOT/"source/ImportRefreshManager.hx").read_text()
        module=(ROOT/"source/ModuleFunctions.hx").read_text()
        capture=workflow.index("discoveryScope.discoveryReuse.capture(source, selectedType, discovery)")
        mutation=workflow.index("Reflect.setField(songData, 'destinationFolder', storageKey)",capture)
        self.assertLess(capture,mutation)
        self.assertLess(manager.index("io.discoveryReuse.accept()"),manager.index("var imported = convert(source,scan,names)"))
        take=module.index("discoveryScope.discoveryReuse.take(normalizedSource, selectedType)")
        for fragment in ["applyPackageDisplayNames(songs, packageNames)","ImportSongOwnership.setSourceFingerprintHints", "ImportSongOwnership.planDestination("]:
            self.assertGreater(module.index(fragment,take),take)
        self.assertIn("ImportSourceSnapshot.verify(Path.directory(source), Std.string(record.snapshotId), cancel",manager)
        io=(ROOT/"source/ImportIO.hx").read_text()
        self.assertIn("context.discoveryReuse.close()",io)
        self.assertIn("context.discoveryReuse = null",io)

    def test_actual_snapshot_changes_abort_reuse(self):
        fixture = r'''class Main {
 static function main():Void {
  var args=Sys.args();
  var snapshot=ImportSourceSnapshot.capture(args[0],args[1],"Psych Engine","0.0.24");
  if(!snapshot.complete)throw snapshot.error;
  var content=snapshot.snapshotRoot+"/content";
  var file=content+"/chart.json";
  var original=sys.io.File.getContent(file);
  ImportSourceSnapshot.verify(snapshot.snapshotRoot,snapshot.snapshotId);
  for(mode in ["unchanged","same-size-change","new-file","removed-file"]) {
   var plan=new ImportDiscoveryReuse(content,"Auto",function()return "transaction",
    function()ImportSourceSnapshot.verify(snapshot.snapshotRoot,snapshot.snapshotId),function()return false);
   plan.capture(content,"Auto",{songs:[{name:"song"}],packageDiscovery:{truncated:false,cancelled:false}});plan.accept();
   switch(mode) {
    case "same-size-change":sys.io.File.saveContent(file,"{\"value\":2}");
    case "new-file":sys.io.File.saveContent(content+"/new.json","{}");
    case "removed-file":sys.FileSystem.deleteFile(file);
    default:
   }
   var failed=false;var value:Dynamic=null;try value=plan.take(content,"Auto") catch(e:Dynamic)failed=true;
   if(mode=="unchanged") {if(failed || value==null)throw "valid snapshot rejected";}
   else if(!failed)throw "stale discovery accepted: "+mode;
   if(sys.FileSystem.exists(content+"/new.json"))sys.FileSystem.deleteFile(content+"/new.json");
   sys.io.File.saveContent(file,original);
  }
 }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            temp=Path(folder)
            donor=temp/"donor";donor.mkdir()
            (donor/"chart.json").write_text('{"value":1}',encoding="utf-8")
            (temp/"Main.hx").write_text(fixture,encoding="utf-8")
            run=subprocess.run([*HAXE_COMMAND,"-cp",str(ROOT/"source"),"-cp",str(temp),"--run","Main",str(donor),str(temp/"snapshots")],cwd=temp,text=True,capture_output=True,timeout=30)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
