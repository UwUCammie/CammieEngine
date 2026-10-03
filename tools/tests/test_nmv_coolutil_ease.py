from haxe_test_support import HAXE_COMMAND
import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"


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
                return source[start:index + 1]
    raise AssertionError(f"Unclosed method body for {marker}")


class NightmareVisionCoolUtilEaseTest(unittest.TestCase):
    def test_source_easing_aliases_execute_with_source_fallbacks(self):
        source = (ROOT / "source" / "CoolUtil.hx").read_text()
        method = extract_method(source, "public static function getEaseFromString(")

        aliases = {
            "backin": "backIn", "backinout": "backInOut", "backout": "backOut",
            "bouncein": "bounceIn", "bounceinout": "bounceInOut", "bounceout": "bounceOut",
            "circin": "circIn", "circinout": "circInOut", "circout": "circOut",
            "cubein": "cubeIn", "cubeinout": "cubeInOut", "cubeout": "cubeOut",
            "elasticin": "elasticIn", "elasticinout": "elasticInOut", "elasticout": "elasticOut",
            "expoin": "expoIn", "expoinout": "expoInOut", "expoout": "expoOut",
            "quadin": "quadIn", "quadinout": "quadInOut", "quadout": "quadOut",
            "quartin": "quartIn", "quartinout": "quartInOut", "quartout": "quartOut",
            "quintin": "quintIn", "quintinout": "quintInOut", "quintout": "quintOut",
            "sinein": "sineIn", "sineinout": "sineInOut", "sineout": "sineOut",
            "smoothstepin": "smoothStepIn", "smoothstepinout": "smoothStepInOut",
            "smoothstepout": "smoothStepOut",
            "smootherstepin": "smootherStepIn", "smootherstepinout": "smootherStepInOut",
            "smootherstepout": "smootherStepOut",
        }
        haxe_cases = "\n".join(
            f'    if (CoolUtil.getEaseFromString("{alias}") != "{field}") throw "{alias}";'
            for alias, field in aliases.items()
        )
        haxe = f"""
using StringTools;
class FlxEase {{
  public static inline var linear:String = "linear";
{chr(10).join(f'  public static inline var {field}:String = "{field}";' for field in sorted(set(aliases.values())))}
}}
class CoolUtil {{
  {method}
}}
class Main {{
  static function main() {{
{haxe_cases}
    if (CoolUtil.getEaseFromString("  BaCkInOuT  ") != "backInOut") throw "trim/case normalization";
    if (CoolUtil.getEaseFromString(null) != "linear") throw "null fallback";
    if (CoolUtil.getEaseFromString("") != "linear") throw "empty fallback";
    if (CoolUtil.getEaseFromString("unknownEase") != "linear") throw "unknown fallback";
  }}
}}
"""

        with tempfile.TemporaryDirectory() as folder:
            (pathlib.Path(folder) / "Main.hx").write_text(haxe, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
