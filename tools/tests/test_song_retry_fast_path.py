"""Retrying the same song restarts at once and keeps what the attempt loaded."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

SOUND_STUB = '''package openfl.media;
class Sound {
 public var name:String;
 public function new(name:String) this.name = name;
}
'''


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


def run_fixture(fixture: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
        fixture = fixture.replace('@@TRACK@@', str(Path(folder, 'track.ogg')))
        Path(folder, 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
        Path(folder, 'openfl', 'media').mkdir(parents=True)
        Path(folder, 'openfl', 'media', 'Sound.hx').write_text(SOUND_STUB, encoding='utf-8', newline='\n')
        return subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                               '--main', 'Main', '--interp'], cwd=ROOT,
                              capture_output=True, text=True, timeout=60)


class SongRetryFastPathTest(unittest.TestCase):
    def test_retry_rules_and_carried_song_tracks(self):
        fixture = r'''import openfl.media.Sound;
class Main {
 static var decodes = 0;
 static function check(ok:Bool, why:String):Void if (!ok) throw why;
 static function decode(name:String):Void->Sound return function():Sound { decodes++; return new Sound(name); };
 static function main():Void {
  var chart = {song: 'Fixture'};
  // Nothing has been played yet: nothing to retry quickly.
  check(!SongRetry.request(chart, 1, 1.0), 'retry before any attempt');
  check(!SongRetry.keepsSongAssets(true, 0), 'no attempt keeps nothing');

  // First attempt decodes its tracks.
  check(!SongRetry.beginAttempt(), 'a first play is not a retry');
  var inst = SongRetry.songTrack('songs/fixture/Inst.ogg', 'plain', decode('inst'));
  var voices = SongRetry.songTrack('songs/fixture/Voices.ogg', 'plain', decode('voices'));
  check(decodes == 2, 'first attempt decodes');
  SongRetry.finishAttempt(chart, 1, 7);

  // Same chart object and difficulty: fast retry.
  check(SongRetry.request(chart, 1, 2.5) && SongRetry.lastFast && SongRetry.requestedAt == 2.5, 'same song retries fast');
  check(SongRetry.keepsSongAssets(true, 7), 'assets kept for the next attempt');
  check(SongRetry.beginAttempt() && SongRetry.active, 'the next start is a retry');
  check(SongRetry.hasCarriedTrack('songs/fixture/Inst.ogg', 'plain'), 'instrumental waits for the retry');
  check(!SongRetry.hasCarriedTrack('songs/fixture/Inst.ogg', 'normalized'), 'a different decode is not carried');
  check(SongRetry.songTrack('songs/fixture/Inst.ogg', 'plain', decode('again')) == inst, 'instrumental taken back');
  check(SongRetry.songTrack('songs/fixture/Voices.ogg', 'plain', decode('again')) == voices, 'vocals taken back');
  check(decodes == 2, 'a retry decodes nothing again');
  // Taken once: a second request in the same attempt decodes.
  var extra = SongRetry.songTrack('songs/fixture/Inst.ogg', 'normalized', decode('normalized'));
  check(decodes == 3 && extra != inst, 'other variants still decode');
  SongRetry.finishAttempt(chart, 1, 7);
  check(!SongRetry.active, 'retry over once created');

  // Another chart or difficulty takes the full loading path.
  check(!SongRetry.request({song: 'Fixture'}, 1, 3.0) && !SongRetry.lastFast && SongRetry.lastRefusal == 'chart',
   'another chart object');
  check(!SongRetry.request(chart, 2, 3.0) && SongRetry.lastRefusal == 'difficulty', 'another difficulty');
  check(!SongRetry.keepsSongAssets(true, 7), 'a slow retry keeps nothing');

  // A chart read again from its own file stands for the same attempt.
  SongRetry.beginAttempt();
  SongRetry.songTrack('songs/fixture/Inst.ogg', 'plain', decode('inst'));
  SongRetry.finishAttempt(chart, 1, 7);
  var reread = {song: 'Fixture'};
  SongRetry.chartReloaded(reread);
  check(SongRetry.request(reread, 1, 4.0), 'reloaded chart retries fast');
  // The asset epoch moved during the song: images are not kept, and a track
  // whose file cannot be checked is decoded again.
  check(!SongRetry.keepsSongAssets(true, 8), 'stale images are not kept');
  check(SongRetry.beginAttempt(), 'still a quick retry');
  check(!SongRetry.hasCarriedTrack('songs/fixture/Inst.ogg', 'plain'), 'unchecked track not offered');
  decodes = 0;
  SongRetry.songTrack('songs/fixture/Inst.ogg', 'plain', decode('fresh'));
  check(decodes == 1, 'stale track decoded again');
  SongRetry.finishAttempt(chart, 1, 8);

  // A real file keeps its decode across an epoch move until it changes.
  var file = '@@TRACK@@';
  sys.io.File.saveContent(file, 'one');
  SongRetry.beginAttempt();
  var real = SongRetry.songTrack(file, 'plain', decode('real'));
  SongRetry.finishAttempt(chart, 1, 8);
  check(SongRetry.request(chart, 1, 4.5) && !SongRetry.keepsSongAssets(true, 9) && SongRetry.beginAttempt(), 'epoch moved');
  check(SongRetry.hasCarriedTrack(file, 'plain') && SongRetry.songTrack(file, 'plain', decode('x')) == real, 'unchanged file reused');
  SongRetry.finishAttempt(chart, 1, 9);
  sys.io.File.saveContent(file, 'longer text');
  check(SongRetry.request(chart, 1, 4.6) && SongRetry.keepsSongAssets(true, 9) && SongRetry.beginAttempt(), 'same epoch');
  check(!SongRetry.hasCarriedTrack(file, 'plain') && SongRetry.songTrack(file, 'plain', decode('y')) != real,
   'changed file decoded again');
  SongRetry.finishAttempt(chart, 1, 9);

  // Leaving for a menu forgets the song's tracks even mid retry.
  check(SongRetry.request(chart, 1, 5.0), 'retry asked');
  check(!SongRetry.keepsSongAssets(false, 8), 'a menu keeps nothing');
  check(!SongRetry.beginAttempt() && !SongRetry.hasCarriedTrack('songs/fixture/Inst.ogg', 'plain'), 'tracks released');
  SongRetry.reset();
  check(!SongRetry.pending && SongRetry.requestedAt == -1, 'reset');

  // Script translations: reused only by a fast retry and only for the same text.
  var translated = 0;
  function translate(text:String):Void->String return function():String { translated++; return 'out:' + text; };
  SongRetry.beginAttempt();
  check(SongRetry.translation('lua|a', 'one', translate('one')) == 'out:one', 'first translation');
  check(SongRetry.translation('lua|b', 'two', translate('two')) == 'out:two', 'second translation');
  check(translated == 2, 'first attempt translates');
  SongRetry.finishAttempt(chart, 1, 7);
  check(SongRetry.request(chart, 1, 6.0) && SongRetry.keepsSongAssets(true, 7) && SongRetry.beginAttempt(), 'fast retry');
  check(SongRetry.translation('lua|a', 'one', translate('one')) == 'out:one' && translated == 2, 'unchanged script reused');
  check(SongRetry.translation('lua|b', 'edited', translate('edited')) == 'out:edited' && translated == 3,
   'edited script translated again');
  SongRetry.finishAttempt(chart, 1, 7);
  // A full load translates everything again.
  check(!SongRetry.keepsSongAssets(false, 7) && !SongRetry.beginAttempt(), 'menu in between');
  SongRetry.translation('lua|a', 'one', translate('one'));
  check(translated == 4, 'no reuse without a fast retry');
  SongRetry.finishAttempt(chart, 1, 7);
  // Within one attempt nothing is reused, so a first play behaves as before.
  SongRetry.translation('lua|a', 'one', translate('one'));
  check(translated == 5, 'no reuse inside an attempt');

  // A result the caller refuses to keep (it depends on other files) is
  // translated again on the retry even when its own text is unchanged.
  SongRetry.reset();
  var refuse = function(result:Dynamic):Bool return result != 'out:base';
  SongRetry.beginAttempt();
  SongRetry.translation('hxc|c', 'base', translate('base'), refuse);
  SongRetry.translation('hxc|d', 'plain', translate('plain'), refuse);
  SongRetry.finishAttempt(chart, 1, 7);
  translated = 0;
  check(SongRetry.request(chart, 1, 7.0) && SongRetry.keepsSongAssets(true, 7) && SongRetry.beginAttempt(), 'retry for keep');
  check(SongRetry.translation('hxc|c', 'base', translate('base'), refuse) == 'out:base' && translated == 1,
   'refused result translated again');
  check(SongRetry.translation('hxc|d', 'plain', translate('plain'), refuse) == 'out:plain' && translated == 1,
   'kept result reused');
  SongRetry.finishAttempt(chart, 1, 7);
 }
}'''
        result = run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        source = (ROOT / 'source/SongRetry.hx').read_text(encoding='utf-8')
        # mtime and size survive a copy, so the status time is part of the stamp.
        self.assertIn("return stat.size + ':' + stat.mtime.getTime() + ':' + stat.ctime.getTime();", source)

    def test_same_chart_loads_are_retries(self):
        fixture = r'''class Main {
 static var names = ['easy', 'normal', 'hard'];
 static function same(name:Null<String>, difficulty:Dynamic):Bool
  return SongFlow.sameChart(SongFlow.loadTarget(name, difficulty, 'Fixture Song', 2, names, 1), 'Fixture Song', 2, names, 1);
 static function main():Void {
  if (!same(null, -1)) throw 'reload of the current chart';
  if (!same('fixture song', 'HARD')) throw 'same song spelled in another case';
  if (same(null, 1)) throw 'another difficulty';
  if (same('Other', 2)) throw 'another song';
  if (same(null, 'fixture song-remix')) throw 'another chart file';
  if (SongFlow.sameChart(null, 'Fixture Song', 2, names, 1)) throw 'nothing to load';
  if (SongFlow.sameChart(SongFlow.loadTarget(null, -1, 'Song', 1, names, 1), null, 1, names, 1)) throw 'no song playing';
 }
}'''
        result = run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_every_retry_route_shares_the_fast_restart(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        fixture = r'''class Main {
 static function check(ok:Bool, why:String):Void if (!ok) throw why + ': ' + Log.events.join(',');
 static function main():Void {
  var state = new PlayState();
  PlayState.instance = state;
  FlxG.state = state;
  PlayState.SONG = {song: 'Fixture Song'};
  PlayState.storyDifficulty = 1;
  SongRetry.beginAttempt();
  SongRetry.finishAttempt(PlayState.SONG, 1, 0);

  // Game over and the pause menu: callbacks, cleanup, then straight in.
  PlayState.restartCurrentSong();
  check(Log.events.join(',') == 'songRetry,flash,flash,flash,now', 'fast retry');
  check(!state.paused && SongRetry.requestedAt >= 0, 'retry state');
  SongRetry.keepsSongAssets(false, 0);

  // A songRetry callback that resets the song again neither loops nor
  // dispatches songRetry a second time.
  Log.events = [];
  Log.nested = true;
  PlayState.resetCurrentState();
  Log.nested = false;
  check(Log.events.join(',') == 'songRetry,flash,flash,flash,now', 'nested reset');
  SongRetry.keepsSongAssets(false, 0);

  // A callback that throws does not block the next retry.
  Log.events = [];
  Log.fail = true;
  var threw = false;
  try PlayState.restartCurrentSong() catch (_:Dynamic) threw = true;
  Log.fail = false;
  check(threw, 'failure surfaced');
  Log.events = [];
  PlayState.restartCurrentSong();
  check(Log.events.join(',') == 'songRetry,flash,flash,flash,now', 'retry after a failed callback');
  SongRetry.keepsSongAssets(false, 0);

  // A script resetting the state while a song plays retries it.
  Log.events = [];
  PlayState.resetCurrentState();
  check(Log.events.join(',') == 'songRetry,flash,flash,flash,now', 'script reset retries');
  SongRetry.keepsSongAssets(false, 0);

  // Loading the same chart reads it again but still restarts fast.
  Log.events = [];
  check(PlayState.loadSongByName(null, -1), 'same chart load');
  check(Log.events.join(',') == 'read:fixture song,songRetry,flash,flash,flash,now', 'same chart reload');
  SongRetry.keepsSongAssets(false, 0);

  // Another difficulty takes the loading screen, without retry callbacks.
  Log.events = [];
  check(PlayState.loadSongByName(null, 2), 'other difficulty');
  check(Log.events.join(',') == 'read:fixture song-hard,loading', 'difficulty change loads');

  // Background import work does not cost the quick switch; Main drops the
  // cached decodes on its own when the asset epoch moved.
  PlayState.storyDifficulty = 1;
  SongRetry.beginAttempt();
  SongRetry.finishAttempt(PlayState.SONG, 1, 0);
  Log.events = [];
  state.restartSong();
  check(Log.events.join(',') == 'songRetry,flash,flash,flash,now' && !SongRetry.keepsSongAssets(true, 1),
   'refresh switches quickly with cold caches');

  // Outside a song a reset is an ordinary reset.
  FlxG.state = null;
  Log.events = [];
  PlayState.resetCurrentState();
  check(Log.events.join(',') == 'reset', 'menu reset');
 }
}
class Log {
 public static var events:Array<String> = [];
 public static var nested = false;
 public static var fail = false;
}
class Camera { public function new() {} public function stopFlash():Void Log.events.push('flash'); }
class EngineCompat { public static function hxcSongRetryPayload(id:String):Dynamic return {}; }

class LoadingState {
 public static function switchStateNow(state:Dynamic):Void Log.events.push('now');
 public static function loadAndSwitchState(state:Dynamic):Void Log.events.push('loading');
}
class FlxG {
 public static var state:Dynamic;
 public static function resetState():Void Log.events.push('reset');
}
class DifficultyManager {
 public static function getDifficultyNames():Array<String> return ['easy', 'normal', 'hard'];
 public static function getDefaultDiff():Int return 1;
}
class Song {
 public static function loadFromJson(chart:String, folder:String):Dynamic {
  Log.events.push('read:' + chart);
  return {song: 'Fixture Song'};
 }
}
class PlayState {
 public static var instance:PlayState;
 public static var SONG:Dynamic;
 public static var storyDifficulty:Int = 1;
 public var paused:Bool = true;
 public var compatCustomSubstateOpen:Bool = true;
 var songRetryDispatching:Bool = false;
 var camGame = new Camera();
 var camHUD = new Camera();
 var camOther = new Camera();
 public function new() {}
 function callAllHScript(name:String, args:Array<Dynamic>, ?a:Dynamic, ?b:Dynamic, ?c:Dynamic):Void {
  Log.events.push(name);
  if (Log.fail) throw 'callback failed';
  if (Log.nested) PlayState.resetCurrentState();
 }
 function hxcDifficultyId():String return 'normal';
 function hxcClearAllNoteTextCues():Void {}
 function clearHxcVignette():Void {}
 function hxcClearRuntimeShaderBindings():Void {}
 static function skipNextSongTransition(skip:Bool):Void if (skip) Log.events.push('skip');
 @@METHODS@@
}
'''.replace('@@METHODS@@', '\n'.join(method(play, marker) for marker in (
            '@:keep public function restartSong(', '@:keep public static function resetCurrentState(',
            '@:keep public static function restartCurrentSong(', '@:keep public static function loadSongByName(')))
        result = run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_state_swap_create_and_audio_use_the_retry(self):
        main = (ROOT / 'source/Main.hx').read_text(encoding='utf-8')
        create = main[main.index('FlxG.signals.preStateCreate.add('):]
        create = create[:create.index('});')]
        keep = create.index('SongRetry.keepsSongAssets(Std.isOfType(_state, PlayState), FNFAssets.pathEpoch());')
        # A kept retry skips only the release of held images and atlases; the
        # sweep of images nothing holds still runs, so retries cannot pile up.
        skip = create.index('if (!retryKeepsAssets) {\n\t\t\t\t\tSongGraphicRetention.end();\n'
            '\t\t\t\t\tDynamicSprite.DynamicAtlasFrames.releaseAll();\n\t\t\t\t}')
        self.assertLess(keep, skip)
        self.assertLess(skip, create.index('else FlxG.bitmap.clearCache();'))
        self.assertIn('if (!retryKeepsAssets)\n\t\t\t\t\tSongGraphicRetention.begin(FNFAssets.pathEpoch());', create)

        loading = (ROOT / 'source/LoadingState.hx').read_text(encoding='utf-8')
        now = method(loading, 'public static function switchStateNow(')
        self.assertNotIn('SongLoadingScreen.queue', now)
        self.assertIn('CodenameRequestedStateCompat.switchToKnownTarget(target,', now)
        self.assertIn('if (SongLoadingScreen.active || SongLoadingScreen.preparing) {', now)

        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        create_method = method(play, 'override public function create()')
        self.assertLess(create_method.index('SongRetry.beginAttempt();'), create_method.index('instance = this;'))
        self.assertLess(create_method.index('SongRetry.finishAttempt(SONG, storyDifficulty,'),
            create_method.index('RuntimeSmokeHarness.markPlayStateReady(SONG);'))
        self.assertIn('inst = SongRetry.songTrack(useInst, songTrackVariant(), function():Sound', play)
        compatible = method(play, 'function getCompatibleHscript(')
        for translator in ("SongRetry.translation('psych-hx|' + normalized, text,",
                           "SongRetry.translation('lua|' + psychOwned + '|' + normalized, text,",
                           "SongRetry.translation('hxc|' + normalized, text,\n\t\t\t\tfunction() return HxcCompat.translate(text, normalized),\n"
                           "\t\t\t\tfunction(result:Dynamic):Bool return result == null || result.kind != 'character');",
                           "SongRetry.translation('lua|' + luaPsychOwned + '|' + luaPath, luaText,"):
            self.assertIn(translator, compatible)
        self.assertIn('return new FlxSound().loadEmbedded(SongRetry.songTrack(path, songTrackVariant(), function():Sound',
            method(play, 'private function loadVocalTrack('))
        # The loop modifier and script resets retry like everything else.
        self.assertNotIn('FlxG.resetState();', method(play, 'function runPsychGameOverTransition()'))
        self.assertIn('PlayState.resetCurrentState();', method((ROOT / 'source/HxcStateFactory.hx').read_text(
            encoding='utf-8'), 'public static function resetState()'))
        self.assertIn('public function resetState():Void PlayState.resetCurrentState();',
            (ROOT / 'source/CodenameFlxGFacade.hx').read_text(encoding='utf-8'))
        session = method((ROOT / 'source/NightmareVisionStateSession.hx').read_text(encoding='utf-8'),
            'public function resetState()')
        self.assertLess(session.index('PlayState.resetCurrentState();'), session.index('factory.lastConstructor'))


if __name__ == '__main__':
    unittest.main()
