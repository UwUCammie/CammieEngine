"""Pinned historical two-pass event admission, callback ABI and timing."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from test_source_event_preparation import extract_method
ROOT=Path(__file__).resolve().parents[2]
REFERENCE=r'''typedef EventNote={strumTime:Float,event:String,value1:String,value2:String};
class Reference {
 public var eventScripts:Map<String,Dynamic>=[];
 public var log:Array<String>=[];public var accepted:Array<EventNote>=[];public var first:EventNote;
 public var offset:Float=5;public var pass=0;public var reject:Bool;public var language:String;
 public function new(reject:Bool,language:String){this.reject=reject;this.language=language;eventScripts.set('E',{scriptType:language});}
 function callScript(script:Dynamic,name:String,args:Array<Dynamic>):Dynamic {
  var e:Dynamic=language=='lua'?null:args[0];var value=language=='lua'?args[0]:Reflect.getProperty(e,'value1');
  log.push(name+':'+value+':'+args.length);
  if(name=='shouldPush') {if(e!=null)Reflect.setProperty(e,'value2','admitted');return value=='reject'&&reject?false:true;}
  if(name=='firstPush') {first=e;if(e!=null){Reflect.setProperty(e,'value1','first-only');Reflect.setProperty(e,'strumTime',999.);}offset=9;}
  if(name=='getOffset'){if(e!=null)Reflect.setProperty(e,'strumTime',800.);return value=='zero'?0:12.5;}
  if(name=='onPush'&&e!=null){if(accepted.indexOf(e)<0)throw 'not published';Reflect.setProperty(e,'value2','retained');}
  return 0;
 }
 function callOnScripts(name:String,args:Array<Dynamic>):Dynamic {log.push(name+':'+args[0]+':'+args[1]);return 30.;}
 function rows():Array<EventNote> {pass++;return [for(v in ['zero','reject','zero']){strumTime:100.+offset,event:'E',value1:v,value2:null}];}
 function getEvents():Array<EventNote>{var out=[];for(e in rows())if(shouldPush(e))out.push(e);return out;}
 public function run(){var names:Map<String,Bool>=[];for(e in getEvents())if(!names.exists(e.event)){names.set(e.event,true);firstEventPush(e);}for(n in names.keys())log.push('load:'+n);for(e in getEvents()){e.strumTime-=eventNoteEarlyTrigger(e);accepted.push(e);eventPushed(e);}}
 __METHODS__
}
'''
MAIN=r'''@:access(Reference) class Main {
 static function check(b:Bool,m:String){if(!b)throw m;}
 static function main(){
 for(language in ['hscript','lua'])for(reject in [false,true]) {
  var expected=new Reference(reject,language);expected.run();
  var actual=new Reference(reject,language);var rows:Array<Dynamic>=[];var views:Array<SourceEventNote>=[];
  NightmareVisionLegacyEventPreparation.prepare(function(){actual.pass++;return [for(v in ['zero','reject','zero']){time:100.,name:'E',v1:v,v2:null,order:0}];},function()return actual.offset,
   function()return actual.eventScripts,actual.callScript,actual.callOnScripts,function(n)actual.log.push('load:'+n),
   function(r,e){rows.push(r);views.push(e);actual.accepted.push(cast e);},function(e)return false);
  check(actual.log.join('|')==expected.log.join('|'),'pinned callback sequence '+language+' '+actual.log.join('|')+' != '+expected.log.join('|'));
  check(views.length==expected.accepted.length&&actual.pass==2,'two independent admissions');
  for(i in 0...views.length){var a=views[i];var b=expected.accepted[i];check(a.strumTime==b.strumTime&&a.value1==b.value1&&a.value2==b.value2,'pinned fresh view and timing '+a.strumTime+' != '+b.strumTime);check(a!=cast actual.first,'first pass reference leaked');a.value2='later';check(rows[i].v2=='later','retained queue identity');rows[i].time=17.;check(a.strumTime==17,'native queue writes visible');}
 }
 // Fresh admission completes before offset callbacks; map replacement stays live.
 var map:Map<String,Dynamic>=[];var loaded=false;var calls:Array<String>=[];var kept:Array<SourceEventNote>=[];
 NightmareVisionLegacyEventPreparation.prepare(function()return [{time:100.,name:'E',v1:'x',v2:null,order:0}],function()return 0.,function()return map,
  function(s,n,a):Dynamic {calls.push(n);return n=='shouldPush'?false:0;},function(n,a)return 0,function(n){loaded=true;map=['E'=>{scriptType:'hscript'}];},function(r,e)kept.push(e),function(e)return false);
 check(loaded&&kept.length==0&&calls.join(',')=='shouldPush','newly loaded module can reject the second pass');
 trace('historical event preparation verified');
 }
}'''
class HistoricalEventPreparationTest(unittest.TestCase):
 def test_pinned_multi_pass_callbacks_and_retained_identity(self):
  donor=ROOT.parent/'fnf_sources/NightmareVision'
  if not donor.is_dir():self.skipTest('pinned source unavailable')
  source=subprocess.check_output(['git','show','7f96eb3b5a60352413229bf134bd348b79ad5fe6:source/meta/states/PlayState.hx'],cwd=donor,text=True)
  methods=[]
  for name in ['shouldPush','firstEventPush','eventNoteEarlyTrigger']:
   methods.append(extract_method(source,'function '+name+'('))
  # Default event branch is copied verbatim; builtins are covered by the host fixture.
  pushed=extract_method(source,'function eventPushed(')
  methods.append('function eventPushed(event:EventNote){switch(event.event){'+pushed[pushed.rindex('default:'):])
  ref=REFERENCE.replace('__METHODS__','\n'.join(methods)).replace('function callScript','public function callScript').replace('function callOnScripts','public function callOnScripts')
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder);(work/'Main.hx').write_text(ref+MAIN)
   for name in ['SourceEventNote','NightmareVisionLegacyEventPreparation']:(work/(name+'.hx')).write_text((ROOT/'source'/(name+'.hx')).read_text())
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
