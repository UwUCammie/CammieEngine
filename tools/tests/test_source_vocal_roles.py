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
  public var length:Float = 0;
  public var playing:Bool = false;
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
  public var boyfriend:Dynamic;
  public var dad:Dynamic;
  public function new(format:String) SONG = {format:format};
  function characterVocalsFile(character:Dynamic):String return character == null ? null : character.vocalsFile;
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

    // a character's vocals_file names its stem at load, as in Psych
    var named = new StemRoles('psych_v1');
    named.boyfriend = {vocalsFile:'bf-alt'};
    named.dad = {vocalsFile:''};
    check(named.role({id:'bf-alt', role:'shared'}) == 'player' && named.role({id:'Opponent', role:'shared'}) == 'opponent',
      'character vocals_file stem');
    // once a character's own file is there, stems nobody asks for stay silent
    function kept(ids:Array<Dynamic>, player:String, opponent:String):String
      return [for (index in 0...ids.length) if (SourceVocalRole.keepStems(ids, player, opponent)[index]) Std.string(ids[index])].join(',');
    check(kept(['Player', 'Opponent', 'bf-alt', 'gf-alt'], 'bf-alt', null) == 'Opponent,bf-alt',
      'player file replaces Voices-Player: ' + kept(['Player', 'Opponent', 'bf-alt', 'gf-alt'], 'bf-alt', null));
    check(kept(['Player', 'Opponent', 'pico'], null, 'Pico') == 'Player,pico', 'opponent file replaces Voices-Opponent');
    check(kept(['Player', 'Opponent', 'choir'], 'bf-alt', 'rival') == 'Player,Opponent,choir',
      'nothing is dropped when no character file was shipped');
    check(kept(['alto', 'bass'], null, null) == 'alto,bass' && kept([null, 'Player'], 'lead', '') == 'null,Player',
      'free stem names without character files keep every stem');
    // a format that gave each stem its side (V-Slice) keeps them even when an id
    // happens to be a character's vocals_file; Psych's own side names still follow the rule
    var vsliceKeep = SourceVocalRole.keepStems(['pico', 'darnell', 'Player'], 'pico', null, ['player', 'opponent', 'player']);
    check(vsliceKeep.join(',') == 'true,true,false', 'stems with a format-given side were dropped: ' + vsliceKeep.join(','));
    check(SourceVocalRole.keepStems(['bf-alt', 'choir'], 'bf-alt', null, ['shared', 'shared']).join(',') == 'true,false',
      'shared stems still follow the Psych rule');
    // with the combined file as the player's fallback the source rule is exact:
    // the player's own stem or the combined file, the opponent's own stem, and
    // no character-named stem nobody asks for
    function withFallback(ids:Array<Dynamic>, player:String, opponent:String):String {
      var roles:Array<Dynamic> = [for (id in ids) id == 'Voices' ? 'player' : 'shared'];
      var keep = SourceVocalRole.keepStems(ids, player, opponent, roles);
      return [for (index in 0...ids.length) if (keep[index]) Std.string(ids[index])].join(',');
    }
    check(withFallback(['Voices', 'pico', 'tankman'], 'bf', 'pico') == 'Voices,pico',
      'opponent file beside the combined file: ' + withFallback(['Voices', 'pico', 'tankman'], 'bf', 'pico'));
    check(withFallback(['Voices', 'bf-alt', 'pico'], 'bf-alt', 'pico') == 'bf-alt,pico',
      'player file replaces the combined file: ' + withFallback(['Voices', 'bf-alt', 'pico'], 'bf-alt', 'pico'));
    check(withFallback(['Voices', 'alto', 'bass'], null, null) == 'Voices',
      'unasked character stems must not double the combined file: ' + withFallback(['Voices', 'alto', 'bass'], null, null));
    check(withFallback(['Voices', 'Opponent', 'alto'], null, '') == 'Voices,Opponent',
      'side stem beside the combined file: ' + withFallback(['Voices', 'Opponent', 'alto'], null, ''));
    check(withFallback(['Voices', 'Opponent', 'rival'], null, 'rival') == 'Voices,rival',
      'opponent file replaces Voices-Opponent beside the combined file');
    // the old import id for the fallback still reads as a plain player stem
    check(withFallback(['Player', 'Opponent'], null, null) == 'Player,Opponent', 'older fallback id changed');
    // only the importer's player-role fallback switches the exact rule on, and
    // never beside stems whose format already gave them a side
    check(SourceVocalRole.keepStems(['Voices', 'alto'], null, null, ['shared', 'shared']).join(',') == 'true,true',
      'a shared stem named Voices is not the combined fallback');
    check(SourceVocalRole.keepStems(['Voices', 'bf', 'dad'], 'bf', 'dad', ['player', 'player', 'opponent']).join(',')
      == 'true,true,true', 'format-given sides were dropped by the combined fallback rule');

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
  static function describe(folder:String, combinedPlaysAsPlayer:Bool = true, followCharacters:Bool = true):String {
    var song:SongImport = {vocalStems: findImportVocalStems(Path.join([Sys.args()[0], folder]), combinedPlaysAsPlayer,
      followCharacters)};
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
    // an opponent stem beside the combined file plays with that file as the
    // player's voice, the way Psych and Nightmare Vision fall back to it
    check(describe('opponent-and-combined') == 'Voices.ogg=player,Voices-Opponent.ogg=opponent',
      'opponent beside combined: ' + describe('opponent-and-combined'));
    // engines that only load the combined file never played that stem, so it
    // stays out for them; their other layouts read the same as before
    check(describe('opponent-and-combined', false) == '',
      'opponent beside combined without the fallback: ' + describe('opponent-and-combined', false));
    for (folder in ['pair-and-combined', 'pair', 'player-and-combined', 'mixed-and-combined', 'named', 'combined'])
      check(describe(folder, false) == describe(folder), 'fallback flag changed ' + folder);
    // character-named stems beside a combined file come along with the
    // fallback; which one plays is decided at load from the characters
    check(describe('named-and-combined') == 'Voices.ogg=player,Voices-alto.ogg=shared',
      'named beside combined: ' + describe('named-and-combined'));
    check(describe('named-and-combined', false) == '',
      'named beside combined without the fallback: ' + describe('named-and-combined', false));
    // Nightmare Vision never reads vocals_file: it keeps the opponent stem
    // beside the combined file but never a character-named one
    check(describe('named-and-combined', true, false) == '',
      'named beside combined for an engine without vocals_file: ' + describe('named-and-combined', true, false));
    check(describe('opponent-and-combined', true, false) == describe('opponent-and-combined'),
      'opponent fallback must not depend on vocals_file support');
    check(describe('mixed-and-combined', true, false) == describe('mixed-and-combined'),
      'mixed layout changed without vocals_file support');
    var fallbackIds = [for (stem in findImportVocalStems(Path.join([Sys.args()[0], 'opponent-and-combined']), true)) stem.id];
    check(fallbackIds.join(',') == SourceVocalRole.COMBINED_FALLBACK_ID + ',Opponent',
      'combined fallback id: ' + fallbackIds.join(','));
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
        self.assertIn("SourceVocalRole.keepStems([for (entry in stems) vocalStemId(entry)]", loader)
        self.assertIn("if (!keepStem[stemIndex])", loader)
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
        # Only the Psych-family discovery asks for the combined-file fallback; the
        # shared song builder keeps the default for every other engine.
        # Character-named stems follow vocals_file, which only Psych reads.
        call = "findImportVocalStems(songFolder, true, engine == ImportEngine.PSYCH)"
        self.assertEqual(importer.count("findImportVocalStems(songFolder, true"), 1)
        self.assertEqual(importer.count(call), 1)
        gate = importer.index("if (songData != null && (engine == ImportEngine.NIGHTMARE_VISION || engine == ImportEngine.PSYCH)) {")
        fallback = importer.index(call)
        self.assertLess(gate, fallback)
        self.assertLess(fallback, importer.index("normalizeSourceVocalRoles(songData);", gate))
        self.assertIn("var splitVocalStems = findImportVocalStems(audioRoot);", importer)
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
