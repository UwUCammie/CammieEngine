"""Freeplay reuses chart receipts and owners while the asset path epoch holds.

Opening Freeplay resolves every listed chart's receipt and owner the first time
it filters. The production cachedChartIdentity and resolveSongIdentity are run
here with a counting reader: a second Freeplay visit at the same epoch reads
nothing, an import generation or a file the engine wrote itself reads again,
and the song fields come out the same as a direct read.
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


class FreeplayIdentityCacheTest(unittest.TestCase):
    def test_identity_reads_once_per_generation(self):
        source = (ROOT / 'source/FreeplayState.hx').read_text(encoding='utf-8')
        cache = method(source, '\tstatic function cachedChartIdentity(')
        resolve = method(source, '\tfunction resolveSongIdentity(')
        fields = [l.strip() for l in source.splitlines() if l.strip().startswith('static var identityCache')]
        self.assertEqual(len(fields), 2, fields)
        # The receipt existence check is cached under the path epoch, so the
        # identity cache must use the same key, not the import generation alone.
        self.assertIn('cachedChartIdentity(song.songName, FNFAssets.pathEpoch(), LibraryChartIdentity.read)', resolve)
        fixture = '''
typedef LibraryChartRecord = {ownerRoot:String, sourceFolder:String, provenance:Dynamic, hasReceipt:Bool};
class LibraryChartIdentity {
	public static var reads:Array<String> = [];
	public static function read(folder:String):Null<LibraryChartRecord> {
		reads.push(folder);
		if (folder == 'native') return {ownerRoot: '', sourceFolder: '', provenance: null, hasReceipt: false};
		return {ownerRoot: 'mods/' + folder, sourceFolder: folder + '-src', provenance: {modName: folder}, hasReceipt: true};
	}
}
class ImportRefreshManager { public static var generation = 3; }
class FNFAssets {
	public static var localPathEpoch = 0;
	public static function pathEpoch():Int return ImportRefreshManager.generation + localPathEpoch;
}
class SongMetadata {
	public var songName:String; public var isProvisional = false; public var identityResolved = false;
	public var importProvenancePresent = false; public var provenance:Dynamic; public var sourceFolder = '';
	public var ownerRoot = ''; public var ownerResolved = false;
	public function new(name:String) songName = name;
}
class State {
	''' + '\n\t'.join(f.replace('LibraryChartIdentity.LibraryChartRecord', 'LibraryChartRecord') for f in fields) + '''
	''' + cache.replace('LibraryChartIdentity.LibraryChartRecord', 'LibraryChartRecord') + '''
	public function new() {}
	public ''' + resolve.strip() + '''
}
class Main {
	static function check(ok:Bool, message:String) if (!ok) throw message;
	static function visit():Array<SongMetadata> {
		var state = new State();
		var songs = [for (name in ['alpha', 'native', 'Beta']) new SongMetadata(name)];
		for (song in songs) { state.resolveSongIdentity(song); state.resolveSongIdentity(song); }
		return songs;
	}
	static function main() {
		var first = visit();
		check(LibraryChartIdentity.reads.join(',') == 'alpha,native,Beta', 'first visit reads each chart once: ' + LibraryChartIdentity.reads);
		check(first[0].ownerRoot == 'mods/alpha' && first[0].sourceFolder == 'alpha-src' && first[0].importProvenancePresent
			&& first[0].ownerResolved && first[1].ownerRoot == '' && !first[1].importProvenancePresent, 'fields match the read record');
		var second = visit();
		check(LibraryChartIdentity.reads.length == 3, 'a second visit in the same generation reads nothing');
		check(second[2].ownerRoot == 'mods/Beta' && second[2].sourceFolder == 'Beta-src' && second[2].identityResolved, 'cached fields match');
		ImportRefreshManager.generation++;
		visit();
		check(LibraryChartIdentity.reads.length == 6, 'a new import generation reads every chart again');
		visit();
		check(LibraryChartIdentity.reads.length == 6, 'the new epoch is cached too');
		FNFAssets.localPathEpoch++;
		visit();
		check(LibraryChartIdentity.reads.length == 9, 'a file written outside an import reads every chart again');
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
