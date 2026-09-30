"""Regression tests for the pinned hxcpp large-allocation ownership patch."""

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "patch_hxcpp_large_free", ROOT / "tools/patch_hxcpp_large_free.py"
)
PATCHER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCHER)


class HxcppLargeFreePatchTest(unittest.TestCase):
    def pinned_original(self):
        installed = PATCHER.IMMIX_SOURCE.read_bytes()
        if PATCHER.sha256(installed) == PATCHER.PATCHED_SHA256:
            self.assertEqual(installed.count(PATCHER.NEW_SITE), 1)
            installed = installed.replace(PATCHER.NEW_SITE, PATCHER.OLD_SITE, 1)
        self.assertEqual(PATCHER.sha256(installed), PATCHER.SOURCE_SHA256)
        return installed

    def test_pinned_patch_is_idempotent_for_exact_source(self):
        original = self.pinned_original()
        patched = PATCHER.patch_source(original)

        self.assertEqual(PATCHER.sha256(original), PATCHER.SOURCE_SHA256)
        self.assertEqual(PATCHER.sha256(patched), PATCHER.PATCHED_SHA256)
        self.assertEqual(PATCHER.patch_source(patched), patched)

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "Immix.cpp"
            target.write_bytes(original)
            self.assertTrue(PATCHER.patch_file(target))
            self.assertFalse(PATCHER.patch_file(target))
            self.assertEqual(target.read_bytes(), patched)

    def test_unknown_source_fails_closed(self):
        original = self.pinned_original()
        with self.assertRaisesRegex(ValueError, "differs from the pinned"):
            PATCHER.patch_source(original + b"// unexpected change\n")

    def test_only_live_list_owner_reaches_accounting_or_recycle(self):
        original = self.pinned_original()
        patched = PATCHER.patch_source(original)
        method_start = patched.index(b"   void FreeLarge(void *inLarge)\n")
        method_end = patched.index(b"   void *AllocLarge(int inSize, bool inClear)\n", method_start)
        method = patched[method_start:method_end]

        guard = b"if (!mLargeList.qerase_val(blob))"
        self.assertEqual(method.count(guard), 1)
        guard_start = method.index(guard)
        marker = b"((unsigned char *)inLarge)[HX_ENDIAN_MARK_ID_BYTE] = 0;"
        first_marker = method.index(marker, guard_start)
        size_read = method.index(b"unsigned int size = *blob;", guard_start)
        accounting = method.index(b"mLargeAllocated -= size;", guard_start)
        recycle = method.index(b"largeObjectRecycle.push(blob);", accounting)
        fallback_free = method.index(b"HxFree(blob);", accounting)
        failed_return = method.index(b"            return;\n         }", guard_start)
        failed_owner_branch = method[guard_start:failed_return + len(b"            return;\n         }")]
        no_capacity_branch = method[method.index(b"      else\n", guard_start):]

        self.assertIn(b"mLargeListLock.Unlock();", failed_owner_branch)
        self.assertIn(b"return;", failed_owner_branch)
        self.assertNotIn(marker, failed_owner_branch)
        self.assertLess(guard_start, first_marker)
        self.assertLess(first_marker, size_read)
        self.assertLess(size_read, accounting)
        self.assertLess(accounting, recycle)
        self.assertLess(accounting, fallback_free)
        self.assertIn(marker, no_capacity_branch)
        self.assertNotIn(b"qerase_val", no_capacity_branch)
        self.assertNotIn(b"mLargeAllocated -= size;", no_capacity_branch)


if __name__ == "__main__":
    unittest.main()
