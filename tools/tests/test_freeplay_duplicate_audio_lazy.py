"""Hiding base game duplicates reads instrumentals only for charts whose title matches.

The first Freeplay filter decides for every imported chart whether it repeats a
base game song. The decision needs a shared title before anything else, so the
production baseDuplicate is run here with counting stand-ins: unrelated charts
read no audio, base songs are measured only when a title matches, and the
decisions are the same as measuring everything first.
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


class FreeplayDuplicateAudioLazyTest(unittest.TestCase):
    def test_audio_is_read_only_for_title_matches(self):
        source = (ROOT / 'source/FreeplayState.hx').read_text(encoding='utf-8')
        parts = [method(source, '\tfunction chartFingerprintFor('),
                 method(source, '\tfunction measureFingerprintAudio('),
                 method(source, '\tfunction baseDuplicate(')]
        body = '\n'.join(parts).replace('#if sys', '').replace('#else\n\t\treturn false;\n\t\t#end', '').replace('#end', '')
        body = body.replace('BaseGameDuplicate.measureAudio(', 'Probe.measure(').replace('FNFAssets.resolveCaseInsensitivePath(', 'Probe.resolve(')
        duplicate = (ROOT / 'source/BaseGameDuplicate.hx').read_text(encoding='utf-8')
        # The real decision rules; only the sys file reader is left out.
        duplicate = duplicate[:duplicate.index('\t#if sys')] + '}\n' if '\t#if sys' in duplicate else duplicate
        duplicate = duplicate.replace('package;', '')
        fixture = '''import BaseGameDuplicate.ChartFingerprint;
typedef Song = {songName:String, sourceFolder:String, importProvenancePresent:Bool, ownerRoot:String};
class Probe {
	public static var measured:Array<String> = [];
	public static function resolve(p:String):String return p;
	public static function measure(path:String, into:ChartFingerprint) {
		measured.push(path);
		// Same-sized instrumentals for the two charts named like a base song.
		into.audioBytes = path.indexOf('remix') >= 0 ? 999 : 4321;
		into.audioSeconds = path.indexOf('remix') >= 0 ? 120 : 90;
	}
}
class FreeplayRegistry {
	public static function getJson():Dynamic {
		var songs:Array<Dynamic> = ['bopeebo', {name: 'fresh'}, 'dad-battle'];
		return [{name: 'Base Game', songs: songs}];
	}
}
@:allow(Main)
class State {
	static var duplicateCache:Map<String, Bool> = [];
	static var baseFingerprints:Null<Array<ChartFingerprint>> = null;
	static var baseFingerprintSongs:Array<String> = [];
	static var baseFingerprintAudio:Array<Bool> = [];
	public var songs:Array<Song> = [];
	public function new() {}
	function safeSongFolder(name:String) return true;
	function resolveSongIdentity(song:Song) {}
	function previewInstPath(name:String):String return 'music/' + name;
	function readFingerprintChart(name:String, print:ChartFingerprint) { print.bpm = 100; print.player = 'bf'; print.opponent = 'dad'; }
	function sharedNoteCounts(a:String, b:String):Array<Int> return [100, 100];
	public ''' + body.strip() + '''
}
class Main {
	static function check(ok:Bool, message:String) if (!ok) throw message;
	static function main() {
		var state = new State();
		state.songs = [
			{songName: 'unrelated--mod-a', sourceFolder: 'my-original-song', importProvenancePresent: true, ownerRoot: 'a'},
			{songName: 'another--mod-b', sourceFolder: '', importProvenancePresent: true, ownerRoot: 'b'},
			{songName: 'bopeebo--mod-c', sourceFolder: 'bopeebo', importProvenancePresent: true, ownerRoot: 'c'},
			{songName: 'fresh-remix--mod-d', sourceFolder: 'fresh', importProvenancePresent: true, ownerRoot: 'd'},
			{songName: 'native', sourceFolder: '', importProvenancePresent: false, ownerRoot: ''}
		];
		check(!state.baseDuplicate(0) && !state.baseDuplicate(1), 'unrelated charts are not duplicates');
		check(Probe.measured.length == 0, 'charts sharing no base title read no audio, read ' + Probe.measured);
		check(state.baseDuplicate(2), 'a same-titled copy with the same instrumental is a duplicate');
		check(Probe.measured.join(',') == 'music/bopeebo--mod-c,music/bopeebo', 'only the matching chart and its base song are measured: ' + Probe.measured);
		check(!state.baseDuplicate(3), 'a remix with its own instrumental is kept');
		check(Probe.measured.join(',') == 'music/bopeebo--mod-c,music/bopeebo,music/fresh-remix--mod-d,music/fresh', 'base audio is measured once, on first title match: ' + Probe.measured);
		check(!state.baseDuplicate(4), 'native charts are never duplicates');
		state.baseDuplicate(2); state.baseDuplicate(3);
		check(Probe.measured.length == 4, 'decisions are remembered');
		Sys.println('ok');
	}
}
'''
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            (Path(folder) / 'BaseGameDuplicate.hx').write_text(duplicate, encoding='utf-8', newline='\n')
            (Path(folder) / 'FreeplayPulse.hx').write_text(
                'class FreeplayPulse { public static function bpmFromChartText(t:String):Float return 100; }\n',
                encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'Main', '--interp'],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
