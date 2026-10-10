"""Compare source-constructed state clocks to the pinned Psych methods.
Stage callbacks and transitions remain separate acceptance gaps.
"""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import ROOT, HAXE_COMMAND
from test_source_gameplay_lifecycle import extract_method

class PsychMusicBeatStateTest(unittest.TestCase):
 def test_pinned_state_clock_and_native_isolation(self):
  donor=subprocess.check_output(['git','-C',str(ROOT.parent/'fnf_sources/FNF-PsychEngine'),'show','5c67ced49e5a98535298a6daa3f8f4ec79ac8399:source/backend/MusicBeatState.hx'],text=True)
  actual=(ROOT/'source/MusicBeatState.hx').read_text(encoding='utf-8')
  methods=['update','updateCurStep','updateBeat','updateSection','rollbackSection','getBeatsOnSection','stepHit','beatHit','sectionHit']
  def body(source):
   result=[]
   for name in methods:
    if name in ['updateSection','rollbackSection','getBeatsOnSection'] and 'class MusicBeatState extends FlxUIState' in source:
     start=source.index('function '+name+'(');end=source.index(';',start)+1;method=source[start:end]
    else: method=extract_method(source,'function '+name+'(')
    result.append(('override public ' if name=='update' else 'public ')+method)
   return '\n'.join(result)
  fields='public var curStep=0;public var curBeat=0;public var curDecStep=0.0;public var curDecBeat=0.0;public var curSection=0;public var stepsToDo=0;public var psychSourceTiming=true;public var maxStepCatchUp=32;public function new(){super();}'
  actual=body(actual).replace('timePassedOnState','MusicBeatState.timePassedOnState')
  donor=body(donor).replace('timePassedOnState','MusicBeatState.timePassedOnState')
  bpm=extract_method((ROOT/'source/Conductor.hx').read_text(encoding='utf-8'),'public static function getBPMFromSeconds(')
  files={
   'Host.hx':'import Conductor.BPMChangeEvent;class Host extends Base {'+fields+actual+'}',
   'Donor.hx':'class Donor extends Base {'+fields+donor+'public function stagesFunc(f:Dynamic->Void):Void {}}',
   'Base.hx':"class Base {public function new(){}public function update(e:Float):Void Main.log.push('children');}",
   'BaseStage.hx':'class BaseStage {public var curStep:Int;public var curBeat:Int;public var curDecStep:Float;public var curDecBeat:Float;public var curSection:Int;public function update(e:Float):Void{}public function stepHit():Void{}public function beatHit():Void{}public function sectionHit():Void{}}',
   'Conductor.hx':'typedef BPMChangeEvent={var stepTime:Int;var songTime:Float;var bpm:Float;@:optional var stepCrochet:Float;}class Conductor {public static var songPosition:Float;public static var bpm=120.0;public static var stepCrochet=125.0;public static var bpmChangeMap:Array<BPMChangeEvent>;'+bpm+'}',
   'MusicBeatState.hx':'class MusicBeatState {public static var timePassedOnState=0.0;}',
   'PlayState.hx':'class PlayState {public static var SONG:Dynamic;}',
   'FlxG.hx':'class FlxG {public static var save:Dynamic={data:{}};public static var fullscreen=false;public static var keys={justPressed:{ESCAPE:false},pressed:{SHIFT:false}};public static function resetGame():Void throw "unexpected reset";}',
   'TitleState.hx':'class TitleState {public static var initialized=true;}',
   'NightmareVisionPluginHost.hx':'class NightmareVisionPluginHost {public static function callActive(n:String):Void throw "source state leaked host plugin";}',
   'PlayerSettings.hx':"class PlayerSettings {public static var player1={controls:'native'};}",
   'Controls.hx':"class Controls {public static var instance:Dynamic='source';}",
   'PsychControlsCompat.hx':'typedef PsychControlsCompat=Controls;',
   'ClientPrefs.hx':'class ClientPrefs {public static var data:Dynamic={noteOffset:0.0};}',
   'PsychClientPrefsCompat.hx':'typedef PsychClientPrefsCompat=ClientPrefs;',
   'Main.hx':r"""class RecordingHost extends Host {override public function stepHit():Void {Main.log.push('step:'+curStep);super.stepHit();}override public function beatHit():Void Main.log.push('beat:'+curBeat);override public function sectionHit():Void Main.log.push('section:'+curSection);}
class RecordingDonor extends Donor {override public function stepHit():Void {Main.log.push('step:'+curStep);super.stepHit();}override public function beatHit():Void Main.log.push('beat:'+curBeat);override public function sectionHit():Void Main.log.push('section:'+curSection);}
class Main {public static var log:Array<String>;static function run(source:Bool,offset:Float,chart:Int):String {log=[];MusicBeatState.timePassedOnState=0;ClientPrefs.data.noteOffset=offset;Conductor.bpmChangeMap=[{stepTime:8,songTime:1000.,bpm:60.,stepCrochet:250.},{stepTime:16,songTime:3000.,bpm:240.,stepCrochet:62.5}];PlayState.SONG=chart==0?null:{notes:[{sectionBeats:1.5},null,{sectionBeats:null},{sectionBeats:3.}]};var state:Dynamic=source?new RecordingDonor():new RecordingHost();var i=0;for(time in [-125.,0.,124.5,999.,1000.,1001.,2000.,3500.,100.,-10.,5000.,5000.]){FlxG.save.data=(i%3==0)?null:{};FlxG.fullscreen=i++%2==0;Conductor.songPosition=time;state.update(.125);log.push([state.curStep,state.curBeat,state.curDecStep,state.curDecBeat,state.curSection,MusicBeatState.timePassedOnState,FlxG.save.data==null?null:FlxG.save.data.fullscreen].join(','));}return log.join('|');}static function main(){var count=0;for(offset in [-150.,0.,75.])for(chart in 0...2){var expected=run(true,offset,chart),actual=run(false,offset,chart);if(expected!=actual)throw expected+' != '+actual;count++;}trace('psych-state-source:'+count);}}
"""
  }
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=Path(folder)
   for name,data in files.items(): (work/name).write_text(data,encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'--run','Main'],capture_output=True,text=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('psych-state-source:6',result.stdout)
