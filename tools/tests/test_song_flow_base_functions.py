"""Restart, exit and load-song requests share one base-game implementation."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]


def method(source: str, marker: str) -> str:
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
    raise AssertionError('Unclosed source method: ' + marker)


class SongFlowBaseFunctionsTest(unittest.TestCase):
    def test_load_requests_resolve_song_and_difficulty(self):
        fixture = r'''class Main {
 static var names = ['easy', 'normal', 'hard', 'Erect'];
 static function load(name:Null<String>, difficulty:Dynamic, ?current:Int = 2):Dynamic
  return SongFlow.loadTarget(name, difficulty, 'Fixture Song', current, names, 1);
 static function same(target:Dynamic, song:String, chart:String, difficulty:Int, why:String):Void {
  if (target == null || target.song != song || target.chart != chart || target.difficulty != difficulty)
   throw why + ': ' + Std.string(target);
 }
 static function main():Void {
  // Psych's defaults: no name is the current song, -1 keeps the difficulty.
  same(load(null, -1), 'Fixture Song', 'fixture song-hard', 2, 'reload');
  same(load(null, null), 'Fixture Song', 'fixture song-hard', 2, 'reload without difficulty');
  same(load('  ', ''), 'Fixture Song', 'fixture song-hard', 2, 'blank arguments');
  same(load('Other', 2), 'Other', 'other-hard', 2, 'index');
  same(load('Other', 2.0), 'Other', 'other-hard', 2, 'script number');
  same(load('Other', 'hard'), 'Other', 'other-hard', 2, 'name');
  same(load('Other', 'HARD'), 'Other', 'other-hard', 2, 'name case');
  same(load('Other', '3'), 'Other', 'other-erect', 3, 'numeric text');
  // The default difficulty is the plain chart file.
  same(load('Other', 1), 'Other', 'other', 1, 'default index');
  same(load('Other', 'normal'), 'Other', 'other', 1, 'default name');
  same(load('Other', 0, 1), 'Other', 'other-easy', 0, 'non default from default');
  // Out of range keeps what is being played instead of failing.
  same(load('Other', 9), 'Other', 'other-hard', 2, 'index too high');
  same(load('Other', Math.NaN), 'Other', 'other-hard', 2, 'not a number');
  same(load('Other', -1, 9), 'Other', 'other', 1, 'broken current difficulty');
  // Older scripts passed a chart file name.
  same(load('Other', 'Other-Remix'), 'Other', 'other-remix', 2, 'chart file name');
  if (SongFlow.loadTarget(null, 1, null, 1, names, 1) != null) throw 'nothing to load must stay nothing';
  if (SongFlow.loadTarget(null, 1, 'Song', 1, null, 0).chart != 'song') throw 'missing difficulty list';

  if (SongFlow.exitMenu(true) != SongFlow.MENU_STORY || SongFlow.exitMenu(false) != SongFlow.MENU_FREEPLAY)
   throw 'exit target';
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            Path(folder, 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                                     '--main', 'Main', '--interp'], cwd=ROOT,
                                    capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_exit_picks_the_menu_and_only_plays_music_when_asked(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        fixture = r'''class Main {
 static function check(ok:Bool, why:String):Void if (!ok) throw why + ': ' + Log.events.join(',');
 static function main():Void {
  PlayState.isStoryMode = true;
  PlayState.exitToMenu();
  check(Log.events.join(',') == 'story', 'story mode exit');
  Log.events = [];
  PlayState.isStoryMode = false;
  PlayState.exitToMenu(true, true);
  check(Log.events.join(',') == 'skip,freeplay,music:freakyMenu', 'freeplay exit with music');
  Log.events = [];
  PlayState.owner = 'assets/imported_mods/A';
  PlayState.instance = new PlayState();
  PlayState.balls = 3;
  PlayState.watchedCutscene = true;
  PlayState.exitToMenu();
  check(Log.events.join(',') == 'freeplay,charting.clear:assets/imported_mods/A'
   && PlayState.balls == 0 && !PlayState.watchedCutscene && !PlayState.instance.canResync
   && FlxG.camera.followLerp == 0, 'charting owner exit');
 }
}
class Log { public static var events:Array<String> = []; }
class PlayState {
 public static var instance:PlayState;
 public static var owner:String = '';
 public static var isStoryMode:Bool = false;
 public static var balls:Int = 0;
 public static var watchedCutscene:Bool = false;
 public var canResync:Bool = true;
 public function new() {}
 static function psychChartingOwnerRoot():String return owner;
 static function skipNextSongTransition(skip:Bool):Void if (skip) Log.events.push('skip');
 @@EXIT@@
}
class LoadingState { public static function loadAndSwitchState(state:Dynamic):Void Log.events.push('story'); }
class StoryMenuState { public function new() {} }
class ImportedMenuEntry { public static function returnToFreeplay():Void Log.events.push('freeplay'); }
class PsychOwnerChartingMode { public static function clear(owner:String):Void Log.events.push('charting.clear:' + owner); }
class Paths { public static function music(key:String):String return key; }
class FlxG {
 public static var camera:Dynamic = {followLerp: 1.0};
 public static var sound:Dynamic = {playMusic: function(path:String):Void Log.events.push('music:' + path)};
}
'''.replace('@@EXIT@@', method(play, 'public static function exitToMenu('))
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            Path(folder, 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                                     '--main', 'Main', '--interp'], cwd=ROOT,
                                    capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_every_retry_exit_and_load_path_uses_the_base_functions(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        pause = (ROOT / 'source/PauseSubState.hx').read_text(encoding='utf-8')
        game_over = (ROOT / 'source/GameOverSubstate.hx').read_text(encoding='utf-8')

        restart = method(play, 'public function restartSong(')
        self.assertIn("callAllHScript('songRetry', []);", restart)
        self.assertLess(restart.index("callAllHScript('songRetry', []);"), restart.index('new PlayState()'))
        self.assertIn('skipNextSongTransition(skipTransition);', restart)
        self.assertEqual(play.count("callAllHScript('songRetry'"), 1)
        self.assertIn('instance.restartSong(skipTransition);', method(play, 'public static function restartCurrentSong('))

        # The script-facing names are thin calls into the same functions.
        self.assertIn('function compatRestartSong(?skipTransition:Bool = false):Void restartSong(skipTransition);', play)
        self.assertIn('exitToMenu(skipTransition, true);', method(play, 'function compatExitSong('))
        self.assertIn('function compatLoadSong(?songName:String, ?difficulty:Dynamic):Void loadSongByName(songName, difficulty);', play)
        load = method(play, 'public static function loadSongByName(')
        self.assertIn('SongFlow.loadTarget(name, difficulty,', load)
        self.assertLess(load.index('Song.loadFromJson('), load.index('storyDifficulty = target.difficulty;'))
        self.assertLess(load.index('return false;'), load.index('new PlayState()'))

        for name, source in (('pause menu', pause), ('game over', game_over)):
            self.assertNotIn('FlxG.resetState()', source, name)
            self.assertNotIn('new PlayState()', source, name)
            self.assertNotIn('new StoryMenuState()', source, name)
            self.assertNotIn('ImportedMenuEntry.returnToFreeplay()', source, name)
            self.assertNotIn('Song.loadFromJson(', source, name)
        self.assertEqual(pause.count('PlayState.restartCurrentSong();'), 2)
        self.assertIn('PlayState.exitToMenu();', method(pause, 'function exitPauseToMenu()'))
        self.assertIn('PlayState.loadSongByName(null, diffs[curSelected - 1]);', pause)
        self.assertIn('PlayState.restartCurrentSong();', method(game_over, 'function endBullshit():Void'))
        self.assertEqual(game_over.count('PlayState.exitToMenu('), 2)

    def test_script_end_song_drops_remaining_notes_first(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        start = play.index('if (Std.isOfType(interp, LuaCompatInterp))\n\t\t\tinterp.variables.set("endSong"')
        binding = play[start:play.index('trace("set vars");', start)]
        self.assertLess(binding.index('retireNotesBefore(Math.POSITIVE_INFINITY);'), binding.index('this.endSong();'))


if __name__ == '__main__':
    unittest.main()
