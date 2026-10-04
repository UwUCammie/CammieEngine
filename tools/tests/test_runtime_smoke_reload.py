"""Execute the two-visit smoke state machine without a native display."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def method(source, name):
    start = source.index("\tpublic static function " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        depth += (source[i] == "{") - (source[i] == "}")
        if depth == 0:
            return source[start:i + 1]
    raise AssertionError(name)


class RuntimeSmokeReloadTest(unittest.TestCase):
    def test_cross_song_selection_after_first_visit(self):
        harness = (ROOT / "source/RuntimeSmokeHarness.hx").read_text()
        state = (ROOT / "source/RuntimeSmokeState.hx").read_text()
        self.assertIn("case '--smoke-next-song'", harness)
        self.assertIn("--smoke-next-song requires --smoke-playstate-visits 2", harness)
        self.assertIn("RuntimeSmokeHarness.markVisitSelection(selection)", state)
        self.assertIn("Song.loadFromJson(selection.chart, selection.songFolder)", state)
        selection = method(harness, "nextVisitSelection")
        fixture = r'''
class Main {
 static var visitsStarted=0;
 static var cfg:Dynamic={songFolder:"first",chart:"first-hard",difficulty:"hard",
  playstateVisits:2,nextSongFolder:"second",nextChart:"second-easy",nextDifficulty:"easy"};
 static function config():Dynamic return cfg;
''' + selection + r'''
 static function main():Void {
  var first=nextVisitSelection();
  if(first.songFolder!="first" || first.chart!="first-hard" || first.difficulty!="hard")
   throw "first selection changed";
  visitsStarted=1;
  var second=nextVisitSelection();
  if(second.songFolder!="second" || second.chart!="second-easy" || second.difficulty!="easy")
   throw "second selection not switched";
  cfg.nextSongFolder="";
  if(nextVisitSelection().songFolder!="first") throw "same-song reload changed";
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            folder = Path(work)
            (folder / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run([
                *HAXE_COMMAND, "-cp", str(folder), "--run", "Main"],
                cwd=ROOT, env={**os.environ, "TMPDIR": work}, capture_output=True,
                text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_visit_sequence_and_single_visit(self):
        harness = (ROOT / "source/RuntimeSmokeHarness.hx").read_text()
        self.assertIn("playstateVisits: 1", harness)
        self.assertIn("case '--smoke-playstate-visits'", harness)
        self.assertIn("--smoke-playstate-visits requires 1 or 2", harness)
        methods = "\n".join(method(harness, name) for name in (
            "markPlayStateStart", "markPlayStateReady", "markPlayStateDestroyed",
            "markCodenameActorSnapshot", "markCodenameActorTeardown", "tick"))
        fixture = r'''
class RuntimeDecodeMetrics {
 public static function reset(_:Bool):Void {}
 public static function snapshot():Dynamic return {};
}
class RuntimeSmokeState {public function new() {}}
class Note {}
class FlxG {
 public static var switches=0;
 public static var state:Dynamic=null;
 public static function switchState(_:Dynamic):Void switches++;
}
class PlayState {public static var instance:Dynamic=null;}
class RuntimeSmokeVisuals {
 public static function character(_:String,_:Dynamic):Dynamic return {};
 public static function stage(_:Dynamic):Dynamic return {memberCount:0,members:[]};
}
class Main {
 static var cfg:Dynamic={playstateVisits:2,durationMs:1000,frameStats:false,tracePlayerHits:false,
  requireEndHandoff:false,requireSongEnd:false,gameOverAfterMs:-1,
  freeplay:false,freeplayAcceptSong:""};
 static var started=true; static var finished=false;
 static var naturalSongEndObserved=false; static var naturalSongEndAt:Float=0;
 static var playStateStarted=false; static var playStateReady=false;
 static var acceptInitiated=false;
 static var visitsStarted=0; static var visitsReady=0; static var visitsDestroyed=0;
 static var teardownsMarked=0;
 static var validatedTeardown:Dynamic=null;
 static var transitionPending=false;
 static var playStateLoadStartedAt:Float=0;
 static var introRenderHeldAt:Float=-1;
 static var deadline:Float=0; static var playDeadline:Float=0; static var visitDeadline:Float=0;
 static var watchdogDeadline:Float=0; static var elapsedMs:Float=0;
 static var ratingPopupPairs:Map<String,Bool> = new Map();
 static var ratingPopupPairCount:Int = 0;
 static var visualNoteKinds:Map<String,Bool>=new Map();
 static var nightmareVisionVisualKinds:Map<String,Bool>=new Map();
 static var nightmareVisionSplashSeen:Map<Int,Bool>=new Map();
 static var liveVisualNoteKinds:Map<String,Bool>=new Map();
 static var psychSkinDiagnosticPhase:String="";
 static var pendingPlayerHitProbes:Array<Dynamic>=[];
 static var events:Array<String>=[]; static var success=false;
 static function config():Dynamic return cfg;
 static function enabled():Bool return true;
 static function emit(name:String,extra:Dynamic):Void events.push(name+":"+Reflect.field(extra,"visit"));
 static function fail(kind:String,detail:String):Void throw kind+":"+detail;
 static function succeed():Void {success=true;finished=true;}
 static function flushPlayerHitProbes():Void {}
 static function applyWindowResize():Void {}
 static function applySongRate():Void {}
 static function installFrameStats():Void {}
 static function installNoteRenderReadback():Void {}
 static function installGameOverClock():Void {}
 static function installSongEndCompletionWatch():Void {}
 static function markEndHandoff():Void {}
 static function missingRequiredSongEnd(required:Bool, observed:Bool):Bool return required && !observed;
 static function markReceptorLayout(_:String):Void {}
 // The reload sequence fixture has no seek request; smoke seek is tested separately.
 static function maybeRunSeek():Void {}
 static function observePlayerOneGoodHit(_:Dynamic,_:Note):Void {}
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
''' + methods + r'''
 static function main():Void {
  watchdogDeadline=Sys.time()+100;
  markPlayStateStart({song:"example"});
  markPlayStateReady({song:"example"});
  check(visitsStarted==1 && visitsReady==1,"first start/ready");
  visitDeadline=Sys.time()-1;
  check(tick(0.016) && FlxG.switches==1 && transitionPending,
   "first deadline queues one reload and stops old update");
  check(tick(0.016) && FlxG.switches==1,"pending reload cannot queue twice");
  watchdogDeadline=Sys.time()-1;
  var pendingTimeout=false;
  try tick(0.016) catch(e:Dynamic) pendingTimeout=Std.string(e).indexOf("reload-timeout")>=0;
  check(pendingTimeout,"queued transition remains under watchdog");
  watchdogDeadline=Sys.time()+100;
  var early=false;
  try markPlayStateStart({song:"example"}) catch(e:Dynamic) early=Std.string(e).indexOf("reload-sequence")>=0;
  check(early,"second start before teardown rejected");
  var bypass=false;
  try markPlayStateDestroyed({owned:2,borrowed:1,destroyCalls:2,
   remainingBindings:0,cleanupErrors:[]})
  catch(e:Dynamic) bypass=Std.string(e).indexOf("reload-sequence")>=0;
  check(bypass,"destroy marker cannot bypass cleanup evidence");
  markCodenameActorTeardown({owned:2,borrowed:1,destroyCalls:2,remainingBindings:0,cleanupErrors:[]});
  var inconsistent=false;
  try markPlayStateDestroyed({owned:2,borrowed:0,destroyCalls:2,
   remainingBindings:0,cleanupErrors:[]})
  catch(e:Dynamic) inconsistent=Std.string(e).indexOf("reload-sequence")>=0;
  check(inconsistent,"destroy summary must match validated teardown");
  markPlayStateDestroyed({owned:2,borrowed:1,destroyCalls:2,remainingBindings:0,cleanupErrors:[]});
  naturalSongEndObserved=true;
  markPlayStateStart({song:"example"});
  check(!naturalSongEndObserved,"first song end leaked into the second visit");
  markPlayStateReady({song:"example"});
  check(visitsStarted==2 && visitsReady==2 && visitsDestroyed==1 && !transitionPending,
   "second visit begins only after destroy");
  visitDeadline=Sys.time()-1;
  cfg.requireSongEnd=true;
  var unfinished=false;
  try tick(0.016) catch(e:Dynamic) unfinished=Std.string(e).indexOf("song-end-timeout")>=0;
  check(unfinished,"first ending cannot satisfy second visit's completion requirement");
  cfg.requireSongEnd=false;
  check(!tick(0.016) && success && FlxG.switches==1,"second deadline succeeds");
  check(events.indexOf("playstate_destroyed:1")>=0,"destroy marker recorded");
  finished=false;
  markCodenameActorSnapshot({owned:2,borrowed:1,actors:[]});
  var missingFailed=false;
  try markCodenameActorTeardown(null)
  catch(e:Dynamic) missingFailed=Std.string(e).indexOf("actor-cleanup")>=0;
  check(missingFailed,"missing cleanup evidence fails smoke");
  markCodenameActorTeardown({owned:2,borrowed:1,destroyCalls:2,remainingBindings:0,cleanupErrors:[]});
  check(events.indexOf("codename_actor_snapshot:2")>=0
   && events.indexOf("codename_actor_teardown:2")>=0,"actor evidence includes visit");
  var cleanupFailed=false;
  teardownsMarked=1;
  try markCodenameActorTeardown({owned:2,destroyCalls:1,remainingBindings:0,cleanupErrors:[]})
  catch(e:Dynamic) cleanupFailed=Std.string(e).indexOf("actor-cleanup")>=0;
  check(cleanupFailed,"incomplete owned cleanup fails smoke");
  // Gameplay time begins at readiness; a slow load does not consume it.
  cfg.playstateVisits=1; finished=false; success=false; started=true;
  cfg.durationMs=1000; transitionPending=false; deadline=Sys.time()-1;
  watchdogDeadline=Sys.time()+100; playStateReady=false; playStateStarted=true;
  check(!tick(0.016) && !success,"startup duration does not end gameplay before ready");
  markPlayStateReady({song:"example"});
  check(playDeadline>Sys.time(),"ready starts a full gameplay window");
  check(!tick(0.016) && !success,"single visit remains active for the ready-relative window");
  playDeadline=Sys.time()-1;
  check(!tick(0.016) && success,"single visit ends when its ready-relative window expires");

  finished=false; success=false; playStateReady=false; playDeadline=0;
  watchdogDeadline=Sys.time()-1;
  var startupTimeout=false;
  try tick(0.016) catch(e:Dynamic) startupTimeout=Std.string(e).indexOf("timeout")>=0;
  check(startupTimeout,"unready PlayState still fails under the separate startup watchdog");
 }
}
'''
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            folder = Path(work)
            (folder / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run([
                *HAXE_COMMAND, "-cp", str(folder), "--run", "Main"],
                cwd=ROOT, env={**os.environ, "TMPDIR": work}, capture_output=True,
                text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_visit_count_parser_rejects_prefixes_and_fractional_values(self):
        harness = (ROOT / "source/RuntimeSmokeHarness.hx").read_text()
        parser = harness[harness.index("\tstatic function parsePlaystateVisits("):]
        parser = parser[:parser.index("\n\t}") + 3]
        fixture = "class Main {\n" + parser + r'''
 static function main():Void {
  if (parsePlaystateVisits("1")!=1 || parsePlaystateVisits(" 2 ")!=2
   || parsePlaystateVisits("2junk")!=0 || parsePlaystateVisits("1.5")!=0
   || parsePlaystateVisits(null)!=0 || parsePlaystateVisits("")!=0)
   throw "invalid visit count parser";
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            folder = Path(work)
            (folder / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run([
                *HAXE_COMMAND, "-cp", str(folder), "--run", "Main"],
                cwd=ROOT, env={**os.environ, "TMPDIR": work}, capture_output=True,
                text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
