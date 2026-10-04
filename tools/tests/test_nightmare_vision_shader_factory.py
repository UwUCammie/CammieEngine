"""Execute the NMV source-shaped runtime shader factory with isolated assets."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"


class NightmareVisionShaderFactoryTest(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(dir=ROOT / "tmp")
        self.addCleanup(self.scratch.cleanup)
        self.work = Path(self.scratch.name)
        self.owner = self.work / "assets/imported_mods/nmv-selected"
        self.core = self.owner / "__nmv_core"
        self.foreign = self.work / "assets/imported_mods/nmv-other"
        self.write("flixel/FlxG.hx", '''
package flixel;
class FlxG {
 public static var bitmap={add:function(value:Dynamic,unique:Bool,key:String):flixel.graphics.FlxGraphic return new flixel.graphics.FlxGraphic(key)};
 public static var random={int:function(min:Int,max:Int):Int return min};
}
''')
        self.write("flixel/graphics/FlxGraphic.hx", '''
package flixel.graphics;
class FlxGraphic { public var key:String; public function new(key:String) this.key=key; }
''')
        self.write("flixel/graphics/frames/FlxAtlasFrames.hx", '''
package flixel.graphics.frames;
class FlxAtlasFrames {
 public function new() {}
 public static function fromSparrow(image:flixel.graphics.FlxGraphic, text:String):FlxAtlasFrames return new FlxAtlasFrames();
 public static function fromAseprite(image:flixel.graphics.FlxGraphic, text:String):FlxAtlasFrames return new FlxAtlasFrames();
 public static function fromSpriteSheetPacker(image:flixel.graphics.FlxGraphic, text:String):FlxAtlasFrames return new FlxAtlasFrames();
}
''')
        self.write("animate/FlxAnimateFrames.hx", '''
package animate;
import flixel.graphics.frames.FlxAtlasFrames;
typedef SpritemapInput = {source:Dynamic, json:String}
class FlxAnimateFrames extends FlxAtlasFrames {
 public function new() super();
 public static function fromAnimate(input:String, spritemaps:Array<SpritemapInput>,
  ?metadata:String, ?key:String):FlxAnimateFrames return new FlxAnimateFrames();
}
''')
        self.write("openfl/media/Sound.hx", '''
package openfl.media;
class Sound { public function new() {} }
''')
        self.write("flixel/system/FlxAssets.hx", '''
package flixel.system;
class FlxAssets {
 public static function getSoundAddExtension(_path:String):openfl.media.Sound return new openfl.media.Sound();
}
''')
        self.write("FNFAssets.hx", '''
class FNFAssets {
 public static function getText(path:String):String return sys.io.File.getContent(path);
 public static function getBitmapData(path:String):Dynamic return path;
 public static function getFlxGraphic(path:String):flixel.graphics.FlxGraphic return new flixel.graphics.FlxGraphic(path);
 public static function getSound(path:String):openfl.media.Sound return new openfl.media.Sound();
}
''')
        self.write("flixel/addons/display/FlxRuntimeShader.hx", '''
package flixel.addons.display;
class FlxRuntimeShader {
 public final requestedFragment:String;
 public final requestedVertex:String;
 public final glFragmentSource:String;
 public final glVertexSource:String;
 public final writes:Array<Dynamic> = [];
 public function new(?fragmentSource:String, ?vertexSource:String) {
  requestedFragment = fragmentSource;
  requestedVertex = vertexSource;
  glFragmentSource = fragmentSource == null || fragmentSource.length == 0 ? 'DEFAULT_FRAGMENT' : fragmentSource;
  glVertexSource = vertexSource == null || vertexSource.length == 0 ? 'DEFAULT_VERTEX' : vertexSource;
 }
 public function setFloat(name:String, value:Float):Void writes.push([name, value]);
 public function compileForTest(vertex:String, fragment:String):lime.graphics.opengl.GLProgram
  return __createGLProgram(vertex, fragment);
 public function __createGLProgram(vertex:String, fragment:String):lime.graphics.opengl.GLProgram {
  if (fragment == 'BROKEN') throw 'shader compile failure';
  return new lime.graphics.opengl.GLProgram(vertex, fragment);
 }
 public function toString():String return 'FlxRuntimeShader';
}
''')
        self.write("lime/graphics/opengl/GLProgram.hx", '''
package lime.graphics.opengl;
class GLProgram {
 public final vertexSource:String;
 public final fragmentSource:String;
 public function new(vertexSource:String, fragmentSource:String) {
  this.vertexSource=vertexSource; this.fragmentSource=fragmentSource;
 }
}
''')
        self.write("flixel/addons/system/macros/FlxRuntimeShaderMacro.hx", '''
package flixel.addons.system.macros;
#if macro
import haxe.macro.Expr;
#end
class FlxRuntimeShaderMacro {
 public static macro function retrieveMetadata(metaName:String, overwrite:Bool=true):Expr return macro 'GL_FRAGMENT_HEADER';
}
''')
        self.write("NightmareVisionShaderFactoryTestMain.hx", '''
import flixel.addons.display.FlxRuntimeShader;
class NightmareVisionShaderFactoryTestMain {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var args = Sys.args();
  var owner = args[0];
  var shader = NightmareVisionShaderFactory.fromPath(owner, 'selected');
  check(shader.requestedFragment == '#version 130\\n#pragma header\\nuniform float darkness;\\n',
   'owner fragment source must pass through unchanged');
  check(shader.requestedVertex == null, 'fromPath must not infer a same-name vertex shader');
  check(shader.glVertexSource == 'DEFAULT_VERTEX', 'null vertex retains FlxRuntimeShader default');
  shader.setFloat('darkness', 0.5);
  check(shader.writes.length == 1 && shader.writes[0][0] == 'darkness' && shader.writes[0][1] == 0.5,
   'returned runtime shader keeps its uniform API');

  var core = NightmareVisionShaderFactory.fromPath(owner, 'core-only');
  check(core.requestedFragment == 'CORE_FRAGMENT\\n', 'selected installation core provides explicit fallback');

  var vertexOnly = NightmareVisionShaderFactory.fromPath(owner, null, 'vertex-only');
  check(vertexOnly.requestedFragment == null && vertexOnly.requestedVertex == 'OWNER_VERTEX\\n',
   'optional fragment and vertex keys are independent');

  var defaults = NightmareVisionShaderFactory.fromPath(owner);
  check(defaults.requestedFragment == null && defaults.requestedVertex == null,
   'no-argument source API retains FlxRuntimeShader defaults');

  var empty = NightmareVisionShaderFactory.fromPath(owner, 'empty');
  check(empty.requestedFragment == '', 'an authored empty shader is forwarded like FunkinRuntimeShader.fromPath');

  var rawSnowfall = FNFAssets.getText(owner + '/shaders/snowfall.frag');
  check(rawSnowfall.indexOf('x + 48, 38 / (x + 2.5)') >= 0
   && rawSnowfall.indexOf('x + 48.0') < 0,
   'factory normalization must not rewrite the owner asset on disk');
  var snowfall = NightmareVisionShaderFactory.fromPath(owner, 'snowfall', 'snowfall');
  check(snowfall.requestedFragment.indexOf('x + 48.0') >= 0
   && snowfall.requestedFragment.indexOf('38.0 / (x + 2.5)') >= 0
   && snowfall.requestedFragment.indexOf('(43758.0)') >= 0
   && snowfall.requestedFragment.indexOf('vec2(13, 78)') >= 0
   && snowfall.requestedFragment.indexOf('for (int i = 0; i < amount; i++)') >= 0,
   'fragment constructor input gets shared scalar normalization while integer syntax stays intact');
  check(snowfall.requestedVertex.indexOf('x + 48.0') >= 0
   && snowfall.requestedVertex.indexOf('38.0 / (x + 2.5)') >= 0,
   'vertex constructor input gets the same shared scalar normalization');

  var broken = NightmareVisionShaderFactory.fromPath(owner, 'broken', 'selected');
  var recovered = broken.compileForTest('AUTHORED_VERTEX', 'BROKEN');
  check(recovered.vertexSource == 'AUTHORED_VERTEX', 'compile recovery retains authored vertex source');
  check(recovered.fragmentSource.indexOf('GL_FRAGMENT_HEADER') == 0
   && recovered.fragmentSource.indexOf('flixel_texture2D(bitmap, openfl_TextureCoordv)') >= 0,
   'compile failure uses FunkinRuntimeShader template fragment');
  check(Std.string(broken) == 'FunkinRuntimeShader', 'source shader string identity');

  var missingFragment = false;
  try NightmareVisionShaderFactory.fromPath(owner, 'foreign-only') catch (error:Dynamic) {
   missingFragment = Std.string(error).indexOf('Missing fragment shader "foreign-only"') >= 0;
  }
  check(missingFragment, 'named missing fragment must fail instead of using another owner/default');
  var missingVertex = false;
  try NightmareVisionShaderFactory.fromPath(owner, null, 'foreign-only') catch (error:Dynamic) {
   missingVertex = Std.string(error).indexOf('Missing vertex shader "foreign-only"') >= 0;
  }
  check(missingVertex, 'named missing vertex must fail instead of using another owner/default');
  Sys.println('nightmare-vision-shader-factory-ok');
 }
}
''')

    def write(self, relative, content):
        path = self.work / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, newline='\n')
        return path

    def shader(self, root, relative, content):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, newline='\n')
        return path

    def test_source_factory_preserves_shader_source_and_owner_scope(self):
        self.shader(self.owner, "shaders/selected.frag", "#version 130\n#pragma header\nuniform float darkness;\n")
        self.shader(self.owner, "shaders/selected.vert", "SAME_NAME_VERTEX_MUST_NOT_BE_AUTOLOADED\n")
        self.shader(self.core, "shaders/selected.frag", "CORE_SHADOWED_BY_OWNER\n")
        self.shader(self.core, "shaders/core-only.frag", "CORE_FRAGMENT\n")
        self.shader(self.owner, "shaders/vertex-only.vert", "OWNER_VERTEX\n")
        self.shader(self.owner, "shaders/empty.frag", "")
        snowfall_source = (
            "uniform float x;\nuniform int amount;\n"
            "float rnd() { return fract(sin(dot(vec2(x + 48, 38 / (x + 2.5)), vec2(13, 78))) * (43758)); }\n"
            "void main() { for (int i = 0; i < amount; i++) { float unused = float(i); } }\n"
        )
        self.shader(self.owner, "shaders/snowfall.frag", snowfall_source)
        self.shader(self.owner, "shaders/snowfall.vert",
                    "uniform float x;\nvoid main() { gl_Position = vec4(x + 48, 38 / (x + 2.5), 0.0, 1.0); }\n")
        self.shader(self.foreign, "shaders/foreign-only.frag", "FOREIGN_FRAGMENT\n")
        self.shader(self.foreign, "shaders/foreign-only.vert", "FOREIGN_VERTEX\n")

        self.shader(self.owner, "shaders/broken.frag", "BROKEN")
        result = subprocess.run(
            [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(self.work),
             "--run", "NightmareVisionShaderFactoryTestMain", "assets/imported_mods/nmv-selected"],
            cwd=self.work, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("nightmare-vision-shader-factory-ok", result.stdout)
        self.assertIn("[nightmare-vision-shader-compile] fragment=",
                      result.stdout + result.stderr)
        self.assertIn(": shader compile failure", result.stdout + result.stderr)
        self.assertIn("assets/imported_mods/nmv-selected/shaders/broken.frag",
                      result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
