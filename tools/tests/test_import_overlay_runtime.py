"""Destination-side tests for the bounded Polymod overlay transaction."""
from haxe_test_support import HAXE_COMMAND

import hashlib
import json
import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
TMP_ROOT = ROOT / "tmp"
EXAMPLES = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
SEO_ROOT = EXAMPLES / "SeoS"
TAKEOVER_ROOT = EXAMPLES / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE"
HAXE = ROOT / ".tools/haxe/haxe"


RUNTIME_FIXTURE = r'''import haxe.Json;
import haxe.crypto.Md5;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
import ImportOverlayPlanner.ImportOverlaySummary;

using StringTools;

class Main {
  static function fail(message:String):Void throw message;
  static function hasDiagnostic(summary:ImportOverlaySummary, needle:String):Bool {
    if (summary == null || summary.diagnostics == null) return false;
    for (message in summary.diagnostics)
      if (message != null && message.indexOf(needle) >= 0) return true;
    return false;
  }
  static function main() {
    var mode = Sys.args()[0];
    if (mode == "paths") {
      var assets = ImportOverlayPath.canonicalPath("assets");
      var missing = Path.join([assets, "data/players/pico.json"]);
      var linked = Path.join([assets, "data/linked/pico.json"]);
      var linkedParent = assets + "/data/linked/../pico.json";
      if (!ImportOverlayPath.withinRoot(assets, missing))
        fail("missing destination path escaped assets: " + ImportOverlayPath.canonicalPath(missing));
      if (ImportOverlayPath.withinRoot(assets, linked))
        fail("symlinked destination path escaped containment check");
      if (ImportOverlayPath.withinRoot(assets, linkedParent))
        fail("symlink followed by parent traversal escaped containment check");
      return;
    }
    if (mode == "aggregate") {
      var total = 0;
      for (candidate in Sys.args().slice(1)) {
        var aggregatePlan = ImportOverlayPlanner.plan(candidate);
        if (aggregatePlan.diagnostics.length != 0)
          fail("aggregate diagnostics for " + candidate);
        total += aggregatePlan.entries.length;
      }
      if (total != 2) fail("aggregate planned entries: " + total);
      return;
    }
    var root = Sys.args()[1];
    var plan = ImportOverlayPlanner.plan(root);
    var contentRoot = mode == "takeover" ? root : Path.join([root, "assets"]);
    var mount = ImportOverlayRuntime.mount(root, contentRoot, "fixture", plan);
    if (mode == "rollback") {
      var second = StringTools.replace(FileSystem.fullPath("assets"), "\\", "/") + "/data/second.txt";
      var collision = second + ".overlay-" + Md5.encode(second).substr(0, 12) + ".tmp";
      if (!FileSystem.exists(collision)) fail("collision not visible: " + collision);
    }
    var summary = ImportOverlayRuntime.apply([mount], "assets");
    if (mode == "synthetic") {
      if (summary.planned != 3 || summary.applied != 3 || summary.retained != 0)
        fail("synthetic summary: " + summary.planned + "/" + summary.applied + "/" + summary.retained);
      if (File.getBytes("assets/data/intro.txt").toString() != "base\n+tail")
        fail("synthetic append bytes");
      if (File.getBytes("assets/data/replaced.bin").toString() != "replacement")
        fail("synthetic replace bytes");
      var merged:Dynamic = Json.parse(File.getContent("assets/data/config.json"));
      if (merged.ownedChars.length != 2 || merged.ownedChars[1] != "pico-doki")
        fail("synthetic merge semantics");
    } else if (mode == "rollback") {
      if (summary.applied != 0 || summary.retained < 2
        || !hasDiagnostic(summary, "overlay-transaction-rollback"))
        fail("rollback summary: " + summary.planned + "/" + summary.applied + "/"
          + summary.retained + "/" + summary.diagnostics.join("|"));
      if (FileSystem.exists("assets/data/first.txt") || FileSystem.exists("assets/data/second.txt"))
        fail("rollback left a destination file");
    } else if (mode == "traversal") {
      if (summary.planned != 1 || summary.skipped != 1
        || !hasDiagnostic(summary, "overlay-unsupported-target"))
        fail("unsupported target summary");
      if (FileSystem.exists("assets/outside.txt")) fail("unsupported target materialized");
    } else if (mode == "seos") {
      if (summary.planned != 1 || summary.applied != 1 || summary.retained != 0)
        fail("SeoS summary");
      var base = File.getBytes(Path.join([root, "assets/data/introText.txt"])).toString();
      var append = File.getBytes(Path.join([root, "mods/introMod/_append/data/introText.txt"])).toString();
      if (File.getBytes("assets/data/introText.txt").toString() != base + append)
        fail("SeoS imported introText");
    } else if (mode == "takeover") {
      if (summary.planned != 1 || summary.applied != 0 || summary.retained != 1)
        fail("TAKEOVER summary");
      if (summary.retainedPatches.length != 1
        || summary.retainedPatches[0].reason != "missing-merge-base"
        || summary.retainedPatches[0].relativePath != "data/players/pico.json"
        || summary.retainedPatches[0].payload.indexOf("ownedChars") < 0)
        fail("TAKEOVER retained patch");
      if (FileSystem.exists("assets/data/players/pico.json"))
        fail("TAKEOVER fabricated a missing base");
    } else if (mode == "protected") {
      if (summary.applied != 0 || summary.retained != 1 || summary.retainedPatches.length != 1)
        fail("protected summary");
      if (!summary.retainedPatches[0].payload.startsWith("base64:"))
        fail("binary replacement was not encoded safely: " + summary.retainedPatches[0].payload);
      if (File.getBytes("assets/data/replaced.bin").toString() != "old")
        fail("protected destination was modified");
    }
  }
}'''


