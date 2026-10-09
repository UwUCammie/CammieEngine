"""Pinned historical group/class callbacks and removal lifecycle comparisons."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from test_source_event_preparation import extract_method
ROOT=Path(__file__).resolve().parents[2];REV='7f96eb3b5a60352413229bf134bd348b79ad5fe6'
class HistoricalGroupPropertiesTest(unittest.TestCase):
 def test_source_group_class_and_removal_sequences(self):
  lua=subprocess.check_output(['git','-C',str(ROOT.parent/'fnf_sources/NightmareVision'),'show',REV+':source/meta/data/scripts/FunkinLua.hx'],text=True)
  helpers='\n'.join('public static '+extract_method(lua,'function '+name+'(') for name in ['getPropertyLoopThingWhatever','getObjectDirectly','getVarInArray','setVarInArray','getGroupStuff','setGroupStuff'])
  callbacks=[]
  for name in ['getPropertyFromGroup','setPropertyFromGroup','removeFromGroup','getPropertyFromClass','setPropertyFromClass']:
   start=lua.index('Lua_helper.add_callback(lua, "'+name+'"');callback=extract_method(lua[start:],'function(');callbacks.append(callback.replace('function(', 'public static function '+name+'(',1))
  play=(ROOT/'source/PlayState.hx').read_text();install=extract_method(play,'function installHistoricalLuaProperties(')
  fixture=r'''import Type.ValueType;
class Interp {public var variables:Map<String,Dynamic>=[];public function new(){}}
class LuaCompatInterp extends Interp {public function new(){super();}}
class Storage {public static var raw:Dynamic;public static var items:Array<Dynamic>;public static var map:Map<String,Dynamic>;}
class FlxTypedGroup {
 public var members:Array<Dynamic>;public var id:String;public function new(id:String,a:Array<Dynamic>){this.id=id;members=a;}
 public function remove(item:Dynamic,splice:Bool):Dynamic {PlayState.instance.events.push('remove:'+id+':'+splice);members.remove(item);if(PlayState.instance.mode==2)PlayState.instance.bucketStore=PlayState.instance.alternate;return item;}
}
class Actor {
 public var id:String;public var value:Dynamic='old';public var inner:Dynamic={value:'inner'};public var items:Array<Dynamic>=['array'];public var map:Map<String,Dynamic>=['a'=>'map'];
 public function new(id:String)this.id=id;
 public function kill(){PlayState.instance.events.push('kill:'+id);if(PlayState.instance.mode==1)PlayState.instance.bucketStore=PlayState.instance.alternate;}
 public function destroy(){PlayState.instance.events.push('destroy:'+id);}
}
class FunkinLua {
 public static function getInstance():Dynamic return PlayState.instance;
 public static function luaTrace(text:String):Void PlayState.instance.warnings++;
 __HELPERS__
}
class PlayState {
 public static var instance:PlayState;public var events:Array<String>=[];public var warnings=0;public var mode:Int;
 public var nightmareVisionLegacyFieldCameras=true;public var bucketStore:Dynamic;public var alternate:Dynamic;public var bucket(get,never):Dynamic;
 public var reads=0;function get_bucket():Dynamic {reads++;return bucketStore;}
 public var array:Array<Dynamic>;public var group:FlxTypedGroup;public var nested:Dynamic;public var first:Actor;public var second:Actor;var api:LuaCompatInterp;
 public function new(shape:Int,mode:Int){instance=this;this.mode=mode;first=new Actor('a');second=new Actor('b');array=[first,null,second];group=new FlxTypedGroup('main',array.copy());nested={array:array,group:group};bucketStore=shape==0?cast group:cast [first,second,first];alternate=new FlxTypedGroup('alternate',[first,second]);api=new LuaCompatInterp();installHistoricalLuaProperties(api,false);Storage.raw='raw';Storage.items=[['nested'],first];Storage.map=['a'=>'map'];}
 public function getLuaObject(name:String,?texts:Bool=true):Dynamic return name=='tag'?nested:null;
 function historicalPropertyInstance():Dynamic return this;
 function historicalReadProperty(o:Dynamic,k:String):Dynamic return Reflect.getProperty(o,k);
 function historicalWriteProperty(o:Dynamic,k:String,v:Dynamic):Void Reflect.setProperty(o,k,v);
 function historicalPropertyObject(name:String):Dynamic {var value=getLuaObject(name);return value!=null?value:SourceScriptReflection.readLegacyPathPart(this,name,historicalReadProperty);}
 function historicalPropertyGroup(value:Dynamic):Bool return Std.isOfType(value,FlxTypedGroup);
 function historicalRemoveGroupMember(group:Dynamic,item:Dynamic):Void group.remove(item,true);
 function historicalClassAliases():Map<String,Dynamic> return [];
 function compatResolveClass(name:String):Dynamic return Type.resolveClass(name);
 __INSTALL__
 function call(actual:Bool,name:String,args:Array<Dynamic>):Dynamic {
  return Reflect.callMethod(null,actual?api.variables.get(name):Reflect.field(FunkinLua,name),args);
 }
 static function repr(value:Dynamic):String return Std.string(Type.typeof(value))+':'+Std.string(value);
 public function sequence(actual:Bool,path:String,index:Int,field:Dynamic,value:Dynamic):String {
  var outcome=[];for(name in ['getPropertyFromGroup','setPropertyFromGroup','getPropertyFromGroup'])try {var args:Array<Dynamic>=[path,index,field];if(name=='setPropertyFromGroup')args.push(value);outcome.push(repr(call(actual,name,args)));}catch(_:Dynamic)outcome.push('error');
  return outcome.join('|')+';'+[reads,first.value,second.value,first.inner.value,first.items[0],first.map.get('a')].join(';');
 }
 public function removeSequence(actual:Bool,index:Int,keep:Bool):String {
  var failed=false;try call(actual,'removeFromGroup',['bucket',index,keep])catch(_:Dynamic)failed=true;
  var remaining:Dynamic=Std.isOfType(bucketStore,FlxTypedGroup)?bucketStore.members:bucketStore;
  var ids=[];for(i in 0...remaining.length)ids.push(remaining[i]==null?'null':remaining[i].id);
  return failed+':'+reads+':'+events.join(',')+':'+ids.join(',')+':'+group.members.length;
 }
 public function classSequence(actual:Bool,path:String,value:Dynamic):String {
  var outcome=[];for(name in ['getPropertyFromClass','setPropertyFromClass','getPropertyFromClass'])try{var args:Array<Dynamic>=['Storage',path];if(name=='setPropertyFromClass')args.push(value);outcome.push(repr(call(actual,name,args)));}catch(_:Dynamic)outcome.push('error');return outcome.join('|');
 }
 static function main(){var groupCount=0,removeCount=0,classCount=0;var keys:Array<Dynamic>=['value','inner.value','items[0]','map.a','missing.value',0,null];var values:Array<Dynamic>=[null,'false',false,12];
  for(path in ['array','group','nested.array','nested.group','tag.array','tag.group','missing','bucket'])for(index in [-1,0,1,2,4])for(field in keys)for(value in values){var expected=new PlayState(0,0).sequence(false,path,index,field,value);var observed=new PlayState(0,0).sequence(true,path,index,field,value);if(expected!=observed)throw path+':'+index+':'+field+':'+value+'\n'+expected+'\n'+observed;groupCount++;}
  for(shape in 0...2)for(mode in 0...3)for(index in [-1,0,1,2,4])for(keep in [false,true]){var expected=new PlayState(shape,mode).removeSequence(false,index,keep);var observed=new PlayState(shape,mode).removeSequence(true,index,keep);if(expected!=observed)throw 'remove '+shape+':'+mode+':'+index+':'+keep+'\n'+expected+'\n'+observed;removeCount++;}
  for(path in [null,'','raw','Raw',' raw','items[0][0]','items[1].value','map.a','missing.value'])for(value in values){var expected=new PlayState(0,0).classSequence(false,path,value);var observed=new PlayState(0,0).classSequence(true,path,value);if(expected!=observed)throw 'class '+path+'\n'+expected+'\n'+observed;classCount++;}
  trace(groupCount+' group, '+removeCount+' removal, '+classCount+' class sequences');
 }
}'''.replace('__HELPERS__',helpers+'\n'+'\n'.join(callbacks)).replace('__INSTALL__',install)
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder);(work/'PlayState.hx').write_text(fixture);(work/'SourceScriptReflection.hx').write_text((ROOT/'source/SourceScriptReflection.hx').read_text())
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','PlayState','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
