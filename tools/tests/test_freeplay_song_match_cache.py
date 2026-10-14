"""Freeplay keeps each song's filter answer until an input of the filter changes.

One scroll step in the library browser asked songMatches about every song four
or five times (ordering, chart rows, layout, details), which was most of the
step's cost. The production songMatches, syncSongMatchInputs and
invalidateSongMatches run here with a counting filter: repeated questions are
answered from the cache, and every input the filter reads (search text,
category, favourites, hidden entries, library view, sound test, the library
save, the duplicate option, the asset path epoch, and the song at that index)
makes it ask again.
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


class FreeplaySongMatchCacheTest(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / 'source/FreeplayState.hx').read_text(encoding='utf-8')

    def test_relabel_callback_drops_cached_answers(self):
        # Library management resets resolved source labels, which a search reads.
        reset = self.source.index('song.sourceLabel = song.registrySourceLabel; }')
        self.assertIn('invalidateSongMatches();', self.source[reset:reset + 200])
        # The uncached filter keeps the original rules.
        uncached = method(self.source, '\tfunction songMatchesUncached(i:Int):Bool {')
        for rule in ('libraryHidden(i)', 'matchesCategories(categoryFilters', 'isFavorite(libraryChartKey(i))', 'searchNorm(searchString)'):
            self.assertIn(rule, uncached)

    def test_answers_are_cached_until_an_input_changes(self):
        source = self.source
        cached = method(source, '\tfunction songMatches(i:Int):Bool {')
        sync = method(source, '\tfunction syncSongMatchInputs():Void {')
        invalidate = method(source, '\tfunction invalidateSongMatches():Void {')
        fields = [l.strip() for l in source.splitlines() if l.startswith('\tvar songMatch')]
        self.assertGreaterEqual(len(fields), 11, fields)
        fixture = '''
class UserLibraryData { public function new() {} }
class UserLibrary {
	public static var current = new UserLibraryData();
	public static function data():UserLibraryData return current;
}
class OptionsHandler { public static var options = {showDuplicateBaseCharts: false}; }
class FNFAssets {
	public static var epoch = 4;
	public static function pathEpoch():Int return epoch;
}
class SongMetadata { public var songName:String; public function new(name:String) songName = name; }
class State {
	public static var favoritesOnly:Bool = false;
	public static var showHiddenEntries:Bool = false;
	public static var categoryFilters:Array<String> = [];
	public static var libraryViewId:String = '';
	public var soundTest = false;
	public var searchString = '';
	public var songs:Array<SongMetadata> = [for (name in ['alpha', 'beta', 'gamma']) new SongMetadata(name)];
	public var asked:Array<String> = [];
	''' + '\n\t'.join(fields) + '''
	public function new() {}
	function songMatchesUncached(i:Int):Bool {
		var name = songs[i].songName;
		asked.push(name);
		if (favoritesOnly && name != 'beta') return false;
		if (categoryFilters.length > 0 && categoryFilters.indexOf(name) < 0) return false;
		return searchString == '' || name.indexOf(searchString) >= 0;
	}
	public ''' + cached.strip() + '''
	public ''' + sync.strip() + '''
	public ''' + invalidate.strip() + '''
	public function all():String return [for (i in 0...songs.length) songMatches(i) ? '1' : '0'].join('');
}
class Main {
	static function check(ok:Bool, message:String) if (!ok) throw message;
	static function main() {
		var state = new State();
		check(state.all() == '111' && state.asked.length == 3, 'first pass asks each song once');
		for (round in 0...4) state.all();
		check(state.asked.length == 3, 'later passes are answered from the cache: ' + state.asked);
		check(!state.songMatches(-1) && !state.songMatches(3), 'out of range is not a match');
		state.searchString = 'ta';
		check(state.all() == '010' && state.asked.length == 6, 'new search text asks again');
		State.categoryFilters = ['beta', 'gamma'];
		state.searchString = '';
		check(state.all() == '011', 'a replaced category list asks again');
		var before = state.asked.length;
		State.favoritesOnly = true;
		check(state.all() == '010' && state.asked.length == before + 3, 'favourites only asks again');
		State.favoritesOnly = false;
		state.all();
		before = state.asked.length;
		UserLibrary.current = new UserLibraryData();
		state.all();
		check(state.asked.length == before + 3, 'a saved library edit asks again');
		FNFAssets.epoch++;
		state.all();
		check(state.asked.length == before + 6, 'a new path epoch asks again');
		OptionsHandler.options.showDuplicateBaseCharts = true;
		state.all();
		check(state.asked.length == before + 9, 'the duplicate option asks again');
		State.showHiddenEntries = true;
		state.all();
		State.libraryViewId = 'favorites';
		state.all();
		state.soundTest = true;
		state.all();
		check(state.asked.length == before + 18, 'hidden entries, library view and sound test each ask again');
		before = state.asked.length;
		state.songs.splice(0, 1);
		check(state.all() == '11', 'a removed song shifts the list');
		check(state.asked.length == before + 2, 'shifted indexes hold other songs and ask again');
		state.songs.push(new SongMetadata('delta'));
		check(state.all() == '110' && state.asked.length == before + 3, 'only the new song is asked');
		state.invalidateSongMatches();
		state.all();
		check(state.asked.length == before + 6, 'an explicit invalidation asks again');
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
