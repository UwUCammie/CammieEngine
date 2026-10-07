"""The staged importer worker must keep its owner index off the live thread."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source"


IMPORT_IO = r'''package;
import haxe.io.Path;
import sys.FileSystem as RawFileSystem;
import sys.thread.Tls;
class ImportIO {
 static var currentContext:Tls<ImportIO> = new Tls();
 public var root:String;
 public function new(root:String) this.root=RawFileSystem.fullPath(root);
 public static function begin(root:String):Void currentContext.value=new ImportIO(root);
 public static function current():Null<ImportIO> return currentContext.value;
 function mapped(path:String):String return Path.isAbsolute(path)?path:Path.join([root,path]);
 public function exists(path:String):Bool return RawFileSystem.exists(mapped(path));
 public function isDirectory(path:String):Bool return RawFileSystem.isDirectory(mapped(path));
 public function readDirectory(path:String):Array<String> return RawFileSystem.readDirectory(mapped(path));
 public function stat(path:String):sys.FileStat return RawFileSystem.stat(mapped(path));
 public function fullPath(path:String):String return RawFileSystem.fullPath(mapped(path));
 public function absolutePath(path:String):String return RawFileSystem.absolutePath(mapped(path));
 public function sourceLabel(path:String):String return null;
 public function hasOwnedPath(path:String):Bool return false;
}'''

IMPORT_FILE_SYSTEM = r'''package;
import sys.FileSystem as RawFileSystem;
class ImportFileSystem {
 static function context() return ImportIO.current();
 public static function exists(path:String):Bool {var c=context();return c==null?RawFileSystem.exists(path):c.exists(path);}
 public static function isDirectory(path:String):Bool {var c=context();return c==null?RawFileSystem.isDirectory(path):c.isDirectory(path);}
 public static function readDirectory(path:String):Array<String> {var c=context();return c==null?RawFileSystem.readDirectory(path):c.readDirectory(path);}
 public static function stat(path:String):sys.FileStat {var c=context();return c==null?RawFileSystem.stat(path):c.stat(path);}
 public static function fullPath(path:String):String {var c=context();return c==null?RawFileSystem.fullPath(path):c.fullPath(path);}
 public static function absolutePath(path:String):String {var c=context();return c==null?RawFileSystem.absolutePath(path):c.absolutePath(path);}
 public static function rename(path:String,next:String):Void RawFileSystem.rename(path,next);
 public static function createDirectory(path:String):Void RawFileSystem.createDirectory(path);
 public static function deleteFile(path:String):Void RawFileSystem.deleteFile(path);
 public static function deleteDirectory(path:String):Void RawFileSystem.deleteDirectory(path);
}'''

IMPORT_FILE = r'''package;
import sys.io.File as RawFile;
class ImportFile {
 public static function getContent(path:String):String {var c=ImportIO.current();return RawFile.getContent(c==null?path:c.fullPath(path));}
 public static function saveContent(path:String,value:String):Void RawFile.saveContent(path,value);
}'''

COMPAT_SCRIPT_MANIFEST = r'''package;
class CompatScriptManifest {
 public static inline var ROOT_PREFIX="assets/imported_mods";
 public static inline var FILE_NAME="compatScripts.json";
 public var roots:Array<Dynamic>=[];
 public function new() {}
 public static function destinationKey(value:String):String return value==null?"":StringTools.replace(value,"\\","/");
 public static function destinationRoot(source:String,engine:String):String return ROOT_PREFIX+"/fixture-owner";
 public static function namespaceFor(source:String,engine:String):String return "fixture-owner";
 public static function parse(value:String):CompatScriptManifest return new CompatScriptManifest();
 public static function selectedRoot(value:CompatScriptManifest):String return "";
}'''

MAIN = r'''package;
import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
import sys.thread.Lock;
import sys.thread.Thread;
@:access(ImportSongOwnership)
class Main {
 static function ensure(value:Bool,message:String):Void if(!value)throw message;
 static function main():Void {
  var args=Sys.args();var rootA=args[0];var rootB=args[1];
  for(root in [rootA,rootB]) {
   FileSystem.createDirectory(Path.join([root,"assets/data/song"]));
   FileSystem.createDirectory(Path.join([root,"import-cache/staging"]));
  }
  File.saveContent(Path.join([rootA,"assets/data/song/importProvenance.json"]),Json.stringify({
   version:1,destinationFolder:"song",sourceEngine:"Psych Engine",
   sourceOwner:"assets/imported_mods/owner-a",sourceIdentity:"psych engine|id|fixture"
  }));
  File.saveContent(Path.join([rootB,"assets/data/song/importProvenance.json"]),Json.stringify({
   version:1,destinationFolder:"song",sourceEngine:"Psych Engine",
   sourceOwner:"assets/imported_mods/owner-b",sourceIdentity:"psych engine|id|fixture"
  }));

  ImportIO.begin(rootA);
  ImportSongOwnership.invalidateOwnerIdentityIndex();
  var mainCache=ImportSongOwnership.ownerIdentityCache();
  ImportSongOwnership.buildOwnerIdentityIndex(mainCache);
  ensure(mainCache.index.get("psych engine|id|fixture")=="owner-a","main thread did not read its installed tree");

  var workerCache:Dynamic=null;var workerOwner="";var failed:Dynamic=null;var done=new Lock();
  Thread.create(function() {
   try {
    ImportIO.begin(rootB);
    ImportSongOwnership.invalidateOwnerIdentityIndex();
    workerCache=ImportSongOwnership.ownerIdentityCache();
    ImportSongOwnership.buildOwnerIdentityIndex(workerCache);
    workerOwner=workerCache.index.get("psych engine|id|fixture");
    ImportSongOwnership.invalidateOwnerIdentityIndex();
    if(workerCache.ready) throw "worker invalidation did not target its own cache";
   } catch(error:Dynamic) failed=error;
   done.release();
  });
  done.wait();
  ensure(failed==null,"worker cache read failed: "+Std.string(failed));
  ensure(workerOwner=="owner-b","worker did not read its staged filesystem view");
  ensure(workerCache!=mainCache,"main and worker shared mutable cache identity");
  ensure(mainCache.ready&&mainCache.index.get("psych engine|id|fixture")=="owner-a",
   "worker cache build or invalidation replaced the live owner index");
  ImportSongOwnership.invalidateOwnerIdentityIndex();
  ensure(!mainCache.ready&&workerCache.ready==false,"main invalidation did not remain thread-local");
  Sys.println("owner identity caches are thread-local");
 }
}'''


class ImportSongOwnershipThreadLocalTest(unittest.TestCase):
    def test_worker_staging_index_cannot_replace_live_owner_index(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temp:
            temp_path = Path(temp)
            ownership = (SOURCE / "ImportSongOwnership.hx").read_text(encoding="utf-8")
            self.assertEqual(ownership.count("#if target.threaded"), 2)
            # Eval supports sys.thread.Tls but does not set target.threaded. Force
            # only that target condition so the production branch is exercised.
            (temp_path / "ImportSongOwnership.hx").write_text(
                ownership.replace("#if target.threaded", "#if sys"), encoding="utf-8", newline="\n")
            (temp_path / "ImportIO.hx").write_text(IMPORT_IO, encoding="utf-8", newline="\n")
            (temp_path / "ImportFileSystem.hx").write_text(IMPORT_FILE_SYSTEM, encoding="utf-8", newline="\n")
            (temp_path / "ImportFile.hx").write_text(IMPORT_FILE, encoding="utf-8", newline="\n")
            (temp_path / "CompatScriptManifest.hx").write_text(COMPAT_SCRIPT_MANIFEST,
                encoding="utf-8", newline="\n")
            (temp_path / "ImportEngine.hx").write_text(
                (SOURCE / "ImportEngine.hx").read_text(encoding="utf-8"),
                encoding="utf-8", newline="\n")
            (temp_path / "Main.hx").write_text(MAIN, encoding="utf-8", newline="\n")
            root_a = temp_path / "install-a"
            root_b = temp_path / "install-b"
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", temp, "--run", "Main", str(root_a), str(root_b)],
                cwd=temp, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("owner identity caches are thread-local", result.stdout)


if __name__ == "__main__":
    unittest.main()
