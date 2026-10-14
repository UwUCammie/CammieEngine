"""Runtime shaders share source preparation and compile-error recovery."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

# No GL under the interpreter, so the shader base classes are stand-ins and the
# real RecoveringRuntimeShader, RuntimeShaderSource and normaliser run on top.
STUBS = {
    "flixel/addons/display/FlxRuntimeShader.hx": r'''package flixel.addons.display;
class FlxRuntimeShader {
 public static var failing:Array<String> = [];
 public static var compiles:Array<String> = [];
 public var requestedFragment:String;
 public var requestedVertex:String;
 public function new(?fragmentSource:String, ?vertexSource:String) {
  requestedFragment = fragmentSource; requestedVertex = vertexSource;
 }
 public var writes:Array<String> = [];
 public function setFloat(name:String, value:Float):Void writes.push(name + '=' + value);
 public function setFloatArray(name:String, value:Array<Float>):Void writes.push(name + '=' + value.join(','));
 public function setInt(name:String, value:Int):Void writes.push(name + '=int:' + value);
 public function setIntArray(name:String, value:Array<Int>):Void writes.push(name + '=int:' + value.join(','));
 public function setBool(name:String, value:Bool):Void writes.push(name + '=' + value);
 public function setBoolArray(name:String, value:Array<Bool>):Void writes.push(name + '=' + value.join(','));
 public function toString():String return 'FlxRuntimeShader';
 public function draw():lime.graphics.opengl.GLProgram
  return __createGLProgram(requestedVertex == null ? 'STOCK_VERTEX' : requestedVertex,
   requestedFragment == null ? 'STOCK_FRAGMENT' : requestedFragment);
 function __createGLProgram(vertex:String, fragment:String):lime.graphics.opengl.GLProgram {
  compiles.push(fragment);
  for (bad in failing) if (fragment.indexOf(bad) >= 0 || vertex.indexOf(bad) >= 0) throw 'driver rejected ' + bad;
  return new lime.graphics.opengl.GLProgram(vertex, fragment);
 }
}
''',
    "lime/graphics/opengl/GLProgram.hx": r'''package lime.graphics.opengl;
class GLProgram {
 public var vertex:String; public var fragment:String;
 public function new(vertex:String, fragment:String) { this.vertex = vertex; this.fragment = fragment; }
}
''',
    "flixel/addons/system/macros/FlxRuntimeShaderMacro.hx": r'''package flixel.addons.system.macros;
class FlxRuntimeShaderMacro {
 public static function retrieveMetadata(name:String):String return 'TEMPLATE_HEADER';
}
''',
    "ShaderRecoveryProbe.hx": r'''import flixel.addons.display.FlxRuntimeShader;
class ShaderRecoveryProbe {
 static function check(value:Bool, label:String):Void if (!value) throw label;
 static function main() {
  // Preparation: mixed int/float arithmetic is made legal, for either half.
  var mixed = "#pragma header\nvoid main(){ float x = 1.5; float y = x + 48; gl_FragColor = vec4(y); }";
  var pair = RuntimeShaderSource.prepareSources(mixed, null);
  check(pair[0].indexOf('x + 48.0') >= 0 && pair[1] == null, 'fragment-only pair');
  var vertexOnly = RuntimeShaderSource.prepareSources(null, mixed);
  check(vertexOnly[0] == null && vertexOnly[1].indexOf('x + 48.0') >= 0, 'a vertex-only pair must still be normalised');
  check(RuntimeShaderSource.prepare(null) == null, 'a missing half stays missing');
  check(RuntimeShaderSource.looksLikeSource(mixed) && RuntimeShaderSource.looksLikeSource('  #pragma header')
   && RuntimeShaderSource.looksLikeSource('uniform float a; void main() {}')
   && !RuntimeShaderSource.looksLikeSource('chromaticAberration') && !RuntimeShaderSource.looksLikeSource(null),
   'telling shader text from a shader name');

  // Recovery with the compile step passed in.
  var attempts:Array<String> = [];
  var errors:Array<String> = [];
  var compile = function(vertex:String, fragment:String):String {
   attempts.push(fragment);
   if (fragment == 'BROKEN') throw 'syntax error';
   return vertex + '+' + fragment;
  };
  var hook = function(error:Dynamic):Void errors.push(Std.string(error));
  check(RuntimeShaderSource.recover(RuntimeShaderSource.PASS_THROUGH, compile, 'V', 'GOOD', 'TEMPLATE', hook) == 'V+GOOD'
   && attempts.join(',') == 'GOOD' && errors.length == 0, 'a shader that compiles is left alone');
  attempts = [];
  check(RuntimeShaderSource.recover(RuntimeShaderSource.PASS_THROUGH, compile, 'V', 'BROKEN', 'TEMPLATE', hook) == 'V+TEMPLATE',
   'pass-through must retry with the template fragment and keep the vertex');
  check(attempts.join(',') == 'BROKEN,TEMPLATE' && errors.join('|') == 'syntax error', 'pass-through reports once, then retries');
  attempts = []; errors = [];
  check(RuntimeShaderSource.recover(RuntimeShaderSource.NULL_PROGRAM, compile, 'V', 'BROKEN', 'TEMPLATE', hook) == null,
   'null-program mode must not hand back a program');
  check(attempts.join(',') == 'BROKEN' && errors.join('|') == 'syntax error', 'null-program mode reports once and does not retry');
  attempts = []; errors = [];
  var alwaysBroken = function(vertex:String, fragment:String):String { attempts.push(fragment); throw 'bad vertex'; };
  check(RuntimeShaderSource.recover(RuntimeShaderSource.PASS_THROUGH, alwaysBroken, 'V', 'F', 'TEMPLATE', hook) == null
   && attempts.join(',') == 'F,TEMPLATE' && errors.length == 1, 'a failed retry ends quietly with no program and one report');
  var throwingHook = function(error:Dynamic):Void throw 'hook exploded';
  check(RuntimeShaderSource.recover(RuntimeShaderSource.NULL_PROGRAM, compile, 'V', 'BROKEN', 'TEMPLATE', throwingHook) == null,
   'a failing error hook must not escape');

  // The shared shader class: normalises both halves, recovers on first draw.
  var plain = new RecoveringRuntimeShader(mixed, mixed);
  check(plain.requestedFragment.indexOf('x + 48.0') >= 0 && plain.requestedVertex.indexOf('x + 48.0') >= 0,
   'constructor did not normalise both halves');
  var onlyVertex = new RecoveringRuntimeShader(null, mixed);
  check(onlyVertex.requestedFragment == null && onlyVertex.requestedVertex.indexOf('x + 48.0') >= 0,
   'vertex-only constructor did not normalise');
  check(plain.compileRecovery == RuntimeShaderSource.PASS_THROUGH, 'native default is pass-through');
  check(plain.writes.length == 0, 'a shader without initializers gets no default writes');

  // GLSL ES rejects initialized uniforms: the text loses them, the values come back as defaults.
  var initialized = "#pragma header\nuniform float amount = 0.5;\nuniform  highp  float neg=-0.1 ;\n"
   + "uniform int steps = 200;\nuniform vec3 tint = vec3(1.0, 0.5, 0.25);\nuniform vec2 splat = vec2(2.0);\n"
   + "uniform bool on = true;\nuniform float odd = sin(1.0);\nuniform float plain;\n"
   + "// uniform float commented = 3.0;\nvoid main(){ float local = 1.0; gl_FragColor = vec4(amount); }";
  var stripped = RuntimeShaderSource.stripUniformInitializers(initialized);
  check(stripped.indexOf('uniform float amount;') >= 0 && stripped.indexOf('uniform highp float neg;') >= 0
   && stripped.indexOf('uniform int steps;') >= 0 && stripped.indexOf('uniform vec3 tint;') >= 0
   && stripped.indexOf('uniform vec2 splat;') >= 0 && stripped.indexOf('uniform bool on;') >= 0
   && stripped.indexOf('uniform float odd;') >= 0 && stripped.indexOf('uniform float plain;') >= 0, 'initializers stripped: ' + stripped);
  check(stripped.indexOf('// uniform float commented = 3.0;') >= 0 && stripped.indexOf('float local = 1.0;') >= 0,
   'comments and non-uniform initializers are left alone');
  var defaults = [for (entry in RuntimeShaderSource.uniformDefaults(initialized)) entry.type + ' ' + entry.name + '=' + entry.values.join(',')];
  check(defaults.join('|') == 'float amount=0.5|float neg=-0.1|int steps=200|vec3 tint=1,0.5,0.25|vec2 splat=2,2|bool on=1',
   'defaults: ' + defaults.join('|'));
  check(RuntimeShaderSource.prepare(initialized).indexOf('= 0.5') == -1, 'prepare strips initializers');
  var withDefaults = new RecoveringRuntimeShader(initialized, null);
  check(withDefaults.requestedFragment.indexOf('uniform float amount;') >= 0, 'compiled text has no initializer');
  check(withDefaults.writes.join('|') == 'amount=0.5|neg=-0.1|steps=int:200|tint=1,0.5,0.25|splat=2,2|on=true',
   'defaults applied: ' + withDefaults.writes.join('|'));

  FlxRuntimeShader.failing = ['BROKEN_MARK'];
  var broken = "#pragma header\nvoid main(){ BROKEN_MARK; }";
  var seen:Array<String> = [];
  var passing = new RecoveringRuntimeShader(broken, null, RuntimeShaderSource.PASS_THROUGH, 'effects/wobble');
  passing.onCompileError = function(error:Dynamic):Void seen.push(Std.string(error));
  var program = passing.draw();
  check(program != null && program.fragment.indexOf('TEMPLATE_HEADER') == 0
   && program.fragment.indexOf('flixel_texture2D(bitmap, openfl_TextureCoordv)') > 0, 'pass-through program');
  check(program.vertex == 'STOCK_VERTEX' && seen.join('|') == 'driver rejected BROKEN_MARK', 'pass-through hook');

  seen = [];
  var silent = new RecoveringRuntimeShader(broken, null, RuntimeShaderSource.NULL_PROGRAM, 'effects/wobble');
  silent.onCompileError = function(error:Dynamic):Void seen.push(Std.string(error));
  check(silent.draw() == null && seen.length == 1, 'null-program shader');

  // Front ends are policies over that class.
  var nmv = new NightmareVisionRuntimeShader(broken, null, 'owned/shaders/wobble.frag', null);
  check(nmv.compileRecovery == RuntimeShaderSource.PASS_THROUGH && nmv.draw() != null, 'pass-through front end');
  check(Std.string(nmv) == 'FunkinRuntimeShader', 'front end identity');
  Sys.println('RECOVERY_OK');
 }
}
''',
}


class RuntimeShaderRecoveryTest(unittest.TestCase):
    def test_source_preparation_and_recovery_modes(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            for name, content in STUBS.items():
                path = Path(folder) / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"), "-main", "ShaderRecoveryProbe", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=120)
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("RECOVERY_OK", output)
        # The failure is logged with the shader's name and what happened to it.
        self.assertIn("[shader-compile-error] effects/wobble (drawing without it): driver rejected BROKEN_MARK", output)
        self.assertIn("[shader-compile-error] effects/wobble (not drawing): driver rejected BROKEN_MARK", output)
        self.assertIn("[shader-compile-error] fragment=owned/shaders/wobble.frag vertex=<default> (drawing without it)", output)

    def test_front_ends_are_policies_over_the_shared_shader(self):
        read = lambda name: (ROOT / "source" / name).read_text(encoding="utf-8")
        nmv = read("NightmareVisionRuntimeShader.hx")
        self.assertIn("extends RecoveringRuntimeShader", nmv)
        self.assertNotIn("__createGLProgram", nmv)
        self.assertNotIn("normalizeOpenFL", nmv)
        hscript = read("PsychHscriptSourceBindings.hx")
        block = hscript[hscript.index("class PsychHscriptErrorHandledRuntimeShader"):]
        block = block[:block.index("\n}") + 2]
        self.assertIn("extends RecoveringRuntimeShader", block)
        self.assertIn("RuntimeShaderSource.NULL_PROGRAM", block)
        self.assertIn("onCompileError = function(error:Dynamic):Void onError(error);", block)
        # No raw source goes straight to the stock runtime shader any more.
        self.assertNotIn("super(fragmentSource, vertexSource);", block)
        self.assertNotIn("__createGLProgram", block)
        handler = read("ShaderHandler.hx")
        self.assertIn("class CoolRuntimeShader extends RecoveringRuntimeShader", handler)
        self.assertNotIn("normalizeOpenFL", handler)
        lua = read("PsychSourceBindings.hx")
        self.assertIn("new RecoveringRuntimeShader(fragment, vertex, RuntimeShaderSource.NULL_PROGRAM, name)", lua)
        self.assertNotIn("new ShaderHandler.CoolRuntimeShader(sources[0]", lua)


if __name__ == "__main__":
    unittest.main()
