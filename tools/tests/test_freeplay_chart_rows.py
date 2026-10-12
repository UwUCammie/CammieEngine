"""Expanded chart identities sort independently while retaining canonical song indexes."""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND
ROOT = Path(__file__).resolve().parents[2]

class FreeplayChartRowsTest(unittest.TestCase):
    def test_expand_sort_jump_filter_and_refresh(self):
        body = r"""import LibrarySort.LibrarySortRow;
class Main {
 static function check(ok:Bool, message:String) {if (!ok) throw message;}
 static function main() {
  var songs:Array<LibrarySortRow> = [
   {index:0,id:'a',title:'A',owner:'a',modTitle:'A',engine:'Psych',ordinal:0,favorite:false,random:false},
   {index:1,id:'b',title:'B',owner:'b',modTitle:'B',engine:'Psych',ordinal:1,favorite:false,random:false},
   {index:2,id:'empty',title:'Empty',owner:'b',modTitle:'B',engine:'Psych',ordinal:2,favorite:false,random:false}];
  var before=haxe.Json.stringify(songs);
  var rows=FreeplayChartRows.expand(songs,function(i) return i==0?[0,1,1]:i==1?[1]:[],
    function(i,d) return {value:i==0?(d==0?3:19):10,scale:'Difficulty Rating /20'});
  check(rows.length==4,'one row per distinct supported difficulty plus empty fallback');
  check(haxe.Json.stringify(songs)==before,'expansion mutates registry');
  var order=LibrarySort.order([for(r in rows) r.sort],'flat','default','npsHigh',true);
  check(order.join(',')=='1,2,0,3','each row must sort its own difficulty, unknown last');
  var first=FreeplayChartRows.find(rows,order,0,0);var other=FreeplayChartRows.find(rows,order,0,1);
  check(order.indexOf(first)==2 && order.indexOf(other)==0,'difficulty switch did not jump to chart location');
  check(rows[LibrarySort.select(order,other,1)].song==1,'up/down chart navigation skips a song difficulty');
  var filtered=[for(id in order) if(rows[id].song==0) id];
  check(filtered.join(',')=='1,0','filter disrupted chart ordering');
  check(FreeplayChartRows.find(rows,filtered,1,1)==-1,'hidden song retained a presentation selection');
  rows[0].sort.favorite=true;rows[1].sort.favorite=true;
  check(LibrarySort.order([for(r in rows) r.sort],'flat','default','npsLow',true).join(',')=='0,1,2,3','favorites must precede chart metrics');
  var refreshed=FreeplayChartRows.expand(songs,function(i) return i==0?[1,2]:[],function(i,d) return null);
  var refreshedOrder=[for(i in 0...refreshed.length) i];
  check(refreshed[FreeplayChartRows.find(refreshed,refreshedOrder,0,1)].difficulty==1,'named difficulty lost on support refresh');
  check(refreshed[FreeplayChartRows.find(refreshed,refreshedOrder,0,0)].difficulty==1,'removed difficulty lacks same-song fallback');
  check(LibrarySort.order(songs,'flat','default','az').join(',')=='0,1,2','ordinary alphabetical sorting expanded songs');
 }
}"""
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
            (Path(temp)/'Main.hx').write_text(body)
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',temp,'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_actual_same_capsule_difficulty_hook(self):
        from test_freeplay_random_difficulty import extract_method
        source=(ROOT/'source/FreeplayState.hx').read_text()
        method=extract_method(source,'function dispatchChartNavigationDifficulty(').replace('function dispatchChartNavigationDifficulty(', 'public function dispatchChartNavigationDifficulty(', 1)
        selection=extract_method(source,'function changeSelection(')
        self.assertLess(selection.index('var previousSelectionSong'),selection.index('curSelected = chartRows[id].song'))
        self.assertLess(selection.index('changeDiff();'),selection.index('dispatchChartNavigationDifficulty('))
        self.assertLess(selection.index('dispatchChartNavigationDifficulty('),selection.index("dispatch('capsuleSelected'"))
        body=r"""class Spy {
 public var calls=0; public var difficulty=-1;
 public function new() {}
 public function dispatch(name:String,payload:Dynamic):Void {if(name!='difficultySwitch') throw 'wrong hook'; calls++; difficulty=payload.difficulty;}
}
class Harness {
 public var curSelected=0; public var curDifficulty=1; public var hxcRuntime=new Spy();
 public var ready=true;
 public function new() {}
 function hxcCapsuleView(index:Int):Dynamic return ready?{}:null;
 METHOD
}
class Main {static function main() {
 var state=new Harness();state.dispatchChartNavigationDifficulty(true,0,0);
 if(state.hxcRuntime.calls!=1 || state.hxcRuntime.difficulty!=1) throw 'same capsule chart navigation missed or duplicated difficulty event';
 state.dispatchChartNavigationDifficulty(true,0,1);state.dispatchChartNavigationDifficulty(true,1,0);
 if(state.hxcRuntime.calls!=1) throw 'unchanged or other capsule sent duplicate difficulty hook';
 state.hxcRuntime.dispatch('difficultySwitch',{difficulty:2});state.curDifficulty=2;
 state.dispatchChartNavigationDifficulty(false,0,1);
 if(state.hxcRuntime.calls!=2) throw 'ordinary left-right hook duplicated by chart navigation';
 state.ready=false;state.dispatchChartNavigationDifficulty(true,0,1);
 if(state.hxcRuntime.calls!=2) throw 'unready chart exposed a capsule hook';
 state.hxcRuntime=null;state.dispatchChartNavigationDifficulty(true,0,1);
}}
""".replace('METHOD',method)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
            (Path(temp)/'Main.hx').write_text(body)
            (Path(temp)/'EngineCompat.hx').write_text('class EngineCompat {public static function hxcFreeplayPayload(name:String,host:Dynamic,capsule:Dynamic,difficulty:Int,last:Dynamic):Dynamic return {difficulty:difficulty};}')
            result=subprocess.run([*HAXE_COMMAND,'-cp',temp,'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__': unittest.main()
