"""Completed loading stages and rendered-frame, single-request handoff."""
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
ROOT=Path(__file__).resolve().parents[2]

def method(source, name):
    start=source.index(name)
    brace=source.index('{', start)
    depth=1; at=brace+1
    while depth:
        depth += (source[at]=='{')-(source[at]=='}'); at+=1
    return source[start:at].replace('context:RenderContext','context:Dynamic')

class SongLoadingScreenTest(unittest.TestCase):
    def test_real_deferred_callback_and_completed_stage_model(self):
        source=(ROOT/'source/SongLoadingScreen.hx').read_text(encoding='utf-8')
        helper='\n'.join(method(source,n) for n in ['public static function queue(', 'static function describeWork(', 'static function afterDraw(', 'static function afterRender(', 'public static function cancel('])
        fixture=r'''class PlayState { public static var SONG:Dynamic; }
class LoadingProbe {
 static var outro=false; static var installed=true; static var stateRequested=false; static var viewportWaitLogged=false; static var viewportReady=false;
 static var active=false; static var preparing=false;
 static var workFrames=0; static var lastWorkPresentation=0.; static var phaseFrames=0; static var requestNumber=0; static var pending:Void->Void;
 static var initialFrameRendered=false; static var readyFrameRendered=false;
 static var progress:SongLoadingProgress;
 static var overlay:Dynamic; static var design:Dynamic; static var fill:Dynamic; static var artwork:Dynamic; static var stars:Array<Dynamic>=[];
 static var status:Dynamic; static var count:Dynamic;
 static function build(a:String,b:String):Void {}
 static function authoredOutroStarted():Bool return outro;
 static function renderViewportReady():Bool return viewportReady;
 static function workUnit(units:Float=1):Void progress.worked(units);
 static function redraw():Void {}
 static function layout():Void {}
 static function animateStars():Void {}
 static function log(a:String):Void {}
 static function capture(a:String):Void {}
 static function complete(n:Int,label:String):Void progress.finish(n,label);
''' + helper + r'''
 static function check(ok:Bool,message:String):Void if(!ok)throw message;
 static function main():Void {
  var model=new SongLoadingProgress();
  check(model.fraction()==0,"initial progress");
  model.finish(1,"prepared"); model.finish(0,"old"); model.finish(8,"invalid");
  check(model.completed==1&&model.label=="prepared"&&model.fraction()==0,"lifecycle steps guessed synchronous progress");
  model.beginWork("scene", 4, 0.25, 0.98);
  model.worked(); var first=model.fraction();
  model.worked(1,true); var second=model.fraction();
  check(first>0.25&&second>first&&second<0.98,"completed resources did not advance actual work");
  model.worked(-5);check(model.fraction()==second,"negative work changed progress");
  model.worked(3);check(model.fraction()==0.98,"planned work did not complete");
  model.finish(3,"created");check(model.fraction()<1,"creation completed before final frame");
  model.finish(4,"drawn");check(model.fraction()==1,"final frame did not complete");
  check(SongLoadingProgress.chartRows({notes:[{sectionNotes:[[0,0,0],[1,-1,0]]},{sectionNotes:[[2,1,0]]}]})==3,"row plan incorrect");
  var detail=SongLoadingProgress.chartDetail({stage:"windy",player1:"bf",player2:"dad",gf:"gf",needsVoices:true,
   notes:[{sectionNotes:[[0,0,0],[1,-1,0]]},{sectionNotes:[[2,1,0]]}]});
  check(detail.indexOf("2 sections, 3 rows")>=0&&detail.indexOf("Stage: windy")>=0&&detail.indexOf("bf, dad, gf")>=0,"prepared chart facts missing");
  var calls=0; var nested=0;
  check(queue("song","detail",function(){stateRequested=true;calls++;queue("nested","",function(){stateRequested=true;nested++;});}),"first request refused");
  check(!queue("duplicate","",function(){calls+=50;}),"duplicate accepted");
  afterDraw(); check(calls==0&&active&&progress.completed==0,"prepared before rendered frame");
  afterDraw(); check(calls==0,"draw count guessed renderer completion");
  afterRender(null); afterDraw();check(calls==0,"work began while viewport was still clipped");
  viewportReady=true;afterRender(null); afterDraw(); check(calls==1&&nested==0&&active&&progress.completed==1,"nested switch ran before scene render");
  afterDraw();check(nested==0,"scene phase guessed render completion");
  afterRender(null);afterDraw();check(nested==1&&active,"rendered scene phase did not execute once");
  afterDraw(); check(active&&progress.completed==1,"timer completed actual work");
  complete(2,"cleaned");complete(3,"created");
  afterDraw();check(active&&progress.completed==4,"completion frame missing");
  afterDraw();check(active,"completed overlay retired before rendering");
  afterRender(null);afterDraw();check(!active,"overlay did not retire");
  queue("abort","",function(){});afterDraw();afterRender(null);afterDraw();
  check(!active,"aborted preparation left loading overlay");
  queue("failure","",function(){throw "expected";});afterDraw();afterRender(null);
  var caught=false;try afterDraw() catch(e:Dynamic)caught=e=="expected";
  check(caught&&!active&&!preparing&&pending==null,"failure hidden or overlay leaked");
  queue("authored","",function(){calls+=100;});outro=true;afterDraw();
  check(!active&&pending==null&&calls==1,"source outro did not cancel host overlay");outro=false;
  queue("nested-failure","",function(){queue("scene","",function(){throw "nested";});});
  afterRender(null);afterDraw();afterRender(null);
  caught=false;try afterDraw() catch(e:Dynamic)caught=e=="nested";
  check(caught&&!active&&!preparing,"nested scene exception trapped overlay");
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'LoadingProbe.hx').write_text(fixture,encoding='utf-8')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',folder,'-main','LoadingProbe','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_worker_reads_never_repaint_foreground_and_values_are_unchanged(self):
        fixture = r'''class LoadingWorkProbe {
 static function main():Void {
  var sentinel={identity:17};
  if(SongLoadingWork.complete(sentinel)!=sentinel)throw "uninstalled sink changed asset";
  var calls=0;var kinds:Array<String>=[];
  SongLoadingWork.install(function(kind){calls++;kinds.push(kind);});
  if(SongLoadingWork.complete(sentinel)!=sentinel||calls!=1)throw "foreground resource completion lost value";
  var lock=new sys.thread.Lock();
  sys.thread.Thread.create(function(){
   if(SongLoadingWork.complete(sentinel)!=sentinel)throw "worker resource identity changed";
   lock.release();
  });
  if(!lock.wait(3)||calls!=1)throw "worker invoked display sink";
  SongLoadingWork.complete(true,"cleanup");
  if(calls!=2||kinds.join(",")!="resource,cleanup")throw "resource kind or completion lost";
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'LoadingWorkProbe.hx').write_text(fixture,encoding='utf-8')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',folder,'-main','LoadingWorkProbe','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_completed_scene_stops_resource_accounting_and_repaints(self):
        source=(ROOT/'source/SongLoadingScreen.hx').read_text(encoding='utf-8')
        fixture=r'''class WorkGateProbe {
 static var active=true;static var calls=0;static var progress=new SongLoadingProgress();
 static function presentWork():Void calls++;
''' + method(source,'public static function workUnit(') + method(source,'public static function resourceComplete<T>(') + r'''
 static function main():Void {
  var value={identity:7};progress.beginWork("scene",3,0.05,0.98);
  workUnit();if(calls!=1)throw "actual create checkpoint omitted";
  progress.finish(3,"ready");var completed=progress.workCompleted,total=progress.workTotal;
  workUnit();if(resourceComplete(value)!=value)throw "ready resource identity changed";
  if(calls!=1||progress.workCompleted!=completed||progress.workTotal!=total)throw "completed scene repainted or counted regular updates";
  active=false;workUnit();resourceComplete(value);if(calls!=1)throw "inactive scene repainted";
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'WorkGateProbe.hx').write_text(fixture,encoding='utf-8')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',folder,'-main','WorkGateProbe','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_bitmap_pruning_keeps_flixel_eligibility_and_counts_actual_scans(self):
        source=(ROOT/'source/Main.hx').read_text(encoding='utf-8')
        fixture = r'''class Graphic {
 public var persist:Bool;public var useCount:Int;public var destroyed=0;
 public function new(persist:Bool,useCount:Int){this.persist=persist;this.useCount=useCount;}
}
class BitmapCache {
 public var _cache:Map<String,Graphic>=[];
 public var removed:Array<String>=[];
 public function new(){}
 public function get(k:String):Graphic return _cache.get(k);
 public function removeByKey(k:String):Void {var g=_cache.get(k);_cache.remove(k);removed.push(k);g.destroyed++;}
 public function clearCache():Void throw "unexpected atomic prune";
}
class FlxG {public static var bitmap=new BitmapCache();}
class SongLoadingScreen {
 public static var planned=0.;public static var worked=0;
 public static function beginWork(n:String,t:Float,a:Float,b:Float):Void {planned=t;worked=0;}
 public static function workUnit():Void worked++;
}
class BitmapProbe {
''' + method(source,'static function pruneSongBitmapCache(') + r'''
 static function main():Void {
  var dead=new Graphic(false,0),persistent=new Graphic(true,0),used=new Graphic(false,1);
  FlxG.bitmap._cache.set("dead",dead);FlxG.bitmap._cache.set("persistent",persistent);FlxG.bitmap._cache.set("used",used);
  pruneSongBitmapCache();
  if(dead.destroyed!=1||persistent.destroyed!=0||used.destroyed!=0)throw "cache eligibility changed";
  if(FlxG.bitmap.removed.join(",")!="dead"||SongLoadingScreen.planned!=3||SongLoadingScreen.worked!=3)throw "scan progress incorrect";
  FlxG.bitmap._cache=[];pruneSongBitmapCache();
  if(SongLoadingScreen.planned!=1||SongLoadingScreen.worked!=1)throw "empty cache plan did not finish";
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'BitmapProbe.hx').write_text(fixture,encoding='utf-8')
            result=subprocess.run([*HAXE_COMMAND,'-cp',folder,'-main','BitmapProbe','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_existing_cleanup_and_owner_callback_routes_remain(self):
        main=(ROOT/'source/Main.hx').read_text(encoding='utf-8')
        loading=(ROOT/'source/LoadingState.hx').read_text(encoding='utf-8')
        self.assertLess(main.index('FlxG.bitmap.clearCache()'),main.index('SongLoadingScreen.install()'))
        self.assertLess(main.index('corpses.splice(i, 1)'),main.index('SongLoadingScreen.install()'))
        self.assertIn('CodenameMusicBeatTransition.switchStateForCurrentOwner(target)',loading)
        self.assertIn('SongLoadingScreen.cancel(); return;',loading)
        self.assertIn('CodenameRequestedStateCompat.switchToKnownTarget(target',loading)
        self.assertIn('UncaughtErrorEvent.UNCAUGHT_ERROR', (ROOT/'source/SongLoadingScreen.hx').read_text())

    def test_source_handoff_cancels_before_requested_substate_is_visible(self):
        loading=(ROOT/'source/LoadingState.hx').read_text(encoding='utf-8')
        screen=(ROOT/'source/SongLoadingScreen.hx').read_text(encoding='utf-8')
        fixture=r'''class FlxState { public var subState:FlxState; public function new() {} }
class PlayState extends FlxState { public static var SONG:Dynamic; }
class CodenameMusicBeatTransition extends FlxState { public static var handled=true; public static function switchStateForCurrentOwner(t:FlxState):Bool return handled; }
class CodenameRequestedStateCompat { public static function switchToKnownTarget(t:FlxState,f:Void->Void):Void f(); }
class FlxG { public static var state=new FlxState(); public static var switches=0; public static function switchState(t:FlxState):Void switches++; }
class SongLoadingScreen { public static var preparing=false; public static var active=true; public static var cancelled=0; public static function stateRequestStarted():Void {} public static function cancel():Void {active=false;cancelled++;} public static function queue(a:String,b:String,f:Void->Void):Void f(); }
class LoadingProbe {
''' + method(loading,'static function switchState(') + '\n' + method(screen,'static function authoredOutroStarted(') + r'''
 static function main():Void {
  switchState(new PlayState());
  if(SongLoadingScreen.active||SongLoadingScreen.cancelled!=1||FlxG.switches!=0||FlxG.state.subState!=null)throw "source requested/vetoed handoff left overlay";
  CodenameMusicBeatTransition.handled=false;switchState(new PlayState());if(FlxG.switches!=1)throw "native fallback swallowed";
  FlxG.state.subState=new FlxState();FlxG.state.subState.subState=new CodenameMusicBeatTransition();
  if(!authoredOutroStarted())throw "nested source transition missed";
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'LoadingProbe.hx').write_text(fixture,encoding='utf-8')
            result=subprocess.run([*HAXE_COMMAND,'-cp',folder,'-main','LoadingProbe','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__':unittest.main()
