"""Pinned mutable queue consumption, reentry and registry lifecycle."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from test_source_event_preparation import extract_method
from tools.haxe_flixel_math_stubs import write_flixel_point_stub
ROOT=Path(__file__).resolve().parents[2]
MAIN=r'''class Conductor {public static var songPosition:Float=20;}
class Model {
 public var eventNotes:Array<Dynamic>=[{strumTime:0.,event:'A',value1:null,value2:'a'},{strumTime:10.,event:'B',value1:'b',value2:null},{strumTime:30.,event:'Future',value1:'',value2:''}];
 public var log:Array<String>=[];public var once=false;public var mode:Int;public var native:Bool;public var retained:Array<Dynamic>;
 public function new(mode:Int,native:Bool){this.mode=mode;this.native=native;retained=eventNotes;}
 function triggerEventNote(name:String,v1:String,v2:String):Void {
  log.push(name+':'+v1+':'+v2+':'+eventNotes.length);
  if(once)return;once=true;
  switch(mode){
   case 1:eventNotes=[{strumTime:0.,event:'replacement-head',value1:'',value2:''},{strumTime:0.,event:'replacement-tail',value1:'',value2:''}];
   case 2:eventNotes.push({strumTime:0.,event:'appended',value1:'',value2:''});
   case 3:eventNotes.shift();
   case 4:eventNotes.unshift({strumTime:0.,event:'inserted',value1:'',value2:''});
   case 5:eventNotes=[];
   case 6:throw 'callback failure';
   case 7:run();
   case 8:Conductor.songPosition=35.;
   case 9:eventNotes.reverse();
   case 10:eventNotes[1].strumTime=Math.NaN;
   case 11:Conductor.songPosition=Math.NaN;
  }
 }
 public function run(){if(native)NightmareVisionLegacyEventQueue.drain(function()return eventNotes,function()return Conductor.songPosition,function(e)triggerEventNote(e.name,e.v1,e.v2));else checkEventNote();}
 __SOURCE__
}
class Main {
 static function names(a:Array<Dynamic>):String return [for(e in a)e.event].join(',');
 static function main(){
  for(mode in 0...12){
   Conductor.songPosition=20.;var expected=new Model(mode,false);var failed=false;try expected.run()catch(e:Dynamic)failed=true;
   Conductor.songPosition=20.;var actual=new Model(mode,true);var actualFailed=false;try actual.run()catch(e:Dynamic)actualFailed=true;
   if(failed!=actualFailed||expected.log.join('|')!=actual.log.join('|')||names(expected.eventNotes)!=names(actual.eventNotes)||names(expected.retained)!=names(actual.retained))throw 'queue mismatch '+mode+' '+expected.log.join('|')+' != '+actual.log.join('|');
  }
  var row:Dynamic={time:10.,name:'view',v1:null,v2:null};var view=new SourceEventNote(row);var queue:Array<Dynamic>=[view];var log=[];
  NightmareVisionLegacyEventQueue.drain(function()return queue,function()return 10.,function(e){if(queue[0]!=view||e.v1!=''||e.v2!='')throw 'identity/null ABI';log.push(e.name);},null,true);
  if(log.length!=0||queue.length!=1)throw 'exclusive seek bound';
  NightmareVisionLegacyEventQueue.drain(function()return queue,function()return 10.,function(e){if(queue[0]!=view)throw 'callback observes original';log.push(e.name);});
  if(log.join(',')!='view'||queue.length!=0)throw 'view drain';
  trace('12 pinned queue mutations and native views verified');
 }
}'''
BINDINGS=r'''class Host {public function new(){}}
class Main {
 static function main(){
  var host=new Host();var registry=new NightmareVisionLegacyScriptRegistry();
  var i=new NightmareVisionScriptInterp(host);i.variables.set('game',host);i.variables.set('PlayState',Host);i.variables.set('Reflect',i.sourceClassScope().reflectFacade());NightmareVisionLegacyRegistryBindings.install(i,host,Host,registry);i.variables.set('replacementMap',new Map<String,Bool>());i.variables.set('retainedMap',null);
  i.execute(new NightmareVisionScriptParser().parseString('var saved=eventNotes;if(saved!=game.eventNotes||saved!=PlayState.eventNotes||saved!=Reflect.getProperty(game,"eventNotes"))throw "queue aliases";eventNotes=[{strumTime:1,event:"E",value1:null,value2:null}];if(eventNotes==saved||saved.length!=0)throw "queue replacement";Reflect.setProperty(game,"eventPushedMap",replacementMap);eventPushedMap.set("before",true);retainedMap=eventPushedMap;'));
  var retained=registry.eventPushedMap;registry.finishEventDiscovery();if(retained.iterator().hasNext()||registry.eventPushedMap!=null)throw 'discovery cleanup';
  i.execute(new NightmareVisionScriptParser().parseString('if(eventPushedMap!=null||game.eventPushedMap!=null||retainedMap.exists("before"))throw "cleanup aliases";'));
  var names:Map<String,Bool>=[];var loaded=[];var scripts:Map<String,Dynamic>=['A'=>{scriptType:'hscript'}];
  NightmareVisionLegacyEventPreparation.prepare(function(visit)visit({time:0.,name:'A',v1:'',v2:'',order:0}),function()return 0.,function()return scripts,
   function(s,n,a):Dynamic {if(n=='firstPush')names=['Injected'=>true];return 0;},function(n,a)return 0.,function(n)loaded.push(n),function(r,e){},function(e)return false,function()return names);
  if(loaded.join(',')!='Injected')throw 'callback replacement of discovery map';
  i.release();trace('live queue/map bindings verified');
 }
}'''
class HistoricalEventQueueTest(unittest.TestCase):
 def run_fixture(self,text):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder);write_flixel_point_stub(work);(work/'Main.hx').write_text(text)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
 def test_queue_matches_pinned_mutation_and_reentry(self):
  donor=ROOT.parent/'fnf_sources/NightmareVision'
  if not donor.is_dir():self.skipTest('pinned source unavailable')
  source=subprocess.check_output(['git','show','7f96eb3b5a60352413229bf134bd348b79ad5fe6:source/meta/states/PlayState.hx'],cwd=donor,text=True)
  self.run_fixture(MAIN.replace('__SOURCE__',extract_method(source,'function checkEventNote(')))
 def test_writable_bindings_and_discovery_lifetime(self):self.run_fixture(BINDINGS)
if __name__=='__main__':unittest.main()
