"""Raw-source snapshots are bounded, isolated, and receipt-backed."""
from haxe_test_support import HAXE_COMMAND, TEST_TMP
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
NEKO = ROOT / ".tools/neko/neko.exe"

MAIN = r'''
import ImportSourceSnapshot.ImportSourceSnapshotOptions;
class Main {
 static function main():Void {
  var config:Dynamic = haxe.Json.parse(sys.io.File.getContent("config.json"));
  var copyProgress = 0;
  var activeWorkerPeak = 0;
  var mutatedBeforeCopy = false;
  var options:ImportSourceSnapshotOptions = {
   chunkSize: 4096,
   maxEntries: config.maxEntries,
   maxBytes: config.maxBytes,
   workerCount: config.workerCount,
   unresolvedDependencies: config.dependencies,
   onProgress: function(progress) {
    if (progress.activeWorkers > activeWorkerPeak) activeWorkerPeak = progress.activeWorkers;
    if (config.mutateBeforeCopy && !mutatedBeforeCopy && progress.phase == "copy" && progress.bytesCompleted == 0) {
     sys.io.File.saveContent(config.source + "/payload.bin", "changed after source scan");
     mutatedBeforeCopy = true;
    }
    if (progress.phase == "copy" && progress.bytesCompleted > 0) copyProgress++;
   },
   cancelled: function() {
    if (config.throwCancelAfterCopy && copyProgress > 0) throw "cancel callback exploded";
    return config.cancelAfterCopy && copyProgress > 0;
   }
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
   assessment:assessment, legacyStatus:legacyStatus, staleSchemaStatus:staleSchemaStatus,
   copyProgress:copyProgress, activeWorkerPeak:activeWorkerPeak}));
 }
}'''

VERIFY_MAIN = r'''import haxe.Json;
class VerifyMain {
 static function main():Void {
  var args = Sys.args();
  var activeWorkerPeak = 0;
  try {
   var workers = args.length > 2 ? Std.parseInt(args[2]) : null;
   ImportSourceSnapshot.verify(args[0], args[1], null, function(progress) {
    if (progress.activeWorkers > activeWorkerPeak) activeWorkerPeak = progress.activeWorkers;
   }, workers);
   var revision = ImportSourceSnapshot.assessReceipt(args[0] + "/receipt.json", "Psych Engine");
   Sys.println(Json.stringify({ok:true, error:"", activeWorkerPeak:activeWorkerPeak,
    assessmentStatus:revision.status}));
  } catch (error:Dynamic) {
   Sys.println(Json.stringify({ok:false, error:Std.string(error), activeWorkerPeak:activeWorkerPeak,
    assessmentStatus:""}));
  }
 }
}'''


HASH_MAIN = r'''import haxe.io.Bytes;
import ImportSourceSnapshot.ImportSnapshotSha256;
class HashMain {
 static function digest(bytes:Bytes):String {
  var hash = new ImportSnapshotSha256();
  var chunks = [1, 7, 56, 63, 64, 65, 4093, 65536];
  var offset = 0;
  var chunkIndex = 0;
  while (offset < bytes.length) {
   var count = chunks[chunkIndex++ % chunks.length];
   if (count > bytes.length - offset) count = bytes.length - offset;
   hash.update(bytes, offset, count);
   offset += count;
  }
  return hash.digestHex();
 }
 static function main():Void {
  var empty = Bytes.alloc(0);
  var short = Bytes.ofString("abc");
  var repeated = sys.io.File.getBytes(Sys.args()[0]);
  var streamedFile = ImportSourceSnapshot.sha256File(Sys.args()[0]);
  Sys.println(haxe.Json.stringify({empty:digest(empty), short:digest(short),
   repeated:digest(repeated), streamedFile:streamedFile}));
 }
}'''


