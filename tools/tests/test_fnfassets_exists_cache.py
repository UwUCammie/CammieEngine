"""Repeated probes for a missing asset do not list directories again."""
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_native_asset_resolution import extract_method

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class FNFAssetsExistsCacheTest(unittest.TestCase):
    def run_fixture(self, name, source):
        with tempfile.TemporaryDirectory() as folder:
            (FixturePath(folder) / (name + ".hx")).write_text(source, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"), "--run", name],
                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_probe_resolver_remembers_misses_without_hiding_new_files(self):
        source = (ROOT / "source/FNFAssets.hx").read_text(encoding="utf-8")
        resolver = extract_method(source, "static function resolveDiskPath(")
        probed = extract_method(source, "static function resolveProbedDiskPath(")
        scoped = extract_method(source, "static function inScopeAbsolutePath(")
        invalidate = extract_method(source, "public static function invalidatePathCache(")
        fixture = r'''import haxe.io.Path;
using StringTools;
class Main { public static var cwd="/game"; }
class ImportRefreshManager { public static var generation:Int = 0; }
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
class ExistsCacheFixture {
 static var caseResolvedPaths:Map<String,String>=new Map();
 static var pathMisses:DiskPathMissCache = new DiskPathMissCache();
 static var localPathEpoch:Int = 0;
 #if target.threaded static var pathLock:sys.thread.Mutex = new sys.thread.Mutex(); #end
 RESOLVER
 PROBED
 SCOPED
 INVALIDATE
 static function fail(message:String):Void throw message;
 static function main() {
  for(p in ["/game","/game/assets","/game/assets/images","/game/assets/images/pack"])
   FileSystem.files.set(p,true);
  FileSystem.files.set("/game/assets/images/pack/Icon.png",false);
  FileSystem.files.set("/game/assets/images/pack/icon.png",false);
  FileSystem.files.set("/game/assets/images/pack/Real.PNG",false);

  var missing="assets/images/pack/num7.png";
  if(resolveProbedDiskPath(missing)!=null) fail("a missing file resolved");
  var firstReads=FileSystem.reads;
  if(firstReads==0) fail("the first miss did not look for a case variant");
  for(i in 0...200) if(resolveProbedDiskPath(missing)!=null) fail("a repeated miss resolved");
  if(FileSystem.reads!=firstReads) fail("a repeated miss listed directories again: "+(FileSystem.reads-firstReads));

  // The exact spelling is always asked for, so a new file shows up at once.
  FileSystem.files.set("/game/assets/images/pack/num7.png",false);
  if(resolveProbedDiskPath(missing)==null) fail("a file created after a miss stayed hidden");
  FileSystem.files.remove("/game/assets/images/pack/num7.png");
  if(resolveProbedDiskPath(missing)!=null) fail("a deleted file kept resolving");

  // A file under another letter case is found once the layer is told.
  var folded="assets/images/pack/late.png";
  if(resolveProbedDiskPath(folded)!=null) fail("late file resolved early");
  FileSystem.files.set("/game/assets/images/pack/Late.PNG",false);
  invalidatePathCache();
  if(resolveProbedDiskPath(folded)==null) fail("invalidate did not drop the remembered miss");

  // So does a library refresh.
  var imported="assets/images/pack/imported.png";
  if(resolveProbedDiskPath(imported)!=null) fail("imported file resolved early");
  FileSystem.files.set("/game/assets/images/pack/Imported.png",false);
  ImportRefreshManager.generation++;
  if(resolveProbedDiskPath(imported)==null) fail("a library refresh did not drop the remembered miss");

  // Hits and the ambiguity rule are untouched.
  if(resolveProbedDiskPath("assets/images/pack/real.png")==null) fail("a case-folded hit was lost");
  if(resolveProbedDiskPath("assets/images/pack/ICON.png")!=null) fail("an ambiguous spelling was guessed");
  if(resolveProbedDiskPath("assets/images/pack/ICON.png")!=null) fail("an ambiguous spelling was guessed on repeat");
  var outside:Array<String>=[null, "", "../outside/file.png", "/game-evil/file.png"];
  for(bad in outside)
   if(resolveProbedDiskPath(bad)!=null) fail("an out of scope id resolved: "+bad);
  if(pathMisses.missedAt("../outside/file.png", ImportRefreshManager.generation+localPathEpoch, haxe.Timer.stamp())!=null)
   fail("an out of scope id was remembered");
 }
}
'''.replace("RESOLVER", resolver).replace("PROBED", probed).replace("SCOPED", scoped).replace("INVALIDATE", invalidate)
        self.run_fixture("ExistsCacheFixture", fixture)

    def test_remembered_misses_age_out_and_stay_bounded(self):
        fixture = r'''class MissCacheFixture {
 static function fail(message:String):Void throw message;
 static function main() {
  var cache = new DiskPathMissCache();
  cache.remember("a.png", "/game/a.png", 0, 10.0);
  if (cache.missedAt("a.png", 0, 10.5) != "/game/a.png") fail("a fresh miss was not remembered");
  if (cache.missedAt("b.png", 0, 10.5) != null) fail("an unknown id was reported as missed");
  if (cache.missedAt("a.png", 0, 10.0 + DiskPathMissCache.LIFETIME_SECONDS + 0.01) != null)
   fail("a miss outlived its lifetime");
  cache.remember("a.png", "/game/a.png", 0, 20.0);
  if (cache.missedAt("a.png", 1, 20.1) != null) fail("a miss survived an epoch change");
  cache.remember("a.png", "/game/a.png", 1, 30.0);
  if (cache.missedAt("a.png", 1, 29.0) != null) fail("a clock stepping backwards kept old misses");
  cache.remember("a.png", "/game/a.png", 1, 40.0);
  cache.forget("a.png");
  if (cache.count() != 0 || cache.missedAt("a.png", 1, 40.0) != null) fail("forget left the miss behind");
  cache.remember(null, "/game/x", 1, 40.0);
  cache.remember("x", null, 1, 40.0);
  if (cache.count() != 0) fail("an unusable miss was stored");
  for (i in 0...(DiskPathMissCache.MAX_ENTRIES * 3))
   cache.remember("id" + i, "/game/id" + i, 1, 40.0);
  if (cache.count() > DiskPathMissCache.MAX_ENTRIES) fail("the miss map grew without bound");
 }
}'''
        self.run_fixture("MissCacheFixture", fixture)

    def test_exists_uses_the_probe_resolver_and_saves_invalidate(self):
        source = (ROOT / "source/FNFAssets.hx").read_text(encoding="utf-8")
        exists = extract_method(source, "static public function exists(")
        self.assertIn("directoryEntries == null ? resolveProbedDiskPath(id) : resolveDiskPath(id, directoryEntries)", exists)
        for marker in ("public static function saveContent(", "public static function saveBytes("):
            self.assertIn("invalidatePathCache();", extract_method(source, marker))
        # The plain resolver keeps answering fresh for readers that need it.
        self.assertNotIn("pathMisses", extract_method(source, "static function resolveDiskPath("))


if __name__ == "__main__":
    unittest.main()
