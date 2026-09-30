"""Pin shared 3D view sizing and once-only native resource teardown."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class Flx3DLifecycleTest(unittest.TestCase):
    def test_authored_view_dimensions_remain_unscaled(self):
        source = (ROOT / "source/flx3d/FlxView3D.hx").read_text()
        constructor = source[source.index("public function new("):source.index("/**\n\t * Disposes")]
        self.assertIn("view.width = width == -1 ? FlxG.width : width;", constructor)
        self.assertIn("view.height = height == -1 ? FlxG.height : height;", constructor)
        self.assertIn("new BitmapData(Std.int(view.width), Std.int(view.height), true, 0x0)", constructor)
        self.assertNotIn("Flx3DRenderBudget", constructor)
        self.assertNotIn("scale.set(", constructor)

    def test_view_and_model_destroy_paths_are_idempotent(self):
        base = (ROOT / "source/flx3d/FlxView3D.hx").read_text()
        derived = (ROOT / "source/flx3d/Flx3DView.hx").read_text()
        base_destroy = base[base.index("override function destroy():Void"):base.index("@:noCompletion override function draw()")]
        derived_destroy = derived[derived.index("override function destroy():Void"):derived.index("public function addChild")]
        self.assertLess(base_destroy.index("if (destroyed3DView) return"), base_destroy.index("oldView.dispose()"))
        self.assertLess(base_destroy.index("super.destroy();"), base_destroy.index("FlxG.bitmap.remove(oldGraphic)"))
        self.assertIn("if (oldGraphic != null && !oldGraphic.isDestroyed)", base_destroy)
        self.assertIn("else if (oldGraphic == null && oldBitmap != null)", base_destroy)
        self.assertLess(base_destroy.index("if (destroyed3DView) return"), base_destroy.index("oldView.dispose()"))
        self.assertLess(derived_destroy.index("if (destroyed3DAssets) return"), derived_destroy.index("mesh.dispose()"))
        self.assertLess(derived_destroy.index("meshes = [];"), derived_destroy.index("mesh.dispose()"))
        self.assertIn("super.destroy();", derived_destroy)


if __name__ == "__main__":
    unittest.main()
