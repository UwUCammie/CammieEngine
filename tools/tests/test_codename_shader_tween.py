"""Codename shader tweens update real uniforms while preserving callbacks."""

from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def method(source: str, signature: str) -> str:
    start = source.index(signature)
    depth = 0
    for index in range(source.index("{", start), len(source)):
        depth += (source[index] == "{") - (source[index] == "}")
        if depth == 0:
            return source[start:index + 1]
    raise AssertionError(f"unterminated method: {signature}")


class CodenameShaderTweenTest(unittest.TestCase):
    def test_numeric_uniform_tween_and_callback(self):
        source = (ROOT / "source/CodenameScriptInterp.hx").read_text()
        tween = method(source, "\tfunction tweenShaderUniforms(")
        fixture = '''class FlxRuntimeShader {
 public var data:Dynamic;
 public function new() { data={saturation:{value:[-30]}, hue:{value:[0.5]}}; }
}
class FlxTween {
 public static function tween(mirror:Dynamic, properties:Dynamic, duration:Float, options:Dynamic):FlxTween {
  for (name in Reflect.fields(properties)) Reflect.setField(mirror,name,Reflect.field(properties,name));
  Reflect.callMethod(null,Reflect.field(options,'onUpdate'),[new FlxTween()]);
  Reflect.callMethod(null,Reflect.field(options,'onComplete'),[new FlxTween()]);
  return new FlxTween();
 }
 public function new() {}
}
class Main {
 public function new() {}
 var numericShaderValues:Map<FlxRuntimeShader, Map<String, Float>> = [];
 static function shaderUniformName(shader:Dynamic,name:String):String return name;
 static function shaderParameter(shader:Dynamic,name:String):Dynamic return Reflect.field(shader.data,name);
 static function setShaderParameter(shader:FlxRuntimeShader,name:String,value:Dynamic):Bool {
  Reflect.field(shader.data,name).value=[value]; return true;
 }
''' + tween + '''
 static function main() {
  var shader=new FlxRuntimeShader();
  var updates=0; var completions=0;
  var options:Dynamic={onUpdate:function(_) updates++, onComplete:function(_) completions++};
  var main=new Main();
  main.tweenShaderUniforms(shader,{saturation:0.0,hue:1.0},1,options);
  if (shader.data.saturation.value[0]!=0 || shader.data.hue.value[0]!=1
    || updates!=1 || completions!=1) throw 'uniform tween/callback lost';
  if (Reflect.field(options,'onUpdate')==null) throw 'caller options mutated';
  shader.data.saturation.value=null;
  var remembered:Map<String, Float> = [];
  remembered.set('saturation', -30.0);
  main.numericShaderValues.set(shader, remembered);
  main.tweenShaderUniforms(shader,{saturation:0.0},1,null);
  if (shader.data.saturation.value[0]!=0) throw 'remembered uniform tween';
  var rejected=false;
  try new Main().tweenShaderUniforms(shader,{missing:2.0},1,null)
  catch (error:Dynamic) rejected=Std.string(error).indexOf('Unknown tween uniform')>=0;
  if (!rejected) throw 'missing uniform accepted';
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            (Path(directory) / "Main.hx").write_text(fixture)
            result = subprocess.run([
                str(ROOT / ".tools/haxe/haxe"), "-cp", directory, "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Std.isOfType(object, FlxRuntimeShader)", source)


if __name__ == "__main__":
    unittest.main()
