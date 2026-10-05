"""Execute source sustain finalization after source atlas dimensions become available."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_nv_multifield_routes import method

ROOT = Path(__file__).resolve().parents[2]


class PsychSustainGeometryTest(unittest.TestCase):
    def test_source_finalizer_uses_final_dimensions_once_and_preserves_other_routes(self):
        note = (ROOT / 'source/Note.hx').read_text()
        finalizer = method(note, '@:keep public function finalizePsychSustainSegment(')
        ctor = method(note, 'public function new(strumTime:Float')
        branch = ctor[ctor.index("// Source skin installation happens after construction."):]
        self.assertIn('scale.y = 1;', branch)
        self.assertIn('} else {', branch)
        self.assertIn('prevNote.scale.y *= Conductor.stepCrochet / 100 * 1.5', branch)
        fixture = r'''
class Point {public var x:Float=1;public var y:Float=1;public function new() {}}
class Animation {
 public var curAnim:Dynamic={name:'holdend'};var note:Note;
 public function new(note:Note)this.note=note;
 public function play(name:String):Void {
  curAnim={name:name};note.frameHeight=name=='hold'?note.bodyFrameHeight:note.endFrameHeight;
 }
}
class PlayState {public static var daPixelZoom:Float=6;}
class Note {
 public var sourceTimingMode:Int=1;public var codenameInputLine:Dynamic=null;
 public var isSustainNote:Bool=true;public var psychSustainLayoutInitialized:Bool=false;
 public var psychSustainStartWidth:Float=100;public var correctionOffset:Float=0;
 public var offsetX:Float=7;public var width:Float=40;public var height:Float=6;
 public var frameHeight:Float=6;public var bodyFrameHeight:Float=20;public var endFrameHeight:Float=6;
 public var scale:Point=new Point();public var animation:Animation;
 public var hitboxes:Int=0;
 public function new()animation=new Animation(this);
 public function updateHitbox():Void {height=frameHeight*scale.y;hitboxes++;}
 __FINALIZER__
}
class Main {
 static function check(ok:Bool,label:String):Void if(!ok)throw label;
 static function near(a:Float,b:Float,label:String):Void check(Math.abs(a-b)<0.00001,label+':'+a+'!='+b);
 static function main() {
  var head=new Note();head.isSustainNote=false;head.height=100;
  var first=new Note();first.finalizePsychSustainSegment(head,head,100,150,2,1.25,false,false);
  near(first.offsetX,37,'source centering uses installed start/end width');
  near(first.correctionOffset,50,'upscroll head correction');near(first.scale.y,1,'normal end keeps donor unit scale');
  var next=new Note();next.finalizePsychSustainSegment(first,head,100,150,2,1.25,false,true);
  near(first.scale.y,3.696,'donor1.05 stretch and44/final body frame height, local step and playback rate');
  near(first.height,73.92,'body hitbox follows donor stretch');
  check(first.animation.curAnim.name=='hold'&&next.animation.curAnim.name=='holdend','previous becomes body; final stays end');
  near(next.correctionOffset,0,'normal downscroll clears correction');
  var scale=first.scale.y;var offset=next.offsetX;var hits=first.hitboxes;
  next.finalizePsychSustainSegment(first,head,100,150,2,1.25,false,true);
  check(first.scale.y==scale&&next.offsetX==offset&&first.hitboxes==hits,'finalizer cannot accumulate on repeated calls');
  var pfirst=new Note();pfirst.finalizePsychSustainSegment(head,head,100,150,2,1.25,true,true);
  near(pfirst.scale.y,6,'pixel end gets zoom once');near(pfirst.offsetX,67,'pixel source30px offset');
  var pnext=new Note();pnext.finalizePsychSustainSegment(pfirst,head,100,150,2,1.25,true,true);
  near(pfirst.scale.y,11.9952,'pixel1.19*6/current unzoomed end height with local/rate generation adjustment');
  near(pnext.scale.y,6,'last pixel end stays zoomed');near(pnext.correctionOffset,50,'pixel downscroll retains correction');
  for(mode in [0,2]) {
   var untouched=new Note();untouched.sourceTimingMode=mode;
   untouched.finalizePsychSustainSegment(first,head,100,150,2,1.25,true,true);
   check(untouched.offsetX==7&&untouched.scale.y==1&&!untouched.psychSustainLayoutInitialized,'native/NV route untouched');
  }
  var codename=new Note();codename.codenameInputLine={};
  codename.finalizePsychSustainSegment(first,head,100,150,2,1.25,true,true);
  check(codename.offsetX==7&&codename.scale.y==1&&!codename.psychSustainLayoutInitialized,'Codename route untouched');
  trace('PSYCH_SUSTAIN_GEOMETRY_OK');
 }
}
'''.replace('__FINALIZER__', finalizer)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = FixturePath(directory)
            (work / 'Main.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(work),
                                     '-main', 'Main', '--interp'], capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PSYCH_SUSTAIN_GEOMETRY_OK', result.stdout)


if __name__ == '__main__':
    unittest.main()
