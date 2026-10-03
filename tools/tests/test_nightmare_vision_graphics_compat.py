"""Execute owner-scoped Nightmare Vision sprite and HSL shader helpers."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class NightmareVisionGraphicsCompatTest(unittest.TestCase):
    def test_bg_sprite_uses_owner_atlas_static_graphic_and_idle_animation(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe unavailable")
        files = {
            "NightmareVisionPaths.hx": r'''class NightmareVisionPaths {
 public var calls:Array<String> = [];
 public function new() {}
 public function getSparrowAtlas(path:String):Dynamic {
  calls.push('atlas:' + path); return 'atlas:' + path;
 }
 public function image(path:String):Dynamic {
  calls.push('image:' + path); return 'image:' + path;
 }
}
''',
            "NightmareVisionFlxSprite.hx": r'''class TestAnimation {
 public var calls:Array<String> = [];
 public function new() {}
 public function addByPrefix(name:String, prefix:String, fps:Int, loop:Bool):Void
  calls.push('add:' + name + ':' + prefix + ':' + fps + ':' + loop);
 public function play(name:String, forceplay:Bool = false):Void
  calls.push('play:' + name + ':' + forceplay);
}
class TestScrollFactor {
 public var x:Float = 1;
 public var y:Float = 1;
 public function new() {}
 public function set(x:Float, y:Float):Void { this.x = x; this.y = y; }
}
class NightmareVisionFlxSprite {
 public var ownerPaths:Null<NightmareVisionPaths>;
 public var animation:TestAnimation = new TestAnimation();
 public var scrollFactor:TestScrollFactor = new TestScrollFactor();
 public var active:Bool = true;
 public var frames:Dynamic;
 public var loaded:Dynamic;
 public var x:Float;
 public var y:Float;
 public function new(x:Float = 0, y:Float = 0, ?graphic:Dynamic,
  ?ownerPaths:NightmareVisionPaths) {
  this.x = x; this.y = y; this.ownerPaths = ownerPaths;
 }
 public function loadGraphic(graphic:Dynamic):Dynamic { loaded = graphic; return this; }
}
''',
            "flixel/system/FlxAssets.hx": '''package flixel.system;\ntypedef FlxShader = flixel.graphics.tile.FlxGraphicsShader;\n''',
            "flixel/graphics/tile/FlxGraphicsShader.hx": r'''package flixel.graphics.tile;
class ShaderUniform { public var value:Array<Float> = []; public function new() {} }
class FlxGraphicsShader {
 public var hue:ShaderUniform = new ShaderUniform();
 public var saturation:ShaderUniform = new ShaderUniform();
 public var lightness:ShaderUniform = new ShaderUniform();
 public function new() {}
}
''',
            "Main.hx": r'''class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main() {
  var owner = new NightmareVisionPaths();
  var atlas = new NightmareVisionBGSprite('backgrounds/city', 12, 34,
   0.25, 0.5, ['Tenma1', 'Tenma2'], true, owner);
  check(owner.calls.join(',') == 'atlas:backgrounds/city', 'atlas must use its selected owner');
  check(atlas.frames == 'atlas:backgrounds/city', 'atlas frames');
  check(atlas.active, 'animated background remains active');
  check(atlas.scrollFactor.x == 0.25 && atlas.scrollFactor.y == 0.5, 'parallax factors');
  check(atlas.animation.calls.join(',') ==
   'add:Tenma1:Tenma1:24:true,play:Tenma1:false,add:Tenma2:Tenma2:24:true',
   'first atlas animation is the initial idle');
  atlas.dance(true);
  check(atlas.animation.calls[3] == 'play:Tenma1:true', 'dance replays idle with force flag');

  var staticOwner = new NightmareVisionPaths();
  var staticSprite = new NightmareVisionBGSprite('backdrop', 2, 3, 1, 1, null, false, staticOwner);
  check(staticOwner.calls.join(',') == 'image:backdrop', 'static graphic must use its selected owner');
  check(staticSprite.loaded == 'image:backdrop' && !staticSprite.active, 'static sprite load/deactivation');
  check(staticSprite.animation.calls.length == 0, 'static sprite has no animation');
  staticSprite.dance();
  check(staticSprite.animation.calls.length == 0, 'static sprite dance is a no-op');

  var hsl = new NightmareVisionHSLColorSwap();
  check(hsl.hue == 0 && hsl.saturation == 0 && hsl.lightness == 0, 'zero HSL defaults');
  check(hsl.shader.hue.value[0] == 0 && hsl.shader.saturation.value[0] == 0
   && hsl.shader.lightness.value[0] == 0, 'shader uniform defaults');
  hsl.saturation = -0.2;
  hsl.hue = 1.575;
  hsl.lightness = 0.25;
  check(hsl.shader.saturation.value[0] == -0.2, 'saturation setter updates shader');
  check(hsl.shader.hue.value[0] == 1.575, 'hue setter updates shader');
  check(hsl.shader.lightness.value[0] == 0.25, 'lightness setter updates shader');
  hsl.saturation = 0;
  check(hsl.shader.saturation.value[0] == 0, 'tween-style updates reach the shader');
 }
}
''',
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            for name, source in files.items():
                target = work / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(source, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hsl_shader_keeps_source_color_math_and_alpha(self):
        source = (ROOT / "source/NightmareVisionHSLColorSwap.hx").read_text()
        self.assertIn("hsl.x = mod(hsl.x + hue, 1.0);", source)
        self.assertIn("hsl.y = clamp(hsl.y + saturation, 0.0, 1.0);", source)
        self.assertIn("hsl.z = clamp(hsl.z * (1.0 + lightness), 0.0, 1.0);", source)
        self.assertIn("vec4 color = vec4(hsl2rgb(hsl),oColor.a);", source)
        self.assertIn("class NightmareVisionHSLColorSwapShader extends FlxShader", source)


if __name__ == "__main__":
    unittest.main()
