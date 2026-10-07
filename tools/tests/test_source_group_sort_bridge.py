"""Source sort calls accept HUD adapters as well as native groups."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath

ROOT = Path(__file__).resolve().parents[2]


class SourceGroupSortBridgeTest(unittest.TestCase):
    def test_refresh_z_calls_the_selected_group_sort_without_native_cast(self):
        text = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        start = text.index('@:keep public function refreshZ(')
        end = text.index('\n\t/** Source sorting', start)
        method = text[start:end].replace('@:keep ', '')
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='source-sort-', dir=TEST_TMP) as directory:
            work = FixturePath(directory)
            (work / 'flixel/util').mkdir(parents=True)
            (work / 'flixel/util/FlxSort.hx').write_text('''package flixel.util;
class FlxSort {public static inline var ASCENDING:Int=-1;
 public static function byValues(order:Int,a:Int,b:Int):Int return a<b?order:a>b?-order:0;}
''', encoding='utf-8')
            (work / 'HxcCompatRuntime.hx').write_text('''class HxcCompatRuntime {
 public static function getZIndex(value:Dynamic):Int return value.zIndex;}
''', encoding='utf-8')
            (work / 'Bridge.hx').write_text(
                'class Bridge {public var stage:Dynamic; public function new(stage:Dynamic){this.stage=stage;} '
                + method + '}', encoding='utf-8')
            (work / 'Main.hx').write_text('''class NativeGroup {
 public var members:Array<Dynamic>; public var calls:Int=0;
 public function new(members:Array<Dynamic>) {this.members=members;}
 public function sort(compare:Int->Dynamic->Dynamic->Int,order:Int):Void {
  calls++;members.sort(function(a,b) return compare(order,a,b));}
}
class HudAdapter {
 public var logical:Array<Dynamic>; public var display:Array<Dynamic>; public var calls:Int=0;
 public function new(logical:Array<Dynamic>,display:Array<Dynamic>) {this.logical=logical;this.display=display;}
 public function sort(compare:Int->Dynamic->Dynamic->Int,order:Int):Void {
  calls++;var slots:Array<Int>=[];
  for(i in 0...display.length) if(logical.indexOf(display[i])>=0) slots.push(i);
  logical.sort(function(a,b) return compare(order,a,b));
  for(i in 0...slots.length) display[slots[i]]=logical[i];
 }
}
class Main {
 static function check(value:Bool,message:String):Void if(!value) throw message;
 static function main():Void {
  var stage=new NativeGroup([{zIndex:3},{zIndex:1}]);var bridge=new Bridge(stage);
  bridge.refreshZ();check(stage.calls==1 && stage.members[0].zIndex==1,'default native stage sort');
  var shadow:Dynamic={zIndex:995};var text:Dynamic={zIndex:997};var hand:Dynamic={zIndex:1};
  var unrelated:Dynamic={zIndex:10000};var display=[text,unrelated,shadow,hand];
  var hud=new HudAdapter([text,shadow,hand],display);
  bridge.refreshZ(hud);
  check(hud.calls==1 && stage.calls==1,'HUD uses its own live sort');
  check(display[0]==hand && display[1]==unrelated && display[2]==shadow && display[3]==text,
   'clock hand and black shadow behind foreground text without moving unrelated slots');
 }
}''', encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '--run', 'Main'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
