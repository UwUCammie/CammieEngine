"""Coverage for engine-aware import-root discovery.

The detector is deliberately exercised through the portable Haxe interpreter:
this catches Haxe typing/target regressions while keeping the fixture small and
avoiding any dependency on the user's multi-gigabyte asset tree.
"""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
EXPECTED_DONOR_DIRS = {
    "HatsuneMiku-ProjectFunkin-V-Slice": ["v-slice/HatsuneMiku-ProjectFunkin-V-Slice"],
    "PERFEXION Demo1": ["psych/PERFEXION Demo1"],
    "DDTO++_V10_RELEASE": ["v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE"],
    "Wacky World UPDATE [V-Slice]": ["v-slice/Wacky World UPDATE [V-Slice]"],
    "Vs Tricky": ["v-slice/Vs Tricky"],
    "vs_brucedaworst_update_2_hotfix": ["psych/vs_brucedaworst_update_2_hotfix"],
    "vsfreddy_1_9_5": ["modding-plus/vsfreddy_1_9_5"],
    "HL17": ["codename/hl17_v3/mods/HL17"],
    "fnas_after_hours": ["fnas_after_hours"],
}
SOURCE_RELEASE_EVIDENCE = "Haxe source release: Project.xml + source/*.hx"
EXAMPLE_ROOT = Path("/run/media/cammie/External Storage/FNF-Example-Mods")


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


class ImportEngineRegistryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = (ROOT / "source/ImportEngine.hx").read_text()
        cls.scanner = (ROOT / "source/ImportRootScanner.hx").read_text()
        cls.settings = (ROOT / "source/ImportSettings.hx").read_text()

    def write_scanner(self, folder: Path) -> None:
        (folder / "ImportRootScanner.hx").write_text(self.scanner, newline='\n')
        (folder / "ImportDirectoryListing.hx").write_text(
            (ROOT / "source/ImportDirectoryListing.hx").read_text()
        , newline='\n')
        (folder / "PsychSongNameCompat.hx").write_text(
            (ROOT / "source/PsychSongNameCompat.hx").read_text()
        , newline='\n')

    def test_labels_are_stable_and_do_not_claim_unsupported_kate_engine(self):
        for label in (
            "Auto",
            "V-Slice",
            "Kade Engine",
            "Modding Plus",
            "Psych Engine",
            "FPS Plus",
            "Legacy FNF/Polymod",
        ):
            self.assertIn(label, self.engine)
        self.assertNotIn("Kate Engine", self.engine)
        self.assertIn("public static function normalize", self.engine)

    def test_scanner_exposes_paths_evidence_and_injected_callbacks(self):
        for field in (
            "root:String",
            "contentRoot:String",
            "engine:String",
            "confidence:Float",
            "evidence:Array<String>",
            "data:String",
            "audio:String",
            "images:String",
            "shared:String",
            "scripts:String",
            "onProgress",
            "isCancelled",
            "canonicalize",
            "identityKey",
            "shouldSkipDirectory",
        ):
            self.assertIn(field, self.scanner)
        self.assertIn("MAX_DIRECTORIES", self.scanner)
        self.assertIn("FileSystem.fullPath", self.scanner)
        self.assertIn("FileSystem.stat", self.scanner)

    def test_source_path_normalization_preserves_unc_and_drive_spellings(self):
        method = extract_method(self.settings, "public static function normalizeSourcePath")
        fixture = """import haxe.io.Path;
using StringTools;
class ImportSettings {
""" + method + r'''
  static function main() {
    var unc = ImportSettings.normalizeSourcePath('\\\\server\\share\\Pack\\');
    var uncSlash = ImportSettings.normalizeSourcePath('//server/share/Pack/');
    var posix = ImportSettings.normalizeSourcePath('/server/share/Pack');
    if (unc != uncSlash) throw 'UNC separator normalization is unstable';
    if (unc == posix) throw 'UNC root collapsed into a POSIX root';

    var drive = ImportSettings.normalizeSourcePath('C:\\Games\\FNF\\Pack\\');
    var driveSlash = ImportSettings.normalizeSourcePath('C:/Games/FNF/Pack/');
    if (drive != driveSlash) throw 'drive separator normalization is unstable';
  }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "ImportSettings.hx"
            fixture_path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "ImportSettings"],
                cwd=folder,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_scanner_canonicalize_keeps_unc_and_converts_native_separators(self):
        method = extract_method(self.scanner, "public static function canonicalize")
        fixture = """import haxe.io.Path;
import sys.FileSystem;
using StringTools;
class ImportRootScanner {
""" + method + r'''
  static function main() {
    var unc = ImportRootScanner.canonicalize('\\\\server\\share\\Pack\\');
    var uncSlash = ImportRootScanner.canonicalize('//server/share/Pack/');
    if (unc != uncSlash) throw 'scanner lost UNC separator identity';
    if (unc.indexOf('//server/share/Pack') != 0)
      throw 'scanner did not retain the UNC prefix: ' + unc;

    var nativePath = Sys.args()[0];
    var windowsSpelling = StringTools.replace(nativePath, '/', '\\');
    if (ImportRootScanner.canonicalize(nativePath)
        != ImportRootScanner.canonicalize(windowsSpelling))
      throw 'scanner native separator normalization is unstable';
  }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "ImportRootScanner.hx"
            fixture_path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "ImportRootScanner", folder],
                cwd=folder,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_scanner_normalizes_null_directory_enumeration_before_sorting(self):
        method = extract_method(self.scanner, "static function sortDirectoryEntries")
        read_directory = extract_method(self.scanner, "static function readDirectory")
        self.assertIn("!FileSystem.isDirectory(path)", read_directory)
        self.assertIn("sortDirectoryEntries(ImportDirectoryListing.normalize(FileSystem.readDirectory(path)))", read_directory)
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        codename_scan = extract_method(module, "static function discoverCodenameSongsFromBase")
        self.assertIn("ImportDirectoryListing.normalize(FileSystem.readDirectory(songsRoot))", codename_scan)
        self.assertIn("ImportDirectoryListing.normalize(FileSystem.readDirectory(audioFolder))", codename_scan)
        fixture = """import sys.FileSystem;
class ImportRootScanner {
""" + read_directory + "\n" + method + r'''
  static function main() {
    var missingPath:Array<String> = ImportRootScanner.readDirectory('missing-directory');
    if (missingPath == null || missingPath.length != 0)
      throw 'missing directory was not normalized to an empty array';
    var nullable:Array<String> = ImportDirectoryListing.normalize(null);
    if (nullable == null || nullable.length != 0)
      throw 'null native directory listing was not normalized before iteration';
    var enumerated = 0;
    for (_ in nullable) enumerated++;
    if (enumerated != 0) throw 'null listing unexpectedly produced entries';
    var missing:Array<String> = ImportRootScanner.sortDirectoryEntries(null);
    if (missing == null || missing.length != 0)
      throw 'null directory listing was not normalized to an empty array';
    var entries = ImportRootScanner.sortDirectoryEntries(['pack', 'Alpha', 'Pack']);
    if (entries.join('|') != 'Alpha|Pack|pack')
      throw 'directory sorting order changed: ' + entries.join('|');
  }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture_path = Path(folder) / "ImportRootScanner.hx"
            fixture_path.write_text(fixture, newline='\n')
            (Path(folder) / "ImportDirectoryListing.hx").write_text(
                (ROOT / "source/ImportDirectoryListing.hx").read_text()
            , newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "ImportRootScanner"],
                cwd=folder,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_synthetic_parent_finds_multiple_engine_roots_without_assets_duplicates(self):
        main = """class Main {
  static function main() {
    var roots = ImportRootScanner.scan(Sys.args()[0]);
    trace('COUNT=' + roots.length);
    for (root in roots)
      trace(root.engine + '|' + root.root + '|' + root.data + '|' + root.audio + '|' + root.images + '|' + root.shared + '|' + root.scripts);
  }
}
"""
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            (temp_path / "ImportEngine.hx").write_text(self.engine, newline='\n')
            self.write_scanner(temp_path)
            (temp_path / "Main.hx").write_text(main, newline='\n')
            parent = temp_path / "source"

            # V-Slice: modern metadata/chart pairs and a Polymod marker.
            vs = parent / "vslice"
            (vs / "data/songs/demo").mkdir(parents=True)
            (vs / "data/songs/demo/demo-metadata.json").write_text("{}", newline='\n')
            (vs / "data/songs/demo/demo-chart.json").write_text("{}", newline='\n')
            for folder in ("images", "shared", "scripts"):
                (vs / folder).mkdir()
            (vs / "_polymod_meta.json").write_text("{}", newline='\n')

            # Kade: executable marker plus the classic assets layout.
            kade = parent / "kade"
            for folder in ("data/demo", "songs/demo", "images"):
                (kade / "assets" / folder).mkdir(parents=True)
            (kade / "assets/data/demo/demo.json").write_text("{}", newline='\n')
            (kade / "assets/songs/demo/Inst.ogg").write_bytes(b"x")
            (kade / "Kade Engine.exe").write_bytes(b"x")

            # Modding Plus: its custom registry directories are stronger than
            # the generic assets/data layout.
            modplus = parent / "modplus"
            for folder in ("data/demo", "songs/demo", "images/custom_chars", "images/custom_stages", "images/custom_ui"):
                (modplus / "assets" / folder).mkdir(parents=True)
            (modplus / "assets/data/demo/demo.json").write_text("{}", newline='\n')
            (modplus / "assets/songs/demo/Inst.ogg").write_bytes(b"x")

            # Psych: direct pack/data/songs/images/characters/stages/scripts.
            psych = parent / "psych"
            for folder in ("data/demo", "songs/demo", "images", "characters", "stages", "scripts", "custom_events"):
                (psych / folder).mkdir(parents=True)
            (psych / "data/demo/demo-hard.json").write_text("{}", newline='\n')
            (psych / "songs/demo/Inst.ogg").write_bytes(b"x")
            (psych / "pack.json").write_text("{}", newline='\n')
            (psych / "scripts/demo.lua").write_text("return 0", newline='\n')

            # A chart-free Psych global pack may have no data, audio or image
            # directories. Its pack marker and scripts tree are still a valid
            # import root in Auto mode.
            global_pack = parent / "psych-global-pack"
            (global_pack / "scripts").mkdir(parents=True)
            (global_pack / "pack.json").write_text('{"runsGlobally":true}', newline='\n')
            (global_pack / "scripts/results.lua").write_text("return 0", newline='\n')

            # FPS Plus: the port metadata names its underlying engine.
            fps = parent / "fps"
            for folder in ("data/songs/demo", "songs/demo", "images"):
                (fps / folder).mkdir(parents=True)
            (fps / "data/songs/demo/demo.json").write_text("{}", newline='\n')
            (fps / "songs/demo/Inst.ogg").write_bytes(b"x")
            (fps / "meta.json").write_text('{"description":"Ported to FPS Plus"}', newline='\n')

            # Legacy FNF/Polymod: an asset manifest without the modern
            # metadata pair (the detector must not call this V-Slice).
            legacy = parent / "legacy"
            for folder in ("assets/data/demo", "assets/songs/demo", "assets/images"):
                (legacy / folder).mkdir(parents=True)
            (legacy / "assets/data/demo/demo.json").write_text("{}", newline='\n')
            (legacy / "assets/songs/demo/Inst.ogg").write_bytes(b"x")
            (legacy / "manifest/default.json").parent.mkdir()
            (legacy / "manifest/default.json").write_text("{}", newline='\n')

            # A media/build subtree is intentionally shaped like a root; it
            # must not be discovered while scanning the parent.
            skipped = parent / "unrelated" / "images" / "fake"
            skipped.mkdir(parents=True)
            (skipped / "pack.json").write_text("{}", newline='\n')
            (skipped / "data").mkdir()
            (skipped / "songs").mkdir()

            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", temp, "--run", "Main", (parent).as_posix()],
                cwd=temp,
                capture_output=True,
                text=True,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn("COUNT=7", output)
            for label in (
                "V-Slice",
                "Kade Engine",
                "Modding Plus",
                "Psych Engine",
                "FPS Plus",
                "Legacy FNF/Polymod",
            ):
                self.assertIn(label + "|", output)
            self.assertIn("psych-global-pack", output)
            self.assertEqual(output.count("Psych Engine|"), 2)
            self.assertNotIn("unrelated/images/fake", output)
            # The Kade root is reported once; its nested assets directory is
            # contentRoot, not an independent import root.
            self.assertEqual(output.count("Kade Engine|"), 1)

    def test_fresh_stronger_root_evidence_supersedes_stale_retained_engine(self):
        """Auto must repair a previously misclassified root without overriding an explicit selector."""
        main = r'''class Main {
  static function main() {
    var changed = Sys.args()[0];
    var stable = Sys.args()[1];
    var retained = new Map<String, String>();
    retained.set(changed, ImportEngine.PSYCH);
    retained.set(stable, ImportEngine.PSYCH);
    ImportRootScanner.setRetainedSourceEngines(retained);

    var rediscovered = ImportRootScanner.inspectRoot(changed, ImportEngine.AUTO);
    if (rediscovered == null || rediscovered.engine != ImportEngine.V_SLICE)
      throw 'strong current V-Slice evidence was hidden by stale retained identity';
    var explained = false;
    for (item in rediscovered.evidence)
      if (item.indexOf('superseded retained engine identity') >= 0) explained = true;
    if (!explained) throw 'engine rediscovery omitted its retained-identity explanation';

    var explicit = ImportRootScanner.inspectRoot(changed, ImportEngine.PSYCH);
    if (explicit == null || explicit.engine != ImportEngine.PSYCH)
      throw 'explicit engine selection was not preserved';

    var retainedRoot = ImportRootScanner.inspectRoot(stable, ImportEngine.AUTO);
    if (retainedRoot == null || retainedRoot.engine != ImportEngine.PSYCH)
      throw 'retained engine no longer wins when current evidence is weaker';
    trace('REDISCOVERED=' + rediscovered.engine + '|RETAINED=' + retainedRoot.engine);
  }
}'''
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            (temp_path / "ImportEngine.hx").write_text(self.engine, newline='\n')
            self.write_scanner(temp_path)
            (temp_path / "Main.hx").write_text(main, newline='\n')

            changed = temp_path / "changed-polymod"
            (changed / "data/songs/demo").mkdir(parents=True)
            (changed / "songs/demo").mkdir(parents=True)
            (changed / "shared").mkdir()
            (changed / "_polymod_meta.json").write_text("{}", newline='\n')
            (changed / "data/songs/demo/demo-metadata.json").write_text("{}", newline='\n')
            (changed / "data/songs/demo/demo-chart.json").write_text("{}", newline='\n')

            stable = temp_path / "stable-psych"
            for folder in ("data/songs/demo", "songs/demo", "images"):
                (stable / folder).mkdir(parents=True, exist_ok=True)
            (stable / "pack.json").write_text("{}", newline='\n')
            (stable / "data/songs/demo/demo.json").write_text("{}", newline='\n')

            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", temp, "--run", "Main",
                 changed.as_posix(), stable.as_posix()],
                cwd=temp,
                capture_output=True,
                text=True,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn("REDISCOVERED=V-Slice|RETAINED=Psych Engine", output)

    def test_retained_engine_beats_weak_generic_pack_and_asset_layout(self):
        main = r'''import sys.io.File;
