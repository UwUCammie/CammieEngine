"""Texture decoders write converted PNGs into the import stage.

The ASTC (astcenc) and DDS decoders write with the raw file API, so the
importer must hand them the staged path. Given the logical assets/ path they
wrote where no folder exists, and every ASTC V-Slice import failed.
"""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]


def extract_method(source, marker):
    start = source.index(marker)
    start = source.rfind('\n', 0, start) + 1
    brace = source.index('{', start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError('unterminated method: ' + marker)


def dds_dxt5(width, height):
    header = bytearray(128)
    header[0:4] = b'DDS '
    header[4:8] = (124).to_bytes(4, 'little')
    header[12:16] = height.to_bytes(4, 'little')
    header[16:20] = width.to_bytes(4, 'little')
    header[76:80] = (32).to_bytes(4, 'little')
    header[80:84] = (4).to_bytes(4, 'little')
    header[84:88] = b'DXT5'
    blocks = ((width + 3) // 4) * ((height + 3) // 4)
    return bytes(header) + bytes(16) * blocks


class ImportTextureDecodeStagingTest(unittest.TestCase):
    def test_decoded_png_lands_in_the_stage_and_is_visible_through_the_facade(self):
        module = (ROOT / 'source/ModuleFunctions.hx').read_text()
        helper = extract_method(module, 'static function importWriteTarget(')
        for call in ('VSliceAstcAdapter.decodeFile(source, importWriteTarget(destination))',
                'VSliceAstcAdapter.decodeFile(mapping.source, importWriteTarget(destination))',
                'DdsTextureDecoder.decodeFile(source, importWriteTarget(destination))',
                'DdsTextureDecoder.decodeFile(mapping.source, importWriteTarget(destination))'):
            self.assertIn(call, module)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            base = Path(folder)
            install = base / 'install'
            (install / 'assets').mkdir(parents=True)
            stage = install / 'import-cache/staging/run'
            stage.mkdir(parents=True)
            donor = base / 'donor.dds'
            donor.write_bytes(dds_dxt5(8, 4))
            main = '''import ImportFile as File;
import ImportFileSystem as FileSystem;

class Main {
%s

  static function main() {
    var install = Sys.args()[0];
    ImportIO.begin(install, Sys.args()[1]);
    var destination = "assets/imported_mods/pack/images/characters/hero/char.png";
    FileSystem.createDirectory("assets/imported_mods/pack/images/characters/hero");
    var decoded = VSliceAstcAdapter.DdsTextureDecoder.decodeFile(Sys.args()[2], importWriteTarget(destination));
    if (!decoded.success) throw decoded.message;
    if (!FileSystem.exists(destination)) throw "converted PNG is not visible in the import";
    if (File.getBytes(destination).getString(1, 3) != "PNG") throw "staged file is not a PNG";
    if (sys.FileSystem.exists(install + "/" + destination)) throw "decoder wrote past the stage into the install";
    ImportIO.end();
  }
}''' % helper
            (base / 'Main.hx').write_text(main, newline=chr(10))
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(base),
                '--run', 'Main', str(install), str(stage), str(donor)],
                cwd=install, capture_output=True, text=True, timeout=600)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
