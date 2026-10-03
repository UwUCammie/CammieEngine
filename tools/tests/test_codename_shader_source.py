"""Owner-scoped GLSL imports are expanded before OpenFL shader compilation."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import json
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameShaderSourceTest(unittest.TestCase):
    def test_nested_imports_expand_and_invalid_or_cyclic_paths_fail_closed(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            (base / "Main.hx").write_text(r'''class Main {
 static function main():Void {
  var files:Map<String,String> = [
   "base/postprocess.frag" => "#import <shared/coords.glsl>\nuniform vec4 uCameraBounds;\n",
   "shared/coords.glsl" => "vec2 screenCoord;\n"
  ];
  var seen:Array<String> = [];
  var source = "#pragma header\n#import <base/postprocess.frag>\nfloat shade = 1 - sample(1.0);\n";
  var expanded = CodenameShaderSource.forOpenFL(source, function(key:String):String {
   seen.push(key);
   return files.get(key);
  });
  if (expanded.indexOf("#import") >= 0 || expanded.indexOf("vec2 screenCoord;") < 0
   || expanded.indexOf("uniform vec4 uCameraBounds;") < 0
   || expanded.indexOf("float shade = 1.0 - sample") < 0)
   throw "nested imports or OpenFL scalar normalization";
  if (seen.join(",") != "base/postprocess.frag,shared/coords.glsl") throw seen.join(",");
  var sampled = CodenameShaderSource.forOpenFL(
   "uniform float layernumbers;\nfloat SAMPLEDIST = layernumbers;\n"
   + "void main() { for (int i = 0; i < SAMPLEDIST; i++) { vec2 offset = vec2(0.5 * i); } }\n");
  if (sampled.indexOf("for (float i = 0.0; i < SAMPLEDIST; i++)") < 0)
   throw "float-bound iterator was not promoted";
  var scalarMath = CodenameShaderSource.forOpenFL(
   "float rnd(float x) { return fract(sin(dot(vec2(x + 48, 38 / (x + 2.5)), vec2(13, 78))) * (43758)); }\n"
   + "float negative(float x) { return x * -2; }\n");
  if (scalarMath.indexOf("x + 48.0") < 0 || scalarMath.indexOf("38.0 / (x + 2.5)") < 0
   || scalarMath.indexOf("(43758.0)") < 0 || scalarMath.indexOf("x * -2.0") < 0
   || scalarMath.indexOf("vec2(13, 78)") < 0)
   throw "mixed scalar literals were not promoted: " + scalarMath;
  var integerExpressions = CodenameShaderSource.forOpenFL(
   "uniform float scale; uniform int amount; void main() { int sum = 2 + 3; "
   + "for (int i = 0; i < amount; i++) { color[i + 1] = scale * 2; } }\n");
  if (integerExpressions.indexOf("int sum = 2 + 3") < 0
   || integerExpressions.indexOf("for (int i = 0; i < amount; i++)") < 0
   || integerExpressions.indexOf("color[i + 1]") < 0
   || integerExpressions.indexOf("scale * 2.0") < 0)
   throw "integer loops or indices changed during scalar promotion: " + integerExpressions;
  var indexed = CodenameShaderSource.forOpenFL(
   "float count = 3.0; void main() { for (int i = 0; i < count; i++) { color[i] = 0.0; } }");
  if (indexed.indexOf("for (int i = 0; i < count; i++)") < 0)
   throw "array iterator type changed";

  var integerCoordinates = CodenameShaderSource.forOpenFL(
   "float noise(int x, int y) { return hash12(vec2(x, y)); }\n"
   + "float smoothNoise(int x, int y) { return noise(x + 1.0, y) + noise(x - 1.0, y) "
   + "+ noise(x, y + 1.0) + noise(x, y - 1.0); }\n"
   + "float perlin(ivec2 i) { return smoothNoise(i.x + 1.0, i.y - 1.0); }\n"
   + "ivec2 adjacent(int x, int y) { return ivec2(x - 2.0, y + 2.0); }\n"
   + "float keepFloat(int x) { return float(x) + 1.0; }\n"
   + "float quotient(int x) { return x / 2.0; }\n");
  if (integerCoordinates.indexOf("noise(x + 1, y)") < 0
   || integerCoordinates.indexOf("noise(x - 1, y)") < 0
   || integerCoordinates.indexOf("noise(x, y + 1)") < 0
   || integerCoordinates.indexOf("noise(x, y - 1)") < 0
   || integerCoordinates.indexOf("smoothNoise(i.x + 1, i.y - 1)") < 0
   || integerCoordinates.indexOf("ivec2(x - 2, y + 2)") < 0
   || integerCoordinates.indexOf("float(x) + 1.0") < 0
   || integerCoordinates.indexOf("return x / 2.0") < 0)
   throw "integer-coordinate literals were not normalized without changing float math: " + integerCoordinates;

  var modernFeatures = CodenameShaderSource.normalizeOpenFL(
   "#pragma header\n#extension GL_EXT_gpu_shader4 : enable\n#extension GL_NV_non_square_matrices : enable\n"
   + "mat3x2 transform; void main() { float value = round(uv.x); }\n");
  if (!StringTools.startsWith(modernFeatures, "#version 130\n")
   || modernFeatures.indexOf("#extension GL_NV_non_square_matrices") >= 0
   || modernFeatures.indexOf("#extension GL_EXT_gpu_shader4") >= 0
   || modernFeatures.indexOf("mat3x2 transform") < 0 || modernFeatures.indexOf("round(uv.x)") < 0)
   throw "GLSL feature version or core extension normalization failed: " + modernFeatures;
  var explicitVersion = CodenameShaderSource.normalizeOpenFL(
   "#version 120\nvoid main() { float value = round(uv.x); }\n");
  if (!StringTools.startsWith(explicitVersion, "#version 130\n"))
   throw "explicit shader version was not raised to the required core version: " + explicitVersion;
  var currentVersion = CodenameShaderSource.normalizeOpenFL(
   "#version 330 core\nvoid main() { float value = round(uv.x); }\n");
  if (!StringTools.startsWith(currentVersion, "#version 330 core\n"))
   throw "newer explicit shader version was changed: " + currentVersion;

  var missing = false;
  try CodenameShaderSource.forOpenFL("#import <base/missing.frag>\n", function(_key:String):String return null)
   catch (error:Dynamic) missing = Std.string(error).indexOf("Missing scoped shader import") >= 0;
  if (!missing) throw "missing include did not fail with scoped diagnostic";
  var unsafe = false;
  try CodenameShaderSource.forOpenFL("#import <../foreign.frag>\n", function(_key:String):String return "")
   catch (error:Dynamic) unsafe = Std.string(error).indexOf("Invalid scoped shader import") >= 0;
  if (!unsafe) throw "path traversal include accepted";
  var cycle = false;
  try CodenameShaderSource.forOpenFL("#import <cycle.frag>\n", function(_key:String):String return "#import <cycle.frag>\n")
   catch (error:Dynamic) cycle = Std.string(error).indexOf("Cyclic shader import") >= 0;
  if (!cycle) throw "cyclic include accepted";
 }
}''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base), "--run", "Main"],
                cwd=ROOT, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_shared_shader_loader_normalizes_mounted_try_harder_cloud(self):
        donor = Path("/run/media/cammie/External Storage/FNF-Example-Mods/codename/D-Sides REDUX Codename Engine (Cancelled)/mods/D-Sides REDUX/shaders/cloud.frag")
        if not donor.exists():
            self.skipTest("D-Sides Try Harder donor shader is not mounted")
        source = donor.read_text(errors="ignore")
        rewrites = {
            "noise(x+1,y)": "noise(x+1.0,y)",
            "noise(x-1,y)": "noise(x-1.0,y)",
            "noise(x,y+1)": "noise(x,y+1.0)",
            "noise(x,y-1)": "noise(x,y-1.0)",
            "i.x + 1, i.y": "i.x + 1.0, i.y",
            "i.x, i.y + 1": "i.x, i.y + 1.0",
            "cell + ivec2(x-2, y-2)": "cell + ivec2(x-2.0, y-2.0)",
        }
        for original, invalid in rewrites.items():
            self.assertIn(original, source, f"donor shader changed around {original}")
            source = source.replace(original, invalid)

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            (base / "Main.hx").write_text('''class Main {
 static function main():Void {
  var normalized = CodenameShaderSource.normalizeOpenFL(''' + json.dumps(source, ensure_ascii=False) + ''');
  var expected = ["noise(x+1,y)", "noise(x-1,y)", "noise(x,y+1)", "noise(x,y-1)",
    "smoothNoise(i.x + 1, i.y)", "smoothNoise(i.x, i.y + 1)", "ivec2(x-2, y-2)"];
  for (fragment in expected) if (normalized.indexOf(fragment) < 0) throw "not normalized: " + fragment;
  for (fragment in ["noise(x+1.0,y)", "i.x + 1.0", "ivec2(x-2.0, y-2.0)"])
    if (normalized.indexOf(fragment) >= 0) throw "invalid integer arithmetic remains: " + fragment;
 }
}''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base), "--run", "Main"],
                cwd=ROOT, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        loader = (ROOT / "source/ShaderHandler.hx").read_text()
        self.assertGreaterEqual(loader.count("CodenameShaderSource.normalizeOpenFL(s)"), 2)


if __name__ == "__main__":
    unittest.main()
