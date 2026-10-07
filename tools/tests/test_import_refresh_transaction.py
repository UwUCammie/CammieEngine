"""Exercise the shared import refresh transaction with portable Haxe fixtures."""
from haxe_test_support import HAXE_COMMAND, TEST_TMP

import hashlib
import json
import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
SOURCE = ROOT / "source"
OWNED = "assets/imported/engine/package"
OWNER = "Psych Engine|fixture-package"


FIXTURE = r'''import haxe.Json;
import haxe.crypto.Sha256;
import haxe.io.Bytes;
import ImportRefreshTransaction.ImportRefreshConflict;
import ImportRefreshTransaction.ImportRefreshManifestFile;
import ImportRefreshTransaction.ImportRefreshResult;
import ImportRefreshTransaction.ImportRefreshStagedOutput;
import sys.FileSystem;
import sys.io.File;

class ImportRefreshTransactionFixture {
  static var root:String;
  static var staging:String;
  static var state:String;
  static var owner:String = "Psych Engine|fixture-package";
  static var owned:Array<String> = ["assets/imported/engine/package"];

  static function outputs(names:Array<String>, includeDigest:Bool=true):Array<ImportRefreshStagedOutput> {
    var result:Array<ImportRefreshStagedOutput> = [];
    for (name in names) {
      var stagedPath = name + ".stage";
      var output:ImportRefreshStagedOutput = {path: owned[0] + "/" + name, stagedPath: stagedPath};
      if (includeDigest) output.sha256 = ImportSourceSnapshot.sha256File(staging + "/" + stagedPath);
      result.push(output);
    }
    return result;
  }

  static function apply(names:Array<String>, ?cancel:Void->Bool, ?progress:Dynamic->Void,
    includeDigest:Bool=true):ImportRefreshResult {
    return ImportRefreshTransaction.apply(root, staging, state, owner, owned, outputs(names,includeDigest),
      {commonRevision: 1, engineRevision: 1}, cancel, null, progress);
  }

  static function applyWithBaselines(names:Array<String>):ImportRefreshResult {
    var baselines:Array<ImportRefreshManifestFile> = [];
    for (name in names) {
      var relative = owned[0] + "/" + name;
      var installed = root + "/" + relative;
      baselines.push({path: relative, sha256: ImportSourceSnapshot.sha256File(installed), owner: owner});
    }
    return ImportRefreshTransaction.apply(root, staging, state, owner, owned, outputs(names),
      {commonRevision: 1, engineRevision: 1}, null, baselines);
  }

  static function report(status:String, conflicts:Array<ImportRefreshConflict>):Void {
    Sys.println(Json.stringify({status: status, conflicts: conflicts}));
  }

  static function reportResult(result:ImportRefreshResult):Void {
    Sys.println(Json.stringify({status: result.status, conflicts: result.conflicts,
      manifestPath: result.manifestPath, receiptPath: result.receiptPath,
      transactionPath: result.transactionPath}));
  }

  static function main():Void {
    var args = Sys.args();
    var mode = args[0];
    root = args[1];
    staging = args[2];
    state = args[3];
    switch (mode) {
      case "initial":
        var result = apply(["a.txt", "obsolete.txt"]);
        reportResult(result);
      case "initial-registry":
        reportResult(apply(["registry.json"]));
      case "baseline-registry":
        reportResult(applyWithBaselines(["registry.json"]));
      case "stale-registry-baseline":
        var baselines:Array<ImportRefreshManifestFile> = [{
          path: owned[0] + "/registry.json",
          sha256: Sha256.make(Bytes.ofString("{\"base\":true,\"new\":1}\n")).toHex(),
          owner: owner
        }];
        var result = ImportRefreshTransaction.apply(root, staging, state, owner, owned,
          outputs(["registry.json"]), {commonRevision: 1, engineRevision: 1}, null, baselines);
        reportResult(result);
      case "first-registry-baseline":
        reportResult(applyWithBaselines(["registry.json"]));
      case "refresh-registry":
        reportResult(apply(["registry.json"]));
      case "refresh":
        var result = apply(["a.txt"]);
        reportResult(result);
      case "computed-digest":
        reportResult(apply(["a.txt"], null, null, false));
      case "wrong-digest":
        // Deliberately pass a syntactically valid but incorrect caller digest.
        var mismatched:Array<ImportRefreshStagedOutput> = outputs(["a.txt"]);
        mismatched[0].sha256 = "0000000000000000000000000000000000000000000000000000000000000000";
        reportResult(ImportRefreshTransaction.apply(root, staging, state, owner, owned, mismatched,
          {commonRevision: 1, engineRevision: 1}));
      case "unchanged-progress":
        var events:Array<Dynamic> = [];
        var result = apply(["a.txt", "obsolete.txt"], null, function(event) events.push(event));
        Sys.println(Json.stringify({status: result.status, events: events}));
      case "staged-drift":
        var changed = false;
        var staged = staging + "/a.txt.stage";
        var result = apply(["a.txt"], function() {
          if (!changed) {
            changed = true;
            File.saveContent(staged, "mutated after preflight");
          }
          return false;
        });
        reportResult(result);
      case "unchanged-live-drift":
        var changed = false;
        var target = root + "/" + owned[0] + "/a.txt";
        var result = apply(["a.txt", "obsolete.txt"], function() {
          if (!changed) {
            changed = true;
            File.saveContent(target, "local edit after preflight");
          }
          return false;
        });
        reportResult(result);
      case "unchanged-staged-drift":
        var changed = false;
        var staged = staging + "/a.txt.stage";
        var result = apply(["a.txt", "obsolete.txt"], function() {
          if (!changed) {
            changed = true;
            File.saveContent(staged, "mutated after preflight");
          }
          return false;
        });
        reportResult(result);
      case "two-outputs":
        var result = apply(["a.txt", "user-added.txt"]);
        reportResult(result);
      case "cancel":
        var target = root + "/" + owned[0] + "/a.txt";
        var cancelled = false;
        var result = apply(["a.txt", "b.txt"], function() {
          if (!cancelled && FileSystem.exists(target) && File.getContent(target) == "updated a") {
            cancelled = true;
            return true;
          }
          return false;
        });
        reportResult(result);
      case "crash":
        var target = root + "/" + owned[0] + "/a.txt";
        apply(["a.txt", "b.txt"], function() {
          if (FileSystem.exists(target) && File.getContent(target) == "updated a") Sys.exit(44);
          return false;
        });
      case "recover":
        report("recovered", ImportRefreshTransaction.recover(root, state, owner));
      case "manifest":
        var manifest = ImportRefreshTransaction.loadManifest(state, owner);
        Sys.println(Json.stringify(manifest));
      case "symlink-output":
        var custom:Array<ImportRefreshStagedOutput> = [{path: owned[0] + "/linked/file.txt",
          stagedPath: "linked/file.txt.stage",
          sha256: ImportSourceSnapshot.sha256File(staging + "/linked/file.txt.stage")}];
        var customResult = ImportRefreshTransaction.apply(root, staging, state, owner, owned, custom);
        report(customResult.status, customResult.conflicts);
      case "invalid-traversal":
        var invalid:Array<ImportRefreshStagedOutput> = [{path: "assets/imported/engine/package/../../../../outside.txt",
          stagedPath: "escape.txt.stage", sha256: ImportSourceSnapshot.sha256File(staging + "/escape.txt.stage")}];
        ImportRefreshTransaction.apply(root, staging, state, owner, owned, invalid);
      case "invalid-settings":
        var invalid:Array<ImportRefreshStagedOutput> = [{path: "assets/data/options.json",
          stagedPath: "escape.txt.stage", sha256: ImportSourceSnapshot.sha256File(staging + "/escape.txt.stage")}];
        ImportRefreshTransaction.apply(root, staging, state, owner, ["assets"], invalid);
      default:
        throw "unknown fixture mode: " + mode;
    }
  }
}
'''


class ImportRefreshTransactionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HAXE.is_file():
            raise unittest.SkipTest("portable Haxe interpreter is unavailable")

    def setUp(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        # Keep Haxe's Windows interpreter fixture below MAX_PATH. The parallel
        # test runner supplies a short CAMMIE_TEST_TMP because it redirects TEMP
        # to the repository; standalone unittest runs can use the OS temp root.
        temp_root = (str(TEST_TMP) if os.environ.get("CAMMIE_TEST_TMP")
                     else (os.environ.get("TEMP") if os.name == "nt" else str(TEST_TMP)))
        self.temp = tempfile.TemporaryDirectory(dir=temp_root)
        self.addCleanup(self.temp.cleanup)
        self.scratch = Path(self.temp.name)
        self.install = self.scratch / "install"
        self.staging = self.scratch / "staging"
        self.state = self.scratch / "state"
        (self.install / OWNED).mkdir(parents=True)
        self.staging.mkdir()
        self.state.mkdir()
        self.fixture = self.scratch / "ImportRefreshTransactionFixture.hx"
        self.fixture.write_text(FIXTURE, encoding="utf-8", newline='\n')
        self.destination = self.install / OWNED
        self.settings = self.install / "assets/data/options.json"
        self.settings.parent.mkdir(parents=True)
        self.settings.write_bytes(b'{"personal":"keep"}\n')

    def stage(self, name: str, content: bytes) -> None:
        path = self.staging / (name + ".stage")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def run_fixture(self, mode: str, *, expected: int = 0, install: Path | None = None,
                    state: Path | None = None) -> subprocess.CompletedProcess:
        result = subprocess.run(
            [*HAXE_COMMAND, "-cp", str(self.scratch), "-cp", str(SOURCE), "--run", "ImportRefreshTransactionFixture",
             mode, str(install or self.install), str(self.staging), str(state or self.state)],
            cwd=ROOT,
            env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def report(self, result: subprocess.CompletedProcess) -> dict:
        return json.loads(result.stdout.strip().splitlines()[-1])

    def seed_initial_import(self) -> None:
        self.stage("a.txt", b"original a")
        self.stage("obsolete.txt", b"obsolete")
        self.assertEqual(self.report(self.run_fixture("initial"))["status"], "applied")

    def test_refresh_replaces_and_retires_only_unchanged_owned_files(self):
        self.seed_initial_import()
        user_file = self.destination / "user-added.txt"
        user_file.write_bytes(b"keep user file")
        self.stage("a.txt", b"updated a")

        result = self.report(self.run_fixture("refresh"))

        self.assertEqual(result["status"], "applied")
        self.assertEqual((self.destination / "a.txt").read_bytes(), b"updated a")
        self.assertFalse((self.destination / "obsolete.txt").exists())
        self.assertEqual(user_file.read_bytes(), b"keep user file")
        self.assertEqual(self.settings.read_bytes(), b'{"personal":"keep"}\n')
        manifest = json.loads(Path(result["manifestPath"]).read_text(encoding="utf-8"))
        self.assertEqual([entry["path"] for entry in manifest["files"]], [OWNED + "/a.txt"])
        self.assertEqual(manifest["files"][0]["owner"], OWNER)
        self.assertEqual(manifest["ownedRoots"], [OWNED])
        self.assertTrue(Path(result["receiptPath"]).is_file())
        transaction = Path(result["transactionPath"])
        self.assertFalse((transaction / "backups").exists(), "committed rollback copies should be reclaimed")

    def test_unchanged_outputs_keep_their_timestamp_and_report_transaction_progress(self):
        self.seed_initial_import()
        unchanged = self.destination / "a.txt"
        fixed_time_ns = 1_600_000_000_123_456_789
        os.utime(unchanged, ns=(fixed_time_ns, fixed_time_ns))
        before = unchanged.stat().st_mtime_ns

        result = json.loads(self.run_fixture("unchanged-progress").stdout.strip())

        self.assertEqual(result["status"], "applied")
        self.assertEqual(unchanged.read_bytes(), b"original a")
        self.assertEqual(unchanged.stat().st_mtime_ns, before,
                         "unchanged owned output should not be backed up and replaced")
        events = result["events"]
        phases = [event["phase"] for event in events]
        self.assertEqual(list(dict.fromkeys(phases)), [
            "checking-output", "checking-installed", "backing-up-import", "publishing-import"])
        expected_totals = {
            "checking-output": 2,
            "checking-installed": 2,
            "backing-up-import": 1,  # The prior manifest is backed up; unchanged files are not.
            "publishing-import": 4,  # Two guards, the manifest, and its commit receipt.
        }
        for phase, total in expected_totals.items():
            phase_events = [event for event in events if event["phase"] == phase]
            self.assertTrue(phase_events)
            self.assertTrue(all(event["total"] == total for event in phase_events), phase)
            self.assertEqual(phase_events[-1]["completed"], total, phase)
            self.assertTrue(all(event["current"] for event in phase_events if total > 0), phase)

    def test_owned_file_already_equal_to_new_output_is_accepted_without_rewrite(self):
        self.seed_initial_import()
        target = self.destination / "a.txt"
        target.write_bytes(b"repaired output")
        fixed_time_ns = 1_600_000_000_123_456_789
        os.utime(target, ns=(fixed_time_ns, fixed_time_ns))
        before = target.stat().st_mtime_ns
        self.stage("a.txt", b"repaired output")

        result = self.report(self.run_fixture("refresh"))

        self.assertEqual(result["status"], "applied")
        self.assertEqual(target.read_bytes(), b"repaired output")
        self.assertEqual(target.stat().st_mtime_ns, before,
                         "already-correct owned output should be retained in place")

    def test_transaction_computes_omitted_digest_and_rejects_explicit_mismatch(self):
        self.seed_initial_import()
        self.stage("a.txt", b"updated a")

        refreshed = self.report(self.run_fixture("computed-digest"))

        self.assertEqual(refreshed["status"], "applied")
        target = self.destination / "a.txt"
        self.assertEqual(target.read_bytes(), b"updated a")
        manifest = json.loads(Path(refreshed["manifestPath"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["files"][0]["sha256"], hashlib.sha256(b"updated a").hexdigest())

        manifest_path = Path(refreshed["manifestPath"])
        prior_manifest = manifest_path.read_bytes()
        self.stage("a.txt", b"different staged bytes")
        failed = self.run_fixture("wrong-digest", expected=1)

        self.assertIn("wrong SHA-256", failed.stderr)
        self.assertEqual(target.read_bytes(), b"updated a")
        self.assertEqual(manifest_path.read_bytes(), prior_manifest)

    def test_stale_registry_baseline_still_rejects_output_equal_to_live_bytes(self):
        registry = self.destination / "registry.json"
        registry.write_bytes(b'{"base":true}\n')
        self.stage("registry.json", b'{"base":true,"new":1}\n')
        self.assertEqual(self.report(self.run_fixture("first-registry-baseline"))["status"], "applied")
        prior_manifest = json.loads(self.run_fixture("manifest").stdout.strip())
        registry.write_bytes(b'{"base":true,"new":2}\n')
        self.stage("registry.json", b'{"base":true,"new":2}\n')

        result = self.report(self.run_fixture("stale-registry-baseline"))

        self.assertEqual(result["status"], "conflict")
        self.assertIn("merge baseline was captured", result["conflicts"][0]["reason"])
        self.assertEqual(registry.read_bytes(), b'{"base":true,"new":2}\n')
        self.assertEqual(json.loads(self.run_fixture("manifest").stdout.strip())["transactionId"],
                         prior_manifest["transactionId"])

    def test_staged_output_changed_after_preflight_is_rejected(self):
        self.seed_initial_import()
        prior_manifest = json.loads(self.run_fixture("manifest").stdout.strip())
        self.stage("a.txt", b"updated a")

        failed = self.run_fixture("staged-drift", expected=1)

        self.assertIn("Staged output changed while copying", failed.stderr)
        self.assertEqual((self.destination / "a.txt").read_bytes(), b"original a")
        self.assertEqual(json.loads(self.run_fixture("manifest").stdout.strip())["transactionId"],
                         prior_manifest["transactionId"])

    def test_unchanged_live_edit_after_preflight_is_preserved_and_aborts_commit(self):
        self.seed_initial_import()
        prior_manifest = json.loads(self.run_fixture("manifest").stdout.strip())

        failed = self.run_fixture("unchanged-live-drift", expected=1)

        self.assertIn("Installed file changed before manifest commit", failed.stderr)
        self.assertEqual((self.destination / "a.txt").read_bytes(), b"local edit after preflight")
        self.assertEqual((self.destination / "obsolete.txt").read_bytes(), b"obsolete")
        self.assertEqual(json.loads(self.run_fixture("manifest").stdout.strip())["transactionId"],
                         prior_manifest["transactionId"])

    def test_unchanged_staged_output_changed_after_preflight_aborts_commit(self):
        self.seed_initial_import()
        prior_manifest = json.loads(self.run_fixture("manifest").stdout.strip())

        failed = self.run_fixture("unchanged-staged-drift", expected=1)

        self.assertIn("Staged output changed before manifest commit", failed.stderr)
        self.assertEqual((self.destination / "a.txt").read_bytes(), b"original a")
        self.assertEqual((self.destination / "obsolete.txt").read_bytes(), b"obsolete")
        self.assertEqual(json.loads(self.run_fixture("manifest").stdout.strip())["transactionId"],
                         prior_manifest["transactionId"])

    def test_recover_reclaims_legacy_backups_after_valid_commit_receipt(self):
        self.seed_initial_import()
        self.stage("a.txt", b"updated a")
        result = self.report(self.run_fixture("refresh"))
        transaction = Path(result["transactionPath"])
        journals = sorted(transaction.glob("journal-*.json"))
        journal = json.loads(journals[-1].read_text(encoding="utf-8"))
        operation = next(item for item in journal["operations"] if item["path"] == OWNED + "/a.txt")
        backup = transaction / operation["backupPath"]
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_bytes(b"legacy committed backup")

        recovered = self.report(self.run_fixture("recover"))

        self.assertEqual(recovered["conflicts"], [])
        self.assertTrue(Path(result["receiptPath"]).is_file())
        self.assertFalse(backup.exists(), "valid committed receipt makes the old rollback copy unnecessary")

    def test_local_edits_and_unowned_destinations_return_conflicts_before_writes(self):
        self.seed_initial_import()
        edited = self.destination / "a.txt"
        edited.write_bytes(b"local edit")
        user_added = self.destination / "user-added.txt"
        user_added.write_bytes(b"local new file")
        self.stage("a.txt", b"updated a")
        self.stage("user-added.txt", b"import output")

        result = self.report(self.run_fixture("two-outputs"))

        self.assertEqual(result["status"], "conflict")
        self.assertEqual(len(result["conflicts"]), 2)
        self.assertEqual(edited.read_bytes(), b"local edit")
        self.assertEqual(user_added.read_bytes(), b"local new file")
        self.assertEqual((self.destination / "obsolete.txt").read_bytes(), b"obsolete")

    def test_validated_registry_baseline_allows_only_the_captured_live_bytes(self):
        registry = self.destination / "registry.json"
        registry.write_bytes(b'{"base":true}\n')
        self.stage("registry.json", b'{"base":true,"new":1}\n')
        first = self.report(self.run_fixture("first-registry-baseline"))
        self.assertEqual(first["status"], "applied")
        self.assertEqual(registry.read_bytes(), b'{"base":true,"new":1}\n')

        generated = self.destination / "registry.json"
        self.stage("registry.json", b'{"base":true,"new":2,"local":true}\n')
        # The merge helper supplies this exact current-live hash as the baseline.
        generated.write_bytes(b'{"base":true,"new":1,"local":true}\n')
        second = self.report(self.run_fixture("baseline-registry"))
        self.assertEqual(second["status"], "applied")
        self.assertEqual(generated.read_bytes(), b'{"base":true,"new":2,"local":true}\n')

    def test_validated_registry_baseline_does_not_authorize_a_later_live_edit(self):
        registry = self.destination / "registry.json"
        registry.write_bytes(b'{"base":true}\n')
        self.stage("registry.json", b'{"base":true,"new":1}\n')
        self.assertEqual(self.report(self.run_fixture("first-registry-baseline"))["status"], "applied")
        registry.write_bytes(b'{"base":true,"new":1,"local":true}\n')
        self.stage("registry.json", b'{"base":true,"new":2}\n')
        self.assertEqual(self.report(self.run_fixture("refresh-registry"))["status"], "conflict")
        self.assertEqual(registry.read_bytes(), b'{"base":true,"new":1,"local":true}\n')

    def test_cancellation_rolls_back_replacement_and_created_files(self):
        self.seed_initial_import()
        prior_manifest = json.loads(self.run_fixture("manifest").stdout.strip())
        self.stage("a.txt", b"updated a")
        self.stage("b.txt", b"created b")

        result = self.report(self.run_fixture("cancel"))

        self.assertEqual(result["status"], "cancelled")
        self.assertEqual((self.destination / "a.txt").read_bytes(), b"original a")
        self.assertFalse((self.destination / "b.txt").exists())
        self.assertEqual((self.destination / "obsolete.txt").read_bytes(), b"obsolete")
        self.assertEqual(json.loads(self.run_fixture("manifest").stdout.strip())["transactionId"],
                         prior_manifest["transactionId"])

    def test_recovery_rolls_back_a_process_interrupted_after_one_write(self):
        self.seed_initial_import()
        self.stage("a.txt", b"updated a")
        self.stage("b.txt", b"created b")
        crashed = self.run_fixture("crash", expected=44)
        self.assertEqual((self.destination / "a.txt").read_bytes(), b"updated a")
        self.assertFalse((self.destination / "b.txt").exists())

        recovered = self.report(self.run_fixture("recover"))

        self.assertEqual(recovered["conflicts"], [])
        self.assertEqual((self.destination / "a.txt").read_bytes(), b"original a")
        self.assertFalse((self.destination / "b.txt").exists())
        self.assertEqual((self.destination / "obsolete.txt").read_bytes(), b"obsolete")

    def test_recovery_refuses_to_replay_a_journal_after_installation_relocation(self):
        state = self.install / "import-cache/state"
        state.mkdir(parents=True)
        self.stage("a.txt", b"original a")
        self.stage("obsolete.txt", b"obsolete")
        self.assertEqual(self.report(self.run_fixture("initial", state=state))["status"], "applied")
        self.stage("a.txt", b"updated a")
        self.stage("b.txt", b"created b")
        self.run_fixture("crash", expected=44, state=state)
        self.assertEqual((self.destination / "a.txt").read_bytes(), b"updated a")

        relocated = self.scratch / "r"
        self.install.rename(relocated)
        relocated_state = relocated / "import-cache/state"
        recovered = self.report(self.run_fixture("recover", install=relocated, state=relocated_state))

        self.assertTrue(recovered["conflicts"])
        self.assertIn("install root differs", recovered["conflicts"][0]["reason"])
        self.assertEqual((relocated / OWNED / "a.txt").read_bytes(), b"updated a")
        self.assertFalse((relocated / OWNED / "b.txt").exists())

    def test_recovery_accepts_committed_receipts_after_installation_relocation(self):
        state = self.install / "import-cache/state"
        state.mkdir(parents=True)
        self.stage("a.txt", b"original a")
        self.stage("obsolete.txt", b"obsolete")
        self.assertEqual(self.report(self.run_fixture("initial", state=state))["status"], "applied")

        relocated = self.scratch / "relocated-install"
        self.install.rename(relocated)
        recovered = self.report(self.run_fixture("recover", install=relocated,
            state=relocated / "import-cache/state"))

        self.assertEqual(recovered["conflicts"], [])
        self.assertEqual((relocated / OWNED / "a.txt").read_bytes(), b"original a")

    def test_symlinked_destination_parent_is_a_conflict(self):
        outside = self.scratch / "outside"
        outside.mkdir()
        link = self.destination / "linked"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"symlink fixture unavailable: {error}")
        self.stage("linked/file.txt", b"must not escape")
        result = self.report(self.run_fixture("symlink-output"))
        self.assertEqual(result["status"], "conflict")
        self.assertFalse((outside / "file.txt").exists())

    def test_traversal_and_user_settings_targets_are_rejected(self):
        self.stage("escape.txt", b"no")
        failed = self.run_fixture("invalid-traversal", expected=1)
        self.assertIn("Unsafe path segment", failed.stderr)
        self.assertFalse((self.install.parent / "outside.txt").exists())

        failed = self.run_fixture("invalid-settings", expected=1)
        self.assertIn("cannot target the user settings file", failed.stderr)
        self.assertEqual(self.settings.read_bytes(), b'{"personal":"keep"}\n')


if __name__ == "__main__":
    unittest.main()
