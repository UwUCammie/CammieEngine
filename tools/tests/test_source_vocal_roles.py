"""Role-scoped vocal volume updates preserve split vocal buses."""

from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath


ROOT = Path(__file__).resolve().parents[2]


class SourceVocalRolesTest(unittest.TestCase):
    def test_actual_vocal_tracks_keep_roles_isolated_and_legacy_fanout(self):
        tracks_source = (ROOT / "source/VocalTracks.hx").read_text(encoding="utf-8")
        sound_stub = r'''package flixel.sound;
class FlxSound {
 public var id:Int;
 public var playing:Bool=false;
 public var time:Float=0;
 public var volume:Float=1;
 public var pitch:Float=1;
 public function new(id:Int) this.id=id;
 public function play():FlxSound {playing=true;return this;}
 public function pause():FlxSound {playing=false;return this;}
 public function stop():FlxSound {playing=false;return this;}
 public function getActualVolume():Float return volume;
 public function destroy():Void {}
}
'''
        main = r'''import flixel.sound.FlxSound;
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function near(actual:Float,expected:Float,message:String):Void
  if(Math.abs(actual-expected)>0.00001) throw message;
 static function main():Void {
  var opponentPrimary=new FlxSound(1);
  var playerStem=new FlxSound(2);
  var opponentStem=new FlxSound(3);
  opponentPrimary.volume=0.2;
  playerStem.volume=0.3;
  opponentStem.volume=0.4;
  var tracks=new VocalTracks(opponentPrimary,[playerStem,opponentStem]);
  tracks.setRole(opponentPrimary,'opponent');
  tracks.setRole(playerStem,'player');
  tracks.setRole(opponentStem,'opponent');
  check(tracks.hasRole('OPPONENT') && tracks.hasRole('Player') && !tracks.hasRole('missing'),
   'role lookup is case-insensitive and reports only present buses');

  check(tracks.setRoleVolume('OPPONENT',0.55), 'opponent role setter should find both opponent stems');
  near(opponentPrimary.volume,0.55,'primary opponent stem was updated');
  near(opponentStem.volume,0.55,'secondary opponent stem was updated');
  near(playerStem.volume,0.3,'opponent update did not touch player stem');
  tracks.syncPrimaryVolume();
  near(playerStem.volume,0.3,'scoped primary write did not fan out on sync');
  near(opponentStem.volume,0.55,'scoped role write kept matching group volumes');

  check(tracks.setRoleVolume('player',0.8), 'player role setter should find player stem');
  near(playerStem.volume,0.8,'player stem received its scoped volume');
  near(opponentPrimary.volume,0.55,'player update did not touch opponent primary');
  tracks.syncPrimaryVolume();
  near(playerStem.volume,0.8,'player scoped write survived primary sync');

  check(!tracks.hasRole('unknown') && !tracks.setRoleVolume('unknown',0.1),
   'unknown role has no implicit volume target');
  near(opponentPrimary.volume,0.55,'unknown role did not mutate primary');
  near(playerStem.volume,0.8,'unknown role did not mutate player');

  var sharedA=new FlxSound(4);
  var sharedB=new FlxSound(5);
  var shared=new VocalTracks(sharedA,[sharedB]);
  shared.setRole(sharedA,'shared');
  shared.setRole(sharedB,'shared');
  check(!shared.setRoleVolume('player',0.6),
   'role setter does not use a shared bus unless fallback is requested');
  near(sharedA.volume,1,'missing role without fallback leaves shared primary unchanged');
  check(shared.setRoleVolume('player',0.65,true),
   'explicit fallback uses shared stems when the requested role is absent');
  near(sharedA.volume,0.65,'shared primary fallback volume');
  near(sharedB.volume,0.65,'all shared fallback stems update');
  shared.setPlayerVolume(0.7);
  near(shared.getPlayerVolume(),0.7,'legacy player volume keeps its shared fallback');
  near(sharedB.volume,0.7,'legacy player setter updates all shared stems');

  opponentPrimary.volume=0.42;
  tracks.syncPrimaryVolume();
  near(playerStem.volume,0.42,'direct legacy primary writes still fan out');
  near(opponentStem.volume,0.42,'legacy fanout still reaches every other role');
 }
}
'''
        with tempfile.TemporaryDirectory(prefix="source-vocal-roles-", dir=ROOT / "tmp") as folder:
            scratch = FixturePath(folder)
            (scratch / "flixel/sound").mkdir(parents=True)
            (scratch / "flixel/sound/FlxSound.hx").write_text(sound_stub, encoding="utf-8", newline="\n")
            (scratch / "VocalTracks.hx").write_text(tracks_source, encoding="utf-8", newline="\n")
            (scratch / "Main.hx").write_text(main, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(scratch), "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
