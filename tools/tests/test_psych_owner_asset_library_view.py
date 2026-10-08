"""Owner identity guards stop stale Lime library IO and Future publication."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PsychOwnerAssetLibraryViewTest(unittest.TestCase):
    def test_stale_library_rejects_reads_and_async_completion(self):
        fixture = r'''package;
import haxe.io.Bytes;
import lime.app.Future;
import lime.app.Promise;
import lime.utils.AssetType;
import lime.utils.AssetLibrary;

@:access(lime.utils.AssetLibrary)
class SlowAssetLibrary extends AssetLibrary {
 public var pending:Promise<Bytes>;
 public function new() {
  super();
  types.set("delayed",AssetType.BINARY);
  preload.set("delayed",true);
  sizes.set("delayed",4);
  paths.set("delayed","delayed.bin");
 }
 public function hasCachedBytes(id:String):Bool return cachedBytes.exists(id);
 override public function loadBytes(id:String):Future<Bytes> {
  pending=new Promise<Bytes>();
  return pending.future;
 }
}

class Main {
 static function check(value:Bool,message:String):Void if(!value)throw message;
 static function main():Void {
  var active=true;
  var delegate=new SlowAssetLibrary();
  var library=new PsychOwnerAssetLibraryView(delegate,function()return active);
  var completed=false;
  var failure="";
  var read=library.loadBytes("delayed");
  read.onComplete(function(_bytes:Bytes) completed=true);
  read.onError(function(error:Dynamic) failure=Std.string(error));

  active=false;
  delegate.pending.complete(Bytes.ofString("stale bytes"));
  check(!completed,"a Future published bytes after its owner identity expired");
  check(failure.indexOf("identity changed")>=0,"stale Future did not report the owner identity expiry");

  var syncRejected=false;
  try library.getPath("delayed") catch(error:Dynamic)
   syncRejected=Std.string(error).indexOf("identity changed")>=0;
  check(syncRejected,"a retained library performed a lazy synchronous read after identity expiry");
  var asyncRejected=false;
  var staleLoad=library.loadText("delayed");
  staleLoad.onError(function(error:Dynamic) asyncRejected=Std.string(error).indexOf("identity changed")>=0);
  check(asyncRejected,"a retained library did not reject a new async read after identity expiry");

  var preloadActive=true;
  var preloadingDelegate=new SlowAssetLibrary();
  var preloadingView=new PsychOwnerAssetLibraryView(preloadingDelegate,function()return preloadActive);
  var published=false;
  var preloadFailure="";
  var preload=preloadingView.load();
  preload.onComplete(function(_library:AssetLibrary) published=true);
  preload.onError(function(error:Dynamic) preloadFailure=Std.string(error));
  preloadActive=false;
  preloadingDelegate.pending.complete(Bytes.ofString("late"));
  check(!published,"preload Future completed after owner invalidation");
  check(preloadFailure.indexOf("identity changed")>=0,"preload Future did not report owner invalidation");
  check(!preloadingDelegate.hasCachedBytes("delayed"),
   "a preload callback repopulated the retired Lime delegate after owner invalidation");
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            env = dict(os.environ)
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
            env["PATH"] = os.pathsep.join(
                [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
            )
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "-lib", "lime", "--main", "Main", "--interp"],
                cwd=work,
                env=env,
                text=True,
                capture_output=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
