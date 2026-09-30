"""Regression tests for OpenFL's bounded Context3D bitmap-readback buffer."""

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "patch_openfl_context3d_readback",
    ROOT / "tools/patch_openfl_context3d_readback.py",
)
PATCHER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCHER)


class OpenFLContext3DReadbackPatchTest(unittest.TestCase):
    def pinned_original(self):
        installed = PATCHER.OPENFL_SOURCE.read_bytes()
        if PATCHER.sha256(installed) == PATCHER.PATCHED_SHA256:
            installed = PATCHER._replace_once(
                installed, PATCHER.NEW_SNAPSHOT, PATCHER.OLD_SNAPSHOT, "snapshot"
            )
            installed = PATCHER._replace_once(
                installed, PATCHER.NEW_DISPOSE, PATCHER.OLD_DISPOSE, "dispose"
            )
            installed = PATCHER._replace_once(
                installed, PATCHER.NEW_FIELDS, PATCHER.OLD_FIELDS, "context fields"
            )
        self.assertEqual(PATCHER.sha256(installed), PATCHER.SOURCE_SHA256)
        return installed

    def test_pinned_patch_is_idempotent_and_fails_closed(self):
        original = self.pinned_original()
        patched = PATCHER.patch_source(original)

        self.assertEqual(PATCHER.sha256(patched), PATCHER.PATCHED_SHA256)
        self.assertEqual(PATCHER.patch_source(patched), patched)
        with self.assertRaisesRegex(ValueError, "differs from the pinned"):
            PATCHER.patch_source(original + b"// unexpected source drift\n")

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "Context3D.hx"
            target.write_bytes(original)
            self.assertTrue(PATCHER.patch_file(target))
            self.assertFalse(PATCHER.patch_file(target))
            self.assertEqual(target.read_bytes(), patched)

    def test_readback_reuses_exact_size_storage_and_keeps_copy_path(self):
        source = PATCHER.patch_source(self.pinned_original()).decode("utf-8")
        branch_start = source.index("else if (__backBufferTexture != null)")
        branch_end = source.index("\n\t\t}\n\t\t#end", branch_start)
        branch = source[branch_start:branch_end]

        resize_guard = "if (__readbackPixels == null || __readbackWidth != backBufferWidth || __readbackHeight != backBufferHeight)"
        self.assertEqual(branch.count(resize_guard), 1)
        guard_start = branch.index(resize_guard)
        allocation = branch.index("new UInt8Array(backBufferWidth * backBufferHeight * 4)")
        readback = branch.index("gl.readPixels(")
        bitmap_copy = branch.index("destination.image.copyPixels(__readbackImage, sourceRect, destVector)")
        self.assertLess(guard_start, allocation)
        self.assertLess(allocation, readback)
        self.assertLess(readback, bitmap_copy)
        self.assertEqual(branch.count("new UInt8Array("), 1)
        self.assertIn("__readbackImage = new Image(new ImageBuffer(__readbackPixels, backBufferWidth, backBufferHeight, 32, BGRA32));", branch)
        self.assertIn("__readbackImage = null;", branch[:allocation])
        self.assertIn("__readbackPixels = null;", branch[:allocation])

        dispose_start = source.index("private function __dispose():Void")
        dispose = source[dispose_start:source.index("\n\t}", dispose_start)]
        self.assertIn("__readbackImage = null;", dispose)
        self.assertIn("__readbackPixels = null;", dispose)
        self.assertIn("__readbackWidth = 0;", dispose)
        self.assertIn("__readbackHeight = 0;", dispose)


if __name__ == "__main__":
    unittest.main()
