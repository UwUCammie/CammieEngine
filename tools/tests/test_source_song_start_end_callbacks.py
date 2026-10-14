"""Scripts can replace a song's start and end step under either engine's name."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from tools.haxe_flixel_math_stubs import write_flixel_point_stub

ROOT = Path(__file__).resolve().parents[2]


def method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index('{', start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError('Unclosed source method: ' + marker)


class SourceSongStartEndCallbacksTest(unittest.TestCase):
    def setUp(self):
        self.play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        start = self.play.index('@:keep public var songStartCallback(get, set):Dynamic;')
        last = '@:keep function set_endCallback(value:Dynamic):Dynamic return set_songEndCallback(value);'
        self.accessors = self.play[start:self.play.index(last, start) + len(last)]

    def test_four_names_share_two_slots_and_both_call_sites_use_them(self):
        for name in ('songStartCallback', 'songEndCallback', 'startCallback', 'endCallback'):
            self.assertIn('@:keep public var %s(get, set):Dynamic;' % name, self.accessors)
        self.assertEqual(self.accessors.count('psychStageStartCallback = SongFlow.handoffSlot(value, startCountdown);'), 1)
        self.assertEqual(self.accessors.count('psychStageEndCallback = SongFlow.handoffSlot(value, endSong);'), 1)
        self.assertIn('return get_songStartCallback();', self.accessors)
        self.assertIn('return set_songEndCallback(value);', self.accessors)
        # The BaseStage setters write the same slots the runners take from.
        self.assertIn('psychStageStartCallback = callback;', method(self.play, 'public function setStartCallback('))
        self.assertIn('psychStageEndCallback = callback;', method(self.play, 'public function setEndCallback('))
        self.assertIn('var callback = psychStageStartCallback;', method(self.play, 'function runPsychStageStartCallback('))
        self.assertIn('var callback = psychStageEndCallback;', method(self.play, 'function runPsychStageEndCallback('))
        # Song creation and song end ask the slot whatever kind of script filled it.
        self.assertIn('\t\tif (runPsychStageStartCallback()) {', self.play)
        self.assertIn('if (runPsychStageEndCallback()) return;', method(self.play, 'function endSong('))
        # A compiled stage that failed to build loses its intro before the slot is asked.
        dropped = self.play.index('if (psychCompiledStageSource != null && !psychCompiledStageCreated)\n'
                                  '\t\t\tpsychStageStartCallback = null;')
        asked = self.play.index('\t\tif (runPsychStageStartCallback()) {')
        self.assertLess(dropped, asked)
        self.assertLess(self.play.index('psychCompiledStageCreated = startPsychCompiledStage('), dropped)

    def test_script_assignments_drive_the_start_and_end_handoff(self):
        fixture = r'''
class Host {
 var psychStageStartCallback:Dynamic = null;
 var psychStageEndCallback:Dynamic = null;
 public var psychStageCutsceneEnding:Bool = false;
 public var countdowns:Int = 0;
 public var endRequests:Int = 0;
 public var endings:Int = 0;
 public function new() {}
 public function startCountdown():Void countdowns++;
 function endSong(?force:Bool = false):Void endRequests++;
 function endForReal():Void endings++;
 @@ACCESSORS@@
 @:keep public @@SET_START@@
 public @@RUN_START@@
 public @@RUN_END@@
 public function startPending():Bool return psychStageStartCallback != null;
 public function endPending():Bool return psychStageEndCallback != null;
}
class Main {
 static function check(ok:Bool, why:String):Void if (!ok) throw why;
 static function main():Void {
  var host = new Host();
  var parser = new NightmareVisionScriptParser();
  var interp = new NightmareVisionScriptInterp(host, new Map<String, Dynamic>());
  var hits:Array<String> = [];
  interp.variables.set('record', function(text:String) hits.push(text));
  function run(source:String):Void interp.execute(parser.parseString(source));

  // Untouched: the game's own start runs, and scripts read it back.
  check(!host.runPsychStageStartCallback() && !host.runPsychStageEndCallback(), 'default handoff claimed');
  run('songStartCallback(); startCallback();');
  check(host.countdowns == 2, 'default start callback is not the countdown');
  run('songEndCallback(); endCallback();');
  check(host.endRequests == 2, 'default end callback is not the song end');

  // A bare assignment reaches the game instead of becoming a script variable.
  run('songStartCallback = function() record("intro");');
  check(host.startPending() && !interp.variables.exists('songStartCallback'), 'assignment stayed inside the script');
  check(host.runPsychStageStartCallback() && hits.join(',') == 'intro' && host.countdowns == 2,
   'scripted intro did not replace the countdown');
  check(!host.runPsychStageStartCallback(), 'scripted intro ran twice');

  // Putting the game's own step back, or nothing, clears the slot.
  run('songStartCallback = function() record("unused"); songStartCallback = startCountdown;');
  check(!host.startPending(), 'assigning the countdown kept a scripted start');
  run('startCallback = function() record("unused"); startCallback = null;');
  check(!host.startPending(), 'assigning null kept a scripted start');

  // Both engine names and the stage setter fill the same slot.
  run('startCallback = function() record("psych intro");');
  check(host.runPsychStageStartCallback() && hits.join(',') == 'intro,psych intro', 'Psych name missed the slot');
  host.setStartCallback(function() hits.push('stage intro'));
  run('record(songStartCallback == startCountdown ? "default" : "scripted");');
  check(hits[hits.length - 1] == 'scripted' && host.runPsychStageStartCallback()
   && hits[hits.length - 1] == 'stage intro', 'stage setter and script names disagree');

  hits = [];
  run('songEndCallback = function() record("outro");');
  check(host.endPending() && host.runPsychStageEndCallback() && hits.join(',') == 'outro'
   && host.endings == 0 && host.psychStageCutsceneEnding, 'scripted ending did not hold the song end');
  check(!host.runPsychStageEndCallback(), 'scripted ending ran twice');
  run('endCallback = function() record("psych outro");');
  check(host.runPsychStageEndCallback() && hits.join(',') == 'outro,psych outro', 'Psych end name missed the slot');

  // A broken script step falls back to the game's own.
  run('songStartCallback = function() { throw "broken intro"; };');
  check(host.runPsychStageStartCallback() && host.countdowns == 3, 'broken intro did not start the countdown');
  run('songEndCallback = function() { throw "broken outro"; };');
  check(host.runPsychStageEndCallback() && host.endings == 1 && !host.psychStageCutsceneEnding,
   'broken ending did not finish the song');

  var refused = false;
  try run('songStartCallback = 5;') catch (error:Dynamic) refused = true;
  check(refused && !host.startPending(), 'a non function was accepted as a start step');
 }
}
'''.replace('@@ACCESSORS@@', self.accessors) \
   .replace('@@SET_START@@', method(self.play, 'function setStartCallback(')) \
   .replace('@@RUN_START@@', method(self.play, 'function runPsychStageStartCallback(')) \
   .replace('@@RUN_END@@', method(self.play, 'function runPsychStageEndCallback('))
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            write_flixel_point_stub(work)
            (work / 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            for defines in ([], ['-D', 'hscriptPos']):
                result = subprocess.run([
                    *HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                    '-cp', str(ROOT / '.haxelib/hscript-iris/1,1,3'),
                    '-cp', str(work), *defines, '--run', 'Main'],
                    cwd=ROOT, text=True, capture_output=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
