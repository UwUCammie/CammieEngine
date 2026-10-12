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
        helper='\n'.join(method(source,n) for n in ['public static function queue(', 'static function afterDraw(', 'static function afterRender(', 'public static function cancel('])
        fixture=r'''class LoadingProbe {
 static var installed=true; static var stateRequested=false; static var viewportWaitLogged=false; static var viewportReady=false;
 static var active=false; static var preparing=false;
 static var requestNumber=0; static var pending:Void->Void;
 static var initialFrameRendered=false; static var readyFrameRendered=false;
 static var progress:SongLoadingProgress;
 static var overlay:Dynamic; static var design:Dynamic; static var fill:Dynamic; static var artwork:Dynamic; static var stars:Array<Dynamic>=[];
 static var status:Dynamic; static var count:Dynamic;
 static function build(a:String,b:String):Void {}
 static function authoredOutroStarted():Bool return false;
 static function renderViewportReady():Bool return viewportReady;
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
  var calls=0; var nested=0;
  check(queue("song","detail",function(){stateRequested=true;calls++;queue("nested","",function(){nested++;});}),"first request refused");
  check(!queue("duplicate","",function(){calls+=50;}),"duplicate accepted");
  afterDraw(); check(calls==0&&active&&progress.completed==0,"prepared before rendered frame");
  afterDraw(); check(calls==0,"draw count guessed renderer completion");
  afterRender(null); afterDraw();check(calls==0,"work began while viewport was still clipped");
  viewportReady=true;afterRender(null); afterDraw(); check(calls==1&&nested==1&&active&&progress.completed==1,"callback duplication");
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
        self.assertIn('CodenameRequestedStateCompat.switchToKnownTarget(target',loading)
        self.assertIn('UncaughtErrorEvent.UNCAUGHT_ERROR', (ROOT/'source/SongLoadingScreen.hx').read_text())

if __name__=='__main__':unittest.main()
