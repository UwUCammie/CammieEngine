from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]

def extract_method(source, name):
    start=source.index('function %s(' % name)
    depth=0;body=None
    for i in range(source.index('{',start),len(source)):
        if source[i]=='{':depth+=1
        elif source[i]=='}':
            depth-=1
            if depth==0:
                body=source[start:i+1];break
    assert body is not None
    return body
class HealthIconStripClampTest(unittest.TestCase):
    def run_interp(self,main_body):
        s=(ROOT/'source/HealthIcon.hx').read_text()
        clamp=extract_method(s,'clampIconFrames')
        fixture='''class Strip {public var numFrames(default,null):Int;public function new(n:Int)numFrames=n;}
class Test {
 public var frames:Strip;
 public function new(cells:Int)frames=new Strip(cells);
''' + clamp + '''
 static function eq(a:Array<Int>,b:Array<Int>){
  if(a.length!=b.length)throw 'length mismatch: '+a+' vs '+b;
  for(i in 0...a.length)if(a[i]!=b[i])throw 'cell '+i+' mismatch: '+a+' vs '+b;
 }
 static function main(){''' + main_body + '''
 }
}'''
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'Test.hx').write_text(fixture, newline='\n')
            p=subprocess.run([*HAXE_COMMAND,'-cp',d,'-main','Test','--interp'],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
    def test_short_strips_map_every_state_onto_a_loaded_cell(self):
        # decision table: the registry "icons" array asks for the native
        # normal/losing/poisoned/winning cells of a 150x150 strip; imported
        # V-Slice strips can carry fewer cells and every mapped state must
        # land on a cell that exists in the loaded strip.
        self.run_interp('''
  // full-size native 4-cell strip (and bigger grids) keep the authored mapping
  eq(new Test(4).clampIconFrames([0,1,2,3]),[0,1,2,3]);
  eq(new Test(5).clampIconFrames([0,1,2,3]),[0,1,2,3]);
  // 2-cell V-Slice strip (neutral + losing): poisoned falls to losing,
  // winning falls back to neutral
  eq(new Test(2).clampIconFrames([0,1,2,3]),[0,1,1,0]);
  // 1-cell strip: every state shows the neutral icon
  eq(new Test(1).clampIconFrames([0,1,2,3]),[0,0,0,0]);
  // an honest 3-entry registry on a 3-cell strip stays untouched
  eq(new Test(3).clampIconFrames([0,1,2]),[0,1,2]);
  // arrays already in range are never rewritten
  eq(new Test(2).clampIconFrames([0,0,0,0]),[0,0,0,0]);
  // stale registry index far past the strip clamps instead of wrapping
  eq(new Test(2).clampIconFrames([0,1,24]),[0,1,1]);''')
    def test_registry_json_array_is_never_mutated(self):
        # the registry json is cached statically and shared across icon
        # reloads, so clamping must work on a copy
        self.run_interp('''
  var registry=[0,1,2,3];
  new Test(1).clampIconFrames(registry);
  eq(registry,[0,1,2,3]);
  new Test(2).clampIconFrames(registry);
  eq(registry,[0,1,2,3]);''')
if __name__=='__main__':
    unittest.main()
