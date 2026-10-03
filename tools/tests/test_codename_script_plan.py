"""Destination-only Codename song and authored-stage selection."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class CodenameScriptPlanTest(unittest.TestCase):
    def test_note_type_sidecar_round_trip_and_selected_difficulty(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            (base / "Main.hx").write_text('''class Main {
 static function check(ok:Bool, reason:String):Void if (!ok) throw reason;
 static function rejected(raw:String):Bool {
  try { CodenameScriptPlan.parseNoteTypes(raw); return false; }
  catch (_:Dynamic) return true;
 }
 static function main():Void {
  var authored:Dynamic = {};
  Reflect.setField(authored, "hard", ["Ice", "No Anim Note", "Ice"]);
  Reflect.setField(authored, "easy", ["Other"]);
  var plan = CodenameScriptPlan.createNoteTypes("try-harder", authored);
  var raw = CodenameScriptPlan.stringifyNoteTypes(plan);
  var parsed = CodenameScriptPlan.parseNoteTypes(raw);
  check(parsed.version == 1 && parsed.song == "try-harder", "note sidecar identity");
  check(CodenameScriptPlan.noteTypesMetadataPath("owner", "try-harder")
    == "owner/songs/try-harder/__cammie_compat_note_types.json", "note sidecar path");
  check(CodenameScriptPlan.noteTypesMetadataPath("owner", "../foreign") == "",
    "unsafe note sidecar path");
  check(CodenameScriptPlan.selectedNoteTypes(parsed, "hard").join("|")
    == "Ice|No Anim Note|Ice", "authored note order or duplicates changed");
  check(CodenameScriptPlan.selectedNoteTypes(parsed, "easy").join(",") == "Other",
    "difficulty selection");
  check(CodenameScriptPlan.selectedNoteTypes(parsed, "unknown").length == 0,
    "missing difficulty should be empty");
  check(rejected('{"version":2,"song":"try-harder","difficulties":{}}')
    && rejected('{"version":1,"song":"try-harder","difficulties":{"../hard":[]}}')
    && rejected('{"version":1,"song":"try-harder","difficulties":{"hard":[3]}}'),
    "malformed note sidecar accepted");
 }
}''', newline='\n')
            process = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base), "--run", "Main"],
                cwd=ROOT, text=True, capture_output=True,
            )
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)

    def test_optional_exact_native_character_mapping(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            (base / "Main.hx").write_text('''import haxe.Json;
class Main {
  static function check(ok:Bool, reason:String):Void if (!ok) throw reason;
  static function rejected(value:Dynamic):Bool {
    try { CodenameScriptPlan.createCamera("song", value); return false; }
    catch (_:Dynamic) return true;
  }
  static function entry():Dynamic {
    var native:Dynamic = {};
    Reflect.setField(native, "Authored Name", "converted-name");
    Reflect.setField(native, "boyfriend", "bf");
    Reflect.setField(native, "bf", "bf");
    Reflect.setField(native, "ghost", null);
    return {stage:"room", nativeStage:"owned-room", lines:[{role:"player", type:1, position:null, visible:true,
      characters:["Authored Name", "Authored Name", "boyfriend", "bf", "ghost"]}],
      characters:{}, missingCharacters:["Authored Name", "boyfriend", "bf", "ghost"],
      nativeCharacters:native, stageOffsets:{}, stageOffsetsKnown:false,
      stageStartCamera:{x:null,y:null}, stagePlacement:null};
  }
  static function main():Void {
    var difficulties:Dynamic = {hard:entry()};
    var plan = CodenameScriptPlan.parseCamera(CodenameScriptPlan.stringifyCamera(
      CodenameScriptPlan.createCamera("song", difficulties)));
    var selected:Dynamic = CodenameScriptPlan.selectedCamera(plan, "hard");
    check(selected.nativeStage == "owned-room", "native stage identity lost");
    check(selected.lines[0].characters.length == 5, "duplicate occurrences collapsed");
    check(Reflect.field(selected.nativeCharacters, "Authored Name") == "converted-name",
      "transformed authored ID lost");
    check(selected.nativeCharacters.boyfriend == "bf" && selected.nativeCharacters.bf == "bf",
      "shared native fallback alias rejected");
    check(Reflect.hasField(selected.nativeCharacters, "ghost")
      && selected.nativeCharacters.ghost == null, "known unresolved actor lost");
    var old:Dynamic = entry();
    Reflect.deleteField(old, "nativeCharacters");
    Reflect.deleteField(old, "nativeStage");
    var oldPlan = CodenameScriptPlan.parseCamera(CodenameScriptPlan.stringifyCamera(
      CodenameScriptPlan.createCamera("song", {hard:old})));
    check(CodenameScriptPlan.selectedCamera(oldPlan, "hard").nativeCharacters == null,
      "old sidecar invented a mapping");
    check(CodenameScriptPlan.selectedCamera(oldPlan, "hard").nativeStage == null,
      "old sidecar invented native stage identity");
    var missing:Dynamic = entry();
    Reflect.deleteField(missing.nativeCharacters, "ghost");
    check(rejected({hard:missing}), "partial map silently lost an occurrence");
    var unsafe:Dynamic = entry();
    Reflect.setField(unsafe.nativeCharacters, "Authored Name", "../foreign");
    check(rejected({hard:unsafe}), "unsafe mapped registry name accepted");
    var malformed:Dynamic = entry();
    Reflect.setField(malformed.nativeCharacters, "bf", 3);
    check(rejected({hard:malformed}), "non-string mapped registry name accepted");
    var wrongShape:Dynamic = entry(); wrongShape.nativeCharacters = [];
    check(rejected({hard:wrongShape}), "array native mapping accepted");
    var unsafeStage:Dynamic = entry(); unsafeStage.nativeStage = "../foreign";
    check(rejected({hard:unsafeStage}), "unsafe native stage accepted");
  }
}
''', newline='\n')
            process = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base), "--run", "Main"],
                cwd=ROOT, text=True, capture_output=True,
            )
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)

    def test_aliases_exact_stage_names_and_invalid_metadata(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            (base / "Main.hx").write_text('''class Main {
  static function rejects(raw:String):Bool {
    try { CodenameScriptPlan.parse(raw); return false; }
    catch (_:Dynamic) return true;
  }
  static function main():Void {
    var authored:Dynamic = {};
    Reflect.setField(authored, "hard", "Stage_One");
    Reflect.setField(authored, "easy", "stage-Two");
    var plan = CodenameScriptPlan.create("source-folder", authored);
    var parsed = CodenameScriptPlan.parse(CodenameScriptPlan.stringify(plan));
    if (parsed.song != "source-folder" || CodenameScriptPlan.selectedStage(parsed, "hard") != "Stage_One"
        || CodenameScriptPlan.selectedStage(parsed, "easy") != "stage-Two"
        || CodenameScriptPlan.selectedStage(parsed, "unknown") != "") throw "stage selection";
    if (CodenameScriptPlan.metadataPath("owned", parsed.song)
        != "owned/songs/source-folder/__cammie_compat_scripts.json") throw "folder alias";
    if (CodenameScriptPlan.metadataPath("owned", "../other") != "") throw "unsafe path";
    if (!rejects('{"version":2,"song":"source-folder","stages":{}}')
        || !rejects('{"version":1,"song":"../other","stages":{}}')
        || !rejects('{"version":1,"song":"source-folder","stages":{"hard":"../other"}}')
        || !rejects('{"version":1,"song":"source-folder","stages":{"../hard":"stage"}}')
        || !rejects('{"version":1,"song":"source-folder","stages":4}')) throw "unsafe plan";
  }
}
''', newline='\n')
            process = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base), "--run", "Main"],
                cwd=ROOT, text=True, capture_output=True,
            )
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)


if __name__ == "__main__":
    unittest.main()
