"""Historical post-effect notification order and live map selection against pinned source."""
import subprocess, unittest
import test_nv_historical_event_queue as fixture
from test_source_event_preparation import extract_method
ROOT=fixture.ROOT
MAIN=r'''class Model {
 public var registry=new NightmareVisionLegacyScriptRegistry();
 public var eventScripts(get,set):Map<String,Dynamic>;
 function get_eventScripts()return registry.eventScripts;
 function set_eventScripts(v:Map<String,Dynamic>)return registry.eventScripts=v;
 public var log:Array<String>=[];var mode:Int;var stop:Dynamic;var replacement:Dynamic;
 public function new(mode:Int,stop:Dynamic,lua:Bool){
  this.mode=mode;this.stop=stop;
  var make=function(name:String,global:Bool):Dynamic {
   var code=global?'function onEvent(n,a,b){record(n+":"+a+":"+b);mutate();return result;}':'function onTrigger(a,b){record(a+":"+b);return 2;}';
   if(lua){
    var i=new hscript.Interp();i.variables.set('record',function(s:String)log.push(name+':'+s));i.variables.set('mutate',mutate);i.variables.set('result',stop);
    i.execute(new hscript.Parser().parseString(code));
    return new NightmareVisionLegacyLuaScript(name,i,function(n,a){var f=i.variables.get(n);return f==null?0:Reflect.callMethod(i,f,a);});
   }
   return NightmareVisionScriptModule.fromSource(name,code,null,null,function(i){
    var h:NightmareVisionScriptModule=cast i.variables.get('script');h.historicalCalls=true;
    i.variables.set('record',function(s:String)log.push(name+':'+s));i.variables.set('mutate',mutate);i.variables.set('result',stop);
   },function(n,c,e)throw e);
  };
  registry.add(make('first',true));registry.add(make('last',true));
  eventScripts=['E'=>make('E',false)];replacement=make('replacement',false);
 }
 function mutate():Void {
  switch(mode){
   case 1:eventScripts=['E'=>replacement];
   case 2:eventScripts.remove('E');
   case 3:eventScripts=['E'=>null];
   case 4:registry.funkyScripts.resize(1);
   case 5:throw 'global failed';
   default:
  }
 }
 function callOnScripts(n:String,a:Array<Dynamic>):Dynamic return registry.callOnScripts(n,a);
 function callScript(s:Dynamic,n:String,a:Array<Dynamic>):Dynamic return registry.callScript(s,n,a);
 function source(eventName:String,value1:String,value2:String):Void { __TAIL__ }
 public function run(native:Bool):String {
  log.push('effect');
  try {if(native)registry.notifyEvent('E','left','right');else source('E','left','right');}catch(e:Dynamic)log.push('error');
  return log.join(',');
 }
}
class Main {
 static function main(){
  for(lua in [false,true])for(mode in 0...6)for(stop in [0,1,2]){
   var expected=new Model(mode,stop,lua).run(false);var actual=new Model(mode,stop,lua).run(true);
   if(expected!=actual)throw mode+':'+stop+':'+lua+':'+expected+' != '+actual;
   if(mode==0&&stop==2&&actual!='effect,first:E:left:right,E:left:right')throw 'stop must retain selected event';
  }
  trace('36 source notification scenarios verified');
 }
}'''
class HistoricalEventNotificationTest(unittest.TestCase):
 def test_pinned_notification_tail_and_language_handles(self):
  donor=ROOT.parent/'fnf_sources/NightmareVision'
  if not donor.is_dir():self.skipTest('pinned source unavailable')
  source=subprocess.check_output(['git','show','7f96eb3b5a60352413229bf134bd348b79ad5fe6:source/meta/states/PlayState.hx'],cwd=donor,text=True)
  method=extract_method(source,'function triggerEventNote(')
  tail=method[method.index("callOnScripts('onEvent'"):].rstrip()[:-1]
  fixture.HistoricalEventQueueTest().run_fixture(MAIN.replace('__TAIL__',tail))
if __name__=='__main__':unittest.main()
