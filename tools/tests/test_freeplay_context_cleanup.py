"""Exercise Freeplay owner cleanup independently of Flixel state transitions."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"


class FreeplayContextCleanupTest(unittest.TestCase):
    def test_chart_owner_clears_for_base_menu_but_explicit_entry_is_retained(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        source = (ROOT / "source/FreeplayState.hx").read_text()
        start = source.index("function prepareDirectFreeplayContext():Void {")
        end = source.index("\n\t}", start) + 3
        method = source[start:end]
        fixture = '''
class CodenameModRuntime {
 public static var owner:String='';
 public static var clears:Int=0;
 public static function activeRoot():String return owner;
 public static function clearActiveOwner():Void { owner=''; clears++; }
}
class ImportedFreeplayCaller {
 public static var explicitlyScopedOwner:String='';
 public static function ownerForFreeplay(_activeOwner:String):String
  return explicitlyScopedOwner;
}
class FreeplayState {
 var directOwnerRoot:String='';
 public function new() {}
 public function prepare():Void prepareDirectFreeplayContext();
 public function owner():String return directOwnerRoot;
''' + method + '''
}
class Main {
 static function check(value:Bool,message:String):Void if(!value) throw message;
 static function main():Void {
  var state=new FreeplayState();
  CodenameModRuntime.owner='assets/imported_mods/chart-owner';
  ImportedFreeplayCaller.explicitlyScopedOwner='';
  state.prepare();
  check(state.owner()=='','ordinary Freeplay must have no imported owner filter');
  check(CodenameModRuntime.owner=='' && CodenameModRuntime.clears==1,
   'stale chart owner must be released when base Freeplay is prepared');
  CodenameModRuntime.owner='assets/imported_mods/package-owner';
  ImportedFreeplayCaller.explicitlyScopedOwner=CodenameModRuntime.owner;
  state.prepare();
  check(state.owner()==CodenameModRuntime.owner,
   'explicit package entry must retain its owner filter');
  check(CodenameModRuntime.clears==1,
   'explicit imported Freeplay must not clear its active owner');
  Sys.println('freeplay-context-cleanup-ok');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("freeplay-context-cleanup-ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
