"""Execute pinned stage iteration and timing publication against shared services."""
import subprocess,tempfile,unittest
from pathlib import Path
from haxe_test_support import ROOT,HAXE_COMMAND
from test_source_gameplay_lifecycle import extract_method
class SourceStageCallbacksTest(unittest.TestCase):
 def test_source_iteration_mutation_and_timing(self):
  donor=subprocess.check_output(['git','-C',str(ROOT.parent/'fnf_sources/FNF-PsychEngine'),'show','5c67ced49e5a98535298a6daa3f8f4ec79ac8399:source/backend/MusicBeatState.hx'],text=True)
  methods='\n'.join('public '+extract_method(donor,'function '+name+'(') for name in ['stepHit','beatHit','sectionHit','stagesFunc'])
  fields='public var stages:Array<BaseStage>=[];public var curStep=8;public var curDecStep=8.5;public var curBeat=2;public var curDecBeat=2.125;public var curSection=3;public function new(){}'
  files={
   'Donor.hx':'class Donor {'+fields+methods+'}',
   'Host.hx':"class Host {"+fields+"public function stagesFunc(f:BaseStage->Void):Void SourceStageCallbacks.each(cast stages,Reflect.getProperty,f);function dispatch(n:String):Void stagesFunc(function(s){SourceStageCallbacks.publish(this,s,n,Reflect.getProperty,Reflect.setProperty);Reflect.callMethod(s,Reflect.getProperty(s,n),[]);});public function stepHit():Void {dispatch('stepHit');if(curStep%4==0)beatHit();}public function beatHit():Void dispatch('beatHit');public function sectionHit():Void dispatch('sectionHit');}",
   'BaseStage.hx':"class BaseStage {public var exists=true;public var active=true;public var curStep=0;public var curDecStep=0.0;public var curBeat=0;public var curDecBeat=0.0;public var curSection=0;public var name:String;public var callback:String->Void;public function new(n:String){name=n;}public function stepHit():Void {Main.record(this,'step');callback('step');}public function beatHit():Void {Main.record(this,'beat');callback('beat');}public function sectionHit():Void {Main.record(this,'section');callback('section');}}",
   'Main.hx':r"""class Main {public static var log:Array<String>;public static function record(s:BaseStage,n:String):Void {var values:Array<Dynamic>=[s.name,n,s.curStep,s.curDecStep,s.curBeat,s.curDecBeat,s.curSection];log.push(values.join(':'));};static function run(source:Bool,mode:Int,mask:Int):String {log=[];var state:Dynamic=source?new Donor():new Host();var a=new BaseStage('a'),b=new BaseStage('b'),c=new BaseStage('c');a.active=(mask&1)==0;b.exists=(mask&2)==0;c.active=(mask&4)==0;state.stages=[a,null,b];a.callback=function(n){if(n!='step')return;switch(mode){case 0:state.stages.push(c);case 1:state.stages.remove(b);case 2:state.stages=[c];case 3:b.active=false;case 4:state.curStep=12;state.curDecStep=12.75;case 5:b.curBeat=99;default:}};b.callback=function(n){if(n=='step'&&mode==6)state.curSection=7;};c.callback=function(n){};state.stepHit();state.sectionHit();state.curStep=9;state.stepHit();return log.join('|');}static function main(){var count=0;for(mode in 0...8)for(mask in 0...8){var expected=run(true,mode,mask),actual=run(false,mode,mask);if(expected!=actual)throw mode+'/'+mask+': '+expected+' != '+actual;count++;}trace('source-stage-callbacks:'+count);}}"""
  }
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=Path(folder)
   for name,content in files.items(): (work/name).write_text(content,encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'--run','Main'],capture_output=True,text=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('source-stage-callbacks:64',result.stdout)
