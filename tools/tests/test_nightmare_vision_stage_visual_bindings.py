"""Exercise donor stage visual classes through the actual NV script interpreter."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import FixturePath as Path, HAXE_COMMAND
from tools.haxe_flixel_math_stubs import write_flixel_point_stub


ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionStageVisualBindingsTest(unittest.TestCase):
    def test_backdrop_preset_and_legacy_rgb_palette_import(self):
        with tempfile.TemporaryDirectory(prefix="nv-stage-visual-", dir=ROOT / "tmp") as scratch:
            work = Path(scratch)
            write_flixel_point_stub(work)
            files = {
                "PsychRGBShader.hx": r'''package;
class Uniform { public var value:Array<Float>=[]; public function new(){} }
class PsychRGBShader {
 public var r=new Uniform();public var g=new Uniform();public var b=new Uniform();
 public var mult=new Uniform();public var u_alpha=new Uniform();public var u_flash=new Uniform();
 public function new(){}
}''',
                "flixel/util/FlxColor.hx": r'''package flixel.util;
abstract FlxColor(Int) from Int to Int {
 public var redFloat(get,never):Float;
 public var greenFloat(get,never):Float;
 public var blueFloat(get,never):Float;
 inline function get_redFloat():Float return ((this>>16)&255)/255;
 inline function get_greenFloat():Float return ((this>>8)&255)/255;
 inline function get_blueFloat():Float return (this&255)/255;
}''',
                "flixel/addons/display/FlxBackdrop.hx": r'''package flixel.addons.display;
class FlxBackdrop {
 public var graphic:Dynamic;
 public var axes:Dynamic;
 public var spacing:Float;
 public function new(?graphic:Dynamic,?axes:Dynamic,spacing:Float=0){
  this.graphic=graphic;this.axes=axes;this.spacing=spacing;
 }
}''',
                "HxcCompatRuntime.hx": r'''package;
class HxcCompatRuntime {
 public static function getZIndex(_target:Dynamic):Dynamic return 0;
 public static function setZIndex(_target:Dynamic,value:Dynamic,?op:String="="):Dynamic return value;
}''',
                "Main.hx": r'''package;
class Main {
 static function check(value:Bool,message:String):Void if(!value)throw message;
 static function main():Void {
  var interp=new NightmareVisionScriptInterp();
  interp.variables.set("Type",Type);
  NightmareVisionStageVisualBindings.install(interp);
  var parser=new NightmareVisionScriptParser();
  interp.execute(parser.parseString('
   import funkin.game.shaders.RGBPalette;
   palette = new RGBPalette();
   palette.g = 0xFF102030;
   palette.b = 0xFF405060;
   palette.mult = 0.75;
   backdropDefault = new FlxBackdrop();
   backdropConfigured = new FlxBackdrop("fog", 1, 12);
   sprite = {shader:null};
   sprite.shader = palette.shader;
   importedType = Type.resolveClass("funkin.game.shaders.RGBPalette");
   reflectedBackdrop = Type.resolveClass("flixel.addons.display.FlxBackdrop");
  '));
  var palette:PsychRGBPalette=cast interp.variables.get("palette");
  var backdrop:flixel.addons.display.FlxBackdrop=cast interp.variables.get("backdropConfigured");
  check(Std.isOfType(palette,PsychRGBPalette),"legacy RGBPalette import resolves to the shared channel palette");
  check(palette.g==0xFF102030&&palette.b==0xFF405060&&palette.mult==0.75,
   "imported palette retains RGB channel setters and bounded blend amount");
  check(palette.shader.g.value.length==3&&palette.shader.g.value[0]==16/255
   &&palette.shader.g.value[1]==32/255&&palette.shader.g.value[2]==48/255,
   "palette setters update the shader uniforms used by stage sprites");
  check(Reflect.field(interp.variables.get("sprite"),"shader")==palette.shader,
   "stage sprite accepts the imported palette shader directly");
  check(backdrop.graphic=="fog"&&backdrop.axes==1&&backdrop.spacing==12,
   "bare FlxBackdrop constructor receives donor arguments");
  check(Std.isOfType(interp.variables.get("backdropDefault"),flixel.addons.display.FlxBackdrop),
   "donor preset exposes FlxBackdrop without an explicit import");
  check(interp.variables.get("importedType")==PsychRGBPalette
   &&interp.variables.get("reflectedBackdrop")==flixel.addons.display.FlxBackdrop,
   "qualified class reflection keeps the same real runtime class tokens");
  check(interp.getOrImportClass("funkin.game.shaders.RGBPalette")==PsychRGBPalette,
   "Iris import lookup resolves the legacy class path");
  interp.release();
 }
}''',
            }
            for name, content in files.items():
                path = work / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript-iris/1,1,3"),
                 "-cp", scratch, "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_shared_seed_installs_bindings_for_stage_and_other_nightmare_vision_scripts(self):
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        start = play_state.index("public static function seedNightmareVisionCommon(")
        end = play_state.index("\n\tpublic static function ", start + 1)
        common_seed = play_state[start:end]
        self.assertIn("NightmareVisionStageVisualBindings.install(interp);", common_seed)
        self.assertLess(common_seed.index("NightmareVisionStageVisualBindings.install"),
                        common_seed.index("NightmareVisionScriptBindings.install"))


if __name__ == "__main__":
    unittest.main()
