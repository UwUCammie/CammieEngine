"""V-Slice's IntervalShake: scripts shake an object by name, and it returns to where it started."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

STUBS = {
    'flixel/FlxG.hx': '''package flixel;
class Random { public function new() {} public function float(min:Float, max:Float):Float return max; }
class FlxG { public static var elapsed = 1 / 60; public static var random = new Random(); }''',
    'flixel/FlxObject.hx': '''package flixel;
class FlxObject { public var x = 0.0; public var y = 0.0; public var width = 100.0; public function new(x = 0.0, y = 0.0) { this.x = x; this.y = y; } }''',
    'flixel/math/FlxMath.hx': '''package flixel.math;
class FlxMath { public static function lerp(a:Float, b:Float, ratio:Float):Float return a + ratio * (b - a); }''',
    'flixel/util/FlxTimer.hx': '''package flixel.util;
class FlxTimer {
 public static var all:Array<FlxTimer> = [];
 public var loops = 0; public var loopsLeft = 0; public var finished = false; public var active = true;
 var callback:FlxTimer->Void;
 public function new() {}
 public function start(time:Float, callback:FlxTimer->Void, loops:Int):FlxTimer {
  this.callback = callback; this.loops = loops; loopsLeft = loops; all.push(this); return this;
 }
 public function cancel():Void { active = false; finished = true; }
 public function tick():Void {
  if (!active || finished) return;
  if (loops > 0) loopsLeft--;
  if (loops > 0 && loopsLeft == 0) finished = true;
  callback(this);
 }
}''',
}

MAIN = '''import flixel.FlxObject;
import flixel.util.FlxTimer;
class Main {
 static function main() {
  var stage = new FlxObject(10, 20);
  // Scripts pass four or five arguments and no ease.
  var progressed = 0;
  var shake = IntervalShake.shake(stage, 0.12, 0.04, 0.1, 0.1, null, null, function(_) progressed++);
  if (shake == null || !IntervalShake.isShaking(stage)) throw 'shake did not start';
  if (IntervalShake.shake(stage, 1, 0.04, 0.5, 0.5) != shake) throw 'a second call must return the running shake';
  var timer = FlxTimer.all[0];
  if (timer.loops != 3) throw 'loop count must be duration / interval, got ' + timer.loops;
  timer.tick();
  // The stub random returns the top of the range: the start position plus intensity * width.
  if (stage.x != 20 || stage.y != 30) throw 'shake offset was ' + stage.x + ',' + stage.y;
  timer.tick();
  timer.tick();
  if (stage.x != 10 || stage.y != 20) throw 'the object must return to its start when the shake ends';
  if (IntervalShake.isShaking(stage)) throw 'a finished shake must release its object';
  if (progressed != 0) throw 'V-Slice never runs the progress callback, so it must not run here either';
  var other = new FlxObject(5, 5);
  IntervalShake.shake(other, 0, 0.04, 0.2, 0.2);
  FlxTimer.all[1].tick();
  IntervalShake.stopShaking(other);
  if (other.x != 5 || other.y != 5 || IntervalShake.isShaking(other)) throw 'stopShaking must restore and release';
  if (IntervalShake.shake(null, 1, 0.04, 0, 0) != null) throw 'a null object must be ignored';
  var plugins = sys.io.File.getContent('source/PluginManager.hx');
  if (plugins.indexOf('interp.variables.set("IntervalShake", IntervalShake);') < 0) throw 'scripts cannot reach IntervalShake by name';
 }
}
'''


class IntervalShakeTest(unittest.TestCase):
    def test_shake_moves_then_restores_and_releases(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            root = Path(folder)
            for relative, text in STUBS.items():
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                (root / relative).write_text(text, newline=chr(10))
            (root / 'IntervalShake.hx').write_text((ROOT / 'source/IntervalShake.hx').read_text(encoding='utf-8'), newline=chr(10))
            (root / 'Main.hx').write_text(MAIN, newline=chr(10))
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'Main', '--interp'],
                cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
