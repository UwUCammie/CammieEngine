"""Psych 1.0.4 short holds, local BPM generation and frame-dependent stretch."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND

ROOT=Path(__file__).resolve().parents[2]


class PsychSustainLayoutTest(unittest.TestCase):
    def test_source_rounding_times_and_stretch(self):
        fixture=r'''
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function near(a:Float,b:Float,message:String):Void check(Math.abs(a-b)<0.0000001,message);
 static function main():Void {
  var step=125.0;
  for (value in [0.0,-1.0,Math.NaN,Math.POSITIVE_INFINITY]) check(PsychSustainLayout.holdLength(value)==0,'invalid source duration');
  check(PsychSustainLayout.holdLength('125')==125,'serialized source hold');
  check(PsychSustainLayout.holdLength(1e-13)==1e-13,'authored short duration erased');
  check(PsychSustainLayout.segmentCount(0,step)==0,'zero hold');
  check(PsychSustainLayout.segmentCount(step*0.4999,step)==0,'below half-step');
  check(PsychSustainLayout.segmentCount(step*0.5,step)==1,'half-step boundary');
  check(PsychSustainLayout.segmentCount(step,step)==1,'one-step hold became native tap');
  check(PsychSustainLayout.segmentCount(step*1.49,step)==1,'rounded source count became ceil');
  check(PsychSustainLayout.segmentCount(step*1.5,step)==2,'second half-step boundary');
  check(PsychSustainLayout.segmentCount(250,0)==0,'invalid step');
  check(PsychSustainLayout.segmentTime(1000,0,step)==1000,'first source piece must share head time');
  check(PsychSustainLayout.segmentTime(1000,2,step)==1250,'segment spacing');
  var bpm=120.0;
  bpm=PsychSustainLayout.sectionBpm(bpm,false,180); check(bpm==120,'ignored section BPM became active');
  bpm=PsychSustainLayout.sectionBpm(bpm,true,180); var changedStep=PsychSustainLayout.stepCrochet(bpm,125);
  near(changedStep,15000/180,'changed section step');
  bpm=PsychSustainLayout.sectionBpm(bpm,false,null); check(bpm==180,'section BPM not carried forward');
  check(PsychSustainLayout.segmentCount(125,changedStep)==2,'local BPM count');
  near(PsychSustainLayout.segmentTime(2000,1,changedStep),2000+15000/180,'local BPM timestamp');
  near(PsychSustainLayout.bodyStretchRatio(125,2,false,6),2.625,'normal constructor ratio');
  near(PsychSustainLayout.bodyStretchRatio(125,2,true,6),3.12375,'pixel constructor ratio');
  near(PsychSustainLayout.bodyStretchRatio(125,2,true,12),1.561875,'pixel cap-dependent ratio');
  near(PsychSustainLayout.generationStretchRatio(83.3333333333333,125,2,false,44),1.0/3,'normal localstep/rate/frame ratio');
  near(PsychSustainLayout.generationStretchRatio(83.3333333333333,125,2,false,88),1.0/6,'alternate source body frame height');
  near(PsychSustainLayout.generationStretchRatio(83.3333333333333,125,2,true,44),1.0/3,'pixel localstep/rate ratio');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            shutil.copyfile(ROOT/'source/PsychSustainLayout.hx',Path(folder)/'PsychSustainLayout.hx')
            (Path(folder)/'Main.hx').write_text(fixture,encoding='utf-8')
            result=subprocess.run([*HAXE_COMMAND,'-cp',folder,'-main','Main','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_real_generation_expressions_keep_dialects_separate(self):
        from test_psych_note_follow import extract_method
        source=(ROOT/'source/PlayState.hx').read_text()
        def snippet(start,end):
            at=source.index(start)
            return source[at:source.index(end,at)]
        hold=snippet('var psychSustain = isPsychReceptorNote(swagNote);','swagNote.scrollFactor.set();')
        count=snippet('var sustainSteps:Int = sustainStepCount(susLength, Conductor.stepCrochet);','\n\n\t\t\t\tsusLength =')
        time_at=source.index('var segmentTime = nightmareVisionScripts != null')
        time=source[time_at:source.index(';',time_at)+1]
        section=snippet('psychSectionBpm = PsychSustainLayout.sectionBpm','if (nightmareVisionScripts != null && !nightmareVisionLegacyFieldCameras && section.changeBPM)')
        normalize=extract_method(source,'public static function normalizeSustainLength(')
        steps=extract_method(source,'public static function sustainStepCount(')
        fixture=r'''
class Conductor { public static var stepCrochet:Float=125; }
class Note { public var mode:Int; public var sustainLength:Float=0; public function new(mode:Int) this.mode=mode; }
class Main {
 public static inline var SUSTAIN_LENGTH_EPSILON:Float=0.000001;
 public static inline var SUSTAIN_STEP_EPSILON:Float=0.000001;
 static var psychSectionBpm:Float=120; static var psychSectionStep:Float=125;
 static function isPsychReceptorNote(note:Note):Bool return note.mode==1;
 __NORMALIZE__
 __STEPS__
 static function generate(mode:Int,length:Float,headTime:Float,changed:Bool,bpm:Float):Dynamic {
  var section={changeBPM:changed,bpm:bpm}; __SECTION__
  var swagNote=new Note(mode); var nightmareVisionScripts:Dynamic=mode>=2?{}:null; var nightmareVisionLegacyFieldCameras=mode==3; var songSpeed=2.;
  var songNotes:Array<Dynamic>=[headTime,0,length];
  __HOLD__
  var susLength=swagNote.sustainLength; var nightmareHoldStep=125.0;
  __COUNT__
  var times:Array<Float>=[]; var daStrumTime=headTime;
  for(susNote in 0...sustainSteps) { __TIME__ times.push(segmentTime); }
  return {length:swagNote.sustainLength,times:times};
 }
 static function check(value:Bool,message:String):Void if(!value)throw message;
 static function main():Void {
  var one=generate(1,125,1000,false,180); check(one.length==125 && one.times.length==1 && one.times[0]==1000,'source one-step hold');
  var changed=generate(1,125,2000,true,180); check(changed.times.length==2 && changed.times[0]==2000,'local BPM count/head timestamp');
  check(Math.abs(changed.times[1]-2083.3333333333333)<0.0001,'local BPM spacing');
  var carried=generate(1,125,3000,false,120); check(carried.times.length==2,'BPM not carried to subsequent section');
  var zero=generate(1,0,4000,false,120); check(zero.length==0 && zero.times.length==0,'zero source length');
  var short=generate(1,62.5,4000,true,120); check(short.length==62.5 && short.times.length==1,'half-step source hold');
  var tiny=generate(1,1e-13,4000,false,120); check(tiny.length==1e-13 && tiny.times.length==0,'tiny authored source hold metadata');
  var native=generate(0,125,5000,false,120); check(native.length==0 && native.times.length==0,'native sentinel changed');
  native=generate(0,156.25,5000,false,120); check(native.times.length==2 && native.times[0]==5125 && native.times[1]==5250,'native ceil/+step placement changed');
  var nv=generate(2,125,6000,false,120); check(nv.length==125 && nv.times.length==2 && nv.times[0]==6000 && nv.times[1]==6125,'NV rounded+one rule changed');
  var legacy=generate(3,125,6000,false,120); check(legacy.times.length==2 && legacy.times[0]==6062.5 && legacy.times[1]==6187.5,'historical NV first-tail speed offset');
 }
}
'''
        for key,value in {'NORMALIZE':normalize,'STEPS':steps,'SECTION':section,'HOLD':hold,'COUNT':count,'TIME':time}.items():
            fixture=fixture.replace('__'+key+'__',value)
        fixture='using StringTools;\n'+fixture
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            for name in ['PsychSustainLayout','NightmareVisionSustainLayout']:
                shutil.copyfile(ROOT/('source/'+name+'.hx'),Path(folder)/(name+'.hx'))
            (Path(folder)/'Main.hx').write_text(fixture,encoding='utf-8')
            result=subprocess.run([*HAXE_COMMAND,'-cp',folder,'-main','Main','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_generation_wiring_and_source_skin_finalization_order(self):
        source=(ROOT/'source/PlayState.hx').read_text()
        start=source.index('var psychSectionBpm = Conductor.bpm;')
        stop=source.index('if (OptionsHandler.options.emuOsuLifts',start)
        generation=source[start:stop]
        for fragment in (
            'PsychSustainLayout.sectionBpm(psychSectionBpm, section.changeBPM, section.bpm)',
            'var psychSustain = isPsychReceptorNote(swagNote);',
            'else if (psychSustain) swagNote.sustainLength = PsychSustainLayout.holdLength(songNotes[2]);',
            'else if (psychSustain) sustainSteps = PsychSustainLayout.segmentCount(susLength, psychSectionStep);',
            'if (nightmareVisionScripts != null || psychSustain || susLength > susNote)',
            ': psychSustain ? PsychSustainLayout.segmentTime(daStrumTime, susNote, psychSectionStep)',
            'sustainNote.parent = swagNote;', 'swagNote.tail.push(sustainNote);',
        ): self.assertIn(fragment,generation)
        skin=generation.index('configurePsychNoteSkin(sustainNote, psychSkinRoot);')
        finalized=generation.index('if (psychSustain) sustainNote.finalizePsychSustainSegment(oldNote, swagNote, psychSectionStep,')
        queued=generation.index('unspawnNotes.push(sustainNote);',finalized)
        self.assertLess(skin,finalized); self.assertLess(finalized,queued)
        self.assertIn('else swagNote.sustainLength = normalizeSustainLength(songNotes[2], Conductor.stepCrochet);',generation)
        self.assertIn('NightmareVisionSustainLayout.segmentCount(susLength, nightmareHoldStep)',generation)
        self.assertIn(': daStrumTime + Conductor.stepCrochet * (susNote + 1);',generation)
        donor=(ROOT.parent/'fnf_sources/FNF-PsychEngine/source/states/PlayState.hx').read_text()
        self.assertIn('final roundSus:Int = Math.round(swagNote.sustainLength / curStepCrochet);',donor)
        self.assertIn('new Note(spawnTime + (curStepCrochet * susNote)',donor)
        self.assertIn('oldNote.scale.y *= Note.SUSTAIN_SIZE / oldNote.frameHeight;',donor)


if __name__=='__main__': unittest.main()
