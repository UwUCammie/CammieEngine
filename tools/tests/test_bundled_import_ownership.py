"""Compiled host ownership protection matches the clean Windows package baseline."""
from pathlib import Path
import importlib.util
import re
import unittest
ROOT=Path(__file__).resolve().parents[2]
class BundledImportOwnershipTest(unittest.TestCase):
    def test_protected_namespace_is_the_explicit_packaged_results_root(self):
        spec=importlib.util.spec_from_file_location('package_windows_release',ROOT/'tools/package_windows_release.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        source=(ROOT/'source/BundledImportOwnership.hx').read_text(encoding='utf-8')
        match=re.search(r"RESULTS_ROOT:String\s*=\s*'([^']+)'",source)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1),'/'.join(module.BUNDLED_RESULTS_ROOT))
        self.assertNotIn('File.getContent',source)
        self.assertNotIn('baseSongKeys',source)
if __name__=='__main__':unittest.main()
