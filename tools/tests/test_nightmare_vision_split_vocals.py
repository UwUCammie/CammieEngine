"""Regression coverage for Nightmare Vision's player/opponent vocal buses."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class NightmareVisionSplitVocalsTest(unittest.TestCase):
    def test_source_visualizer_vocal_groups_resolve_from_imported_stem_ids(self):
        play_state = (ROOT / "source/PlayState.hx").read_text()
        importer = (ROOT / "source/ModuleFunctions.hx").read_text()
        for marker in (
            "private function resolveImportedVocalStemRole",
        ):
            self.assertIn(marker, play_state)
        self.assertIn("format == 'nmv2'", play_state)
        self.assertIn("NightmareVisionVocalRole.resolve(authoredId, authoredRole)", play_state)
        self.assertIn("normalizeNightmareVisionVocalRoles(songData)", importer)
        self.assertIn("nmv-vocal-groups:", play_state)
        self.assertIn("nmv-vocal-pcm:", play_state)
        self.assertIn("markNightmareVisionVocalPcmSmoke();", play_state)
        self.assertIn("new NightmareVisionSpectogramAudioData(player[0])", play_state)
        self.assertIn("existing.role = resolvePreferredVocalStemRole(existing.role, entry)", play_state)

        role_resolver = extract_method(play_state, "private function resolveImportedVocalStemRole")
        preferred_role_resolver = extract_method(play_state, "private function resolvePreferredVocalStemRole")

        repair_methods = "\n".join(
            extract_method(importer, marker)
            for marker in (
                "static function vocalStemMetadataMatches",
                "static function updateChartVocalStemMetadata",
            )
        )
        fixture = '''
import flixel.sound.FlxSound;
import NightmareVisionPlayableSongView;
import NightmareVisionVocalRole;
import VocalTracks;

class VocalStemRepair {
''' + repair_methods + '''
  public static function verify():Void {
    var expected:Array<Dynamic> = [
      {id:"opp", role:"opponent", file:"Voices-opp.ogg"},
      {id:"player", role:"player", file:"Voices-player.ogg"}
    ];
    var chart:Dynamic = {song:{notes:[[10, 1]], events:[{time:55}], chartEditorTag:"preserve-me",
      needsVoices:true, vocalStems:[
      {id:"opp", role:"shared", file:"Voices-opp.ogg"},
      {id:"player", role:"shared", file:"Voices-player.ogg"}
    ]}};
    if (vocalStemMetadataMatches(expected, chart.song.vocalStems))
      throw "stale shared vocal roles were treated as current";
    if (!updateChartVocalStemMetadata(chart, expected))
      throw "existing chart vocal roles were not repaired";
    if (!vocalStemMetadataMatches(expected, chart.song.vocalStems)
        || chart.song.vocalStems[0].role != "opponent"
        || chart.song.vocalStems[1].role != "player")
      throw "corrected vocal metadata did not persist";
    if (chart.song.notes.length != 1 || chart.song.notes[0][0] != 10)
      throw "vocal metadata repair changed authored notes";
    if (chart.song.events.length != 1 || chart.song.events[0].time != 55
        || chart.song.chartEditorTag != "preserve-me")
      throw "vocal metadata repair changed other chart edits";
    if (updateChartVocalStemMetadata(chart, expected))
      throw "vocal metadata repair was not idempotent";
}
}

class VocalRoleResolver {
  public var SONG:Dynamic;
  public function new(format:String) this.SONG = {format:format};
''' + role_resolver + '''
''' + preferred_role_resolver + '''
  public function resolve(entry:Dynamic):String return resolveImportedVocalStemRole(entry);
  public function preferred(currentRole:String, entry:Dynamic):String
    return resolvePreferredVocalStemRole(currentRole, entry);
}

class SplitVocalTestMain {
  static function main():Void {
    var nmvRoles = new VocalRoleResolver("nmv2");
    if (nmvRoles.resolve("Voices-opp.ogg") != "player"
        || nmvRoles.resolve({file:"Voices-player.ogg"}) != "player"
        || nmvRoles.resolve({role:null}) != "player")
      throw "NMV string or ID-less stems lost their player fallback";
    if (nmvRoles.resolve({id:"opp", role:"shared"}) != "opponent"
        || nmvRoles.resolve({id:"player", role:"shared"}) != "player")
      throw "NMV split-stem IDs did not resolve to their vocal groups";
    if (nmvRoles.resolve({id:"opp", role:"mix-bus"}) != "mix-bus"
        || nmvRoles.resolve({role:"opponent"}) != "opponent")
      throw "explicit custom NMV vocal roles were overwritten";
    if (nmvRoles.preferred("player", {id:"opp"}) != "opponent")
      throw "preferred NMV alternate encoding lost its ID-derived role";
    var psychRoles = new VocalRoleResolver("psych_v1");
    if (psychRoles.resolve({id:"opp", role:"shared"}) != "shared"
        || psychRoles.resolve({id:"player", role:"mix-bus"}) != "mix-bus")
      throw "NMV stem-ID inference changed non-NMV role behavior";
    if (psychRoles.preferred("opponent", "Voices-opp.ogg") != "opponent"
        || psychRoles.preferred("opponent", {id:"opp"}) != "opponent"
        || psychRoles.preferred("opponent", {role:"player"}) != "player")
      throw "preferred non-NMV encoding changed its legacy role precedence";

    var opponent = new FlxSound(900);
    var player = new FlxSound(1000);
    var tracks = new VocalTracks(opponent);
    tracks.setRole(opponent, NightmareVisionVocalRole.resolve("opp", "shared"));
    tracks.add(player, NightmareVisionVocalRole.resolve("player", "shared"));
    var audio = new NightmareVisionPlayableSongView(function() return null,
      function() return 0, function() return tracks);

    if (audio.opponentVocals.members.length != 1 || audio.opponentVocals.members[0] != opponent)
      throw "NMV opponent vocal visualizer cannot resolve the opp stem";
    if (audio.playerVocals.members.length != 1 || audio.playerVocals.members[0] != player)
      throw "NMV player vocal visualizer cannot resolve the player stem";
    if (NightmareVisionVocalRole.resolve("backup", "opponent") != "opponent")
      throw "explicit vocal role was overwritten";
    if (NightmareVisionVocalRole.resolve("backup", null) != "player")
      throw "unlabeled vocal kept its native player default";
    if (NightmareVisionVocalRole.resolve("opp", "shared") != "opponent")
      throw "opponent stem alias is case-sensitive or unresolved";
    VocalStemRepair.verify();
    audio.release();
  }
}
'''
        stubs = {
            "flixel/sound/FlxSound.hx": '''package flixel.sound;
class FlxSound {
  public var volume:Float = 1;
  public var time:Float = 0;
  public var length:Float;
  public var playing:Bool = false;
  public var pitch:Float = 1;
  public function new(length:Float = 0) this.length = length;
  public function play(forceRestart:Bool = false, startTime:Float = 0, ?endTime:Null<Float>):Void {
    time = startTime; playing = true;
  }
  public function pause():Void playing = false;
  public function resume():Void playing = true;
  public function stop():Void { playing = false; time = 0; }
  public function destroy():Void {}
  public function getActualVolume():Float return volume;
}
'''
        }
        with tempfile.TemporaryDirectory(prefix="nmv-vocals-", dir=ROOT / "tmp") as scratch:
            work = Path(scratch)
            for relative, contents in stubs.items():
                path = work / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(contents, newline="\n")
            (work / "SplitVocalTestMain.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "-cp", str(ROOT / "source"), "--run", "SplitVocalTestMain"],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=90,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("updateChartVocalStemMetadata(existingChart, metadata)", importer)
        self.assertIn("updateChartVocalStemMetadata(existingChart, cast expectedVocalMetadata)", importer)
        self.assertIn("vocalStemMetadataMatches(expectedStems, existingStems)", importer)


if __name__ == "__main__":
    unittest.main()
