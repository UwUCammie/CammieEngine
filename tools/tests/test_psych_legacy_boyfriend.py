"""Older Psych's `new Boyfriend(x, y, name)` builds the host's player Character."""
from pathlib import Path
import shutil, subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND
ROOT = Path(__file__).resolve().parents[2]


class PsychLegacyBoyfriendTest(unittest.TestCase):
	def test_constructs_player_character(self):
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
			work = Path(folder)
			shutil.copyfile(ROOT / 'source/PsychLegacyBoyfriend.hx', work / 'PsychLegacyBoyfriend.hx')
			(work / 'Character.hx').write_text('class Character {public var x:Float;public var y:Float;public var name:String;public var isPlayer:Bool;'
				'public function new(x:Float, y:Float, ?character:String = "bf", ?isPlayer:Bool = false, ?codename:Dynamic, ?source:Dynamic) '
				'{this.x=x;this.y=y;name=character;this.isPlayer=isPlayer;}}', encoding='utf-8')
			(work / 'Main.hx').write_text('''class Main {
	static function ok(v:Bool, m:String):Void if (!v) throw m;
	static function main() {
		var made:Character = cast PsychLegacyBoyfriend.create([100, -20.5, 'bf-car']);
		ok(made.x == 100 && made.y == -20.5 && made.name == 'bf-car' && made.isPlayer, 'Boyfriend is the player Character');
		var plain:Character = cast PsychLegacyBoyfriend.create([3, 4]);
		ok(plain.name == 'bf' && plain.isPlayer, 'Boyfriend defaults to bf, as in Psych');
		var empty:Character = cast PsychLegacyBoyfriend.create([]);
		ok(empty.x == 0 && empty.y == 0 && empty.name == 'bf', 'missing arguments use Psych defaults');
		Sys.println('ok');
	}
}''', encoding='utf-8')
			result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '-main', 'Main', '--interp'], cwd=work,
				capture_output=True, text=True, timeout=60)
			self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
			self.assertIn('ok', result.stdout)


if __name__ == '__main__':
	unittest.main()
