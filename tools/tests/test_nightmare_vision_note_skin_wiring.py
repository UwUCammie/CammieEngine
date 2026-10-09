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
            "function nightmareVisionDefaultSkinForField(",
            "function nightmareVisionKeyCount(",
            "public function nightmareVisionSkinForStrumline(",
            "function configureNightmareVisionNoteSkin(",
            "function applyNightmareVisionNoteSkin(",
        ))
        # Atlas-provider binding is outside this extracted skin-selection subject.
        fixture = '''using StringTools;
class NightmareVisionSpriteMethods {public static function bind(object:Dynamic,owner:Dynamic):Void {}}
class NightmareVisionSpriteRegistry {public static function capture(paths:Dynamic):Dynamic return null;}
class NightmareVisionPaths {
 public var root:String;
 public function new(root:String) this.root=root;
}
class NightmareVisionNoteSkin {
 public var noteTexture="NOTE_assets";public var splashTexture="noteSplashes";
 public var paths:NightmareVisionPaths; public var name:String;
 public var applied:Array<Int>=[];
 public var quantsEnabled:Bool=true;
 public var keys:Int; public var ID:Int;
 public function new(paths:NightmareVisionPaths,name:String,keys:Int=4,id:Int=0) {
  this.paths=paths;this.name=name;this.keys=keys;this.ID=id;
 }
 public function stringField(key:String,fallback:String):String return fallback;
 public function applyNote(note:Note,lane:Int,?frames:Dynamic):Bool {applied.push(lane);return true;}
}
class FlxAtlasFrames {}
class NightmareVisionQuantRendering {
 public static var classifyCalls:Int=0; public static var applyCalls:Int=0;
 public static var classifiedNote:Note; public static var appliedNote:Note;
 public static var classifiedPrefs:Dynamic; public static var appliedPrefs:Dynamic;
 public static var appliedSkin:NightmareVisionNoteSkin; public static var classifiedBeat:Float=0;
 public static function classify(note:Note,prefs:Dynamic,beat:Float,legacy:Bool=false):Void {
  if (note==null || note.nightmareVisionQuantInitialized) return;
  note.nightmareVisionQuantInitialized=true;
  classifyCalls++; classifiedNote=note; classifiedPrefs=prefs; classifiedBeat=beat;
  if (prefs!=null && prefs.quants==true && note.canQuant) note.quant=12;
 }
 public static function apply(note:Note,skin:NightmareVisionNoteSkin,prefs:Dynamic):Void {
  applyCalls++; appliedNote=note; appliedSkin=skin; appliedPrefs=prefs;
  note.isQuant=prefs!=null && prefs.quants==true && skin.quantsEnabled && note.canQuant;
 }
}
class NightmareVisionNoteTypeRuntime {
 public function new() {}
 public function setupNote(note:Note):Void {}
 public function syncNote(note:Note):Void {}
}
class NightmareVisionRGBGraphics {public var legacyHSV:Dynamic;public function new(){}}
class NightmareVisionLegacyNoteColors {public var swap:Dynamic;public function new(p:Dynamic,?s:String){}public static function selectTexture(t:String,p:Dynamic,q:Bool,a:String->Bool):String return t;}
class Note {
 public var nightmareVisionLegacyColors:NightmareVisionLegacyNoteColors;
 public var nightmareVisionRGB:NightmareVisionRGBGraphics;
 public var colorSwap:Dynamic;
 public static inline var NOTE_AMOUNT:Int=4;
 public var nightmareVisionTypeRuntime:NightmareVisionNoteTypeRuntime;
 public var quant:Int=4; public var isQuant:Bool=false; public var canQuant:Bool=true;
 public var nightmareVisionQuantInitialized:Bool=false;
 public var strumTime:Float=0;
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
 var nightmareVisionLegacyFieldCameras=false;
 function nightmareVisionHasOwnerSparrowAtlas(s:String):Bool return false;
 function nightmareVisionGetOwnerSparrowAtlas(s:String):FlxAtlasFrames return null;
 var nightmareVisionNoteTypes:NightmareVisionNoteTypeRuntime;
 var nightmareVisionPaths:NightmareVisionPaths;
 var nightmareVisionNoteSkins:Map<String,NightmareVisionNoteSkin>;
 var SONG:Dynamic;
 var arrowSkins:Array<String>;
 var playerStrums:Strumline; var enemyStrums:Strumline;
 var nightmareVisionFields:Array<{ID:Int,strumline:Strumline}>=[];
 var playFields:Dynamic=null;
 var nightmareVisionPrefs:Dynamic;
 var nightmareVisionConductor:Dynamic;
 var beatCalls:Int=0;
 var beatInput:Float=0;
 public function new() {}
''' + methods + '''
 static function main():Void {
  var s=new SkinWiring(); s.nightmareVisionPaths=new NightmareVisionPaths("owner-a");
  s.SONG={arrowSkins:["pink","gray"]};s.arrowSkins=s.SONG.arrowSkins;
  s.playerStrums=new Strumline(); s.enemyStrums=new Strumline();
  s.nightmareVisionFields=[{ID:0,strumline:s.playerStrums},{ID:1,strumline:s.enemyStrums}];
  var first=s.nightmareVisionSkinForField(0), second=s.nightmareVisionSkinForField(1);
  if (first==second || first.name!="pink" || second.name!="gray") throw "field skins merged";
  if (first.paths.root!="owner-a" || second.paths.root!="owner-a") throw "owner lost";
  if (first.keys!=4 || first.ID!=0 || second.ID!=1) throw "source skin key/player identity lost";
  if (s.nightmareVisionSkinForStrumline(s.playerStrums)!=first
   || s.nightmareVisionSkinForStrumline(s.enemyStrums)!=second) throw "line routing wrong";
  var note=new Note(1,3); note.ratingDisabled=true; note.rating="good"; note.ratingMod=0.8;
  note.strumTime=300;
  s.nightmareVisionNoteTypes=new NightmareVisionNoteTypeRuntime();
  s.nightmareVisionPrefs={view:{quants:true,noteOffset:50}};
  s.nightmareVisionConductor={getBeat:function(time:Float):Float {s.beatCalls++;s.beatInput=time;return time/100;}};
  s.configureNightmareVisionNoteSkin(note);
  if (second.applied.join(",")!="3" || RuntimeSmokeHarness.marks!=1) throw "note lane wrong";
  if (NightmareVisionQuantRendering.classifyCalls!=1
   || NightmareVisionQuantRendering.classifiedNote!=note
   || NightmareVisionQuantRendering.classifiedPrefs!=s.nightmareVisionPrefs.view
   || NightmareVisionQuantRendering.classifiedBeat!=2.5 || s.beatInput!=250 || note.quant!=12
   || !note.nightmareVisionQuantInitialized || s.beatCalls!=1) throw "source quant classification inputs lost";
  if (NightmareVisionQuantRendering.applyCalls!=1
   || NightmareVisionQuantRendering.appliedNote!=note
   || NightmareVisionQuantRendering.appliedSkin!=second
   || NightmareVisionQuantRendering.appliedPrefs!=s.nightmareVisionPrefs.view
   || !note.isQuant) throw "quant rendering did not follow selected field skin";
  if (note.nightmareVisionTypeRuntime!=s.nightmareVisionNoteTypes || note.rating!=null
   || !note.ratingDisabled || note.ratingMod!=0) throw "type attach did not reset rating while preserving disabled flag";
  if (note.sourceSemanticsApplied!=1) throw "source semantics not applied on attach";
  s.nightmareVisionConductor={getBeat:function(time:Float):Float {s.beatCalls++;return time/100+100;}};
  s.configureNightmareVisionNoteSkin(note);
  if (NightmareVisionQuantRendering.classifyCalls!=1 || note.quant!=12 || s.beatCalls!=2)
   throw "initialized note must keep its original quant classification";
  var missingSkinNote=new Note(1,2);
  var selectedPaths=s.nightmareVisionPaths;
  s.nightmareVisionPaths=null;
  s.configureNightmareVisionNoteSkin(missingSkinNote);
  if (NightmareVisionQuantRendering.classifyCalls!=1 || missingSkinNote.nightmareVisionQuantInitialized
   || missingSkinNote.quant!=4 || s.beatCalls!=2)
   throw "missing skin must not classify a source note";
  s.nightmareVisionPaths=selectedPaths;
  s.SONG={arrowSkins:[]};s.arrowSkins=s.SONG.arrowSkins;
  if (s.nightmareVisionSkinForField(0).name!="default") throw "missing skin has no source default";
  var sameNameFirst=s.nightmareVisionSkinForField(0), sameNameSecond=s.nightmareVisionSkinForField(1);
  if (sameNameFirst==sameNameSecond || sameNameSecond.ID!=1) throw "mutable skin instances merged across fields";
  sameNameFirst.name="mutated";
  if (sameNameSecond.name!="default") throw "skin mutation leaked between fields";
  var injected=new NightmareVisionNoteSkin(s.nightmareVisionPaths,"injected");
  s.playFields={getFieldFromID:function(id:Int):Dynamic return id==0 ? {_skin:injected} : null};
  if(s.nightmareVisionSkinForField(0)!=injected
   ||s.nightmareVisionSkinForStrumline(s.playerStrums)!=injected) throw "live injected field skin lost";
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
