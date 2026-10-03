"""Source-level coverage for isolated imported-script provenance."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
from tools.haxe_import_io_stubs import install_import_io_dependencies


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class CompatScriptManifestTest(unittest.TestCase):
    def test_namespaces_are_stable_unique_and_manifest_paths_are_bounded(self):
        main = r'''class Main {
  static function main() {
    var first = CompatScriptManifest.destinationRoot('/mods/Pack A', 'V-Slice');
    var again = CompatScriptManifest.destinationRoot('/mods/Pack A/', 'V-Slice');
    var second = CompatScriptManifest.destinationRoot('/other/Pack A', 'V-Slice');
    if (first != again) throw 'namespace is not stable';
    if (first == second) throw 'same-basename roots collided';
    if (first.indexOf('assets/imported_mods/v-slice-pack-a-') != 0)
      throw 'unexpected namespace: ' + first;

    sys.FileSystem.createDirectory('mods');
    sys.FileSystem.createDirectory('mods/Pack A');
    var relative = CompatScriptManifest.destinationRoot('mods/../mods/Pack A', 'V-Slice');
    var absolute = CompatScriptManifest.destinationRoot(Sys.getCwd() + '/mods/Pack A', 'V-Slice');
    if (relative != absolute) throw 'relative and absolute roots diverged';

    var encoded = CompatScriptManifest.stringify(
      CompatScriptManifest.create('/mods/Pack A', 'V-Slice'));
    var parsed = CompatScriptManifest.parse(encoded);
    if (parsed.roots.length != 1 || parsed.roots[0].path != first)
      throw 'round trip failed';

    var hostile = CompatScriptManifest.parse('{"roots":['
      + '{"engine":"Psych Engine","path":"../../outside"},'
      + '{"engine":"Psych Engine","path":"/absolute"},'
      + '{"engine":"Psych Engine","path":"assets/imported_mods/safe"},'
      + '{"engine":"Psych Engine","path":"assets/imported_mods/safe"}'
      + ']}');
    if (hostile.roots.length != 1
      || hostile.roots[0].path != 'assets/imported_mods/safe')
      throw 'unsafe or duplicate paths survived';

    // Path.normalize collapses a leading double slash.  Keep UNC roots
    // equivalent across native separators while keeping them distinct from
    // a POSIX path with the same server/share spelling.
    var unc = CompatScriptManifest.destinationRoot('\\\\server\\share\\Pack\\', 'V-Slice');
    var uncSlash = CompatScriptManifest.destinationRoot('//server/share/Pack/', 'V-Slice');
    var posix = CompatScriptManifest.destinationRoot('/server/share/Pack', 'V-Slice');
    if (unc != uncSlash) throw 'UNC separator normalization is unstable';
    if (unc == posix) throw 'UNC root collapsed into a POSIX root';

    var drive = CompatScriptManifest.destinationRoot('C:\\Games\\FNF\\Pack\\', 'V-Slice');
    var driveSlash = CompatScriptManifest.destinationRoot('C:/Games/FNF/Pack/', 'V-Slice');
    if (drive != driveSlash) throw 'drive separator normalization is unstable';

    var variants = CompatScriptManifest.parse('{"roots":['
      + '{"engine":"A","path":"assets/imported_mods/CasePack"},'
      + '{"engine":"B","path":"assets/imported_mods/casepack"}]}');
    #if windows
    if (variants.roots.length != 1) throw 'Windows manifest keys were not case-insensitive';
    #else
    if (variants.roots.length != 2) throw 'Linux manifest keys were case-folded';
    #end
  }
}'''
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            install_import_io_dependencies(temp)
            (temp / "CompatScriptManifest.hx").write_text(
                (ROOT / "source/CompatScriptManifest.hx").read_text()
            , newline='\n')
            (temp / "ImportSongOwnership.hx").write_text(
                (ROOT / "source/ImportSongOwnership.hx").read_text()
            , newline='\n')
            (temp / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(temp), "--run", "Main"],
                cwd=temp,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_selected_owner_precedes_legacy_roots(self):
        main = r'''class Main {
  static function main() {
    var raw = '{"roots":['
      + '{"engine":"A","path":"assets/imported_mods/a"},'
      + '{"engine":"B","path":"assets/imported_mods/b"}],'
      + '"selectedRoot":"assets/imported_mods/b"}';
    var parsed = CompatScriptManifest.parse(raw);
    if (CompatScriptManifest.selectedRoot(parsed) != 'assets/imported_mods/b')
      throw 'explicit owner was not retained';
    var ordered = CompatScriptManifest.rootsInPrecedence(parsed);
    if (ordered.length != 2 || ordered[0].path != 'assets/imported_mods/b'
      || ordered[1].path != 'assets/imported_mods/a')
      throw 'owner did not control precedence';

    var legacy = CompatScriptManifest.parse('{"roots":['
      + '{"engine":"A","path":"assets/imported_mods/a"},'
      + '{"engine":"B","path":"assets/imported_mods/b"}]}');
    if (CompatScriptManifest.selectedRoot(legacy) != 'assets/imported_mods/a')
      throw 'legacy first-root fallback changed';
  }
}'''
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            install_import_io_dependencies(temp)
            (temp / "CompatScriptManifest.hx").write_text(
                (ROOT / "source/CompatScriptManifest.hx").read_text()
            , newline='\n')
            (temp / "ImportSongOwnership.hx").write_text(
                (ROOT / "source/ImportSongOwnership.hx").read_text()
            , newline='\n')
            (temp / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(temp), "--run", "Main"],
                cwd=temp,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
