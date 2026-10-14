"""The shared source callback router: which engines hear each lifecycle event, in what order, and when it stops."""
import re
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''class Main {
 static var log:Array<String> = [];
 static var nvOwns = true;
 static var psychOwns = true;
 static var nvReturn:Dynamic = null;
 static var psychReturn:Dynamic = null;
 static var lastArgs:Array<Array<Dynamic>> = [];
 static function check(v:Bool, s:String):Void if (!v) throw s;
 static function router():SourceCallbackRouter {
  return new SourceCallbackRouter(function() return nvOwns, function() return psychOwns,
   function(name, args) { log.push('nv:' + name); lastArgs.push(args); return nvReturn; },
   function(name, args, family, ignoreStops) { log.push('psych:' + name + ':' + family + ':' + ignoreStops); lastArgs.push(args); return psychReturn; },
   function(name, args) { log.push('hscript:' + name + ':' + args.join(',')); lastArgs.push(args); });
 }
 static function run(event:SourceLifecycleEvent, ?hscriptArgs:Array<Dynamic>):String {
  log = []; lastArgs = [];
  var outcome = router().dispatch(event, [], hscriptArgs);
  return log.join(' > ') + ' = ' + (outcome.stopped ? 'stop' : outcome.handled ? 'continue' : 'unhandled');
 }
 static function expect(event:SourceLifecycleEvent, want:String, ?hscriptArgs:Array<Dynamic>):Void {
  var got = run(event, hscriptArgs);
  check(got == want, event + ': expected [' + want + '] got [' + got + ']');
 }
 static function main():Void {
  nvReturn = 0; psychReturn = ScriptCallbackResult.CONTINUE;
  // Every row, both engines owning the song.
  expect(GameOver, 'nv:onGameOver = continue');
  expect(RecalculateRating, 'nv:onRecalculateRating = continue');
  expect(Pause, 'nv:onPause = continue');
  expect(EndSong, 'nv:onEndSong = continue');
  expect(UpdateScoreBar, 'nv:onUpdateScore = continue');
  expect(PreUpdateScore, 'psych:preUpdateScore:Scripts:true = continue');
  expect(UpdateScore, 'psych:onUpdateScore:Scripts:false = continue');
  expect(CountdownStarted, 'psych:onCountdownStarted:Scripts:false > nv:onCountdownStarted = continue');
  expect(StartCountdownAgain, 'psych:onStartCountdown:Scripts:false > nv:onStartCountdown = continue');
  expect(CreatePost, 'psych:onCreatePost:Scripts:false > nv:onCreatePost = continue');
  expect(SongStart, 'nv:onSongStart > hscript:songStart:Song A = continue', ['Song A']);
  expect(StepHit, 'nv:onStepHit > hscript:stepHit:12 = continue', [12]);
  check(lastArgs[0] != lastArgs[1], 'each sink gets its own argument array');
  expect(UpdateScore, 'psych:onUpdateScore:Scripts:false = continue');
  log = []; lastArgs = [];
  var shared:Array<Dynamic> = [true];
  router().dispatch(CountdownStarted, shared);
  check(lastArgs.length == 2 && lastArgs[0] == shared && lastArgs[1] != shared && lastArgs[1][0] == true,
   'the first engine gets the caller array, the second an equal copy');
  log = []; lastArgs = [];
  router().dispatch(SongStart, ['n']);
  check(lastArgs.length == 2 && lastArgs[0] != lastArgs[1] && lastArgs[1][0] == 'n',
   'HScript without its own arguments gets a copy of the shared ones');
  log = []; lastArgs = [];
  var own:Array<Dynamic> = [7];
  router().dispatch(StepHit, [], own);
  check(lastArgs[1] == own, 'HScript hears its own arguments unchanged');

  // Exclusive gates fall through to Psych only when Nightmare Vision does not own the song.
  nvOwns = false;
  expect(GameOver, 'psych:onGameOver:Scripts:true = continue');
  expect(RecalculateRating, 'psych:onRecalculateRating:Scripts:true = continue');
  psychOwns = false;
  expect(RecalculateRating, ' = unhandled');
  expect(GameOver, 'psych:onGameOver:Scripts:true = continue');
  // An engine that does not own the song never hears owner-gated events.
  expect(CreatePost, ' = continue');
  expect(Pause, ' = continue');
  expect(SongStart, 'hscript:songStart:x = continue', ['x']);
  expect(CountdownStarted, 'psych:onCountdownStarted:Scripts:false = continue');

  // Stop rules: each engine's own sentinel, never the other's.
  nvOwns = true; psychOwns = true;
  nvReturn = NightmareVisionScriptGroup.STOP_FUNC;
  expect(Pause, 'nv:onPause = stop');
  expect(GameOver, 'nv:onGameOver = stop');
  nvReturn = ScriptCallbackResult.STOP;
  expect(Pause, 'nv:onPause = continue');
  nvReturn = null;
  expect(EndSong, 'nv:onEndSong = continue');
  nvReturn = 0;
  psychReturn = ScriptCallbackResult.STOP;
  expect(PreUpdateScore, 'psych:preUpdateScore:Scripts:true = stop');
  expect(CountdownStarted, 'psych:onCountdownStarted:Scripts:false > nv:onCountdownStarted = stop');
  psychReturn = 1;
  expect(PreUpdateScore, 'psych:preUpdateScore:Scripts:true = continue');
  psychReturn = 'Function_Continue';
  expect(PreUpdateScore, 'psych:preUpdateScore:Scripts:true = continue');
  psychReturn = null;
  expect(PreUpdateScore, 'psych:preUpdateScore:Scripts:true = continue');
  check(SourceCallbackRouter.stops('nv', 1) && SourceCallbackRouter.stops('psych', ScriptCallbackResult.STOP)
   && !SourceCallbackRouter.stops('hscript', 1), 'stops() applies each sink rule');
 }
}
'''


def nv_constants():
    group = (ROOT / 'source/NightmareVisionScriptGroup.hx').read_text(encoding='utf-8')
    names = ['CONTINUE_FUNC', 'STOP_FUNC', 'HALT_FUNC']
    lines = []
    for name in names:
        match = re.search(r'public static inline var ' + name + r':Int = (\d+);', group)
        lines.append('\tpublic static inline var %s:Int = %s;' % (name, match.group(1)))
    return 'package;\nclass NightmareVisionScriptGroup {\n' + '\n'.join(lines) + '\n}\n'


class SourceCallbackRouterTest(unittest.TestCase):
    def test_routing_table_order_and_stop_rules(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            for name in ['SourceCallbackRouter', 'SourceLifecycleEvent', 'SourceCallbackOutcome', 'ScriptCallbackResult']:
                (work / (name + '.hx')).write_text(
                    (ROOT / ('source/' + name + '.hx')).read_text(encoding='utf-8'), encoding='utf-8')
            # The real sentinels, without the script group's interpreter imports.
            (work / 'NightmareVisionScriptGroup.hx').write_text(nv_constants(), encoding='utf-8')
            (work / 'Main.hx').write_text(MAIN, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '--main', 'Main', '--interp'],
                                    cwd=work, capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_playstate_sends_migrated_events_through_the_router(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        for event in ['GameOver', 'RecalculateRating', 'Pause', 'EndSong', 'UpdateScoreBar', 'PreUpdateScore',
                      'UpdateScore', 'CountdownStarted', 'StartCountdownAgain', 'CreatePost', 'SongStart', 'StepHit']:
            self.assertTrue('sourceCallbacks().dispatch(SourceLifecycleEvent.' + event + ',' in play, event)
        # The hand-written sentinel checks for the migrated events are gone.
        for name in ['onGameOver', 'onPause', 'onEndSong', 'onUpdateScore', 'onRecalculateRating',
                     'onCountdownStarted', 'onCreatePost', 'onSongStart', 'onStepHit']:
            self.assertFalse("callNightmareVision('" + name + "'" in play, name)
        for name in ['onGameOver', 'preUpdateScore', 'onUpdateScore', 'onRecalculateRating',
                     'onCountdownStarted', 'onCreatePost']:
            self.assertFalse("PsychRuntimeBindings.dispatch(this, '" + name + "'" in play, name)
        self.assertFalse("callAllHScript('songStart'" in play)
        step_hit = play[play.index('override function stepHit()'):]
        step_hit = step_hit[:step_hit.index('\n\t}\n') if '\n\t}\n' in step_hit else step_hit.index('\n\t}\r\n')]
        self.assertFalse('callAllHScript("stepHit"' in step_hit)

    def test_audit_reads_the_routing_table(self):
        import sys
        sys.path.insert(0, str(ROOT / 'tools'))
        import audit_script_api_coverage as audit
        routes = audit._source_callback_router_routes(ROOT)
        self.assertIn('onGameOver', routes['nv'])
        self.assertIn('onGameOver', routes['psych'])
        self.assertIn('preUpdateScore', routes['psych'])
        self.assertNotIn('preUpdateScore', routes['nv'])
        self.assertIn('stepHit', routes['hscript'])
        self.assertTrue(any(ref.path.endswith('SourceCallbackRouter.hx') for ref in routes['nv']['onPause']))


if __name__ == '__main__':
    unittest.main()
