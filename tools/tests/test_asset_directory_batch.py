"""Read-only asset lookup batches preserve resolution without repeated directory scans."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath,write_multiplayer_stubs
from test_native_asset_resolution import extract_method
ROOT=Path(__file__).resolve().parents[2]
class AssetDirectoryBatchTest(unittest.TestCase):
    def test_bounded_batch_preserves_case_scope_and_freshness(self):
        source=(ROOT/"source/FNFAssets.hx").read_text()
        resolver=extract_method(source,"static function resolveDiskPath(")
        fixture=r'''import haxe.io.Path;
using StringTools;
class Main { public static var cwd="/game"; }
class FileSystem {
 public static var files:Map<String,Bool>=new Map();
 public static var reads=0;
 public static function absolutePath(p:String):String return Path.normalize(Path.isAbsolute(p)?p:"/game/"+p);
 public static function exists(p:String):Bool return files.exists(p);
 public static function isDirectory(p:String):Bool return files.get(p)==true;
 public static function readDirectory(p:String):Array<String> {
  reads++; if(!isDirectory(p)) throw "missing directory";
  var prefix=p+"/";
  return [for(k in files.keys()) if(k.startsWith(prefix) && k.substr(prefix.length).indexOf("/")<0) k.substr(prefix.length)];
 }
}
class BatchFixture {
 static var caseResolvedPaths:Map<String,String>=new Map();
 RESOLVER
 static function main() {
  for(p in ["/game","/game/assets","/game/assets/data","/game/assets/data/owner"])
   FileSystem.files.set(p,true);
  for(i in 0...500) FileSystem.files.set("/game/assets/data/other"+i,true);
  FileSystem.files.set("/game/assets/data/owner/Present.JSON",false);
  FileSystem.files.set("/game/assets/data/owner/Ambiguous.json",false);
  FileSystem.files.set("/game/assets/data/owner/aMBIGUOUS.json",false);
  FileSystem.files.set("/game/assets/data/owner/ambiguouS.json",false);
  var paths=[for(i in 0...40) "assets/data/owner/missing"+i+".json"];
  paths.push("assets/data/owner/present.json");
  paths.push("assets/data/owner/AMBIGUOUS.json");
  paths.push("../outside/file.json");
  paths.push("/game-evil/file.json");
  paths.push(null); paths.push("");
  var expected=[for(p in paths) resolveDiskPath(p)];
  var oldReads=FileSystem.reads; caseResolvedPaths.clear(); FileSystem.reads=0;
  var batch:Map<String,Map<String,String>>=new Map();
  var actual=[for(p in paths) resolveDiskPath(p,batch)];
  if(haxe.Json.stringify(expected)!=haxe.Json.stringify(actual)) throw "resolution changed";
  if(FileSystem.reads!=4 || FileSystem.reads*20>=oldReads) throw "directory scans were not shared";
  if(actual[41]!=null) throw "ambiguous case was selected";
  if(resolveDiskPath("assets/data/owner/Ambiguous.json",batch)==null) throw "exact path priority changed";
  FileSystem.files.remove("/game/assets/data/owner/Present.JSON");
  if(resolveDiskPath("assets/data/owner/present.json",batch)!=null) throw "deleted positive survived";
  FileSystem.files.set("/game/assets/data/owner/New.JSON",false);
  if(resolveDiskPath("assets/data/owner/new.json",new Map())==null) throw "next batch missed a new file";
  if(resolveDiskPath("assets/data/owner/new.json")==null) throw "ordinary lookup missed a new file";
  FileSystem.files.set("/game/assets/data/owner/missing0.json",false);
  if(resolveDiskPath("assets/data/owner/missing0.json",batch)==null) throw "exact native hit was cached away";
 }
}
'''.replace("RESOLVER",resolver)
        with tempfile.TemporaryDirectory() as folder:
            (FixturePath(folder)/"BatchFixture.hx").write_text(fixture,newline="\n")
            write_multiplayer_stubs(folder)
            result=subprocess.run([*HAXE_COMMAND,"-cp",folder,"--run","BatchFixture"],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
