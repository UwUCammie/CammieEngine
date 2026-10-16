"""The title screen logo: CAMMIE ENGINE's art, its shine mask and the shine shader."""
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]
LOGO_PNG = ROOT / "assets" / "images" / "logoBumpin.png"
MASK_PNG = ROOT / "assets" / "images" / "logoBumpinShine.png"
LOGO_XML = ROOT / "assets" / "images" / "logoBumpin.xml"
SOURCE_PNG = ROOT / "art" / "logoBumpin-source.png"
GENERATOR = ROOT / "tools" / "generate_title_logo.py"
SHADER = ROOT / "source" / "TitleShineShader.hx"
SHINE = ROOT / "source" / "TitleLogoShine.hx"
TITLE_STATE = ROOT / "source" / "TitleState.hx"

# The untouched original art. The generator reads it and nothing may rewrite it.
SOURCE_SHA256 = "578e8e0f8b102ad8899663e7c207c590dc5697a02637f2f31788faf05194dcb9"

# The four distinct frames of the sheet. The generator must never move them.
EXPECTED_FRAME_RECTS = {
    (0, 0, 922, 670),
    (922, 0, 969, 703),
    (0, 703, 940, 683),
    (940, 703, 933, 679),
}

# Runs inside a Python that has Pillow and numpy (the bundled one does not).
PIXEL_CHECKS = r"""
import json, sys
import numpy as np
from PIL import Image
sys.path.insert(0, sys.argv[1])
import generate_title_logo as G

source, logo, mask = G.generate(sys.argv[2])
committed_logo = np.array(Image.open(sys.argv[3]).convert("RGBA"))
committed_mask = np.array(Image.open(sys.argv[4]).convert("RGBA"))
report = {
    "logo_matches_committed": bool(np.array_equal(logo, committed_logo)),
    "mask_matches_committed": bool(np.array_equal(mask, committed_mask)),
    "size": list(logo.shape[:2]),
    "frames": [],
}
in_frames = np.zeros(source.shape[:2], dtype=bool)
for (x, y, w, h) in G.FRAMES:
    in_frames[y:y + h, x:x + w] = True
    fs, fl, fm = source[y:y + h, x:x + w], logo[y:y + h, x:x + w], mask[y:y + h, x:x + w]
    box = G.locate_cammie(fs)
    x0, y0, x1, y1 = box
    inside, counters = G.cammie_regions(fs, box)
    hole = np.zeros(fs.shape[:2], dtype=bool)
    for c in counters:
        hole |= c
    near_hole = G.distance_to(hole, limit=14) <= 12
    inbox = np.zeros(fs.shape[:2], dtype=bool)
    inbox[y0:y1 + 1, x0:x1 + 1] = True
    (tx0, ty0, tx1, ty1), tube = G.text_line(fl, box)
    changed = (fs != fl).any(axis=-1)
    strict_tube = (fs[..., 0] > 235) & (fs[..., 1] > 95) & (fs[..., 1] < 142) & (fs[..., 2] > 200)
    # CAMMIE's profile against ENGINE's: median red by distance from the tube's inner edge
    depth = G.distance_to(np.pad(~inside, 1, constant_values=True))[1:-1, 1:-1] - 0.5
    centres, engine_colours, _tube = G.engine_profile(fs, box)
    sample = inside & ~near_hole
    cammie_red, engine_red = [], []
    for k in range(6):
        picked = sample & (depth >= centres[k] - 0.5) & (depth < centres[k] + 0.5)
        cammie_red.append(float(np.median(fl[..., 0][picked])))
        engine_red.append(float(engine_colours[k, 0]))
    glow = fl[inside & ~near_hole][:, :3].astype(int)
    rgb = fl[..., :3].astype(int)
    red, green, blue = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    white = (rgb.min(axis=-1) >= 250)
    splash = (blue > 200) & (red < 90) & (green < 90)
    black = (rgb.max(axis=-1) <= 2)
    amount, position = fm[..., 0], fm[..., 1]
    xs = np.nonzero(tube)[1]
    row_band = np.zeros(fs.shape[:2], dtype=bool)
    row_band[max(ty0 - G.GLOW_REACH, 0):ty1 + G.GLOW_REACH + 1] = True
    left = tube & (np.arange(fs.shape[1])[None, :] < tx0 + 0.1 * (tx1 - tx0))
    right = tube & (np.arange(fs.shape[1])[None, :] > tx1 - 0.1 * (tx1 - tx0))
    counter_pixels = fl[hole][:, :3].astype(int)
    report["frames"].append({
        "rebuilt_pixels": int(inside.sum()),
        "changed": int(changed.sum()),
        "changed_outside_rebuilt": int((changed & ~inside).sum()),
        "changed_outside_box": int((changed & ~inbox).sum()),
        "changed_tube": int((changed & strict_tube).sum()),
        "tube_pixels": int(strict_tube.sum()),
        "alpha_changed": int((fs[..., 3] != fl[..., 3]).sum()),
        "stripes_before": G.stripe_pixels(fs[y0:y1 + 1, x0:x1 + 1]),
        "stripes_after": G.stripe_pixels(fl[y0:y1 + 1, x0:x1 + 1]),
        "black_outline_left": int(((fl[..., :3].max(axis=-1) < G.DARK_LIMIT) & (fs[..., :3].max(axis=-1) < G.DARK_LIMIT)
                                   & inside & (depth < 2.0) & ~near_hole).sum()),
        "glow_brightest": int(glow.max()),
        "glow_deep_pixels": int((depth[inside & ~near_hole] > 5.5).sum()),
        "glow_deep_red": int(fl[..., 0][inside & ~near_hole & (depth > 5.5)].max()),
        "cammie_red_by_depth": cammie_red,
        "engine_red_by_depth": engine_red,
        "counters": len(counters),
        "counter_pixels": int(hole.sum()),
        "counter_tube_pixels": int((counter_pixels[:, 0] > 200).sum()),
        "counter_dark_pixels": int((counter_pixels.max(axis=-1) < 130).sum()),
        "mask_alpha_min": int(fm[..., 3].min()),
        "mask_blue_max": int(fm[..., 2].max()),
        "mask_outside_text_rows": int(amount[~row_band].max()),
        "mask_tube_median": float(np.median(amount[tube])),
        "mask_tube_p5": float(np.percentile(amount[tube], 5)),
        "mask_on_white": int(amount[white].max()),
        "mask_on_splash": int(amount[splash].max()),
        "mask_on_black": int(amount[black].max()),
        "mask_glow_mean": float(amount[inside & ~near_hole & (depth >= 1.5)].mean()),
        "position_tube_min": int(position[tube].min()),
        "position_tube_max": int(position[tube].max()),
        "position_left_mean": float(position[left].mean()),
        "position_right_mean": float(position[right].mean()),
        "position_correlation": float(np.corrcoef(xs, position[tube])[0, 1]),
    })
report["mask_outside_frames"] = int(mask[~in_frames][..., :3].max())
report["logo_outside_frames_changed"] = int((source[~in_frames] != logo[~in_frames]).any(axis=-1).sum())
print(json.dumps(report))
"""


