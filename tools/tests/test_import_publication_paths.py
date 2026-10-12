"""Publication path deduplication preserves readiness locks and transaction inputs."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_native_asset_resolution import extract_method
ROOT = Path(__file__).resolve().parents[2]


def fixture(source, body):
    methods = '\n'.join(extract_method(source, marker) for marker in (
        'static function setReservationPaths(', 'static function normalizeInstallRelative(',
        'static function ownerRootFromInstalledPath('))
    start = source.index('var publishedPaths = masked.copy();')
    end = source.index('setReservationPaths(reservationToken, publishedPaths);', start)
    collection = source[start:end]
    return r'''import haxe.io.Path;
class Mutex {
 public var held=false;
 public function new(){}
 public function acquire(){if(held)throw "nested lock";held=true;}
 public function release(){if(!held)throw "unbalanced lock";held=false;}
}
class Main {
 static var mutex=new Mutex();
 static var reservations:Map<String,Dynamic>=new Map();
 static var bumps=0;
 static var steps=0;
 static var expanded:Array<String>=[];
 static function bumpAvailabilityLocked(){if(!mutex.held)throw "unlocked mutation";bumps++;}
 static function ownerRootForNamespace(s:String):String return "assets/imported_mods/"+s;
 static function expandDependentOwnerRoots(a:Array<String>):Array<String> {
  if(mutex.held)throw "expansion under lock";expanded=a.copy();
  return a.length==0?a:a.concat(["dependent"]);
 }
 static function cooperateImportWork(cancel:Void->Bool):Void {
  steps++;if(cancel!=null && cancel())throw "cancelled";
 }
 METHODS
 static function collect(masked:Array<String>, outputs:Array<{path:String}>, cancel:Void->Bool):Array<String> {
 COLLECTION
 return publishedPaths;
 }
 static function check(v:Bool,m:String):Void if(!v)throw m;
 static function equal(a:Dynamic,b:Dynamic):Bool return haxe.Json.stringify(a)==haxe.Json.stringify(b);
 static function main() { BODY }
}'''.replace('METHODS', methods).replace('COLLECTION', collection).replace('BODY', body)


class ImportPublicationPathsTest(unittest.TestCase):
    def test_order_normalization_owner_expansion_and_cancellation(self):
        source=(ROOT/'source/ImportRefreshManager.hx').read_text()
        body=r'''
 var masked=["keep","keep","A","a"];
 var outputs=[{path:"keep"},{path:"A"},{path:"a"},{path:"new"},{path:"new"},{path:"New"}];
 check(equal(collect(masked,outputs,null),["keep","keep","A","a","new","New"]),"exact order and duplicates");
 check(equal(masked,["keep","keep","A","a"]),"input mutated");
 check(steps>=outputs.length,"cooperation dropped");
 var cancelled=false;
 try collect(masked,outputs,function() return true) catch(e:Dynamic) cancelled=e=="cancelled";
 check(cancelled,"cancellation lost");
 reservations.set("owner",{touchedPaths:[],roots:["original"]});
 var paths=[" ./assets/imported_mods/alpha/image.png ","assets/imported_mods/alpha/image.png",
  "assets\\imported_mods\\beta\\icon.png","assets/data/A.json","assets/data/a.json",
  "../escape","C:/escape","",null];
 setReservationPaths("owner",paths);
 check(equal(reservations.get("owner").touchedPaths,["assets/data/A.json","assets/data/a.json",
  "assets/imported_mods/alpha/image.png","assets/imported_mods/beta/icon.png"]),"normalized paths");
 check(equal(expanded,["assets/imported_mods/alpha","assets/imported_mods/beta"]),"owner expansion input");
 check(equal(reservations.get("owner").roots,["assets/imported_mods/alpha","assets/imported_mods/beta","dependent","original"]),"owner locks");
 check(bumps==1 && !mutex.held,"atomic revision");
 paths.reverse();setReservationPaths("owner",paths);check(bumps==1,"unchanged snapshot invalidated");
 setReservationPaths("missing",paths);check(bumps==1 && !mutex.held,"missing reservation recreated");
 setReservationPaths("owner",null);check(bumps==2 && reservations.get("owner").touchedPaths.length==0,"clear paths");
 check(reservations.get("owner").roots.length==4,"existing owner locks lost");
 '''
        with tempfile.TemporaryDirectory() as folder:
            (FixturePath(folder)/'Main.hx').write_text(fixture(source,body),newline='\n')
            result=subprocess.run([*HAXE_COMMAND,'-cp',folder,'--run','Main'],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
