"""DDS sheets decode to the right pixels and are written as a valid PNG."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''import haxe.io.Bytes;
import VSliceAstcAdapter.DdsTextureDecoder;

class Main {
	static function header(width:Int, height:Int, fourCC:String, flags:Int, bits:Int, redMask:Int, payload:Int):Bytes {
		var bytes = Bytes.alloc(128 + payload);
		bytes.blit(0, Bytes.ofString('DDS '), 0, 4);
		bytes.setInt32(4, 124);
		bytes.setInt32(12, height);
		bytes.setInt32(16, width);
		bytes.setInt32(76, 32);
		bytes.setInt32(80, flags);
		if (fourCC != null) bytes.blit(84, Bytes.ofString(fourCC), 0, 4);
		bytes.setInt32(88, bits);
		bytes.setInt32(92, redMask);
		return bytes;
	}

	static function pixel(rgba:Bytes, width:Int, x:Int, y:Int):String {
		var o = (y * width + x) * 4;
		return rgba.get(o) + ',' + rgba.get(o + 1) + ',' + rgba.get(o + 2) + ',' + rgba.get(o + 3);
	}

	static function expect(label:String, actual:String, wanted:String):Void {
		if (actual != wanted) throw label + ': got ' + actual + ', wanted ' + wanted;
	}

	static function main() {
		// DXT1, 3x2 image (one partial block): red and blue end points, c0 > c1
		// so index 2 is the 2/3 mix. Row 0: idx 0,1,2,3; row 1: idx 1,0,...
		var bc1 = header(3, 2, 'DXT1', 0x4, 0, 0, 8);
		bc1.setUInt16(128, 0xF800);
		bc1.setUInt16(130, 0x001F);
		bc1.setInt32(132, (0 | (1 << 2) | (2 << 4) | (3 << 6)) | ((1 | (0 << 2)) << 8));
		var h = DdsTextureDecoder.parseHeader(bc1);
		expect('bc1 format', h.format + ' ' + h.width + 'x' + h.height, 'BC1 3x2');
		var rgba = DdsTextureDecoder.decodeRgba(bc1, h);
		expect('bc1 size', '' + rgba.length, '24');
		expect('bc1 c0', pixel(rgba, 3, 0, 0), '255,0,0,255');
		expect('bc1 c1', pixel(rgba, 3, 1, 0), '0,0,255,255');
		expect('bc1 mix', pixel(rgba, 3, 2, 0), '170,0,85,255');
		expect('bc1 row 1', pixel(rgba, 3, 0, 1), '0,0,255,255');

		// DXT1 with c0 <= c1 has a transparent fourth colour.
		var punch = header(4, 4, 'DXT1', 0x4, 0, 0, 8);
		punch.setUInt16(128, 0x001F);
		punch.setUInt16(130, 0xF800);
		punch.setInt32(132, 3);
		var punchRgba = DdsTextureDecoder.decodeRgba(punch, DdsTextureDecoder.parseHeader(punch));
		expect('bc1 transparent', pixel(punchRgba, 4, 0, 0), '0,0,0,0');

		// DXT5: alpha end points 255 and 0 with 8-value interpolation, white colour.
		var bc3 = header(4, 4, 'DXT5', 0x4, 0, 0, 16);
		bc3.set(128, 255);
		bc3.set(129, 0);
		// pixel 0 code 1 (a1 = 0), pixel 1 code 2 (6/7 of a0), pixel 8 code 7.
		bc3.set(130, 1 | (2 << 3));
		bc3.set(133, 7);
		bc3.setUInt16(136, 0xFFFF);
		bc3.setUInt16(138, 0xFFFF);
		bc3.setInt32(140, 0);
		var bc3Rgba = DdsTextureDecoder.decodeRgba(bc3, DdsTextureDecoder.parseHeader(bc3));
		expect('bc3 code 1', pixel(bc3Rgba, 4, 0, 0), '255,255,255,0');
		expect('bc3 code 2', pixel(bc3Rgba, 4, 1, 0), '255,255,255,218');
		expect('bc3 code 0', pixel(bc3Rgba, 4, 2, 0), '255,255,255,255');
		expect('bc3 code 7', pixel(bc3Rgba, 4, 0, 2), '255,255,255,36');

		// Plain 32-bit BGRA pixels.
		var bgra = header(1, 1, null, 0x41, 32, 0x00ff0000, 4);
		bgra.set(128, 10); bgra.set(129, 20); bgra.set(130, 30); bgra.set(131, 40);
		var bgraRgba = DdsTextureDecoder.decodeRgba(bgra, DdsTextureDecoder.parseHeader(bgra));
		expect('bgra', pixel(bgraRgba, 1, 0, 0), '30,20,10,40');

		// DXT3: explicit 4-bit alpha, low nibble first; colour always uses the
		// four-colour mode even when c0 <= c1.
		var bc2 = header(4, 4, 'DXT3', 0x4, 0, 0, 16);
		bc2.set(128, 0x3F);
		bc2.setUInt16(136, 0x001F);
		bc2.setUInt16(138, 0xF800);
		bc2.setInt32(140, 3 << 2);
		var bc2Rgba = DdsTextureDecoder.decodeRgba(bc2, DdsTextureDecoder.parseHeader(bc2));
		expect('bc2 alpha low nibble', pixel(bc2Rgba, 4, 0, 0), '0,0,255,255');
		expect('bc2 alpha high nibble', pixel(bc2Rgba, 4, 1, 0), '170,0,85,51');

		// DX10 extension header naming BC1 (DXGI 71): pixels start 20 bytes later.
		var dx10 = header(4, 4, 'DX10', 0x4, 0, 0, 20 + 8);
		dx10.setInt32(128, 71);
		dx10.setUInt16(148, 0xF800);
		dx10.setUInt16(150, 0x001F);
		dx10.setInt32(152, 0);
		var dx10Header = DdsTextureDecoder.parseHeader(dx10);
		expect('dx10 format', dx10Header.format + ' @' + dx10Header.dataOffset, 'BC1 @148');
		expect('dx10 pixel', pixel(DdsTextureDecoder.decodeRgba(dx10, dx10Header), 4, 3, 3), '255,0,0,255');

		// 24-bit rows are tightly packed by the DDS rule: a 1x2 surface is 6 bytes.
		var packed = header(1, 2, null, 0x40, 24, 0x00ff0000, 6);
		packed.set(128, 1); packed.set(129, 2); packed.set(130, 3);
		packed.set(131, 4); packed.set(132, 5); packed.set(133, 6);
		var packedHeader = DdsTextureDecoder.parseHeader(packed);
		if (!packedHeader.valid) throw 'packed 24-bit surface refused: ' + packedHeader.error;
		var packedRgba = DdsTextureDecoder.decodeRgba(packed, packedHeader);
		expect('rgb24 packed row 0', pixel(packedRgba, 1, 0, 0), '3,2,1,255');
		expect('rgb24 packed row 1', pixel(packedRgba, 1, 0, 1), '6,5,4,255');

		// A writer that pads rows to 32-bit words says so in the pitch field.
		var padded = header(1, 2, null, 0x40, 24, 0x00ff0000, 8);
		padded.setInt32(8, 0x8);
		padded.setInt32(20, 4);
		padded.set(128, 1); padded.set(129, 2); padded.set(130, 3);
		padded.set(132, 4); padded.set(133, 5); padded.set(134, 6);
		var paddedRgba = DdsTextureDecoder.decodeRgba(padded, DdsTextureDecoder.parseHeader(padded));
		expect('rgb24 padded row 1', pixel(paddedRgba, 1, 0, 1), '6,5,4,255');

		// Truncated and unknown files are refused, not misread.
		var short = header(8, 8, 'DXT5', 0x4, 0, 0, 16);
		if (DdsTextureDecoder.parseHeader(short).valid) throw 'truncated payload accepted';
		if (DdsTextureDecoder.parseHeader(header(4, 4, 'ATI2', 0x4, 0, 0, 16)).valid) throw 'unknown compression accepted';
		if (DdsTextureDecoder.parseHeader(Bytes.ofString('not a texture')).valid) throw 'non-DDS accepted';

		// PNG: signature, IHDR size, and the IDAT rows inflate back to the pixels.
		var png = DdsTextureDecoder.encodePng(rgba, 3, 2);
		if (png.get(0) != 0x89 || png.getString(1, 3) != 'PNG') throw 'missing PNG signature';
		if (png.getString(12, 4) != 'IHDR') throw 'IHDR is not first';
		var idatLength = (png.get(33) << 24) | (png.get(34) << 16) | (png.get(35) << 8) | png.get(36);
		if (png.getString(37, 4) != 'IDAT') throw 'IDAT is not second';
		var raw = haxe.zip.Uncompress.run(png.sub(41, idatLength));
		expect('png rows', '' + raw.length, '' + ((3 * 4 + 1) * 2));
		expect('png first pixel', raw.get(0) + ':' + raw.get(1) + ',' + raw.get(2) + ',' + raw.get(3), '0:255,0,0');

		if (!DdsTextureDecoder.isDdsPath('a/B.DDS') || DdsTextureDecoder.isDdsPath('a/b.png')) throw 'extension check';
		Sys.println('DDS OK');
	}
}
'''


class DdsTextureDecoderTest(unittest.TestCase):
    def test_block_and_plain_formats_decode_and_encode(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'Main.hx').write_text(MAIN, newline=chr(10))
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('DDS OK', result.stdout)


if __name__ == '__main__':
    unittest.main()
