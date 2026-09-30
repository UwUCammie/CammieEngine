from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class FreeplayNavigationTest(unittest.TestCase):
    def test_five_visible_songs_and_wraparound(self):
        source = (ROOT / 'source/FreeplayState.hx').read_text()
        method = source[source.index('\tpublic static function nextVisibleSelection('):source.index('\n\tfunction changeSelection(')]
        fixture = 'class NavigationTest {\n' + method + '''
 static function main(){
  var all=function(i:Int)return true;
  if(nextVisibleSelection(8,5,10,all)!=3||nextVisibleSelection(1,-5,10,all)!=6)throw 'Five-song wrap';
  var even=function(i:Int)return i%2==0;
  if(nextVisibleSelection(0,5,20,even)!=10||nextVisibleSelection(0,-5,20,even)!=10)throw 'Must count visible listings';
  if(nextVisibleSelection(1,0,20,even)!=2||nextVisibleSelection(4,0,20,even)!=4)throw 'Search selection';
  if(nextVisibleSelection(0,5,1,all)!=0)throw 'Single song';
  nextVisibleSelection(0,5,10,function(i:Int)return false);
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'NavigationTest.hx').write_text(fixture)
            result = subprocess.run([str(ROOT / '.tools/haxe/haxe'), '-cp', folder, '-main', 'NavigationTest', '--interp'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
