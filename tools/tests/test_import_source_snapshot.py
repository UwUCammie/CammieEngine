"""Raw-source snapshots are bounded, isolated, and receipt-backed."""
from haxe_test_support import HAXE_COMMAND
import hashlib
import json
import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"

MAIN = r'''
import ImportSourceSnapshot.ImportSourceSnapshotOptions;
class Main {
 static function main():Void {
  var config:Dynamic = haxe.Json.parse(sys.io.File.getContent("config.json"));
  var copyProgress = 0;
  var options:ImportSourceSnapshotOptions = {
   chunkSize: 4096,
   unresolvedDependencies: config.dependencies,
   onProgress: function(progress) {
    if (progress.phase == "copy" && progress.bytesCompleted > 0) copyProgress++;
   },
   cancelled: function() return config.cancelAfterCopy && copyProgress > 0
  };
  var captured = ImportSourceSnapshot.capture(config.source, config.cache, config.engine,
   config.applicationVersion, options);
  var assessment:Dynamic = null;
  if (captured.receiptPath != "") assessment = ImportSourceSnapshot.assessReceipt(captured.receiptPath, config.engine);
  var legacyStatus = "";
  if (config.legacyReceipt != null) legacyStatus = ImportSourceSnapshot.assessReceipt(config.legacyReceipt, config.engine).status;
  var staleSchemaStatus = "";
  if (config.staleSchemaReceipt != null) staleSchemaStatus = ImportSourceSnapshot.assessReceipt(config.staleSchemaReceipt, config.engine).status;
  sys.io.File.saveContent("result.json", haxe.Json.stringify({capture:captured,
   assessment:assessment, legacyStatus:legacyStatus, staleSchemaStatus:staleSchemaStatus, copyProgress:copyProgress}));
 }
}'''

VERIFY_MAIN = r'''import haxe.Json;
class VerifyMain {
 static function main():Void {
  var args = Sys.args();
  try {
   ImportSourceSnapshot.verify(args[0], args[1]);
   Sys.println(Json.stringify({ok:true, error:""}));
  } catch (error:Dynamic) {
   Sys.println(Json.stringify({ok:false, error:Std.string(error)}));
  }
 }
}'''


class ImportSourceSnapshotTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "tmp")
        self.base = Path(self.temp.name)
        self.main = self.base / "Main.hx"
        self.main.write_text(MAIN, newline='\n')

    def tearDown(self):
        self.temp.cleanup()

    def run_capture(self, source, cache, *, cancel=False, legacy_receipt=None, dependencies=None, timeout=90):
        (self.base / "config.json").write_text(json.dumps({
            "source": str(source), "cache": str(cache), "engine": "Psych Engine",
            "applicationVersion": "0.0.9", "cancelAfterCopy": cancel,
            "legacyReceipt": None if legacy_receipt is None else str(legacy_receipt),
            "staleSchemaReceipt": str(self.base / "stale-schema.json") if (self.base / "stale-schema.json").exists() else None,
            "dependencies": dependencies,
        }), newline='\n')
        process = subprocess.run(
            [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(self.base), "--run", "Main"],
            cwd=self.base, text=True, capture_output=True, timeout=timeout,
        )
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        return json.loads((self.base / "result.json").read_text())

    def verify_snapshot(self, snapshot, snapshot_id):
        fixture = self.base / "VerifyMain.hx"
        fixture.write_text(VERIFY_MAIN, encoding="utf-8", newline='\n')
        process = subprocess.run(
            [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(self.base), "--run", "VerifyMain",
             str(snapshot), snapshot_id],
            cwd=self.base, text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        return json.loads(process.stdout.strip().splitlines()[-1])

    @staticmethod
    def tree_fingerprint(root):
        result = {}
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                result[relative] = ("symlink", os.readlink(path))
            elif path.is_dir():
                result[relative] = ("directory",)
            else:
                result[relative] = ("file", path.read_bytes())
        return result

    def test_copies_unknown_files_and_empty_dirs_omits_native_payloads_without_touching_donor(self):
        donor = self.base / "Donor"
        cache = self.base / "Cache"
        (donor / "Assets" / "Empty Folder").mkdir(parents=True)
        (donor / "Assets" / "One.HXC").write_bytes(b"chart-like authored source\x00\xff")
        (donor / "README.strange-extension").write_text("unknown files are retained", newline='\n')
        (donor / "archive.so.notes").write_text("not a versioned shared library", newline='\n')
        (donor / "mesh.obj").write_text("v 0.0 0.0 0.0\nv 1.0 0.0 0.0\nf 1 2 1\n", newline='\n')
        (donor / "receipt.json").write_text("donor-owned raw file", newline='\n')
        (donor / ".receipt.tmp").write_bytes(b"donor temporary-looking source bytes")
        if os.name != "nt":
            (donor / "authored\\backslash.data").write_text("POSIX backslash is a filename character", newline='\n')
        (donor / "payload.DLL").write_bytes(b"extension marked native")
        (donor / "sneaky.data").write_bytes(b"\x7fELF" + b"\x00" * 120)
        java_class = bytes.fromhex(
            "cafebabe000000340005010001410700010100106a6176612f6c616e672f4f626a656374"
            "07000300210002000400000000000000000000") + (b"\x00" * 4096)
        self.assertGreaterEqual(len(java_class), 4096)
        (donor / "Dependency.class").write_bytes(java_class)
        (donor / "universal.macho").write_bytes(bytes.fromhex(
            "cafebabe0000000100000007000000030000001c0000000400000002feedface"))
        pe = bytearray(256)
        pe[:2] = b"MZ"
        struct.pack_into("<I", pe, 0x3C, 0x80)
        pe[0x80:0x84] = b"PE\x00\x00"
        (donor / "hidden-native.unknown").write_bytes(pe)
        before = self.tree_fingerprint(donor)

        result = self.run_capture(donor, cache)
        captured = result["capture"]
        self.assertEqual(captured["status"], "complete", captured)
        self.assertTrue(captured["complete"])
        self.assertEqual(before, self.tree_fingerprint(donor), "capture modified donor files or layout")
        snapshot = Path(captured["snapshotRoot"])
        receipt = json.loads(Path(captured["receiptPath"]).read_text())
        self.assertEqual(receipt["snapshotSchemaVersion"], 1)
        self.assertEqual(receipt["contentRoot"], "content")
        self.assertNotIn(str(donor), Path(captured["receiptPath"]).read_text(),
                         "receipt must not retain an absolute donor path")
        self.assertEqual(result["assessment"]["status"], "current")
        files = {entry["path"]: entry for entry in receipt["files"]}
        self.assertIn("Assets/One.HXC", files, "source case or unknown extension was lost")
        self.assertIn("README.strange-extension", files, "unknown extension was filtered")
        self.assertIn("archive.so.notes", files, "a nonnumeric .so suffix was mistaken for a native library")
        self.assertIn("mesh.obj", files, "authored Wavefront meshes must be retained")
        self.assertIn("Dependency.class", files, "Java class magic alone must not imply a fat Mach-O")
        if os.name != "nt":
            self.assertIn("authored\\backslash.data", files, "a valid POSIX filename was treated as a path separator")
        self.assertEqual((snapshot / "content/Assets/One.HXC").read_bytes(), (donor / "Assets/One.HXC").read_bytes())
        self.assertTrue((snapshot / "content/Assets/Empty Folder").is_dir())
        self.assertEqual((snapshot / "content/receipt.json").read_text(), "donor-owned raw file")
        self.assertEqual((snapshot / "content/.receipt.tmp").read_bytes(), b"donor temporary-looking source bytes")
        self.assertNotEqual((snapshot / "receipt.json").read_bytes(), (snapshot / "content/receipt.json").read_bytes())
        self.assertTrue(any(entry["path"] == "payload.DLL" for entry in receipt["exclusions"]))
        self.assertTrue(any(entry["detectedHeader"] == "elf" for entry in receipt["exclusions"]))
        self.assertTrue(any(entry["detectedHeader"] == "pe" for entry in receipt["exclusions"]))
        self.assertTrue(any(entry["path"] == "universal.macho" and entry["detectedHeader"] == "mach-o-fat"
                            for entry in receipt["exclusions"]))
        self.assertNotIn("payload.DLL", files)
        self.assertNotIn("sneaky.data", files)
        self.assertNotIn("hidden-native.unknown", files)
        for relative, entry in files.items():
            self.assertEqual(hashlib.sha256((snapshot / "content" / relative).read_bytes()).hexdigest(), entry["sha256"])
            self.assertNotEqual(os.stat(snapshot / "content" / relative).st_ino, os.stat(donor / relative).st_ino,
                                "snapshot content must be copied, not hardlinked")
        self.assertEqual([entry.name for entry in cache.iterdir()], [captured["snapshotId"]])
        self.assertTrue(self.verify_snapshot(snapshot, captured["snapshotId"])["ok"])

    def test_verification_rejects_tampering_and_tree_drift(self):
        donor = self.base / "VerifyDonor"
        cache = self.base / "VerifyCache"
        (donor / "nested" / "empty").mkdir(parents=True)
        source_file = donor / "nested" / "payload.bin"
        source_file.write_bytes(b"authentic-payload")
        captured = self.run_capture(donor, cache)["capture"]
        snapshot = Path(captured["snapshotRoot"])
        content = snapshot / "content"
        payload = content / "nested" / "payload.bin"
        original = payload.read_bytes()
        snapshot_id = captured["snapshotId"]
        self.assertTrue(self.verify_snapshot(snapshot, snapshot_id)["ok"])

        payload.write_bytes(b"modified--payload")
        self.assertFalse(self.verify_snapshot(snapshot, snapshot_id)["ok"])
        payload.write_bytes(original)

        (content / "unexpected.txt").write_text("extra", encoding="utf-8", newline='\n')
        self.assertFalse(self.verify_snapshot(snapshot, snapshot_id)["ok"])
        (content / "unexpected.txt").unlink()

        payload.unlink()
        self.assertFalse(self.verify_snapshot(snapshot, snapshot_id)["ok"])
        payload.write_bytes(original)
        self.assertFalse(self.verify_snapshot(snapshot, "0" * 64)["ok"])

        receipt_path = snapshot / "receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["files"][0]["sha256"] = "0" * 64
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8", newline='\n')
        self.assertFalse(self.verify_snapshot(snapshot, snapshot_id)["ok"])

    def test_cancelled_copy_cleans_only_its_staging_tree(self):
        donor = self.base / "Donor"
        cache = self.base / "Cache"
        donor.mkdir()
        (donor / "large.rawsource").write_bytes(b"A" * (1024 * 1024))
        sentinel = cache / "keep.txt"
        cache.mkdir()
        sentinel.write_text("caller-owned cache content", newline='\n')

        result = self.run_capture(donor, cache, cancel=True)["capture"]
        self.assertEqual(result["status"], "cancelled", result)
        self.assertFalse(result["complete"])
        self.assertEqual(sentinel.read_text(), "caller-owned cache content")
        self.assertEqual(sorted(path.name for path in cache.iterdir()), ["keep.txt"])

    @unittest.skipUnless(hasattr(os, "mkfifo"), "named pipes are unavailable on this platform")
    def test_special_files_are_reported_without_opening_fifo(self):
        donor = self.base / "SpecialDonor"
        cache = self.base / "SpecialCache"
        donor.mkdir()
        (donor / "regular.txt").write_text("regular content", encoding="utf-8", newline='\n')
        fifo = donor / "events.pipe"
        os.mkfifo(fifo)

        # Haxe's eval filesystem backend reports permission bits only (it drops
        # S_IFIFO), so it cannot exercise the native node-type guard safely.
        mode_fixture = self.base / "FileModeFixture.hx"
        mode_fixture.write_text(
            'class FileModeFixture { static function main() '
            '{ Sys.println(sys.FileSystem.stat(Sys.args()[0]).mode); } }',
            encoding="utf-8",
         newline='\n')
        mode_result = subprocess.run(
            [*HAXE_COMMAND, "-cp", str(self.base), "--run", "FileModeFixture", str(fifo)],
            cwd=self.base, text=True, capture_output=True, timeout=10,
        )
        self.assertEqual(mode_result.returncode, 0, mode_result.stdout + mode_result.stderr)
        if int(mode_result.stdout.strip()) & 0xF000 != 0x1000:
            self.skipTest("this Haxe backend omits filesystem node-type bits")

        result = self.run_capture(donor, cache, timeout=8)["capture"]
        self.assertEqual(result["status"], "incomplete", result)
        self.assertFalse(result["complete"])
        self.assertIn("special-filesystem-node-fifo:events.pipe", result["incompleteReasons"])
        self.assertTrue(any(item["path"] == "events.pipe"
                            and item["reason"] == "special-filesystem-node-fifo"
                            for item in result["omissions"]))
        snapshot = Path(result["snapshotRoot"])
        self.assertTrue((snapshot / "content/regular.txt").is_file())
        self.assertFalse((snapshot / "content/events.pipe").exists())

    def test_external_symlink_and_tree_loop_are_recorded_as_incomplete(self):
        donor = self.base / "Donor"
        outside = self.base / "Outside"
        cache = self.base / "Cache"
        (donor / "nested").mkdir(parents=True)
        outside.mkdir()
        (outside / "secret.bin").write_text("outside donor tree", newline='\n')
        os.symlink(outside / "secret.bin", donor / "outside-link.bin")
        os.symlink(donor, donor / "nested" / "loop")

        result = self.run_capture(donor, cache)
        captured = result["capture"]
        self.assertEqual(captured["status"], "incomplete", captured)
        self.assertFalse(captured["complete"])
        self.assertTrue(any(item["reason"] == "path-escapes-source-root" for item in captured["omissions"]))
        self.assertTrue(any(item["reason"] == "directory-loop" for item in captured["omissions"]))
        receipt = json.loads(Path(captured["receiptPath"]).read_text())
        paths = {entry["path"] for entry in receipt["files"]}
        self.assertNotIn("outside-link.bin", paths)
        self.assertFalse((Path(captured["snapshotRoot"]) / "content/outside-link.bin").exists())
        self.assertFalse(any(reason.startswith("external-dependency:") for reason in receipt["incompleteReasons"]),
                         "unspecified external dependencies should not be invented")

    def test_external_dependency_and_legacy_receipt_remain_noncurrent(self):
        donor = self.base / "Donor"
        cache = self.base / "Cache"
        donor.mkdir()
        (donor / "mod.data").write_text("package", newline='\n')
        legacy = self.base / "legacy.json"
        legacy.write_text(json.dumps({"applicationVersion": "0.0.9"}), newline='\n')
        stale_schema = self.base / "stale-schema.json"
        stale_schema.write_text(json.dumps({
            "snapshotSchemaVersion": 0,
            "importRevision": {"schemaVersion": 1, "commonRevision": 1,
                               "sourceEngine": "Psych Engine", "engineRevision": 1,
                               "applicationVersion": "0.0.9"},
        }), newline='\n')

        result = self.run_capture(donor, cache, legacy_receipt=legacy,
                                  dependencies=["assets/shared/plugin.dll", "outside-settings.json"])
        captured = result["capture"]
        self.assertEqual(captured["status"], "incomplete")
        self.assertTrue(any(reason.startswith("external-dependency:") for reason in captured["incompleteReasons"]))
        self.assertEqual(result["legacyStatus"], "unknown")
        self.assertEqual(result["staleSchemaStatus"], "outdated")

    def test_published_snapshot_is_reused_without_rewriting_its_receipt(self):
        donor = self.base / "Donor"
        cache = self.base / "Cache"
        donor.mkdir()
        (donor / "package.unknown").write_bytes(b"source bytes")
        first = self.run_capture(donor, cache)["capture"]
        receipt_path = Path(first["receiptPath"])
        before = receipt_path.read_bytes()
        second = self.run_capture(donor, cache)["capture"]
        self.assertEqual(second["status"], "existing")
        self.assertEqual(second["snapshotId"], first["snapshotId"])
        self.assertEqual(receipt_path.read_bytes(), before)

    def test_cache_inside_donor_is_rejected_without_creating_snapshot_data(self):
        donor = self.base / "Donor"
        donor.mkdir()
        (donor / "package.data").write_text("leave this alone", newline='\n')
        before = self.tree_fingerprint(donor)
        result = self.run_capture(donor, donor / "snapshot-cache")["capture"]
        self.assertEqual(result["status"], "failed")
        self.assertFalse((donor / "snapshot-cache").exists())
        self.assertEqual(before, self.tree_fingerprint(donor))


if __name__ == "__main__":
    unittest.main()
