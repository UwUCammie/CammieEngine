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

    def test_mutable_rgb_array_uses_legacy_triplet_before_packed_color(self):
        source = (ROOT / "source/Character.hx").read_text(encoding="utf-8")
        self.assertIn("healthColorArray(get, set):Array<Int>", source)
        self.assertIn("nightmareVisionHealthColorArray:Array<Int> = [255, 0, 0]", source)
        self.assertIn("loadNightmareVisionHealthColors(definition)", source)
        self.assertIn("Reflect.field(definition, 'healthbar_colors')", source)
        self.assertIn("EngineCompat.psychHealthColorArray", (ROOT / "source/PlayState.hx").read_text(encoding="utf-8"))

        getter = extract_method(source, "function get_healthColour()")
        setter = extract_method(source, "function set_healthColour(value:FlxColor):FlxColor")
        array_getter = extract_method(source, "function get_healthColorArray():Array<Int>")
        array_setter = extract_method(source, "function set_healthColorArray(value:Array<Int>):Array<Int>")
        packed_array = extract_method(source, "static function nightmareVisionColorArrayFromPacked(")
        load_colors = extract_method(source, "function loadNightmareVisionHealthColors(")
        number = extract_method(source, "static function nightmareVisionNumber(")

        fixture = '''
import flixel.util.FlxColor;

class Character {
  public var isPlayer:Bool;
  public var playerColor:FlxColor = 0xFF66FF33;
  public var enemyColor:FlxColor = 0xFFFF0000;
  public var nightmareVisionCharacterData:Dynamic = null;
  var nightmareVisionHealthColour:Null<FlxColor> = null;
  var nightmareVisionHealthColorArray:Array<Int> = [255, 0, 0];
  public var healthColour(get, set):FlxColor;
  public var healthColorArray(get, set):Array<Int>;
''' + getter + '\n' + setter + '\n' + array_getter + '\n' + array_setter + '\n' + packed_array + '\n' + load_colors + '\n' + number + '''
  public function new(definition:Dynamic, player:Bool=false) {
    isPlayer=player;
    healthColorArray=nightmareVisionColorArrayFromPacked(healthColour);
    if (definition != null) loadNightmareVisionHealthColors(definition);
  }
}

class Main {
  static function check(value:Bool, message:String):Void if (!value) throw message;
  static function packed(value:FlxColor):Int return cast value;
  static function main():Void {
    var noDefinitionPlayer = new Character(null, true);
    check(noDefinitionPlayer.healthColorArray[0] == 0x66
      && noDefinitionPlayer.healthColorArray[1] == 0xFF
      && noDefinitionPlayer.healthColorArray[2] == 0x33,
      'generic Character RGB fallback must derive from packed player healthColour');

    var authored:Array<Int> = [12, 34, 56];
    var triplet = new Character({healthbar_colors:authored, healthbar_colour:-8751940});
    check(triplet.healthColorArray == authored,
      'authored RGB array identity must be preserved for mutable source scripts');
    check(packed(triplet.healthColour) == 0xFF0C2238,
      'legacy healthbar_colors triplet must take precedence over healthbar_colour');
    authored[0] = 99;
    check(triplet.healthColorArray[0] == 99,
      'mutating the authored RGB array must mutate the Character view');
    check(packed(triplet.healthColour) == 0xFF0C2238,
      'packed healthColour remains the loaded value until explicitly changed');

    var packedOnly = new Character({healthbar_colour:-8751940});
    check(packed(packedOnly.healthColour) == 0xFF7A74BC
      && packedOnly.healthColorArray[0] == 0x7A
      && packedOnly.healthColorArray[1] == 0x74
      && packedOnly.healthColorArray[2] == 0xBC,
      'packed healthbar_colour must provide the RGB fallback');

    var replacement:Array<Int> = [7, 8, 9];
    Reflect.setProperty(packedOnly, 'healthColorArray', replacement);
    check(packedOnly.healthColorArray == replacement,
      'assigning an array must preserve the replacement reference');
    replacement[1] = 88;
    check(packedOnly.healthColorArray[1] == 88,
      'mutating a replacement array must remain visible through Character');
    Reflect.setProperty(packedOnly, 'healthColour', 0xFF998877);
    check(packed(packedOnly.healthColour) == 0xFF998877,
      'packed healthColour script override remains writable');

    var defaultArray = new Character({healthbar_colour:'not-a-colour'});
    check(defaultArray.healthColorArray[0] == 255
      && defaultArray.healthColorArray[1] == 0
      && defaultArray.healthColorArray[2] == 0,
      'invalid packed color uses the sensible enemy RGB fallback');

    // PlayState's Lua property bridge uses Reflect.field to detect a concrete
    // array. Keep the Character script property from shadowing that adapter.
    check(Reflect.field(triplet, 'healthColorArray') == null,
      'healthColorArray property must not replace the icon-aware Lua read path');
  }
}
'''
        flx_color_stub = '''package flixel.util;
abstract FlxColor(Int) from Int to Int {
  public static inline function fromInt(value:Int):FlxColor return cast value;
  public static function fromRGB(red:Int, green:Int, blue:Int, alpha:Int=255):FlxColor {
    return cast ((alpha << 24) | ((red & 0xFF) << 16) | ((green & 0xFF) << 8) | (blue & 0xFF));
  }
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


if __name__ == "__main__":
    unittest.main()
