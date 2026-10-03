"""Regression coverage for Psych's string-valued generic property writes."""
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


class PsychPropertyCoercionTest(unittest.TestCase):
    def test_event_strings_coerce_at_the_shared_property_boundary(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        methods = []
        for marker in (
            "function compatPathIndex",
            "function compatReadPathPart",
            "function compatParseColor",
            "function compatCoercePropertyValue",
            "function compatWritePathPart",
        ):
            method = extract_method(source, marker)
            method = method.replace(
                "function " + marker.split("function ", 1)[1],
                "static function " + marker.split("function ", 1)[1],
                1,
            )
            methods.append(method)
        fixture = """
class FlxColor {{
  public static function fromString(value:String):Null<Int> {{
    if (value == "#112233") return 0xFF112233;
    return null;
  }}
}}
class PsychRGBShaderReference {{}}
class EngineCompat {{
  public static function psychHealthColorArray(actor:Dynamic, playerActor:Dynamic,
      opponentActor:Dynamic, girlfriendActor:Dynamic, playerIcon:Dynamic,
      opponentIcon:Dynamic):Array<Int> return [255, 255, 255];
}}
class Note {{
  public var hitHealth:Null<Float> = null;
  public var missHealth:Null<Float> = null;
  public function new() {{}}
}}
class PropertyCoercionCompat {{
{methods}
  static var boyfriend:Dynamic;
  static var dad:Dynamic;
  static var gf:Dynamic;
  static var iconP1:Dynamic;
  static var iconP2:Dynamic;
  static function main() {{
    var target:Dynamic = {{
      defaultCamZoom: 1.25,
      color: 0xFFFFFFFF,
      borderColor: 0xFFFFFFFF,
      visible: true,
      count: 2,
      text: ""
    }};
    if (!compatWritePathPart(target, "defaultCamZoom", "0.875")
        || target.defaultCamZoom != 0.875)
      throw "numeric event string was not coerced";
    if (!compatWritePathPart(target, "visible", "false") || target.visible != false)
      throw "false event string was not coerced";
    if (!compatWritePathPart(target, "visible", "1") || target.visible != true)
      throw "true event string was not coerced";
    if (!compatWritePathPart(target, "count", "7") || target.count != 7)
      throw "integer event string was not coerced";
    if (!compatWritePathPart(target, "color", "000000")
        || target.color != 0xFF000000)
      throw "bare generic color was not normalized";
    if (!compatWritePathPart(target, "borderColor", "112233")
        || target.borderColor != 0xFF112233)
      throw "bare border color was not normalized";
    if (!compatWritePathPart(target, "text", "123") || target.text != "123")
      throw "string property was unexpectedly coerced";
  }}
}}
""".format(methods="\n".join(methods))
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "PropertyCoercionCompat.hx"
            path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "PropertyCoercionCompat", "--interp"],
                cwd=ROOT,
                env={**__import__("os").environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(DONOR.is_dir(), "mounted FNF-Example-Mods corpus is unavailable")
    def test_mounted_corpus_exercises_numeric_and_generic_color_writes(self):
        zoom_calls = []
        for path in DONOR.rglob("*.lua"):
            text = path.read_text(errors="ignore")
            zoom_calls.extend(
                (path.relative_to(DONOR), line)
                for line in text.splitlines()
                if re.search(
                    r"setProperty\s*\(\s*['\"]defaultCamZoom['\"]\s*,\s*value1\s*\)",
                    line,
                    re.IGNORECASE,
                )
            )
        self.assertGreaterEqual(len(zoom_calls), 5)
        self.assertTrue(
            {
                "psych/PERFEXION Demo1/custom_events/Set Cam ZoomBoom.lua",
                "psych/PERFEXION Demo1/custom_events/Set Cam ZoomBoomSlow.lua",
                "psych/PERFEXION Demo1/custom_events/Set Cam Zoom.lua",
                "psych/PERFEXION Demo1/custom_events/Set Cam Default Zoom.lua",
                "psych/PERFEXION Demo1/custom_events/Zoom Camera.lua",
            }.issubset({path.as_posix() for path, _ in zoom_calls}),
        )

        silhouette = DONOR / "psych/PERFEXION Demo1/custom_events/Silhouette.lua"
        self.assertTrue(silhouette.is_file())
        self.assertTrue(
            any(
                re.search(r"setProperty\s*\([^\n]*\.color[^\n]*['\"]000000['\"]", line)
                for line in silhouette.read_text(errors="ignore").splitlines()
            )
        )

        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("function compatCoercePropertyValue", play_state)
        self.assertIn("var writeValue = compatCoercePropertyValue(target, token, value)", play_state)
        self.assertIn("Std.isOfType(current, Float)", play_state)
        self.assertIn("normalizedField == 'color' || normalizedField == 'bordercolor'", play_state)


if __name__ == "__main__":
    unittest.main()
