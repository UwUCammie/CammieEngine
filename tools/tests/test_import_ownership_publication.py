"""Atomic ownership replacement keeps unrelated packages and avoids repeated path retirement."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from test_native_asset_resolution import extract_method
ROOT=Path(__file__).resolve().parents[2]
class ImportOwnershipPublicationTest(unittest.TestCase):
    def test_multi_root_replacement_preserves_unrelated_owners(self):
        source=(ROOT/"source/ImportRefreshManager.hx").read_text()
        methods="\n".join(extract_method(source,m) for m in (
            "static function addCommittedPathOwners(","static function normalizeInstallRelative("))
        fixture=r'''import haxe.io.Path;
class ImportWorkScheduler { public static function cooperate():Bool return true; }
class Mutex {
 public var held=false;
 public function new(){}
 public function acquire(){if(held)throw "nested lock";held=true;}
 public function release(){if(!held)throw "unbalanced lock";held=false;}
}
class OwnershipFixture {
 static var mutex=new Mutex();
 static var retiredKeys=0;
 static var committedPathsByOwner:Map<String,Array<String>>=new Map();
 static var committedPathOwners:Map<String,Array<String>>=new Map();
 static function ownerPathKey(p:String):String {if(mutex.held)retiredKeys++;return p.toLowerCase();}
 static function isRegistry(p:String):Bool return p=="assets/registry.json";
 static function buildAssetIndexBindings(m:Dynamic,r:Array<String>):Map<String,Dynamic> {
  if(mutex.held)throw "binding computation under lock";return new Map();
 }
 static function updateAssetIndexBindingsLocked(r:Array<String>,m:Map<String,Dynamic>):Void {
  if(!mutex.held)throw "non-atomic binding publication";
 }
 METHODS
 static function check(p:String,expected:Array<String>) {
  var result=committedPathOwners.get(p.toLowerCase());
  if(haxe.Json.stringify(result)!=haxe.Json.stringify(expected))throw p+": "+haxe.Json.stringify(result);
 }
 static function main() {
  var roots=[for(i in 0...8) "assets/imported_mods/root"+i];
  var files:Array<Dynamic>=[for(i in 0...1000) {path:"assets/data/file"+i+".json"}];
  addCommittedPathOwners({files:files},roots);
  addCommittedPathOwners({files:[{path:"assets/data/file0.json"},{path:"assets/data/external.json"}]},["external"]);
  retiredKeys=0;
  addCommittedPathOwners({files:[{path:"assets/data/NEW.json"},{path:"assets/data/new.json"},
   {path:"assets/data/new.json"},{path:"../escape"},{path:"assets/registry.json"}]},roots.concat([roots[0]]));
  if(mutex.held || retiredKeys!=1000)throw "repeated retirement or leaked lock: "+retiredKeys;
  check("assets/data/file0.json",["external"]);check("assets/data/file1.json",null);
  check("assets/data/new.json",roots);check("assets/registry.json",null);check("../escape",null);
  if(committedPathsByOwner.get(roots[0]).length!=2)throw "path spelling/dedup changed";
  committedPathsByOwner.get(roots[0]).push("sentinel");
  if(committedPathsByOwner.get(roots[1]).indexOf("sentinel")>=0)throw "root path arrays alias";
  committedPathsByOwner.get(roots[0]).pop();
  retiredKeys=0;addCommittedPathOwners({files:[]},roots);
  if(retiredKeys!=2)throw "unexpected path normalization count";
  check("assets/data/new.json",null);check("assets/data/file0.json",["external"]);
  check("assets/data/external.json",["external"]);
 }
}
'''.replace("METHODS",methods)
        with tempfile.TemporaryDirectory() as folder:
            (FixturePath(folder)/"OwnershipFixture.hx").write_text(fixture,newline="\n")
            result=subprocess.run([*HAXE_COMMAND,"-cp",folder,"--run","OwnershipFixture"],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
