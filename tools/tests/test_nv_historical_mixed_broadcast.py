"""Verify one ordered historical broadcast over both existing language runtimes."""
from unittest import TestCase, main
from unittest.mock import patch
import test_psych_runtime_bindings as fixture

MIXED=r'''
  var log:Array<String>=[];
  var mixedHost=new PlayState();
  var plan:NightmareVisionScriptDiscovery.NightmareVisionScriptPlan={root:'owner',baseAssetsRoot:'',song:'fixture',stage:'',coverageNotes:[],scripts:[]};
  var backend=new NightmareVisionGameplayScripts({},plan,function(p)return '',function(i,e,a){},function(n,p,e)throw e);
  var registry:Map<String,NightmareVisionScriptModule>=[];backend.legacyNoteRegistry=function()return registry;
  var addHx=function(name:String):NightmareVisionScriptModule return backend.group.loadSource(name,'function noteMissPress(n){record(n);return result;}',function(i){
   i.variables.set('record',function(n:Int){if(n!=-2)throw 'live lane';log.push(name);});i.variables.set('result',0);
  });
  var addLua=function(name:String):LuaCompatInterp {
   var lua=new LuaCompatInterp();lua.variables.set('__psychScoreGlobals',true);lua.variables.set('result',0);
   lua.variables.set('noteMissPress',function(n:Int):Dynamic {if(n!=-2)throw 'Lua lane';log.push(name);return lua.variables.get('result');});
   mixedHost.hscriptStates.set(name,lua);mixedHost.psychRuntimeBindings.push(new PsychRuntimeBindings(mixedHost,lua,name));return lua;
  };
  var h1=addHx('h1');var l1=addLua('z-lua');var h2=addHx('h2');var l2=addLua('a-lua');
  var dispatch=function():Dynamic {
   var entries=backend.historicalCalls('noteMissPress',[-2]);
   for(e in PsychRuntimeBindings.historicalNightmareCalls(mixedHost,'noteMissPress',[-2]))entries.push(e);
   return NightmareVisionHistoricalBroadcast.call(entries);
  };
  var vals:Array<Dynamic>=[0,null,1,2,'text',false,0.25];
  for(a in vals)for(b in vals)for(c in vals){
   h1.set('result',a);l1.variables.set('result',b);h2.set('result',c);l2.variables.set('result',0);log.resize(0);
   var expected:Array<String>=[];var expectedResult:Dynamic=0;var i=0;
   for(v in [a,b,c,0]){expected.push(['h1','z-lua','h2','a-lua'][i++]);if(v==2)break;if(v!=null&&v!=0)expectedResult=v;}
   var result=dispatch();check(log.join(',')==expected.join(','),'cross-language registration order/halt');
   check(haxe.Json.stringify(result)==haxe.Json.stringify(expectedResult),'combined return');
  }
  h1.set('result',0);l1.variables.set('result',0);h2.set('result',0);
  registry.set('h2',null);l2.variables.set('__compatClosed',true);log.resize(0);dispatch();
  check(log.join(',')=='h1,z-lua','live type registry and closed Lua filtering');
  registry.remove('h2');l2.variables.set('__compatClosed',false);
  backend.group.removeScript(h1);backend.group.addScript(h1);log.resize(0);dispatch();
  check(log.join(',')=='z-lua,h2,a-lua,h1','re-registration moves to end');
  backend.destroy();
'''

class HistoricalMixedBroadcastTest(TestCase):
 def test_mixed_order_halt_live_filters_and_reregistration(self):
  with patch.object(fixture,'MAIN',fixture.MAIN.replace("  Sys.println('OK');",MIXED+"\n  Sys.println('OK');")):
   fixture.PsychRuntimeBindingsTest().test_runtime_broadcast_dispatch_and_embedded_source_callbacks()
if __name__=='__main__':main()
