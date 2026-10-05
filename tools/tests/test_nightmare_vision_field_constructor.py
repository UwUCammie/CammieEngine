"""Execute the pure parser against Nightmare Vision PlayField.new semantics."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionFieldConstructorTest(unittest.TestCase):
    def test_constructor_defaults_overrides_and_layout_admission(self):
        main = r'''class Main {
 static function check(ok:Bool, label:String):Void {
  if (!ok) throw 'assertion failed: ' + label;
 }
 static function rejects(args:Array<Dynamic>, maxKeys:Int, fragment:String):Void {
  var message = '';
  try NightmareVisionFieldConstructor.parse(args, maxKeys)
  catch (error:Dynamic) message = Std.string(error);
  check(message.indexOf('[nightmare-vision-field-constructor] ') == 0, 'diagnostic prefix: ' + message);
  check(message.indexOf(fragment) >= 0, 'diagnostic should mention ' + fragment + ': ' + message);
 }
 static function main():Void {
  var defaults = NightmareVisionFieldConstructor.parse([12, 34], 8);
  check(defaults.x == 12 && defaults.y == 34, 'required coordinates retain integer values');
  check(defaults.keyCount == 4 && defaults.owner == null, 'key count and owner defaults');
  check(!defaults.isPlayer && !defaults.cpu && !defaults.playerControls, 'boolean defaults');
  check(defaults.player == 0 && defaults.skin == 'default' && defaults.skinInput == null, 'skin and player defaults');

  var nulls = NightmareVisionFieldConstructor.parse([1.5, -2.25, null, null, null, null, null, null, null, null], 8);
  check(nulls.x == 1.5 && nulls.y == -2.25 && nulls.keyCount == 4, 'null optional arguments use donor defaults');
  check(!nulls.isPlayer && !nulls.cpu && !nulls.playerControls && nulls.player == 0, 'null flags and player use defaults');
  check(nulls.skin == 'default' && nulls.skinInput == null, 'null skin args use defaults');

  var owner:Dynamic = {name: 'bf'};
  var skinInput:Dynamic = {sentinel: 42};
  var supplied = NightmareVisionFieldConstructor.parse([12.25, 45.5, 3.0, owner, true, true, false, 2.0, 'custom', skinInput], 4);
  check(supplied.x == 12.25 && supplied.y == 45.5 && supplied.keyCount == 3, 'coordinates and integral float key count');
  check(supplied.owner == owner && supplied.skinInput == skinInput, 'dynamic object arguments retain identity');
  check(supplied.isPlayer && supplied.cpu && !supplied.playerControls, 'constructor flags stay independent');
  check(supplied.player == 2 && supplied.skin == 'custom', 'player and skin overrides');

  var controlsDefault = NightmareVisionFieldConstructor.parse([0, 0, 0, null, true], 4);
  check(controlsDefault.isPlayer && controlsDefault.playerControls, 'playerControls defaults to isPlayer');
  var maximum = NightmareVisionFieldConstructor.parse([0, 0, 4], 4);
  check(maximum.keyCount == 4, 'host layout maximum is admitted');
  var zero = NightmareVisionFieldConstructor.parse([0, 0, 0], 4);
  check(zero.keyCount == 0, 'zero-key field is admitted');

  rejects([], 4, 'x is required');
  rejects([1], 4, 'y is required');
  rejects([null, 1], 4, 'x must be a finite number');
  rejects([1, '2'], 4, 'y must be a finite number');
  rejects([true, 2], 4, 'x must be a finite number');
  rejects([Math.NaN, 2], 4, 'x must be a finite number');
  rejects([Math.POSITIVE_INFINITY, 2], 4, 'x must be a finite number');
  rejects([0, 0, -1], 4, 'keyCount must be nonnegative');
  rejects([0, 0, 2.5], 4, 'keyCount must be an integer');
  rejects([0, 0, 5], 4, 'exceeds host layout limit 4');
  rejects([0, 0, Math.NaN], 4, 'keyCount must be a finite number');
  rejects([0, 0, 4, null, 1], 4, 'isPlayer must be a boolean or null');
  rejects([0, 0, 4, null, false, false, false, 1.5], 4, 'player must be an integer');
  rejects([0, 0, 4, null, false, false, false, 0, 12], 4, 'skin must be a string or null');
  rejects([0, 0, 4], -1, 'host key limit must be nonnegative');
 }
}'''
        with tempfile.TemporaryDirectory(prefix='nv-field-constructor-') as temp_dir:
            temp = Path(temp_dir)
            (temp / 'Main.hx').write_text(main, encoding='utf-8')
            command = [
                *HAXE_COMMAND,
                '-cp', str(ROOT / 'source'),
                '-cp', str(temp),
                '-main', 'Main',
                '--interp',
            ]
            result = subprocess.run(command, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
