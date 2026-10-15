"""Repeat loads of one owner atlas reuse its frames and frame names instead of
probing the disk again. A results screen built in one end-of-song callback
loads the same sheets dozens of times in one frame."""
import unittest
from pathlib import Path

from test_native_asset_resolution import extract_method

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source"


class OwnerAtlasReuseTest(unittest.TestCase):
    def test_sparrow_atlas_stops_at_the_xml_and_is_keyed_by_path(self):
        paths = (SOURCE / "PsychOwnerPaths.hx").read_text(encoding="utf-8")
        body = extract_method(paths, "static function autoAtlas(")
        sparrow = body.index("var sparrow = ownerAsset(owner, 'images/' + clean + '.xml'")
        early = body.index("return DynamicAtlasFrames.fromSparrow(imagePath, sparrow);")
        # Psych's own order: a Sparrow file wins, the JSON and packer files are
        # only looked for when there is none.
        self.assertLess(sparrow, early)
        self.assertLess(early, body.index("var aseprite = ownerAsset("))
        self.assertLess(early, body.index("var packer = ownerAsset("))
        # A Sparrow file with no image is still refused before anything loads.
        self.assertIn("if (imagePath == null)\n\t\t\t\tthrow '[psych-assets] Incomplete selected-owner atlas: ' + clean;\n\t\t\treturn DynamicAtlasFrames.fromSparrow",
            body)
        # The path, not the text: the atlas cache then answers without a file read.
        self.assertNotIn("fromSparrow(imagePath, FNFAssets.getText(sparrow))", body)
        frames = (SOURCE / "DynamicSprite.hx").read_text(encoding="utf-8")
        loader = extract_method(frames, "public static function fromSparrow(png:FlxGraphicAsset, xml:String)")
        self.assertLess(loader.index("cachedFor(key, xml)"), loader.index("FNFAssets.getText(xml)"))
        self.assertIn("if (!isInlineText(xml) && FNFAssets.exists(xml))", loader)

    def test_frame_names_are_read_once_per_atlas_and_file_generation(self):
        play = (SOURCE / "PlayState.hx").read_text(encoding="utf-8")
        body = extract_method(play, "function compatPsychSpriteFrameNames(")
        epoch = body.index("var epoch = FNFAssets.pathEpoch();")
        lookup = body.index("var cached = compatSpriteFrameNamesCache.get(cacheKey);")
        read = body.index("compatReadSparrowFrameNames(FNFAssets.getText(Std.string(xmlPath)))")
        # A file change (new epoch) drops every remembered list before the lookup.
        self.assertLess(epoch, body.index("compatSpriteFrameNamesCache.clear();"))
        self.assertLess(body.index("compatSpriteFrameNamesCache.clear();"), lookup)
        self.assertLess(lookup, read)
        self.assertIn("var cacheKey = ownerRoot + '|' + key;", body)
        self.assertIn("compatSpriteFrameNamesCache.set(cacheKey, names);", body)
        # Missing XML is not remembered, so a sheet added later is still found.
        self.assertLess(body.index("if (xmlPath != null && FNFAssets.exists(Std.string(xmlPath))) {"),
            body.index("compatSpriteFrameNamesCache.set(cacheKey, names);"))
        # The remembered lists are only read by the animation helpers.
        self.assertNotIn("authoredNames.push", play)
        self.assertNotIn("authoredNames.splice", play)


if __name__ == "__main__":
    unittest.main()
