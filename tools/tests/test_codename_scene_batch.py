"""Run Codename's shared scene batch normalizer with real Haxe."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class CodenameSceneBatchTest(unittest.TestCase):
    def test_arrays_deduplicate_native_objects_and_keep_groups_atomic(self):
        fixture = '''class Basic { public var name:String; public function new(name:String) this.name=name; }
class Group extends Basic { public var members:Array<Basic>; public function new(name:String,members:Array<Basic>) { super(name);this.members=members; } }
class Main {
 static function check(actual:Array<Dynamic>, expected:Array<Dynamic>):Void {
  if(actual.length!=expected.length) throw "length "+actual.length+" != "+expected.length;
  for(i in 0...actual.length) if(actual[i]!=expected[i]) throw "item "+i+" was not retained in order";
 }
 static function main():Void {
  var first=new Basic("first"), second=new Basic("second");
  var group=new Group("group",[first,second]);
  var nested:Array<Dynamic>=[second];
  var invalid:Array<Dynamic>=[];
  var batch=CodenameSceneBatch.collect([first,second,first,group,group,"not a FlxBasic",nested],
   function(value:Dynamic):Basic return Std.isOfType(value,Basic)?cast value:null,
   function(value:Dynamic) invalid.push(value));
  check(batch,[first,second,group]);
  if(invalid.length!=2 || invalid[0]!="not a FlxBasic" || invalid[1]!=nested) throw "invalid values were not reported in order";
  check(group.members,[first,second]);
  check(CodenameSceneBatch.collect(first,function(value:Dynamic):Basic return cast value,
   function(value:Dynamic) throw "valid scalar rejected"),[first]);
  check(CodenameSceneBatch.collect([],function(value:Dynamic):Basic return cast value,
   function(value:Dynamic) throw "empty array rejected"),[]);
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            (Path(work) / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", work, "--run", "Main"], cwd=ROOT, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
