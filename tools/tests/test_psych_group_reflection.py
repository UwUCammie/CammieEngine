"""Exact pinned Psych group callbacks, including mutation and evaluation order."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,ROOT
from test_source_event_preparation import extract_method

class PsychGroupReflectionTest(unittest.TestCase):
 def test_source_group_contracts(self):
  donor=ROOT.parent/'fnf_sources/FNF-PsychEngine'
  def source(path):return subprocess.check_output(['git','-C',str(donor),'show','5c67ced49e5a98535298a6daa3f8f4ec79ac8399:'+path],text=True)
  reflect=source('source/psychlua/ReflectionFunctions.hx');utils=source('source/psychlua/LuaUtils.hx')
  names=['getPropertyFromGroup','setPropertyFromGroup','addToGroup','removeFromGroup']
  callbacks=[]
  for name in names:
   start=reflect.index('function(',reflect.index('"'+name+'"'));callbacks.append('public static var '+name+'='+extract_method(reflect[start:],'function(')+';')
  methods='\n'.join('public static '+extract_method(utils,'function '+name+'(') for name in ['getGroupStuff','setGroupStuff','getVarInArray','getPropertyLoop','getObjectDirectly','getTargetInstance','isMap'])
  fixture=r'''import Type.ValueType;
using StringTools;
typedef FlxSprite=Dynamic;
class Item {
 public var id:Int;public var x:Dynamic;public var deep:Dynamic;public var map:Map<String,Dynamic>=["key"=>4];public var rows:Array<Int>=[1];
 public function new(id:Int){this.id=id;x=id;deep={value:id+1};}
 public function destroy():Void {Main.events.push("destroy:"+id);Main.destroyed.push(id);Main.swap();}
}
class Group {
 public var members:Array<Dynamic>;
 public function new(items:Array<Dynamic>){members=items;}
 public function add(v:Dynamic):Dynamic {Main.events.push("add");members.push(v);Main.swap();return v;}
 public function insert(i:Int,v:Dynamic):Dynamic {Main.events.push("insert:"+i);members.insert(i,v);Main.swap();return v;}
 public function remove(v:Dynamic,splice:Bool):Dynamic {Main.events.push("remove:"+Std.string(v==null?null:v.id)+":"+splice);var removed=members.remove(v);Main.swap();return removed?v:null;}
}
class MusicBeatState {
 public var items:Dynamic;public var group:Dynamic;public var nested:Dynamic;public var invalid:Dynamic={};
 public function new(id:Int){items=[new Item(id),[5,6],null];group=new Group([new Item(id+10),null]);nested={items:[new Item(id+20)],group:new Group([new Item(id+30)])};}
 public static function getState():Dynamic {Main.events.push("state");return Main.current;}
 public static function getVariables():Dynamic return Main.registry();
}
class PlayState extends MusicBeatState {public static var instance:PlayState;public var isDead:Bool=false;public function new(id:Int){super(id);}}
class GameOverSubstate {public static var instance:Dynamic;}
class FlxColor {public static var RED:Int=0;}
class FunkinLua {public static function luaTrace(s:String,?a:Bool,?b:Bool,?c:Dynamic):Void Main.warn(s);}
class LuaUtils {__METHODS__}
class Donor {public static function parseInstances(v:Dynamic):Dynamic return Main.parse(v);__CALLBACKS__}
class Main {
 public static var events:Array<String>;public static var destroyed:Array<Int>;public static var current:Dynamic;
 static var vars:Map<String,Dynamic>;static var changed:PlayState;static var mode:Int;static var reads:Int;
 public static function registry():Dynamic {events.push("registry");return vars;}
 public static function swap():Void {if(mode>=2){PlayState.instance=changed;vars=["after"=>true];}}
 public static function prop(o:Dynamic,k:String):Dynamic {events.push("read:"+k);var result=Reflect.getProperty(o,k);reads++;if(mode==3&&reads==1)swap();return result;}
 public static function write(o:Dynamic,k:String,v:Dynamic):Void {events.push("write:"+k+":"+Std.string(v));Reflect.setProperty(o,k,v);}
 public static function warn(s:String):Void events.push("warn:"+s);
 public static function play():Dynamic return PlayState.instance;
 public static function target():Dynamic return PlayState.instance!=null?(PlayState.instance.isDead?GameOverSubstate.instance:PlayState.instance):MusicBeatState.getState();
 public static function parse(v:Dynamic):Dynamic {events.push("parse:"+Std.string(v));swap();return 8;}
 static function stateSummary(state:Dynamic):String {
  var items:Array<Dynamic>=state.items;
  return [for(item in items)item==null?"null":Std.isOfType(item,Item)?Std.string(item.id)+":"+Std.string(item.x)+":"+Std.string(item.deep.value)+":"+Std.string(item.map.get("key")):Std.string(item)].join(",")+"/"+[for(item in (cast state.group.members:Array<Dynamic>))item==null?"null":Std.string(item.id)+":"+Std.string(item.x)].join(",");
 }
 static function run(source:Bool,op:Int,path:String,field:Dynamic,index:Int,scenario:Int,maps:Bool,flag:Bool):String {
  events=[];destroyed=[];reads=0;mode=scenario;current=new MusicBeatState(1);var original=new PlayState(100);PlayState.instance=original;changed=new PlayState(500);
  var dead=new MusicBeatState(200);GameOverSubstate.instance=dead;original.isDead=mode==1;
  vars=["tag"=>new Item(900),"invalid"=>{},"alias"=>original.nested];
  var service=new SourcePsychReflection(registry,MusicBeatState.getState,play,target,function(v)return Std.isOfType(v,MusicBeatState),function(n)return null,prop,write,parse,warn);
  var result:Dynamic;
  try {
   if(source) switch(op){case 0:result=Donor.getPropertyFromGroup(path,index,field,maps);case 1:result=Donor.setPropertyFromGroup(path,index,field,"raw",maps,flag);case 2:Donor.addToGroup(path,field,index);result="void";default:Donor.removeFromGroup(path,index,field,flag);result="void";}
   else switch(op){case 0:result=service.getGroup(path,index,field,maps);case 1:result=service.setGroup(path,index,field,"raw",maps,flag);case 2:service.addGroup(path,field,index);result="void";default:service.removeGroup(path,index,field,flag);result="void";}
  } catch(e:Dynamic){result="error";}
  return events.join("|")+"=>"+Std.string(result)+";destroy="+destroyed.join(",")+";original="+stateSummary(original)+";dead="+stateSummary(dead)+";changed="+stateSummary(changed)+";current="+stateSummary(current);
 }
 static function main(){var count=0;for(op in 0...4){var paths=op<2?["items","group","nested.items","alias.items","missing"]:["items","group","nested.items","missing"];var fields:Array<Dynamic>=op<2?["x","deep.value","map.key","rows[0]",0,null]:["tag","invalid","missing",null];for(path in paths)for(field in fields)for(index in [-1,0,1,3])for(mode in 0...4)for(maps in (op<2?[false,true]:[false]))for(flag in [false,true]){var expected=run(true,op,path,field,index,mode,maps,flag),actual=run(false,op,path,field,index,mode,maps,flag);if(expected!=actual)throw op+":"+path+":"+Std.string(field)+":"+index+":"+mode+":"+maps+":"+flag+" expected "+expected+" got "+actual;count++;}}trace("group-reflection-cases:"+count);}
}
'''.replace('__METHODS__',methods.replace('Reflect.getProperty','Main.prop').replace('Reflect.setProperty','Main.write')).replace('__CALLBACKS__','\n'.join(callbacks).replace('Reflect.getProperty','Main.prop'))
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=Path(folder);(work/'Main.hx').write_text(fixture)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'-main','Main','--interp'],capture_output=True,text=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('group-reflection-cases:4864',result.stdout)