class ImportSourceSnapshotTest(unittest.TestCase):
    def setUp(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=TEST_TMP)
        self.base = Path(self.temp.name)
        self.main = self.base / "Main.hx"
        self.main.write_text(MAIN, newline='\n')

    def tearDown(self):
        self.temp.cleanup()

    def run_capture(self, source, cache, *, cancel=False, legacy_receipt=None, dependencies=None,
                    worker_count=None, threaded=False, mutate_before_copy=False,
                    throw_cancel_after_copy=False, max_bytes=None, max_entries=None, timeout=90):
        (self.base / "config.json").write_text(json.dumps({
            "source": str(source), "cache": str(cache), "engine": "Psych Engine",
            "applicationVersion": "0.0.9", "cancelAfterCopy": cancel,
            "workerCount": worker_count, "mutateBeforeCopy": mutate_before_copy,
            "throwCancelAfterCopy": throw_cancel_after_copy,
            "maxEntries": max_entries, "maxBytes": max_bytes,
            "legacyReceipt": None if legacy_receipt is None else str(legacy_receipt),
            "staleSchemaReceipt": str(self.base / "stale-schema.json") if (self.base / "stale-schema.json").exists() else None,
            "dependencies": dependencies,
        }), newline='\n')
        if threaded:
            output = "SnapshotFixture.n"
            compiled = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(self.base),
                 "-main", "Main", "-neko", output],
                cwd=self.base, text=True, capture_output=True, timeout=timeout,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            process = subprocess.run([str(NEKO), output], cwd=self.base,
                                     text=True, capture_output=True, timeout=timeout)
        else:
            process = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(self.base), "--run", "Main"],
                cwd=self.base, text=True, capture_output=True, timeout=timeout,
            )
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        return json.loads((self.base / "result.json").read_text())

    def verify_snapshot(self, snapshot, snapshot_id, *, worker_count=None, threaded=False):
        fixture = self.base / "VerifyMain.hx"
        fixture.write_text(VERIFY_MAIN, encoding="utf-8", newline='\n')
        args = [str(snapshot), snapshot_id]
        if worker_count is not None:
            args.append(str(worker_count))
        if threaded:
            output = "VerifyFixture.n"
            compiled = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(self.base),
                 "-main", "VerifyMain", "-neko", output],
                cwd=self.base, text=True, capture_output=True, timeout=30,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            process = subprocess.run([str(NEKO), output, *args], cwd=self.base,
                                     text=True, capture_output=True, timeout=30)
        else:
            process = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(self.base), "--run", "VerifyMain",
                 *args],
                cwd=self.base, text=True, capture_output=True, timeout=30,
            )
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        return json.loads(process.stdout.strip().splitlines()[-1])

    def test_streaming_sha256_known_vectors_and_chunk_boundaries(self):
        fixture = self.base / "HashMain.hx"
        fixture.write_text(HASH_MAIN, encoding="utf-8", newline='\n')
        repeated = self.base / "repeated-a.bin"
        repeated.write_bytes(b"a" * 1_000_000)
        process = subprocess.run(
            [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(self.base), "--run", "HashMain", str(repeated)],
            cwd=self.base, text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        actual = json.loads(process.stdout.strip().splitlines()[-1])
        self.assertEqual(actual["empty"], "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        self.assertEqual(actual["short"], "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
        self.assertEqual(actual["repeated"], "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0")
        self.assertEqual(actual["streamedFile"], "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0")

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

    def test_copies_every_regular_file_and_empty_directory_without_touching_donor(self):
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
        (donor / "Game.EXE").write_bytes(pe)
        before = self.tree_fingerprint(donor)

        result = self.run_capture(donor, cache)
        captured = result["capture"]
        self.assertEqual(captured["status"], "complete", captured)
        self.assertTrue(captured["complete"])
        self.assertEqual(before, self.tree_fingerprint(donor), "capture modified donor files or layout")
        snapshot = Path(captured["snapshotRoot"])
        receipt = json.loads(Path(captured["receiptPath"]).read_text())
        self.assertEqual(receipt["snapshotSchemaVersion"], 2)
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
        self.assertEqual(receipt["exclusions"], [])
        self.assertIn("payload.DLL", files)
        self.assertIn("sneaky.data", files)
        self.assertIn("hidden-native.unknown", files)
        self.assertIn("universal.macho", files)
        self.assertIn("Game.EXE", files)
        self.assertEqual((snapshot / "content/Game.EXE").read_bytes(), bytes(pe))
        self.assertEqual((snapshot / "content/payload.DLL").read_bytes(), b"extension marked native")
        self.assertEqual((snapshot / "content/sneaky.data").read_bytes(), b"\x7fELF" + b"\x00" * 120)
        self.assertEqual((snapshot / "content/hidden-native.unknown").read_bytes(), bytes(pe))
        self.assertEqual((snapshot / "content/universal.macho").read_bytes(), (donor / "universal.macho").read_bytes())
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
        self.assertEqual(captured["status"], "complete", captured)
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

    def test_parallel_capture_and_verification_match_serial_snapshot_identity(self):
        if not NEKO.is_file():
            self.skipTest("portable Neko is unavailable for threaded target coverage")
        donor = self.base / "ParallelDonor"
        serial_cache = self.base / "SerialCache"
        parallel_cache = self.base / "ParallelCache"
        donor.mkdir()
        # Eight files still exercise bounded overlap, repeated read/hash chunks,
        # deterministic identities and byte-for-byte retention. Large SHA-256
        # inputs are covered separately; avoid redundant megabyte hashing in
        # the slow Neko fixture when the full suite runs concurrently.
        payload = bytes((index * 37 + 11) % 256 for index in range(256 * 1024))
        for index in range(8):
            (donor / f"chunk-{index:02}.dll").write_bytes(payload + bytes([index]))
        before = self.tree_fingerprint(donor)

        serial = self.run_capture(donor, serial_cache, worker_count=1)["capture"]
        parallel_result = self.run_capture(donor, parallel_cache, threaded=True)
        parallel = parallel_result["capture"]
        self.assertEqual(serial["status"], "complete", serial)
        self.assertEqual(parallel["status"], "complete", parallel)
        self.assertEqual(parallel["snapshotId"], serial["snapshotId"],
                         "worker scheduling must not affect the snapshot identity")
        self.assertGreaterEqual(parallel_result["activeWorkerPeak"], 2,
                                "the Neko fixture must exercise overlapping copy/hash workers")
        self.assertLessEqual(parallel_result["activeWorkerPeak"], 4,
                             "default snapshot worker count is bounded at four")
        self.assertEqual(before, self.tree_fingerprint(donor), "workers modified the donor")
        receipt = json.loads(Path(parallel["receiptPath"]).read_text())
        self.assertEqual(len(receipt["files"]), 8)
        self.assertTrue(all((Path(parallel["snapshotRoot"]) / "content" / item["path"]).read_bytes()
                            == (donor / item["path"]).read_bytes() for item in receipt["files"]))
        verified = self.verify_snapshot(Path(parallel["snapshotRoot"]), parallel["snapshotId"], threaded=True)
        self.assertTrue(verified["ok"], verified)
        self.assertGreaterEqual(verified["activeWorkerPeak"], 2,
                                "snapshot verification should hash files concurrently")
        self.assertLessEqual(verified["activeWorkerPeak"], 4)

    def test_schema_one_snapshot_with_native_exclusions_remains_rebuildable(self):
        cache = self.base / "LegacyCache"
        payload = b"retained v1 source"
        file_hash = hashlib.sha256(payload).hexdigest()
        files = [{"path": "old/source.hx", "size": len(payload), "sha256": file_hash}]
        directories = ["old"]
        exclusions = [{"path": "old/plugin.dll", "size": 4096,
                       "reason": "native-extension", "detectedHeader": ""}]
        records = [
            ("D", "old"),
            ("F", f"old/source.hx\t{len(payload)}\t{file_hash}"),
            ("X", "old/plugin.dll\t4096\tnative-extension\t"),
        ]
        digest = hashlib.sha256(b"ImportSourceSnapshot\n1\nPsych Engine\n")
        for kind, value in records:
            digest.update((json.dumps([kind, value], separators=(",", ":")) + "\n").encode())
        snapshot_id = digest.hexdigest()
        snapshot = cache / snapshot_id
        content = snapshot / "content"
        (content / "old").mkdir(parents=True)
        (content / "old" / "source.hx").write_bytes(payload)
        receipt = {
            "snapshotSchemaVersion": 1,
            "snapshotId": snapshot_id,
            "contentRoot": "content",
            "importRevision": {"schemaVersion": 1, "commonRevision": 2,
                               "sourceEngine": "Psych Engine", "engineRevision": 1,
                               "applicationVersion": "0.0.9"},
            "files": files,
            "directories": directories,
            "bytes": len(payload),
            "exclusions": exclusions,
            "omissions": [],
            "incompleteReasons": [],
        }
        (snapshot / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8", newline='\n')
        result = self.verify_snapshot(snapshot, snapshot_id)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["assessmentStatus"], "outdated")
        self.assertNotIn("plugin.dll", {path.name for path in (snapshot / "content" / "old").iterdir()},
                         "legacy verification must not invent old excluded payloads")
        self.assertEqual((snapshot / "content/old/source.hx").read_bytes(), payload)

    def test_parallel_worker_failure_joins_before_staging_cleanup(self):
        if not NEKO.is_file():
            self.skipTest("portable Neko is unavailable for threaded target coverage")
        donor = self.base / "ChangingDonor"
        cache = self.base / "FailureCache"
        donor.mkdir()
        (donor / "payload.bin").write_bytes(b"before scan")
        cache.mkdir()
        sentinel = cache / "caller-owned.txt"
        sentinel.write_text("keep", encoding="utf-8", newline='\n')

        result = self.run_capture(donor, cache, threaded=True, mutate_before_copy=True)["capture"]
        self.assertEqual(result["status"], "failed", result)
        self.assertIn("changed after snapshot scanning", result["error"])
        self.assertEqual(sorted(path.name for path in cache.iterdir()), ["caller-owned.txt"],
                         "failure cleanup must happen after every started worker exits")
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_parallel_cancellation_joins_workers_and_removes_staging_tree(self):
        if not NEKO.is_file():
            self.skipTest("portable Neko is unavailable for threaded target coverage")
        donor = self.base / "CancelledParallelDonor"
        cache = self.base / "CancelledParallelCache"
        donor.mkdir()
        payload = b"cancel promptly " * (128 * 1024)
        for index in range(6):
            (donor / f"large-{index}.raw").write_bytes(payload)
        cache.mkdir()
        sentinel = cache / "caller-owned.txt"
        sentinel.write_text("keep", encoding="utf-8", newline='\n')

        result = self.run_capture(donor, cache, cancel=True, threaded=True)["capture"]
        self.assertEqual(result["status"], "cancelled", result)
        self.assertEqual(sorted(path.name for path in cache.iterdir()), ["caller-owned.txt"],
                         "cancel cleanup must wait until workers close their source and staging files")
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_parallel_cancel_callback_exception_fails_after_workers_join(self):
        if not NEKO.is_file():
            self.skipTest("portable Neko is unavailable for threaded target coverage")
        donor = self.base / "ThrowingCancelDonor"
        cache = self.base / "ThrowingCancelCache"
        donor.mkdir()
        payload = b"cancel callback exception " * (64 * 1024)
        for index in range(6):
            (donor / f"large-{index}.raw").write_bytes(payload)
        cache.mkdir()
        sentinel = cache / "caller-owned.txt"
        sentinel.write_text("keep", encoding="utf-8", newline='\n')

        result = self.run_capture(donor, cache, threaded=True,
                                  throw_cancel_after_copy=True)
        captured = result["capture"]
        self.assertEqual(captured["status"], "failed", captured)
        self.assertIn("cancel callback exploded", captured["error"])
        self.assertGreater(result["copyProgress"], 0,
                           "the callback must throw after copy workers report progress")
        self.assertGreaterEqual(result["activeWorkerPeak"], 2,
                                "the callback must throw while multiple copy workers are active")
        self.assertEqual(sorted(path.name for path in cache.iterdir()), ["caller-owned.txt"],
                         "callback failure cleanup must wait for every worker")
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_byte_limit_omission_remains_explicit_and_verifiable(self):
        donor = self.base / "LimitedDonor"
        cache = self.base / "LimitedCache"
        donor.mkdir()
        (donor / "small-a.bin").write_bytes(b"1234")
        (donor / "small-b.bin").write_bytes(b"5678")
        captured = self.run_capture(donor, cache, worker_count=2, max_bytes=4)["capture"]
        self.assertEqual(captured["status"], "incomplete", captured)
        self.assertTrue(any(reason.startswith("byte-limit-exceeded:")
                            for reason in captured["incompleteReasons"]))
        receipt = json.loads(Path(captured["receiptPath"]).read_text())
        self.assertEqual(receipt["bytes"], 4)
        self.assertTrue(any(item["reason"] == "byte-limit-exceeded" for item in receipt["omissions"]))
        self.assertTrue(self.verify_snapshot(Path(captured["snapshotRoot"]), captured["snapshotId"])["ok"])

    def test_only_validated_mac_metadata_is_excluded(self):
        donor = self.base / "MetadataDonor"
        cache = self.base / "MetadataCache"
        donor.mkdir()
        (donor / ".DS_Store").write_bytes(b"\x00\x00\x00\x01Bud1" + b"finder catalog")
        (donor / "notes.DS_Store").write_bytes(b"\x00\x00\x00\x01Bud1" + b"user source")
        (donor / "Thumbs.db").write_bytes(bytes.fromhex("d0cf11e0a1b11ae1") + b"thumbnail data")
        (donor / "desktop.ini").write_text("[.ShellClassInfo]\nIconResource=folder.ico,0\n",
                                            encoding="utf-8", newline='\n')
        (donor / "unknown-binary.bin").write_bytes(b"\x7fELF" + b"unrecognized source payload")

        captured = self.run_capture(donor, cache)["capture"]
        self.assertEqual(captured["status"], "complete", captured)
        receipt = json.loads(Path(captured["receiptPath"]).read_text())
        self.assertEqual(receipt["exclusions"], [{
            "path": ".DS_Store", "size": len(b"\x00\x00\x00\x01Bud1") + len(b"finder catalog"),
            "reason": "recognized-os-metadata-ds-store", "detectedHeader": "macos-buddy-store-v1",
        }])
        files = {item["path"] for item in receipt["files"]}
        self.assertEqual(files, {"notes.DS_Store", "Thumbs.db", "desktop.ini", "unknown-binary.bin"})
        content = Path(captured["snapshotRoot"]) / "content"
        self.assertFalse((content / ".DS_Store").exists())
        self.assertEqual((content / "Thumbs.db").read_bytes(), (donor / "Thumbs.db").read_bytes())
        self.assertTrue(self.verify_snapshot(Path(captured["snapshotRoot"]), captured["snapshotId"])["ok"])

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
        try:
            os.symlink(outside / "secret.bin", donor / "outside-link.bin")
            os.symlink(donor, donor / "nested" / "loop")
        except OSError as error:
            if os.name == "nt" and getattr(error, "winerror", None) == 1314:
                self.skipTest("Windows symbolic links require Developer Mode or elevated privileges")
            raise

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
        self.assertEqual(first["status"], "complete", first)
        self.assertTrue(first["receiptPath"], first)
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
