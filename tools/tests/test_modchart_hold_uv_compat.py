"""Pin the Flixel 6.1.2 UV adapter and the isolated haxelib source patch."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
MODCHART_UTIL = ROOT / ".haxelib/funkin-modchart/1,2,5/modchart/backend/util/ModchartUtil.hx"
PATCHER = ROOT / "tools/patch_funkin_modchart_uv.py"


class ModchartHoldUVCompatTest(unittest.TestCase):
    def test_asymmetric_uv_bounds_subdivision_and_continuity(self):
        fixture = r'''
class Main {
    static function near(actual:Float, expected:Float, label:String):Void {
        if (Math.abs(actual - expected) > 0.000001)
            throw label + ": expected " + expected + ", got " + actual;
    }
    static function main():Void {
        var left = 0.13;
        var top = 0.21;
        var right = 0.47;
        var bottom = 0.93;
        var height = bottom - top;
        var subdivisions = 3;
        var uv = ModchartHoldUVCompat.getHoldUVT(left, top, right, bottom, 0, subdivisions);
        if (uv.length != 12 * subdivisions) throw "wrong UVT length";

        for (sub in 0...subdivisions) {
            var base = sub * 12;
            var v0 = top + height * sub / subdivisions;
            var v1 = top + height * (sub + 1) / subdivisions;
            near(uv[base], left, "sub top-left U");
            near(uv[base + 1], v0, "sub top-left V");
            near(uv[base + 3], right, "sub top-right U");
            near(uv[base + 4], v0, "sub top-right V");
            near(uv[base + 6], left, "sub bottom-left U");
            near(uv[base + 7], v1, "sub bottom-left V");
            near(uv[base + 9], right, "sub bottom-right U");
            near(uv[base + 10], v1, "sub bottom-right V");
            for (vertex in 0...4) near(uv[base + vertex * 3 + 2], 1, "perspective T");
        }

        for (sub in 0...(subdivisions - 1)) {
            var base = sub * 12;
            var next = base + 12;
            near(uv[base + 6], uv[next], "vertical seam left U");
            near(uv[base + 7], uv[next + 1], "vertical seam left V");
            near(uv[base + 9], uv[next + 3], "vertical seam right U");
            near(uv[base + 10], uv[next + 4], "vertical seam right V");
        }
    }
}
'''
        self.run_haxe_fixture(fixture)

    def test_rotated_non_square_frames_stay_inside_atlas_and_join(self):
        fixture = r'''
class Main {
    static function near(actual:Float, expected:Float, label:String):Void {
        if (Math.abs(actual - expected) > 0.000001)
            throw label + ": expected " + expected + ", got " + actual;
    }
    static function checkAngle(angle:Float, expectedTLU:Float, expectedTLV:Float,
        expectedTRU:Float, expectedTRV:Float):Void {
        var left = 0.11;
        var top = 0.20;
        var right = 0.41;
        var bottom = 0.90;
        var uv = ModchartHoldUVCompat.getHoldUVT(left, top, right, bottom, angle, 2);
        if (uv.length != 24) throw "rotated UVT stride/length mismatch";
        near(uv[0], expectedTLU, "rotated first TL U");
        near(uv[1], expectedTLV, "rotated first TL V");
        near(uv[3], expectedTRU, "rotated first TR U");
        near(uv[4], expectedTRV, "rotated first TR V");

        for (i in 0...uv.length) {
            if (i % 3 == 2) near(uv[i], 1, "rotated perspective T");
            else if (uv[i] < (i % 3 == 0 ? left - 0.000001 : top - 0.000001)
                || uv[i] > (i % 3 == 0 ? right + 0.000001 : bottom + 0.000001))
                throw "rotated UV escaped the non-square atlas rectangle at index " + i + ": " + uv[i];
        }

        // Bottom corners of subdivision zero meet the corresponding top
        // corners of subdivision one even after the packed frame rotation.
        near(uv[6], uv[12], "rotated seam left U");
        near(uv[7], uv[13], "rotated seam left V");
        near(uv[9], uv[15], "rotated seam right U");
        near(uv[10], uv[16], "rotated seam right V");
    }
    static function main():Void {
        // Frame angle is the inverse of FlxFrame.angle, as in upstream.
        // +90 maps local (u,v) to (1-v,u); -90 maps to (v,1-u).
        checkAngle(90, 0.41, 0.20, 0.41, 0.90);
        checkAngle(-90, 0.11, 0.90, 0.11, 0.20);
    }
}
'''
        self.run_haxe_fixture(fixture)

    def test_bad_subdivision_count_is_reported(self):
        fixture = r'''
class Main {
    static function main():Void {
        var rejected = false;
        try ModchartHoldUVCompat.getHoldUVT(0, 0, 1, 1, 0, 0) catch (_:Dynamic) rejected = true;
        if (!rejected) throw "zero subdivisions were accepted";
    }
}
'''
        self.run_haxe_fixture(fixture)

    def test_haxelib_patch_is_narrow_idempotent_and_wired(self):
        self.assertTrue(MODCHART_UTIL.is_file(), "pinned haxelib source must be available for a temp-copy patch test")
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            patched_path = Path(work) / "ModchartUtil.hx"
            shutil.copyfile(MODCHART_UTIL, patched_path)
            first = subprocess.run(
                [sys.executable, str(PATCHER), str(patched_path)], cwd=ROOT,
                capture_output=True, text=True, timeout=30)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            once = patched_path.read_text(encoding="utf-8")
            self.assertIn("import ModchartHoldUVCompat;", once)
            self.assertIn("ModchartCameraCompat.resolve(item, playfield, Adapter.instance.getArrowCamera)", once)
            self.assertNotIn("item.getCameras()", once)
            self.assertIn("// DisappointingPlus: FlxUVRect field order + hold UV stride fix", once)
            self.assertIn("frameUV.left, frameUV.top, frameUV.right, frameUV.bottom", once)
            self.assertIn("-ModchartUtil.getFrameAngle(arrow), subs", once)
            self.assertNotIn("curSub * 8", once)
            patched_bytes = patched_path.read_bytes()
            self.assertIn(b"\r\n", patched_bytes)
            self.assertEqual(patched_bytes.count(b"\n"), patched_bytes.count(b"\r\n"))

            second = subprocess.run(
                [sys.executable, str(PATCHER), str(patched_path)], cwd=ROOT,
                capture_output=True, text=True, timeout=30)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertEqual(patched_path.read_text(encoding="utf-8"), once)
            self.assertEqual(second.stdout, "")

        run_script = (ROOT / "run.sh").read_text(encoding="utf-8")
        self.assertIn("python3 tools/patch_funkin_modchart_uv.py \"$FMU\"", run_script)
        self.assertIn("FMU=.haxelib/funkin-modchart/1,2,5/modchart/backend/util/ModchartUtil.hx", run_script)

    def run_haxe_fixture(self, fixture):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            folder = Path(work)
            (folder / "Main.hx").write_text(fixture, encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(folder), "-main", "Main", "--interp"],
                cwd=ROOT, env={**os.environ, "TMPDIR": work},
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