class Main {
  static function check(value:Bool, message:String):Void if (!value) throw message;
  static function main() {
    var root = Sys.args()[0];
    var beforePack = File.getContent(root + '/pack.json');
    var beforeChart = File.getBytes(root + '/assets/data/demo/demo.json').toString();
    var beforeAudio = File.getBytes(root + '/assets/songs/demo/Inst.ogg').toString();

    var unretained = ImportRootScanner.inspectRoot(root, ImportEngine.AUTO);
    check(unretained != null && unretained.engine == ImportEngine.PSYCH,
      'fixture did not produce a weak generic Psych pack/layout hint');

    var retainedEngines = new Map<String, String>();
    retainedEngines.set(root, ImportEngine.NIGHTMARE_VISION);
    var previous = ImportRootScanner.setRetainedSourceEngines(retainedEngines);
    var retained = ImportRootScanner.inspectRoot(root, ImportEngine.AUTO);
    check(retained != null && retained.engine == ImportEngine.NIGHTMARE_VISION,
      'weak generic pack/assets evidence replaced the retained engine identity');
    var explained = false;
    for (item in retained.evidence)
      if (item.indexOf('Engine identity retained from the original source scan') >= 0)
        explained = true;
    check(explained, 'retained identity was not shown in root evidence');

    var explicit = ImportRootScanner.inspectRoot(root, ImportEngine.PSYCH);
    check(explicit != null && explicit.engine == ImportEngine.PSYCH,
      'explicit importer selection was changed by retained identity');
    ImportRootScanner.setRetainedSourceEngines(previous);

    check(File.getContent(root + '/pack.json') == beforePack
      && File.getBytes(root + '/assets/data/demo/demo.json').toString() == beforeChart
      && File.getBytes(root + '/assets/songs/demo/Inst.ogg').toString() == beforeAudio,
      'scanner changed source files while weighing retained identity');
    trace('WEAK_HINT=' + unretained.engine + '|RETAINED=' + retained.engine);
  }
}'''
        with tempfile.TemporaryDirectory() as temporary:
            temp_path = Path(temporary)
            (temp_path / "ImportEngine.hx").write_text(self.engine, newline='\n')
            self.write_scanner(temp_path)
            (temp_path / "Main.hx").write_text(main, newline='\n')

            root = temp_path / "weak-generic-pack"
            for folder in ("assets/data/demo", "assets/songs/demo", "assets/images", "assets/scripts"):
                (root / folder).mkdir(parents=True, exist_ok=True)
            (root / "pack.json").write_text("{}", newline='\n')
            (root / "assets/data/demo/demo.json").write_text("{}", newline='\n')
            (root / "assets/songs/demo/Inst.ogg").write_bytes(b"fixture audio")
            (root / "assets/scripts/script.lua").write_text("function onCreate() end", newline='\n')

            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", temp_path, "--run", "Main", root.as_posix()],
                cwd=temp_path,
                capture_output=True,
                text=True,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn("WEAK_HINT=Psych Engine|RETAINED=Nightmare Vision", output)

    def test_progress_callback_can_cancel_without_throwing(self):
        main = """class Main {
  static function main() {
    var calls = 0;
    var roots = ImportRootScanner.scan(Sys.args()[0], ImportEngine.AUTO, {
      onProgress: function(_) calls++,
      isCancelled: function() return calls > 0
    });
    trace('ROOTS=' + roots.length + '|CALLS=' + calls);
  }
}
"""
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            (temp_path / "ImportEngine.hx").write_text(self.engine, newline='\n')
            self.write_scanner(temp_path)
            (temp_path / "Main.hx").write_text(main, newline='\n')
            root = temp_path / "root"
            (root / "one").mkdir(parents=True)
            (root / "two").mkdir()
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", temp, "--run", "Main", (root).as_posix()],
                cwd=temp,
                capture_output=True,
                text=True,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn("CALLS=1", output)

    def test_bounded_scan_reports_synthetic_over_limit_without_changing_scan_api(self):
        """A small injected cap exercises the production 8192-directory guard."""
        main = """class Main {
  static function main() {
    var detailed = ImportRootScanner.scanBounded(Sys.args()[0], 2);
    if (!detailed.truncated) throw 'bounded scan did not report truncation';
    if (detailed.scannedDirectories != 2) throw 'unexpected scanned count: ' + detailed.scannedDirectories;
    if (detailed.directoryLimit != 2) throw 'unexpected bounded limit: ' + detailed.directoryLimit;
    if (detailed.queuedDirectories <= 0) throw 'truncation lost queued count';
    if (detailed.diagnostics.length != 1 || detailed.diagnostics[0].code != 'root-scan-truncated')
      throw 'root truncation diagnostic missing';
    // The compatibility API still returns only descriptors.
    var roots:Array<ImportRootScanner.ImportRoot> = ImportRootScanner.scan(Sys.args()[0]);
    trace('TRUNCATED=' + detailed.truncated + '|SCANNED=' + detailed.scannedDirectories
      + '|QUEUED=' + detailed.queuedDirectories + '|LEGACY=' + roots.length);
  }
}
"""
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            (temp_path / "ImportEngine.hx").write_text(self.engine, newline='\n')
            self.write_scanner(temp_path)
            (temp_path / "Main.hx").write_text(main, newline='\n')
            root = temp_path / "root"
            root.mkdir()
            for index in range(4):
                (root / f"candidate-{index}").mkdir()
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", temp, "--run", "Main", (root).as_posix()],
                cwd=temp,
                capture_output=True,
                text=True,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn("TRUNCATED=true|SCANNED=2", output)
            self.assertIn("|QUEUED=", output)

    def test_low_bounded_scan_does_not_claim_truncation_when_queue_is_exhausted(self):
        main = """class Main {
  static function main() {
    var detailed = ImportRootScanner.scanDetailed(Sys.args()[0], ImportEngine.AUTO, null, 1);
    if (detailed.truncated) throw 'empty low-limit scan was marked truncated';
    if (detailed.scannedDirectories != 1 || detailed.queuedDirectories != 0)
      throw 'unexpected low-limit counts';
    if (detailed.diagnostics.length != 0) throw 'unexpected low-limit diagnostic';
    trace('TRUNCATED=' + detailed.truncated + '|SCANNED=' + detailed.scannedDirectories);
  }
}
"""
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            (temp_path / "ImportEngine.hx").write_text(self.engine, newline='\n')
            self.write_scanner(temp_path)
            (temp_path / "Main.hx").write_text(main, newline='\n')
            root = temp_path / "root"
            root.mkdir()
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", temp, "--run", "Main", (root).as_posix()],
                cwd=temp,
                capture_output=True,
                text=True,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn("TRUNCATED=false|SCANNED=1", output)

    def test_vslice_pair_after_bounded_probe_window_is_still_detected(self):
        """Auto must inspect a late pair without making discovery unbounded."""
        main = """class Main {
  static function main() {
    var root = ImportRootScanner.inspectRoot(Sys.args()[0]);
    if (root == null) throw 'late V-Slice root was not detected';
    trace('ENGINE=' + root.engine);
  }
}
"""
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            (temp_path / "ImportEngine.hx").write_text(self.engine, newline='\n')
            self.write_scanner(temp_path)
            (temp_path / "Main.hx").write_text(main, newline='\n')

            # Keep the real pair after both old probe limits: the chart folder
            # sorts after 32 placeholders, and its pair sorts after 64 files.
            root = temp_path / "late-mod"
            songs = root / "data/songs"
            songs.mkdir(parents=True)
            (root / "songs").mkdir()
            for index in range(32):
                (songs / f"000-placeholder-{index:02d}").mkdir()
            late = songs / "late-song"
            late.mkdir()
            for index in range(64):
                (late / f"000-noise-{index:02d}.txt").write_text("", newline='\n')
            (late / "late-song-metadata.json").write_text("{}", newline='\n')
            (late / "late-song-chart.json").write_text("{}", newline='\n')

            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", temp, "--run", "Main", (root).as_posix()],
                cwd=temp,
                capture_output=True,
                text=True,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn("ENGINE=V-Slice", output)

    @staticmethod
    def write_haxe_source_release(base: Path, preload_layout: bool = False) -> None:
        """A minimal Kade-family source release: Project.xml + source/*.hx plus
        the standard assets layout (charts directly below assets/data, or below
        assets/preload/data for Project.xml `preload` library trees)."""
        assets = base / ("assets/preload" if preload_layout else "assets")
        (assets / "data/demo").mkdir(parents=True)
        (assets / "songs/demo").mkdir(parents=True)
        (assets / "images").mkdir(parents=True)
        (assets / "data/demo/demo.json").write_text('{"song":{"notes":[]}}', newline='\n')
        (assets / "songs/demo/Inst.ogg").write_bytes(b"x")
        (base / "source").mkdir()
        (base / "source/PlayState.hx").write_text("class PlayState {}", newline='\n')
        (base / "Project.xml").write_text("<project/>", newline='\n')

    def test_haxe_source_releases_classify_as_kade_and_incomplete_ones_are_diagnosed(self):
        main = """class Main {
  static function main() {
    var detailed = ImportRootScanner.scanDetailed(Sys.args()[0], ImportEngine.AUTO);
    for (root in detailed.roots)
      trace('ROOT|' + root.engine + '|' + root.root + '|data=' + root.data
        + '|audio=' + root.audio + '|ev=' + root.evidence.join(';'));
    for (diag in detailed.diagnostics)
      trace('DIAG|' + diag.severity + '|' + diag.code + '|' + diag.message);
    var incomplete = ImportRootScanner.inspectRoot(Sys.args()[1]);
    trace('INCOMPLETE=' + (incomplete == null ? 'null' : incomplete.engine));
    trace('DONE');
  }
}
"""
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            (temp_path / "ImportEngine.hx").write_text(self.engine, newline='\n')
            self.write_scanner(temp_path)
            (temp_path / "Main.hx").write_text(main, newline='\n')

            parent = temp_path / "source"
            classic = parent / "kade-source"
            self.write_haxe_source_release(classic)
            preload = parent / "kade-source-preload"
            self.write_haxe_source_release(preload, preload_layout=True)

            # An interrupted download: project manifest and art only, no
            # source/ and no assets/data.  Never a root, never a crash.
            incomplete = parent / "incomplete-download"
            (incomplete / "art").mkdir(parents=True)
            (incomplete / "Project.xml").write_text("<project/>", newline='\n')
            (incomplete / "Preloader.hx").write_text("class Preloader {}", newline='\n')

            # A source checkout that lost its manifest still wins over the
            # generic legacy layout instead of misclassifying.
            bare = parent / "bare-source"
            self.write_haxe_source_release(bare)
            (bare / "Project.xml").unlink()

            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", temp, "--run", "Main", (parent).as_posix(), (incomplete).as_posix()],
                cwd=temp,
                capture_output=True,
                text=True,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)

            self.assertIn("ROOT|Kade Engine|" + (classic).as_posix(), output)
            self.assertIn("ROOT|Kade Engine|" + (preload).as_posix(), output)
            self.assertIn("ROOT|Kade Engine|" + (bare).as_posix(), output)
            self.assertEqual(output.count("Haxe source release: Project.xml + source/*.hx"), 2)
            self.assertIn("Haxe source modules: source/*.hx", output)
            # Charts resolve for both layouts; audio follows the same library.
            self.assertIn("|data=" + (classic / "assets/data").as_posix() + "|", output)
            self.assertIn("|data=" + (preload / "assets/preload/data").as_posix() + "|", output)
            self.assertIn("|audio=" + (preload / "assets/preload/songs").as_posix() + "|", output)
            # The incomplete tree is skipped with an actionable diagnostic.
            self.assertIn("INCOMPLETE=null", output)
            self.assertNotIn((incomplete).as_posix(), output)
            self.assertIn(
                "DIAG|warning|source-release-incomplete|[source-release-incomplete] incomplete-download: "
                "Haxe source project detected but source/ or assets/data is missing",
                output,
            )
            self.assertIn("re-download the complete source release.", output)

    @unittest.skipUnless(
        (EXAMPLE_ROOT / "trickster-master/Project.xml").is_file(),
        "the trickster-master source-release fixture is not mounted",
    )
    def test_trickster_source_release_classifies_with_preload_chart_root(self):
        main = """class Main {
  static function main() {
    var root = ImportRootScanner.inspectRoot(Sys.args()[0]);
    if (root == null) throw 'trickster source release was not detected';
    trace('ENGINE=' + root.engine + '|DATA=' + root.data + '|EV=' + root.evidence.join(';'));
  }
}
"""
        fixture = EXAMPLE_ROOT / "trickster-master"
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            (temp_path / "ImportEngine.hx").write_text(self.engine, newline='\n')
            self.write_scanner(temp_path)
            (temp_path / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", temp, "--run", "Main", (fixture).as_posix()],
                cwd=temp,
                capture_output=True,
                text=True,
                timeout=90,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn("ENGINE=Kade Engine|", output)
            self.assertIn("DATA=" + (fixture / "assets/preload/data").as_posix(), output)
            self.assertIn(SOURCE_RELEASE_EVIDENCE, output)

    @unittest.skipUnless(EXAMPLE_ROOT.is_dir(), "the external example-mod fixture is not mounted")
    def test_actual_example_executables_choose_their_engine(self):
        main = """class Main {
  static function main() {
    for (path in Sys.args()) {
      var roots = ImportRootScanner.scan(path);
      for (root in roots)
        trace(path + '=' + root.engine + '|' + root.evidence.join(','));
    }
  }
}
"""
        paths = [
            EXAMPLE_ROOT / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice",
            EXAMPLE_ROOT / "psych/PERFEXION Demo1",
            EXAMPLE_ROOT / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE",
            EXAMPLE_ROOT / "v-slice/Wacky World UPDATE [V-Slice]",
            EXAMPLE_ROOT / "v-slice/Vs Tricky",
            EXAMPLE_ROOT / "psych/vs_brucedaworst_update_2_hotfix",
            EXAMPLE_ROOT / "modding-plus/vsfreddy_1_9_5",
            EXAMPLE_ROOT / "codename/hl17_v3/mods/HL17",
            EXAMPLE_ROOT / "fnas_after_hours",
        ]
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            (temp_path / "ImportEngine.hx").write_text(self.engine, newline='\n')
            self.write_scanner(temp_path)
            (temp_path / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", temp, "--run", "Main", *((path).as_posix() for path in paths)],
                cwd=temp,
                capture_output=True,
                text=True,
                timeout=90,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            expected = {
                "HatsuneMiku-ProjectFunkin-V-Slice": "V-Slice",
                "PERFEXION Demo1": "Psych Engine",
                "DDTO++_V10_RELEASE": "V-Slice",
                "Wacky World UPDATE [V-Slice]": "V-Slice",
                "Vs Tricky": "V-Slice",
                "vs_brucedaworst_update_2_hotfix": "Psych Engine",
                "vsfreddy_1_9_5": "Modding Plus",
                # Compiled Codename releases classify through their mods/<name>
                # content trees instead of the generic legacy layouts they
                # used to fall back to.
                "HL17": "Codename Engine",
                "fnas_after_hours": "Codename Engine",
            }
            # The mounted donor set changes as mods are added and removed;
            # verify every donor that is actually present classifies exactly.
            checked = 0
            for name, engine in expected.items():
                mounted = any((path).as_posix().find(name) >= 0 for path in paths if path.exists())
                if not mounted:
                    continue
                self.assertIn(name + "=" + engine + "|", output)
                checked += 1
            self.assertGreaterEqual(checked, 3, "too few mounted donors to validate classification")

    @unittest.skipUnless(EXAMPLE_ROOT.is_dir(), "the external example-mod fixture is not mounted")
    def test_one_parent_discovers_the_mixed_real_fixture(self):
        main = """class Main {
  static function main() {
    var roots = ImportRootScanner.scan(Sys.args()[0]);
    trace('COUNT=' + roots.length);
    for (root in roots)
      trace(root.engine + '|' + root.root);
  }
}
"""
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            (temp_path / "ImportEngine.hx").write_text(self.engine, newline='\n')
            self.write_scanner(temp_path)
            (temp_path / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", temp, "--run", "Main", (EXAMPLE_ROOT).as_posix()],
                cwd=temp,
                capture_output=True,
                text=True,
                timeout=90,
            )
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        for name in EXPECTED_DONOR_DIRS:
            # Only donors still mounted must be discovered.
            if any((EXAMPLE_ROOT / candidate).exists() for candidate in EXPECTED_DONOR_DIRS.get(name, [])):
                self.assertIn(name, output)
        # Only engines whose donor families are actually mounted must appear.
        # Compiled Codename releases used to fill the Kade/Legacy slots through
        # their generic layouts; they now classify as Codename Engine.
        engines_with_mounted_donors = {
            "V-Slice": (EXAMPLE_ROOT / "v-slice").is_dir(),
            "Kade Engine": False,
            "Modding Plus": (EXAMPLE_ROOT / "modding-plus").is_dir(),
            "Psych Engine": (EXAMPLE_ROOT / "psych").is_dir(),
            "Legacy FNF/Polymod": False,
            "Codename Engine": ((EXAMPLE_ROOT / "codename").is_dir()
                                or (EXAMPLE_ROOT / "fnas_after_hours").is_dir()),
        }
        for engine, mounted in engines_with_mounted_donors.items():
            if mounted:
                self.assertIn(engine + "|", output)


if __name__ == "__main__":
    unittest.main()
