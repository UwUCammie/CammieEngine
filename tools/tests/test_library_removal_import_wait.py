"""Removing a mod while import work runs always leaves a usable screen."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, TEST_TMP
from test_nv_multifield_routes import method

ROOT = Path(__file__).resolve().parents[2]


def run_haxe(work, main):
    (work / 'Main.hx').write_text(main, encoding='utf-8')
    result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '--main', 'Main', '--interp'],
        cwd=work, capture_output=True, text=True, timeout=30)
    return result


class LibraryRemovalImportWaitTest(unittest.TestCase):
    def test_wait_status_follows_actual_coordinator_fields(self):
        source = (ROOT / 'source/ImportRefreshManager.hx').read_text(encoding='utf-8')
        body = method(source, 'public static function removalWaitStatus(')
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            work = Path(folder)
            result = run_haxe(work, '''typedef ImportRefreshWaitStatus={var busy:Bool;var label:String;var fraction:Float;var queued:Int;}
typedef Status={var label:String;var fraction:Float;}
class Main {
 static var mutex=new sys.thread.Mutex();static var removalToken="";static var active=false;static var inspectionPending=false;static var inspectionRunning=false;
 static var queue:Array<Dynamic>=[];static var pendingHandoffs:Array<String>=[];static var handoffTotal=0;static var handoffCompleted=0;
 static var status:Status={label:"Refreshing import: Example",fraction:.4};
 static function hasRunnableHandoffLocked():Bool return pendingHandoffs.length>0;
 ''' + body + '''
 static function ok(v:Bool,m:String):Void {if(!v)throw m;}
 static function main(){
  ok(!removalWaitStatus().busy,"idle importer reported as busy");
  inspectionPending=true;ok(removalWaitStatus().busy,"a pending saved-import check is not waited for");inspectionPending=false;
  inspectionRunning=true;ok(removalWaitStatus().busy,"a running saved-import check is not waited for");inspectionRunning=false;
  active=true;queue=[1,2];var running=removalWaitStatus();
  ok(running.busy&&running.label=="Refreshing import: Example"&&running.fraction==.4&&running.queued==2,"refresh progress is not exposed");
  active=false;queue=[1];ok(removalWaitStatus().busy,"queued refresh is not waited for");queue=[];
  pendingHandoffs=["a"];handoffTotal=10;handoffCompleted=5;var handoff=removalWaitStatus();
  ok(handoff.busy&&handoff.label=="Loading imported songs"&&handoff.fraction==.5,"handoff progress is not exposed");
  pendingHandoffs=[];removalToken="removal-1";active=true;
  ok(!removalWaitStatus().busy,"the removal's own reservation counts as import work");
  Sys.println("wait status passed");
 }
}''')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('wait status passed', result.stdout)

    def test_handoff_may_finish_on_the_removal_screen(self):
        source = (ROOT / 'source/ImportRefreshManager.hx').read_text(encoding='utf-8')
        body = method(source, 'static function canHandoffOnCurrentState(')
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            work = Path(folder)
            (work / 'flixel').mkdir()
            (work / 'flixel/FlxG.hx').write_text('package flixel; class FlxG {public static var state:Dynamic;}', encoding='utf-8')
            result = run_haxe(work, '''import flixel.FlxG;
class LibraryRemovalState {public function new(){}}
class GameplayState {public function new(){}}
class Main {
 ''' + body + '''
 static function main(){
  FlxG.state=new GameplayState();
  if(canHandoffOnCurrentState())throw "gameplay may hand off";
  FlxG.state=new LibraryRemovalState();
  if(!canHandoffOnCurrentState())throw "the refresh can never finish on the removal screen";
  Sys.println("handoff passed");
 }
}''')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('handoff passed', result.stdout)

    def test_removal_state_never_stays_a_bare_backdrop(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            work = Path(folder)
            (work / 'LibraryRemovalState.hx').write_text((ROOT / 'source/LibraryRemovalState.hx').read_text(encoding='utf-8'), encoding='utf-8')
            files = {
                'flixel/FlxG.hx': 'package flixel; class FlxG {public static var width=1280;public static var height=720;public static var switched:Array<Dynamic>=[];public static function switchState(state:Dynamic):Void switched.push(state);}',
                'flixel/FlxSprite.hx': 'package flixel; class FlxSprite {public function new(){} public function makeGraphic(w:Int,h:Int,c:Int):FlxSprite return this;}',
                'flixel/text/FlxText.hx': '''package flixel.text; enum Align {CENTER;}
class FlxText {public var text:String;public function new(x:Float=0,y:Float=0,w:Float=0,text:String='',size:Int=0){this.text=text;}public function setFormat(font:String,size:Int,color:Int,align:Align):Void{}}''',
                'MusicBeatState.hx': '''class MusicBeatState {
 public var subState:Dynamic;public var added:Array<Dynamic>=[];
 public function new(){} public function create():Void{} public function update(elapsed:Float):Void{}
 public function add(item:Dynamic):Void added.push(item);
 public function openSubState(state:Dynamic):Void{subState=state;}
 public function close():Void{var finished=subState;subState=null;if(finished.closeCallback!=null)finished.closeCallback();}
}''',
                'LibraryRemovalSubState.hx': 'class LibraryRemovalSubState {public var closeCallback:Void->Void;public function new(owner:String,?published:Void->Void,?title:String){}}',
                'ImportedMenuEntry.hx': 'class ImportedMenuEntry {public static var released=0;public static function release():Void released++;}',
                'ImportRefreshManager.hx': 'class ImportRefreshManager {public static var ticks=0;public static function browseTick():Void ticks++;}',
                'ImportRemovalManager.hx': 'class ImportRemovalManager {public static var busy=false;public static function poll():{busy:Bool} return {busy:busy};}',
                'FreeplayState.hx': 'class FreeplayState {public function new(){}}',
                'LoadingState.hx': 'class LoadingState {public static var destination:Array<Dynamic>=[];public static function loadAndSwitchState(state:Dynamic):Void destination.push(state);}',
            }
            for name, content in files.items():
                path = work / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding='utf-8')
            result = run_haxe(work, '''import flixel.FlxG;
@:access(LibraryRemovalState)
class Main {
 static function check(ok:Bool,why:String):Void if(!ok)throw why;
 static function texts(state:LibraryRemovalState):Array<String> {var result=[];for(item in state.added){var text=Std.downcast(item,flixel.text.FlxText);if(text!=null)result.push(text.text);}return result;}
 static function main(){
  // Closing the popup says where it is going until Freeplay has been built.
  var state=new LibraryRemovalState('assets/imported_mods/alpha','Alpha');state.create();
  check(state.subState!=null&&ImportedMenuEntry.released==1,'popup missing after create');
  state.update(.016);state.update(.016);
  check(LoadingState.destination.length==0&&texts(state).length==0,'left before the popup closed');
  state.close();
  check(LoadingState.destination.length==1&&Std.isOfType(LoadingState.destination[0],FreeplayState),'closing did not request Freeplay');
  check(texts(state).indexOf('Returning to Freeplay...')>=0,'closed popup leaves a bare backdrop');
  // A slow Freeplay does not cancel itself, and a request that never starts is repeated once.
  state.update(2);check(FlxG.switched.length==0,'switch forced too early');
  state.update(3);check(FlxG.switched.length==1&&Std.isOfType(FlxG.switched[0],FreeplayState),'stalled return never forced');
  state.update(10);check(FlxG.switched.length==1&&LoadingState.destination.length==1,'return requested repeatedly');
  // A popup that never opened (or vanished) cannot strand the player either.
  var bare=new LibraryRemovalState('assets/imported_mods/alpha');bare.create();bare.subState=null;
  bare.update(1);check(LoadingState.destination.length==1,'left too soon without a popup');
  bare.update(1);check(LoadingState.destination.length==2&&texts(bare).indexOf('Returning to Freeplay...')>=0,'bare backdrop without a popup was kept');
  // A running check, recovery or removal is never abandoned by either safety exit.
  ImportRemovalManager.busy=true;
  var running=new LibraryRemovalState('assets/imported_mods/alpha');running.create();running.subState=null;
  running.update(5);running.update(5);check(LoadingState.destination.length==2,'left while a removal was running');
  ImportRemovalManager.busy=false;running.update(.1);check(LoadingState.destination.length==3,'did not leave once the removal had finished');
  var stalled=new LibraryRemovalState('assets/imported_mods/alpha');stalled.create();stalled.close();
  var switchedBefore=FlxG.switched.length;ImportRemovalManager.busy=true;stalled.update(5);
  check(FlxG.switched.length==switchedBefore,'forced a switch while a removal was running');
  ImportRemovalManager.busy=false;stalled.subState=new LibraryRemovalSubState('assets/imported_mods/alpha');stalled.update(.1);
  check(FlxG.switched.length==switchedBefore,'forced a switch over a visible popup');
  check(ImportRefreshManager.ticks>0,'import progress is not polled on the removal screen');
  Sys.println('removal state passed');
 }
}''')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('removal state passed', result.stdout)


if __name__ == '__main__':
    unittest.main()
