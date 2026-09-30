"""Focused coverage for shared HXC module pixel and mutable-state adapters."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"
MOUNTED_MODULE = (
    Path("/run/media/cammie/External Storage/FNF-Example-Mods")
    / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/IconColoredHealthBar.hxc"
)

SYNTHETIC_MODULE = r'''
import funkin.modding.module.Module;
import funkin.util.Constants;
import haxe.ds.StringMap;
class PixelColors extends Module {
    static var defaultGreen = Constants.COLOR_HEALTH_BAR_GREEN;
    static var defaultRed = Constants.COLOR_HEALTH_BAR_RED;
    static var bfColor;
    static var dadColor;
    var iconColorCache = new StringMap();
    var inPlay = false;
    function new() { super("pixel-colors"); }
    function dominantColor(sprite, ?scale:Float = 1.0) {
        if (sprite == null || !inPlay) return 0;
        return sprite.pixels.getPixel32(0.8 * scale, 0.2 * scale);
    }
    function getIconColor(sprite) {
        var cached = iconColorCache.get(sprite.characterId);
        if (cached != null) return cached;
        var color = dominantColor(sprite);
        iconColorCache.set(sprite.characterId, color);
        return color;
    }
    function fillHealthBar() {
        Constants.COLOR_HEALTH_BAR_GREEN = bfColor;
        Constants.COLOR_HEALTH_BAR_RED = dadColor;
    }
}
'''


def hx_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


@unittest.skipUnless(HAXE.is_file() and HSCRIPT.is_dir(), "portable Haxe/HScript toolchain unavailable")
class HxcModulePixelStateRuntimeTest(unittest.TestCase):
    def run_fixture(self, source: str) -> subprocess.CompletedProcess:
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="hxc-module-pixels-", dir=ROOT / "tmp") as folder:
            main = Path(folder) / "Main.hx"
            main.write_text(source)
            return subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(HSCRIPT),
                 "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )

    def test_module_initializers_pixel_reads_and_mutable_cache_run_through_shared_adapters(self):
        module_source = MOUNTED_MODULE.read_text() if MOUNTED_MODULE.is_file() else SYNTHETIC_MODULE
        main = f'''import haxe.ds.StringMap;
import hscript.Interp;
import hscript.Parser;
class Main {{
  static function fail(message:String):Void throw message;
  static function main() {{
    HxcCompatRuntime.clear();
    var result = HxcCompat.analyze({hx_string(module_source)}, "scripts/modules/IconColoredHealthBar.hxc");
    if (!result.moduleSafe || !result.moduleInitializationSafe)
      fail("module should have safe mutable defaults: " + result.moduleSafetyReasons.join(",")
        + "\\n" + result.generatedHscript);
    for (finding in result.diagnostics)
      if (finding.code == "unsupported-hxc-module-body")
        fail("module body was not adapted: " + finding.message);
    var generated = result.generatedHscript;
    if (generated.indexOf("HxcCompatRuntime.spritePixelColor32(sprite,") < 0
      || generated.indexOf("sprite.pixels.getPixel32(") >= 0)
      fail("pixel read did not use the bounded runtime adapter: " + generated);
    if (generated.indexOf("new StringMap()") < 0
      || generated.indexOf("constantsForRoot(hxcAssetRoot).COLOR_HEALTH_BAR_GREEN") < 0)
      fail("mutable map or root-scoped constants initializer missing: " + generated);

    var parser = new Parser();
    parser.parseString(generated);
    var interp = new Interp();
    var owner = "assets/imported_mods/pixel-adapter-owner";
    interp.variables.set("HxcCompatRuntime", HxcCompatRuntime);
    interp.variables.set("hxcAssetRoot", owner);
    interp.variables.set("StringMap", StringMap);
    interp.variables.set("Math", Math);
    interp.variables.set("Std", Std);
    var executable = generated
      + "\\nfunction __testSetInPlay(value) {{ inPlay = value; }}"
      + "\\nfunction __testSetColors(green, red) {{ bfColor = green; dadColor = red; }}";
    interp.execute(parser.parseString(executable));
    var setInPlay:Dynamic = interp.variables.get("__testSetInPlay");
    Reflect.callMethod(null, setInPlay, [true]);

    var red = 0xFF112233;
    var green = 0xFF445566;
    var colors = [red, green, 0, red];
    var coordinates:Array<Array<Int>> = [];
    var pixels:Dynamic = {{
      width: 2,
      height: 2,
      getPixel32: function(x:Int, y:Int):Int {{
        coordinates.push([x, y]);
        return colors[y * 2 + x];
      }}
    }};
    var icon:Dynamic = {{characterId: "bf", frameWidth: 2, frameHeight: 2, pixels: pixels}};
    var dominant:Dynamic = interp.variables.get("dominantColor");
    var dominantColor = Reflect.callMethod(null, dominant, [icon, 1.0]);
    if (dominantColor != red)
      fail("pixel sampling did not return the dominant opaque color: "
        + Std.string(dominantColor) + " reads=" + coordinates.length);
    if (coordinates.length != 4 || coordinates[0][0] != 0 || coordinates[0][1] != 0)
      fail("pixel coordinates were not converted to integer bitmap coordinates");

    var getIconColor:Dynamic = interp.variables.get("getIconColor");
    if (Reflect.callMethod(null, getIconColor, [icon, 1.0, false]) != red)
      fail("StringMap cache missed the first dominant-color result");
    var readsAfterFill = coordinates.length;
    if (Reflect.callMethod(null, getIconColor, [icon, 1.0, false]) != red
      || coordinates.length != readsAfterFill)
      fail("mutable StringMap cache did not preserve the color result");

    var setColors:Dynamic = interp.variables.get("__testSetColors");
    Reflect.callMethod(null, setColors, [0xFF010203, 0xFF040506]);
    Reflect.callMethod(null, setInPlay, [false]);
    var fill:Dynamic = interp.variables.get("fillHealthBar");
    Reflect.callMethod(null, fill, []);
    var ownedConstants = HxcCompatRuntime.constantsForRoot(owner);
    var otherConstants = HxcCompatRuntime.constantsForRoot("assets/imported_mods/other-owner");
    if (Reflect.field(ownedConstants, "COLOR_HEALTH_BAR_GREEN") != 0xFF010203
      || Reflect.field(ownedConstants, "COLOR_HEALTH_BAR_RED") != 0xFF040506
      || Reflect.field(otherConstants, "COLOR_HEALTH_BAR_GREEN") != 0xFF66FF33)
      fail("mutable color constants were not isolated by imported root");
    if (Reflect.field(ownedConstants, "STRUMLINE_X_OFFSET") != 48.0
      || Reflect.field(ownedConstants, "STRUMLINE_Y_OFFSET") != 24.0
      || Reflect.field(ownedConstants, "PIXELS_PER_MS") != 0.45
      || Reflect.field(otherConstants, "STRUMLINE_X_OFFSET") != 48.0)
      fail("source-backed V-Slice strumline constants were missing");
    if (HxcCompatRuntime.spritePixelColor32(icon, 2.2, 0) != 0
      || HxcCompatRuntime.spritePixelColor32(null, 0, 0) != 0)
      fail("pixel adapter did not bound absent or out-of-range reads");
    HxcCompatRuntime.clear();
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