class ImportOverlayRuntimeTest(unittest.TestCase):
    def run_fixture(self, mode: str, root: Path, prepare=None) -> subprocess.CompletedProcess:
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as folder:
            folder_path = Path(folder)
            (folder_path / "Main.hx").write_text(RUNTIME_FIXTURE, newline='\n')
            if prepare is not None:
                prepare(folder_path)
            env = os.environ.copy()
            env["TMPDIR"] = str(TMP_ROOT)
            return subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(folder_path),
                 "--run", "Main", mode, str(root)],
                cwd=folder_path,
                capture_output=True,
                text=True,
                env=env,
            )

    def test_missing_targets_are_contained_and_symlink_ancestors_are_resolved(self):
        def prepare(workspace: Path):
            (workspace / "assets/data").mkdir(parents=True)
            outside = workspace / "outside"
            outside.mkdir()
            (workspace / "assets/data/linked").symlink_to(outside, target_is_directory=True)

        result = self.run_fixture("paths", Path("unused"), prepare)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_synthetic_operations_materialize_transactionally(self):
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as folder:
            root = Path(folder) / "donor"
            (root / "assets/data").mkdir(parents=True)
            (root / "mods/fixture/_append/data").mkdir(parents=True)
            (root / "mods/fixture/_replace/data").mkdir(parents=True)
            (root / "mods/fixture/_merge/data").mkdir(parents=True)
            (root / "mods/modList.txt").write_text("fixture\n", newline='\n')
            (root / "assets/data/intro.txt").write_bytes(b"base\n")
            (root / "assets/data/config.json").write_text('{"ownedChars":["bf"]}', newline='\n')
            (root / "mods/fixture/_append/data/intro.txt").write_bytes(b"+tail")
            (root / "mods/fixture/_replace/data/replaced.bin").write_bytes(b"replacement")
            (root / "mods/fixture/_merge/data/config.json").write_text(
                '[{"op":"add","path":"/ownedChars/-","value":"pico-doki"}]'
            , newline='\n')
            before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
            result = self.run_fixture("synthetic", root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(before, {path: path.read_bytes() for path in root.rglob("*") if path.is_file()})

    def test_transaction_rolls_back_all_new_files_on_commit_failure(self):
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as folder:
            root = Path(folder) / "donor"
            (root / "_replace/data").mkdir(parents=True)
            (root / "_replace/data/first.txt").write_text("first", newline='\n')
            (root / "_replace/data/second.txt").write_text("second", newline='\n')

            def prepare(workspace: Path):
                destination = workspace / "assets/data/second.txt"
                destination.parent.mkdir(parents=True)
                digest = hashlib.md5(str(destination.resolve()).encode()).hexdigest()[:12]
                (destination.parent / (destination.name + ".overlay-" + digest + ".tmp")).write_text("collision", newline='\n')

            result = self.run_fixture("rollback", root, prepare)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_non_data_target_is_diagnosed_and_not_written(self):
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as folder:
            root = Path(folder) / "donor"
            (root / "_replace").mkdir(parents=True)
            (root / "_replace/outside.txt").write_text("outside", newline='\n')
            result = self.run_fixture("traversal", root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_existing_binary_target_retention_is_base64_safe(self):
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as folder:
            root = Path(folder) / "donor"
            (root / "_replace/data").mkdir(parents=True)
            (root / "_replace/data/replaced.bin").write_bytes(b"\x00\xffA")

            def prepare(workspace: Path):
                destination = workspace / "assets/data/replaced.bin"
                destination.parent.mkdir(parents=True)
                destination.write_bytes(b"old")

            result = self.run_fixture("protected", root, prepare)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(EXAMPLES.is_dir(), "mounted FNF-Example-Mods corpus is unavailable")
    def test_mounted_overlay_inventory_is_planned_in_aggregate(self):
        # The overlay donors still mounted in the library.  (SeoS, the old
        # vstricky Kade release, and the HellBeats engine install left the
        # library; their transaction coverage is skipped below.)
        roots = [
            EXAMPLES / "modding-plus/vsfreddy_1_9_5",
            TAKEOVER_ROOT,
        ]
        if not all(root.is_dir() for root in roots):
            self.skipTest("one or more mounted overlay roots are unavailable")
        # run_fixture's single-root API is intentionally kept for the
        # transaction tests; invoke the same fixture directly for this
        # aggregate read-only audit.
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as folder:
            folder_path = Path(folder)
            (folder_path / "Main.hx").write_text(RUNTIME_FIXTURE, newline='\n')
            env = os.environ.copy()
            env["TMPDIR"] = str(TMP_ROOT)
            aggregate = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(folder_path),
                 "--run", "Main", "aggregate", *(str(root) for root in roots)],
                cwd=folder_path,
                capture_output=True,
                text=True,
                env=env,
            )
        self.assertEqual(aggregate.returncode, 0, aggregate.stdout + aggregate.stderr)

    @unittest.skipUnless(SEO_ROOT.is_dir(), "mounted FNF-Example-Mods/SeoS is unavailable")
    def test_mounted_seos_append_is_materialized_without_donor_mutation(self):
        base_path = SEO_ROOT / "assets/data/introText.txt"
        append_path = SEO_ROOT / "mods/introMod/_append/data/introText.txt"
        before = {base_path: base_path.read_bytes(), append_path: append_path.read_bytes()}
        result = self.run_fixture("seos", SEO_ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(before, {base_path: base_path.read_bytes(), append_path: append_path.read_bytes()})

    @unittest.skipUnless(TAKEOVER_ROOT.is_dir(), "mounted TAKEOVER V-Slice root is unavailable")
    def test_mounted_takeover_patch_is_retained_without_fabricating_base(self):
        patch_path = TAKEOVER_ROOT / "_merge/data/players/pico.json"
        before = patch_path.read_bytes()
        result = self.run_fixture("takeover", TAKEOVER_ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(before, patch_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
