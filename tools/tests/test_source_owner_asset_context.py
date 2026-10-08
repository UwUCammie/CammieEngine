"""Owner contexts keep source Lime/OpenFL Assets inside exact authenticated scopes."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class SourceOwnerAssetContextTest(unittest.TestCase):
    def test_nv_scope_boundaries_and_no_unindexed_fallback(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            owner = work / "assets/imported_mods/nv-owner"
            (owner / "data").mkdir(parents=True)
            (owner / "__nmv_core/data").mkdir(parents=True)
            (owner / "data/package-only.txt").write_text("package", encoding="utf-8")
            (owner / "__nmv_core/data/core-only.txt").write_text("core", encoding="utf-8")
            (work / "FNFAssets.hx").write_text(
                r'''package;
import haxe.io.Bytes;
import haxe.io.Path;
import openfl.display.BitmapData;
import openfl.media.Sound;
import sys.FileSystem;
import sys.io.File;
class FNFAssets {
 static function resolve(id:String):String return Path.normalize(id);
 public static function exists(id:String, ?ext:Dynamic):Bool return id != null && FileSystem.exists(resolve(id));
 public static function resolveCaseInsensitivePath(id:String):String return exists(id) ? resolve(id) : null;
 public static function getText(id:String):String return File.getContent(resolve(id));
 public static function getBytes(id:String):Bytes return File.getBytes(resolve(id));
 public static function getBitmapData(id:String, ?useCache:Bool=true):BitmapData return null;
 public static function getSound(id:String, ?useCache:Bool=true):Sound return null;
}''', encoding="utf-8", newline="\n")
            (work / "CompatScriptManifest.hx").write_text(
                'package; class CompatScriptManifest { public static inline var ROOT_PREFIX = "assets/imported_mods"; }',
                encoding="utf-8", newline="\n")
            (work / "ImportRefreshManager.hx").write_text(
                '''package;
class ImportRefreshManager {
 public static var generation:Int=1;
 public static function availabilityRevision():Int return 1;
 public static function ownerAssetIndexBinding(owner:String,engine:String,scope:String):Dynamic return null;
}''', encoding="utf-8", newline="\n")
            tjson = work / "tjson/TJSON.hx"
            tjson.parent.mkdir(parents=True, exist_ok=True)
            tjson.write_text(
                '''package tjson;
class TJSON {}
enum EncodeStyle { Full; }
class TJSONEncoder {
 public function new(){}
 public function doEncode(value:Dynamic,?style:String):String return haxe.Json.stringify(value);
 public function encodeValue(value:Dynamic,style:EncodeStyle,depth:Int):String return haxe.Json.stringify(value);
}''', encoding="utf-8", newline="\n")
            (work / "SourceOwnerAssetContextProbe.hx").write_text(
                r'''package;
import haxe.io.Bytes;
import lime.utils.AssetType;
import sys.FileSystem;
@:access(SourceCompositeAssetLibrary)
class SourceOwnerAssetContextProbe {
 static function check(value:Bool,message:String):Void if (!value) throw message;
 static function rejects(proxy:Dynamic,method:String,id:String):Bool {
  try Reflect.callMethod(proxy,Reflect.field(proxy,method),[id]) catch (error:Dynamic)
   return Std.string(error).indexOf("Asset is unavailable in selected owner") >= 0
    || Std.string(error).indexOf("Asset is unavailable to selected owner") >= 0;
  return false;
 }
 static function main():Void {
  var owner="assets/imported_mods/nv-owner";
  var packageContext=SourceOwnerAssetContext.nightmareVision(owner,"package");
  var coreContext=SourceOwnerAssetContext.nightmareVision(owner,"core");
  var assetsContext=SourceOwnerAssetContext.nightmareVisionAssets(owner);
  check(packageContext.identityScopes.length==1 && packageContext.identityScopes[0]=="package",
   "package context included another identity scope");
  check(coreContext.identityScopes.length==1 && coreContext.identityScopes[0]=="core",
   "core context included another identity scope");
  check(assetsContext.composite && assetsContext.identityScopes.join(",")=="package,core",
   "raw Assets context did not preserve package-over-core Project order");
  var packageLime=PsychOwnerLimeAssets.createForContext(packageContext);
  var coreLime=PsychOwnerLimeAssets.createForContext(coreContext);
  var compositeLime=PsychOwnerLimeAssets.createForContext(assetsContext);
  var packageOpenFl=PsychOwnerOpenFlAssets.createForContext(packageContext);
  var coreOpenFl=PsychOwnerOpenFlAssets.createForContext(coreContext);
  var compositeOpenFl=PsychOwnerOpenFlAssets.createForContext(assetsContext);
  var rawLibrary=SourceOwnerAssetContextCache.limeLibrary(assetsContext,"default",compositeLime);
  var rawOpenFlLibrary=SourceOwnerAssetContextCache.openFlLibrary(assetsContext,"default",compositeOpenFl);
  check(Std.isOfType(rawLibrary,lime.utils.AssetLibrary),
   "composite Lime getLibrary view is not an actual AssetLibrary");
  check(Std.isOfType(rawOpenFlLibrary,openfl.utils.AssetLibrary)
   &&Reflect.field(rawOpenFlLibrary,"__proxy")==rawLibrary,
   "composite OpenFL getLibrary view does not wrap the shared Lime library");
  check(rawLibrary.name=="default",
   "composite Lime library did not preserve its declared library name");
  var directLibraryChanges=0;
  var contextChanges=0;
  rawLibrary.onChange.add(function() directLibraryChanges++);
  var rawEvents=SourceOwnerAssetsEvents.forContext(assetsContext);
  rawEvents.addOnChange(function() contextChanges++);
  rawLibrary.onChange.dispatch();
  check(directLibraryChanges==1&&contextChanges==1,
   "manual composite library change did not reach its owner Assets event exactly once");
  var delegateLibrary=new lime.utils.AssetLibrary();
  rawLibrary.watchLibrary(delegateLibrary);
  delegateLibrary.onChange.dispatch();
  check(directLibraryChanges==2&&contextChanges==2,
   "delegate library change did not reach the composite and owner Assets event exactly once");
  rawLibrary.unload();
  delegateLibrary.onChange.dispatch();
  check(directLibraryChanges==2&&contextChanges==2,
   "composite library unload left delegate change listeners attached");
  rawLibrary.onChange.dispatch();
  check(directLibraryChanges==3&&contextChanges==3,
   "composite unload detached the still-active view's owner event bridge");
  var reloadedDelegateLibrary=new lime.utils.AssetLibrary();
  rawLibrary.watchLibrary(reloadedDelegateLibrary);
  reloadedDelegateLibrary.onChange.dispatch();
  check(directLibraryChanges==4&&contextChanges==4,
   "reloaded delegate did not forward one composite owner event");
  rawLibrary.retire();
  reloadedDelegateLibrary.onChange.dispatch();
  rawLibrary.onChange.dispatch();
  check(directLibraryChanges==5&&contextChanges==4,
   "retired composite view retained delegate or owner Assets event callbacks");
  check(!Reflect.callMethod(packageLime,Reflect.field(packageLime,"exists"),["data/package-only.txt",AssetType.TEXT]),
   "package facade read a loose file without receipt identity");
  check(rejects(packageLime,"getText","data/package-only.txt"),
   "package facade used a loose-file fallback without receipt identity");
  check(!Reflect.callMethod(coreLime,Reflect.field(coreLime,"exists"),["data/package-only.txt",AssetType.TEXT]),
   "core facade crossed into package files");
  check(rejects(coreLime,"getText","data/core-only.txt"),
   "core facade used an unindexed disk path");
  check(rejects(compositeLime,"getText","data/package-only.txt"),
   "composite facade used a package path without a committed package identity");
  check(rejects(compositeLime,"getText","data/core-only.txt"),
   "composite facade used a core path without a committed core identity");
  check(rejects(packageOpenFl,"getText","data/package-only.txt"),
   "OpenFL package facade used an unindexed disk path");
  check(rejects(coreOpenFl,"getText","data/core-only.txt"),
   "OpenFL core facade used an unindexed disk path");
  check(rejects(compositeOpenFl,"getText","data/package-only.txt"),
   "OpenFL composite facade used an unindexed package path");
  check(rejects(compositeOpenFl,"getText","data/core-only.txt"),
   "OpenFL composite facade used an unindexed core path");
  check(Reflect.callMethod(compositeLime,Reflect.field(compositeLime,"list"),[AssetType.TEXT]).length==0,
   "composite list exposed owner files without receipt identity");
  check(PsychOwnerAssetPath.resolveInScope(owner,"data/core-only.txt",owner+"/__nmv_core").owned,
   "core subtree path resolver rejected its selected tree");
  check(PsychOwnerAssetPath.resolveInScope(owner,
   "assets/imported_mods/nv-owner/__nmv_core/data/core-only.txt",owner,"__nmv_core").blocked,
   "package path resolver accepted the reserved core subtree");
  check(PsychOwnerAssetPath.resolveInScope(owner,"data/../__nmv_core/data/core-only.txt",owner).blocked,
   "scope path resolver accepted traversal");
  var retiredOwner=owner+"/retired";
  FileSystem.createDirectory(retiredOwner);
  var retiredContext=SourceOwnerAssetContext.nightmareVisionAssets(retiredOwner);
  var retiredCache=SourceOwnerAssetContextCache.lime(retiredContext);
  var retiredEvents=SourceOwnerAssetsEvents.forContext(retiredContext);
  FileSystem.deleteDirectory(retiredOwner);
  PsychOwnerAssetPath.releaseOwner(retiredOwner);
  FileSystem.createDirectory(retiredOwner);
  var renewedContext=SourceOwnerAssetContext.nightmareVisionAssets(retiredOwner);
  var renewedCache=SourceOwnerAssetContextCache.lime(renewedContext);
  var renewedEvents=SourceOwnerAssetsEvents.forContext(renewedContext);
  check(retiredCache!=renewedCache,
   "owner release after directory removal retained the old composite cache");
  check(retiredEvents!=renewedEvents,
   "identity owner release after directory removal retained the old event provider");
 }
}''', encoding="utf-8", newline="\n")
            env = dict(os.environ)
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
            env["PATH"] = os.pathsep.join(
                [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
            )
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "-lib", "lime", "-lib", "openfl", "--run", "SourceOwnerAssetContextProbe"],
                cwd=work, env=env, text=True, capture_output=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
