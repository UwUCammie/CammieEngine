"""Pinned Psych instance construction/publication and live scene placement."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,ROOT
from test_source_event_preparation import extract_method

class PsychInstanceLifecycleTest(unittest.TestCase):
 def test_source_instance_transactions(self):
  donor=ROOT.parent/'fnf_sources/FNF-PsychEngine'
  reflect=subprocess.check_output(['git','-C',str(donor),'show','5c67ced49e5a98535298a6daa3f8f4ec79ac8399:source/psychlua/ReflectionFunctions.hx'],text=True)
  callbacks=[]
  for name in ['createInstance','addInstance']:
   start=reflect.index('function(',reflect.index('"'+name+'"'));callbacks.append('public static var '+name+'='+extract_method(reflect[start:],'function(')+';')
  fixture=r'''using StringTools;
class Item {public var id:Int;public function new(id:Int){this.id=id;}}
class Scene {
 public var id:String;public var slots:Array<Dynamic>;public var members(get,never):Array<Dynamic>;public var boyfriend(get,never):Dynamic;var bf:Dynamic;
 public function new(id:String){this.id=id;bf=new Item(10);slots=[new Item(9),bf];}
 function get_members():Array<Dynamic> {Main.events.push("members:"+id);return slots;}
 function get_boyfriend():Dynamic {Main.events.push("boyfriend:"+id);return bf;}
 public function add(o:Dynamic):Void {Main.events.push("add:"+id+":"+o.id);slots.push(o);Main.change();}
 public function insert(pos:Int,o:Dynamic):Void {Main.events.push("insert:"+id+":"+pos+":"+o.id);slots.insert(pos,o);Main.change();}
}
class PlayState extends Scene {
 public static var instance(get,set):PlayState;static var value:PlayState;
 static function get_instance():PlayState {Main.events.push("play");return value;}
 static function set_instance(v:PlayState):PlayState return value=v;
 public var isDead:Bool=false;public function new(id:String){super(id);}
}
class GameOverSubstate {
 public static var instance(get,set):Scene;static var value:Scene;
 static function get_instance():Scene {Main.events.push("over");return value;}
 static function set_instance(v:Scene):Scene return value=v;
}
class MusicBeatState {public static function getVariables():Dynamic return Main.registry();}
class LuaUtils {public static function getTargetInstance():Dynamic return Main.target();public static function getLowestCharacterGroup():Dynamic return Main.anchor();}
class FlxColor {public static var RED:Int=0;}
class FunkinLua {public static function luaTrace(s:String,?a:Bool,?b:Bool,?c:Dynamic):Void Main.warn(s);}
class Donor {public static function parseInstances(v:Dynamic):Dynamic return Main.parse(v);__CALLBACKS__}
class Main {
 public static var events:Array<String>=[];static var mode:Int;static var vars:Map<String,Dynamic>;static var next:Map<String,Dynamic>;
 static var current:Scene;static var changed:PlayState;static var changedOver:Scene;
 public static function change():Void {if(mode>=3){vars=next;PlayState.instance=changed;GameOverSubstate.instance=changedOver;}}
 public static function registry():Dynamic {events.push("registry");if(mode==8)change();return vars;}
 public static function resolve(s:String):Dynamic {events.push("resolve:"+s);if(mode==3)change();return s=="Item"?Item:null;}
 public static function parse(v:Dynamic):Dynamic {events.push("parse:"+Std.string(v));if(mode==4)change();return [new Item(20)];}
 public static function construct(type:Dynamic,args:Array<Dynamic>):Dynamic {events.push("construct:"+args[0].id);if(mode==5)change();if(mode==6)return null;if(mode==7)throw "constructor";return new Item(30);}
 public static function warn(s:String):Void events.push("warn:"+s);
 public static function target():Dynamic {events.push("target");return PlayState.instance==null?current:PlayState.instance.isDead?GameOverSubstate.instance:PlayState.instance;}
 public static function anchor():Dynamic {events.push("anchor");change();return PlayState.instance.slots[0];}
 static function summary(map:Map<String,Dynamic>):String {var keys=[for(k in map.keys())k];keys.sort(Reflect.compare);return [for(k in keys)k+":"+(map.get(k)==null?"null":Std.string(map.get(k).id))].join(",");}
 static function run(source:Bool,add:Bool,name:String,type:String,args:Dynamic,front:Bool,scenario:Int):String {
  mode=scenario;events=[];current=new Scene("current");var original=new PlayState("original");changed=new PlayState("changed");var over=new Scene("over");changedOver=new Scene("changedOver");PlayState.instance=original;GameOverSubstate.instance=over;
  original.isDead=mode==1;if(add&&mode==2)PlayState.instance=null;
  var initial:Map<String,Dynamic>=["member"=>new Item(90),"null"=>null,"existing"=>new Item(91)];vars=initial;next=["replacement"=>new Item(92)];if(!add&&mode==1)vars.set("ab",null);if(!add&&mode==2)vars.set("ab",new Item(93));
  events=[];var result:Dynamic;
  try {
   if(add){if(source)Donor.addInstance(name,front);else SourceScriptInstances.add(name,front,registry,target,function():Dynamic return PlayState.instance,function():Dynamic return GameOverSubstate.instance,anchor,warn);result="void";}
   else result=source?Donor.createInstance(name,type,args):SourceScriptInstances.create(name,type,args,registry,resolve,parse,construct,warn);
  } catch(e:Dynamic){result="error";}
  return events.join("|")+"=>"+Std.string(result)+";initial="+summary(initial)+";next="+summary(next)+";scenes="+[for(s in [original,over,changed,changedOver,current])s.id+":"+[for(o in s.slots)o.id].join(",")].join("/");
 }
 static function main(){var count=0;var argumentSets:Array<Dynamic>=[null,[],["raw"],"bad"];
  for(name in [" a.b ","existing","",null])for(type in ["Item","missing"])for(args in argumentSets)for(mode in 0...9){var e=run(true,false,name,type,args,false,mode),a=run(false,false,name,type,args,false,mode);if(e!=a)throw "create:"+name+":"+type+":"+Std.string(args)+":"+mode+" expected "+e+" actual "+a;count++;}
  for(name in ["member","null","missing"," member "])for(front in [false,true])for(mode in 0...9){var e=run(true,true,name,"",null,front,mode),a=run(false,true,name,"",null,front,mode);if(e!=a)throw "add:"+name+":"+front+":"+mode+" expected "+e+" actual "+a;count++;}
  trace("instance-lifecycle-cases:"+count);
 }
}
'''.replace('__CALLBACKS__','\n'.join(callbacks).replace('Type.resolveClass','Main.resolve').replace('Type.createInstance','Main.construct'))
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=Path(folder);(work/'Main.hx').write_text(fixture)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'-main','Main','--interp'],capture_output=True,text=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('instance-lifecycle-cases:360',result.stdout)