def pillow_python():
    """A Python with Pillow and numpy, or None."""
    candidates = []
    explicit = os.environ.get("CAMMIE_PILLOW_PYTHON")
    if explicit:
        candidates.append([explicit])
    candidates.append([sys.executable])
    for name in ("python", "python3"):
        found = shutil.which(name)
        if found:
            candidates.append([found])
    if shutil.which("py"):
        candidates.extend([["py", "-3.12"], ["py", "-3"]])
    seen = set()
    for command in candidates:
        key = tuple(command)
        if key in seen:
            continue
        seen.add(key)
        try:
            probe = subprocess.run(command + ["-c", "import PIL, numpy"], capture_output=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0:
            return command
    return None


def png_header(path):
    with open(path, "rb") as handle:
        data = handle.read(33)
    assert data[:8] == b"\x89PNG\r\n\x1a\n", path
    width, height, depth, colour_type = struct.unpack(">IIBB", data[16:26])
    return width, height, depth, colour_type


class TitleLogoArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        command = pillow_python()
        cls.report = None
        if command is None:
            return
        result = subprocess.run(
            command + ["-c", PIXEL_CHECKS, str(ROOT / "tools"), str(SOURCE_PNG), str(LOGO_PNG), str(MASK_PNG)],
            capture_output=True, text=True, timeout=900)
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        cls.report = json.loads(result.stdout.strip().splitlines()[-1])

    def need_report(self):
        if self.report is None:
            self.skipTest("no Python with Pillow and numpy found (set CAMMIE_PILLOW_PYTHON)")
        return self.report

    def test_frame_rectangles_in_the_xml_are_unchanged(self):
        text = LOGO_XML.read_text(encoding="utf-8-sig")
        rects = {tuple(int(v) for v in m) for m in re.findall(
            r'<SubTexture name="logo bumpin\d+" x="(\d+)" y="(\d+)" width="(\d+)" height="(\d+)"', text)}
        self.assertEqual(rects, EXPECTED_FRAME_RECTS)
        self.assertEqual(text.count("<SubTexture"), 15)

    def test_sheets_keep_their_size_and_format(self):
        for path in (LOGO_PNG, MASK_PNG, SOURCE_PNG):
            self.assertEqual(png_header(path), (2048, 2048, 8, 6), path)

    def test_source_art_is_untouched(self):
        self.assertEqual(hashlib.sha256(SOURCE_PNG.read_bytes()).hexdigest(), SOURCE_SHA256)

    def test_generator_script_exists_next_to_the_source_art(self):
        self.assertTrue(GENERATOR.is_file())
        self.assertTrue(SOURCE_PNG.is_file())

    def test_committed_pngs_are_what_the_generator_makes(self):
        report = self.need_report()
        self.assertEqual(report["size"], [2048, 2048])
        self.assertTrue(report["logo_matches_committed"],
                        "assets/images/logoBumpin.png is stale: rerun tools/generate_title_logo.py")
        self.assertTrue(report["mask_matches_committed"],
                        "assets/images/logoBumpinShine.png is stale: rerun tools/generate_title_logo.py")

    def test_only_cammie_inside_the_tube_changes(self):
        report = self.need_report()
        self.assertEqual(report["logo_outside_frames_changed"], 0)
        for frame in report["frames"]:
            self.assertGreater(frame["rebuilt_pixels"], 9000)
            # every changed pixel is a pixel of the fill, the outline around it
            # or the antialiasing next to the tube: nothing outside, no tube pixel
            self.assertEqual(frame["changed_outside_rebuilt"], 0)
            self.assertEqual(frame["changed_outside_box"], 0)
            self.assertGreater(frame["tube_pixels"], 5000)
            self.assertEqual(frame["changed_tube"], 0)
            self.assertEqual(frame["alpha_changed"], 0)
            self.assertGreater(frame["changed"], 9000)

    def test_no_stripe_colours_remain_in_cammie(self):
        for frame in self.need_report()["frames"]:
            self.assertGreater(frame["stripes_before"], 2500)
            self.assertEqual(frame["stripes_after"], 0)

    def test_cammie_has_one_tube_and_no_black_outline_gap(self):
        for frame in self.need_report()["frames"]:
            # the black outline between the tube and the fill is gone
            self.assertEqual(frame["black_outline_left"], 0)

    def test_cammie_inner_glow_matches_engines(self):
        for frame in self.need_report()["frames"]:
            cammie, engine = frame["cammie_red_by_depth"], frame["engine_red_by_depth"]
            # same brightness at every distance from the tube's inner edge
            for depth, (c, e) in enumerate(zip(cammie, engine)):
                self.assertAlmostEqual(c, e, delta=max(12.0, 0.12 * e), msg="depth %d: cammie %r engine %r" % (depth, cammie, engine))
            # a visible magenta glow at the tube, black a few pixels in
            self.assertGreater(cammie[0], 100)
            self.assertGreater(cammie[1], 40)
            self.assertLess(cammie[5], 8)
            self.assertLess(frame["glow_brightest"], 255)
            self.assertGreater(frame["glow_deep_pixels"], 500)
            self.assertLessEqual(frame["glow_deep_red"], 6)

    def test_the_counter_of_the_a_is_drawn_as_a_neon_contour(self):
        for frame in self.need_report()["frames"]:
            self.assertEqual(frame["counters"], 1)
            self.assertGreater(frame["counter_pixels"], 50)
            self.assertLess(frame["counter_pixels"], 150)
            # a pink tube along the hole's outline and a dark hole inside it
            self.assertGreater(frame["counter_tube_pixels"], 25)
            self.assertGreaterEqual(frame["counter_dark_pixels"], 3)

    def test_shine_mask_is_limited_to_the_neon_text_line(self):
        report = self.need_report()
        self.assertEqual(report["mask_outside_frames"], 0)
        for frame in report["frames"]:
            self.assertEqual(frame["mask_alpha_min"], 255)
            self.assertEqual(frame["mask_blue_max"], 0)
            # nothing above or below the text line: the FRIDAY NIGHT lettering is out
            self.assertEqual(frame["mask_outside_text_rows"], 0)
            # the neon tube takes the full shine, white lettering, the splash and
            # the black fill take none, and the glow only a few percent
            self.assertGreaterEqual(frame["mask_tube_median"], 250)
            self.assertGreaterEqual(frame["mask_tube_p5"], 100)
            self.assertEqual(frame["mask_on_white"], 0)
            self.assertEqual(frame["mask_on_splash"], 0)
            self.assertEqual(frame["mask_on_black"], 0)
            self.assertLess(frame["mask_glow_mean"], 0.03 * 255)

    def test_shine_mask_position_runs_along_the_text_in_every_frame(self):
        for frame in self.need_report()["frames"]:
            self.assertLessEqual(frame["position_tube_min"], 1)
            self.assertGreaterEqual(frame["position_tube_max"], 254)
            self.assertLess(frame["position_left_mean"], 0.1 * 255)
            self.assertGreater(frame["position_right_mean"], 0.9 * 255)
            self.assertGreater(frame["position_correlation"], 0.99)


# Stand-ins for the engine types TitleLogoShine touches, so its real logic runs
# under the Haxe interpreter.
STUBS = {
    "flixel/system/FlxAssets.hx": '''package flixel.system;
class Param { public var value:Array<Float>; public var input:Dynamic; public var filter:openfl.display3D.Context3DTextureFilter; public function new() {} }
class FlxAssets {}
class FlxShader {
 public var uShineMask = new Param();
 public var uShineCenter = new Param();
 public var uShineWidth = new Param();
 public var uShineStrength = new Param();
 public function new() {}
}
''',
    "openfl/display3D/Context3DTextureFilter.hx": '''package openfl.display3D;
enum abstract Context3DTextureFilter(Int) { var LINEAR = 1; var NEAREST = 0; }
''',
    "openfl/display/BitmapData.hx": '''package openfl.display;
class BitmapData { public var width:Int; public var height:Int; public function new(w:Int, h:Int) { width = w; height = h; } }
''',
    "flixel/graphics/FlxGraphic.hx": '''package flixel.graphics;
class FlxGraphic { public var width:Int; public var height:Int; public function new(w:Int, h:Int) { width = w; height = h; } }
''',
    "flixel/FlxSprite.hx": '''package flixel;
class StubRect { public var x:Float; public var y:Float; public var width:Float; public var height:Float;
 public function new(x:Float, y:Float, w:Float, h:Float) { this.x = x; this.y = y; width = w; height = h; } }
class StubFrame { public var frame:StubRect; public function new(r:StubRect) { frame = r; } }
class StubFrames { public var frames:Array<StubFrame> = []; public function new() {} }
class FlxSprite {
 public var frames:StubFrames;
 public var graphic:flixel.graphics.FlxGraphic;
 public var exists:Bool = true;
 public var shader:flixel.system.FlxAssets.FlxShader;
 public function new() {}
}
''',
    "flixel/FlxG.hx": '''package flixel;
class FlxG { public static var stage:{context3D:Dynamic} = {context3D: {}}; }
''',
    "OptionsHandler.hx": '''class OptionsHandler { public static var options = {gameplayShaders: true}; }
''',
    "FNFAssets.hx": '''class FNFAssets {
 public static var requested:Array<String> = [];
 public static var mask:openfl.display.BitmapData = new openfl.display.BitmapData(2048, 2048);
 public static var failure:Bool = false;
 public static function getBitmapData(id:String, ?useCache:Bool = true):openfl.display.BitmapData {
  requested.push(id);
  if (failure) throw 'File ' + id + ' does not exist';
  return mask;
 }
}
''',
}

MAIN = r'''
import flixel.FlxSprite;
import flixel.graphics.FlxGraphic;

class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function stockLogo():FlxSprite {
  var logo = new FlxSprite();
  logo.graphic = new FlxGraphic(2048, 2048);
  logo.frames = new flixel.FlxSprite.StubFrames();
  for (r in [[0, 0, 922, 670], [922, 0, 969, 703], [922, 0, 969, 703], [0, 703, 940, 683], [940, 703, 933, 679]])
   logo.frames.frames.push(new flixel.FlxSprite.StubFrame(new flixel.FlxSprite.StubRect(r[0], r[1], r[2], r[3])));
  return logo;
 }
 static function reset():Void {
  OptionsHandler.options.gameplayShaders = true;
  flixel.FlxG.stage = {context3D: {}};
  FNFAssets.failure = false;
  FNFAssets.requested = [];
  FNFAssets.mask = new openfl.display.BitmapData(2048, 2048);
 }
 static function main() {
  // the sweep: idle first, then one pass across the text, then idle until the next period
  check(TitleLogoShine.centerAt(-0.5) == TitleShineShader.IDLE, 'no shine before the first sweep');
  check(Math.abs(TitleLogoShine.centerAt(0.0) + TitleLogoShine.REACH) < 1e-9, 'the band starts left of the text');
  var last = TitleLogoShine.centerAt(0.0);
  var t = 0.01;
  while (t < TitleLogoShine.SWEEP) {
   var now = TitleLogoShine.centerAt(t);
   check(now > last, 'the band must keep moving right at ' + t);
   last = now;
   t += 0.01;
  }
  check(last > 1.0 + TitleLogoShine.REACH - 0.02, 'the band ends right of the text');
  check(TitleLogoShine.centerAt(TitleLogoShine.SWEEP + 0.01) == TitleShineShader.IDLE, 'idle after the sweep');
  check(TitleLogoShine.centerAt(TitleLogoShine.PERIOD - 0.01) == TitleShineShader.IDLE, 'idle until the next period');
  check(Math.abs(TitleLogoShine.centerAt(TitleLogoShine.PERIOD * 3 + 0.25) - TitleLogoShine.centerAt(0.25)) < 1e-9, 'the sweep repeats');
  check(Math.abs(TitleLogoShine.centerAt(TitleLogoShine.PERIOD + 0.5) - TitleLogoShine.centerAt(0.5)) < 1e-9, 'every period is the same');

  // layout check
  check(TitleLogoShine.isStockLayout([[0, 0, 922, 670], [940, 703, 933, 679]], 2048, 2048), 'stock frames');
  check(!TitleLogoShine.isStockLayout([[0, 0, 922, 671]], 2048, 2048), 'a changed frame is not stock');
  check(!TitleLogoShine.isStockLayout([[0, 0, 922, 670]], 1024, 1024), 'a smaller sheet is not stock');
  check(!TitleLogoShine.isStockLayout([], 2048, 2048), 'no frames is not stock');

  // attaches to the stock logo
  reset();
  var logo = stockLogo();
  var shine = TitleLogoShine.attach(logo, 'assets/images/');
  check(shine != null && logo.shader != null, 'the stock logo gets the shine');
  check(FNFAssets.requested.join(',') == 'assets/images/logoBumpinShine.png', 'the mask path: ' + FNFAssets.requested);
  var shader:TitleShineShader = cast logo.shader;
  check(shader.uShineCenter.value[0] == TitleShineShader.IDLE, 'idle before the title is shown');
  shine.update(0.5);
  check(shader.uShineCenter.value[0] == TitleShineShader.IDLE, 'the clock waits for start()');
  shine.start();
  shine.update(TitleLogoShine.FIRST_DELAY + 0.4);
  check(shader.uShineCenter.value[0] != TitleShineShader.IDLE, 'sweeping after the first delay');
  shine.update(TitleLogoShine.SWEEP + 0.1);
  check(shader.uShineCenter.value[0] == TitleShineShader.IDLE, 'idle after one sweep');

  // a script that loads its own logo atlas keeps it as it is
  reset();
  logo = stockLogo();
  check(TitleLogoShine.attach(logo, 'assets/images/custom_states/title/template/') == null, 'a custom logo folder is left alone');
  check(logo.shader == null && FNFAssets.requested.length == 0, 'nothing is loaded for a custom folder');

  // shaders off (low quality) means no shine and no mask load
  reset();
  OptionsHandler.options.gameplayShaders = false;
  logo = stockLogo();
  check(TitleLogoShine.attach(logo, 'assets/images/') == null && logo.shader == null, 'shaders off means no shine');
  check(FNFAssets.requested.length == 0, 'shaders off loads nothing');

  // no GL context (software rendering) means no shine and no mask load
  reset();
  flixel.FlxG.stage = {context3D: null};
  logo = stockLogo();
  check(TitleLogoShine.attach(logo, 'assets/images/') == null && logo.shader == null, 'no GL context means no shine');
  check(FNFAssets.requested.length == 0, 'no GL context loads nothing');
  flixel.FlxG.stage = null;
  check(TitleLogoShine.attach(stockLogo(), 'assets/images/') == null, 'no stage means no shine');

  // a missing mask or a mask of another size means no shine
  reset();
  FNFAssets.failure = true;
  logo = stockLogo();
  check(TitleLogoShine.attach(logo, 'assets/images/') == null && logo.shader == null, 'a missing mask means no shine');
  reset();
  FNFAssets.mask = new openfl.display.BitmapData(512, 512);
  logo = stockLogo();
  check(TitleLogoShine.attach(logo, 'assets/images/') == null && logo.shader == null, 'a mask of another size means no shine');

  // an atlas with a different layout, or a logo without frames, means no shine
  reset();
  logo = stockLogo();
  logo.frames.frames.push(new flixel.FlxSprite.StubFrame(new flixel.FlxSprite.StubRect(0, 0, 100, 100)));
  check(TitleLogoShine.attach(logo, 'assets/images/') == null && logo.shader == null, 'a replaced atlas means no shine');
  reset();
  logo = stockLogo();
  logo.frames = null;
  check(TitleLogoShine.attach(logo, 'assets/images/') == null, 'no frames means no shine');
  check(TitleLogoShine.attach(null, 'assets/images/') == null, 'no sprite means no shine');

  // a script that swaps the logo's graphic ends the shine and removes only its own shader
  reset();
  logo = stockLogo();
  shine = TitleLogoShine.attach(logo, 'assets/images/');
  shine.start();
  logo.graphic = new FlxGraphic(2048, 2048);
  shine.update(0.1);
  check(logo.shader == null, 'a swapped graphic drops the shine');
  shine.update(0.1);

  // a script that installs its own shader keeps it
  reset();
  logo = stockLogo();
  shine = TitleLogoShine.attach(logo, 'assets/images/');
  var own = new TitleShineShader();
  logo.shader = own;
  shine.update(0.1);
  check(logo.shader == own, 'a script shader is never removed');

  // harness freeze
  reset();
  logo = stockLogo();
  shine = TitleLogoShine.attach(logo, 'assets/images/');
  TitleLogoShine.frozenTime = 0.5 * TitleLogoShine.SWEEP;
  shine.update(10.0);
  shader = cast logo.shader;
  check(Math.abs(shader.uShineCenter.value[0] - 0.5) < 1e-6, 'a frozen sweep stays where it was put');
  TitleLogoShine.frozenTime = null;
 }
}
'''


class TitleShineHaxeTests(unittest.TestCase):
    def test_logo_shine_logic_and_fallbacks(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            root = Path(folder)
            for relative, text in STUBS.items():
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, newline="\n")
            for source in (SHADER, SHINE):
                (root / source.name).write_text(source.read_text(encoding="utf-8"), newline="\n")
            (root / "Main.hx").write_text(MAIN, newline="\n")
            result = subprocess.run([*HAXE_COMMAND, "-cp", folder, "-main", "Main", "--interp"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_title_state_applies_the_shine_to_the_stock_logo_only(self):
        text = TITLE_STATE.read_text(encoding="utf-8")
        self.assertIn("var logoShine:TitleLogoShine;", text)
        # attached right after the logo is built, with the folder it was loaded from
        built = text.index("logoBl.frames = DynamicAtlasFrames.fromSparrow(path + 'logoBumpin.png'")
        self.assertIn("logoShine = TitleLogoShine.attach(logoBl, path);", text[built:built + 900])
        # advanced every frame and started when the intro text is skipped
        self.assertIn("logoShine.update(elapsed);", text)
        skip = text[text.index("function skipIntro():Void"):]
        self.assertIn("logoShine.start();", skip[:600])
        # everything is guarded: a null shine (custom title, shaders off) changes nothing
        for line in ("logoShine.update(elapsed);", "logoShine.start();"):
            self.assertRegex(text, r"if \(logoShine != null\)\s+" + re.escape(line))

    def test_shine_falls_back_to_the_plain_logo(self):
        text = SHINE.read_text(encoding="utf-8")
        for guard in ("path != STOCK_PATH", "OptionsHandler.options.gameplayShaders", "shadersAvailable()", "isStockLayout(",
                      "mask.width != SHEET_SIZE", "catch (error:Dynamic)"):
            self.assertIn(guard, text)
        self.assertIn("sprite.shader != shader", text)

    def test_shader_follows_the_overlay_shader_conventions(self):
        text = SHADER.read_text(encoding="utf-8")
        self.assertIn("extends FlxShader", text)
        self.assertIn("@:glFragmentSource('", text)
        self.assertIn("#pragma header", text)
        self.assertIn("flixel_texture2D(bitmap, openfl_TextureCoordv)", text)
        self.assertIn("texture2D(uShineMask, openfl_TextureCoordv)", text)
        # premultiplied alpha: the tint is scaled by the pixel's alpha before mixing
        self.assertIn("shineTint(edge) * base.a", text)
        # the flag colours: light blue #5BCEFA and pink #F5A9B8
        for name, hexcode in (("SHINE_BLUE", "5BCEFA"), ("SHINE_PINK", "F5A9B8")):
            found = re.search(name + r" = vec3\(([\d.]+), ([\d.]+), ([\d.]+)\)", text)
            self.assertIsNotNone(found, name)
            wanted = [int(hexcode[i:i + 2], 16) / 255 for i in (0, 2, 4)]
            for got, want in zip(found.groups(), wanted):
                self.assertAlmostEqual(float(got), want, places=3)
        self.assertIn("vec3(1.0)", text)

    def test_startup_profile_run_keeps_the_ordinary_title_state(self):
        main = (ROOT / "source" / "Main.hx").read_text(encoding="utf-8")
        self.assertIn("else if (RuntimeSmokeHarness.enabled() && !RuntimeStartupProbe.enabled())", main)
        probe = (ROOT / "source" / "RuntimeStartupProbe.hx").read_text(encoding="utf-8")
        self.assertIn("--profile-startup-screenshot", probe)
        # screenshots of the sweep: skip the intro text and freeze the shine at a chosen moment
        self.assertIn("--profile-startup-skip-intro", probe)
        self.assertIn("--profile-startup-shine-time", probe)
        self.assertIn("TitleLogoShine.frozenTime = seconds", probe)

    def test_update_log_describes_the_logo(self):
        text = (ROOT / "updateLog.txt").read_text(encoding="utf-8")
        section = text[text.index("v0.0.44 development - CammieEngine"):]
        section = section[:section.index("\nv0.0.43")]
        lines = [line for line in section.splitlines() if "title screen logo" in line]
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("shine", lines[0])


if __name__ == "__main__":
    unittest.main()
