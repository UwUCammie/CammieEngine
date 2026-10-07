"""Pin the shared owner-save backend's opt-in write batching contract."""
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND, TEST_TMP

ROOT = Path(__file__).resolve().parents[2]


class CodenameOwnerSaveStorageTest(unittest.TestCase):
    def test_autoflush_default_batching_cloning_and_validation(self):
        main = r'''package;
import flixel.FlxG;

class OwnerSaveFixtureMain {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function call(storage:Dynamic,name:String,args:Array<Dynamic>):Dynamic {
  var method=Reflect.field(storage,name);
  return Reflect.callMethod(storage,method,args);
 }
 static function main():Void {
  FlxG.save={data:{personalSetting:'preserve'},flushCount:0,
   flush:function():Void FlxG.save.flushCount++};
  var defaultStorage=CodenameOwnerSaveStorage.create();
  var original:Dynamic={nested:{value:1}};
  call(defaultStorage,'write',['assets/imported_mods/family/a','settings',original]);
  Reflect.setField(Reflect.field(original,'nested'),'value',9);
  var saved=Reflect.field(Reflect.field(Reflect.field(FlxG.save.data,
   'codenameImportedModData'),'assets/imported_mods/family/a'),'settings');
  check(Reflect.field(Reflect.field(saved,'nested'),'value')==1,
   'write must persist a JSON clone rather than a caller-owned mutable value');
  check(FlxG.save.flushCount==1,
   'create() must preserve the historical immediate flush after each write');
  var read=call(defaultStorage,'read',['assets/imported_mods/family/a','settings']);
  check(Reflect.field(Reflect.field(read,'nested'),'value')==1,
   'the selected owner and field should read back the cloned JSON value');

  var batched=CodenameOwnerSaveStorage.create(false);
  call(batched,'write',['assets/imported_mods/family/a','settings',{nested:{value:2}}]);
  call(batched,'write',['assets/imported_mods/family/b','settings',{nested:{value:3}}]);
  check(FlxG.save.flushCount==1,
   'autoFlushWrites=false must update the native save data without flushing');
  var a=call(batched,'read',['assets/imported_mods/family/a','settings']);
  var b=call(batched,'read',['assets/imported_mods/family/b','settings']);
  check(Reflect.field(Reflect.field(a,'nested'),'value')==2
   && Reflect.field(Reflect.field(b,'nested'),'value')==3,
   'batched values must remain isolated under their owner keys');
  call(batched,'flush',[]);
  check(FlxG.save.flushCount==2,
   'the explicit flush delegate must persist batched writes');

  FlxG.save.data.codenameImportedModData='malformed-root';
  var rejected=false;
  try call(batched,'write',['assets/imported_mods/family/c','settings',{value:4}])
  catch (_:Dynamic) rejected=true;
  check(rejected && FlxG.save.data.codenameImportedModData=='malformed-root',
   'malformed owner namespace data must be rejected without being overwritten');
 }
}
'''
        flxg = r'''package flixel;
class FlxG { public static var save:Dynamic; }
'''
        with tempfile.TemporaryDirectory(prefix="codename-owner-save-storage-", dir=TEST_TMP) as directory:
            work = Path(directory)
            (work / "OwnerSaveFixtureMain.hx").write_text(main, encoding="utf-8", newline="\n")
            target = work / "flixel/FlxG.hx"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(flxg, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "-cp", str(ROOT / "source"),
                 "--main", "OwnerSaveFixtureMain", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
