"""Regression coverage for indexed Psych/Kade property paths and colours."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class PsychPropertyPathTest(unittest.TestCase):
    def run_haxe(self, source: str, name: str) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / f"{name}.hx"
            path.write_text(source, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", name, "--interp"],
                cwd=ROOT,
                env={**__import__("os").environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_indexed_reads_and_writes_share_the_runtime_traversal(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        methods = []
        for marker in (
            "function compatPathTokens",
            "function compatPathIndex",
            "function compatReadPathPart",
            "function compatParseColor",
            "function compatCoercePropertyValue",
            "function compatWritePathPart",
            "function compatReadPath(target:Dynamic",
            "function compatWritePath(target:Dynamic",
        ):
            method = extract_method(source, marker)
            method = method.replace("function " + marker.split("function ", 1)[1],
                                    "static function " + marker.split("function ", 1)[1], 1)
            methods.append(method)
        fixture = """
class FlxColor {
  public static function fromString(value:String):Null<Int> return null;
}
class PsychRGBShaderReference {}
class EngineCompat {
  public static function psychHealthColorArray(actor:Dynamic, playerActor:Dynamic,
      opponentActor:Dynamic, girlfriendActor:Dynamic, playerIcon:Dynamic,
      opponentIcon:Dynamic):Array<Int> {
    var direct:Dynamic = Reflect.field(actor, 'healthColorArray');
    return direct == null ? [255, 255, 255] : cast direct;
  }
}
class Note {
  public var hitHealth:Null<Float> = null;
  public var missHealth:Null<Float> = null;
  public function new() {}
}
class IndexedPathCompat {
__METHODS__
  static var boyfriend:Dynamic;
  static var dad:Dynamic;
  static var gf:Dynamic;
  static var iconP1:Dynamic;
  static var iconP2:Dynamic;
  static function main() {
    var target:Dynamic = {
      healthColorArray: [101, 202, 303],
      touches: {list: [{screenX: 123, screenY: 456}]}
    };
    if (compatReadPath(target, "healthColorArray[1]") != 202)
      throw "array property read failed";
    if (compatReadPath(target, "touches.list[0].screenX") != 123)
      throw "nested indexed property read failed";
    if (!compatWritePath(target, "healthColorArray[2]", 909)
        || target.healthColorArray[2] != 909)
      throw "array property write failed";
    if (!compatWritePath(target, "touches.list[0].screenY", 777)
        || target.touches.list[0].screenY != 777)
      throw "nested indexed property write failed";

    var group:Dynamic = {members: [{x: 42}]};
    if (compatReadPath(group, "[0].x") != 42)
      throw "FlxGroup members read failed";
    if (!compatWritePath(group, "[0].x", 84) || group.members[0].x != 84)
      throw "FlxGroup members write failed";
    if (compatReadPath(target, "touches.list[9].screenX") != null)
      throw "out-of-range read should be null";
    var psychNote = new Note();
    if (compatCoercePropertyValue(psychNote, "hitHealth", "0") != 0
        || compatCoercePropertyValue(psychNote, "missHealth", "0.125") != 0.125)
      throw "Psych note health strings were not coerced before typed writes";
  }
}
""".replace("__METHODS__", "\n".join(methods))
        self.run_haxe(fixture, "IndexedPathCompat")

    def test_flxg_class_paths_keep_the_real_game_root(self):
        play_state = (ROOT / "source/PlayState.hx").read_text()
        engine_compat = (ROOT / "source/EngineCompat.hx").read_text()
        self.assertIn("RuntimeSmokeHarness.enabled() && !psychFlxGGameTicksProbeEmitted", play_state)
        self.assertIn("ticksReflectType=' + psychClassPropertyProbeType(reflectedTicks)", play_state)
        self.assertIn("resultType=' + psychClassPropertyProbeType(result)", play_state)
        methods = []
        for marker in (
            "function compatClassPropertyPath",
            "function compatGetPropertyFromClass",
            "function compatSetPropertyFromClass",
            "function compatFlxGStaticRoot",
            "function compatPropertySeparator",
            "function compatPathTokens",
            "function compatPathIndex",
            "function compatReadPathPart",
            "function compatReadPath(target:Dynamic",
            "function tracePsychFlxGGameTicksProbe",
            "static function psychClassPropertyProbeValue",
            "static function psychClassPropertyProbeType",
        ):
            method = extract_method(play_state, marker)
            if marker == "function compatClassPropertyPath":
                method = method.replace("function compatClassPropertyPath",
                                        "static function compatClassPropertyPath", 1)
            methods.append(method)
        engine_methods = []
        for marker in (
            "public static function propertyPath",
            "public static function propertyRoot",
        ):
            engine_methods.append(extract_method(engine_compat, marker))
        fixture = """
