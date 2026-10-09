"""Historical Lua property callbacks against the pinned source functions."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from test_source_event_preparation import extract_method
ROOT=Path(__file__).resolve().parents[2]
REV='7f96eb3b5a60352413229bf134bd348b79ad5fe6'
class HistoricalLuaPropertiesTest(unittest.TestCase):
 def test_source_callbacks_and_profile_binding(self):
  lua=subprocess.check_output(['git','-C',str(ROOT.parent/'fnf_sources/NightmareVision'),'show',REV+':source/meta/data/scripts/FunkinLua.hx'],text=True)
  play=(ROOT/'source/PlayState.hx').read_text()
  helpers='\n'.join('public static '+extract_method(lua,'function '+name+'(') for name in ['getPropertyLoopThingWhatever','getObjectDirectly','getVarInArray','setVarInArray'])
  callbacks=[]
  for name in ['getProperty','setProperty']:
   start=lua.index('Lua_helper.add_callback(lua, "'+name+'"')
   callback=extract_method(lua[start:],'function(variable:')
   callbacks.append(callback.replace('function(variable:', 'public static function '+name+'(variable:',1))
  methods='\n'.join(extract_method(play,'function '+name+'(') for name in ['historicalPropertyInstance','historicalPropertyObject','installHistoricalLuaProperties'])
  lookup=extract_method(play,'public function getLuaObject(')
  fixture=r'''import Type.ValueType;
class Interp {public var variables:Map<String,Dynamic>=[];public function new(){}}
class LuaCompatInterp extends Interp {public function new(){super();}}
class GameOverSubstate {public static var instance:Dynamic;}
class FunkinLua {
 public static function getInstance():Dynamic return PlayState.instance.isDead?GameOverSubstate.instance:PlayState.instance;
 __HELPERS__
}
class Probe {
 public var value:Dynamic='original';public var items:Array<Dynamic>=[{value:'first'},[{value:'nested'}]];
 public var child(get,never):Dynamic;public var kid:Dynamic={value:'child'};var s:PlayState;
 public function new(s:PlayState)this.s=s;
 function get_child():Dynamic {s.reads++;if(s.mutating) {s.isDead=!s.isDead;s.probe=new Probe(s);}return kid;}
}
class PlayState {
 public static var instance:PlayState;public var isDead:Bool;public var nightmareVisionLegacyFieldCameras=true;
 public var modchartObjects:Map<String,Dynamic>=[];public var modchartSprites:Map<String,Dynamic>=[];public var modchartTexts:Map<String,Dynamic>=[];
 public var probe:Probe;public var original:Probe;public var raw:Dynamic='live';public var map:Map<String,Dynamic>=['a'=>'map'];public var other:Dynamic;
 public var originalMap:Map<String,Dynamic>;public var deadMap:Map<String,Dynamic>;public var deadProbe:Probe;public var reads=0;public var mutating:Bool;var actual:Bool;var api:LuaCompatInterp;
 public function new(actual:Bool,dead:Bool,mutating:Bool) {
  instance=this;this.actual=actual;isDead=dead;this.mutating=mutating;probe=new Probe(this);original=probe;
  modchartObjects=['shared'=>{value:'object'},'nil'=>null];modchartSprites=['shared'=>{value:'sprite'},'nil'=>{value:'spriteNil'}];modchartTexts=['text'=>{value:'text'}];
  other={raw:'dead',probe:new Probe(this),map:['a'=>'deadMap']};GameOverSubstate.instance=other;originalMap=map;deadMap=other.map;deadProbe=other.probe;
  api=new LuaCompatInterp();installHistoricalLuaProperties(api,false);
 }
 function compatFindObject(tag:String):Dynamic return null;
 function historicalReadProperty(o:Dynamic,k:String):Dynamic return Reflect.getProperty(o,k);
 function historicalWriteProperty(o:Dynamic,k:String,v:Dynamic):Void Reflect.setProperty(o,k,v);
 __METHODS__
 public function run(path:String,value:Dynamic):String {
  var outcomes=[];
  var get=function():Dynamic return actual?Reflect.callMethod(null,api.variables.get('getProperty'),[path]):FunkinLua.getProperty(path);
  var set=function():Dynamic return actual?Reflect.callMethod(null,api.variables.get('setProperty'),[path,value]):FunkinLua.setProperty(path,value);
  for(action in [get,set,get]) {try {var result:Dynamic=action();outcomes.push(Std.string(Type.typeof(result))+':'+Std.string(result));}catch(_:Dynamic)outcomes.push('error');}
  var snapshot:Array<Dynamic>=[raw,other.raw,originalMap.get('a'),deadMap.get('a'),original.value,original.kid.value,deadProbe.value,deadProbe.kid.value,reads,isDead,original.items[0],original.items[1][0],modchartObjects.get('shared').value,modchartSprites.get('shared').value,modchartTexts.get('text').value];return outcomes.join('|')+';'+snapshot.join(';');
 }
 public static function main(){var count=0;var values:Array<Dynamic>=[null,'false','1.25',false,12];
  for(dead in [false,true])for(mutating in [false,true])for(path in [null,'','raw',' raw','raw ','RAW','probe','probe.value','probe.child.value','probe.items[0]','probe.items[1][0]','probe.items[0].value','probe.items[1][0].value','probe.items[bad]','map.a','map','missing.value','shared','shared.value','text.value','nil.value','modchartTexts.text.value','.raw','probe..value'])for(value in values) {
   var expected=new PlayState(false,dead,mutating).run(path,value);var observed=new PlayState(true,dead,mutating).run(path,value);
   if(expected!=observed)throw dead+':'+mutating+':'+path+':'+value+'\n'+expected+'\n'+observed;count++;
  }
  var s=new PlayState(true,false,false);for(mode in 0...3) {var i:Interp=mode==0?new Interp():new LuaCompatInterp();var sentinel=function()return 'unchanged';i.variables.set('getProperty',sentinel);i.variables.set('setProperty',sentinel);s.nightmareVisionLegacyFieldCameras=mode!=1;s.installHistoricalLuaProperties(i,mode==2);if(i.variables.get('getProperty')!=sentinel||i.variables.get('setProperty')!=sentinel)throw 'profile isolation';}
  trace(count+' Lua property sequences');
 }
}'''.replace('__HELPERS__',helpers+'\n'+'\n'.join(callbacks)).replace('__METHODS__',methods+'\n'+lookup)
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder);(work/'PlayState.hx').write_text(fixture);(work/'SourceScriptReflection.hx').write_text((ROOT/'source/SourceScriptReflection.hx').read_text())
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','PlayState','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
