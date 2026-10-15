"""Nightmare Vision scripts read and write sicks/goods/bads/shits as PlayState members."""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND
from test_psych_skin_runtime import method
ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionRatingCountBindingsTest(unittest.TestCase):
	def test_counts_are_live_values_on_every_nv_script(self):
		play_state = (ROOT / 'source/PlayState.hx').read_text()
		seed = method(play_state, 'seedNightmareVision')
		self.assertIn('bindNightmareVisionRatingCounts(interp);', seed)
		bind = method(play_state, 'bindNightmareVisionRatingCounts')
		files = {
			'NightmareVisionScriptInterp.hx': '''class NightmareVisionScriptInterp {
	public var live:Map<String, {read:Void->Dynamic, write:Dynamic->Dynamic, target:Void->Dynamic}> = new Map();
	public function new() {}
	public function bindLiveValue(name:String, read:Void->Dynamic, ?write:Dynamic->Dynamic, ?target:Void->Dynamic):Void
		live.set(name, {read:read, write:write, target:target});
}''',
			'PlayState.hx': 'class PlayState {public static var shits:Int=0;public static var bads:Int=0;public static var goods:Int=0;public static var sicks:Int=0;'
				'public function new(){} public function run(i:NightmareVisionScriptInterp) bindNightmareVisionRatingCounts(i);' + bind + '}',
			'Main.hx': '''class Main {
	static function ok(v:Bool, m:String):Void if (!v) throw m;
	static function main() {
		var state = new PlayState();
		var interp = new NightmareVisionScriptInterp();
		state.run(interp);
		PlayState.sicks = 7; PlayState.goods = 3; PlayState.bads = 2; PlayState.shits = 1;
		ok(interp.live.get('sicks').read() == 7 && interp.live.get('goods').read() == 3
			&& interp.live.get('bads').read() == 2 && interp.live.get('shits').read() == 1, 'reads follow the live counts');
		interp.live.get('bads').write(0);
		interp.live.get('shits').write(4.0);
		ok(PlayState.bads == 0 && PlayState.shits == 4, 'script writes reach the counts');
		ok(interp.live.get('goods').target() == state, 'game.goods resolves on this PlayState');
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
