"""Historical event maps share modules while preserving source initialization order."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from tools.haxe_flixel_math_stubs import write_flixel_point_stub
ROOT=Path(__file__).resolve().parents[2]
REFERENCE=r'''class Reference {
 public var phases:Array<String>=[];public var eventScripts:Map<String,Dynamic>=[];public var hscriptArray:Array<Dynamic>=[];public var funkyScripts:Array<Dynamic>=[];
 public function new(){}
 function create(file:String,event:String):Dynamic {
  phases.push('top:'+eventScripts.exists(event)+':false');var script:Dynamic={};
  Reflect.setField(script,'call',function(n:String,args:Array<Dynamic>){phases.push('load:'+(eventScripts.get(args[0])==script)+':'+(hscriptArray.indexOf(script)>=0));return 0;});return script;
 }
 public function load(){var file='fixture';var event='E';var doPush=false;__SOURCE_BLOCK__}
}
'''
MAIN=r'''class Host {public var eventScripts=new NightmareVisionScriptGroup();public function new(){}}
class Main {
 static function check(b:Bool,m:String){if(!b)throw m;}
 static function main(){
  var owner=new Host();var registry=new NightmareVisionLegacyScriptRegistry();var phases:Array<String>=[];
  var replacement:Map<String,Dynamic>=[];
  var entries:Array<NightmareVisionScriptDiscovery.NightmareVisionScriptEntry>=[{scope:'event',name:'E',relative:'events/E.hx',path:'owner/events/E.hx'}, {scope:'event',name:'Replace',relative:'events/Replace.hx',path:'owner/events/Replace.hx'}];
  var host=new NightmareVisionGameplayScripts(owner,{root:'owner',baseAssetsRoot:'',song:'fixture',stage:'',coverageNotes:[],scripts:entries},
   function(path)return path.indexOf('Replace')>=0?'function onLoad(n){eventScripts=replacement;}':
    'record("top",eventScripts.exists("E"),funkyScripts.indexOf(script)>=0);function onLoad(n){record("load",eventScripts.get(n)==script,hscriptArray.indexOf(script)>=0);} function onTrigger(a,b){return a+":"+b;}',
   function(i,e,a){var module:NightmareVisionScriptModule=cast i.variables.get('script');module.historicalCalls=true;NightmareVisionLegacyRegistryBindings.install(i,owner,Host,registry);i.variables.set('replacement',replacement);i.variables.set('record',function(n:String,map:Bool,array:Bool)phases.push(n+":"+map+":"+array));},
   function(n,c,e)throw e);
  host.legacyEventRegistry=function()return registry.eventScripts;
  host.group.onRegistered=function(s)registry.add(s);host.group.onRemoved=registry.remove;
  host.group.loadSource('E','function dummy(){}');
  check(!host.hasEventCallback('E','onTrigger')&&host.callEvent('E','onTrigger',['a','b'])==0&&phases.length==0,'historical lookup never loads an absent script');
  host.loadScope('event','E');
  check(host.callEvent('E','onTrigger',['a','b'])=='a:b','source event dispatch');
  var original:NightmareVisionScriptModule=registry.eventScripts.get('E');
  var reference=new Reference();reference.load();check(phases.join(',')==reference.phases.join(','),'pinned construction/map/onLoad/array order '+phases.join(','));
  check(host.group.members.length==2&&registry.hscriptArray.indexOf(original)>=0,'same-name global does not suppress event');
  check(host.hasEventCallback('E','onTrigger'),'callable owned entry');
  registry.eventScripts.remove('E');check(host.callEvent('E','onTrigger',['x','y'])==0&&!host.hasEventCallback('E','onTrigger'),'removed entry stays removed');
  registry.eventScripts.set('Alias',original);check(host.callEvent('Alias','onTrigger',['x','y'])=='x:y','live map accepts unplanned alias');
  var old=registry.eventScripts;host.loadScope('event','Replace');check(registry.eventScripts==replacement&&old.exists('Replace')&&!replacement.exists('Replace'),'onLoad replacement persists');
  var api=new NightmareVisionScriptInterp(owner);NightmareVisionLegacyRegistryBindings.install(api,owner,Host,registry);api.variables.set('game',owner);api.variables.set('PlayState',Host);api.variables.set('Reflect',api.sourceClassScope().reflectFacade());api.variables.set('old',old);
  api.execute(new NightmareVisionScriptParser().parseString('if(eventScripts!=game.eventScripts||eventScripts!=PlayState.eventScripts||eventScripts!=Reflect.getProperty(game,"eventScripts"))throw "map aliases";Reflect.setProperty(game,"eventScripts",old);if(eventScripts!=old)throw "map replace";'));
  check(registry.eventScripts==old&&host.callEvent('Alias','onTrigger',['1','2'])=='1:2','backend follows reflected replacement');
  check(owner.eventScripts.members.length==0,'native modern group storage preserved');
  registry.eventScripts.set('E',original);var count=registry.funkyScripts.length;registry.callOnScripts('missing',[]);check(registry.funkyScripts.length==count+3,'combined call appends map values including duplicates');
  var fake:Dynamic={scriptName:'Lua',scriptType:'lua'};Reflect.setField(fake,'call',function(n:String,a:Array<Dynamic>)return a.join('/'));Reflect.setField(fake,'get',function(n:String):Dynamic return n=='onTrigger'?Reflect.field(fake,'call'):null);
  registry.eventScripts.set('Lua',fake);check(host.hasEventCallback('Lua','onTrigger')&&host.callEvent('Lua','onTrigger',['l','r'])=='l/r','existing language handle dispatch');
  registry.eventScripts.set('Null',null);var failed=false;try host.callEvent('Null','x',[])catch(e:Dynamic)failed=true;check(failed,'invalid map entries remain errors');
  api.release();host.destroy();owner.eventScripts.destroy();
 }
}'''
class HistoricalEventMapTest(unittest.TestCase):
 def test_live_map_aliases_loader_order_and_shared_dispatch(self):
  donor=ROOT.parent/'fnf_sources/NightmareVision'
  if not donor.is_dir():self.skipTest('pinned source unavailable')
  source=subprocess.check_output(['git','show','7f96eb3b5a60352413229bf134bd348b79ad5fe6:source/meta/states/PlayState.hx'],cwd=donor,text=True)
  start=source.index('var script = FunkinHScript.fromFile(file, event);')
  end=source.index('doPush = true;',start)+len('doPush = true;')
  reference=REFERENCE.replace('__SOURCE_BLOCK__',source[start:end].replace('FunkinHScript.fromFile','create'))
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder);write_flixel_point_stub(work);(work/'Main.hx').write_text(reference+MAIN)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
