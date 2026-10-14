"""Seek, note clearing, song volume and pause entry points scripts expect on PlayState."""
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


def run(files: dict, main: str = 'Main', source_path: bool = True) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
        for name, text in files.items():
            target = Path(folder, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding='utf-8', newline='\n')
        paths = (['-cp', str(ROOT / 'source')] if source_path else []) + ['-cp', folder]
        return subprocess.run([*HAXE_COMMAND, *paths, '--main', main, '--interp'], cwd=ROOT,
                              capture_output=True, text=True, timeout=60)


class SourcePlayStateTransportSurfaceTest(unittest.TestCase):
    def setUp(self):
        self.play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')

    def test_seek_moves_every_clock_both_ways_and_clearing_is_separate(self):
        methods = '\n'.join(method(self.play, marker) for marker in (
            'function moveSongClock(target:Float):Void',
            'function retireNotesBefore(cutoff:Float)',
            'public function seekSongTime(',
            'public function clearNotesBefore(',
            'public function finishSong(',
        ))
        result = run({'Main.hx': r'''
class Conductor { public static var songPosition:Float = 0; public static var lastSongPos:Float = 0;
 public static var instrumentalOffset:Float = 0;
 public static function audioTimeFromSong(time:Float):Float return time - instrumentalOffset; }
class Music { public var time:Float = 0; public var volume:Float = 1; public function new() {} }
class FlxG {
 public static var sound:{music:Music} = {music: new Music()};
 public static var game = {ticks: 4242};
}
class NoteStub {
 public var strumTime:Float;
 public var alive:Bool = true;
 public var destroyed:Bool = false;
 public var repaired:Int = 0;
 public function new(time:Float) strumTime = time;
 public function kill():Void alive = false;
 public function destroy():Void destroyed = true;
 public function repairSustainChainAfterSeek():Void repaired++;
}
class NoteGroup {
 public var members:Array<NoteStub> = [];
 public function new() {}
 public function remove(note:NoteStub, splice:Bool):Void members.remove(note);
}
class Host {
 public var startingSong:Bool = false;
 public var endingSong:Bool = false;
 public var songLength:Float = 10000;
 public var songTime:Float = 0;
 public var previousFrameTime:Int = 0;
 public var unspawnNotes:Array<NoteStub> = [];
 public var notes:NoteGroup = new NoteGroup();
 public var vocalPosition:Float = 0;
 public var vocalVolume:Float = 1;
 public var log:Array<String> = [];
 public function new() {}
 function pauseVocals():Void log.push('vocals.pause');
 function playVocals():Void log.push('vocals.play');
 function seekVocals(time:Float):Void vocalPosition = time;
 function setVocalsVolume(volume:Float):Void vocalVolume = volume;
 function endSong(?force:Bool = false):Void log.push('endSong');
 function nightmareVisionRemoveFieldNoteMembership(note:NoteStub):Void {}
 @@METHODS@@
}
class Main {
 static function check(ok:Bool, why:String):Void if (!ok) throw why;
 static function at(host:Host, time:Float):Bool
  return FlxG.sound.music.time == time && host.vocalPosition == time && Conductor.songPosition == time
   && Conductor.lastSongPos == time && host.songTime == time && host.previousFrameTime == 4242;
 static function fill(host:Host):Void {
  host.unspawnNotes = [for (time in [3100.0, 3349.0, 3350.0, 6000.0]) new NoteStub(time)];
  host.notes.members = [for (time in [2900.0, 3349.5, 3350.0]) new NoteStub(time)];
 }
 static function main():Void {
  var host = new Host();
  fill(host);
  check(host.seekSongTime(5000) && at(host, 5000), 'forward seek');
  check(host.seekSongTime(1200) && at(host, 1200), 'backward seek');
  check(host.unspawnNotes.length == 4 && host.notes.members.length == 3, 'a plain seek dropped notes');
  check(host.seekSongTime(-50) && at(host, 0), 'negative time is the song start');
  check(host.seekSongTime(99999) && at(host, 10000), 'time past the end is the end');
  check(!host.seekSongTime(Math.NaN) && at(host, 10000), 'not a number moved the song');
  host.startingSong = true;
  check(!host.seekSongTime(2000) && at(host, 10000), 'seek before the song started');
  host.startingSong = false;
  host.endingSong = true;
  check(!host.seekSongTime(2000) && at(host, 10000), 'seek while the song is ending');
  host.endingSong = false;

  // Notes less than 350 ms after the given time go, from both queues.
  var pending = host.unspawnNotes.copy();
  var active = host.notes.members.copy();
  host.clearNotesBefore(3000);
  check([for (note in host.unspawnNotes) note.strumTime].join(',') == '3350,6000', 'pending notes left: '
   + [for (note in host.unspawnNotes) note.strumTime].join(','));
  check([for (note in host.notes.members) note.strumTime].join(',') == '3350', 'active notes left');
  check(!pending[0].alive && pending[0].destroyed && !pending[1].alive && pending[2].alive, 'pending retirement');
  check(!active[0].alive && active[0].destroyed && !active[1].alive && active[2].alive, 'active retirement');
  check(pending[2].repaired == 1 && pending[3].repaired == 1 && active[2].repaired == 1, 'survivors were not repaired');
  host.clearNotesBefore(Math.NaN);
  check(host.unspawnNotes.length == 2, 'not a number cleared notes');

  fill(host);
  check(host.seekSongTime(3000, true) && at(host, 3000) && host.unspawnNotes.length == 2
   && host.notes.members.length == 1, 'seek with clearing');

  host.log = [];
  host.finishSong();
  check(FlxG.sound.music.volume == 0 && host.vocalVolume == 0
   && host.log.join(',') == 'vocals.pause,endSong', 'finishSong: ' + host.log.join(','));
 }
}
'''.replace('@@METHODS@@', methods)}, source_path=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_volume_multiplier_stacks_on_groups_and_survives_volume_writes(self):
        bus = (ROOT / 'source/SongVolumeBus.hx').read_text(encoding='utf-8')
        result = run({
            'SongVolumeBus.hx': bus,
            'flixel/sound/FlxSoundGroup.hx': '''package flixel.sound;
class FlxSoundGroup {
 public var sounds:Array<FlxSound> = [];
 public var volume(default, set):Float;
 public function new(volume:Float = 1) this.volume = volume;
 public function add(sound:FlxSound):Bool {
  if (sounds.contains(sound)) return false;
  if (sound.group != null) sound.group.sounds.remove(sound);
  sounds.push(sound);
  sound.group = this;
  return true;
 }
 public function remove(sound:FlxSound):Bool {
  if (!sounds.contains(sound)) return false;
  sound.group = null;
  return sounds.remove(sound);
 }
 public function getVolume():Float return volume;
 function set_volume(value:Float):Float return volume = value;
}''',
            'flixel/sound/FlxSound.hx': '''package flixel.sound;
class FlxSound {
 public var volume:Float = 1;
 public var group:FlxSoundGroup = null;
 public function new() {}
 public function heard():Float return (group == null ? 1.0 : group.getVolume()) * volume;
}''',
            'Main.hx': r'''import flixel.sound.FlxSound;
import flixel.sound.FlxSoundGroup;
class Main {
 static function near(value:Float, expected:Float, why:String):Void
  if (Math.abs(value - expected) > 0.0001) throw why + ': ' + value + ' != ' + expected;
 static function main():Void {
  var musicOption = new FlxSoundGroup(0.8);
  var soundOption = new FlxSoundGroup(0.5);
  var inst = new FlxSound();
  var player = new FlxSound();
  var opponent = new FlxSound();
  var loose = new FlxSound();
  musicOption.add(inst);
  soundOption.add(player);
  soundOption.add(opponent);

  var bus = new SongVolumeBus();
  for (sound in [inst, player, opponent, loose]) bus.attach(sound);
  near(inst.heard(), 0.8, 'attaching alone changed the instrumental');
  bus.setMultiplier(0.5);
  near(inst.heard(), 0.4, 'instrumental keeps the music option');
  near(player.heard(), 0.25, 'vocals keep the sound option');
  near(loose.heard(), 0.5, 'ungrouped sound');

  // A miss mutes one stem and a hit restores it: the multiplier stays put.
  player.volume = 0;
  near(player.heard(), 0, 'muted stem');
  near(opponent.heard(), 0.25, 'other stem was touched');
  player.volume = 1;
  near(player.heard(), 0.25, 'restored stem lost the multiplier');
  near(player.volume, 1, 'the multiplier overwrote the stem volume');

  // Attaching again (song start rebuilds its audio) must not stack twice.
  for (sound in [inst, player, opponent]) bus.attach(sound);
  near(inst.heard(), 0.4, 'second attach');
  bus.setMultiplier(0);
  near(inst.heard(), 0, 'silence');
  bus.setMultiplier(1);
  near(player.heard(), 0.5, 'back to normal');

  // The instrumental outlives a song: the next song's multiplier replaces the old one.
  bus.setMultiplier(0.25);
  var next = new SongVolumeBus();
  next.attach(inst);
  next.setMultiplier(0.5);
  near(inst.heard(), 0.4, 'old multiplier leaked into the next song');

  next.release();
  bus.release();
  if (inst.group != musicOption || player.group != soundOption || loose.group != null)
   throw 'release did not hand the sounds back';
  near(inst.heard(), 0.8, 'released instrumental');
 }
}'''}, source_path=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_donor_names_are_thin_aliases_over_the_base_functions(self):
        play = self.play
        self.assertIn('@:keep public function setSongTime(time:Float):Void seekSongTime(time);', play)
        self.assertIn('@:keep public function clearNotesBefore(time:Float):Void', play)
        self.assertIn('@:keep public function finishSong(?ignoreNoteOffset:Bool = false):Void', play)
        self.assertIn('@:keep public function openPauseMenu():Void', play)
        self.assertIn('@:keep public var volumeMult(get, set):Float;', play)
        self.assertIn('@:keep function set_volumeMult(value:Float):Float return songVolumeMultiplier = value;', play)
        self.assertIn('@:keep public var camZoomingDecay(get, set):Float;', play)
        self.assertIn('@:keep function set_camZoomingDecay(value:Float):Float return camZoomDecay = value;', play)
        self.assertIn('@:keep function get_camZoomingDecay():Float return camZoomDecay;', play)

        # The forward seek used by video skip is the same clock move and retirement.
        forward = method(play, 'function seekForwardSongTime(target:Float, captureSmokeState:Bool):Dynamic')
        self.assertIn('moveSongClock(target);', forward)
        self.assertIn('var retired = retireNotesBefore(target);', forward)
        self.assertNotIn('FlxG.sound.music.time = target;', forward)

        # Untouched songs never leave Flixel's own sound groups.
        apply = method(play, 'function applySongVolumeMultiplier():Void')
        self.assertLess(apply.index('if (songVolumeMultiplier == 1) return;'), apply.index('new SongVolumeBus()'))
        self.assertIn('songVolumeBus.attach(FlxG.sound.music);', apply)
        self.assertIn('for (sound in vocalTracks.tracks) songVolumeBus.attach(sound);', apply)
        start_song = method(play, 'function startSong():Void')
        self.assertLess(start_song.index('FlxG.sound.playMusic(inst, 1, false);'),
                        start_song.index('applySongVolumeMultiplier();'))

        # Leaving the song hands the instrumental back before anything is torn down.
        destroy = method(play, 'override public function destroy()')
        self.assertLess(destroy.index('songVolumeBus.release();'), destroy.index('destroyPsychCustomSubstates();'))
        self.assertLess(destroy.index('songVolumeBus.release();'), destroy.index('songVolumeBus = null;'))

        # The pause key still asks scripts first; a direct call does not.
        open_pause = method(play, 'public function openPauseMenu():Void')
        self.assertNotIn('onPause', open_pause)
        self.assertLess(open_pause.index("callCodenameEvent('onGamePause'"), open_pause.index('openSubState(new PauseSubState('))


if __name__ == '__main__':
    unittest.main()
