"""Retries leave nothing behind and every retry is timed: sound list, HUD texts, probe."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path

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


def block(source: str, start_marker: str, end_marker: str) -> str:
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


def run_fixture(files: dict) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
        for name, text in files.items():
            path = Path(folder, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf-8', newline='\n')
        return subprocess.run([*HAXE_COMMAND, '-cp', folder, '--main', 'Main', '--interp'], cwd=ROOT,
                              capture_output=True, text=True, timeout=60)


# Same bookkeeping as the pinned Flixel FlxTypedGroup: length is its own
# counter, moved only by add and remove.
GROUP_STUB = '''class Sound {
 public var exists:Bool = true;
 public function new() {}
}
class SoundGroup {
 public var members(default, null):Array<Sound> = [];
 public var length(default, null):Int = 0;
 public function new() {}
 public function add(sound:Sound):Sound {
  if (members.indexOf(sound) >= 0) return sound;
  var index = members.indexOf(null);
  if (index != -1) { members[index] = sound; if (index >= length) length = index + 1; return sound; }
  members.push(sound); length++;
  return sound;
 }
 public function remove(sound:Sound):Sound {
  var index = members.indexOf(sound);
  if (index >= 0) members[index] = null;
  return sound;
 }
}
class FlxG {
 public static var sound = {list: new SoundGroup()};
}
'''


class SongRetryLeftoversTest(unittest.TestCase):
    def test_sound_list_prune_keeps_the_group_length(self):
        main = (ROOT / 'source/Main.hx').read_text(encoding='utf-8')
        prune = block(main, 'var corpses = FlxG.sound.list.members;', '\t\t});')
        fixture = '''import FlxG;
class Main {
 static function prune():Void {
  ''' + prune + '''
 }
 static function main():Void {
  var list = FlxG.sound.list;
  var music = list.add(new Sound());
  // Each retry: a pause track removed without splicing, a game over sound
  // that finished and stopped existing.
  for (attempt in 0...5) {
   var pause = list.add(new Sound());
   var death = list.add(new Sound());
   list.remove(pause);
   death.exists = false;
   prune();
   if (list.members.length != 1 || list.members[0] != music) throw 'dead sounds stay listed';
   if (list.length != list.members.length) throw 'length ' + list.length + ' after attempt ' + attempt;
  }
 }
}'''
        result = run_fixture({'Main.hx': fixture, 'FlxG.hx': GROUP_STUB})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hud_texts_never_added_are_released_on_destroy(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        release = method(play, 'function releaseDetachedHudTexts():Void')
        fixture = '''class FlxText {
 public static var destroyed = 0;
 public var graphic:Dynamic = {};
 public function new() {}
 public function destroy():Void { destroyed++; graphic = null; }
}
@:allow(Main)
class State {
 public var healthTxt:FlxText = new FlxText();
 public var accuracyTxt:FlxText = new FlxText();
 public var botplayTxt:FlxText = new FlxText();
 public var currentTimingShown:FlxText = null;
 public function new() {}
 ''' + release + '''
}
class Main {
 static function main():Void {
  var state = new State();
  // A text that was on screen was already destroyed with the members.
  state.accuracyTxt.destroy();
  FlxText.destroyed = 0;
  state.releaseDetachedHudTexts();
  if (FlxText.destroyed != 2) throw 'released ' + FlxText.destroyed;
  if (state.healthTxt.graphic != null || state.botplayTxt.graphic != null) throw 'graphic kept';
  state.releaseDetachedHudTexts();
  if (FlxText.destroyed != 2) throw 'released twice';
 }
}'''
        result = run_fixture({'Main.hx': fixture})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        destroy = method(play, 'override public function destroy()')
        # After the members are gone, so an added text is never destroyed twice.
        self.assertLess(destroy.index('super.destroy();'), destroy.index('releaseDetachedHudTexts();'))

    def test_retry_probe_times_script_restarts(self):
        probe = (ROOT / 'source/RuntimeRetryProbe.hx').read_text(encoding='utf-8')
        restarted = method(probe, 'static function restartedByScript(')
        fixture = '''class PlayState {
 public function new() {}
}
class Main {
 static var first:PlayState;
 static var triggerAt:Float = -1;
 static var pressAt:Float = -1;
 static var pressedBy:String = 'probe';
 static var phase:Int = 1;
 static var ready:Bool = true;
 static function playable(state:PlayState):Bool return state != null && ready;
 ''' + restarted + '''
 static function main():Void {
  first = new PlayState();
  triggerAt = 10;
  if (restartedByScript(first, 12)) throw 'the dying attempt is no retry';
  var next = new PlayState();
  ready = false;
  if (restartedByScript(next, 12)) throw 'not playable yet';
  ready = true;
  if (!restartedByScript(next, 13)) throw 'script restart missed';
  if (pressAt != 10 || pressedBy != 'script' || phase != 3) throw 'timed from ' + pressAt + ' by ' + pressedBy;
 }
}'''
        result = run_fixture({'Main.hx': fixture})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        tick = method(probe, 'static function tick():Void')
        gameover = block(tick, 'case 1:', 'case 2:')
        pause = block(tick, 'case 2:', 'case 3:')
        # Both waits notice a restart they did not cause, and the game over
        # wait also confirms a script's own game over substate.
        self.assertIn('if (restartedByScript(state, now)) return;', gameover)
        self.assertIn('if (restartedByScript(state, now)) return;', pause)
        self.assertIn('if (GameOverSubstate.instance == null && (state == null || state.subState == null)) return;',
                      gameover)
        self.assertIn('triggerAt = now;', block(tick, 'case 0:', 'case 1:'))


if __name__ == '__main__':
    unittest.main()
