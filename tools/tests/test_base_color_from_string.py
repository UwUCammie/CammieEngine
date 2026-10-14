"""Script colours are read by one base function; camera flash and fade use it."""
import subprocess
import tempfile
import unittest

from base_helper_fixtures import cool_util_colors, play_state_method
from haxe_test_support import HAXE_COMMAND, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

FIXTURE = r'''
// Same contract as the real colour type: names in any case, or prefixed hex.
class FlxColor {
 static var names:Map<String, Int> = ['RED' => 0xFFFF0000, 'GREEN' => 0xFF008000, 'BLUE' => 0xFF0000FF,
  'WHITE' => 0xFFFFFFFF, 'BLACK' => 0xFF000000, 'TRANSPARENT' => 0x00000000];
 public static function fromString(value:String):Null<Int> {
  var upper = StringTools.trim(value).toUpperCase();
  if (names.exists(upper)) return names.get(upper);
  return null;
 }
}
class Camera {
 public var log:Array<String> = [];
 public function new() {}
 public function flash(color:Int, duration:Float, onComplete:Dynamic, force:Bool):Void
  log.push('flash ' + StringTools.hex(color, 8) + ' ' + duration + ' ' + force);
 public function fade(color:Int, duration:Float, fadeIn:Bool, onComplete:Dynamic, force:Bool):Void
  log.push('fade ' + StringTools.hex(color, 8) + ' ' + duration + ' in=' + fadeIn + ' ' + force);
}
class Main {
 var cameras:Map<String, Camera> = ['game' => new Camera(), 'hud' => new Camera()];
 function new() {}
 function compatCameraForName(name:Dynamic):Camera return cameras.get(Std.string(name));
__METHODS__
 static function same(actual:Null<Int>, expected:Null<Int>, label:String):Void
  if (actual != expected) throw label + ': got ' + (actual == null ? 'null' : StringTools.hex(actual, 8));
 static function main() {
  for (text in ['RED', 'red', ' Red ', '#FF0000', 'FF0000', 'ff0000', '0xFFFF0000', '0xFF0000', '#FFFF0000'])
   same(CoolUtil.colorFromString(text), 0xFFFF0000, 'red spelling "' + text + '"');
  same(CoolUtil.colorFromString('BLUE'), 0xFF0000FF, 'a colour name must not be read as hex digits');
  same(CoolUtil.colorFromString('GREEN'), 0xFF008000, 'colour name');
  same(CoolUtil.colorFromString('FF000000'), 0xFF000000, 'eight digit ARGB');
  same(CoolUtil.colorFromString('FFFFFFFF'), 0xFFFFFFFF, 'full alpha must not be clamped');
  same(CoolUtil.colorFromString('80112233'), 0x80112233, 'authored alpha kept');
  same(CoolUtil.colorFromString('0x00FFFFFF'), 0x00FFFFFF, 'authored zero alpha kept');
  same(CoolUtil.colorFromString(0xFF0000), 0xFFFF0000, 'RGB number becomes opaque');
  same(CoolUtil.colorFromString(0x80112233), 0x80112233, 'ARGB number kept');
  same(CoolUtil.colorFromString(16711680.0), 0xFFFF0000, 'float RGB number');
  for (junk in ['not-a-colour', 'zzz', '', '   '])
   same(CoolUtil.colorFromString(junk), 0xFFFFFFFF, 'unreadable text is white: "' + junk + '"');
  same(CoolUtil.colorFromString(null), 0xFFFFFFFF, 'null is white');
  // Callers that must leave things alone on bad input can tell the difference.
  same(CoolUtil.colorFromStringOrNull('not-a-colour'), null, 'nullable reader on junk');
  same(CoolUtil.colorFromStringOrNull(null), null, 'nullable reader on null');
  same(CoolUtil.colorFromStringOrNull(''), null, 'nullable reader on empty text');
  same(CoolUtil.colorFromStringOrNull('white'), 0xFFFFFFFF, 'nullable reader on a real colour');

  var state = new Main();
  var game = state.cameras.get('game');
  state.compatCameraFlash('game', 'BLUE', 0.5);
  state.compatCameraFlash('game', 'FF000000', 1, true);
  state.compatCameraFade('game', 'red', 2);
  state.compatCameraFade('game', '0xFF00FF00', 1, true);
  state.compatCameraFade('game', 'BLACK', 0.25, false, true);
  state.compatCameraFade('game', 'BLACK', -3, true, true);
  var expected = ['flash FF0000FF 0.5 false', 'flash FF000000 1 true', 'fade FFFF0000 2 in=false false',
   'fade FF00FF00 1 in=false true', 'fade FF000000 0.25 in=true false', 'fade FF000000 0 in=true true'];
  if (game.log.join('|') != expected.join('|')) throw 'camera calls: ' + game.log.join('|');
  // The base functions are what other layers call.
  state.flashCamera('hud', 0x00FF00, 1);
  state.fadeCamera('hud', 'white', 1, false, true);
  if (state.cameras.get('hud').log.join('|') != 'flash FF00FF00 1 false|fade FFFFFFFF 1 in=true false')
   throw 'base camera calls: ' + state.cameras.get('hud').log.join('|');
  state.flashCamera('missing', 'red', 1);
  state.fadeCamera('missing', 'red', 1);
 }
}
'''


class BaseColorFromStringTest(unittest.TestCase):
    def test_colour_text_and_camera_flash_fade(self):
        methods = "\n".join(play_state_method(marker) for marker in (
            "public function flashCamera(", "public function fadeCamera(",
            "function compatCameraFlash(", "function compatCameraFade(",
        ))
        methods = methods.replace("\tfunction compatCamera", "\tpublic function compatCamera")
        fixture = FIXTURE.replace("__METHODS__", methods) + cool_util_colors()
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(fixture, newline="\n")
            # Windows is where a single 32-bit parse used to clamp the alpha byte.
            result = subprocess.run([*HAXE_COMMAND, "-cp", folder, "-main", "Main", "--interp"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_every_script_colour_path_delegates_to_the_base_reader(self):
        for marker, call in (("function compatParseColor(", "CoolUtil.colorFromStringOrNull(value)"),
                             ("function compatGetColorFromHex(", "CoolUtil.colorFromString(value)")):
            body = play_state_method(marker)
            self.assertIn(call, body)
            self.assertNotIn("Std.parseInt", body)
        bindings = (ROOT / "source/PsychSourceBindings.hx").read_text(encoding="utf-8")
        self.assertIn("return CoolUtil.colorFromString(value);", bindings)
        fade = play_state_method("function compatCameraFade(")
        self.assertIn("?fadeOut:Bool = false", fade)
        self.assertIn("fadeCamera(cameraName, color, duration, forced == true, fadeOut == true)", fade)


if __name__ == "__main__":
    unittest.main()
