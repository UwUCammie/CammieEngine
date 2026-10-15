"""ASTC sheets decode into import stages deeper than Windows' 260 character limit.

astcenc writes with plain C file calls, so it could not create a PNG whose
full path reached 260 characters, and a V-Slice import whose stage path was
that deep failed. The adapter now lets astcenc write a short temporary file
and moves it into place itself.
"""
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]
DECODER = ROOT / '.tools/astcenc/astcenc-sse2.exe'


def tiny_png(path):
    raw = b''.join(b'\x00' + bytes([200, 40, 40, 255]) * 8 for _ in range(8))
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 8, 8, 8, 6, 0, 0, 0))
        + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def long_folder(base):
    # Deep enough to take the temporary-file route (240 characters and up) but
    # short of 260, because the Haxe interpreter running this test cannot write
    # past the limit itself; the native game can, and real stages go past it.
    folder = os.path.abspath(str(base))
    for part in ('deep-stage-folder', 'abcdefgh', 'abcd', 'ab', 'a'):
        while len(os.path.join(folder, part)) + len('/char.png') <= 255:
            folder = os.path.join(folder, part)
    os.makedirs(folder)
    return folder.replace('\\', '/')


MAIN = '''class Main {
  static function main() {
    var args = Sys.args();
    var destination = args[1] + "/char.png";
    if (!VSliceAstcAdapter.longPathTarget(destination)) throw "fixture path is not long: " + destination.length;
    var result = VSliceAstcAdapter.decodeFile(args[0], destination);
    if (!result.success) throw result.message;
    if (sys.io.File.getBytes(destination).getString(1, 3) != "PNG") throw "decoded file is not a PNG";
    if (VSliceAstcAdapter.longPathTarget("assets/a.png")) throw "short paths take the direct route";
    Sys.println("long-ok");
  }
}
'''


@unittest.skipUnless(sys.platform == 'win32' and DECODER.exists(), 'needs the Windows astcenc tool')
class VSliceAstcLongDestinationTest(unittest.TestCase):
    def test_decoded_png_reaches_a_destination_past_the_path_limit(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            base = Path(folder)
            tiny_png(base / 'in.png')
            subprocess.run([str(DECODER), '-cl', str(base / 'in.png'), str(base / 'in.astc'), '4x4', '-fast'],
                check=True, capture_output=True, timeout=120)
            target = long_folder(base)
            (base / 'Main.hx').write_text(MAIN, newline=chr(10))
            env = dict(os.environ, DISAPPOINTINGPLUS_ASTCENC=str(DECODER))
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(base),
                '--run', 'Main', str(base / 'in.astc'), target], cwd=ROOT, capture_output=True, text=True,
                timeout=600, env=env)
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-3000:])
        self.assertIn('long-ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
