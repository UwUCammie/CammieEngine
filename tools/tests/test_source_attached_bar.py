"""The Psych FlxBar follows its state-owned background through property writes."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]


class SourceAttachedBarTest(unittest.TestCase):
    def test_unbound_and_attached_bar_properties_rebind_and_lifecycle(self):
        main = r'''import flixel.FlxSprite;
import flixel.ui.FlxBar.FlxBarFillDirection;

class AttachedBarHarness {
 static function check(ok:Bool, message:String):Void {
  if (!ok) throw 'assertion failed: ' + message;
 }
 static function near(actual:Float, expected:Float, message:String):Void {
  check(Math.abs(actual - expected) < 0.00001, message + ': ' + actual + ' != ' + expected);
 }
 static function main():Void {
  var tracked:Dynamic = {health: 73};
  var unbound = new SourceAttachedBar(10, 20, FlxBarFillDirection.LEFT_TO_RIGHT, 120, 8, tracked, 'health', 5, 90, true);
  check(unbound.width == 120 && unbound.height == 8, 'standard FlxBar constructor arguments are retained');
  check(unbound.constructorDirection == FlxBarFillDirection.LEFT_TO_RIGHT, 'direction argument is forwarded');
  check(unbound.constructorParent == tracked && unbound.constructorVariable == 'health', 'tracked-value arguments are forwarded');
  check(unbound.constructorMin == 5 && unbound.constructorMax == 90 && unbound.constructorBorder, 'range and border arguments are forwarded');
  Reflect.setProperty(unbound, 'x', 15.0);
  Reflect.setProperty(unbound, 'y', 24.0);
  Reflect.setProperty(unbound, 'alpha', 0.4);
  near(unbound.x, 15, 'unbound x follows ordinary FlxBar behavior');
  near(unbound.y, 24, 'unbound y follows ordinary FlxBar behavior');
  near(unbound.alpha, 0.4, 'unbound alpha follows ordinary FlxBar behavior');
  check(unbound.backgroundFollower == null, 'unbound follower is null');

  var bar = new SourceAttachedBar(10, 20);
  var first = new FlxSprite(14, 27);
  first.alpha = 0.8;
  check(bar.attachBackground(first) == bar, 'attach returns the same bar');
  near(first.x, 14, 'initial bind preserves authored x offset');
  near(first.y, 27, 'initial bind preserves authored y offset');
  check(bar.backgroundFollower == first, 'follower identity is exposed');

  Reflect.setProperty(bar, 'x', 15.0);
  Reflect.setProperty(bar, 'y', 18.0);
  near(first.x, 19, 'reflected x tween moves background by delta');
  near(first.y, 25, 'reflected y tween moves background by delta');

  // A direct background edit changes its offset; a later bar tween preserves it.
  Reflect.setProperty(first, 'x', 50.0);
  Reflect.setProperty(first, 'y', 80.0);
  Reflect.setProperty(bar, 'x', 17.0);
  Reflect.setProperty(bar, 'y', 16.0);
  near(first.x, 52, 'direct background x edit remains offset during bar movement');
  near(first.y, 78, 'direct background y edit remains offset during bar movement');

  Reflect.setProperty(bar, 'alpha', 0.5);
  near(first.alpha, 0.4, 'bar alpha multiplies authored background alpha');
  Reflect.setProperty(first, 'alpha', 0.6);
  Reflect.setProperty(bar, 'alpha', 0.25);
  near(first.alpha, 0.3, 'direct background alpha factor is retained on next bar write');
  Reflect.setProperty(bar, 'alpha', 2.0);
  near(bar.alpha, 1.0, 'base FlxBar clamps alpha');
  near(first.alpha, 1.0, 'background receives effective clamped alpha');

  var second = new FlxSprite(300, 400);
  second.alpha = 0.75;
  check(bar.attachBackground(first) == bar, 'same follower rebind remains idempotent');
  Reflect.setProperty(first, 'x', 60.0);
  bar.attachBackground(second);
  check(bar.backgroundFollower == second, 'replacement follower identity is exposed');
  Reflect.setProperty(bar, 'x', 20.0);
  near(second.x, 303, 'new follower moves by bar delta');
  near(first.x, 60, 'replaced follower stops moving');
  Reflect.setProperty(bar, 'alpha', 0.5);
  near(second.alpha, 0.375, 'replacement captures its own local alpha');

  bar.destroy();
  check(bar.backgroundFollower == null, 'destroy releases follower reference');
  check(bar.destroyed, 'base FlxBar destroy still runs');
  check(!second.destroyed, 'destroy does not own the separate background');
  Reflect.setProperty(bar, 'x', 25.0);
  near(second.x, 303, 'destroyed bar no longer moves the background');
 }
}'''

        stubs = {
            'flixel/FlxSprite.hx': r'''package flixel;
class FlxSprite {
 public var x(default, set):Float = 0;
 public var y(default, set):Float = 0;
 public var alpha(default, set):Float = 1;
 public var width:Float = 0;
 public var height:Float = 0;
 public var destroyed:Bool = false;
 public function new(x:Float = 0, y:Float = 0) {
  this.x = x; this.y = y;
 }
 function set_x(value:Float):Float { x = value; return x; }
 function set_y(value:Float):Float { y = value; return y; }
 function set_alpha(value:Float):Float {
  alpha = value < 0 ? 0 : (value > 1 ? 1 : value);
  return alpha;
 }
 public function destroy():Void destroyed = true;
}''',
            'flixel/ui/FlxBar.hx': r'''package flixel.ui;
import flixel.FlxSprite;
enum FlxBarFillDirection { LEFT_TO_RIGHT; RIGHT_TO_LEFT; }
class FlxBar extends FlxSprite {
 public var constructorDirection:FlxBarFillDirection;
 public var constructorParent:Dynamic;
 public var constructorVariable:String;
 public var constructorMin:Float;
 public var constructorMax:Float;
 public var constructorBorder:Bool;
 public function new(x:Float = 0, y:Float = 0, ?direction:FlxBarFillDirection,
   width:Int = 100, height:Int = 10, ?parentRef:Dynamic, variable:String = '',
   min:Float = 0, max:Float = 100, showBorder:Bool = false) {
  super(x, y);
  constructorDirection = direction == null ? LEFT_TO_RIGHT : direction;
  this.width = width; this.height = height;
  constructorParent = parentRef; constructorVariable = variable;
  constructorMin = min; constructorMax = max; constructorBorder = showBorder;
 }
 override public function destroy():Void super.destroy();
}''',
        }
        with tempfile.TemporaryDirectory(prefix='source-attached-bar-') as folder:
            temp = Path(folder)
            for relative, content in stubs.items():
                file = temp / relative
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(content, encoding='utf-8')
            (temp / 'AttachedBarHarness.hx').write_text(main, encoding='utf-8')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(temp), '-cp', str(ROOT / 'source'),
                 '-main', 'AttachedBarHarness', '--interp'],
                cwd=ROOT, text=True, capture_output=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
