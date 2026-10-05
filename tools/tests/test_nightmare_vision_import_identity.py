"""Nightmare Vision has a distinct, bounded import identity from Psych."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import json
import subprocess
import tempfile
import unittest
from tools.haxe_import_io_stubs import install_import_io_dependencies


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class NightmareVisionImportIdentityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = (ROOT / "source/ImportEngine.hx").read_text()
        cls.scanner = (ROOT / "source/ImportRootScanner.hx").read_text()

    def run_scan(self, *paths):
        main = r'''class Main {
  static function main() {
    if (ImportEngine.names().indexOf(ImportEngine.NIGHTMARE_VISION) < 0)
      throw "Nightmare Vision missing from engine selector";
    for (path in Sys.args()) {
      var root = ImportRootScanner.inspectRoot(path);
      if (root == null) trace("MISSING|" + path);
      else trace("ROOT|" + root.engine + "|" + root.root + "|DATA=" + root.data
        + "|AUDIO=" + root.audio + "|" + root.evidence.join(";"));
    }
  }
}
'''
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            (work / "ImportEngine.hx").write_text(self.engine, newline='\n')
            (work / "ImportRootScanner.hx").write_text(self.scanner, newline='\n')
            (work / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            (work / "PsychSongNameCompat.hx").write_text(
                (ROOT / "source/PsychSongNameCompat.hx").read_text()
            , newline='\n')
            (work / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", temp, "--run", "Main", *((path).as_posix() for path in paths)],
                cwd=temp,
                capture_output=True,
                text=True,
                timeout=60,
            )
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        return output

    def test_nmv_package_marker_wins_over_psych_derived_source_shape(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "nmv-source"
            (project / "source/psychlua").mkdir(parents=True)
            (project / "source/psychlua/FunkinLua.hx").write_text("class FunkinLua {}", newline='\n')
            (project / "Project.xml").write_text(
                '<project><app packageName="com.nmvTeam.nightmareEngine" '
                'package="com.nmvTeam.nightmareEngine" /></project>'
            , newline='\n')
            output = self.run_scan(project)

        self.assertIn("ROOT|Nightmare Vision|", output)
        self.assertIn("Nightmare Vision Haxe project package: com.nmvTeam.nightmareEngine", output)

    def test_nmv_chart_format_is_authoritative_without_project_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "nmv-chart-pack"
            chart_folder = root / "assets/data/demo/charts"
            chart_folder.mkdir(parents=True)
            (root / "assets/songs/demo").mkdir(parents=True)
            (chart_folder / "normal.json").write_text(
                json.dumps({"song": {"format": "nmv2", "notes": []}})
            , newline='\n')
            output = self.run_scan(root)

        self.assertIn("ROOT|Nightmare Vision|", output)
        self.assertIn("Nightmare Vision chart metadata: format=nmv2", output)

    def test_selected_content_package_inherits_nmv_identity_from_parent(self):
        with tempfile.TemporaryDirectory() as temp:
            game = Path(temp) / "arbitrary-game-root"
            game.mkdir()
            (game / "Project.xml").write_text(
                '<project><app packageName="com.nmvTeam.nightmareEngine" /></project>'
            , newline='\n')
            package = game / "content/unbranded-package"
            song = package / "songs/authored-id"
            (song / "data").mkdir(parents=True)
            (song / "audio").mkdir()
            (song / "data/normal.json").write_text(
                json.dumps({"song": {"song": "Display Name", "notes": []}})
            , newline='\n')
            (song / "audio/Inst.ogg").write_bytes(b"inst")
            output = self.run_scan(package)

        self.assertIn(
            f"ROOT|Nightmare Vision|{package}|DATA={package / 'songs'}|AUDIO={package / 'songs'}|",
            output,
        )
        self.assertIn(
            "Nested content package inherits Nightmare Vision identity from its parent game root",
            output,
        )

    def test_unowned_nested_pack_uses_bounded_nmv_chart_format_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / "arbitrary-pack"
            chart = package / "songs/authored-id/data/normal.json"
            chart.parent.mkdir(parents=True)
            (package / "songs/authored-id/audio").mkdir()
            chart.write_text(json.dumps({"song": {"format": "nmv2", "notes": []}}), newline='\n')
            output = self.run_scan(package)

        self.assertIn(f"ROOT|Nightmare Vision|{package}|DATA={package / 'songs'}|", output)
        self.assertIn(
            "Nightmare Vision nested chart metadata: format=nmv2 in songs/<song>/data",
            output,
        )

    def test_psych_songdata_layout_scores_as_psych_and_finds_nested_lua(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "psych-songdata-pack"
            chart_folder = root / "assets/data/songData/all-stars"
            chart_folder.mkdir(parents=True)
            audio_folder = root / "assets/songs/all-stars"
            audio_folder.mkdir(parents=True)
            (audio_folder / "Inst.ogg").write_bytes(b"audio")
            (chart_folder / "all-stars.json").write_text(
                json.dumps({"song": {"song": "All-Stars", "bpm": 128, "notes": []}})
            , newline='\n')
            (chart_folder / "script.lua").write_text("function onCreate() end", newline='\n')
            output = self.run_scan(root)

        self.assertIn("ROOT|Psych Engine|", output)
        self.assertIn("Psych Engine chart layout: data/songData/<song>/*.json", output)
        self.assertIn("Psych Engine Lua chart/script content", output)

    def test_compatibility_namespaces_keep_engine_identity_in_path(self):
        source = (ROOT / "source/CompatScriptManifest.hx").read_text()
        normalize_source = extract_method(source, "static function normalizeSource")
        slug = extract_method(source, "static function slug")
        namespace = extract_method(source, "public static function namespaceFor")
        fixture = """import haxe.crypto.Md5;
import haxe.io.Path;
import sys.FileSystem;
using StringTools;
class ImportSongOwnership {
  public static function priorNamespace(sourceRoot:String, engine:String, legacy:String):String
    return legacy;
}
class CompatScriptManifest {
  static inline var ROOT_PREFIX:String = 'assets/imported_mods';
""" + normalize_source + "\n" + slug + "\n" + namespace + r'''
  static function main() {
    var psych = CompatScriptManifest.namespaceFor('/mods/shared-root', 'Psych Engine');
    var nmv = CompatScriptManifest.namespaceFor('/mods/shared-root', 'Nightmare Vision');
    if (psych == nmv) throw 'NMV reused Psych owner path';
    if (psych.indexOf('psych-engine-') != 0 || nmv.indexOf('nightmare-vision-') != 0)
      throw 'engine labels missing from owner paths: ' + psych + ' / ' + nmv;
  }
}
'''
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            install_import_io_dependencies(work)
            (work / "CompatScriptManifest.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", temp, "--run", "CompatScriptManifest"],
                cwd=temp,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
