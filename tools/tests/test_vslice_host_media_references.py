"""V-Slice scripts that play the base game's own media must not be reported as missing."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / 'source/ModuleFunctions.hx'


def extract_method(source, marker):
    start = source.index(marker)
    depth = 0
    for index in range(source.index('{', source.index('):', start)), len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError('unterminated method: ' + marker)


MAIN = r'''import haxe.io.Path;
import sys.FileSystem;
using StringTools;

class Probe {
METHODS
}

@:access(Probe)
class Main {
 static function main() {
  var work = 'WORK_ROOT';
  var namespace = work + '/assets/imported_mods/v-slice-pack';
  var media = ['.ogg', '.wav', '.mp3'];
  if (!Probe.vSliceHostMediaExists(namespace, 'thunder_1', 'sounds', media)) throw 'a host assets/sounds file was not found';
  if (!Probe.vSliceHostMediaExists(namespace, 'sounds/thunder_1', 'sounds', media)) throw 'a folder-prefixed host key was not found';
  if (!Probe.vSliceHostMediaExists(namespace, 'breakfast', 'music', media)) throw 'a host shared music file was not found';
  if (Probe.vSliceHostMediaExists(namespace, 'not_shipped', 'sounds', media)) throw 'a sound nobody ships was found';
  // Outside an imported_mods namespace there is no host tree to trust.
  if (Probe.vSliceHostMediaExists(work + '/elsewhere/pack', 'thunder_1', 'sounds', media)) throw 'a namespace outside imported_mods trusted a host tree';
  // Images have a basename fallback that would match unrelated host art.
  if (Probe.vSliceHostMediaExists(namespace, 'stageback', 'images', ['.png'])) throw 'host images must not count';
 }
}
'''


class VSliceHostMediaReferencesTest(unittest.TestCase):
    def test_host_media_counts_as_present(self):
        module = MODULE.read_text(encoding='utf-8')
        methods = '\n'.join(extract_method(module, 'static function ' + name + '(') for name in (
            'findChildDirectory', 'normalizedImportFileName', 'findImportFile', 'isImportFile',
            'findVSliceHxcAssetByBasename', 'findVSliceHxcAsset', 'vSliceHostMediaExists'))
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            work = Path(folder)
            for relative in ('assets/sounds/thunder_1.ogg', 'assets/shared/music/breakfast.ogg',
                    'assets/images/stageback.png', 'assets/imported_mods/v-slice-pack/keep.txt'):
                (work / relative).parent.mkdir(parents=True, exist_ok=True)
                (work / relative).write_text('x', newline='\n')
            (work / 'ImportDirectoryListing.hx').write_text(
                (ROOT / 'source/ImportDirectoryListing.hx').read_text(encoding='utf-8'), newline='\n')
            main = MAIN.replace('METHODS', methods).replace('WORK_ROOT', str(work).replace(chr(92), '/'))
            (work / 'Main.hx').write_text(main, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'Main', '--interp'],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-3000:])

    def test_missing_media_report_consults_the_host_tree(self):
        body = extract_method(MODULE.read_text(encoding='utf-8'), 'static function mergeVSliceHxcStageAsset(')
        self.assertIn("if (reportMissing && !vSliceHostMediaExists(runtimeNamespace, reference.key, folder, extensions))", body)


if __name__ == '__main__':
    unittest.main()