using StringTools;
class PlayState {}
class FlxG {
  public static var game:Dynamic = {ticks: 123456};
  public static var state:Dynamic = {};
  public static var camera:Dynamic = {};
  public static var cameras:Dynamic = [];
  public static var scaleMode:Dynamic = {};
  public static var width:Int = 1280;
  public static var height:Int = 720;
  public static var elapsed:Float = 0.016;
  public static var timeScale:Float = 1;
}
class Judge {
  public static var sickJudge:Float = 45;
  public static var goodJudge:Float = 90;
  public static var badJudge:Float = 135;
  public static var shitJudge:Float = 166;
}
class OptionsHandler {
  public static var options:Dynamic = {showNoteSplashes: true};
}
class RuntimeSmokeHarness {
  public static function enabled():Bool return false;
}
class EngineCompat {
__ENGINE_METHODS__
  public static function legacyClassProperty(_className:String, _path:String):String return null;
  public static function psychHealthColorArray(_actor:Dynamic, _player:Dynamic,
      _opponent:Dynamic, _girlfriend:Dynamic, _playerIcon:Dynamic,
      _opponentIcon:Dynamic):Array<Int> return [255, 255, 255];
}
class PsychClassPathCompat {
__METHODS__
  public function new() {}
  var psychGameOverDeathDelaySeconds:Float = 0;
  var psychGameOverOverrides:Map<String, Dynamic> = [];
  var boyfriend:Dynamic;
  var dad:Dynamic;
  var gf:Dynamic;
  var iconP1:Dynamic;
  var iconP2:Dynamic;
  var pixelUI:Bool = false;
  var psychFlxGGameTicksProbeEmitted:Bool = false;
  public var lastWriteTarget:Dynamic;
  public var lastWritePath:String = '';
  function psychGameOverClassPropertyKey(_className:Dynamic, _path:Dynamic):String return null;
  function compatResolveClass(name:Dynamic):Dynamic
    return name != null && Std.string(name).toLowerCase() == 'flixel.flxg' ? FlxG : null;
  function compatWritePath(target:Dynamic, path:String, _value:Dynamic):Bool {
    lastWriteTarget = target;
    lastWritePath = path;
    return true;
  }
  static function main() {
    var compat = new PsychClassPathCompat();
    if (EngineCompat.propertyPath('game.ticks') != 'ticks')
      throw 'ordinary Psych property normalization changed';
    if (compatClassPropertyPath(FlxG, 'game.ticks') != 'game.ticks')
      throw 'FlxG.game root was stripped';
    if (compat.compatGetPropertyFromClass('flixel.FlxG', 'game.ticks') != 123456)
      throw 'Psych FlxG game.ticks lookup did not reach the live game object';
    if (compatClassPropertyPath(PlayState, 'game.camOther.zoom') != 'camOther.zoom')
      throw 'PlayState-relative game alias changed';
    compat.compatSetPropertyFromClass('flixel.FlxG', 'game.ticks', 654321);
    if (compat.lastWriteTarget != FlxG.game || compat.lastWritePath != 'ticks')
      throw 'Psych FlxG game.ticks write did not reach the live game object';
  }
}
""".replace("__METHODS__", "\n".join(methods)).replace(
            "__ENGINE_METHODS__", "\n".join(engine_methods))
        self.run_haxe(fixture, "PsychClassPathCompat")

    def test_bare_psych_hex_text_colours_are_normalized(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        method = extract_method(source, "function compatParseColor")
        method = method.replace("function compatParseColor", "static function compatParseColor", 1)
        graphic_method = extract_method(source, "function compatMakeGraphic(name:Dynamic")
        graphic_method = graphic_method.replace("function compatMakeGraphic", "static function compatMakeGraphic", 1)
        fixture = """
