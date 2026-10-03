"""Synthetic and mounted coverage for compiled legacy character atlases."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
from tools.haxe_import_io_stubs import install_import_io_dependencies


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
VSTRICKY = Path("/run/media/cammie/External Storage/FNF-Example-Mods/vstricky-releasebuild-v21")
MODPLUS = Path("/run/media/cammie/External Storage/modding-plus-fnf")


XML_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<TextureAtlas imagePath="{image}">
  <SubTexture name="{idle}0000" x="0" y="0" width="10" height="10"/>
  <SubTexture name="{up}0000" x="0" y="0" width="10" height="10"/>
  <SubTexture name="{down}0000" x="0" y="0" width="10" height="10"/>
  <SubTexture name="{left}0000" x="0" y="0" width="10" height="10"/>
  <SubTexture name="{right}0000" x="0" y="0" width="10" height="10"/>
</TextureAtlas>
"""


MAIN = r'''import sys.FileSystem;
class Main {
  static function main() {
    var root = Sys.args()[0];
    var reference = Sys.args()[1];
    var role = Sys.args().length > 2
      && (Sys.args()[2] == 'gf' || Sys.args()[2] == 'special') ? Sys.args()[2] : null;
    var result = LegacyCharacterAtlasImporter.inspect(root, reference, role);
    trace('RECOVERABLE=' + result.recoverable);
    trace('NATIVE=' + result.nativeName);
    trace('CANDIDATES=' + result.candidates.length);
    if (result.recoverable) {
      trace('PREFIXES=' + result.candidate.idlePrefix + '|' + result.candidate.singUpPrefix
        + '|' + result.candidate.singDownPrefix + '|' + result.candidate.singLeftPrefix
        + '|' + result.candidate.singRightPrefix);
      var destination = role == null ? Sys.args()[2] : null;
      if (destination != null && destination != '') {
        var copied = LegacyCharacterAtlasImporter.materialize(result, destination);
        trace('COPIED=' + copied.copied + '|SKIPPED=' + copied.skipped + '|FAILED=' + copied.failed);
      }
      var resetIndex = Sys.args().length > 2 && Sys.args()[2] == 'reset' ? 2
        : (Sys.args().length > 3 && Sys.args()[3] == 'reset' ? 3 : -1);
      if (resetIndex >= 0) {
        LegacyCharacterAtlasImporter.clearCache();
        FileSystem.deleteFile(Sys.args()[resetIndex + 1]);
        var after = LegacyCharacterAtlasImporter.inspect(root, reference);
        trace('AFTER_RECOVERABLE=' + after.recoverable);
        trace('AFTER_CANDIDATES=' + after.candidates.length);
      }
    }
    for (diagnostic in result.diagnostics)
      trace('DIAGNOSTIC=' + diagnostic);
  }
}
'''


