"""Freeplay sends V-Slice's songSelected, freeplayIntroDone, freeplayOutro and freeplayClose.

V-Slice's FreeplayState dispatches SONG_SELECTED when a song is confirmed (before
the confirm animation), FREEPLAY_INTRO once the intro is done (at once when there
is no DJ), FREEPLAY_OUTRO when backing out and FREEPLAY_CLOSE just before it
returns to the main menu. The production helpers run here against a recording
runtime, and the call sites are checked for that order.
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


class HxcFreeplayLifecycleEventsTest(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / 'source/FreeplayState.hx').read_text(encoding='utf-8')

    def test_call_sites_follow_vslice_order(self):
        source = self.source
        create = method(source, '\toverride function create()')
        self.assertLess(create.index("hxcRuntime.dispatch('subStateOpenEnd'"),
                        create.index("dispatchHxcFreeplayEvent('freeplayIntroDone')"))
        update = method(source, '\toverride function update(elapsed:Float)')
        back = update[update.index('if (controls.BACK && !FlxG.keys.justPressed.BACKSPACE)'):update.index('if (accepted) {')]
        # Clearing a search is not leaving; the outro comes only on the leaving branch.
        self.assertLess(back.index('} else {'), back.index("dispatchHxcFreeplayEvent('freeplayOutro')"))
        self.assertLess(back.index("dispatchHxcFreeplayEvent('freeplayOutro')"),
                        back.index("dispatchHxcFreeplayEvent('freeplayClose')"))
        self.assertLess(back.index("dispatchHxcFreeplayEvent('freeplayClose')"),
                        back.index('LoadingState.loadAndSwitchState(new MainMenuState())'))
        self.assertEqual(back.count("dispatchHxcFreeplayEvent('freeplayClose')"), 1)
        accept = update[update.index('if (accepted) {'):]
        self.assertLess(accept.index('dispatchHxcSongSelected(daSelection, curDifficulty);'),
                        accept.index('beginBrowserConfirm(daSelection, curDifficulty)'))
        self.assertIn('dispatchHxcSongSelected(curSelected, curDifficulty);', method(source, '\tfunction hxcLaunchCurrentSelection('))
        names = (ROOT / 'source/ScriptLifecycleNames.hx').read_text(encoding='utf-8')
        for name in ('songSelected', 'freeplayIntroDone', 'freeplayOutro', 'freeplayClose'):
            self.assertIn("vsliceRow('%s')" % name, names)

    def test_helpers_send_capsule_payloads(self):
        selected = method(self.source, '\tfunction dispatchHxcSongSelected(')
        wide = method(self.source, '\tfunction dispatchHxcFreeplayEvent(')
        fixture = '''
class Runtime {
	public var sent:Array<String> = [];
	public function new() {}
	public function dispatch(kind:String, payload:Dynamic):Void
		sent.push(kind + ':' + payload.kind + ':' + (payload.capsule == null ? '-' : payload.capsule) + ':' + payload.difficulty);
}
class EngineCompat {
	public static function hxcFreeplayPayload(kind:String, state:Dynamic, ?capsule:Dynamic, ?difficulty:Dynamic, ?variation:Dynamic):Dynamic
		return {kind: kind, capsule: capsule, difficulty: difficulty};
}
class State {
	public var hxcRuntime:Runtime = new Runtime();
	public var curSelected = 0;
	public var curDifficulty = 1;
	public var capsules:Array<String> = ['first', null, 'third'];
	public function new() {}
	public function hxcCapsuleView(index:Int):Dynamic return index >= 0 && index < capsules.length ? capsules[index] : null;
	public ''' + selected.strip() + '''
	public ''' + wide.strip() + '''
}
class Main {
	static function check(ok:Bool, message:String) if (!ok) throw message;
	static function main() {
		var state = new State();
		state.dispatchHxcSongSelected(2, 3);
		check(state.hxcRuntime.sent.join('|') == 'songSelected:songSelected:third:3', 'song selected carries the confirmed capsule: ' + state.hxcRuntime.sent);
		state.dispatchHxcSongSelected(1, 0);
		check(state.hxcRuntime.sent.length == 1, 'no capsule view, no songSelected');
		state.dispatchHxcFreeplayEvent('freeplayOutro');
		state.curSelected = 1;
		state.dispatchHxcFreeplayEvent('freeplayClose');
		check(state.hxcRuntime.sent[1] == 'freeplayOutro:freeplayOutro:first:1', 'outro carries the selected capsule: ' + state.hxcRuntime.sent[1]);
		check(state.hxcRuntime.sent[2] == 'freeplayClose:freeplayClose:-:1', 'a menu-wide event is still sent without a capsule: ' + state.hxcRuntime.sent[2]);
		state.hxcRuntime = null;
		state.dispatchHxcFreeplayEvent('freeplayIntroDone');
		state.dispatchHxcSongSelected(0, 0);
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
