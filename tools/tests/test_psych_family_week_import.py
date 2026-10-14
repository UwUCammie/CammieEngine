"""Psych and Nightmare Vision weeks become Story Mode weeks through one shared reader."""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath

ROOT = Path(__file__).resolve().parents[2]


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if isinstance(value, str) else json.dumps(value), encoding='utf-8')


def extract(source, marker):
    start = source.index(marker)
    opening = source.index('{', start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError('unterminated block: ' + marker)


WEEKS = {
    'w1': {'storyName': 'First Week', 'songs': [['Song One', 'dad', [0, 0, 0]], ['Song Two', 'dad', [0, 0, 0]]],
           'weekCharacters': ['dad', 'bf', ''], 'weekBefore': 'tutorial', 'startUnlocked': True},
    'w2': {'storyName': 'Second Week', 'songs': [['Not Imported', 'x', [0, 0, 0]], ['Song Three', 'x', [0, 0, 0]]],
           'weekCharacters': ['custom', 'bf', 'gf'], 'weekBefore': 'w1', 'hiddenUntilUnlocked': True},
    'secret': {'storyName': 'Hidden', 'songs': [['Song One', 'x', [0, 0, 0]]], 'hideStoryMode': True},
    'empty': {'storyName': 'Nothing', 'songs': []},
}


class PsychFamilyWeekImportTest(unittest.TestCase):
    def run_haxe(self, folder, body, *args, cwd=ROOT):
        (folder / 'Main.hx').write_text(body, encoding='utf-8')
        result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(folder),
            '--run', 'Main', *map(str, args)], cwd=cwd, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_both_engines_convert_the_same_weeks(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            base = FixturePath(temp)
            for name, week in WEEKS.items():
                put(base / 'psych/weeks' / (name + '.json'), week)
                put(base / 'nv/data/weeks' / (name + '.json'), week)
            # weekList.txt puts w2 first; unlisted weeks follow by name.
            put(base / 'psych/weeks/weekList.txt', 'w2\n../escape\nw2\n')
            put(base / 'nv/data/weeks/weekList.txt', 'w2\n')
            output = self.run_haxe(base, r'''class Main {static function main(){
var base = Sys.args()[0];
function convert(root:String, nightmare:Bool):Array<Dynamic> {
	var source = PsychFamilyWeekImport.readSource(root, root, root + '/data', nightmare, haxe.Json.parse);
	return cast PsychFamilyWeekImport.storyWeeks(source, nightmare);
}
Sys.println(haxe.Json.stringify({psych:convert(base + '/psych', false), nv:convert(base + '/nv', true)}));
}}''', base)
            data = json.loads(output.strip().splitlines()[-1])
            psych, nv = data['psych'], data['nv']
            self.assertEqual([w['file'] for w in psych], ['w2', 'w1'])
            self.assertEqual(psych[0]['songs'], ['not-imported', 'song-three'])
            self.assertEqual(psych[1]['characters'], ['dad', 'bf', ''])
            self.assertTrue(psych[0]['weekBeforeLocal'])
            self.assertFalse(psych[1]['weekBeforeLocal'])
            self.assertTrue(psych[0]['hiddenUntilUnlocked'])
            self.assertEqual(psych[0]['art'], 'images/storymenu/w2.png')
            self.assertEqual(nv[0]['art'], 'images/menus/story/weeks/w2.png')
            # A missing startUnlocked reads as locked in Psych and unlocked in the fork.
            self.assertFalse(psych[0]['startUnlocked'])
            self.assertTrue(nv[0]['startUnlocked'])
            # Apart from those two engine facts the conversion is identical.
            for week in psych + nv:
                week.pop('art')
                week.pop('startUnlocked')
            self.assertEqual(psych, nv)

    def test_owner_record_merges_and_offers_only_installed_songs(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            base = FixturePath(temp)
            owner = base / 'assets/imported_mods/psych-engine-pack-0123456789'
            put(base / 'assets/data/song-one/song-one.json', '{}')
            put(base / 'assets/data/song-three--pack/song-three--pack.json', '{}')
            put(owner / 'images/storymenu/w1.png', 'png')
            put(base / 'assets/imported_mods/broken-owner/' / '.cammie-story-weeks.json', 'not json')
            output = self.run_haxe(base, r'''class Main {
static function check(v:Bool, m:String) if (!v) throw m;
static function main(){
var owner = 'assets/imported_mods/psych-engine-pack-0123456789';
var weeks:Array<PsychFamilyWeekImport.PsychFamilyStoryWeek> = [
	{file:'w1', storyName:'First Week', songs:['song-one', 'song-two'], characters:['dad', 'bf', ''],
		startUnlocked:true, weekBefore:'tutorial', weekBeforeLocal:false, hiddenUntilUnlocked:false, art:'images/storymenu/w1.png'},
	{file:'w2', storyName:'Second Week', songs:['not-imported', 'song-three'], characters:['custom', 'bf', 'gf'],
		startUnlocked:false, weekBefore:'w1', weekBeforeLocal:true, hiddenUntilUnlocked:true, art:'images/storymenu/w2.png'}
];
// The first batch imports song-one; a later batch adds song-three under a renamed folder.
check(ImportedStoryWeeks.write(owner, 'Psych Engine', weeks, ['song-one' => 'song-one']), 'first write failed');
var first = sys.io.File.getContent(owner + '/' + ImportedStoryWeeks.FILE_NAME);
check(ImportedStoryWeeks.write(owner, 'Psych Engine', weeks, ['song-one' => 'song-one']), 'repeat write failed');
check(sys.io.File.getContent(owner + '/' + ImportedStoryWeeks.FILE_NAME) == first, 'repeat import changed the record');
check(ImportedStoryWeeks.write(owner, 'Psych Engine', weeks, ['song-three' => 'song-three--pack', 'bad' => '../x']), 'second write failed');
// An owner with no weeks and no earlier record gets no file.
check(ImportedStoryWeeks.write('assets/imported_mods/psych-engine-none-0123456789', 'Psych Engine', [], ['a' => 'a']), 'empty write failed');
check(!sys.FileSystem.exists('assets/imported_mods/psych-engine-none-0123456789'), 'empty owner got a record');
var found = ImportedStoryWeeks.collect();
Sys.println(haxe.Json.stringify(found));
// The base game's storySonglist.json is never touched.
check(!sys.FileSystem.exists('assets/data/storySonglist.json'), 'shared story list written');
// Records written for another engine do not keep the old song map.
var other = ImportedStoryWeeks.merge(first, 'Nightmare Vision', null, new Map());
check(haxe.Json.parse(other).weeks.length == 0 && Reflect.fields(haxe.Json.parse(other).songs).length == 0, 'engine change kept stale record');
}}''', cwd=base)
            found = json.loads(output.strip().splitlines()[-1])
            self.assertEqual([w['key'] for w in found],
                             ['psych-engine-pack-0123456789:w1', 'psych-engine-pack-0123456789:w2'])
            self.assertEqual(found[0]['songs'], ['song-one'])
            self.assertEqual(found[0]['unlockAfter'], 'tutorial')
            self.assertEqual(found[0]['art'], 'assets/imported_mods/psych-engine-pack-0123456789/images/storymenu/w1.png')
            self.assertEqual(found[1]['songs'], ['song-three--pack'])
            self.assertEqual(found[1]['unlockAfter'], 'psych-engine-pack-0123456789:w1')
            self.assertEqual(found[1]['art'], '')
            self.assertEqual(found[1]['characters'], ['custom', 'bf', 'gf'])
            record = json.loads((owner / '.cammie-story-weeks.json').read_text(encoding='utf-8'))
            self.assertEqual(record['songs'], {'song-one': 'song-one', 'song-three': 'song-three--pack'})

    def test_lock_rule_matches_the_source_engines(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            base = FixturePath(temp)
            self.run_haxe(base, r'''class Main {
static function check(v:Bool, m:String) if (!v) throw m;
static function main(){
var done = function(name:String) return name == 'done';
check(!PsychFamilyWeekImport.locked(true, 'missing', done), 'start unlocked week locked');
check(!PsychFamilyWeekImport.locked(false, '', done), 'week with no previous week locked');
check(!PsychFamilyWeekImport.locked(false, 'done', done), 'completed previous week still locks');
check(PsychFamilyWeekImport.locked(false, 'missing', done), 'unfinished previous week unlocked');
}}''')

    def test_importer_groups_weeks_by_owner(self):
        source = (ROOT / 'source/ModuleFunctions.hx').read_text(encoding='utf-8')
        writer = '\n'.join(extract(source, marker) for marker in (
            'static function writeImportedStoryWeeks', 'static function copyImportFileNonOverwriting'))
        self.assertIn('writeImportedStoryWeeks(importedSongs)', source)
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            base = FixturePath(temp)
            put(base / 'donor/title.png', 'png')
            body = r'''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
typedef SongImport = Dynamic;
typedef ImportAssetMergeResult = {var copied:Int; var skipped:Int; var failed:Int; @:optional var errors:Array<String>;};
class Main {
static function validModuleName(name:String):Bool return name != null && name != '' && name.indexOf('/') < 0;
static function importSongFolderName(song:Dynamic):String return song.destinationFolder;
static function ensureDirectory(path:String):Void if (!FileSystem.exists(path)) FileSystem.createDirectory(path);
static function reportImportProgress(phase:String, current:String, completed:Int = 0, total:Int = 0,
	copied:Int = 0, skipped:Int = 0, failed:Int = 0, work:Int = 0):Void {}
WRITER
static function check(v:Bool, m:String) if (!v) throw m;
static function main(){
var weeks:Array<PsychFamilyWeekImport.PsychFamilyStoryWeek> = [{file:'w1', storyName:'W', songs:['song-one', 'two'],
	characters:['', '', ''], startUnlocked:true, weekBefore:'', weekBeforeLocal:false, hiddenUntilUnlocked:false, art:''}];
var levels:Array<PsychFamilyWeekImport.PsychFamilyStoryWeek> = [{file:'level1', storyName:'L', songs:['x'],
	characters:['', '', ''], startUnlocked:true, weekBefore:'', weekBeforeLocal:false, hiddenUntilUnlocked:false,
	art:VSliceStoryWeeks.TITLE_FOLDER + '/level1.png'}];
var titles = ['level1' => Path.join([Sys.getCwd(), 'donor', 'title.png'])];
var songs:Array<Dynamic> = [
	{engine:'Psych Engine', sourceRoot:'source/mods/Pack', sourceFolder:'Song One', destinationFolder:'song-one', authoredStoryWeeks:weeks},
	{engine:'Psych Engine', sourceRoot:'source/mods/Pack', sourceFolder:'two', destinationFolder:'two--pack', authoredStoryWeeks:weeks},
	{engine:'V-Slice', sourceRoot:'source/other', sourceFolder:'X', destinationFolder:'x-song', authoredStoryWeeks:levels,
		authoredStoryArt:titles},
	{engine:'Codename Engine', sourceRoot:'source/third', sourceFolder:'y', destinationFolder:'y', authoredStoryWeeks:weeks}
];
check(writeImportedStoryWeeks(songs).length == 0, 'writer reported a failure');
var owner = CompatScriptManifest.destinationRoot('source/mods/Pack', 'Psych Engine');
var record = haxe.Json.parse(File.getContent(owner + '/' + ImportedStoryWeeks.FILE_NAME));
var levelOwner = CompatScriptManifest.destinationRoot('source/other', 'V-Slice');
var levelRecord = haxe.Json.parse(File.getContent(levelOwner + '/' + ImportedStoryWeeks.FILE_NAME));
check(FileSystem.exists(levelOwner + '/' + VSliceStoryWeeks.TITLE_FOLDER + '/level1.png'), 'level title not copied');
check(File.getContent(levelOwner + '/' + ImportedStoryWeeks.FILE_NAME).indexOf('donor') < 0, 'donor path persisted');
Sys.println(haxe.Json.stringify({psych:record.songs, vslice:levelRecord.songs}));
check(FileSystem.readDirectory('assets/imported_mods').length == 2, 'an engine without weeks got a record');
}}'''
            body = body.replace('WRITER', writer)
            output = self.run_haxe(base, body, cwd=base)
            self.assertEqual(json.loads(output.strip().splitlines()[-1]),
                             {'psych': {'song-one': 'song-one', 'two': 'two--pack'}, 'vslice': {'x': 'x-song'}})

    def test_vslice_levels_become_owner_weeks(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            base = FixturePath(temp)
            put(base / 'mod/data/levels/week2.json', {'name': 'SECOND', 'titleAsset': 'storymenu/titles/week2',
                'songs': ['Spookeez', 'south', 'spookeez'], 'background': '#F9CF51', 'props': []})
            put(base / 'mod/data/levels/week1.json', {'name': 'FIRST', 'titleAsset': 'storymenu/titles/missing',
                'songs': ['bopeebo'], 'background': 'some/image'})
            put(base / 'mod/data/levels/secret.json', {'name': 'HIDDEN', 'songs': ['x'], 'visible': False})
            put(base / 'mod/data/levels/empty.json', {'name': 'NONE', 'songs': []})
            put(base / 'mod/data/levels/broken.json', '{not json')
            put(base / 'mod/images/storymenu/titles/week2.png', 'png')
            output = self.run_haxe(base, r'''class Main {static function main(){
var found = VSliceStoryWeeks.read(Sys.args()[0] + '/mod');
Sys.println(haxe.Json.stringify({weeks:found.weeks, titles:[for (key in found.titles.keys()) key]}));
}}''', base)
            data = json.loads(output.strip().splitlines()[-1])
            weeks = data['weeks']
            # Level-id order; hidden, empty and unreadable levels stay out.
            self.assertEqual([w['file'] for w in weeks], ['week1', 'week2'])
            self.assertEqual(weeks[1]['songs'], ['spookeez', 'south'])
            self.assertEqual(weeks[1]['storyName'], 'SECOND')
            self.assertTrue(all(w['startUnlocked'] and w['weekBefore'] == '' for w in weeks))
            # Only a title image that exists is copied and named as art.
            self.assertEqual(weeks[1]['art'], 'images/vslice-level-titles/week2.png')
            self.assertEqual(weeks[0]['art'], '')
            self.assertEqual(data['titles'], ['week2'])

    def test_reimported_existing_songs_still_reach_owner_records(self):
        # A re-import of an installed song skips importSong, but its owner records
        # (story weeks among them) are written from importedSongs, so both
        # Psych-family engines must be put back there. Only the converting
        # engines get the visual repair.
        source = (ROOT / 'source/ModuleFunctions.hx').read_text(encoding='utf-8').replace('\r\n', '\n')
        start = source.index('if (songTargetExists(songData.name, storageKey) && !songNeedsRepair(songData)) {')
        branch = source[start:source.index('reportImportProgress(', start)]
        gate = branch.index('if ((songData.engine')
        added = branch.index('importedSongs.set(storageKey, songData);', gate)
        condition = branch[gate:added]
        for engine in ('PSYCH', 'NIGHTMARE_VISION', 'CODENAME', 'V_SLICE'):
            self.assertIn('ImportEngine.' + engine, condition)
        repair = branch[added:branch.index('mergeConvertedVisuals(songData)', added)]
        self.assertIn('songData.engine == ImportEngine.CODENAME || songData.engine == ImportEngine.V_SLICE', repair)
        self.assertNotIn('NIGHTMARE_VISION', repair)

    def test_vslice_discovery_hands_levels_to_the_base_variation(self):
        source = (ROOT / 'source/ModuleFunctions.hx').read_text(encoding='utf-8')
        discovery = extract(source, 'static function discoverVSliceSongImports')
        self.assertIn('VSliceStoryWeeks.read(', discovery)
        base_branch = discovery[discovery.index("Reflect.setField(songData, 'destinationFolder', nativeSongName);"):]
        self.assertLess(base_branch.index('else {'), base_branch.index("'authoredStoryWeeks'"))

    def test_menu_lists_weeks_with_the_source_lock_and_hide_rules(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            base = FixturePath(temp)
            output = self.run_haxe(base, r'''class Main {
static function week(key:String, startUnlocked:Bool, after:String, hidden:Bool):ImportedStoryWeeks.ImportedStoryWeek
	return {key:key, owner:'o', title:key, songs:['s'], characters:['', '', ''], startUnlocked:startUnlocked,
		unlockAfter:after, hiddenUntilUnlocked:hidden, art:''};
static function list(ignore:Bool, done:Array<String>):String {
	var weeks = [
		week('o:open', true, 'o:missing', false),
		week('o:afterBase', false, 'week1', false),
		week('o:afterOpen', false, 'o:open', false),
		week('o:secret', false, 'o:open', true),
		week('o:orphan', false, 'o:not-installed', false)
	];
	return [for (entry in ImportedStoryWeeks.menuWeeks(weeks, ['tutorial', 'week1'], ignore, function(name) return done.indexOf(name) >= 0))
		entry.week.key + '=' + (entry.locked ? 'locked' : 'open')].join(',');
}
static function main() {
	Sys.println(list(false, []));
	Sys.println(list(false, ['week1', 'o:open']));
	Sys.println(list(true, []));
	Sys.println(ImportedStoryWeeks.menuWeeks(null, null, false, function(_) return false).length);
}}''')
            lines = output.strip().splitlines()[-4:]
            # Nothing completed: weeks behind a base or local week lock, the hidden one
            # is left out, and a week behind a week that is not installed stays open.
            self.assertEqual(lines[0], 'o:open=open,o:afterBase=locked,o:afterOpen=locked,o:orphan=open')
            # Completing the previous weeks unlocks them and reveals the hidden week.
            self.assertEqual(lines[1], 'o:open=open,o:afterBase=open,o:afterOpen=open,o:secret=open,o:orphan=open')
            # The ignore-unlocks option opens and shows everything.
            self.assertEqual(lines[2], 'o:open=open,o:afterBase=open,o:afterOpen=open,o:secret=open,o:orphan=open')
            self.assertEqual(lines[3], '0')

    def test_story_menu_builds_imported_weeks_without_the_shared_list(self):
        menu = (ROOT / 'source/StoryMenuState.hx').read_text(encoding='utf-8')
        item = (ROOT / 'source/MenuItem.hx').read_text(encoding='utf-8')
        self.assertIn('ImportedStoryWeeks.collect()', menu)
        # The menu takes lock and hide decisions from the tested shared helper.
        self.assertIn('ImportedStoryWeeks.menuWeeks(', menu)
        self.assertIn('importedWeekLocked.set(visibleIndex, locked)', menu)
        self.assertIn('importedWeeks.get(i)', menu)
        # The imported branch returns before the storySonglist.json lookup by index.
        constructor = item[item.index('public function new'):]
        lookup = constructor.index('getJson("assets/data/storySonglist")')
        self.assertLess(constructor.index('if (imported != null)'), lookup)
        self.assertLess(constructor.index('return;'), lookup)


if __name__ == '__main__':
    unittest.main()
