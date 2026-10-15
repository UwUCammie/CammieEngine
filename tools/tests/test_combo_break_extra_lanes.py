"""Combo-break sprites follow the receptors without reading past either list when scripts add receptors."""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND
from test_psych_skin_runtime import method
ROOT = Path(__file__).resolve().parents[2]


class ComboBreakExtraLanesTest(unittest.TestCase):
	def test_extra_receptor_does_not_index_missing_sprite(self):
		source = (ROOT / 'source/PlayState.hx').read_text()
		self.assertIn('syncComboBreakLanes(playerComboBreak, playerStrums);', source)
		self.assertIn('syncComboBreakLanes(enemyComboBreak, enemyStrums);', source)
		sync = method(source, 'syncComboBreakLanes')
		files = {
			'FlxSprite.hx': 'class FlxSprite {public var x:Float=0;public function new(x:Float=0){this.x=x;}}',
			'FlxTypedGroup.hx': 'class FlxTypedGroup<T> {public var members:Array<T>=[];public function new(){}}',
			'Strumline.hx': 'class Strumline {public var members:Array<FlxSprite>=[];public function new(){}}',
			'Main.hx': '''class Host {''' + sync + '''
	public static function run(g:FlxTypedGroup<FlxSprite>, l:Strumline) syncComboBreakLanes(g, l);
}
class Main {
	static function main() {
		var group = new FlxTypedGroup<FlxSprite>();
		var line = new Strumline();
		for (i in 0...4) {group.members.push(new FlxSprite()); line.members.push(new FlxSprite(100 + i * 112));}
		line.members.push(new FlxSprite(900));
		Host.run(group, line);
		for (i in 0...4) if (group.members[i].x != 100 + i * 112) throw 'lane ' + i + ' did not follow its receptor';
		group.members.push(null); group.members.push(new FlxSprite(5));
		line.members[2] = null;
		Host.run(group, line);
		if (group.members[5].x != 5) throw 'a sprite past the receptors was moved';
		Host.run(null, line); Host.run(group, null);
		Sys.println('ok');
	}
}'''
		}
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as tmp:
			for name, content in files.items():
				(Path(tmp) / name).write_text(content, encoding='utf-8')
			result = subprocess.run([*HAXE_COMMAND, '-cp', tmp, '-main', 'Main', '--interp'], cwd=ROOT,
				capture_output=True, text=True, timeout=60)
			self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-3000:])
			self.assertIn('ok', result.stdout)


if __name__ == '__main__':
	unittest.main()
