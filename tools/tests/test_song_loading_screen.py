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
 static var phaseFrames=0; static var requestNumber=0; static var pending:Void->Void;
 static var initialFrameRendered=false; static var readyFrameRendered=false;
 static var progress:SongLoadingProgress;
 static var overlay:Dynamic; static var design:Dynamic; static var fill:Dynamic; static var artwork:Dynamic; static var stars:Array<Dynamic>=[];
 static var status:Dynamic; static var count:Dynamic;
 static function build(a:String,b:String):Void {}
 static function authoredOutroStarted():Bool return outro;
 static function renderViewportReady():Bool return viewportReady;
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
  check(model.completed==1&&model.label=="prepared"&&model.fraction()==0.25,"progress regressed or guessed");
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
