"""Psych's addHaxeLibrary never stops the calling Lua callback when a class does not resolve."""
from pathlib import Path
import re, subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
ROOT = Path(__file__).resolve().parents[2]


def callback_source():
	source = (ROOT / 'source/PsychRuntimeBindings.hx').read_text()
	start = source.index("owner.variables.set('addHaxeLibrary'")
	depth = 0
	for at in range(source.index('{', start), len(source)):
		if source[at] == '{': depth += 1
		elif source[at] == '}':
			depth -= 1
			if depth == 0:
				return source[start:source.index(';', at) + 1]
	raise AssertionError('unclosed addHaxeLibrary callback')


FIXTURE = r'''
class Module {
	public var bound:Array<String> = [];
	public function new() {}
	public function bindLibrary(name:String, path:String):Dynamic {
		if (path == 'HealthIcon' || path == 'shaders.ColorSwap') throw '[psych-hscript-import] Unregistered source module path: ' + path;
		bound.push(name + '=' + path);
		return path;
	}
}
class Owner {public var variables:Map<String, Dynamic> = new Map(); public function new() {}}
class Main {
	static var origin = 'mods/custom_notetypes/Space.lua';
	static var owner = new Owner();
	static var shared = new Module();
	static function module():Module return shared;
	static function main() {
		var traces:Array<String> = [];
		haxe.Log.trace = function(value:Dynamic, ?infos:haxe.PosInfos) traces.push(Std.string(value));
		__CALLBACK__
		var add:Dynamic = owner.variables.get('addHaxeLibrary');
		add('FlxSound', 'flixel.system');
		add('HealthIcon');
		add('ColorSwap', 'shaders');
		add('FlxText', null);
		// The callback returned normally after both failures, so the Lua caller continues.
		if (shared.bound.join('|') != 'FlxSound=flixel.system.FlxSound|FlxText=FlxText') throw 'bound: ' + shared.bound.join('|');
		if (traces.length != 2 || traces[0].indexOf('Space.lua#addHaxeLibrary') < 0 || traces[0].indexOf('HealthIcon') < 0
			|| traces[1].indexOf('shaders.ColorSwap') < 0) throw 'traces: ' + traces.join('|');
		Sys.println('ok');
	}
}
'''


class PsychAddHaxeLibraryTest(unittest.TestCase):
	def test_unresolved_library_is_reported_not_thrown(self):
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
			work = FixturePath(folder)
			(work / 'Main.hx').write_text(FIXTURE.replace('__CALLBACK__', callback_source()))
			result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '-main', 'Main', '--interp'], cwd=ROOT,
				text=True, capture_output=True, timeout=60)
			self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
			self.assertIn('ok', result.stdout)


if __name__ == '__main__':
	unittest.main()
