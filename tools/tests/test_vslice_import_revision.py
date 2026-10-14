"""V-Slice imports made before HXC loadSparrow/loadTexture art was planned must re-plan."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''class Main {
 static function main() {
  var before = {schemaVersion: ImportRevision.SCHEMA_VERSION, commonRevision: ImportRevision.COMMON_REVISION,
   sourceEngine: 'V-Slice', engineRevision: 3};
  var status = ImportRevision.assess(before, 'V-Slice').status;
  if (status != ImportRevision.OUTDATED) throw 'a revision 3 V-Slice receipt must be outdated, got ' + status;
  var now = ImportRevision.current('V-Slice');
  if (ImportRevision.assess(now, 'V-Slice').status != ImportRevision.CURRENT) throw 'the current stamp must be current';
 }
}
'''


class VSliceImportRevisionTest(unittest.TestCase):
    def test_receipts_before_planned_hxc_art_are_outdated(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'Main.hx').write_text(MAIN, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
