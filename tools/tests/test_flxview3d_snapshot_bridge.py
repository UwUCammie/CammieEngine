"""Pin the source-accurate Away3D-to-Flixel snapshot bridge."""

from pathlib import Path
from haxe_test_support import FixturePath as Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


def method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for position in range(opening, len(source)):
        if source[position] == "{":
            depth += 1
        elif source[position] == "}":
            depth -= 1
            if depth == 0:
                return source[start : position + 1]
    raise AssertionError(marker)


class FlxView3DSnapshotBridgeTest(unittest.TestCase):
    def test_away3d_snapshot_uses_authored_size_and_is_drawn_as_flixel_sprite(self):
        source = (ROOT / "source/flx3d/FlxView3D.hx").read_text()
        constructor = method(source, "public function new(")
        draw = method(source, "@:noCompletion override function draw()")

        self.assertIn("view.width = width == -1 ? FlxG.width : width;", constructor)
        self.assertIn("view.height = height == -1 ? FlxG.height : height;", constructor)
        self.assertIn("new BitmapData(Std.int(view.width), Std.int(view.height), true, 0x0)", constructor)
        self.assertLess(draw.index("super.draw();"), draw.index("view.renderer.queueSnapshot(bmp);"))
        self.assertLess(draw.index("view.renderer.queueSnapshot(bmp);"), draw.index("view.render();"))
        self.assertIn("view.shareContext = false;", draw)
        self.assertIn("FlxG.stage.addChildAt(view, 0);", draw)
        self.assertIn("FlxG.stage.removeChild(view);", draw)
        self.assertIn("if (RuntimeSmokeHarness.enabled())", draw)

    def test_gpu_target_experiment_is_not_used_or_left_as_dead_code(self):
        source = (ROOT / "source/flx3d/FlxView3D.hx").read_text()
        self.assertNotIn("gpuOutputActive", source)
        self.assertNotIn("RenderTarget", source)
        self.assertFalse((ROOT / "source/flx3d/FlxView3DRenderTargetRenderer.hx").exists())
        self.assertFalse((ROOT / "source/flx3d/FlxView3DOutputBitmapData.hx").exists())
        self.assertFalse((ROOT / "source/flx3d/FlxView3DRenderTargetPolicy.hx").exists())


if __name__ == "__main__":
    unittest.main()
