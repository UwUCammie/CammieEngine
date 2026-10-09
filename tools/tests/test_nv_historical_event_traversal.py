"""Pinned live source traversal and historical public event APIs."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from test_source_event_preparation import extract_method
from tools.haxe_flixel_math_stubs import write_flixel_point_stub
ROOT=Path(__file__).resolve().parents[2]
MODEL=r'''typedef EventNote={strumTime:Float,event:String,value1:String,value2:String};
class ClientPrefs {public static var noteOffset:Float=0;}
class Model {
 public var SONG:{events:Array<Dynamic>};public var companion:Array<Dynamic>;public var mode:Int;public var calls=0;public var log:Array<String>=[];
 public function new(mode:Int,sidecar:Bool){this.mode=mode;SONG={events:[[100.,[['E','a',null],['E','b',null]]],[200.,[['E','c',null]]]]};companion=sidecar?[[10.,[['E','side',null]]]]:null;}
 public function shouldPush(event:Dynamic):Bool {
  var value:String=Reflect.getProperty(event,'value1');var time:Float=Reflect.getProperty(event,'strumTime');log.push(value+':'+time);calls++;
  if(calls==1){
   switch(mode){
    case 0:SONG.events[0][1][1][1]='edited';
    case 1:SONG.events.push(([300.,[['E','appended',null]]]:Array<Dynamic>));
    case 2:SONG.events[0][1].push(['E','inner-appended',null]);
    case 3:SONG.events[0][0]=444.;
    case 4:SONG.events[0][1]=[['E','replaced-a',null],['E','replaced-b',null]];
    case 5:SONG.events=[ [500.,[['E','new-array',null]]] ];
    case 6:SONG={events:[[600.,[['E','new-song',null]]]]};
    case 7:SONG.events.splice(0,1);
    case 8:ClientPrefs.noteOffset=25.;
    case 9:SONG.events.reverse();
    case 10:if(companion!=null)companion.push([20.,[['E','new-side',null]]]);
    case 11:Reflect.setProperty(event,'event','renamed');Reflect.setProperty(event,'value2','admission-edit');
   }
  }
  return value!='b';
 }
 public function source():Array<EventNote>{__SOURCE__}
 public function actual():Array<SourceEventNote>{
  var scripts:Map<String,Dynamic>=['E'=>{scriptType:'hscript'}];
  var song=SONG;
  var result=NightmareVisionLegacyEventPreparation.collect(function(visit){var order=0;if(companion!=null)order=SongEvents.visitSourceGroups(companion,visit,order);SongEvents.visitSourceGroups(song.events,visit,order);},
   function()return ClientPrefs.noteOffset,function()return scripts,function(s,n,args):Dynamic return shouldPush(args[0]));
  return [for(entry in result)entry.event];
 }
}
class Main {
 static function main(){
 for(mode in 0...12)for(sidecar in [false,true]){
  ClientPrefs.noteOffset=0;var expected=new Model(mode,sidecar);var a=expected.source();
  ClientPrefs.noteOffset=0;var actual=new Model(mode,sidecar);var b=actual.actual();
  if(expected.log.join('|')!=actual.log.join('|')||a.length!=b.length)throw 'traversal '+mode+':'+sidecar+' '+expected.log.join('|')+' != '+actual.log.join('|');
  for(i in 0...a.length)if(a[i].strumTime!=b[i].strumTime||a[i].event!=b[i].event||a[i].value1!=b[i].value1||a[i].value2!=b[i].value2)throw 'record mismatch';
 }
 trace('24 pinned live traversal scenarios verified');
 }
}'''
API=r'''class Host {
 public var registry=new NightmareVisionLegacyScriptRegistry();public var groups:Array<Dynamic>=[[100.,[['E','keep',null],['E','reject',null]]]];
 public function new(){}
 function legacyScriptRegistry():NightmareVisionLegacyScriptRegistry return registry;
 function sourceChartNoteOffset():Float return 5.;
 function visitHistoricalNightmareVisionEvents(visit:Dynamic->Void):Void {SongEvents.visitSourceGroups(groups,visit);}
 __API__
 public function bind(i:NightmareVisionScriptInterp){i.variables.set('game',this);i.variables.set('PlayState',Host);i.variables.set('Reflect',i.sourceClassScope().reflectFacade());NightmareVisionLegacyEventBindings.install(i,this,Host,historicalNightmareVisionEventApi());}
}
@:access(Host) class Main {
 static function main(){
 var owner=new Host();var other=new Host();
 var script=NightmareVisionScriptModule.fromSource('E','var saved=null;function shouldPush(e){saved=e;e.value2="edited";return e.value1!="reject";}function firstPush(e){e.value1="first";}function getOffset(e){e.strumTime=321;return 12.5;}',owner,null,
  function(i){var m:NightmareVisionScriptModule=cast i.variables.get('script');m.historicalCalls=true;owner.bind(i);},function(n,c,e)throw e);
 owner.registry.eventScripts.set('E',script);
 var i=new NightmareVisionScriptInterp(owner);owner.bind(i);var j=new NightmareVisionScriptInterp(other);other.bind(j);
 var code='var events=getEvents();if(events.length!=1||events[0].value2!="edited"||events[0].strumTime!=105)throw "getEvents";var raw={strumTime:100,event:"E",value1:"keep",value2:null};if(!game.shouldPush(raw)||raw.value2!="edited")throw "plain event admission";if(PlayState.eventNoteEarlyTrigger(raw)!=12.5||raw.strumTime!=321)throw "offset mutation";Reflect.callMethod(game,Reflect.field(game,"firstEventPush"),[raw]);if(raw.value1!="first")throw "first push";if(game.getEvents()[0]==events[0])throw "fresh events";';
 i.execute(new NightmareVisionScriptParser().parseString(code,'event-api'));
 j.execute(new NightmareVisionScriptParser().parseString('if(getEvents().length!=2||PlayState.getEvents()[0].value2!=null)throw "owner isolation";'));
 i.release();j.release();script.destroy();trace('real Iris public event API verified');
 }
}'''
class HistoricalEventTraversalTest(unittest.TestCase):
 def run_fixture(self,text,real=False):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder);write_flixel_point_stub(work);(work/'Main.hx').write_text(text)
   command=[*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work)]
   if real:command+=['-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3')]
   result=subprocess.run(command+['-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
 def test_live_traversal_matches_pinned_get_events(self):
  donor=ROOT.parent/'fnf_sources/NightmareVision'
  if not donor.is_dir():self.skipTest('pinned source unavailable')
  s=subprocess.check_output(['git','show','7f96eb3b5a60352413229bf134bd348b79ad5fe6:source/meta/states/PlayState.hx'],cwd=donor,text=True)
  method=extract_method(s,'function getEvents(')
  first=method[method.index('for (event in eventsData)'):method.index('// this is mainly')]
  second=method[method.index('for (event in songData.events)'):method.index('return events;')]
  body='var songData=SONG;var events:Array<EventNote>=[];if(companion!=null){var eventsData=companion;'+first+'}'+second+'return events;'
  self.run_fixture(MODEL.replace('__SOURCE__',body))
 def test_public_event_apis_real_interpreter_and_owner_isolation(self):
  api=extract_method((ROOT/'source/PlayState.hx').read_text(),'function historicalNightmareVisionEventApi(')
  self.run_fixture(API.replace('__API__',api),True)
if __name__=='__main__':unittest.main()
