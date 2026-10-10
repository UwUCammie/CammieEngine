"""Pinned Psych lifecycle transactions across tagged object kinds."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from test_source_event_preparation import extract_method
ROOT=Path(__file__).resolve().parents[2]
REV='5c67ced49e5a98535298a6daa3f8f4ec79ac8399'
class PsychSpriteLifecycleTest(unittest.TestCase):
 def test_source_transactions(self):
  def source(file):return subprocess.check_output(['git','-C',str(ROOT.parent/'fnf_sources/FNF-PsychEngine'),'show',REV+':source/psychlua/'+file],text=True)
  lua=source('FunkinLua.hx');animate=source('FlxAnimateFunctions.hx');utils=source('LuaUtils.hx')
  callbacks=[]
  for name,donor in [('makeLuaSprite',lua),('makeAnimatedLuaSprite',lua),('makeFlxAnimateSprite',animate),('addLuaSprite',lua),('removeLuaSprite',lua)]:
   fn=extract_method(donor[donor.index('Lua_helper.add_callback(lua, "'+name+'"'):],'function(')
   callbacks.append(fn.replace('function(', 'public static function '+name+'(',1))
  reset='public static '+extract_method(utils,'function destroyObject(')
  fixture=r'''using StringTools;
class FlxSprite {
 public var id:Int;public var kind:String;public var active(default,set):Bool=false;
 public function new(kind:String){if(Main.armed&&Main.mode==6)throw 'constructor';id=Main.created++;this.kind=kind;Main.log.push('new:'+kind+':'+id);}
 function set_active(v:Bool):Bool {Main.log.push('active:'+id+':'+v);return active=v;}
 public function loadGraphic(g:Dynamic):Void Main.log.push('graphic:'+id+':'+g);
 public function kill():Void {Main.log.push('kill:'+id);Main.mutate(1);}
 public function destroy():Void {Main.log.push('destroy:'+id);Main.mutate(3);}
}
class ModchartSprite extends FlxSprite {public function new(x:Float=0,y:Float=0){super('sprite');Main.log.push('xy:'+x+':'+y);}}
class ModchartAnimateSprite extends FlxSprite {public function new(x:Float=0,y:Float=0){super('animate');Main.log.push('xy:'+x+':'+y);}}
class Scene {
 public var id:String;public var members:Array<Dynamic>=[];public var boyfriend(get,set):Dynamic;var bf:Dynamic;function get_boyfriend():Dynamic {Main.log.push('bfget:'+id);return bf;}function set_boyfriend(v:Dynamic):Dynamic return bf=v;
 public function new(id:String){this.id=id;boyfriend={id:-2};members=[{id:-1},boyfriend];}
 public function add(o:Dynamic):Void {Main.log.push('add:'+id+':'+o.id);if(members.indexOf(o)<0)members.push(o);}
 public function insert(pos:Int,o:Dynamic):Void {Main.log.push('insert:'+id+':'+pos+':'+o.id);members.insert(pos,o);}
 public function remove(o:Dynamic,splice:Bool=false):Void {Main.log.push('remove:'+id+':'+splice+':'+o.id);var i=members.indexOf(o);if(i>=0){if(splice)members.splice(i,1);else members[i]=null;}Main.mutate(2);}
}
class PlayState extends Scene {
 public static var instance:PlayState;public var isDead:Bool;public var variables:Map<String,Dynamic>=[];
 public function new(dead:Bool){super('game');isDead=dead;}
}
class GameOverSubstate {public static var instance:Scene;}
class MusicBeatState {public static function getVariables():Map<String,Dynamic> return PlayState.instance.variables;}
class Paths {
 public static function image(name:String):String {Main.log.push('image:'+name);Main.mutate(5);if(Main.armed&&Main.mode==7)throw 'asset';return name;}
 public static function loadAnimateAtlas(o:Dynamic,name:String):Void {Main.log.push('atlas:'+o.id+':'+name);Main.mutate(5);if(Main.armed&&Main.mode==7)throw 'asset';}
}
class LuaUtils {
 public static function getTargetInstance():Dynamic return PlayState.instance.isDead?GameOverSubstate.instance:PlayState.instance;
 public static function getLowestCharacterGroup():Dynamic return PlayState.instance.members[1];
 public static function getObjectDirectly(tag:String):Dynamic {var o=MusicBeatState.getVariables().get(tag);return o==null?Reflect.getProperty(PlayState.instance,tag):o;}
 public static function loadFrames(o:Dynamic,name:String,kind:String):Void {Main.log.push('frames:'+o.id+':'+name+':'+kind);Main.mutate(5);if(Main.armed&&Main.mode==7)throw 'asset';}
 __RESET__
}
class Oracle {__CALLBACKS__}
class Main {
 public static var mode:Int;public static var armed:Bool=false;public static var created:Int=0;public static var log:Array<String>=[];
 public static function mutate(event:Int):Void {
  if(!armed)return;var h=PlayState.instance;
  if(mode==event){h.variables=[];armed=false;}
  else if(mode==4&&event==2){h.variables.set('ab',{id:999,kind:'replacement'});armed=false;}
 }
 static function snapshot(map:Map<String,Dynamic>):String {var keys=[for(k in map.keys())k];keys.sort(Reflect.compare);return [for(k in keys)k+':'+map.get(k).id].join(',');}
 static function run(actual:Bool,op:Int,initial:Int,dead:Bool,m:Int):String {
  log=[];created=0;mode=m;armed=false;var h=new PlayState(dead);PlayState.instance=h;GameOverSubstate.instance=new Scene('over');h.variables.set('group',new Scene('group'));
  if(initial>0)h.variables.set('ab',initial==4?{id:99,destroy:null}:new FlxSprite(['','sprite','text','animate'][initial]));
  var before=h.variables;log=[];armed=true;var failed=false;
  var registry=function():Dynamic return h.variables;var scene=function():Dynamic return LuaUtils.getTargetInstance();
  try {
   if(actual)switch(op){
    case 0:SourceScriptSpriteLifecycle.create('a.b',registry,scene,function(){var o=new ModchartSprite(4,5);o.loadGraphic(Paths.image('asset'));return o;},true);
    case 1:SourceScriptSpriteLifecycle.create('a.b',registry,scene,function(){var o=new ModchartSprite(4,5);LuaUtils.loadFrames(o,'asset','auto');return o;},false);
    case 2:SourceScriptSpriteLifecycle.createAnimate('a.b',registry,function():Dynamic return h,function(){var o=new ModchartAnimateSprite(4,5);Paths.loadAnimateAtlas(o,'asset');return o;});
    case 3,4:SourceScriptSpriteLifecycle.add('ab',op==3,registry,scene,LuaUtils.getLowestCharacterGroup,function()return h.isDead,function():Dynamic return GameOverSubstate.instance);
    case 5,6,7:SourceScriptSpriteLifecycle.remove('ab',op!=6,op==7?'group':null,LuaUtils.getObjectDirectly,registry,scene);
   }else switch(op){
    case 0:Oracle.makeLuaSprite('a.b','asset',4,5);
    case 1:Oracle.makeAnimatedLuaSprite('a.b','asset',4,5,'auto');
    case 2:Oracle.makeFlxAnimateSprite('a.b',4,5,'asset');
    case 3,4:Oracle.addLuaSprite('ab',op==3);
    case 5,6,7:Oracle.removeLuaSprite('ab',op!=6,op==7?'group':null);
   }
  }catch(e:Dynamic){failed=true;}
  return haxe.Json.stringify({log:log,failed:failed,before:snapshot(before),live:snapshot(h.variables),game:[for(o in h.members)o==null?null:o.id],over:[for(o in GameOverSubstate.instance.members)o==null?null:o.id]});
 }
 static function main(){var n=0;for(op in 0...8)for(initial in 0...5)for(dead in [false,true])for(mode in 0...8){var expected=run(false,op,initial,dead,mode);var actual=run(true,op,initial,dead,mode);if(expected!=actual)throw op+':'+initial+':'+dead+':'+mode+' expected '+expected+' got '+actual;n++;}trace('sprite-transactions:'+n);}
}
'''.replace('__RESET__',reset).replace('__CALLBACKS__','\n'.join(callbacks))
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder);(work/'Main.hx').write_text(fixture)
   for name in ['SourceScriptTextLifecycle','SourceScriptSpriteLifecycle']:(work/(name+'.hx')).write_text((ROOT/'source'/ (name+'.hx')).read_text())
   proc=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','Main','--interp'],capture_output=True,text=True,timeout=60)
   self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
   self.assertIn('sprite-transactions:640',proc.stdout)