class LegacyCharacterAtlasImportTest(unittest.TestCase):
    def run_fixture(self, donor: Path, reference: str, destination: Path | None = None,
                    extra: list[str] | None = None):
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            install_import_io_dependencies(temp)
            (temp / "LegacyCharacterAtlasImporter.hx").write_text(
                (ROOT / "source/LegacyCharacterAtlasImporter.hx").read_text()
            , newline='\n')
            (temp / "Main.hx").write_text(MAIN, newline='\n')
            args = [*HAXE_COMMAND, "-cp", str(temp), "--run", "Main", str(donor), reference]
            if destination is not None:
                args.append(str(destination))
            if extra is not None:
                args.extend(extra)
            return subprocess.run(args, cwd=temp, capture_output=True, text=True)

    def make_atlas(self, root: Path, folder: str, stem: str, prefixes=None):
        prefixes = prefixes or {
            "idle": "Hero Idle",
            "up": "Hero Sing Up",
            "down": "Hero Sing Down",
            "left": "Hero Sing Left",
            "right": "Hero Sing Right",
        }
        target = root / folder
        target.mkdir(parents=True, exist_ok=True)
        (target / f"{stem}.png").write_bytes(b"png")
        (target / f"{stem}.xml").write_text(
            XML_TEMPLATE.format(image=f"{stem}.png", **prefixes)
        , newline='\n')

    def test_synthetic_infers_prefixes_and_materializes_without_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            donor = temp / "donor"
            destination = temp / "destination"
            self.make_atlas(donor, "engine/library", "Hero")
            first = self.run_fixture(donor, "Hero", destination)
            output = first.stdout + first.stderr
            self.assertEqual(first.returncode, 0, output)
            self.assertIn("RECOVERABLE=true", output)
            self.assertIn("PREFIXES=Hero Idle|Hero Sing Up|Hero Sing Down|Hero Sing Left|Hero Sing Right", output)
            self.assertIn("COPIED=3", output)
            self.assertTrue((destination / "images/custom_chars/Hero/char.png").exists())
            self.assertTrue((destination / "images/custom_chars/Hero/char.xml").exists())
            generated = destination / "images/custom_chars/Hero.hscript"
            self.assertIn("Hero Sing Left", generated.read_text())
            # A second import never replaces user/destination bytes.
            (destination / "images/custom_chars/Hero/char.png").write_bytes(b"user-owned")
            second = self.run_fixture(donor, "Hero", destination)
            output = second.stdout + second.stderr
            self.assertEqual(second.returncode, 0, output)
            self.assertEqual((destination / "images/custom_chars/Hero/char.png").read_bytes(), b"user-owned")

    def test_char_atlas_is_preferred_to_adjacent_portrait_atlas(self):
        with tempfile.TemporaryDirectory() as folder:
            donor = Path(folder) / "donor"
            self.make_atlas(donor, "images/custom_chars/Hero", "portrait")
            self.make_atlas(donor, "images/custom_chars/Hero", "char")
            result = self.run_fixture(donor, "Hero")
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn("RECOVERABLE=true", output)
            self.assertIn("char.xml", output)
            self.assertNotIn("portrait.xml +", output)

    def test_gf_atlas_only_needs_its_dance_animation(self):
        with tempfile.TemporaryDirectory() as folder:
            donor = Path(folder) / "donor"
            self.make_atlas(donor, "library", "gf", {
                "idle": "GF Dancing Beat", "up": "GF Up Note", "down": "GF Down Note",
                "left": "GF Left Note", "right": "GF Right Note",
            })
            # Remove the note frames: a GF/special actor is valid with its
            # authored dance/idle atlas and must not be reported as a missing
            # standard opponent sing set.
            xml = donor / "library/gf.xml"
            text = xml.read_text()
            text = text.replace('  <SubTexture name="GF Up Note0000" x="0" y="0" width="10" height="10"/>\n', '')
            text = text.replace('  <SubTexture name="GF Down Note0000" x="0" y="0" width="10" height="10"/>\n', '')
            text = text.replace('  <SubTexture name="GF Left Note0000" x="0" y="0" width="10" height="10"/>\n', '')
            text = text.replace('  <SubTexture name="GF Right Note0000" x="0" y="0" width="10" height="10"/>\n', '')
            xml.write_text(text, newline='\n')
            result = self.run_fixture(donor, "gf", extra=["gf"])
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn("RECOVERABLE=true", output)

    def test_synthetic_ambiguous_and_incomplete_atlases_stay_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            donor = Path(folder) / "donor"
            self.make_atlas(donor, "library/a", "Hero")
            self.make_atlas(donor, "library/b", "Hero")
            ambiguous = self.run_fixture(donor, "Hero")
            output = ambiguous.stdout + ambiguous.stderr
            self.assertEqual(ambiguous.returncode, 0, output)
            self.assertIn("RECOVERABLE=false", output)
            self.assertIn("ambiguous-character-atlas", output)

            incomplete = Path(folder) / "incomplete"
            target = incomplete / "library"
            target.mkdir(parents=True)
            (target / "Broken.png").write_bytes(b"png")
            (target / "Broken.xml").write_text(
                XML_TEMPLATE.format(
                    image="Broken.png", idle="Hero Idle", up="Hero Sing Up",
                    down="Hero Sing Down", left="Hero Sing Left", right="Missing Right"
                ).replace('name="Missing Right0000"', 'name="Something Else0000"')
            , newline='\n')
            missing = self.run_fixture(incomplete, "Broken")
            output = missing.stdout + missing.stderr
            self.assertEqual(missing.returncode, 0, output)
            self.assertIn("RECOVERABLE=false", output)
            self.assertIn("incomplete-character-atlas", output)

    def test_cache_reset_observes_changed_donor(self):
        with tempfile.TemporaryDirectory() as folder:
            donor = Path(folder) / "donor"
            self.make_atlas(donor, "engine/library", "Hero")
            xml = donor / "engine/library/Hero.xml"
            result = self.run_fixture(donor, "Hero", extra=["reset", str(xml)])
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn("RECOVERABLE=true", output)
            self.assertIn("AFTER_RECOVERABLE=false", output)

    @unittest.skipUnless(VSTRICKY.exists(), "mounted Kade fixture is unavailable")
    def test_mounted_kade_library_atlases_are_inferable(self):
        root = VSTRICKY / "assets"
        for reference in ("tricky", "TrickyMask", "exTricky"):
            result = self.run_fixture(root, reference)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn("RECOVERABLE=true", output, reference + "\n" + output)

    @unittest.skipUnless(MODPLUS.exists(), "mounted legacy fixture is unavailable")
    def test_mounted_legacy_garcello_atlas_is_inferable(self):
        result = self.run_fixture(MODPLUS / "assets", "garcello")
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("RECOVERABLE=true", output)


if __name__ == "__main__":
    unittest.main()
