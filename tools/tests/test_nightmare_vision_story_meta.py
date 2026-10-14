"""Source PlayState.storyMeta, prepareForSong and prepareForWeek for scripted menus."""
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''class Main {
 static function check(v:Bool, s:String):Void if (!v) throw s;
 static var loads:Array<String> = [];
 static var committed:Array<Dynamic> = [];
 static var ownerCharts = ['night-walk', 'night-walk-hard', 'night-walk-erect', 'first-light'];
 static function host():NightmareVisionStoryMeta.NightmareVisionSongPreparationHost {
  var names = ['Easy', 'Normal', 'Hard'];
  return {
   sanitize:function(name) return StringTools.replace(name, ' ', '-').toLowerCase(),
   difficultyName:function(index) return ['easy', 'normal', 'hard', 'erect'][index],
   // The base game's rule, as the session wires it: known names through SongFlow.
   resolve:function(folder, name) {
    if (names.indexOf(name.substr(0, 1).toUpperCase() + name.substr(1)) < 0) return {chart:folder + '-' + name, difficulty:1};
    var target = SongFlow.loadTarget(folder, name, null, 1, names, 1);
    return {chart:target.chart, difficulty:target.difficulty};
   },
   load:function(chart, folder) {
    loads.push(chart + '@' + folder);
    if (ownerCharts.indexOf(chart) < 0) throw 'not installed: ' + chart;
    return {song:chart};
   },
   commit:function(song, difficulty, story) committed.push([song.song, difficulty, story])
  };
 }
 static function main():Void {
  var meta = new NightmareVisionStoryMeta();
  check(meta.difficulty == 1 && meta.playlist.length == 0 && meta.score == 0, 'source StoryMeta defaults');

  check(NightmareVisionStoryMeta.prepareSong(meta, host(), 'Night Walk', 2, false) == null, 'hard chart prepares');
  check(loads[0] == 'night-walk-hard@night-walk', 'source name is sanitized and the hard suffix used: ' + loads[0]);
  check(committed[0][0] == 'night-walk-hard' && committed[0][1] == 2 && committed[0][2] == false, 'chart, native difficulty and mode are committed');
  check(meta.difficulty == 2, 'storyMeta.difficulty follows the prepared song');

  check(NightmareVisionStoryMeta.prepareSong(meta, host(), 'Night Walk', 1, true) == null, 'default difficulty prepares');
  check(loads[1] == 'night-walk@night-walk', 'the default difficulty is the plain chart');
  check(committed[1][2] == true, 'story mode is passed through');

  check(NightmareVisionStoryMeta.prepareSong(meta, host(), 'Night Walk', 3) == null, 'a difficulty the base game does not list still loads');
  check(loads[2] == 'night-walk-erect@night-walk', 'unlisted difficulty uses its own suffix');

  var error = NightmareVisionStoryMeta.prepareSong(meta, host(), 'Missing Song', 2, true);
  check(error != null && committed.length == 3 && meta.difficulty == 3, 'a missing chart returns the error and changes nothing');
  check(NightmareVisionStoryMeta.prepareSong(meta, host(), '', 1) != null, 'an empty name is an error');

  check(NightmareVisionStoryMeta.prepareWeek(meta, host(), ['First Light', 'Night Walk'], 1, true) == null, 'week prepares its first song');
  check(meta.playlist.join(',') == 'First Light,Night Walk' && committed[3][0] == 'first-light', 'the playlist is kept and the first song loaded');
  check(NightmareVisionStoryMeta.prepareWeek(meta, host(), [], 1) != null, 'an empty week is an error');

  // endSong through the week: score and misses add up, the next song comes from the owner.
  var week = new NightmareVisionStoryMeta();
  week.playlist = ['First Light', 'Night Walk']; week.difficulty = 2;
  var reports:Array<String> = [];
  var report = function(song:String, error:Dynamic) reports.push(song);
  check(NightmareVisionStoryMeta.advanceWeek(week, host(), 300, 2, report), 'the second week song is prepared');
  check(week.playlist.join(',') == 'Night Walk' && week.score == 300 && week.misses == 2, 'the finished song is counted and dropped');
  check(loads[loads.length - 1] == 'night-walk-hard@night-walk' && committed[committed.length - 1][2] == true,
   'the next song keeps the week difficulty and story mode');
  check(!NightmareVisionStoryMeta.advanceWeek(week, host(), 200, 1, report), 'the last song ends the week');
  check(week.playlist.length == 0 && week.score == 500 && week.misses == 3 && reports.length == 0, 'week totals after the last song');
  var broken = new NightmareVisionStoryMeta();
  broken.playlist = ['First Light', 'Missing Song'];
  check(!NightmareVisionStoryMeta.advanceWeek(broken, host(), 0, 0, report) && reports.join(',') == 'Missing Song',
   'a next song with no chart is reported and ends the week');
  var empty = new NightmareVisionStoryMeta();
  check(!NightmareVisionStoryMeta.advanceWeek(empty, host(), 10, 0) && empty.score == 10, 'an empty playlist still counts the song');
 }
}
'''


class NightmareVisionStoryMetaTest(unittest.TestCase):
    def test_prepare_song_and_week(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            for name in ['NightmareVisionStoryMeta', 'SongFlow']:
                (work / (name + '.hx')).write_text(
                    (ROOT / ('source/' + name + '.hx')).read_text(encoding='utf-8'), encoding='utf-8')
            (work / 'Main.hx').write_text(MAIN, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '--main', 'Main', '--interp'],
                                    cwd=work, capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_session_binds_the_source_statics(self):
        session = (ROOT / 'source/NightmareVisionStateSession.hx').read_text(encoding='utf-8')
        block = session[session.index('if (importedMenuEntry) {\n\t\t\tinterp.variables.set(\'Song\', Song);'.replace('\n', '\n')) if
                        'if (importedMenuEntry) {\n\t\t\tinterp.variables.set(\'Song\', Song);' in session
                        else session.index("interp.variables.set('Song', Song);"):]
        block = block[:block.index('NightmareVisionMainBindings.install(')]
        self.assertIn("scope.bindStaticField(PlayState, 'storyMeta', function() return storyMeta,", block)
        self.assertIn("scope.bindStaticField(PlayState, 'prepareForSong', function() return prepareSong);", block)
        self.assertIn("scope.bindStaticField(PlayState, 'prepareForWeek', function() return prepareWeek);", block)
        host = session[session.index('function songPreparationHost('):]
        host = host[:host.index('\n\t}\n') if '\n\t}\n' in host else host.index('\n\t}\r\n')]
        # The owner's installed chart and the base game's difficulty rule, nothing keyed to a mod.
        self.assertIn('ImportedMenuEntry.loadOwnedChart(mods.selectedRoot(), chart, folder)', host)
        self.assertIn('SongFlow.loadTarget(folder, name, null, PlayState.storyDifficulty, names,', host)
        self.assertIn('PlayState.SONG = song;', host)

    def test_story_week_continues_through_the_owner_playlist(self):
        session = (ROOT / 'source/NightmareVisionStateSession.hx').read_text(encoding='utf-8')
        for line in ['if (error == null) storyWeekActive = storyMode == true;']:
            self.assertEqual(session.count(line), 2, 'both prepare functions track whether a week was started')
        advance = session[session.index('public function advanceStoryWeek('):]
        advance = advance[:advance.index('function songPreparationHost(')]
        self.assertIn('if (released || !importedMenuEntry || !storyWeekActive) return false;', advance)
        self.assertIn("ImportedModDiscovery.ownerForSong(Song.storageFolder(PlayState.SONG), 'assets/data') != owner", advance)
        self.assertIn('NightmareVisionStoryMeta.advanceWeek(storyMeta, songPreparationHost(storyMeta.difficulty), songScore, songMisses,', advance)
        self.assertIn("switchState(createStateFactory('PlayState'));", advance)
        self.assertIn("switchState(createStateFactory('StoryMenuState'));", advance)
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        story = play[play.index('function endForReal()'):]
        story = story[story.index('if (isStoryMode) {'):]
        self.assertLess(story.index('storySession.advanceStoryWeek(songScore, songMisses)) return;'),
                        story.index('campaignScore += songScore;'),
                        'the owner week is handled before the engine story playlist')


if __name__ == '__main__':
    unittest.main()
