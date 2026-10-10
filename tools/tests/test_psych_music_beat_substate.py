"""Execute the pinned Psych base substate beside the shared native adapter."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import ROOT,HAXE_COMMAND
from test_source_gameplay_lifecycle import extract_method
class PsychMusicBeatSubstateTest(unittest.TestCase):
 def test_pinned_clock_sections_offset_and_controls(self):
  donor=subprocess.check_output(['git','-C',str(ROOT.parent/'fnf_sources/FNF-PsychEngine'),'show','5c67ced49e5a98535298a6daa3f8f4ec79ac8399:source/backend/MusicBeatSubstate.hx'],text=True).replace('package backend;','package;').replace('class MusicBeatSubstate','class Donor')
  donor=donor.replace('private var','public var')
  method=extract_method((ROOT/'source/Conductor.hx').read_text(encoding='utf-8'),'public static function getBPMFromSeconds(')
  map_method=extract_method((ROOT/'source/Conductor.hx').read_text(encoding='utf-8'),'public static function mapBPMChanges(')
  conductor_source=subprocess.check_output(['git','-C',str(ROOT.parent/'fnf_sources/FNF-PsychEngine'),'show','5c67ced49e5a98535298a6daa3f8f4ec79ac8399:source/backend/Conductor.hx'],text=True)
  bpm_oracle=extract_method(conductor_source,'public static function getBPMFromSeconds(').replace('getBPMFromSeconds','donorBPM')
  files={
   'Donor.hx':donor,
   'flixel/FlxSubState.hx':"package flixel;class FlxSubState {public var persistentUpdate:Bool=false;public function new(){}public function update(e:Float):Void Main.log.push('children');}",
   'MusicBeatSubstate.hx':"class MusicBeatSubstate extends flixel.FlxSubState {public var curStep:Int=0;public var curBeat:Int=0;public var controls(get,never):Dynamic;function get_controls():Dynamic return 'native';public function new(){super();}function updateCurStep():Void {}function updateSubstateChildren(e:Float):Void super.update(e);public function stepHit():Void {if(curStep%4==0)beatHit();}public function beatHit():Void {}}",
   'MusicBeatState.hx':'class MusicBeatState {public static var timePassedOnState:Float=0;}',
   'Controls.hx':"class Controls {public static var instance:Dynamic='source';}",
   'PsychControlsCompat.hx':'typedef PsychControlsCompat=Controls;',
   'ClientPrefs.hx':'class ClientPrefs {public static var data:Dynamic={noteOffset:0.0};}',
   'PsychClientPrefsCompat.hx':'typedef PsychClientPrefsCompat=ClientPrefs;',
   'PlayState.hx':'class PlayState {public static var SONG:Dynamic;}',
   'Conductor.hx':'typedef SwagSong=Dynamic;typedef BPMChangeEvent={var stepTime:Int;var songTime:Float;var bpm:Float;var stepCrochet:Float;}class Conductor {public static var songPosition:Float;public static var bpm=120.0;public static var stepCrochet=125.0;public static var bpmChangeMap:Array<BPMChangeEvent>;'+method+bpm_oracle+map_method+'}',
   'Main.hx':r"""class RecordingDonor extends Donor {public function new(){super();}override public function stepHit():Void {Main.log.push('step:'+curStep);super.stepHit();}override public function beatHit():Void Main.log.push('beat:'+curBeat);override public function sectionHit():Void Main.log.push('section:'+curSection);}
class RecordingHost extends PsychMusicBeatSubstate {public function new(){super();}override public function stepHit():Void {Main.log.push('step:'+curStep);super.stepHit();}override public function beatHit():Void Main.log.push('beat:'+curBeat);override public function sectionHit():Void Main.log.push('section:'+curSection);}
class Main {public static var log:Array<String>;static function run(donor:Bool,offset:Float,persistent:Bool,chart:Int):String {log=[];MusicBeatState.timePassedOnState=0;ClientPrefs.data.noteOffset=offset;Conductor.bpmChangeMap=[{stepTime:8,songTime:1000.,bpm:60.,stepCrochet:250.},{stepTime:16,songTime:3000.,bpm:240.,stepCrochet:62.5}];PlayState.SONG=chart==0?null:{notes:[{sectionBeats:1.5},null,{sectionBeats:null},{sectionBeats:3.}]};var target:Dynamic=donor?new RecordingDonor():new RecordingHost();target.persistentUpdate=persistent;for(time in [-125.,0.,124.5,999.,1000.,1001.,2000.,3500.,100.,-10.,5000.,5000.]){Conductor.songPosition=time;if(haxe.Json.stringify(Conductor.getBPMFromSeconds(time))!=haxe.Json.stringify(Conductor.donorBPM(time)))throw "source BPM selection";target.update(.125);if(Math.abs(PsychBeatClock.getDecimalStep()-target.curDecStep)>0.000001)throw 'shared gameplay stage fraction';log.push([target.curStep,target.curBeat,target.curDecStep,target.curDecBeat,target.curSection,MusicBeatState.timePassedOnState,Reflect.getProperty(target,'controls')].join(','));}return log.join('|');}static function main(){Conductor.mapBPMChanges({bpm:120.0,notes:[{lengthInSteps:8,changeBPM:false,bpm:120.0},{lengthInSteps:8,changeBPM:true,bpm:60.0}]});var segment=Conductor.getBPMFromSeconds(1000);if(segment!=Conductor.bpmChangeMap[0]||segment.stepCrochet!=250||segment.stepTime!=8)throw 'mapped source step duration and identity';var count=0;for(offset in [-150.,0.,75.])for(persistent in [false,true])for(chart in 0...2){var expected=run(true,offset,persistent,chart),actual=run(false,offset,persistent,chart);if(expected!=actual)throw expected+' != '+actual;count++;}trace('psych-substate-source:'+count);}}
"""
  }
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=Path(folder)
   for name,data in files.items():
    p=work/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data,encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'--run','Main'],capture_output=True,text=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('psych-substate-source:12',result.stdout)
