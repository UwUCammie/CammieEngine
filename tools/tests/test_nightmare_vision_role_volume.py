"""Keep Nightmare Vision role-volume writes isolated from legacy volume sync."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''package;
import flixel.sound.FlxSound;

class NightmareVisionRoleVolumeMain {
 static function check(ok:Bool,message:String):Void if (!ok) throw message;
 static function near(a:Float,b:Float):Bool return Math.abs(a-b)<0.0001;
 static function main():Void {
  var player=new FlxSound(1000); player.volume=0.8;
  var opponent=new FlxSound(1000); opponent.volume=0.65;
  var split=new VocalTracks(player); split.add(opponent,'opponent');
  var audio=new NightmareVisionPlayableSongView(function() return null,
   function() return 0,function() return split);

  audio.setTrackVolumeState(true);
  check(player.volume==0 && near(opponent.volume,0.65),
   'miss mutes only the player stem');
  split.syncPrimaryVolume();
  check(near(opponent.volume,0.65),
   'primary-volume sync does not overwrite opponent after player mute');

  audio.setTrackVolumeState(false);
  check(player.volume==1 && near(opponent.volume,0.65),
   'hit restores only player stem');
  split.syncPrimaryVolume();
  check(near(opponent.volume,0.65),
   'primary-volume sync does not overwrite opponent after player restore');

  audio.opponentVocals.volume=0.25;
  check(near(opponent.volume,0.25) && player.volume==1,
   'opponent group volume targets opponent role only');
  split.syncPrimaryVolume();
  check(near(opponent.volume,0.25),
   'opponent role write survives legacy primary-volume sync');

  audio.playerVocals.volume=0.4;
  check(near(player.volume,0.4) && near(opponent.volume,0.25),
   'player group volume targets player role only');
  split.syncPrimaryVolume();
  check(near(opponent.volume,0.25),
   'player group role write survives legacy primary-volume sync');

  var shared=new FlxSound(1000); shared.volume=0.55;
  var sharedTracks=new VocalTracks(shared); sharedTracks.setRole(shared,'shared');
  var legacy=new NightmareVisionPlayableSongView(function() return null,
   function() return 0,function() return sharedTracks);
  legacy.playerVocals.volume=0.3;
  check(near(shared.volume,0.3),
   'player group falls back to a lone shared legacy track');
  legacy.setTrackVolumeState(true);
  check(shared.volume==0,'player miss state falls back to a lone shared legacy track');
  legacy.setTrackVolumeState(false);
  check(shared.volume==1,'player hit state restores a lone shared legacy track');
  legacy.opponentVocals.volume=0.9;
  check(shared.volume==1 && legacy.opponentVocals.members.length==0,
   'empty opponent group does not claim the shared player fallback');

  audio.release(); legacy.release();
 }
}'''

FLX_SOUND = r'''package flixel.sound;
class FlxSound {
 public var volume:Float=1;
 public var time:Float=0;
 public var length:Float;
 public var playing:Bool=false;
 public var pitch:Float=1;
 public function new(length:Float=0) this.length=length;
 public function play(forceRestart:Bool=false,startTime:Float=0,?endTime:Null<Float>):Void {
  time=startTime; playing=true;
 }
 public function pause():Void playing=false;
 public function resume():Void playing=true;
 public function stop():Void { playing=false; time=0; }
 public function getActualVolume():Float return volume;
 public function destroy():Void {}
}'''

AUDIO_SOUND_VIEW = r'''package;
import flixel.sound.FlxSound;
class NightmareVisionAudioSoundView {
 var soundProvider:Void->FlxSound;
 var lengthProvider:Void->Float;
 public var volume(get,set):Float;
 public var time(get,set):Float;
 public var length(get,never):Float;
 public var playing(get,never):Bool;
 public function new(soundProvider:Void->FlxSound,lengthProvider:Void->Float) {
  this.soundProvider=soundProvider; this.lengthProvider=lengthProvider;
 }
 function get_volume():Float return soundProvider()==null ? 1 : soundProvider().volume;
 function set_volume(value:Float):Float { if(soundProvider()!=null) soundProvider().volume=value; return value; }
 function get_time():Float return soundProvider()==null ? 0 : soundProvider().time;
 function set_time(value:Float):Float { if(soundProvider()!=null) soundProvider().time=value; return value; }
 function get_length():Float return lengthProvider();
 function get_playing():Bool return soundProvider()!=null && soundProvider().playing;
 public function attachCurrentSound(sound:FlxSound):Void {}
 public function pause():Void if(soundProvider()!=null) soundProvider().pause();
 public function resume():Void if(soundProvider()!=null) soundProvider().resume();
 public function play(forceRestart:Bool=false,startTime:Float=0,?endTime:Null<Float>):Void
  if(soundProvider()!=null) soundProvider().play(forceRestart,startTime,endTime);
 public function stop():Void if(soundProvider()!=null) soundProvider().stop();
 public function release():Void { soundProvider=null; lengthProvider=null; }
}'''


class NightmareVisionRoleVolumeTest(unittest.TestCase):
    def test_role_volume_writes_survive_primary_sync_and_respect_shared_fallback(self):
        with tempfile.TemporaryDirectory(prefix="nmv-role-volume-", dir=ROOT / "tmp") as scratch:
            work = Path(scratch)
            (work / "NightmareVisionRoleVolumeMain.hx").write_text(MAIN, encoding="utf-8", newline="\n")
            sound_stub = work / "flixel/sound/FlxSound.hx"
            sound_stub.parent.mkdir(parents=True, exist_ok=True)
            sound_stub.write_text(FLX_SOUND, encoding="utf-8", newline="\n")
            (work / "NightmareVisionAudioSoundView.hx").write_text(
                AUDIO_SOUND_VIEW, encoding="utf-8", newline="\n"
            )
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "-cp", str(ROOT / "source"), "--main", "NightmareVisionRoleVolumeMain", "--interp"],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
