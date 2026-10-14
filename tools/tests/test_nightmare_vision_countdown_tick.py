"""Nightmare Vision scripts hear every countdown tick, after its sprite exists."""
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


class NightmareVisionCountdownTickTest(unittest.TestCase):
    def setUp(self):
        self.play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')

    def test_tick_is_dispatched_once_per_step_after_the_step_is_shown(self):
        shown = method(self.play, 'function callCountdownTickShown(tick:Int):Void')
        self.assertIn("callNightmareVision('onCountdownTick', [tick]);", shown)
        self.assertEqual(self.play.count("'onCountdownTick'"), 1)
        countdown = method(self.play, 'public function startCountdown():Void')
        self.assertEqual(countdown.count('callCountdownTickShown(swagCounter);'), 1)
        # Before the step: the families that may still change it. After: the
        # scripts that restyle what it put on screen. The counter moves last.
        before = countdown.index('callCountdownTick(swagCounter, tmr);')
        go_sprite = countdown.index("countdownPopup(2, 'assets/images/' + introAlts[2]);")
        after = countdown.index('callCountdownTickShown(swagCounter);')
        self.assertLess(before, go_sprite)
        self.assertLess(go_sprite, after)
        self.assertLess(after, countdown.index('swagCounter += 1;'))
        popup = method(self.play, 'public function countdownPopup(')
        for stage, field in ((0, 'countdownReady'), (1, 'countdownSet'), (2, 'countdownGo')):
            self.assertIn('case %d: %s = count;' % (stage, field), popup)

    def test_script_receives_ticks_zero_to_four_and_can_reach_the_shown_sprite(self):
        fixture = r'''
class Scripts {
 public var group:NightmareVisionScriptGroup;
 public function new(group:NightmareVisionScriptGroup) this.group = group;
 public function call(event:String, ?args:Array<Dynamic>):Dynamic return group.call(event, args);
}
class Host {
 public var nightmareVisionScripts:Scripts = null;
 public var countdownReady:Dynamic = null;
 public var countdownSet:Dynamic = null;
 public var countdownGo:Dynamic = null;
 public function new() {}
 public function show(tick:Int):Void {
  switch (tick) {
   case 1: countdownReady = {visible: true};
   case 2: countdownSet = {visible: true};
   case 3: countdownGo = {visible: true};
   default:
  }
 }
 @@CALL@@
 public @@SHOWN@@
}
class Main {
 static function check(ok:Bool, why:String):Void if (!ok) throw why;
 static function main():Void {
  var host = new Host();
  // No Nightmare Vision scripts loaded: the tick is simply not sent.
  host.callCountdownTickShown(0);

  var ticks:Array<Int> = [];
  var group = new NightmareVisionScriptGroup(host, function(name, phase, error) {
   throw name + ':' + phase + ':' + Std.string(error);
  });
  check(group.loadSource('stage', '
   function onCountdownTick(tick) {
    record(tick);
    if (tick == 3) countdownGo.visible = false;
   }
  ', function(interp:NightmareVisionScriptInterp) {
   interp.variables.set('record', function(tick:Int) ticks.push(tick));
  }) != null, 'stage script');
  host.nightmareVisionScripts = new Scripts(group);
  for (tick in 0...5) {
   host.show(tick);
   host.callCountdownTickShown(tick);
  }
  check(ticks.join(',') == '0,1,2,3,4', 'ticks were ' + ticks.join(','));
  check(host.countdownGo.visible == false, 'the go sprite did not exist when its tick arrived');
  check(host.countdownReady.visible == true && host.countdownSet.visible == true, 'other sprites changed');
  group.destroy();
 }
}
'''.replace('@@CALL@@', method(self.play, 'function callNightmareVision(')) \
   .replace('@@SHOWN@@', method(self.play, 'function callCountdownTickShown(tick:Int):Void'))
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
