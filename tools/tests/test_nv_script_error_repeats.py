"""Nightmare Vision gameplay script errors go through the shared repeat filter, like Psych's."""
from pathlib import Path
import re, subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND
ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionScriptErrorRepeatsTest(unittest.TestCase):
	def test_gameplay_reporter_uses_repeat_filter(self):
		source = (ROOT / 'source/PlayState.hx').read_text()
		start = source.index('var scriptReporter = function(name:String, phase:String, error:Dynamic):Void {')
		reporter = source[start:source.index('};', start) + 2]
		self.assertIn('RepeatedScriptErrorLog.line(message, message)', reporter)
		self.assertIn('if (shown != null) trace(shown);', reporter)
		# The gameplay script set reports through the same filtered reporter.
		self.assertRegex(source, r'File\.getContent, seedNightmareVision, scriptReporter, null,')
		self.assertEqual(len(re.findall(r"trace\('\[nightmare-vision-script-error\] ' \+ root \+ '/' \+ name", source)), 0)
		fixture = '''class Main {
	static function main() {
		var root = 'assets/imported_mods/pack';
		var lines:Array<String> = [];
		haxe.Log.trace = function(v:Dynamic, ?i:haxe.PosInfos) lines.push(Std.string(v));
		__REPORTER__
		for (frame in 0...600) scriptReporter('songs/a/ui.hx', 'onUpdate', 'EUnknownVariable(bads)');
		scriptReporter('songs/a/ui.hx', 'onBeatHit', 'other');
		if (lines.length != RepeatedScriptErrorLog.SHOWN + 2) throw 'lines: ' + lines.length;
		if (lines[RepeatedScriptErrorLog.SHOWN].indexOf('further copies of this error are hidden') < 0) throw 'no repeat note';
		if (lines[lines.length - 1].indexOf('#onBeatHit: other') < 0) throw 'a different error still shows';
		Sys.println('ok');
	}
}'''.replace('__REPORTER__', reporter)
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as tmp:
			(Path(tmp) / 'Main.hx').write_text(fixture, encoding='utf-8')
			(Path(tmp) / 'RepeatedScriptErrorLog.hx').write_text((ROOT / 'source/RepeatedScriptErrorLog.hx').read_text(), encoding='utf-8')
			result = subprocess.run([*HAXE_COMMAND, '-cp', tmp, '-main', 'Main', '--interp'], cwd=ROOT,
				capture_output=True, text=True, timeout=60)
			self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-3000:])
			self.assertIn('ok', result.stdout)


if __name__ == '__main__':
	unittest.main()
