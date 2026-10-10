"""Compare native custom-substate lifecycle and public methods with pinned Psych."""
from pathlib import Path
import re,subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,ROOT

class PsychCustomSubstateSourceTest(unittest.TestCase):
 def test_source_lifecycle_and_live_public_api(self):
  source=subprocess.check_output(['git','-C',str(ROOT.parent/'fnf_sources/FNF-PsychEngine'),'show','5c67ced49e5a98535298a6daa3f8f4ec79ac8399:source/psychlua/CustomSubstate.hx'],text=True)
  source=re.sub(r'\bCustomSubstate\b','Donor',source.replace('package psychlua;','package;\nimport flixel.FlxG;'))
  files={
   'Donor.hx':source,
   'flixel/FlxObject.hx':'package flixel; class FlxObject {public function new(){}}',
   'flixel/FlxG.hx':"package flixel; class FlxG {public static var camera={followLerp:1.0};public static var sound:{music:Dynamic}={music:null};public static var cameras:{list:Array<Dynamic>}={list:['game','hud']};}",
   'PsychRuntimeBindings.hx': "class PsychRuntimeBindings {public static function publish(h:PlayState,n:String,v:Dynamic,f:String):Void h.setAllHaxeVar(n,v);public static function dispatch(h:PlayState,n:String,a:Array<Dynamic>):Void h.callAllHScript(n,a);}",
   'MusicBeatState.hx':'class MusicBeatState {public static var vars:Map<String,Dynamic>=[];public static function getVariables():Map<String,Dynamic>{Main.log.push("registry");return vars;}}',
   'PsychMusicBeatSubstate.hx':'class PsychMusicBeatSubstate extends MusicBeatSubstate {public function new(sourceTiming:Bool=true){super();}}',
'MusicBeatSubstate.hx':r"""
class MusicBeatSubstate {
 public var bgColor:Int;public var cameras:Array<Dynamic>;
 public function new(){Main.log.push('superNew');}
 public function create():Void Main.log.push('superCreate');
 public function update(e:Float):Void Main.log.push('superUpdate:'+e);
 public function destroy():Void Main.log.push('superDestroy');
 public function add(o:Dynamic):Dynamic {Main.log.push('add');return o;}
 public function insert(p:Int,o:Dynamic):Dynamic {Main.log.push('insert:'+p);return o;}
}
""",
   'PlayState.hx':r"""
class PlayState {
 public static var instance:PlayState;
 public var id:String;public var persistentUpdate:Bool=true;public var persistentDraw:Bool=false;public var paused:Bool=false;public var vocals:Dynamic;
 public function new(id:String){this.id=id;vocals={pause:function(){Main.log.push('vocals:'+id);}};}
 public function pauseVocals():Void vocals.pause();
 public function setOnHScript(n:String,v:Dynamic):Void {Main.log.push('set:'+id+':'+n+':'+(n=='customSubstate'?(v==null?'null':'instance'):Std.string(v)));}
 public function setAllHaxeVar(n:String,v:Dynamic):Void setOnHScript(n,v);
 public function callOnScripts(n:String,a:Array<Dynamic>):Void {Main.log.push('call:'+id+':'+n+':'+a.join(','));if(Main.swap)instance=Main.other;}
 public function callAllHScript(n:String,a:Array<Dynamic>):Void callOnScripts(n,a);
 public function openSubState(s:Dynamic):Void {Main.log.push('open:'+id);Main.opened=s;}
 public function compatOpenCustomSubstate(n:String,p:Bool,s:Bool):Void openSubState(new PsychCustomSubstate(n));
 public function closeSubState():Void Main.log.push('close:'+id);
 public function psychCustomSubstateCreate(s:PsychCustomSubstate):Void{}
 public function psychCustomSubstateCreatePost(s:PsychCustomSubstate):Void{}
 public function psychCustomSubstateUpdate(s:PsychCustomSubstate,e:Float):Void{}
 public function psychCustomSubstateUpdatePost(s:PsychCustomSubstate,e:Float):Void{}
 public function psychCustomSubstateDestroy(s:PsychCustomSubstate):Void{}
 public function psychCustomSubstateFinished(s:PsychCustomSubstate):Void{}
}
""",
   'Main.hx':r"""
import flixel.FlxG;
class Main {
 public static var log:Array<String>;public static var other:PlayState;public static var swap:Bool;public static var opened:Dynamic;
 static function run(donor:Bool,op:Int,variant:Int,reentry:Bool):String {
  log=[];swap=reentry;opened=null;PlayState.instance=new PlayState('first');other=new PlayState('second');
  Donor.instance=null;Donor.name='unnamed';PsychCustomSubstate.instance=null;PsychCustomSubstate.name='unnamed';
  FlxG.camera.followLerp=1;FlxG.sound.music=variant%2==0?null:{pause:function(){log.push('music');if(swap)PlayState.instance=other;}};
  MusicBeatState.vars=['object'=>new flixel.FlxObject(),'invalid'=>{}];
  var api:Dynamic=donor?Donor:PsychCustomSubstate;var obj:Dynamic=null;var result:Dynamic=null;
  try {
   if(op==0){Reflect.callMethod(api,Reflect.field(api,'openCustomSubstate'),[variant==0?null:'first',variant>=2]);}
   else {
    obj=Type.createInstance(api,['first']);
    if(variant!=0)obj.create();
    if(variant>=2)Reflect.setField(api,'name','mutated');
    switch(op){
     case 1:obj.update(.25);
     case 2:obj.destroy();
     case 3:result=Reflect.callMethod(api,Reflect.field(api,'closeCustomSubstate'),[]);
     case 4:result=Reflect.callMethod(api,Reflect.field(api,'insertToCustomSubstate'),['object',variant-2]);
     case 5:result=Reflect.callMethod(api,Reflect.field(api,'insertToCustomSubstate'),['missing']);
     case 6:result=Reflect.callMethod(api,Reflect.field(api,'insertToCustomSubstate'),['invalid']);
    }
   }
  }catch(e:Dynamic){result='error';}
  return log.join('|')+' => '+Std.string(result)+';name='+Reflect.field(api,'name')+';instance='+(Reflect.field(api,'instance')!=null)+';paused='+PlayState.instance.paused+';update='+PlayState.instance.persistentUpdate+';draw='+PlayState.instance.persistentDraw+';lerp='+FlxG.camera.followLerp;
 }
 static function main(){var count=0;for(op in 0...7)for(v in 0...4)for(swap in [false,true]){var expected=run(true,op,v,swap),actual=run(false,op,v,swap);if(expected!=actual)throw op+':'+v+':'+swap+' expected '+expected+' got '+actual;count++;}trace('custom-substate-source:'+count);}
}
"""}
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=Path(folder)
   for name,data in files.items():
    p=work/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data,encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'-main','Main','--interp'],capture_output=True,text=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('custom-substate-source:56',result.stdout)
