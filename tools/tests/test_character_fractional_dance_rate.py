"""Dance rates under a beat, or between whole beats, dance on the right steps."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_psych_charting_handoff import method

ROOT = Path(__file__).resolve().parents[2]


class CharacterFractionalDanceRateTest(unittest.TestCase):
    def test_step_gate_matches_bopper_and_beat_and_step_paths_never_double_up(self):
        character = (ROOT / 'source/Character.hx').read_text(encoding='utf-8')
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        helpers = character[character.index('\tfunction get_danceEveryNumBeats()'):
                            character.index('\t@:keep public var danceIdle:')]
        methods = '\n'.join(method(play, marker) for marker in (
            'function characterDanceDue(',
            'function danceCharactersBetweenBeats(',
            'function danceBetweenBeats(',
            'public function setTargetDanceRate(',
        ))
        fixture = '''using StringTools;
class Animations {
 public var curAnim:Dynamic = {name: 'idle'};
 public function new() {}
}
class Character {
 public var danceEvery:Float = 1;
 public var danceEveryNumBeats(get,set):Int;
 public var codenameLiveDefinition:Dynamic = null;
 public var animation:Animations = new Animations();
 public var singPriority:Array<String> = [];
 public var dances:Array<Int> = [];
 public var clock:Int = 0;
 public function new() {}
 public function dance():Void dances.push(clock);
 public static function animationName(c:Character):String
  return c == null || c.animation == null || c.animation.curAnim == null ? '' : c.animation.curAnim.name;
 @@HELPERS@@
}
class EngineCompat {
 public static function danceIntervalBeats(rate:Float):Int return rate < 1 ? 1 : Std.int(rate);
}
class PlayState {
 public static var globalSprites:Map<String, Dynamic> = new Map();
}
class Main {
 var boyfriend:Character = new Character();
 var dad:Character = new Character();
 var gf:Character = new Character();
 var gfSinging:Bool = false;
 var nightmareVisionScripts:Dynamic = null;
 public function new() {}
 @@METHODS@@
 // What beatHit and stepHit do for one actor, in song order.
 function play(actor:Character, steps:Int):Void {
  for (step in 0...steps) {
   actor.clock = step;
   if (step % 4 == 0 && characterDanceDue(actor, Std.int(step / 4))) actor.dance();
   danceCharactersBetweenBeats(step);
  }
 }
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  // Pinned V-Slice Bopper: dance when step % (danceEvery * 4) == 0.
  for (rate in [0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0]) {
   var host = new Main();
   check(host.setTargetDanceRate('dad', rate), 'dad target');
   host.play(host.dad, 64);
   var expected = [for (step in 0...64) if (step % (rate * 4) == 0) step];
   check(host.dad.dances.join(',') == expected.join(','), 'rate ' + rate + ' danced on ' + host.dad.dances.join(','));
  }
  var host = new Main();
  host.setTargetDanceRate('gf', 0.5);
  check(host.gf.danceEvery == 0.5 && host.gf.danceEveryNumBeats == 1, 'half beat rate was rounded away');
  host.setTargetDanceRate('opponent', 1.5);
  check(host.dad.danceEvery == 1.5 && host.dad.danceEveryNumBeats == 1, 'whole beat view of 1.5');
  host.setTargetDanceRate('bf', 0);
  check(host.boyfriend.danceEveryNumBeats == 0, 'zero stops the dance');
  host.play(host.boyfriend, 16);
  check(host.boyfriend.dances.length == 0, 'zero rate danced');
  host.setTargetDanceRate('bf', Math.NaN);
  check(host.boyfriend.danceEvery == 1, 'unreadable rate keeps once a beat');
  // A singing actor is not interrupted between beats.
  var singer = new Main();
  singer.setTargetDanceRate('dad', 0.5);
  singer.dad.animation.curAnim = {name: 'singLEFT'};
  singer.danceCharactersBetweenBeats(2);
  check(singer.dad.dances.length == 0, 'between-beat dance interrupted a sing');
  // Nightmare Vision keeps its own Bopper callback.
  var nv = new Main();
  nv.nightmareVisionScripts = {};
  nv.setTargetDanceRate('dad', 0.5);
  nv.danceCharactersBetweenBeats(2);
  check(nv.dad.dances.length == 0, 'NV host got the native between-beat dance');
 }
}'''.replace('@@HELPERS@@', helpers).replace('@@METHODS@@', methods)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            Path(folder, 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '--main', 'Main', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_step_hit_runs_the_between_beat_dances(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        step = method(play, 'override function stepHit()')
        self.assertIn('danceCharactersBetweenBeats(curStep);', step)


if __name__ == '__main__':
    unittest.main()
