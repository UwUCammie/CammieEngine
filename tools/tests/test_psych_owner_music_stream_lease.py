"""Receipt-verified owner stream copies stay immutable and path-contained."""

from haxe_test_support import HAXE_COMMAND, TEST_TMP

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


FIXTURE = r'''package;
import haxe.crypto.Sha256;
import haxe.io.Bytes;
import PsychOwnerMusicStreamLease;
import RuntimeOwnerAssetIdentity;
import sys.FileSystem;
import sys.io.File;

@:access(PsychOwnerMusicStreamLease)
class Main {
 static function fail(message:String):Void throw message;
 static function check(value:Bool,message:String):Void if(!value)fail(message);
 static function hash(bytes:Bytes):String return Sha256.make(bytes).toHex().toLowerCase();
 static function main():Void {
  var root='lease-root'; FileSystem.createDirectory(root);
  var source='donor-stream.ogg'; var first=Bytes.ofString('first verified stream bytes');
  File.saveBytes(source,first);
  var key=hash(Bytes.ofString('identity-one'));
  var firstPath=PsychOwnerMusicStreamLease.ensureLeaseFile(root,key,source,first.length,hash(first));
  check(firstPath.indexOf(root+'/')==0,'lease file is inside the private root');
  check(firstPath==root+'/'+key+'.ogg','content-bound key keeps native file path short');
  check(File.getBytes(firstPath).compare(first)==0,'lease file copies the exact verified bytes');
  check(!FileSystem.exists(root+'/'+key+'-'+hash(first)+'.ogg'),
   'filename does not repeat the content digest already bound into the key');
  var identity:RuntimeOwnerAssetIdentity=Type.createEmptyInstance(RuntimeOwnerAssetIdentity);
  Reflect.setField(identity,'owner','assets/imported_mods/fixture');
  Reflect.setField(identity,'engine','psych');
  Reflect.setField(identity,'scope','package');
  Reflect.setField(identity,'bindingSignature','fixture-proof');
  PsychOwnerMusicStreamLease.prepareRecord(identity,key,firstPath);

  var changed=Bytes.ofString('changed source after the first stream opened');
  File.saveBytes(source,changed);
  var reused=PsychOwnerMusicStreamLease.ensureLeaseFile(root,key,source,first.length,hash(first));
  check(reused==firstPath&&File.getBytes(reused).compare(first)==0,
   'a lease already verified for this live identity is reused without following a refreshed source path');

  var nextKey=hash(Bytes.ofString('identity-two'));
  var nextPath=PsychOwnerMusicStreamLease.ensureLeaseFile(root,nextKey,source,changed.length,hash(changed));
  check(nextPath!=firstPath&&File.getBytes(nextPath).compare(changed)==0,
   'a changed proof receives a distinct lease with the new bytes');

  var before=FileSystem.readDirectory(root).length;
  var rejected=false;
  try PsychOwnerMusicStreamLease.ensureLeaseFile(root,hash(Bytes.ofString('bad')),source,
   changed.length,hash(Bytes.ofString('wrong bytes'))) catch(_error:Dynamic) rejected=true;
  check(rejected,'copy rejects bytes that do not match the committed hash');
  check(FileSystem.readDirectory(root).length==before,'failed verification leaves no partial lease');

  var tampered=false;
  File.saveContent(firstPath,'tampered lease');
  try PsychOwnerMusicStreamLease.ensureLeaseFile(root,key,source,first.length,hash(first))
   catch(_error:Dynamic) tampered=true;
  check(tampered,'a corrupt immutable lease is rejected instead of overwritten');
  check(File.getContent(firstPath)=='tampered lease','corrupt lease is not silently replaced');

  var retiredIdentity:RuntimeOwnerAssetIdentity=Type.createEmptyInstance(RuntimeOwnerAssetIdentity);
  Reflect.setField(retiredIdentity,'owner','assets/imported_mods/fixture');
  Reflect.setField(retiredIdentity,'engine','psych');
  Reflect.setField(retiredIdentity,'scope','package');
  Reflect.setField(retiredIdentity,'bindingSignature','retired-proof');
  var retired=PsychOwnerMusicStreamLease.prepareRecord(retiredIdentity,nextKey,nextPath);
  retired.retired=true;
  PsychOwnerMusicStreamLease.sweepQueue=[nextKey];
  PsychOwnerMusicStreamLease.sweepCursor=0;
  PsychOwnerMusicStreamLease.sweepScheduled=true;
  PsychOwnerMusicStreamLease.sweepAgain=false;
  PsychOwnerMusicStreamLease.sweepNeedsRetry=false;
  PsychOwnerMusicStreamLease.sweepOne();
  check(!FileSystem.exists(nextPath)&&!PsychOwnerMusicStreamLease.records.exists(nextKey),
   'a retired lease with no live stream is removed by the cleanup pass');

  var traversal=false;
  try PsychOwnerMusicStreamLease.ensureLeaseFile(root,'../'+key,source,changed.length,hash(changed))
   catch(_error:Dynamic) traversal=true;
  check(traversal,'lease names cannot escape the private directory');
 }
}'''

STUBS = {
    "ImportRefreshManager.hx": '''package;
class ImportRefreshManager {
 public static var generation:Int=1;
 public static function availabilityRevision():Int return 1;
 public static function ownerAssetIndexBinding(owner:String,engine:String,scope:String):Dynamic return null;
}''',
    "CompatScriptManifest.hx": '''package;
class CompatScriptManifest { public static inline var ROOT_PREFIX:String='assets/imported_mods'; }''',
    "FNFAssets.hx": '''package;
class FNFAssets {
 public static function resolveCaseInsensitivePath(path:String):String return path;
 public static function exists(path:String):Bool return false;
}''',
}


class PsychOwnerMusicStreamLeaseTest(unittest.TestCase):
    def test_verified_copy_is_immutable_and_confined(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(FIXTURE, encoding="utf-8", newline="\n")
            for name, content in STUBS.items():
                (work / name).write_text(content, encoding="utf-8", newline="\n")
            env = dict(os.environ)
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
            env["PATH"] = os.pathsep.join(
                [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
            )
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "-lib", "lime", "-lib", "openfl", "-lib", "tjson", "--main", "Main", "--interp"],
                cwd=work,
                env=env,
                text=True,
                capture_output=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
