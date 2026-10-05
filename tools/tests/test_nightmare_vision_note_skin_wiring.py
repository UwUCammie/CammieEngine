"""Nightmare Vision selects one owner-local note skin per source playfield."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

from tools.tests.test_psych_character_scope import extract_method


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class NightmareVisionNoteSkinWiringTest(unittest.TestCase):
    def test_source_fields_use_their_own_skin_and_default(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        methods = "\n".join(extract_method(source, marker) for marker in (
            "public function nightmareVisionSkinForField(",
            "public function nightmareVisionSkinForStrumline(",
            "function configureNightmareVisionNoteSkin(",
        ))
        fixture = '''using StringTools;
class NightmareVisionPaths {
 public var root:String;
 public function new(root:String) this.root=root;
}
class NightmareVisionNoteSkin {
 public var paths:NightmareVisionPaths; public var name:String;
 public var applied:Array<Int>=[];
 public function new(paths:NightmareVisionPaths,name:String) {this.paths=paths;this.name=name;}
 public function stringField(key:String,fallback:String):String return fallback;
 public function applyNote(note:Note,lane:Int):Bool {applied.push(lane);return true;}
}
class NightmareVisionNoteTypeRuntime {
 public function new() {}
 public function setupNote(note:Note):Void {}
}
class Note {
 public var nightmareVisionTypeRuntime:NightmareVisionNoteTypeRuntime;
 public var sourceSemanticsApplied:Int=0;
 public function applyPendingSourceNoteSemantics():Void {
  if (nightmareVisionTypeRuntime==null) throw "semantics before runtime attach";
  sourceSemanticsApplied++;
 }
 public var sourcePlayfieldIndex:Int; public var sourceDirection:Int; public var noteData:Int;
 public var ratingDisabled:Bool=false; public var rating:Dynamic="miss"; public var ratingMod:Float=0;
 public function new(field:Int,lane:Int) {sourcePlayfieldIndex=field;sourceDirection=lane;noteData=lane;}
 public function resetSourceRatingState():Void {
  ratingDisabled=false; rating=nightmareVisionTypeRuntime==null ? "miss" : null; ratingMod=0;
 }
}
class Strumline {public function new() {}}
class RuntimeSmokeHarness {
 public static var marks:Int=0;
 public static function markNightmareVisionNoteVisual(note:Note):Void marks++;
}
class SkinWiring {
 var nightmareVisionNoteTypes:NightmareVisionNoteTypeRuntime;
 var nightmareVisionPaths:NightmareVisionPaths;
 var nightmareVisionNoteSkins:Map<String,NightmareVisionNoteSkin>;
 var SONG:Dynamic;
 var playerStrums:Strumline; var enemyStrums:Strumline;
 var nightmareVisionFields:Array<{ID:Int,strumline:Strumline}>=[];
 public function new() {}
''' + methods + '''
 static function main():Void {
  var s=new SkinWiring(); s.nightmareVisionPaths=new NightmareVisionPaths("owner-a");
  s.SONG={arrowSkins:["pink","gray"]};
  s.playerStrums=new Strumline(); s.enemyStrums=new Strumline();
  s.nightmareVisionFields=[{ID:0,strumline:s.playerStrums},{ID:1,strumline:s.enemyStrums}];
  var first=s.nightmareVisionSkinForField(0), second=s.nightmareVisionSkinForField(1);
  if (first==second || first.name!="pink" || second.name!="gray") throw "field skins merged";
  if (first.paths.root!="owner-a" || second.paths.root!="owner-a") throw "owner lost";
  if (s.nightmareVisionSkinForStrumline(s.playerStrums)!=first
   || s.nightmareVisionSkinForStrumline(s.enemyStrums)!=second) throw "line routing wrong";
  var note=new Note(1,3); note.ratingDisabled=true; note.rating="good"; note.ratingMod=0.8;
  s.nightmareVisionNoteTypes=new NightmareVisionNoteTypeRuntime();
  s.configureNightmareVisionNoteSkin(note);
  if (second.applied.join(",")!="3" || RuntimeSmokeHarness.marks!=1) throw "note lane wrong";
  if (note.nightmareVisionTypeRuntime!=s.nightmareVisionNoteTypes || note.rating!=null
   || !note.ratingDisabled || note.ratingMod!=0) throw "type attach did not reset rating while preserving disabled flag";
  if (note.sourceSemanticsApplied!=1) throw "source semantics not applied on attach";
  s.SONG={arrowSkins:[]};
  if (s.nightmareVisionSkinForField(0).name!="default") throw "missing skin has no source default";
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "SkinWiring.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "SkinWiring", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_generated_taps_and_holds_use_the_shared_skin(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        for note in ("swagNote", "sustainNote"):
            self.assertIn(f"configureNightmareVisionNoteSkin({note});", source)
        self.assertIn("skin.applyReceptor(strum, strum.ID)", source)


if __name__ == "__main__":
    unittest.main()
