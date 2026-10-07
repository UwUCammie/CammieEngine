"""Psych compiled-stage Lime Assets calls stay inside the selected import owner."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def haxe_env():
    env = dict(os.environ)
    env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
    env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
    env["PATH"] = os.pathsep.join(
        [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
    )
    return env


class PsychOwnerLimeAssetsTest(unittest.TestCase):
    def test_owner_precedence_sibling_rejection_and_native_fallback(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            root = work / "assets/imported_mods/psych-owner-a"
            sibling = work / "assets/imported_mods/psych-owner-b"
            (root / "data").mkdir(parents=True)
            (sibling / "data").mkdir(parents=True)
            (root / "shared").mkdir(parents=True)
            (work / "assets/data").mkdir(parents=True)
            (root / "data/value.txt").write_text("owner-a", encoding="utf-8", newline='\n')
            (sibling / "data/value.txt").write_text("owner-b", encoding="utf-8", newline='\n')
            (work / "assets/data/native-only.txt").write_text("native", encoding="utf-8", newline='\n')
            symlink_available = True
            try:
                (root / "shared/escape").symlink_to(sibling / "data", target_is_directory=True)
            except (OSError, NotImplementedError):
                symlink_available = False
            (work / "symlink-available.txt").write_text(
                "1" if symlink_available else "0", encoding="utf-8", newline='\n'
            )
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
 public static function getBitmapData(id:String, ?useCache:Bool = true):BitmapData return null;
 public static function getSound(id:String, ?useCache:Bool = true):Sound return null;
}''', encoding="utf-8"
            , newline='\n')
            (work / "CompatScriptManifest.hx").write_text(
                'package; class CompatScriptManifest { public static inline var ROOT_PREFIX = "assets/imported_mods"; }',
                encoding="utf-8",
             newline='\n')
            (work / "ImportRefreshManager.hx").write_text(
                '''package;
class ImportRefreshManager {
 public static var generation:Int=1;
 public static var revision:Int=1;
 public static var binding:Dynamic;
 public static function availabilityRevision():Int return revision;
 public static function ownerAssetIndexBinding(owner:String,engine:String,scope:String):Dynamic return binding;
                }''', encoding="utf-8", newline='\n')
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
}''', encoding="utf-8", newline='\n')
            (work / "PsychOwnerLimeAssetsProbe.hx").write_text(
                r'''package;
import lime.utils.Assets;
import lime.utils.AssetLibrary;
import openfl.utils.Assets as NativeOpenFlAssets;
import openfl.utils.AssetLibrary as NativeOpenFlAssetLibrary;
import haxe.crypto.Sha256;
import haxe.io.Bytes;
import sys.io.File;
class PsychOwnerLimeAssetsProbe {
 static function hash(bytes:Bytes):String return Sha256.make(bytes).toHex();
 static function main():Void {
  var owner = "assets/imported_mods/psych-owner-a";
  var invalidOwnerRejected = false;
  try PsychOwnerLimeAssets.create("") catch (error:Dynamic) {
   invalidOwnerRejected = Std.string(error).indexOf("valid selected import owner root") >= 0;
  }
  if (!invalidOwnerRejected) throw "empty owner root silently exposed native Lime assets";
  var missingOwnerRejected = false;
  try PsychOwnerLimeAssets.create("assets/imported_mods/missing-owner") catch (error:Dynamic) {
   missingOwnerRejected = Std.string(error).indexOf("valid selected import owner root") >= 0;
  }
  if (!missingOwnerRejected) throw "missing owner directory silently exposed native Lime assets";
  var prefixRejected = false;
  try PsychOwnerLimeAssets.create("assets/imported_mods") catch (error:Dynamic) {
   prefixRejected = Std.string(error).indexOf("valid selected import owner root") >= 0;
  }
  if (!prefixRejected) throw "bare imports prefix was treated as one valid owner";
  var proxy:Dynamic = PsychOwnerLimeAssets.create(owner);
  if (Reflect.callMethod(proxy, Reflect.field(proxy, "getText"), ["assets/data/value.txt"]) != "owner-a")
   throw "relative Psych asset did not prefer its selected owner";
  if (!Reflect.callMethod(proxy, Reflect.field(proxy, "exists"), ["data/value.txt"]))
   throw "owner asset existence was not visible";
  if (Reflect.callMethod(proxy, Reflect.field(proxy, "getText"), ["assets/data/native-only.txt"]) != "native")
   throw "native asset fallback was lost";
  var sibling = "assets/imported_mods/psych-owner-b/data/value.txt";
  if (Reflect.callMethod(proxy, Reflect.field(proxy, "exists"), [sibling]))
   throw "sibling import asset crossed the selected owner boundary";
  var rejected = false;
  try Reflect.callMethod(proxy, Reflect.field(proxy, "getText"), [sibling]) catch (error:Dynamic) {
   rejected = Std.string(error).indexOf("outside selected owner") >= 0;
  }
  if (!rejected) throw "sibling import read did not produce an explicit ownership error";
  var symlink = "assets/shared/escape/value.txt";
  if (File.getContent("symlink-available.txt") == "1") {
   if (Reflect.callMethod(proxy, Reflect.field(proxy, "exists"), [symlink]))
    throw "Lime facade accepted an owner symlink into a sibling import";
   var symlinkRejected = false;
   try Reflect.callMethod(proxy, Reflect.field(proxy, "getText"), [symlink]) catch (error:Dynamic) {
    symlinkRejected = Std.string(error).indexOf("outside selected owner") >= 0;
   }
   if (!symlinkRejected) throw "Lime facade read through an owner symlink into a sibling import";
  }
  var limeLibraryRejected = false;
  try Reflect.callMethod(proxy, Reflect.field(proxy, "getLibrary"), ["assets/imported_mods/psych-owner-b/data"]) catch (error:Dynamic) {
   limeLibraryRejected = Std.string(error).indexOf("cannot escape the selected owner") >= 0;
  }
  if (!limeLibraryRejected) throw "Lime library lookup accepted a sibling namespace";
  var traversal = false;
  try Reflect.callMethod(proxy, Reflect.field(proxy, "getBytes"), ["assets/data/../../outside.txt"]) catch (error:Dynamic) {
   traversal = Std.string(error).indexOf("outside selected owner") >= 0;
  }
  if (!traversal) throw "asset traversal did not produce an explicit rejection";
  if (Reflect.field(proxy, "cache") != Assets.cache || Reflect.field(proxy, "onChange") != Assets.onChange)
   throw "the facade did not preserve Lime's cache/event API objects";

  var openfl:Dynamic = PsychOwnerOpenFlAssets.create(owner);
  if (Reflect.callMethod(openfl, Reflect.field(openfl, "getText"), ["assets/data/value.txt"]) != "owner-a")
   throw "relative OpenFL asset did not prefer its selected owner";
  if (Reflect.callMethod(openfl, Reflect.field(openfl, "getText"), ["assets/data/native-only.txt"]) != "native")
   throw "OpenFL native asset fallback was lost";
  if (Reflect.callMethod(openfl, Reflect.field(openfl, "exists"), [sibling]))
   throw "OpenFL facade crossed into a sibling import";
  var openflSiblingRejected = false;
  try Reflect.callMethod(openfl, Reflect.field(openfl, "getText"), [sibling]) catch (error:Dynamic) {
   openflSiblingRejected = Std.string(error).indexOf("outside selected owner") >= 0;
  }
  if (!openflSiblingRejected) throw "OpenFL sibling import read was not explicitly rejected";
  if (File.getContent("symlink-available.txt") == "1") {
   if (Reflect.callMethod(openfl, Reflect.field(openfl, "exists"), [symlink]))
    throw "OpenFL facade accepted an owner symlink into a sibling import";
   var openflSymlinkRejected = false;
   try Reflect.callMethod(openfl, Reflect.field(openfl, "getText"), [symlink]) catch (error:Dynamic) {
    openflSymlinkRejected = Std.string(error).indexOf("outside selected owner") >= 0;
   }
   if (!openflSymlinkRejected) throw "OpenFL facade read through an owner symlink into a sibling import";
  }
  var openflLibraryRejected = false;
  try Reflect.callMethod(openfl, Reflect.field(openfl, "getLibrary"), ["assets/imported_mods/psych-owner-b/data"]) catch (error:Dynamic) {
   openflLibraryRejected = Std.string(error).indexOf("cannot escape the selected owner") >= 0;
  }
  if (!openflLibraryRejected) throw "OpenFL library lookup accepted a sibling namespace";
  var movieClipRejected = false;
  try Reflect.callMethod(openfl, Reflect.field(openfl, "getMovieClip"), ["assets/imported_mods/psych-owner-b:data:Clip"]) catch (error:Dynamic) {
   movieClipRejected = Std.string(error).indexOf("cannot escape the selected owner") >= 0;
  }
  if (!movieClipRejected) throw "OpenFL movie-clip lookup accepted a sibling namespace";
  var movieClipPathRejected = false;
  try Reflect.callMethod(openfl, Reflect.field(openfl, "getMovieClip"), ["assets/imported_mods/psych-owner-b/data/clip.swf"]) catch (error:Dynamic) {
   movieClipPathRejected = Std.string(error).indexOf("cannot escape the selected owner") >= 0;
  }
  if (!movieClipPathRejected) throw "OpenFL movie-clip lookup accepted a path outside its library ID contract";
  if (Reflect.field(openfl, "cache") != NativeOpenFlAssets.cache)
   throw "OpenFL facade did not preserve the native cache API object";
  // A declared owner library is a virtual sidecar view. Mutations must not
  // unload or replace a separate global library registered under the same name.
  var indexPath = owner + "/.cammie-asset-identities/psych.json";
  var index:Dynamic = {version:1,owner:owner,engine:"Psych Engine",scope:"package",namespace:"psych-owner-a",
   snapshotId:StringTools.lpad("","0",64),rootRelative:"content",projectSha256:StringTools.lpad("","1",64),
   complete:true,libraries:["default","lime-declared","openfl-declared"],librariesComplete:true,entries:[]};
  var indexBytes = Bytes.ofString(haxe.Json.stringify(index));
  sys.FileSystem.createDirectory(owner + "/.cammie-asset-identities");
  File.saveBytes(indexPath,indexBytes);
  ImportRefreshManager.generation++;
  ImportRefreshManager.revision++;
  ImportRefreshManager.binding={generation:ImportRefreshManager.generation,revision:ImportRefreshManager.revision,
   transactionId:"facade-test",owner:owner,engine:"Psych Engine",scope:"package",namespace:"psych-owner-a",
   snapshotId:index.snapshotId,rootRelative:"content",projectSha256:index.projectSha256,indexPath:indexPath,
   indexSha256:hash(indexBytes),files:[{path:indexPath,sha256:hash(indexBytes)}]};
  var limeGlobal = new AssetLibrary();
  Assets.registerLibrary("lime-declared",limeGlobal);
  if (!Reflect.callMethod(proxy,Reflect.field(proxy,"hasLibrary"),["lime-declared"]))
   throw "owner facade lost an empty declared library";
  if (Reflect.callMethod(proxy,Reflect.field(proxy,"getLibrary"),["lime-declared"]) == limeGlobal)
   throw "owner facade returned a same-named global library for a declared owner library";
  var limeUnloadRejected = false;
  try Reflect.callMethod(proxy,Reflect.field(proxy,"unloadLibrary"),["lime-declared"])
   catch (error:Dynamic) limeUnloadRejected = Std.string(error).indexOf("Dynamic unload is unsupported") >= 0;
  if (!limeUnloadRejected || Assets.getLibrary("lime-declared") != limeGlobal)
   throw "owner unload changed a same-named Lime global library";
  var limeRemoveRejected = false;
  try Reflect.callMethod(proxy,Reflect.field(proxy,"removeLibrary"),["lime-declared",true])
   catch (error:Dynamic) limeRemoveRejected = Std.string(error).indexOf("Dynamic remove is unsupported") >= 0;
  if (!limeRemoveRejected || Assets.getLibrary("lime-declared") != limeGlobal)
   throw "owner remove changed a same-named Lime global library";
  var limeRegisterRejected = false;
  try Reflect.callMethod(proxy,Reflect.field(proxy,"registerLibrary"),["lime-declared",new AssetLibrary()])
   catch (error:Dynamic) limeRegisterRejected = Std.string(error).indexOf("Dynamic register is unsupported") >= 0;
  if (!limeRegisterRejected || Assets.getLibrary("lime-declared") != limeGlobal)
   throw "owner register replaced a same-named Lime global library";
  var openflGlobal = new NativeOpenFlAssetLibrary();
  NativeOpenFlAssets.registerLibrary("openfl-declared",openflGlobal);
  if (!Reflect.callMethod(openfl,Reflect.field(openfl,"hasLibrary"),["openfl-declared"]))
   throw "OpenFL owner facade lost an empty declared library";
  if (Reflect.callMethod(openfl,Reflect.field(openfl,"getLibrary"),["openfl-declared"]) == openflGlobal)
   throw "OpenFL owner facade returned a same-named global library for a declared owner library";
  var openflUnloadRejected = false;
  try Reflect.callMethod(openfl,Reflect.field(openfl,"unloadLibrary"),["openfl-declared"])
   catch (error:Dynamic) openflUnloadRejected = Std.string(error).indexOf("Dynamic unload is unsupported") >= 0;
  if (!openflUnloadRejected || NativeOpenFlAssets.getLibrary("openfl-declared") != openflGlobal)
   throw "owner unload changed a same-named OpenFL global library";
  var openflRegisterRejected = false;
  try Reflect.callMethod(openfl,Reflect.field(openfl,"registerLibrary"),["openfl-declared",new NativeOpenFlAssetLibrary()])
   catch (error:Dynamic) openflRegisterRejected = Std.string(error).indexOf("Dynamic register is unsupported") >= 0;
  if (!openflRegisterRejected || NativeOpenFlAssets.getLibrary("openfl-declared") != openflGlobal)
   throw "owner register replaced a same-named OpenFL global library";
  var bindingRejected = false;
  try Reflect.callMethod(openfl,Reflect.field(openfl,"unregisterBinding"),["NoSuchBinding",openflGlobal])
   catch (error:Dynamic) bindingRejected = Std.string(error).indexOf("Dynamic OpenFL bindings are unsupported") >= 0;
  if (!bindingRejected) throw "owner facade exposed global OpenFL binding mutation";
  var initBindingRejected = false;
  try Reflect.callMethod(openfl,Reflect.field(openfl,"initBinding"),["NoSuchBinding",{}])
   catch (error:Dynamic) initBindingRejected = Std.string(error).indexOf("Dynamic OpenFL bindings are unsupported") >= 0;
  if (!initBindingRejected) throw "owner facade exposed global OpenFL binding initialization";
 }
}''', encoding="utf-8"
            , newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "-lib", "lime", "-lib", "openfl", "--run", "PsychOwnerLimeAssetsProbe"],
                cwd=work,
                env=haxe_env(),
                text=True,
                capture_output=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
