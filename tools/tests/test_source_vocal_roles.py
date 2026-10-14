"""Split vocal stems keep the player and the opponent on separate buses."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def method(source: str, name: str) -> str:
    match = re.search(r"^\t(?:@:keep |override |public |static |private )*function " + re.escape(name) + r"\(",
                      source, re.M)
    if match is None:
        raise AssertionError(name)
    brace = source.index("{", match.start())
    depth = 0
    for pos in range(brace, len(source)):
        depth += (source[pos] == "{") - (source[pos] == "}")
        if depth == 0:
            return source[match.start():pos + 1]
    raise AssertionError(name)


FLX_SOUND = '''package flixel.sound;
class FlxSound {
  public var volume:Float = 1;
  public var time:Float = 0;
  public var pitch:Float = 1;
  public var name:String;
  public function new(?name:String) this.name = name;
  public function play():Void {}
  public function pause():Void {}
  public function stop():Void {}
  public function destroy():Void {}
  public function getActualVolume():Float return volume;
}
'''

RUNTIME_FIXTURE = r'''import flixel.sound.FlxSound;

class StemRoles {
  public var SONG:Dynamic;
  public function new(format:String) SONG = {format:format};
  RESOLVE
  public function role(entry:Dynamic):String return resolveImportedVocalStemRole(entry);
}

class Main {
  static function check(ok:Bool, message:String):Void if (!ok) throw message;
  static function main():Void {
    // the conventional names, whatever their case, with or without the old 'shared' role
    check(SourceVocalRole.resolve('Player', null) == 'player', 'Player id');
    check(SourceVocalRole.resolve('Opponent', 'shared') == 'opponent', 'Opponent id over shared');
    check(SourceVocalRole.resolve('opp', null) == 'opponent', 'short opponent id');
    check(SourceVocalRole.resolve(' OPPONENT ', '') == 'opponent', 'padded id');
    // an authored role always wins over the id
    check(SourceVocalRole.resolve('opp', 'mix-bus') == 'mix-bus', 'authored role lost');
    check(SourceVocalRole.resolve('backup', 'Opponent') == 'opponent', 'authored role should be normalized');
    // ids that name no side keep their old defaults
    check(SourceVocalRole.resolve('choir', 'shared') == 'shared', 'unknown shared stem changed bus');
    check(SourceVocalRole.resolve('choir', null) == 'player', 'unlabeled stem lost its player default');
    check(SourceVocalRole.resolve(null, null) == 'player', 'missing id');
    // a character can ask for its own file suffix
    check(SourceVocalRole.resolve('Lead', 'shared', 'lead', 'rival') == 'player', 'player suffix');
    check(SourceVocalRole.resolve('rival', null, 'lead', 'Rival') == 'opponent', 'opponent suffix');
    check(SourceVocalRole.resolve('duo', 'shared', 'duo', 'duo') == 'player', 'a shared suffix belongs to the player');
    check(SourceVocalRole.resolve('choir', 'shared', 'lead', '') == 'shared', 'empty suffix matched a stem');
    check(SourceVocalRole.namesSide('Opponent') && SourceVocalRole.namesSide('player')
      && !SourceVocalRole.namesSide('lead') && !SourceVocalRole.namesSide(null), 'side names');
    // the old class name is the same resolver
    check(NightmareVisionVocalRole.resolve('opp', 'shared') == 'opponent'
      && NightmareVisionVocalRole.resolve('backup', null) == 'player', 'alias drifted');

    // the player stem leads even though the files sort opponent first
    check(SourceVocalRole.primaryIndex(['opponent', 'player']) == 1, 'player stem should lead');
    check(SourceVocalRole.primaryIndex(['shared', 'shared']) == 0
      && SourceVocalRole.primaryIndex(['opponent']) == 0
      && SourceVocalRole.primaryIndex([]) == 0 && SourceVocalRole.primaryIndex(null) == 0,
      'songs without a player stem keep their first track');

    // charts imported before roles were written still split by stem id at load
    for (format in ['psych_v1', 'nmv2', '']) {
      var roles = new StemRoles(format);
      check(roles.role({id:'Opponent', role:'shared', file:'Voices-Opponent.ogg'}) == 'opponent',
        format + ': stale shared opponent stem');
      check(roles.role({id:'Player', role:'shared'}) == 'player', format + ': stale shared player stem');
      check(roles.role({id:'choir', role:'shared'}) == 'shared', format + ': unknown stem');
      check(roles.role('Voices-extra.ogg') == 'player' && roles.role({role:null}) == 'player',
        format + ': plain entries');
    }

    // a player miss mutes the player bus and leaves the opponent singing
    var opponent = new FlxSound('opponent');
    var player = new FlxSound('player');
    var tracks = new VocalTracks(player);
    tracks.setRole(player, SourceVocalRole.resolve('Player', 'shared'));
    tracks.add(opponent, SourceVocalRole.resolve('Opponent', 'shared'));
    check(tracks.setRoleVolume('player', 0, true), 'player bus missing');
    check(player.volume == 0 && opponent.volume == 1, 'a player miss muted the opponent');
    check(tracks.setRoleVolume('opponent', 0.5) && opponent.volume == 0.5 && player.volume == 0,
      'opponent bus is not independent');
    check(tracks.primaryFor('opponent') == opponent && tracks.primaryFor('Player') == player
      && tracks.primaryFor('shared') == null, 'one sound per side');
    // muting the player must not look like a script write that drags the others along
    tracks.syncPrimaryVolume();
    check(opponent.volume == 0.5, 'bus mute was mirrored to the other stems');

    // one combined track still mutes on a miss through the shared fallback
    var combined = new FlxSound('combined');
    var single = new VocalTracks(combined);
    single.setRole(combined, 'shared');
    check(single.setRoleVolume('player', 0, true) && combined.volume == 0, 'combined track fallback');
    check(single.primaryFor('opponent') == null, 'combined track has no opponent stem');
  }
}
'''

IMPORT_FIXTURE = r'''import sys.FileSystem;
import haxe.io.Path;
using StringTools;

typedef SongImportVocalStem = {
  var source:String;
  var destination:String;
  @:optional var id:String;
  @:optional var role:String;
}
typedef SongImport = { @:optional var vocalStems:Array<SongImportVocalStem>; }

class Main {
  METHODS
  static function check(ok:Bool, message:String):Void if (!ok) throw message;
  static function describe(folder:String):String {
    var song:SongImport = {vocalStems: findImportVocalStems(Path.join([Sys.args()[0], folder]))};
    normalizeSourceVocalRoles(song);
    return [for (stem in song.vocalStems) stem.destination + '=' + stem.role].join(',');
  }
  static function main():Void {
    // the split pair is played instead of the combined file beside it
    check(describe('pair-and-combined') == 'Voices-Opponent.ogg=opponent,Voices-Player.ogg=player',
      'pair beside combined: ' + describe('pair-and-combined'));
    check(describe('pair') == 'Voices-Opponent.ogg=opponent,Voices-Player.ogg=player', 'pair: ' + describe('pair'));
    // a player stem alone still replaces the combined file
    check(describe('player-and-combined') == 'Voices-Player.ogg=player',
      'player beside combined: ' + describe('player-and-combined'));
    // an opponent stem cannot stand in for the combined file
    check(describe('opponent-and-combined') == '', 'opponent beside combined: ' + describe('opponent-and-combined'));
    // other stems beside a combined file stay out, as before
    check(describe('named-and-combined') == '', 'named beside combined: ' + describe('named-and-combined'));
    check(describe('mixed-and-combined') == 'Voices-Opponent.ogg=opponent,Voices-Player.ogg=player',
      'mixed beside combined: ' + describe('mixed-and-combined'));
    // packs with their own stem names keep every stem on the shared bus
    check(describe('named') == 'Voices-alto.ogg=shared,Voices-bass.ogg=shared', 'named: ' + describe('named'));
    check(describe('combined') == '' && describe('nowhere') == '', 'no stems expected');
  }
}
'''


class SourceVocalRolesTest(unittest.TestCase):
    def test_stem_ids_resolve_to_separate_player_and_opponent_buses(self):
        play_state = (ROOT / "source/PlayState.hx").read_text()
        fixture = RUNTIME_FIXTURE.replace(
            "RESOLVE", method(play_state, "resolveImportedVocalStemRole"))
        loader = method(play_state, "initializeVocalTracks")
        self.assertLess(loader.index("SourceVocalRole.primaryIndex("), loader.index("vocals = sounds[0].sound"),
                        "the player stem has to be chosen before the main vocal object is")
        getter = method(play_state, "get_opponentVocals")
        self.assertIn("vocalTracks.primaryFor('opponent')", getter)
        self.assertIn("public var opponentVocals(get, never):FlxSound;", play_state)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            work = Path(scratch)
            (work / "flixel/sound").mkdir(parents=True)
            (work / "flixel/sound/FlxSound.hx").write_text(FLX_SOUND, newline="\n")
            for name in ("SourceVocalRole.hx", "NightmareVisionVocalRole.hx", "VocalTracks.hx"):
                (work / name).write_text((ROOT / "source" / name).read_text(), newline="\n")
            (work / "Main.hx").write_text(fixture, newline="\n")
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(work), "--run", "Main"], cwd=ROOT,
                                    capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_importer_keeps_the_split_pair_and_writes_its_roles(self):
        importer = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("engine == ImportEngine.NIGHTMARE_VISION || engine == ImportEngine.PSYCH", importer)
        methods = "\n".join(method(importer, name) for name in (
            "normalizedImportFileName", "isImportFile", "findImportFile", "findImportVocalStems",
            "normalizeSourceVocalRoles"))
        layouts = {
            "pair-and-combined": ["Inst.ogg", "Voices.ogg", "Voices-Player.ogg", "Voices-Opponent.ogg"],
            "pair": ["Inst.ogg", "Voices-Player.ogg", "Voices-Opponent.ogg"],
            "player-and-combined": ["Inst.ogg", "Voices.ogg", "Voices-Player.ogg"],
            "opponent-and-combined": ["Inst.ogg", "Voices.ogg", "Voices-Opponent.ogg"],
            "named-and-combined": ["Inst.ogg", "Voices.ogg", "Voices-alto.ogg"],
            "mixed-and-combined": ["Inst.ogg", "Voices.ogg", "Voices-alto.ogg", "Voices-Player.ogg",
                                   "Voices-Opponent.ogg"],
            "named": ["Inst.ogg", "Voices-alto.ogg", "Voices-bass.ogg"],
            "combined": ["Inst.ogg", "Voices.ogg"],
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            work = Path(scratch)
            songs = work / "songs"
            for folder, files in layouts.items():
                (songs / folder).mkdir(parents=True)
                for name in files:
                    (songs / folder / name).write_bytes(b"audio")
            code = work / "code"
            code.mkdir()
            for name in ("SourceVocalRole.hx", "ImportDirectoryListing.hx"):
                (code / name).write_text((ROOT / "source" / name).read_text(), newline="\n")
            (code / "Main.hx").write_text(IMPORT_FIXTURE.replace("METHODS", methods), newline="\n")
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(code), "--run", "Main", str(songs)], cwd=ROOT,
                                    capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
