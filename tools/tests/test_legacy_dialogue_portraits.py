"""FPS/Kade dialogue portrait bundles use the native dialogue renderer."""

from pathlib import Path
import json
import os
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods/whitty")


class LegacyDialoguePortraitTest(unittest.TestCase):
    def test_config_parser_and_safe_frame_order(self):
        fixture = r'''
class PortraitCompatFixture {
  static function fail(message:String):Void throw message;
  static function main() {
    var parsed = LegacyDialoguePortraitCompat.parse(
      '{"antialiasing":false,"scale":1.5,"offset":{"x":-150,"y":50},"fps":12,"loop":false}');
    if (parsed.antialiasing != false || parsed.scale != 1.5
        || parsed.offsetX != -150 || parsed.offsetY != 50
        || parsed.frameRate != 12 || parsed.looped)
      fail("valid portrait config was not retained");
    var malformed = LegacyDialoguePortraitCompat.parse('{nope');
    if (malformed.scale != 1 || malformed.frameRate != 24 || !malformed.looped)
      fail("malformed optional metadata did not fall back safely");
    if (LegacyDialoguePortraitCompat.hasMetadata('{nope')
        || LegacyDialoguePortraitCompat.hasMetadata('[]')
        || !LegacyDialoguePortraitCompat.hasMetadata('{"scale":1}'))
      fail("metadata validity boundary failed");
    var scalar = LegacyDialoguePortraitCompat.parse('1');
    if (scalar.scale != 1 || LegacyDialoguePortraitCompat.hasMetadata('1'))
      fail("scalar metadata did not fall back safely");
    if (LegacyDialoguePortraitCompat.safeId("../escape") != ""
        || LegacyDialoguePortraitCompat.safeId("folder/name") != ""
        || LegacyDialoguePortraitCompat.safeId(" whittyPort ") != "whittyPort")
      fail("portrait path token validation failed");
    if (LegacyDialoguePortraitCompat.frameIndices(4).join(",") != "0,1,2,3")
      fail("atlas frame ordering failed");
    trace("OK");
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "PortraitCompatFixture.hx"
            path.write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder,
                 "-cp", str(ROOT / "source"), "--run", "PortraitCompatFixture"],
                cwd=folder, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_dialogue_box_loads_atlas_and_metadata(self):
        source = (ROOT / "source/DialogueBox.hx").read_text()
        self.assertIn("LegacyDialoguePortraitCompat.safeId(curEmotion)", source)
        self.assertIn("LegacyDialoguePortraitCompat.safeId(curCharacter)", source)
        self.assertEqual(source.count("var portraitBase ="), 1)
        self.assertIn("portraitBase + '.xml'", source)
        self.assertIn("portraitBase + '.json'", source)
        self.assertIn("FlxAtlasFrames.fromSparrow", source)
        self.assertIn("LegacyDialoguePortraitCompat.frameIndices", source)
        self.assertIn("LegacyDialoguePortraitCompat.hasMetadata", source)
        self.assertIn("if (atlasFrames != null)", source)
        self.assertIn("portrait.offset.set(portraitConfig.offsetX", source)

    @unittest.skipUnless(DONOR.is_dir(), "the mounted Whitty fixture is unavailable")
    def test_every_mounted_dialogue_portrait_has_a_complete_bundle(self):
        used = set()
        for path in sorted((DONOR / "data/songs").glob("*/dialogue.json")):
            data = json.loads(path.read_text())
            for entry in data.get("dialogue", []):
                used.update(value for value in entry.get("portraits", []) if value)
        self.assertTrue(used)
        base = DONOR / "images/ui/dialogue/portraits"
        expected_frames = {
            "whittyPort": 6,
            "whittyPortAng": 5,
            "whittyPortCrazy": 4,
            "boyfriendPort": 1,
        }
        for portrait in sorted(used):
            with self.subTest(portrait=portrait):
                self.assertTrue((base / f"{portrait}.png").is_file())
                self.assertTrue((base / f"{portrait}.xml").is_file())
                self.assertTrue((base / f"{portrait}.json").is_file())
                atlas = ET.parse(base / f"{portrait}.xml").getroot()
                self.assertEqual(len(atlas.findall("SubTexture")), expected_frames[portrait])
                image_name = atlas.attrib.get("imagePath")
                if image_name:
                    self.assertTrue((base / image_name).is_file())

    @unittest.skipUnless(DONOR.is_dir(), "the mounted Whitty fixture is unavailable")
    def test_mounted_whitty_metadata_and_frame_bundles_execute_through_helper(self):
        fixture = r'''
import sys.io.File;
class PortraitCompatFixture {
  static function fail(message:String):Void throw message;
  static function main() {
    var root = Sys.args()[0];
    var base = root + "/images/ui/dialogue/portraits/";
    var whittyText = File.getContent(base + "whittyPort.json");
    var boyfriendText = File.getContent(base + "boyfriendPort.json");
    var whitty = LegacyDialoguePortraitCompat.parse(whittyText);
    var boyfriend = LegacyDialoguePortraitCompat.parse(boyfriendText);
    if (!LegacyDialoguePortraitCompat.hasMetadata(whittyText)
        || !LegacyDialoguePortraitCompat.hasMetadata(boyfriendText))
      fail("mounted portrait metadata was not recognized");
    if (whitty.antialiasing != true || whitty.scale != 1
        || whitty.offsetX != -150 || whitty.offsetY != 50)
      fail("Whitty metadata changed");
    if (boyfriend.antialiasing != true || boyfriend.offsetX != -800
        || boyfriend.offsetY != 30)
      fail("boyfriend metadata changed");
    if (LegacyDialoguePortraitCompat.frameIndices(6).join(",") != "0,1,2,3,4,5")
      fail("mounted atlas frame order boundary failed");
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "PortraitCompatFixture.hx"
            path.write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder,
                 "-cp", str(ROOT / "source"), "--run", "PortraitCompatFixture", str(DONOR)],
                cwd=folder, capture_output=True, text=True,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