class FlxColor {{
  public static function fromString(value:String):Null<Int> {{
    if (value == "#112233") return 0xFF112233;
    if (value == "white") return 0xFFFFFFFF;
    return null;
  }}
}}
class FlxSprite {{
  public var graphicColor:Dynamic;
  public function new() {{}}
  public function makeGraphic(width:Int, height:Int, color:Dynamic):Void {{ graphicColor = color; }}
}}
class RuntimeSmokeHarness {{
  public static function enabled():Bool return false;
  public static function markStep(_phase:String):Void {{}}
}}
class ColorCompat {{
{method}
{graphic_method}
  static var object:Dynamic;
  static var psychGlobalProviderFirstSprite:FlxSprite = null;
  static var haxeSpriteAtlasNames:Map<String,Array<String>> = [];
  static var haxeSpriteAtlasNamesByObject:Map<FlxSprite,Array<String>> = [];
  static function markPsychGlobalProviderSpritePhase(_sprite:Dynamic, _phase:String, ?_detail:String):Void {{}}
  static function compatFindObject(name:Dynamic):Dynamic return object;
  static function compatForgetSpriteAtlas(sprite:Dynamic):Void {{
    if (sprite != null && Std.isOfType(sprite, FlxSprite))
      haxeSpriteAtlasNamesByObject.remove(cast sprite);
  }}
  static function tweenColorValue(value:Dynamic):Dynamic {{
    var parsed = compatParseColor(value);
    return parsed == null ? value : parsed;
  }}
  static function main() {{
    if (compatParseColor("FFFFFF") != 0xFFFFFFFF) throw "bare RGB was not parsed";
    if (compatParseColor("AABBCCDD") != 0xAABBCCDD) throw "bare RGBA was not parsed";
    if (compatParseColor("#AABBCCDD") != 0xAABBCCDD) throw "prefixed ARGB changed";
    if (compatParseColor("0xFFFFFFFF") != 0xFFFFFFFF) throw "full-alpha hex was clamped";
    if (compatParseColor(0xFEC85C) != 0xFFFEC85C) throw "numeric RGB tint was not opaque";
    if (compatParseColor(0x80112233) != 0x80112233) throw "explicit numeric alpha changed";
    if (compatParseColor("#112233") != 0xFF112233) throw "prefixed RGB changed";
    if (compatParseColor("white") != 0xFFFFFFFF) throw "named colour changed";
    if (compatParseColor("not-a-colour") != null) throw "invalid colour should be ignored";
    if (tweenColorValue("FF0000") != 0xFFFF0000) throw "tween colour was not normalized";
    object = new FlxSprite();
    compatMakeGraphic("no-colour", 1, 1);
    if (object.graphicColor != 0xFFFFFFFF) throw "makeGraphic default changed";
    compatMakeGraphic("bare-colour", 1, 1, "112233");
    if (object.graphicColor != 0xFF112233) throw "makeGraphic colour was not normalized";
  }}
}}
""".format(method=method, graphic_method=graphic_method)
        self.run_haxe(fixture, "ColorCompat")

    @unittest.skipUnless(DONOR.is_dir(), "mounted FNF-Example-Mods corpus is unavailable")
    def test_mounted_corpus_contains_the_indexed_and_bare_colour_forms(self):
        colored = DONOR / "psych/PERFEXION Demo1/custom_events/coloredSilhouette.lua"
        camera = DONOR / "psych/PERFEXION Demo1/data/Resonance/Used/CAMERA KNOE.lua"
        self.assertTrue(colored.is_file())
        self.assertTrue(camera.is_file())
        self.assertEqual(
            len(re.findall(r"healthColorArray\[[012]\]", colored.read_text(errors="ignore"))),
            9,
        )
        self.assertEqual(
            len(re.findall(r"touches\.list\[0\]\.(?:screenX|screenY)", camera.read_text(errors="ignore"))),
            2,
        )

        bare_colour_calls = 0
        for path in DONOR.rglob("*.lua"):
            text = path.read_text(errors="ignore")
            bare_colour_calls += len(re.findall(
                r"setText(?:Color|Border)\([^\n]*['\"][0-9A-Fa-f]{6}['\"]",
                text,
            ))
        self.assertEqual(bare_colour_calls, 15)

        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("function compatPathTokens", play_state)
        self.assertIn("function compatPropertySeparator", play_state)
        self.assertIn("function compatParseColor", play_state)
        self.assertIn("var high = Std.parseInt('0x' + digits.substr(0, 4))", play_state)
        self.assertIn("var low = Std.parseInt('0x' + digits.substr(4, 4))", play_state)
        self.assertIn("?color:Dynamic", play_state)
        self.assertIn("color == null ? 0xFFFFFFFF : compatParseColor(color)", play_state)
        self.assertIn("field.toLowerCase() == 'color'", play_state)
        self.assertIn("Reflect.setField(props, field, tweenValue)", play_state)

        color_tweens = []
        graphic_calls = []
        for path in DONOR.rglob("*.lua"):
            text = path.read_text(errors="ignore")
            color_tweens.extend(re.findall(r"\bdoTweenColor\s*\(([^\n]*)\)", text))
            graphic_calls.extend(re.findall(r"\bmakeGraphic\s*\(([^\n]*)\)", text))
        self.assertEqual(len(color_tweens), 54)
        self.assertEqual(sum(bool(re.search(r"['\"][0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?['\"]", call))
                           for call in color_tweens), 49)
        # Preserve the original source examples as new mounted packs add more
        # calls (the global results pack contributes additional graphics).
        self.assertGreaterEqual(len(graphic_calls), 16)
        self.assertGreaterEqual(sum(bool(re.search(r"['\"][0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?['\"]", call))
                                    for call in graphic_calls), 10)
        self.assertGreaterEqual(sum(len([part for part in call.split(',')]) == 3 for call in graphic_calls), 5)


if __name__ == "__main__":
    unittest.main()
