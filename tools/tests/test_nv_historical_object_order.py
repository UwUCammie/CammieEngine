"""Compare object ordering with pinned source, including live scene replacement."""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_source_event_preparation import extract_method
ROOT = Path(__file__).resolve().parents[2]
REV = '7f96eb3b5a60352413229bf134bd348b79ad5fe6'

class HistoricalObjectOrderTest(unittest.TestCase):
 def test_source_order_transactions(self):
  lua = subprocess.check_output(['git','-C',str(ROOT.parent/'fnf_sources/NightmareVision'),'show',REV+':source/meta/data/scripts/FunkinLua.hx'],text=True)
  helpers = '\n'.join('public static '+extract_method(lua,'function '+name+'(') for name in ['getObjectDirectly','getVarInArray','getPropertyLoopThingWhatever'])
  callbacks = []
  for name in ['getObjectOrder','setObjectOrder']:
   callback = extract_method(lua[lua.index('Lua_helper.add_callback(lua, "'+name+'"'):],'function(')
   callbacks.append(callback.replace('function(', 'public static function '+name+'(',1))
  play = (ROOT/'source/PlayState.hx').read_text()
  install = extract_method(play,'function installHistoricalLuaObjectOrder(')
  fixture = r'''import Type.ValueType;
class Interp {public var variables:Map<String,Dynamic>=[];public function new(){}}
class LuaCompatInterp extends Interp {public function new(){super();}}
class FlxBasic {public var id:String;public function new(id:String)this.id=id;}
class Scene {
 public var members:Array<FlxBasic>;public var id:String;public var target:FlxBasic;public var nested:Dynamic;
 public function new(id:String,a:FlxBasic,b:FlxBasic){this.id=id;target=b;members=[a,null,b];nested={items:[a,b]};}
 public function remove(o:FlxBasic,splice:Bool):FlxBasic {PlayState.instance.events.push('remove:'+id+':'+o.id+':'+splice);members.remove(o);if(PlayState.instance.mode==2)PlayState.instance.active=PlayState.instance.other;return o;}
 public function insert(position:Int,o:FlxBasic):FlxBasic {PlayState.instance.events.push('insert:'+id+':'+position+':'+o.id);if(members.indexOf(o)<0)members.insert(position,o);return o;}
}
class FunkinLua {
 public static function getInstance():Dynamic return PlayState.instance.getScene();
 public static function luaTrace(text:String):Void {PlayState.instance.warnings++;}
 __SOURCE__
}
class PlayState {
 public static var instance:PlayState;public var nightmareVisionLegacyFieldCameras=true;
 public var active:Scene;public var mainScene:Scene;public var other:Scene;public var a:FlxBasic;public var b:FlxBasic;
 public var events:Array<String>=[];public var warnings=0;public var mode:Int;public var tagReads=0;public var sceneReads=0;
 var api=new LuaCompatInterp();
 public function new(dead:Bool,mode:Int){instance=this;haxe.Log.trace=function(v:Dynamic,?p:haxe.PosInfos){instance.warnings++;};this.mode=mode;a=new FlxBasic('a');b=new FlxBasic('b');mainScene=new Scene('main',a,b);other=new Scene('dead',b,a);active=dead?other:mainScene;installHistoricalLuaObjectOrder(api,false);}
 public function getScene():Scene {sceneReads++;return active;}
 public function getLuaObject(name:String,?texts:Bool=true):Dynamic {tagReads++;if(mode==1&&tagReads==2)active=other;return switch(name){case 'tag':a;case 'nestedTag':{items:[a,b]};default:null;};}
 function historicalPropertyInstance():Dynamic return getScene();
 function historicalPropertyObject(name:String):Dynamic {var o=getLuaObject(name);return o!=null?o:SourceScriptReflection.readLegacyPathPart(getScene(),name,historicalReadProperty);}
 function historicalReadProperty(o:Dynamic,k:String):Dynamic return Reflect.getProperty(o,k);
 __INSTALL__
 function call(actual:Bool,name:String,args:Array<Dynamic>):Dynamic return Reflect.callMethod(null,actual?api.variables.get(name):Reflect.field(FunkinLua,name),args);
 function sequence(actual:Bool,path:String,pos:Int):String {
  var results=[];for(name in ['getObjectOrder','setObjectOrder','getObjectOrder'])try{var args:Array<Dynamic>=[path];if(name=='setObjectOrder')args.push(pos);var result=call(actual,name,args);results.push(name=='setObjectOrder'?'void':Std.string(result));}catch(_:Dynamic)results.push('error');
  return results.join('|')+';'+events.join(',')+';'+[tagReads,sceneReads,warnings].join(',')+';'+[for(o in mainScene.members)o==null?'null':o.id].join(',')+';'+[for(o in other.members)o==null?'null':o.id].join(',');
 }
 static function main(){var count=0;for(dead in [false,true])for(mode in 0...3)for(path in [null,'','tag','target','nestedTag.items[0]','nestedTag.items[1]','nested.items[0]','nested.items[1]','missing','nested.missing','nested.items[4]'])for(pos in [-3,0,1,3,50]){
  var expected=new PlayState(dead,mode).sequence(false,path,pos);var observed=new PlayState(dead,mode).sequence(true,path,pos);if(expected!=observed)throw path+':'+pos+':'+dead+':'+mode+'\n'+expected+'\n'+observed;count++;
 }trace(count+' object-order sequences');
 var state=new PlayState(false,0);var observer=new LuaCompatInterp();state.installHistoricalLuaObjectOrder(observer,true);if(observer.variables.exists('getObjectOrder'))throw 'results observer overwritten';state.nightmareVisionLegacyFieldCameras=false;state.installHistoricalLuaObjectOrder(observer,false);if(observer.variables.exists('getObjectOrder'))throw 'modern profile overwritten';
 }
}'''.replace('__SOURCE__',helpers+'\n'+'\n'.join(callbacks)).replace('__INSTALL__',install)
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder)
   (work/'PlayState.hx').write_text(fixture)
   (work/'SourceScriptReflection.hx').write_text((ROOT/'source/SourceScriptReflection.hx').read_text())
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','PlayState','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
