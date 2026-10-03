"""Pin the OpenFL byte-array boundary used by the Codename Away3D loader."""

from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameFlx3DBytesNormalizationTest(unittest.TestCase):
    def test_pinned_away3d_text_parser_does_not_accept_haxe_bytes_directly(self):
        parser_util = (ROOT / ".haxelib/away3d/git/away3d/loaders/parsers/utils/ParserUtil.hx").read_text()
        parser_base = (ROOT / ".haxelib/away3d/git/away3d/loaders/parsers/ParserBase.hx").read_text()
        self.assertIn("if (isOfType(data, String))", parser_util)
        self.assertIn("if (isOfType(data, ByteArrayData))", parser_util)
        self.assertIn("return null;", parser_util)
        self.assertIn("if (s == null)", parser_base)
        self.assertIn('return "";', parser_base)

    def test_model_bytes_are_normalized_before_away3d_load_data(self):
        source = (ROOT / "source/flx3d/Flx3DView.hx").read_text()
        normalization = re.search(
            r"if \(Std\.isOfType\(model, Bytes\)\)\s*model = ByteArray\.fromBytes\(cast model\);",
            source,
        )
        load_data = source.index("return loadData(model,")
        self.assertIsNotNone(normalization)
        self.assertRegex(source, r"var model:Dynamic = loadModelBytes\(assetPath\);")
        self.assertLess(normalization.start(), load_data)

    def test_owner_mtl_and_texture_dependency_bytes_are_normalized(self):
        source = (ROOT / "source/CodenameFlx3DAssetSource.hx").read_text()
        mapping_start = source.index("static function mapResource(")
        mapping_end = source.index("static function normalizeName(", mapping_start)
        mapping = source[mapping_start:mapping_end]
        self.assertRegex(mapping, r"if \(Std\.isOfType\(data, Bytes\)\)")
        self.assertIn("data = ByteArray.fromBytes(cast data);", mapping)
        self.assertIn("context.mapUrlToData(originalName, data);", mapping)
        self.assertIn("context.mapUrlToData(normalized, data);", mapping)

    def test_codename_hscript_forces_owner_adapter_for_legacy_3d_names(self):
        source = (ROOT / "source/CodenameScriptInterp.hx").read_text()
        self.assertIn("case 'Flx3DView' | 'flx3d.Flx3DView'", source)
        self.assertIn("flx3d.CodenameFlx3DView;", source)
        self.assertIn("case 'Flx3DCamera' | 'flx3d.Flx3DCamera'", source)
        self.assertIn("flx3d.CodenameFlx3DCamera;", source)
        self.assertIn("Type.createInstance(ownerClass", source)


if __name__ == "__main__":
    unittest.main()
