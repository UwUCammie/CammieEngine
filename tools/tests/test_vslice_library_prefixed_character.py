"""A V-Slice base character named with a library prefix (`shared:characters/<id>`) maps like the plain path."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''class Main {
 static function main() {
  var plain = EngineCompat.vSliceNativeCharacterCandidates('characters/pico').join(',');
  if (plain == '') throw 'the plain base path must map';
  for (path in ['shared:characters/pico', 'SHARED:characters/pico', 'preload:characters/pico'])
   if (EngineCompat.vSliceNativeCharacterCandidates(path).join(',') != plain)
    throw path + ' did not map like characters/pico';
  // Another library is a mod's own content, and an unknown id never crosses over.
  if (EngineCompat.vSliceNativeCharacterCandidates('week9:characters/pico').length != 0) throw 'a mod library crossed the boundary';
  if (EngineCompat.vSliceNativeCharacterCandidates('shared:characters/not-a-stock-character').length != 0) throw 'a custom id crossed the boundary';
 }
}
'''


class VSliceLibraryPrefixedCharacterTest(unittest.TestCase):
    def test_shared_library_prefix_is_the_base_library(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'Main.hx').write_text(MAIN, newline=chr(10))
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-3000:])


if __name__ == '__main__':
    unittest.main()
