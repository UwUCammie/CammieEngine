"""The CoolUtil helpers Psych and Nightmare Vision scripts share behave like the source ones."""
import subprocess
import tempfile
import unittest

from base_helper_fixtures import extract_block
from haxe_test_support import FixturePath as Path, HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]

MARKERS = (
    "public static function getBlendMode(",
    "public static function capitalize(",
    "public static function listFromString(",
    "public static function getBlendFromString(",
    "public static function correctArray<T>(",
    "public static function copyMapValues<K, V>(",
    "public static function cancelMusicFadeTween(",
    "static function dominantPixelColor(",
)

BLEND_MODE = r'''package openfl.display;
enum abstract BlendMode(String) {
 var ADD='add'; var ALPHA='alpha'; var DARKEN='darken'; var DIFFERENCE='difference';
 var ERASE='erase'; var HARDLIGHT='hardlight'; var INVERT='invert'; var LAYER='layer';
 var LIGHTEN='lighten'; var MULTIPLY='multiply'; var NORMAL='normal'; var OVERLAY='overlay';
 var SCREEN='screen'; var SHADER='shader'; var SUBTRACT='subtract';
}
'''

FLXG = r'''package flixel;
class FlxG { public static var sound:FixtureSound = new FixtureSound(); }
class FixtureSound { public var music:FixtureMusic; public function new() {} }
class FixtureMusic { public var fadeTween:FixtureTween; public function new() {} }
class FixtureTween {
 public var cancelled:Bool=false;
 public function new() {}
 public function cancel():Void cancelled=true;
}
'''

MAIN = r'''import openfl.display.BlendMode;
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  check(CoolUtil.capitalize('hELLO world') == 'Hello world', 'capitalize upper-cases only the first letter');
  check(CoolUtil.capitalize('') == '', 'capitalize keeps an empty string');
  var lines=CoolUtil.listFromString('  one \r\ntwo\r\n\r\n three  \n');
  check(lines.join('|') == 'one|two||three', 'listFromString trims the text and every CRLF line');
  check(CoolUtil.getBlendFromString(' ADD ') == CoolUtil.getBlendMode('add'),
   'getBlendFromString reads the same blend modes as getBlendMode');
  check(CoolUtil.getBlendFromString('nonsense') == BlendMode.NORMAL
   && CoolUtil.getBlendFromString(null) == BlendMode.NORMAL, 'unknown blends fall back to NORMAL');
  var fallback=[1.0, 1.0, 5.0];
  var corrected=CoolUtil.correctArray([2.0, 3.0], fallback);
  check(corrected == fallback && corrected.join(',') == '2,3,5',
   'correctArray writes input over the front of the fallback and returns it');
  var from=['a'=>1, 'b'=>2];
  var to=['b'=>9, 'c'=>3];
  CoolUtil.copyMapValues(from, to);
  check(to.get('a') == 1 && to.get('b') == 2 && to.get('c') == 3, 'copyMapValues overwrites and keeps extra keys');
  CoolUtil.cancelMusicFadeTween();
  var music=new flixel.FlxG.FixtureMusic();
  var tween=new flixel.FlxG.FixtureTween();
  music.fadeTween=tween;
  flixel.FlxG.sound.music=music;
  CoolUtil.cancelMusicFadeTween();
  check(tween.cancelled && music.fadeTween == null, 'cancelMusicFadeTween cancels and clears the music fade');
  var red=0xFFFF0000; var blue=0x800000FF; var faint=0x0200FF00; var black=0xFF000000;
  var image=[[red, blue, blue], [black, black, black], [faint, faint, faint], [red, black, faint]];
  var picked=@:privateAccess CoolUtil.dominantPixelColor(4, 3, function(x, y) return image[x][y]);
  check(picked == 0xFF0000FF, 'dominantColor counts translucent pixels as opaque and skips black and faint ones');
  check(@:privateAccess CoolUtil.dominantPixelColor(1, 1, function(x, y) return black) == black,
   'an all black image reports black');
 }
}
'''


class CoolUtilSourceHelpersTest(unittest.TestCase):
    def test_shared_script_helpers(self):
        source = (ROOT / "source/CoolUtil.hx").read_text(encoding="utf-8")
        browser = source[source.index("public static function browserLoad("):]
        self.assertIn("CodenameOpenURLCompat.open(site", browser[:200],
                      "browserLoad must go through the shared URL checks")
        methods = "\n".join(extract_block(source, marker) for marker in MARKERS)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "openfl/display").mkdir(parents=True)
            (work / "openfl/display/BlendMode.hx").write_text(BLEND_MODE, encoding="utf-8")
            (work / "flixel").mkdir()
            (work / "flixel/FlxG.hx").write_text(FLXG, encoding="utf-8")
            (work / "CoolUtil.hx").write_text(
                "import openfl.display.BlendMode;\nusing StringTools;\nclass CoolUtil {\n" + methods + "\n}\n",
                encoding="utf-8")
            (work / "Main.hx").write_text(MAIN, encoding="utf-8")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
