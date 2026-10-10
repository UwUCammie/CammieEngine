"""Pinned public Psych property/method callbacks and their ordered native boundaries."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,ROOT
from test_source_event_preparation import extract_method

class PsychPublicReflectionTest(unittest.TestCase):
 def test_property_and_method_contracts(self):
  donor=ROOT.parent/'fnf_sources/FNF-PsychEngine'
  def source(path):return subprocess.check_output(['git','-C',str(donor),'show','5c67ced49e5a98535298a6daa3f8f4ec79ac8399:'+path],text=True)
  reflect=source('source/psychlua/ReflectionFunctions.hx');utils=source('source/psychlua/LuaUtils.hx')
  names=['getProperty','setProperty','getPropertyFromClass','setPropertyFromClass','callMethod','callMethodFromClass']
  callbacks=[]
  for name in names:
   start=reflect.index('function(',reflect.index('"'+name+'"'));callbacks.append('public static var '+name+'='+extract_method(reflect[start:],'function(')+';')
  text_source=source('source/psychlua/TextFunctions.hx')
  start=text_source.index('function(',text_source.index('"getTextSize"'))
  lookup=extract_method(text_source[start:],'function(')
  lookup=lookup[:lookup.index('if(obj != null)')]+'return obj;}'
  callbacks.append('public static var object='+lookup.replace('obj:FlxText','obj:Dynamic')+';')
  methods='\n'.join('public static '+extract_method(utils,'function '+name+'(') for name in ['getVarInArray','setVarInArray','getPropertyLoop','getObjectDirectly','getTargetInstance','isMap'])
  call='public static '+extract_method(reflect,'function callMethodFromObject(')
  fixture=r'''import haxe.Constraints.Function;
using StringTools;
class MusicBeatState {
 public var health:Dynamic=5;public var nested:Dynamic;public var rows:Dynamic=[[11]];public var map:Map<String,Dynamic>=["key"=>3];
 public function new(){nested={value:7,rows:[[13]],plus:function(?n:Int=2)return n+20};}
 public function plus(?n:Int=2):Int return n+10;
 public static function getState():Dynamic {Main.events.push("state");return Main.current;}
 public static function getVariables():Dynamic return Main.registry();
}
class PlayState extends MusicBeatState {public static var instance:PlayState;public var isDead:Bool=false;public function new(){super();}}
class GameOverSubstate {public static var instance:Dynamic;}
class Fixture {public static var nested:Dynamic;public static function plus(?n:Int=2):Int return n+30;}
class FlxColor {public static var RED:Int=0;}
class FunkinLua {public static function luaTrace(s:String,?a:Bool,?b:Bool,?c:Dynamic):Void Main.warn(s);}
class LuaUtils {__METHODS__}
class Donor {public static function parseInstances(v:Dynamic):Dynamic return Main.parse(v);__CALLBACKS__ __CALL__}
class Main {
 public static var events:Array<String>;public static var current:Dynamic;static var vars:Map<String,Dynamic>;static var after:Map<String,Dynamic>;
 public static function registry():Dynamic {events.push("registry");return vars;}
 public static function prop(o:Dynamic,k:String):Dynamic {events.push("read:"+k);return Reflect.getProperty(o,k);}
 public static function write(o:Dynamic,k:String,v:Dynamic):Void {events.push("write:"+k+":"+Std.string(v));Reflect.setProperty(o,k,v);}
 public static function warn(s:String):Void events.push("warn:"+s);
 public static function resolve(s:String):Dynamic {events.push("class:"+s);return s=="Fixture"?Fixture:null;}
 public static function play():Dynamic {return PlayState.instance;}
 public static function target():Dynamic return PlayState.instance!=null?(PlayState.instance.isDead?GameOverSubstate.instance:PlayState.instance):MusicBeatState.getState();
 public static function parse(v:Dynamic):Dynamic {events.push("parse:"+Std.string(v));vars=after;return v=="raw"?"parsed":v;}
 static function run(source:Bool,op:Int,path:String,mode:Int,maps:Bool,instances:Bool):String {
  events=[];current=new MusicBeatState();PlayState.instance=new PlayState();PlayState.instance.isDead=mode==3;
  GameOverSubstate.instance={health:40,nested:{value:41},rows:[[42]]};Fixture.nested={value:50,rows:[[51]]};
  vars=[];after=["after"=>true];
  if(mode>0){vars.set("health",mode==2?null:19);vars.set("nested",mode==2?null:{value:22,rows:[[23]],plus:function(?n:Int=2)return n+40});vars.set("rows",[[29]]);vars.set("fn",function(?n:Int=2)return n+60);}
  if(mode==2)PlayState.instance=null;
  var service=new SourcePsychReflection(registry,MusicBeatState.getState,play,target,function(v)return Std.isOfType(v,MusicBeatState),resolve,prop,write,parse,warn);
  var result:Dynamic;var type=instances?"missing":"Fixture";
  try {result=source?switch(op){case 0:Donor.getProperty(path,maps);case 1:Donor.setProperty(path,"raw",maps,instances);case 2:Donor.getPropertyFromClass(type,path,maps);case 3:Donor.setPropertyFromClass(type,path,"raw",maps,instances);case 4:Donor.callMethod(path,instances?null:[3]);case 6:Donor.object(path);default:Donor.callMethodFromClass(type,path,instances?null:[3]);}:switch(op){case 0:service.get(path,maps);case 1:service.set(path,"raw",maps,instances);case 2:service.getClass(type,path,maps);case 3:service.setClass(type,path,"raw",maps,instances);case 4:service.call(path,instances?null:[3]);case 6:service.object(path);default:service.callClass(type,path,instances?null:[3]);};}catch(e:Dynamic){result="error";}
  return events.join("|")+"=>"+Std.string(result)+";state="+Std.string(current.health)+";play="+(PlayState.instance==null?"null":Std.string(PlayState.instance.health))+";health="+Std.string(vars.get("health"));
 }
 static function main(){var count=0;for(op in 0...7){var paths=(op<4||op==6)?["health","nested.value","nested.rows[0][0]","rows[0][0]","this.nested.value","game.nested.value","instance.nested.value","map.key","missing.child","",null]:["plus","nested.plus","fn"," fn ","missing","nested.missing","",null];for(path in paths)for(mode in 0...4)for(maps in [false,true])for(instances in [false,true]){var expected=run(true,op,path,mode,maps,instances),actual=run(false,op,path,mode,maps,instances);if(expected!=actual)throw op+":"+path+":"+mode+":"+maps+":"+instances+" expected "+expected+" got "+actual;count++;}}trace("public-reflection-cases:"+count);}
}
'''.replace('__METHODS__',methods.replace('Reflect.getProperty','Main.prop').replace('Reflect.setProperty','Main.write')).replace('__CALLBACKS__','\n'.join(callbacks).replace('Type.resolveClass','Main.resolve')).replace('__CALL__',call)
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=Path(folder);(work/'Main.hx').write_text(fixture)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'-main','Main','--interp'],capture_output=True,text=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('public-reflection-cases:1136',result.stdout)

 def test_inventory_records_shared_public_binding_location(self):
  import audit_script_api_coverage as audit
  names={'getProperty','setProperty','getPropertyFromClass','setPropertyFromClass','callMethod','callMethodFromClass'}
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=Path(folder);(work/'source').mkdir()
   (work/'source/PsychPropertyBindings.hx').write_text((ROOT/'source/PsychPropertyBindings.hx').read_text())
   direct,_,_,_=audit._engine_inventory(work,names)
   for name in names:
    self.assertTrue(direct.get(name),name)
