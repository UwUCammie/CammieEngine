"""V-Slice SongRegistry, LevelRegistry, PlayStatePlaylist and loadPlayState planning over installed imports."""
import json
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''import VSliceSongRegistry.VSliceSongEntry;
class Main {
 static function check(condition:Bool, message:String):Void if (!condition) throw message;
 static function main() {
  var ownerA = 'assets/imported_mods/v-slice-a';
  var ownerB = 'assets/imported_mods/v-slice-b';
  VSliceRegistryCatalog.ownerRoots = function() return [ownerA];
  var songs = VSliceSongRegistry.instance;
  var song = songs.fetchEntry('songa');
  check(song != null, 'authored id of the active owner was not found');
  check(song.variations.join(',') == 'default,erect', 'variations: ' + song.variations.join(','));
  check(song.songName == 'Song A', 'display name: ' + song.songName);
  check(song.getDifficulty('hard').storageFolder == 'songa', 'default variation chart folder');
  check(song.getDifficulty('erect', 'erect').storageFolder == 'songa-erect', 'variation chart folder');
  check(song.getDifficulty('erect') == null, 'the default variation has no erect chart');
  check(song.getDifficulty(null).difficulty == 'normal', 'no difficulty means the default one');
  check(song.listDifficulties().join(',') == 'easy,normal,hard,erect,nightmare', 'difficulties: ' + song.listDifficulties().join(','));
  check(song.getFirstValidVariation('nightmare') == 'erect', 'first variation with a nightmare chart');
  var chart = song.getDifficulty('hard');
  check(chart.characters.opponent == 'dad' && chart.stage == 'stage' && chart.scrollSpeed == 2.5, 'chart header fields');
  check(song.getRawMetadata()[0].playData.characters.opponent == 'dad', 'raw metadata opponent');
  var qualified = songs.fetchEntry('songb');
  check(qualified.storageFolder() == 'songb--v-slice-a', 'owner-qualified folder: ' + qualified.storageFolder());
  check(songs.fetchEntry('songb--v-slice-a').id == 'songb', 'installed folder names resolve to the same song');
  check(songs.fetchEntry('missing') == null, 'unknown ids give null');
  check(VSliceRegistryCatalog.folderDisplay('songa-erect') == 'Song A Erect', 'recorded display name');
  check(VSliceRegistryCatalog.folderVariation('songa-erect') == 'erect' && VSliceRegistryCatalog.folderVariation('songa') == 'default',
   'folder variations');
  check(VSliceRegistryCatalog.folderDisplay('basesong') == '', 'no recorded name for a base-game folder');

  VSliceRegistryCatalog.ownerRoots = function() return [ownerB];
  check(songs.fetchEntry('songa').storageFolder() == 'songa--other', 'the active owner wins a shared id');
  VSliceRegistryCatalog.ownerRoots = function() return [];
  check(songs.fetchEntry('basesong').storageFolder() == 'basesong', 'base-game songs resolve without an owner');

  VSliceRegistryCatalog.ownerRoots = function() return [ownerA];
  var levels = VSliceLevelRegistry.instance;
  check(levels.listSortedLevelIds().join(',') == 'week1', 'level ids: ' + levels.listSortedLevelIds().join(','));
  var level = levels.fetchEntry('week1');
  check(level.getTitle() == 'First Week' && level.isUnlocked(), 'level title and lock state');
  check(level.getSongs().join(',') == 'songa,songb--v-slice-a', 'level songs: ' + level.getSongs().join(','));
  check(level._data.name == 'First Week', 'level data name');
  check(level.getDifficulties().join(',') == 'normal,hard', 'level difficulties: ' + level.getDifficulties().join(','));

  VSlicePlayStatePlaylist.reset();
  VSlicePlayStatePlaylist.isStoryMode = true;
  check(VSlicePlayStatePlaylist.isStoryMode && HxcCompatRuntime.playStatePlaylistIsStoryMode, 'story flag is shared with the lowered alias');
  VSlicePlayStatePlaylist.playlistSongIds = level.getSongs();
  var first = VSlicePlayStatePlaylist.playlistSongIds.shift();
  VSlicePlayStatePlaylist.campaignId = 'week1';
  var plan = VSliceSongLaunchPlan.resolve({targetSong: songs.fetchEntry(first), targetDifficulty: 'hard'}, true);
  check(plan.error == null, 'story plan failed: ' + plan.error);
  check(plan.folder == 'songa' && plan.difficulty == 'hard', 'story plan chart');
  check(plan.storyFolders.join(',') == 'songa,songb--v-slice-a', 'story playlist folders: ' + plan.storyFolders.join(','));
  check(plan.levelKey == 'v-slice-a:week1', 'campaign week key: ' + plan.levelKey);
  // A menu that never sets campaignId: the level whose playlist matches is the week.
  VSlicePlayStatePlaylist.campaignId = null;
  VSlicePlayStatePlaylist.playlistSongIds = ['songb--v-slice-a'];
  var unnamed = VSliceSongLaunchPlan.resolve({targetSong: 'songa', targetDifficulty: 'hard'}, true);
  check(unnamed.levelKey == 'v-slice-a:week1', 'week key from the playlist: ' + unnamed.levelKey);
  // A partial playlist is no known week, so no week's score or unlock is touched.
  VSlicePlayStatePlaylist.playlistSongIds = [];
  var partial = VSliceSongLaunchPlan.resolve({targetSong: 'songa', targetDifficulty: 'hard'}, true);
  check(partial.error == null && partial.levelKey == null, 'a partial playlist names no week: ' + partial.levelKey);
  VSlicePlayStatePlaylist.campaignId = 'week1';

  var fallback = VSliceSongLaunchPlan.resolve({targetSong: 'songa', targetDifficulty: 'hard', targetVariation: 'pico'}, false);
  check(fallback.error == null && fallback.folder == 'songa', 'an uninstalled variation plays the base chart');
  var variant = VSliceSongLaunchPlan.resolve({targetSong: song, targetDifficulty: 'nightmare', targetVariation: 'erect'}, false);
  check(variant.folder == 'songa-erect' && variant.storyFolders.length == 0, 'variation plan');
  check(VSliceSongLaunchPlan.resolve({targetSong: 'missing'}, false).error != null, 'unknown songs are refused');
  check(VSliceSongLaunchPlan.resolve({targetSong: song, targetDifficulty: 'insane'}, false).error != null, 'missing charts are refused');

  VSlicePlayStatePlaylist.reset();
  check(!VSlicePlayStatePlaylist.isStoryMode && VSlicePlayStatePlaylist.playlistSongIds.length == 0
   && VSlicePlayStatePlaylist.campaignId == null, 'reset clears the campaign');
  var music = songs.parseMusicDataRaw('{"songName": "Intro", "timeChanges": [{"t": 0, "bpm": 130}]}');
  check(music.timeChanges[0].bpm == 130, 'raw music data');
  check(songs.parseMusicDataRaw('not json') == null, 'invalid music data gives null');
  // The installed-song listing is cached between lookups; invalidate() rereads it.
  sys.FileSystem.createDirectory('assets/data/latesong');
  sys.io.File.saveContent('assets/data/latesong/latesong.json', '{"song": {"song": "latesong"}}');
  VSliceRegistryCatalog.ownerRoots = function() return [];
  check(songs.fetchEntry('latesong') == null, 'a lookup right after another reuses the cached listing');
  VSliceRegistryCatalog.invalidate();
  check(songs.fetchEntry('latesong') != null, 'invalidate picks up a newly installed song');
  var player = VSlicePlayerRegistry.instance.fetchEntry('bf');
  check(player.getName() == 'bf' && player.getFreeplayDJText(1) == '', 'a player without a record answers empty fields');
  check(VSlicePlayerRegistry.instance.fetchEntry('pico') != null, 'the other base-game player always exists');
  check(VSlicePlayerRegistry.instance.fetchEntry('nobody') == null
   && !VSlicePlayerRegistry.instance.hasEntry('nobody'), 'an unknown player id is null, as in V-Slice');
  // The character-to-player map follows the active package, not the first one asked.
  var players = VSlicePlayerRegistry.instance;
  check(players.getCharacterOwnerId('hero-char') == null, 'no active owner means no owning player');
  VSliceRegistryCatalog.ownerRoots = function() return [ownerA];
  check(players.getCharacterOwnerId('hero-char') == 'hero', 'the active owner player owns its character');
  VSliceRegistryCatalog.ownerRoots = function() return [ownerB];
  check(players.getCharacterOwnerId('hero-char') == null && players.getCharacterOwnerId('rival-char') == 'rival',
   'another active owner does not reuse the first owner players');
  VSliceRegistryCatalog.ownerRoots = function() return [];
  // Swapping one song for another keeps the folder count; the listing still changes.
  sys.FileSystem.deleteFile('assets/data/latesong/latesong.json');
  sys.FileSystem.deleteDirectory('assets/data/latesong');
  sys.FileSystem.createDirectory('assets/data/swapsong');
  sys.io.File.saveContent('assets/data/swapsong/swapsong.json', '{"song": {"song": "swapsong"}}');
  @:privateAccess VSliceRegistryCatalog.lastListingStamp = -1;
  check(songs.fetchEntry('swapsong') != null && songs.fetchEntry('latesong') == null,
   'a same-size listing change rebuilds the index');
 }
}
'''


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if isinstance(value, str) else json.dumps(value), newline='\n')


def provenance(owner, source, destination, display):
    return {'version': 1, 'sourceOwner': owner, 'sourceFolder': source,
            'destinationFolder': destination, 'display': display}


def chart(opponent='dad'):
    return {'song': {'song': 'x', 'player1': 'bf', 'player2': opponent, 'gf': 'gf', 'stage': 'stage',
                     'speed': 2.5, 'bpm': 150, 'notes': []}}


class VSliceRegistryFacadesTest(unittest.TestCase):
    def test_registries_resolve_installed_imports(self):
        owner_a = 'assets/imported_mods/v-slice-a'
        owner_b = 'assets/imported_mods/v-slice-b'
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            base = Path(folder)
            data = base / 'assets/data'
            write(data / 'songa/importProvenance.json', provenance(owner_a, 'songa', 'songa', 'Song A'))
            write(data / 'songa/songa.json', chart())
            write(data / 'songa/songa-hard.json', chart())
            write(data / 'songa/songa-easy.json', chart())
            write(data / 'songa/songa-events.json', {})
            write(data / 'songa-erect/importProvenance.json', provenance(owner_a, 'songa', 'songa-erect', 'Song A Erect'))
            write(data / 'songa-erect/songa-erect-erect.json', chart())
            write(data / 'songa-erect/songa-erect-nightmare.json', chart())
            write(data / 'songb--v-slice-a/importProvenance.json', provenance(owner_a, 'songb', 'songb--v-slice-a', 'Song B'))
            write(data / 'songb--v-slice-a/songb--v-slice-a.json', chart())
            write(data / 'songb--v-slice-a/songb--v-slice-a-hard.json', chart())
            write(data / 'songa--other/importProvenance.json', provenance(owner_b, 'songa', 'songa--other', 'Other A'))
            write(data / 'songa--other/songa--other.json', chart('mom'))
            write(data / 'basesong/basesong.json', chart())
            write(base / owner_a / '.cammie-story-weeks.json', {
                'version': 1, 'engine': 'V-Slice',
                'songs': {'songa': 'songa', 'songb': 'songb--v-slice-a'},
                'weeks': [{'file': 'week1', 'storyName': 'First Week', 'songs': ['songa', 'songb'],
                           'startUnlocked': True, 'characters': ['', '', '']}]})
            (base / owner_b).mkdir(parents=True, exist_ok=True)
            write(base / owner_a / 'data/players/hero.json', {'name': 'Hero', 'ownedChars': ['hero-char']})
            write(base / owner_b / 'data/players/rival.json', {'name': 'Rival', 'ownedChars': ['rival-char']})
            write(base / 'Main.hx', MAIN)
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(base),
                '-main', 'Main', '--interp'], cwd=str(base), capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_import_handoff_refreshes_script_registries(self):
        source = (ROOT / 'source/ModuleFunctions.hx').read_text(encoding='utf-8')
        start = source.index('public static function completeImportOnMainThread(')
        body = source[start:source.index('if (songNames == null)', start)]
        self.assertIn('VSliceRegistryCatalog.invalidate();', body)
        self.assertIn('VSlicePlayerRegistry.invalidate();', body)


if __name__ == '__main__':
    unittest.main()
