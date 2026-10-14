"""A pausing custom substate freezes only the tasks running at the pause.

Psych's script substates and the native pause share the base pause helpers in
PlayState; this pins the snapshot freeze in SourcePauseTasks and that the
custom-substate paths no longer carry their own copies of the pause and resume.
"""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND
from test_psych_camera_alias import extract_method
ROOT = Path(__file__).resolve().parents[2]

STUBS = {
    'Task.hx': 'class Task {public var active=true; public var finished=false; public function new(?active:Bool=true, ?finished:Bool=false) {this.active=active; this.finished=finished;}}',
    'Manager.hx': 'class Manager<T> {public var tasks:Array<T>=[]; public function new() {}\n public function forEach(f:T->Void) for(t in tasks)f(t);}',
    'flixel/util/FlxTimer.hx': 'package flixel.util; class FlxTimer extends Task {public static var globalManager=new Manager<FlxTimer>(); public function new(?a:Bool=true, ?f:Bool=false) super(a, f);}',
    'flixel/tweens/FlxTween.hx': 'package flixel.tweens; class FlxTween extends Task {public static var globalManager=new Manager<FlxTween>(); public function new(?a:Bool=true, ?f:Bool=false) super(a, f);}',
}


class SourcePauseTasksSnapshotTest(unittest.TestCase):
    def test_snapshot_restores_only_what_it_stopped(self):
        main = r'''import flixel.util.FlxTimer; import flixel.tweens.FlxTween;
class Main {
 static function check(ok:Bool, m:String) if (!ok) throw m;
 static function main() {
  var running = new FlxTimer(), idle = new FlxTimer(false), done = new FlxTimer(true, true);
  var tween = new FlxTween(), idleTween = new FlxTween(false);
  FlxTimer.globalManager.tasks = [running, idle, done];
  FlxTween.globalManager.tasks = [tween, idleTween];
  var timers:Array<FlxTimer> = [], tweens:Array<FlxTween> = [];
  SourcePauseTasks.freezeRunning(timers, tweens);
  check(!running.active && !tween.active && timers.length == 1 && tweens.length == 1, 'running tasks were not frozen');
  check(!idle.active && !idleTween.active && done.active, 'stopped or finished tasks were touched');
  // The substate starts its own timer while frozen; a second freeze adds it once.
  var menu = new FlxTimer(); FlxTimer.globalManager.tasks.push(menu);
  var later = new FlxTimer(); FlxTimer.globalManager.tasks.push(later);
  later.active = false;
  SourcePauseTasks.freezeRunning(timers, tweens);
  check(timers.length == 2 && !menu.active, 'second freeze listed a task twice or missed a new one');
  running.finished = true;
  SourcePauseTasks.thaw(timers, tweens);
  check(!running.active, 'a task that finished while paused was restarted');
  check(tween.active && menu.active && !idle.active && !idleTween.active && !later.active, 'thaw restored the wrong tasks');
  check(timers.length == 0 && tweens.length == 0, 'thaw kept its lists');
  var created = new FlxTimer(); FlxTimer.globalManager.tasks.push(created);
  SourcePauseTasks.thaw(timers, tweens);
  check(created.active, 'an empty thaw changed a task');
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            for name, text in {**STUBS, 'Main.hx': main}.items():
                (Path(folder) / name).parent.mkdir(parents=True, exist_ok=True)
                (Path(folder) / name).write_text(text, newline='\n')
            (Path(folder) / 'SourcePauseTasks.hx').write_text((ROOT / 'source/SourcePauseTasks.hx').read_text(encoding='utf-8'), newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '--run', 'Main'], cwd=ROOT,
                                    capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_custom_substates_use_the_base_pause(self):
        source = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8').replace('\r\n', '\n')
        opened = extract_method(source, 'function compatOpenCustomSubstate(')
        closed = extract_method(source, 'function compatCloseCustomSubstate(')
        for body in (opened, closed):
            self.assertNotIn('FlxG.sound.music.pause()', body)
            self.assertNotIn("setAllHaxeVar('paused'", body)
            self.assertNotIn('resyncVocals()', body)
        self.assertIn('if (pauseGame) pauseGameplayForSubstate();', opened)
        self.assertIn('resumeGameplayFromSubstate(previous != null && previous.pausesGame);', opened)
        self.assertIn('resumeGameplayFromSubstate(true);', closed)
        # The native substate open pauses the audio through the same helper.
        opening = source[source.index('override function openSubState('):source.index('override function closeSubState(')]
        self.assertIn('pauseGameplayAudio();', opening)
        self.assertNotIn('FlxG.sound.music.pause();', opening)
        timeline = extract_method(source, 'function pausePsychCustomTimeline(') + extract_method(source, 'function resumePsychCustomTimeline(')
        self.assertIn('SourcePauseTasks.freezeRunning(compatCustomPausedTimers, compatCustomPausedTweens);', timeline)
        self.assertIn('SourcePauseTasks.thaw(compatCustomPausedTimers, compatCustomPausedTweens);', timeline)
        self.assertNotIn('globalManager.forEach', timeline)


if __name__ == '__main__':
    unittest.main()
