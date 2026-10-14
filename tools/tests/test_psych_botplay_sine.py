"""PlayState advances botplaySine the way Psych's update does.

Psych adds 180 * elapsed to botplaySine every frame its botplay label is
visible and fades the label with 1 - sin(pi * sine / 180). Scripts read the
value for their own botplay labels, so it must move only while botplay is on
and the label is shown. The production advanceBotplaySine runs here against a
small host.
"""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def method(text, start):
    pos = text.index(start)
    brace = text.index('{', pos)
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0: return text[pos:i + 1]
    raise AssertionError('unterminated ' + start)


class PsychBotplaySineTest(unittest.TestCase):
    def test_sine_advances_only_while_botplay_label_shows(self):
        source = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        advance = method(source, '\tfunction advanceBotplaySine(')
        update = method(source, '\toverride public function update(elapsed:Float)')
        self.assertIn('advanceBotplaySine(elapsed);', update)
        fixture = '''
class Label { public var visible = true; public var alpha:Float = 1; public function new() {} }
class Host {
	public var botplaySine:Float = 0;
	public var botplayTxt:Label = new Label();
	public var botPlay = false;
	public function new() {}
	function sourceBotPlay():Bool return botPlay;
	public ''' + advance.strip() + '''
}
class Main {
	static function check(ok:Bool, message:String) if (!ok) throw message;
	static function near(a:Float, b:Float) return Math.abs(a - b) < 1e-9;
	static function main() {
		var host = new Host();
		host.advanceBotplaySine(0.5);
		check(host.botplaySine == 0 && host.botplayTxt.alpha == 1, 'botplay off leaves the sine and label alone');
		host.botPlay = true;
		host.advanceBotplaySine(0.5);
		check(near(host.botplaySine, 90), 'adds 180 per second: ' + host.botplaySine);
		check(near(host.botplayTxt.alpha, 0), 'label fades with the sine: ' + host.botplayTxt.alpha);
		host.advanceBotplaySine(0.5);
		check(near(host.botplaySine, 180) && near(host.botplayTxt.alpha, 1), 'half a turn later the label is back');
		host.botplayTxt.visible = false;
		host.advanceBotplaySine(1);
		check(near(host.botplaySine, 180), 'a hidden label stops the sine as in Psych');
		host.botplayTxt = null;
		host.advanceBotplaySine(1);
		check(near(host.botplaySine, 180), 'no label is safe');
		Sys.println('ok');
	}
}
'''
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'Main', '--interp'],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
