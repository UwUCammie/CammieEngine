"""Compare modern text transactions with pinned Psych source callbacks."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from test_source_event_preparation import extract_method
ROOT=Path(__file__).resolve().parents[2]
REV='5c67ced49e5a98535298a6daa3f8f4ec79ac8399'

class PsychTextLifecycleTest(unittest.TestCase):
 def test_source_transactions(self):
  def source(file):return subprocess.check_output(['git','-C',str(ROOT.parent/'fnf_sources/FNF-PsychEngine'),'show',REV+':'+file],text=True)
  donor=source('source/psychlua/TextFunctions.hx');utils=source('source/psychlua/LuaUtils.hx')
  callbacks=[]
  for name in ['makeLuaText','addLuaText','removeLuaText']:
   fn=extract_method(donor[donor.index('Lua_helper.add_callback(lua, "'+name+'"'):],'function(')
   callbacks.append(fn.replace('function(', 'public static function '+name+'(',1))
  reset='public static '+extract_method(utils,'function destroyObject(')
  bind=extract_method((ROOT/'source/PsychSourceBindings.hx').read_text(),'function installTextLifecycle(')
  defaults=(ROOT/'source/SourceTextDefaults.hx').read_text();defaults=defaults[defaults.index('class SourceTextDefaults'):]
  def constants(s):return s.replace('FlxTextBorderStyle.OUTLINE','"outline"').replace(', CENTER,',', "center",').replace(', OUTLINE,',', "outline",')
  fixture=r'''using StringTools;
class FlxCamera {public function new(){}}
class FlxColor {public static var WHITE:Int=-1;public static var BLACK:Int=0xff000000;}
class Scroll {public function new(){} public function set():Void Main.log.push('scroll');}
class FlxText {
 public var id:Int;public var scrollFactor=new Scroll();public var cameras:Array<FlxCamera>;public var borderSize:Float;
 public function new(x:Float,y:Float,width:Float,text:String,size:Int){id=Main.created++;Main.log.push('new:'+id+':'+x+':'+y+':'+width+':'+text+':'+size);}
 public function setFormat(font:String,size:Int,color:Int,alignment:String,style:String,border:Int):Void Main.log.push('format:'+font+':'+size+':'+color+':'+alignment+':'+style+':'+border);
 public function destroy():Void {Main.log.push('destroy:'+id);Main.mutate(1);}
}
typedef FlxSprite=FlxText;
class Scene {
 public var id:String;public var members:Array<Dynamic>=[];
 public function new(id:String)this.id=id;
 public function add(o:Dynamic):Void {Main.log.push('add:'+id+':'+o.id);if(members.indexOf(o)<0)members.push(o);Main.mutate(2);}
 public function remove(o:Dynamic,splice:Bool):Void {Main.log.push('remove:'+id+':'+o.id+':'+splice);members.remove(o);Main.mutate(3);}
}
class Host extends Scene {
 public var nightmareVisionLegacyFieldCameras:Bool=false;
 public var psychScriptVariables:Map<String,Dynamic>=[];public var camHUD=new FlxCamera();public var compatCustomSubstate:Scene;
 public function new(){super('game');}
 public function historicalPropertyInstance():Dynamic return Main.dead?Main.over:this;
 public function compatRemoveObject(tag:String,destroy:Bool):Void Main.log.push('generic:'+tag+':'+destroy);
}
class PlayState {public static var instance:Host;}
class CustomSubstate {public static var instance(get,never):Scene;static function get_instance():Scene return PlayState.instance.compatCustomSubstate;}
class MusicBeatState {public static function getVariables():Map<String,Dynamic> return PlayState.instance.psychScriptVariables;}
class Paths {public static function font(s:String):String return 'owner/fonts/'+s;}
class PsychFontPath {public static function resolve(s:String,owner:String):String return 'owner/fonts/'+s;}
class LuaUtils {public static function getTargetInstance():Dynamic return PlayState.instance.historicalPropertyInstance();__RESET__}
class Oracle {__CALLBACKS__}
__DEFAULTS__
class Actual {
 var host:Host;var ownerRoot='owner';public var variables:Map<String,Dynamic>=[];
 public function new(host:Host){this.host=host;installTextLifecycle(variables);}
 __BIND__
}
class Main {
 public static var log:Array<String>=[];public static var created:Int=0;public static var mode:Int=0;public static var trigger:Int=0;public static var armed:Bool=false;public static var dead:Bool=false;
 public static var over:Scene;public static var custom:Scene;
 public static function mutate(at:Int):Void {
  if(!armed||at!=trigger)return;armed=false;var h=PlayState.instance;
  switch(mode){case 1:h.psychScriptVariables=new Map();case 2:h.psychScriptVariables.set('ab',{id:999});case 3:dead=!dead;case 4:h.compatCustomSubstate=custom;default:}
 }
 static function snapshot(map:Map<String,Dynamic>):String {var keys=[for(k in map.keys())k];keys.sort(Reflect.compare);return [for(k in keys)k+':'+map.get(k).id].join(',');}
 static function run(actual:Bool,operation:Int,kind:Int,location:Int,m:Int,t:Int):String {
  log=[];created=0;mode=m;trigger=t;armed=false;dead=location==1;over=new Scene('over');custom=new Scene('custom');var h=new Host();PlayState.instance=h;if(location==2)h.compatCustomSubstate=custom;
  var old=h.psychScriptVariables;
  if(kind==1)old.set('ab',new FlxText(0,0,0,'old',16));
  if(kind==2)old.set('ab',{id:88,destroy:null});
  if(kind==3)old.set('ab',null);
  log=[];armed=true;var error=false;
  try {
   if(actual){var api=new Actual(h);switch(operation){case 0:Reflect.callMethod(null,api.variables.get('makeLuaText'),['a.b','hello',123,4,5]);case 1:Reflect.callMethod(null,api.variables.get('addLuaText'),['ab']);case 2:Reflect.callMethod(null,api.variables.get('removeLuaText'),['ab',false]);case 3:Reflect.callMethod(null,api.variables.get('removeLuaText'),['ab',true]);}}
   else switch(operation){case 0:Oracle.makeLuaText('a.b','hello',123,4,5);case 1:Oracle.addLuaText('ab');case 2:Oracle.removeLuaText('ab',false);case 3:Oracle.removeLuaText('ab',true);}
  }catch(e:Dynamic){error=true;}
  return haxe.Json.stringify({log:log,old:snapshot(old),live:snapshot(h.psychScriptVariables),error:error,dead:dead,custom:h.compatCustomSubstate!=null,game:[for(x in h.members)x.id],over:[for(x in over.members)x.id],sub:[for(x in custom.members)x.id]});
 }
 static function main(){var historical=new Host();historical.nightmareVisionLegacyFieldCameras=true;if(new Actual(historical).variables.iterator().hasNext())throw 'historical callbacks must remain owned by historical adapter';var count=0;for(op in 0...4)for(kind in 0...4)for(location in 0...3)for(mode in 0...5)for(trigger in 1...4){var expected=run(false,op,kind,location,mode,trigger);var got=run(true,op,kind,location,mode,trigger);if(expected!=got)throw [op,kind,location,mode,trigger]+' expected '+expected+' got '+got;count++;}trace('psych-text-transactions:'+count);}
}
'''.replace('__RESET__',reset).replace('__CALLBACKS__',constants('\n'.join(callbacks))).replace('__DEFAULTS__',constants(defaults)).replace('__BIND__',bind)
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder);(work/'Main.hx').write_text(fixture)
   (work/'SourceScriptTextLifecycle.hx').write_text((ROOT/'source/SourceScriptTextLifecycle.hx').read_text())
   proc=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','Main','--interp'],capture_output=True,text=True,timeout=60)
   self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
   self.assertIn('psych-text-transactions:720',proc.stdout)
