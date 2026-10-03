"""Regression coverage for restoring OpenFL's shared GL blend state."""

import importlib.util
from pathlib import Path
from haxe_test_support import FixturePath as Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "patch_openfl_blend_restore", ROOT / "tools/patch_openfl_blend_restore.py"
)
PATCHER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCHER)


class OpenFLBlendRestorePatchTest(unittest.TestCase):
    def pinned_original(self):
        installed = PATCHER.OPENFL_SOURCE.read_bytes()
        if PATCHER.sha256(installed) == PATCHER.PATCHED_SHA256:
            self.assertEqual(installed.count(PATCHER.NEW_RESTORE), 1)
            installed = installed.replace(PATCHER.NEW_RESTORE, PATCHER.OLD_RESTORE, 1)
        self.assertEqual(PATCHER.sha256(installed), PATCHER.SOURCE_SHA256)
        return installed

    def test_pinned_patch_is_idempotent_and_fails_closed(self):
        original = self.pinned_original()
        patched = PATCHER.patch_source(original)

        self.assertEqual(PATCHER.sha256(patched), PATCHER.PATCHED_SHA256)
        self.assertEqual(PATCHER.patch_source(patched), patched)
        with self.assertRaisesRegex(ValueError, "differs from pinned 9.5.2"):
            PATCHER.patch_source(original + b"// unexpected source drift\n")

        temp_root = ROOT / "tmp"
        temp_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as directory:
            target = Path(directory) / "DisplayObjectRenderer.hx"
            target.write_bytes(original)
            self.assertTrue(PATCHER.patch_file(target))
            self.assertFalse(PATCHER.patch_file(target))
            self.assertEqual(target.read_bytes(), patched)

    def test_cached_child_add_restores_saved_normal_to_shared_context(self):
        original = self.pinned_original().decode("utf-8")
        patched = PATCHER.patch_source(original.encode("utf-8")).decode("utf-8")

        def restore_snippet(source):
            cache = source.index("var cacheBlendMode = parentRenderer.__blendMode;")
            start = source.index("parentRenderer.__blendMode = ", cache)
            end = source.index("parentRenderer.__copyShader(childRenderer);", start)
            return source[start:end]

        self.assertIn("parentRenderer.__blendMode = NORMAL;", restore_snippet(original))
        self.assertIn("parentRenderer.__blendMode = null;", restore_snippet(patched))
        self.assertLess(
            restore_snippet(patched).index("parentRenderer.__blendMode = null;"),
            restore_snippet(patched).index("parentRenderer.__setBlendMode(cacheBlendMode);"),
        )

        # OpenGLRenderer.__setBlendMode first applies __overrideBlendMode, then
        # returns early when its cached mode matches. Child renderers share the
        # GL context but keep their own cache, so an ADD child can leave GL in ADD
        # while the parent's cached mode still says NORMAL.
        opengl_source = (ROOT / ".haxelib/openfl/9,5,2/src/openfl/display/OpenGLRenderer.hx").read_text()
        setter_start = opengl_source.index("private override function __setBlendMode(value:BlendMode):Void")
        setter = opengl_source[setter_start : opengl_source.index("@:noCompletion private function __setRenderTarget", setter_start)]
        self.assertLess(setter.index("if (__overrideBlendMode != null)"), setter.index("if (__blendMode == value) return;"))

        def simulate(source, override=None):
            restore = restore_snippet(source)
            context_blend = "ADD"  # the filtered child pass just changed shared GL state
            parent_cache = "NORMAL"  # the parent renderer still believes NORMAL is active
            saved_blend = "NORMAL"
            if "parentRenderer.__blendMode = null;" in restore:
                parent_cache = None
            else:
                parent_cache = "NORMAL"

            actual = override if override is not None else saved_blend
            if parent_cache != actual:
                parent_cache = actual
                context_blend = actual
            return context_blend, parent_cache

        self.assertEqual(simulate(original)[0], "ADD")
        self.assertEqual(simulate(patched), ("NORMAL", "NORMAL"))
        # The patch invalidates bookkeeping but leaves an explicit renderer
        # override effective, matching OpenGLRenderer's real setter order.
        self.assertEqual(simulate(patched, override="ADD"), ("ADD", "ADD"))


if __name__ == "__main__":
    unittest.main()
