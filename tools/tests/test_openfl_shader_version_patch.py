import importlib.util
from pathlib import Path
from haxe_test_support import FixturePath as Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
PATCH_PATH = ROOT / "tools/patch_openfl_shader_version.py"
SPEC = importlib.util.spec_from_file_location("openfl_shader_version_patch", PATCH_PATH)
PATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCH)


class OpenFLShaderVersionPatchTest(unittest.TestCase):
    def test_pinned_openfl_shader_patch_is_idempotent_and_routes_both_stages(self):
        current = PATCH.OPENFL_SOURCE.read_bytes()
        patched = PATCH.patch_source(current)
        self.assertEqual(PATCH.patch_source(patched), patched)
        self.assertIn(b"openfl-glsl-version", patched)
        self.assertIn(b"var vertex = __withGLSLVersion(glVertexSource, prefix);", patched)
        self.assertIn(b"var fragment = __withGLSLVersion(glFragmentSource, prefix);", patched)
        self.assertIn(b'return directive + "\\n" + prefix + lines.join("\\n");', patched)
        self.assertNotIn(b"var vertex = prefix + glVertexSource;", patched)

    def test_patch_rejects_unrecognized_dependency_source(self):
        with self.assertRaisesRegex(ValueError, "differs from pinned 9.5.2"):
            PATCH.patch_source(b"class Shader {}\n")


if __name__ == "__main__":
    unittest.main()
