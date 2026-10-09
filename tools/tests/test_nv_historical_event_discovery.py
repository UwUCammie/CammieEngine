"""Pinned extension/layer selection and post-admission dynamic event loading."""
import subprocess, unittest
import test_nv_historical_event_queue as fixture
from test_source_event_preparation import extract_method
ROOT=fixture.ROOT
REFERENCE=r'''class Paths {
 public static function modFolders(p:String):String return 'mod/'+p;
 public static function getPreloadPath(p:String):String return 'core/'+p;
}
class FileSystem {public static var files:Map<String,Bool>=[];public static function exists(p:String):Bool return files.exists(p);}
class FunkinLua {public function new(file:String,name:String){Reference.selected=file;}public function call(n:String,a:Array<Dynamic>):Dynamic return 0;}
class FunkinHScript {public static function fromFile(file:String,name:String):Dynamic return new FunkinLua(file,name);}
class Reference {
 public static var selected:String;
 public var eventPushedMap:Map<String,Bool>=['E'=>true];public var hscriptExts:Array<String>;
 public var luaArray:Array<Dynamic>=[];public var hscriptArray:Array<Dynamic>=[];public var funkyScripts:Array<Dynamic>=[];public var eventScripts:Map<String,Dynamic>=[];
 public function new(exts:Array<String>){hscriptExts=exts;}
 public function run(){__BLOCK__}
}
class Main {
 static function main(){
  for(exts in [['hx','hxs','hscript'],['hscript','hx'],[]])for(mask in 0...256){
   FileSystem.files=[];var bit=0;
   for(ext in ['lua','hx','hxs','hscript'])for(layer in ['mod/','core/'])if((mask&(1<<bit++))!=0)FileSystem.files.set(layer+'custom_events/E.'+ext,true);
   Reference.selected=null;new Reference(exts).run();
   var actual=NightmareVisionLegacyEventLoader.select('E',exts,Paths.modFolders,Paths.getPreloadPath,FileSystem.exists);
   if((actual==null?null:actual.path)!=Reference.selected)throw 'selection '+mask+':'+exts;
   if(actual!=null&&(actual.name!='E'||actual.scope!='event'))throw 'lost authored identity';
  }
  trace('768 source event path comparisons verified');
 }
}'''
DYNAMIC=r'''class Main {
 static function main(){
  var registry=new NightmareVisionLegacyScriptRegistry();var reads:Array<String>=[];var loads:Array<String>=[];
  var plan:NightmareVisionScriptDiscovery.NightmareVisionScriptPlan={root:'owner',baseAssetsRoot:'',song:'test',stage:'',coverageNotes:[],scripts:[]};
  var backend=new NightmareVisionGameplayScripts(null,plan,function(path){reads.push(path);return 'function onLoad(n){record(n);} function onTrigger(a,b){return a+":"+b;}';},
   function(i,e,a){var s:NightmareVisionScriptModule=cast i.variables.get('script');s.historicalCalls=true;i.variables.set('record',function(n:String)loads.push(n));},function(n,c,e)throw e);
  backend.legacyEventRegistry=function()return registry.eventScripts;
  var queries:Array<String>=[];
  backend.resolveHistoricalEvent=function(name){queries.push(name);return name=='Added'?{scope:'event',name:name,path:'owner/custom_events/Added.hxs',relative:'owner/custom_events/Added.hxs'}:null;};
  var rows:Array<Dynamic>=[];registry.eventScripts.set('Original',{scriptType:'hscript'});
  NightmareVisionLegacyEventPreparation.prepare(function(visit)visit({time:0.,name:'Original',v1:'left',v2:'right',order:0}),function()return 0.,function()return registry.eventScripts,
   function(s,n,a):Dynamic {if(Std.isOfType(s,NightmareVisionScriptModule))return registry.callScript(s,n,a);if(n=='shouldPush'){Reflect.setProperty(a[0],'event','Added');return true;}return 0;},function(n,a)return 0,function(name)backend.loadScope('event',name),function(r,e)rows.push(r),function(e)return false,function()return registry.eventPushedMap);
  if(reads.length!=1||rows.length!=1||rows[0].name!='Added')throw 'admission rename not resolved';
  backend.loadScope('event','Added');backend.loadScope('event','Added');
  if(reads.length!=1||loads.join(',')!='Added'||backend.callEvent('Added','onTrigger',['l','r'])!='l:r'||plan.scripts.length!=0)throw 'live unplanned event load';
  registry.eventScripts.remove('Added');backend.callEvent('Added','onTrigger',[]);
  if(reads.length!=1)throw 'playback rediscovered removed handler';
  var lua=0;backend.loadHistoricalLuaEvent=function(e){lua++;if(e.name!='Lua')throw 'Lua identity';};
  backend.resolveHistoricalEvent=function(n)return {scope:'event',name:n,path:'owner/custom_events/'+n+'.lua',relative:'owner/custom_events/'+n+'.lua'};
  backend.loadScope('event','Lua');backend.loadScope('event','Lua');
  if(lua!=1||reads.length!=1)throw 'Lua passed through HScript parser or loaded twice';
  backend.destroy();
 }
}'''
class HistoricalEventDiscoveryTest(unittest.TestCase):
 def test_pinned_extension_and_owner_precedence(self):
  donor=ROOT.parent/'fnf_sources/NightmareVision'
  if not donor.is_dir():self.skipTest('pinned source unavailable')
  source=subprocess.check_output(['git','show','7f96eb3b5a60352413229bf134bd348b79ad5fe6:source/meta/states/PlayState.hx'],cwd=donor,text=True)
  gen=extract_method(source,'function generateSong(')
  block=extract_method(gen,'for (event in eventPushedMap.keys())')
  # Compile the source-supported native/Lua branches and suppress noisy source tracing.
  block=block.replace('#if LUA_ALLOWED "lua" #end','"lua"').replace('#if MODS_ALLOWED Paths.modFolders(baseFile), #end','Paths.modFolders(baseFile),').replace('trace("event script " + event);','')
  fixture.HistoricalEventQueueTest().run_fixture(REFERENCE.replace('__BLOCK__',block))
 def test_owner_resolver_uses_flat_preload_and_validated_paths(self):
  source=(ROOT/'source/NightmareVisionPaths.hx').read_text()
  method=source[source.index('public function resolveHistoricalEvent('):].split(';',1)[0]+';'
  code=r'''class Owner {
   public var CORE_DIRECTORY='core';public var files:Map<String,Bool>=['core/custom_events/E.lua'=>true,'level/custom_events/E.lua'=>true];
   public function new(){}
   public function modFolders(p:String):String return scopedPath('mod',p);
   public function scopedPath(root:String,p:String):String {if(p.indexOf('..')>=0)throw 'invalid owner path';return root+'/'+p;}
   public function exists(p:String):Bool return files.exists(p);
   public function getOwnerCorePath(p:String):String throw 'stage library must not affect event preload';
   __METHOD__
  }
  class Main {static function main(){
   var o=new Owner();if(o.resolveHistoricalEvent('E',['hx']).path!='core/custom_events/E.lua')throw 'flat preload';
   var rejected=false;try o.resolveHistoricalEvent('../foreign',['hx'])catch(e:Dynamic)rejected=true;
   if(!rejected)throw 'unvalidated event name';
  }}'''
  fixture.HistoricalEventQueueTest().run_fixture(code.replace('__METHOD__',method))
 def test_dynamic_names_use_existing_backend_and_language_loader(self):fixture.HistoricalEventQueueTest().run_fixture(DYNAMIC)
if __name__=='__main__':unittest.main()
