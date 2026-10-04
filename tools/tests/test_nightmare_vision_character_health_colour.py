"""Exercise the NMV Character.healthColour identity bridge."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class NightmareVisionCharacterHealthColourTest(unittest.TestCase):
    def test_packed_character_colors_and_script_overrides(self):
        source = (ROOT / "source/Character.hx").read_text()
        self.assertIn("healthColour(get, set):FlxColor", source)
        self.assertIn("Reflect.field(nightmareVisionCharacterData, 'healthbar_colour')", source)
        getter = extract_method(source, "function get_healthColour()")
        setter = extract_method(source, "function set_healthColour(value:FlxColor):FlxColor")
        fixture = '''
import flixel.util.FlxColor;

class Character {
  public var isPlayer:Bool;
  public var playerColor:FlxColor = 0xFF66FF33;
  public var enemyColor:FlxColor = 0xFFFF0000;
  public var nightmareVisionCharacterData:Dynamic;
  var nightmareVisionHealthColour:Null<FlxColor> = null;
  public var healthColour(get, set):FlxColor;
''' + getter + '\n' + setter + '''
  public function new(definition:Dynamic, player:Bool = false) {
    nightmareVisionCharacterData = definition;
    isPlayer = player;
  }
}

class Main {
  static function check(value:Bool, message:String):Void if (!value) throw message;
  static function packed(value:FlxColor):Int return cast value;
  static function main():Void {
    var darnell = new Character({healthbar_colour:-8751940});
    check(packed(darnell.healthColour) == 0xFF7A74BC,
      'signed NMV Darnell healthbar colour did not preserve its packed ARGB value');
    var boyfriend = new Character({healthbar_colour:-1813032}, true);
    check(packed(boyfriend.healthColour) == 0xFFE455D8,
      'NMV boyfriend healthbar colour was not read from its own definition');
    var pico = new Character({healthbar_colour:-1402941}, true);
    check(packed(pico.healthColour) == 0xFFEA97C3,
      'NMV Pico healthbar colour was not read from its own definition');
    var stringColor = new Character({healthbar_colour:'#123456'});
    check(packed(stringColor.healthColour) == 0xFF123456,
      'string healthbar colour did not receive opaque alpha');
    var malformed = new Character({healthbar_colour:'not-a-colour'});
    check(packed(malformed.healthColour) == 0xFFFF0000,
      'invalid authored colour did not use the enemy fallback');
    var missingPlayer = new Character(null, true);
    check(packed(missingPlayer.healthColour) == 0xFF66FF33,
      'characters without NMV data lost the native player fallback');
    var missingOpponent = new Character(null);
    check(packed(missingOpponent.healthColour) == 0xFFFF0000,
      'characters without NMV data lost the native opponent fallback');
    Reflect.setProperty(darnell, 'healthColour', 0xFF998877);
    check(Std.int(Reflect.getProperty(darnell, 'healthColour')) == 0xFF998877,
      'stage-script healthColour override did not remain writable');
    Sys.println('nightmare-vision-character-health-colour-ok');
  }
}
'''
        flx_color_stub = '''package flixel.util;
abstract FlxColor(Int) from Int to Int {
  public static inline function fromInt(value:Int):FlxColor return cast value;
  public static function fromString(value:String):Null<FlxColor> {
    var clean = StringTools.trim(value);
    if (!(StringTools.startsWith(clean, '#') || StringTools.startsWith(clean, '0x'))) return null;
    var hex = StringTools.startsWith(clean, '#') ? clean.substr(1) : clean.substr(2);
    if (hex.length != 6 && hex.length != 8) return null;
    var parsed = Std.parseInt('0x' + hex);
    return parsed == null ? null : cast (hex.length == 6 ? parsed | 0xFF000000 : parsed);
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            color_path = work / "flixel/util/FlxColor.hx"
            color_path.parent.mkdir(parents=True, exist_ok=True)
            color_path.write_text(flx_color_stub, newline="\n")
            (work / "Main.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "--run", "Main"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("nightmare-vision-character-health-colour-ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
