"""Psych note skin files resolve the way Psych finds them on Windows: by letter-case-insensitive name, and a pixel
sheet without its ENDS half still skins tap notes."""
from pathlib import Path
import shutil, subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND
ROOT = Path(__file__).resolve().parents[2]


class PsychSkinLetterCaseTest(unittest.TestCase):
	def test_unique_case_variant_resolves_to_disk_name(self):
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
			work = Path(folder)
			shutil.copyfile(ROOT / 'source/PsychSkinResolver.hx', work / 'PsychSkinResolver.hx')
			owner = 'assets/imported_mods/owner'
			for path in ['images/pixelUI/door.png', 'images/pixelUI/doorENDS.png', 'images/notes/Gong_Mechanic.png',
					'images/notes/gong_mechanic.XML', 'images/Exact.png', 'images/Exact.xml']:
				target = work / owner / path
				target.parent.mkdir(parents=True, exist_ok=True)
				target.write_bytes(b'fixture')
			(work / 'Probe.hx').write_text(r'''
class Probe {
	static function check(value:Bool, message:String):Void if (!value) throw message;
	static function main():Void {
		var owner = 'assets/imported_mods/owner';
		var pixel = PsychSkinResolver.resolve('Door', owner, true);
		check(pixel != null, 'pixel sheet differing only in case must resolve');
		check(pixel.image == owner + '/images/pixelUI/door.png' && pixel.endsImage == owner + '/images/pixelUI/doorENDS.png',
			'pixel sheet must use the on-disk names: ' + pixel.image + ' ' + pixel.endsImage);
		var atlas = PsychSkinResolver.resolve('Notes/GONG_MECHANIC', owner, false);
		check(atlas != null && atlas.image == owner + '/images/notes/Gong_Mechanic.png'
			&& atlas.metadata == owner + '/images/notes/gong_mechanic.XML', 'folders and files keep their disk spelling');
		var exact = PsychSkinResolver.resolve('Exact', owner, false);
		check(exact.image == owner + '/images/Exact.png' && exact.key == 'Exact', 'exact names are unchanged');
		var missing = PsychSkinResolver.resolveDetailed('Absent', owner, false);
		check(missing.descriptor == null && missing.reason.indexOf('missing ' + owner + '/images/Absent.png') >= 0,
			'missing files still report the requested name');
		Sys.println('ok');
	}
}
''', encoding='utf-8')
			result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '-main', 'Probe', '--interp'], cwd=work,
				capture_output=True, text=True, timeout=60)
			self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
			self.assertIn('ok', result.stdout)


class PsychPixelSheetWithoutEndsTest(unittest.TestCase):
	def test_pixel_sheet_without_ends(self):
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
			work = Path(folder)
			shutil.copyfile(ROOT / 'source/PsychSkinResolver.hx', work / 'PsychSkinResolver.hx')
			owner = 'assets/imported_mods/owner'
			for path in ['images/pixelUI/Solo.png', 'images/pixelUI/Pair.png', 'shared/images/pixelUI/Pair.png',
					'shared/images/pixelUI/PairENDS.png', 'images/pixelUI/Tint-red.png', 'images/pixelUI/Tint.png', 'images/pixelUI/TintENDS.png',
					'images/pixelUI/Lone-red.png', 'images/pixelUI/Lone.png']:
				target = work / owner / path
				target.parent.mkdir(parents=True, exist_ok=True)
				target.write_bytes(b'fixture')
			(work / 'Probe.hx').write_text(r'''
class Probe {
	static function check(value:Bool, message:String):Void if (!value) throw message;
	static function main():Void {
		var owner = 'assets/imported_mods/owner';
		var solo = PsychSkinResolver.resolve('Solo', owner, true);
		check(solo != null && solo.image == owner + '/images/pixelUI/Solo.png' && solo.endsImage == null, 'tap-only pixel sheet resolves');
		var pair = PsychSkinResolver.resolve('Pair', owner, true);
		check(pair.image == owner + '/shared/images/pixelUI/Pair.png' && pair.endsImage == owner + '/shared/images/pixelUI/PairENDS.png',
			'a complete pair in a later folder wins over a sheet without ENDS');
		var tint = PsychSkinResolver.resolve('Tint', owner, true, '-red');
		check(tint.image == owner + '/images/pixelUI/Tint.png' && tint.endsImage == owner + '/images/pixelUI/TintENDS.png',
			'a postfix sheet without ENDS falls back to the complete base pair');
		var lone = PsychSkinResolver.resolve('Lone', owner, true, '-red');
		check(lone.image == owner + '/images/pixelUI/Lone-red.png' && lone.endsImage == null,
			'with no complete pair anywhere, the postfix sheet without ENDS wins over the base one: ' + lone.image);
		check(PsychSkinResolver.resolve('Solo', owner, false) == null, 'normal atlases still need their xml');
		Sys.println('ok');
	}
}
''', encoding='utf-8')
			result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '-main', 'Probe', '--interp'], cwd=work,
				capture_output=True, text=True, timeout=60)
			self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
			self.assertIn('ok', result.stdout)


if __name__ == '__main__':
	unittest.main()
