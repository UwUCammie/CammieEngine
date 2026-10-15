"""Missing text tags are reported once per callback and tag, not once per call."""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
ROOT = Path(__file__).resolve().parents[2]

FIXTURE = r'''
class Main {
	static function main() {
		var warnings:Array<String> = [];
		var present:Dynamic = {text:'hi', size:8};
		var vars:Map<String, Dynamic> = new Map();
		new SourceScriptTextBindings(false, function(tag) return tag == 'real' ? present : null,
			function(name) return name, function(value) return 0, function(text, style) {},
			function(message) warnings.push(message)).install(vars);
		var get = vars.get('getTextString');
		var set = vars.get('setTextString');
		// A script polling a missing text every frame.
		for (i in 0...120) if (get('isPaused') != null) throw 'missing text must read as nil';
		if (set('isPaused', 'x') != false) throw 'missing write must report false';
		if (set('isPaused', 'y') != false) throw 'second missing write must still report false';
		get('other');
		get(null);
		get(null);
		if (get('real') != 'hi') throw 'present text must still read';
		if (set('real', 'new') != true || present.text != 'new') throw 'present text must still write';
		var expected = ["getTextString: Object isPaused doesn't exist!", "setTextString: Object isPaused doesn't exist!",
			"getTextString: Object other doesn't exist!", "getTextString: Object null doesn't exist!"];
		if (warnings.join('|') != expected.join('|')) throw 'warnings: ' + warnings.join('|');
		// Each script owns its bindings, so a second script still gets its own report.
		var second:Map<String, Dynamic> = new Map();
		new SourceScriptTextBindings(false, function(tag) return null, function(name) return name,
			function(value) return 0, function(text, style) {}, function(message) warnings.push(message)).install(second);
		second.get('getTextString')('isPaused');
		if (warnings.length != 5) throw 'second binding must report its own missing tag';
		Sys.println('ok');
	}
}
'''


class SourceTextMissingOnceTest(unittest.TestCase):
	def test_missing_text_reported_once_per_tag(self):
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
			work = FixturePath(folder)
			(work / 'Main.hx').write_text(FIXTURE)
			(work / 'SourceScriptTextBindings.hx').write_text((ROOT / 'source/SourceScriptTextBindings.hx').read_text())
			result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '-main', 'Main', '--interp'], cwd=ROOT,
				text=True, capture_output=True, timeout=60)
			self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
			self.assertIn('ok', result.stdout)


if __name__ == '__main__':
	unittest.main()
