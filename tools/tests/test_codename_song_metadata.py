"""Execute the real Codename data-only song metadata codec."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / '.tools/haxe/haxe'


class CodenameSongMetadataTest(unittest.TestCase):
    def test_original_fields_owner_validation_and_repair_shape(self):
        source = r'''import haxe.Json;
class Main {
 static function rejects(raw:String, expected:String):Void {
  var failed = false;
  try CodenameSongMetadata.parse(raw, expected) catch (_:Dynamic) failed = true;
  if (!failed) throw "accepted invalid meta";
 }
 static function main():Void {
  var original:Dynamic = Json.parse('{"name":"Song ID","displayName":"Fancy Name",'
    + '"icon":"star","parsedColor":-123,"customValues":{"nested":[true,2.5,"x"]}}');
  var record = CodenameSongMetadata.create("Song ID", original);
  original.customValues.nested[2] = "edited after create";
  var encoded = CodenameSongMetadata.stringify(record);
  var restored = CodenameSongMetadata.parse(encoded, "Song ID");
  if (restored.meta.displayName != "Fancy Name" || restored.meta.icon != "star"
      || restored.meta.parsedColor != -123 || restored.meta.customValues.nested[2] != "x")
    throw "original meta fields lost";
  if (CodenameSongMetadata.path("owner", "Song ID")
      != "owner/songs/Song ID/__cammie_compat_song_meta.json") throw "path";
  rejects(encoded, "Other Song");
  rejects('{"version":2,"song":"Song ID","meta":{}}', "Song ID");
  var alias = CodenameSongMetadata.parse('{"version":1,"song":"Song ID",'
      + '"meta":{"name":"Other Song"}}', "Song ID");
  if (alias.meta.name != "Other Song") throw "authored meta alias lost";
  rejects('{"version":1,"song":"Song ID","meta":{"name":"../outside"}}', "Song ID");
  rejects('{"version":1,"song":"../outside","meta":{}}', "../outside");
  rejects('{"version":1,"song":"Song ID","meta":[1]}', "Song ID");
  // Some valid Codename meta.json files omit `name` and retain customValues.
  var nameless = CodenameSongMetadata.parse('{"version":1,"song":"hopkins",'
      + '"meta":{"displayName":"Hopkins","customValues":{"x":1}}}', "hopkins");
  if (nameless.meta.customValues.x != 1) throw "nameless donor meta rejected";
  var entries:Dynamic = {};
  Reflect.setField(entries,"hard",{selectedFile:"meta-hard.json",
    fileMeta:{displayName:"Hard Name",bpm:172,needsVoices:false,customValues:{route:"hard"}},
    inlineMeta:{bpm:180,displayName:null,icon:"inline",customValues:{route:"chart"}}});
  Reflect.setField(entries,"normal",{selectedFile:"meta.json",
    fileMeta:{displayName:"Base Name",customValues:{route:"base"}},inlineMeta:null});
  var resolved = CodenameSongMetadata.createResolved("hopkins",["hard","normal"],entries);
  var hard = CodenameSongMetadata.selectedResolved(resolved,"hard");
  var normal = CodenameSongMetadata.selectedResolved(resolved,"normal");
  if (hard.name!="hopkins" || hard.displayName!="Hard Name" || hard.bpm!=180
      || hard.needsVoices!=false || hard.icon!="inline" || hard.customValues.route!="chart")
    throw "difficulty or inline precedence";
  if (normal.name!="hopkins" || normal.bpm!=100 || normal.needsVoices!=true
      || normal.icon!="face" || normal.beatsPerMeasure!=4 || normal.stepsPerBeat!=4
      || normal.displayName!="Base Name" || normal.color!=0xFF9271FD)
    throw "pinned metadata defaults";
  var flags = CodenameSongMetadata.configDefaults("[Common]\nDEFAULT_BPM=999\n"
    + "[Flags]\nDEFAULT_BPM=132.5\nDEFAULT_BEATS_PER_MEASURE=3\n"
    + "DEFAULT_STEPS_PER_BEAT=6\nDEFAULT_HEALTH_ICON='custom'\n"
    + "DEFAULT_CHARACTER=owner-default\n"
    + "DEFAULT_COOP_ALLOWED=true\nDEFAULT_OPPONENT_MODE_ALLOWED=false\n"
    + "DEFAULT_COLOR=0xFF112233\n");
  var configured = CodenameSongMetadata.resolve("hopkins",{},null,["normal"],flags);
  if (configured.bpm!=132.5 || configured.beatsPerMeasure!=3
      || configured.stepsPerBeat!=6 || configured.icon!="custom"
      || configured.coopAllowed!=true || configured.opponentModeAllowed!=false
      || configured.color!=0xFF112233 || flags.characterFallback!="owner-default")
    throw "Codename flags defaults";
  var authored = CodenameSongMetadata.resolve("hopkins",{bpm:160,color:"#ABCDEF"},
    {bpm:180},["normal"],flags);
  if (authored.bpm!=180 || authored.color!=0xFFABCDEF)
    throw "authored metadata must outrank config defaults";
  var configuredEntries:Dynamic = {};
  Reflect.setField(configuredEntries,"normal",{selectedFile:"meta.json",
    fileMeta:{},inlineMeta:null,configDefaults:flags});
  var flagged = CodenameSongMetadata.createResolved("hopkins",["normal"],configuredEntries);
  if (CodenameSongMetadata.selectedResolved(CodenameSongMetadata.parseResolved(
      CodenameSongMetadata.stringifyResolved(flagged),"hopkins"),"normal").bpm!=132.5)
    throw "resolved flags provenance";
  var roundtrip = CodenameSongMetadata.parseResolved(
    CodenameSongMetadata.stringifyResolved(resolved),"hopkins");
  if (CodenameSongMetadata.selectedResolved(roundtrip,"hard").bpm!=180)
    throw "resolved roundtrip";
  var wrong:Dynamic=Json.parse(CodenameSongMetadata.stringifyResolved(resolved));
  wrong.difficulties.hard.resolved.bpm=190;
  var refused=false;
  try CodenameSongMetadata.createResolved("hopkins",wrong.chartDifficulties,wrong.difficulties)
  catch (_:Dynamic) refused=true;
  if (!refused) throw "importer accepted stale derived metadata";
  var repaired=CodenameSongMetadata.parseResolved(Json.stringify(wrong),"hopkins");
  if (CodenameSongMetadata.selectedResolved(repaired,"hard").bpm!=180)
    throw "runtime did not rebuild derived metadata from source fields";
  if (CodenameSongMetadata.selectedResolved(roundtrip,"HARD")!=null)
    throw "difficulty case guessed";
  var derived=CodenameSongMetadata.resolve("song",{},null,["hard","easy","normal"]);
  if (derived.name!="song" || derived.displayName!="song"
      || derived.difficulties.join(",")!="easy,normal,hard")
    throw "source name or canonical difficulty defaults";
  for (entry in [
    {input:" red ",expected:0xFFFF0000},
    {input:"0xFF123456",expected:0xFF123456},
    {input:" 0x123456 ",expected:0xFF123456},
    {input:"#123456",expected:0xFF123456},
    {input:"#80123456",expected:0x80123456},
    {input:"invalid",expected:0xFF9271FD}
  ]) {
    var colored=CodenameSongMetadata.resolve("song",{color:entry.input},null,["normal"]);
    if (colored.color!=entry.expected) throw "FlxColor string semantics: " + entry.input;
  }
}
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'Main.hx').write_text(source, newline='\n')
            run = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                                  '--run', 'Main'], cwd=ROOT, capture_output=True, text=True,
                                 timeout=30)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == '__main__':
    unittest.main()
