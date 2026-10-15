"""V-Slice PlayState instance API: the currentChart view and the native members behind it."""
import re
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''class Main {
 static function check(condition:Bool, message:String):Void if (!condition) throw message;
 static function main() {
  var chart:Dynamic = {song: 'Song A', songArtist: 'Artist', album: 'vol1', stage: 'stage', uiType: 'pixel',
   speed: 2.25, bpm: 150, player1: 'bf', player2: 'dad', gf: 'gf',
   events: haxe.Json.parse('[[1000, [["FocusCamera", "{\\"char\\":1,\\"duration\\":4}", "", ""], ["PlainEvent", "text", "", ""]]],'
    + '[2500.5, [["ZoomCamera", "{\\"zoom\\":1.1}", "", ""]]]]')};
  var built = 0;
  var view = new VSliceChartView(chart, 'song-a--owner', 'hard', '', function() { built++; return [1, 2, 3]; });
  check(view.songName == 'Song A' && view.songArtist == 'Artist' && view.album == 'vol1', 'header fields');
  check(view.stage == 'stage' && view.scrollSpeed == 2.25 && view.difficulty == 'hard' && view.variation == 'default', 'play fields');
  check(view.characters.player == 'bf' && view.characters.opponent == 'dad' && view.characters.girlfriend == 'gf'
   && view.characters.instrumental == '', 'characters');
  check(view.song.id == 'song-a--owner', 'song id is the installed folder');
  check(view.getStartingBPM() == 150 && view.timeChanges[0].bpm == 150, 'time changes');
  check(Reflect.field(view, 'noteStyle') == null, 'no noteStyle: the engine ui type is a different id set');
  check(built == 0, 'notes are built only when read');
  check(view.notes.length == 3 && view.notes.length == 3 && built == 1, 'notes are built once');
  var events = view.events;
  check(events.length == 3, 'event count ' + events.length);
  check(events[0].eventKind == 'FocusCamera' && events[0].value.char == 1 && events[0].time == 1000, 'decoded V-Slice value');
  check(events[1].eventKind == 'PlainEvent' && events[1].value == 'text', 'plain text values stay text');
  check(events[2].e == 'ZoomCamera' && events[2].t == 2500.5 && events[2].v.zoom == 1.1, 'short field names');
  check(view.getEvents() != view.events && view.getEvents().length == 3, 'getEvents returns a copy');
  check(view.describes(chart, 'hard', 'default') && view.describes(chart, 'hard', ''), 'same chart is reused');
  check(!view.describes(chart, 'easy', 'default') && !view.describes({}, 'hard', 'default'), 'another chart is rebuilt');
  var named = new VSliceChartView(chart, 'song-a--owner', 'hard', '', null, 'Song A (Remix)');
  check(named.songName == 'Song A (Remix)', 'the recorded display name wins over the folder id');
  var empty = new VSliceChartView(null, null, null, null);
  check(empty.events.length == 0 && empty.notes.length == 0 && empty.scrollSpeed == 1, 'missing chart reads safely');
 }
}
'''


class VSlicePlayStateInstanceApiTest(unittest.TestCase):
    def test_current_chart_view(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'Main.hx').write_text(MAIN, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_native_playstate_members(self):
        """The members live on PlayState itself (native build only), so pin their wiring."""
        source = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        for member in ['currentChart(get, never):VSliceChartView', 'currentDifficulty(get, never):String',
                       'currentVariation(get, set):String', 'currentInstrumental:String',
                       'isChartingMode(get, never):Bool', 'isPracticeMode(get, never):Bool',
                       'isBotPlayMode(get, never):Bool', 'camPause(get, never):FlxCamera',
                       'justUnpaused(get, never):Bool']:
            self.assertIn('public var ' + member, source)
        self.assertIn('public function resetCamera(resetZoom:Bool = true, cancelTweens:Bool = true, snap:Bool = true)', source)
        self.assertIn('public function togglePauseButton(visible:Bool = false)', source)
        # The chart view is cached and only rebuilt when the chart, difficulty or variation changes.
        self.assertRegex(source, r'vsliceChartView == null \|\| !vsliceChartView\.describes\(SONG, difficulty, variation\)')
        # Resuming from the pause menu marks justUnpaused, cleared after the next frame.
        resume = source[source.index('override function closeSubState()'):]
        self.assertLess(resume.index('markJustUnpaused();'), resume.index('resumeGameplayFromSubstate('))
        # The pause menu closes inside a frame's update; a clear queued straight on
        # postUpdate would run in that same frame, before the next update could
        # read the flag. The clear must wait for the next frame to begin.
        mark = source[source.index('function markJustUnpaused():Void {'):]
        mark = mark[:mark.index('\n\t}')]
        self.assertIn('FlxG.signals.preUpdate.addOnce(function() FlxG.signals.postUpdate.addOnce('
                      'function() justUnpausedFlag = false))', mark)
        self.assertNotRegex(mark, r'\n\t\tFlxG\.signals\.postUpdate\.addOnce')
        # The variation is the installed folder's, from the same catalog the registries use.
        self.assertIn('VSliceRegistryCatalog.folderVariation(Song.storageFolder(SONG))', source)
        self.assertIn('VSliceRegistryCatalog.folderDisplay(Song.storageFolder(SONG))', source)

    def test_story_launch_replaces_the_previous_week(self):
        """A V-Slice story launch must not leave an older week's retry playlist or score key behind."""
        binding = (ROOT / 'source/VSliceGameBinding.hx').read_text(encoding='utf-8')
        story = binding[binding.index('if (storyMode) {', binding.index('PlayState.SONG = song;')):]
        story = story[:story.index('} else {')]
        self.assertIn('StoryMenuState.storySongPlaylist = plan.storyFolders.copy();', story)
        self.assertIn("PlayState.storyWeek = week == null ? '' : week;", story)
        self.assertNotIn('if (week != null', story)
        catalog = (ROOT / 'source/VSliceRegistryCatalog.hx').read_text(encoding='utf-8')
        rebuild = catalog[catalog.index('indexedListing = listing;'):]
        self.assertIn('chartInfoCache = new Map();', rebuild[:rebuild.index('for (entry in entries)')])

    def test_video_cutscene_facade_steers_the_script_cutscene(self):
        playstate = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        start = playstate.index('@:keep public function hxcPlayImportedVideo')
        body = playstate[start:playstate.index('#else', start)]
        self.assertIn('hxcActiveVideo = video;', body)
        self.assertIn('VSliceVideoCutscene.onVideoStarted.dispatch();', body)
        self.assertIn('VSliceVideoCutscene.onVideoEnded.dispatch();', body)
        facade = (ROOT / 'source/VSliceVideoCutscene.hx').read_text(encoding='utf-8')
        for call, action in [('pauseVideo', 'video.suspend()'), ('resumeVideo', 'video.resume()'),
                             ('restartVideo', 'video.restart()'), ('finishVideo', 'video.finish()'),
                             ('showVideo', 'video.setShown(true)'), ('hideVideo', 'video.setShown(false)')]:
            method = facade[facade.index('public static function ' + call):]
            method = method[:method.index('\n\t}')]
            self.assertIn(action, method, call)
        video = (ROOT / 'source/VideoCutscene.hx').read_text(encoding='utf-8')
        finish = video[video.index('public function finish()'):]
        self.assertIn('finished = true;', finish[:finish.index('\n\t}')])
        shown = video[video.index('public function setShown('):]
        shown = shown[:shown.index('\n\t}')]
        self.assertRegex(shown, r'if \(suspended\) \{\s*suspendedVideoVisible = shown;')


if __name__ == '__main__':
    unittest.main()
