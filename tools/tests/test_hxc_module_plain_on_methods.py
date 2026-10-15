"""A V-Slice module's own `on*` methods that V-Slice never dispatches do not disable the module."""
from pathlib import Path
import json, subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND
ROOT = Path(__file__).resolve().parents[2]

PLAIN = '''import funkin.modding.module.Module;
import funkin.play.PlayState;
class FlashModule extends Module {
    var flashes:Int = 0;
    function new() { super("FlashModule"); }
    override function onBeatHit(event) { super.onBeatHit(event); flashes = flashes + 1; }
    override function onSongDestroy(event) { super.onSongDestroy(event); cleanUp(); }
    override function onStateDestroy() { super.onStateDestroy(); cleanUp(); }
    function cleanUp() { flashes = 0; }
}
'''

DISPATCHED = '''import funkin.modding.module.Module;
class FocusModule extends Module {
    var paused:Bool = false;
    function new() { super("FocusModule"); }
    override function onBeatHit(event) { super.onBeatHit(event); paused = false; }
    override function onAdd(event) { super.onAdd(event); paused = true; }
}
'''


class HxcModulePlainOnMethodsTest(unittest.TestCase):
	def test_only_dispatched_hooks_block_a_module(self):
		main = '''class Main {
	static function has(result:Dynamic, code:String, text:String):Bool {
		for (finding in (cast result.diagnostics:Array<Dynamic>))
			if (finding.code == code && Std.string(finding.message).indexOf(text) >= 0) return true;
		return false;
	}
	static function main() {
		var plain = HxcCompat.analyze(__PLAIN__, "scripts/modules/FlashModule.hxc");
		if (has(plain, "unsupported-hxc-module-body", "unrouted lifecycle")) throw "a method V-Slice never calls blocked the module";
		if (plain.generatedHscript.indexOf("function beatHit") < 0) throw "the routed beat hook was not kept: " + plain.generatedHscript;
		var dispatched = HxcCompat.analyze(__DISPATCHED__, "scripts/modules/FocusModule.hxc");
		if (!has(dispatched, "unsupported-hxc-module-body", "unrouted lifecycle onAdd") || dispatched.moduleSafe)
			throw "a hook V-Slice dispatches but the engine does not route must still be reported";
		Sys.println("ok");
	}
}'''.replace('__PLAIN__', json.dumps(PLAIN)).replace('__DISPATCHED__', json.dumps(DISPATCHED))
		with tempfile.TemporaryDirectory() as folder:
			(Path(folder) / 'Main.hx').write_text(main, encoding='utf-8')
			result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder, '-main', 'Main', '--interp'],
				cwd=ROOT, capture_output=True, text=True, timeout=300)
			self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-3000:])
			self.assertIn('ok', result.stdout)


if __name__ == '__main__':
	unittest.main()
