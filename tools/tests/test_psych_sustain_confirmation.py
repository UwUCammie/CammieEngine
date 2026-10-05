"""Psych confirms use the source auto timer and manual release without changing holds."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from test_psych_note_follow import extract_method

ROOT=Path(__file__).resolve().parents[2]


class PsychSustainConfirmationTest(unittest.TestCase):
    def test_source_timer_manual_release_and_native_nv_exclusions(self):
        play=(ROOT/'source/PlayState.hx').read_text()
        strum=(ROOT/'source/Strumline.hx').read_text()
        sustain=extract_method(play,'function sustain2(').replace('Strumline.StrumNote','Receptor').replace('function sustain2','public function sustain2')
        predicate=extract_method(play,'function isPsychReceptorNote(')
        release=extract_method(play,'function setSourceInputReceptor(').replace('Strumline.StrumNote','Receptor').replace('function setSourceInputReceptor','public function setSourceInputReceptor')
        update=extract_method(strum[strum.index('class StrumNote'):],'public function update(')
        normalize=extract_method(play,'public static function normalizeSustainLength(')
        fixture=r'''
using StringTools;
class Conductor { public static var stepCrochet:Float=125; public static var crochet:Float=500; public static var bpm:Float=120; }
class AnimFrame { public var name:String='confirm'; public var finished:Bool=true; public function new() {} }
class Anim { public var curAnim:AnimFrame=new AnimFrame(); public function new() {} }
class Base { public function new() {} public function update(elapsed:Float):Void {} }
class Receptor extends Base {
 public var ID:Int=0; public var psychSourceTiming:Bool=false; public var nightmareVisionOffsets:Dynamic=null;
 public var resetAnim:Float=0; public var coyoteTime:Float=0; public var holding:Bool=false; public var usesVSliceGeometry:Bool=false;
 public var exists:Bool=true; public var confirmationGeneration:Int=1; public var animation:Anim=new Anim();
 public function playAnim(name:String,force:Bool=false):Void animation.curAnim.name=name;
 public function alignVSliceFrame():Void {} public function markReceptorVisual():Void {}
 override __UPDATE__
}
class Line {
 public var receptor:Receptor; public function new(receptor:Receptor) this.receptor=receptor;
 public function forEachReceptor(callback:Receptor->Void):Void callback(receptor);
}
class Note {
 public var sourceTimingMode:Int=1; public var codenameInputLine:Dynamic=null; public var nightmareVisionTypeRuntime:Dynamic=null;
 public var isSustainNote:Bool=false; public var nightmareVisionSustainEnd:Bool=false; public var nightmareVisionTailState:Dynamic=null;
 public var sustainLength:Float=125; public var prevNote:Note=null; public var strumTime:Float=1000; public var auto:Bool=false;
 public function new() {} public function isAutoPlayed():Bool return auto;
}
class FlxTimer {
 public static var starts:Int=0; public function new() {}
 public function start(delay:Float,callback:FlxTimer->Void):FlxTimer { starts++; return this; }
 public function reset(delay:Float):Void {}
}
class Main {
 public static inline var SUSTAIN_LENGTH_EPSILON:Float=0.000001;
 public static inline var SUSTAIN_STEP_EPSILON:Float=0.000001;
 public var nightmareVisionScripts:Dynamic=null; public var playbackRate:Float=1; public var strumsBlocked:Array<Bool>=[];
 public var line:Line; public function new(spr:Receptor) line=new Line(spr);
 public function nightmareVisionFieldForNote(note:Note):Dynamic return {autoPlayed:true,holdDropLeniency:0.07};
 public function getNightmareVisionField(id:Int):Dynamic return null;
 public function getInputStrumline(dummy:Dynamic,player:Bool):Line return line;
 __PREDICATE__
 __NORMALIZE__
 __SUSTAIN__
 __RELEASE__
 static function check(ok:Bool,message:String):Void if(!ok)throw message;
 static function main():Void {
  var receptor=new Receptor(); var game=new Main(receptor); var note=new Note(); note.auto=true;
  game.sustain2(0,receptor,note);
  check(note.sustainLength==125 && receptor.resetAnim==0.15625 && receptor.psychSourceTiming && FlxTimer.starts==0,'source auto duration/length/host timer');
  receptor.update(0.1); check(receptor.animation.curAnim.name=='confirm' && receptor.resetAnim>0,'source timer ended too early');
  receptor.update(0.06); check(receptor.animation.curAnim.name=='static' && receptor.resetAnim==0,'source timer did not retire confirm');
  Conductor.stepCrochet=100; game.playbackRate=2; game.sustain2(0,receptor,note);
  check(receptor.resetAnim==0.0625,'live BPM/playback rate timer');
  note.auto=false; note.isSustainNote=true; note.sustainLength=50; receptor.playAnim('confirm');
  game.sustain2(0,receptor,note); receptor.update(1);
  check(note.sustainLength==50 && receptor.resetAnim==0 && receptor.animation.curAnim.name=='confirm','manual short hold/timer lifecycle');
  game.setSourceInputReceptor(0,true,true);
  check(receptor.animation.curAnim.name=='static' && receptor.resetAnim==0,'manual release did not reset');
  Conductor.stepCrochet=125; note=new Note(); note.sourceTimingMode=0; receptor=new Receptor(); game=new Main(receptor);
  game.sustain2(0,receptor,note);
  check(note.sustainLength==0 && !receptor.psychSourceTiming && FlxTimer.starts==1,'native sentinel/timer changed');
  note=new Note(); note.sourceTimingMode=2; note.nightmareVisionTypeRuntime={}; note.isSustainNote=true;
  game.sustain2(0,receptor,note);
  check(note.sustainLength==125 && receptor.resetAnim==0.3 && receptor.coyoteTime==0.07 && !receptor.psychSourceTiming && FlxTimer.starts==1,'NV confirm lifecycle changed');
 }
}
'''
        for key,value in {'UPDATE':update,'PREDICATE':predicate,'NORMALIZE':normalize,'SUSTAIN':sustain,'RELEASE':release}.items():
            fixture=fixture.replace('__'+key+'__',value)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            (Path(folder)/'Main.hx').write_text(fixture,encoding='utf-8')
            result=subprocess.run([*HAXE_COMMAND,'-cp',folder,'-main','Main','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        donor=(ROOT.parent/'fnf_sources/FNF-PsychEngine/source/states/PlayState.hx').read_text()
        self.assertIn('Conductor.stepCrochet * 1.25 / 1000 / playbackRate',donor)


if __name__=='__main__': unittest.main()
