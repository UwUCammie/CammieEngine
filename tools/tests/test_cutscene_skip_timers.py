"""Skipping an intro cutscene moves script timers on by the part nobody watched.

Scripts often hold the countdown until a timer that matches their video runs
out. Without the timer catching up, a skip leaves whatever the intro had set up
(a faded camera, a hidden HUD) on screen until the clip's full length passes.
"""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND, TEST_TMP
ROOT = Path(__file__).resolve().parents[2]


class CutsceneSkipTimersTest(unittest.TestCase):
    def run_haxe(self, body):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            (Path(temp) / 'Main.hx').write_text('class Main {\n static function check(ok:Bool, m:String) { if (!ok) throw m; }\n static function main() {\n' + body + '\n }\n}', encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', temp, '--run', 'Main'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unwatched_part_of_a_clip(self):
        self.run_haxe(r"""
  check(CutsceneSkip.unwatchedMs(82000, 5000) == 77000, 'remaining clip time');
  check(CutsceneSkip.unwatchedMs(82000, 90000) == 0, 'a playhead past the end gave negative time');
  check(CutsceneSkip.unwatchedMs(0, 1000) == 0 && CutsceneSkip.unwatchedMs(-5, 0) == 0, 'unknown length moved timers');
  check(CutsceneSkip.unwatchedMs(82000, Math.NaN) == 0 && CutsceneSkip.unwatchedMs(82000, -1) == 0, 'unknown playhead moved timers');
  check(CutsceneSkip.unwatchedMs(Math.POSITIVE_INFINITY, 0) == 0, 'endless clip moved timers');
  // A skip leaves the last five seconds of an intro clip to play.
  check(CutsceneSkip.leadSeekMs(82000, 5000) == 77000 && CutsceneSkip.leadAdvanceMs(82000, 5000) == 72000, 'intro skip did not keep its last five seconds');
  check(Math.isNaN(CutsceneSkip.leadSeekMs(82000, 77000)) && Math.isNaN(CutsceneSkip.leadSeekMs(82000, 80000)), 'a skip inside the last five seconds moved the clip');
  check(CutsceneSkip.leadAdvanceMs(82000, 78000) == 0, 'a skip inside the last five seconds moved timers');
  check(Math.isNaN(CutsceneSkip.leadSeekMs(4000, 0)) && Math.isNaN(CutsceneSkip.leadSeekMs(0, 0)) && Math.isNaN(CutsceneSkip.leadSeekMs(Math.NaN, 0)), 'short or unknown clip skipped');
  check(CutsceneSkip.leadSeekMs(82000, Math.NaN) == 77000 && CutsceneSkip.leadAdvanceMs(82000, Math.NaN) == 0, 'unreadable playhead blocked the skip or moved timers');""")

    def test_timer_catches_up_and_still_fires_through_its_manager(self):
        # The same counter rule as FlxTimer.update: a tick happens once the
        # counter reaches the timer's time.
        self.run_haxe(r"""
  var time = 82.0; var counter = 5.0;
  var advance = CutsceneSkip.timerAdvance(time - counter, 77.0);
  counter += advance;
  check(counter < time, 'the skip fired the timer outside its manager, so its callback would never run');
  check(time - counter <= CutsceneSkip.TIMER_EDGE + 1e-9, 'timer was left far from its end');
  counter += 1 / 60;
  check(counter >= time, 'timer did not fire on the next frame');
  // A timer longer than the skipped part only moves on by that part.
  check(Math.abs(CutsceneSkip.timerAdvance(100, 30) - 30) < 1e-9, 'longer timer moved by the wrong amount');
  check(CutsceneSkip.timerAdvance(10, 0) == 0 && CutsceneSkip.timerAdvance(10, -3) == 0 && CutsceneSkip.timerAdvance(10, Math.NaN) == 0, 'nothing skipped but timer moved');
  check(CutsceneSkip.timerAdvance(0, 5) == 0 && CutsceneSkip.timerAdvance(Math.NaN, 5) == 0, 'finished or broken timer moved');""")

    def test_every_intro_route_moves_script_timers(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8').replace('\r\n', '\n')
        # Song-owned clips report their playhead, and the pre-song skip uses it.
        self.assertIn('?startMs:Null<Float>, ?position:Void->Float):Void {', play)
        # The pre-song skip moves each clip to its last seconds instead of ending it.
        self.assertIn('var seekMs = CutsceneSkip.leadSeekMs(length, position);\n\t\t\t\tif (!Math.isFinite(seekMs)) continue;\n\t\t\t\tmoved = Math.max(moved, CutsceneSkip.leadAdvanceMs(length, position));\n\t\t\t\tentry.seek(seekMs);', play)
        self.assertIn('if (!used) return false;\n\t\t\tadvanceScriptTimersPastCutscene(moved / 1000);', play)
        # Native intro clips move timers at the moment of the skip, not when they end.
        self.assertEqual(play.count('.onSkipAhead = function(ms:Float) advanceScriptTimersPastCutscene(ms / 1000);'), 3)
        self.assertNotIn('advanceScriptTimersPastCutscene(clip.unwatchedMs', play)
        self.assertNotIn('advanceScriptTimersPastCutscene(video.unwatchedMs', play)
        # Only script timers move, each at most once, through the shared rule.
        self.assertIn('for (timer in compatTimers)\n\t\t\tif (timer != null && timer.active && !timer.finished)\n\t\t\t\ttimer.update(CutsceneSkip.timerAdvance(timer.timeLeft, seconds));', play)
        video = (ROOT / 'source/VideoCutscene.hx').read_text(encoding='utf-8')
        self.assertIn('var seekMs = CutsceneSkip.leadSeekMs(durationMs, playedMs);', video)
        self.assertIn('video.time = Std.int(seekMs);', video)
        owner = (ROOT / 'source/NightmareVisionVideoSprite.hx').read_text(encoding='utf-8')
        self.assertIn('function() skip(), null,\n\t\t\t\tfunction() return disposed || bitmap == null ? Math.NaN : haxe.Int64.toInt(bitmap.time) + 0.0]);', owner.replace('\r\n', '\n'))

    def test_pre_song_skip_keeps_the_last_seconds_and_moves_timers_once(self):
        # Runs the real PlayState skip and timer methods against a small host.
        from test_psych_camera_alias import extract_method
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8').replace('\r\n', '\n')
        field = play[play.index('\tvar songCutscenes:Array<'):]
        field = field[:field.index('\n')]
        methods = '\n'.join(extract_method(play, marker) for marker in (
            '@:keep public function registerSongCutscene(',
            'function advanceScriptTimersPastCutscene(',
            'function skipSongCutscenes('))
        host = '''import flixel.FlxG;
class Host {
 public function new() {}
 public var startingSong = true; public var paused = false; public var endingSong = false;
 public var playbackRate:Float = 1; public var songLength:Float = 300000;
 public var compatTimers:Array<Timer> = [];
 function nextPlayerNoteTime():Float return Math.NaN;
 function seekForwardSongTime(ms:Float, b:Bool):Void throw 'pre-song skip seeked the song';
''' + field + '\n' + methods + '\n}'
        main = r'''@:access(Host) class Main {
 static function check(ok:Bool, m:String) if (!ok) throw m;
 static function main() {
  var host = new Host();
  var playhead:Float = 4000; var seeks:Array<Float> = []; var finished = 0;
  var key = {};
  host.registerSongCutscene(key, function() return 82000.0, function() return true,
   function(ms:Float) seeks.push(ms), function() finished++, null, function() return playhead);
  var waiting = new Timer(82); waiting.counter = 4; host.compatTimers.push(waiting);
  check(host.skipSongCutscenes(true), 'intro skip was not used');
  check(seeks.length == 1 && seeks[0] == 77000 && finished == 0, 'intro clip was ended instead of moved to its last five seconds');
  check(Math.abs(waiting.counter - (4 + 73)) < 1e-6, 'script timer did not move by the unwatched part minus five seconds');
  // The decoder has not applied the seek yet: a second press must not move anything.
  check(!host.skipSongCutscenes(true) && seeks.length == 1 && Math.abs(waiting.counter - 77) < 1e-6, 'a quick second press moved the clip or timers again');
  // A clip with five seconds or less left is not skipped at all.
  var late = {}; var lateSeeks = 0;
  host.registerSongCutscene(late, function() return 20000.0, function() return true,
   function(ms:Float) lateSeeks++, function() finished++, null, function() return 16000.0);
  check(!host.skipSongCutscenes(true) && lateSeeks == 0 && finished == 0, 'a press inside the last five seconds did something');
  check(!host.skipSongCutscenes(false), 'a skip ran without a press');
 }
}'''
        files = {
            'Host.hx': host, 'Main.hx': main,
            'CutsceneSkip.hx': (ROOT / 'source/CutsceneSkip.hx').read_text(encoding='utf-8'),
            'Timer.hx': 'class Timer {public var time:Float; public var counter:Float = 0; public var active = true;\n public var finished(get, never):Bool; function get_finished() return counter >= time;\n public var timeLeft(get, never):Float; function get_timeLeft() return time - counter;\n public function new(t:Float) time = t;\n public function update(e:Float) counter += e;}',
            'Conductor.hx': 'class Conductor {public static var songPosition:Float = 0;}',
            'flixel/FlxG.hx': 'package flixel; class FlxG {public static var sound:{music:Dynamic} = {music: null};}',
        }
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            for name, text in files.items():
                (Path(temp) / name).parent.mkdir(parents=True, exist_ok=True)
                (Path(temp) / name).write_text(text, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', temp, '--run', 'Main'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_smoke_harness_can_press_skip_during_an_intro(self):
        harness = (ROOT / 'source/RuntimeSmokeHarness.hx').read_text(encoding='utf-8').replace('\r\n', '\n')
        self.assertIn("case '--smoke-intro-skip-after-ms':", harness)
        self.assertIn('introSkipAfterMs: -1,', harness)
        # One tick of a forced press, then released, like a real key.
        self.assertIn('if (introSkipPressing) {\n\t\t\tintroSkipPressing = false;\n\t\t\tCutsceneSkipKey.forced = false;\n\t\t}', harness)
        self.assertIn('|| !playStateReady || songStartObserved || PlayState.instance == null', harness)


if __name__ == '__main__':
    unittest.main()
