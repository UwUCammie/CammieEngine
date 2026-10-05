"""Source Psych travel/lifetime integration, independent of the native renderer."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from test_psych_note_follow import extract_method

ROOT = Path(__file__).resolve().parents[2]


class PsychNoteFollowIntegrationTest(unittest.TestCase):
    def test_host_passes_preserve_psych_geometry(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("if (daNote.codenameInputLine != null || nightmareVisionScripts != null || isPsychReceptorNote(daNote))", source)
        self.assertIn("if (psychPresentation) {\n\t\t\t\t\tapplyPsychNotePresentation(daNote, daNoteStrums, noteScrollSpeed);\n\t\t\t\t} else if (nightmareContext == null)", source)
        self.assertIn("if (!psychPresentation && nightmareContext == null)", source)
        self.assertIn("if (nightmareContext == null && !psychPresentation && daNote.y > FlxG.height)", source)
        self.assertIn("if (!psychPresentation && nightmareVisionScripts == null && ((daNote.y", source)
        self.assertNotIn("daNote.updateAutoHit(Conductor.songPosition);\n\t\t\t\tif (updatePsychNoteLifetime(daNote)) return;", source)
        self.assertIn("dispatchNoteStrumCallback(daNote);\n\t\t\t\tapplyPsychNoteClip(daNote, daNoteStrums);\n\t\t\t\tif (updatePsychNoteLifetime(daNote)) return;", source)
        self.assertEqual(source.count("applyPsychNoteClip(daNote, daNoteStrums);\n\t\t\t\t\t\tupdatePsychNoteLifetime(daNote);"), 2)
        self.assertEqual(source.count("note.applyPsychReceptorAlpha(receptor.alpha);"), 1)
        self.assertNotIn("daNote.applyPsychReceptorAlpha", source)
        self.assertIn("if (psychSustain) sustainNote.finalizePsychSustainSegment(oldNote, swagNote, psychSectionStep,", source)

    def test_live_receptor_parameters_correction_and_time_retirement(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        methods = "\n".join(extract_method(source, "function " + name + "(").replace("function ", "public function ", 1)
            for name in ["isPsychReceptorNote", "configurePsychSustainCorrection", "applyPsychNotePresentation", "applyPsychNoteClip", "updatePsychNoteLifetime"])
        fixture = r'''
class FlxG { public static var width:Float=1280; public static var height:Float=720; }
class FlxMath { public static function remapToRange(v:Float,a:Float,b:Float,c:Float,d:Float):Float return c+(v-a)/(b-a)*(d-c); }
class Conductor { public static var songPosition:Float=1000; }
class Receptor {
 public var alpha:Float=0.25; public var x:Float=12; public var y:Float=34; public var direction:Float=180;
 public var angle:Float=23; public var downScroll:Bool=true; public var sustainReduce:Bool=true;
 public function new() {}
}
class Strumline { public var members:Array<Receptor>=[new Receptor()]; public function new() {} }
class Note {
 public static var swagWidth:Float=112; public var copyX:Bool=true;
 public var copyAlpha:Bool=true; public var multAlpha:Float=0.6; public var alpha:Float=1;
 public function applyPsychReceptorAlpha(value:Float):Void if (copyAlpha) alpha=value*multAlpha;
 public var sourceTimingMode:Int=1; public var codenameInputLine:Dynamic=null;
 public var isSustainNote:Bool=false; public var height:Float=80; public var correctionOffset:Float=0;
 public var noteData:Int=0; public var strumTime:Float=900; public var mustPress:Bool=true;
 public var dontCountNote:Bool=false; public var ignoreNote:Bool=false; public var tooLate:Bool=false; public var wasGoodHit:Bool=false;
 public var auto:Bool=false; public var active:Bool=true; public var visible:Bool=true;
 public var alive:Bool=true; public var destroyed:Bool=false; public var x:Float=-9999; public var y:Float=9999;
 public var follows:Array<Dynamic>=[]; public var clips:Array<Dynamic>=[];
 public function new() {}
 public function applyPsychReceptorFollow(x:Float,y:Float,d:Float,a:Float,down:Bool,s:Float,pixel:Bool,zoom:Float):Void
  follows=[x,y,d,a,down,s,pixel,zoom];
 public function applyPsychReceptorClip(y:Float,down:Bool):Void clips=[y,down];
 public function isAutoPlayed():Bool return auto;
 public function kill():Void alive=false;
 public function destroy():Void destroyed=true;
}
class Notes {
 public var removed:Int=0; public function new() {}
 public function remove(note:Note,splice:Bool):Void removed++;
}
class PlayState {
 public var nightmareVisionScripts:Dynamic=null; public var pixelUI:Bool=false;
 public var downscroll:Bool=false; public var playbackRate:Float=2; public var daPixelZoom:Float=6;
 public var vnshNotes:Bool=false; public var noteSpeed:Float=0.45; public var drunkNotes:Bool=false; public var snakeNotes:Bool=false; public var songTime:Float=0; public var snekNumber:Float=0;
 public var effectiveScrollSpeed:Float=3; public var noteKillOffset:Float=350;
 public var endingSong:Bool=false; public var notes:Notes=new Notes(); public var misses:Int=0;
 public function new() {}
 public function noteMiss(lane:Int,mustPress:Bool,note:Note,ghost:Bool):Void misses++;
 __METHODS__
}
class Main {
 static function check(value:Bool,message:String):Void if (!value) throw message;
 static function main():Void {
  var game=new PlayState(); var note=new Note(); var line=new Strumline();
  game.applyPsychNotePresentation(note,line,3); game.applyPsychNoteClip(note,line);
  check(note.follows.join(',')=='12,34,180,23,true,1.5,false,6','live direction/downScroll/rate parameters');
  check(note.clips.join(',')=='34,true','clip did not use same receptor');
  check(note.alpha==0.15,'alpha did not follow before hit processing');
  note.copyAlpha=false; note.alpha=0.37; game.applyPsychNotePresentation(note,line,3);
  check(note.alpha==0.37,'copyAlpha=false lost ownership'); note.copyAlpha=true;
  note.isSustainNote=true; line.members[0].alpha=0; game.applyPsychNotePresentation(note,line,3);
  check(note.alpha==0,'accepted sustain sees stale receptor alpha'); note.isSustainNote=false;
  game.noteSpeed=0.9; game.drunkNotes=true;
  game.applyPsychNotePresentation(note,line,4); check(note.follows[5]==2,'resolved override/speed/drunk scaling');
  game.noteSpeed=0.45; game.drunkNotes=false; game.snakeNotes=true; note.copyX=false; note.x=77;
  game.applyPsychNotePresentation(note,line,3); check(note.x==77,'snake overwrote script-owned X');
  note.copyX=true; game.applyPsychNotePresentation(note,line,3); check(note.x==690,'snake geometry preference');
  game.snakeNotes=false;
  line.members[0].sustainReduce=false; note.clips=[];
  game.applyPsychNotePresentation(note,line,3); game.applyPsychNoteClip(note,line); check(note.clips.length==0,'disabled sustainReduce clipped');
  line.members[0]=null; game.applyPsychNotePresentation(note,line,3); game.applyPsychNoteClip(note,line);
  note.noteData=9; game.applyPsychNotePresentation(note,line,3); game.applyPsychNoteClip(note,line); note.noteData=0;
  var head=new Note(); note.isSustainNote=true;
  game.configurePsychSustainCorrection(note,head); check(note.correctionOffset==40,'upscroll head correction');
  game.downscroll=true; game.configurePsychSustainCorrection(note,head); check(note.correctionOffset==0,'nonpixel downscroll correction');
  game.pixelUI=true; game.configurePsychSustainCorrection(note,head); check(note.correctionOffset==40,'pixel downscroll correction');
  note.strumTime=650; check(!game.updatePsychNoteLifetime(note),'exact boundary retired');
  note.y=-100000; note.x=100000; check(!game.updatePsychNoteLifetime(note),'spatially offscreen note retired');
  Conductor.songPosition=1001; note.y=30;
  check(game.updatePsychNoteLifetime(note),'onscreen overdue note did not retire');
  check(game.misses==1 && !note.alive && note.destroyed && !note.active && !note.visible && game.notes.removed==1,'miss/remove lifecycle');
  note=new Note(); note.strumTime=0; note.isSustainNote=true; note.wasGoodHit=true;
  check(game.updatePsychNoteLifetime(note) && game.misses==1,'accepted sustain retirement issued miss');
  for (mode in [0,2]) {
   note=new Note(); note.sourceTimingMode=mode; note.strumTime=0;
   game.applyPsychNotePresentation(note,new Strumline(),3); game.configurePsychSustainCorrection(note,head);
   check(!game.updatePsychNoteLifetime(note) && note.follows.length==0,'native/NV route changed');
  }
  note=new Note(); note.codenameInputLine={}; note.strumTime=0;
  game.applyPsychNotePresentation(note,new Strumline(),3);
  check(!game.updatePsychNoteLifetime(note) && note.follows.length==0,'Codename route changed');
  note=new Note(); note.strumTime=0; game.nightmareVisionScripts={};
  check(!game.updatePsychNoteLifetime(note),'NV session route changed'); game.nightmareVisionScripts=null;
  for (skip in ['auto','ignore','ending','dontCount']) {
   note=new Note(); note.strumTime=0; note.auto=skip=='auto'; note.ignoreNote=skip=='ignore'; note.dontCountNote=skip=='dontCount'; game.endingSong=skip=='ending';
   check(game.updatePsychNoteLifetime(note) && game.misses==1,'source suppression gate changed');
  }
 }
}
'''.replace("__METHODS__", methods)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(fixture)
            result = subprocess.run([*HAXE_COMMAND, "-cp", folder, "-main", "Main", "--interp"], cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
