"""Pinned BaseStage live-state, PlayState-instance and static-provider comparison."""
import re
import os
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_psych_compiled_stage_runtime import ROOT, FLIXEL_ARGS, haxe_env

STATE = """class Scene {
 public var label:String; public var paused:Bool=false; public var inCutscene:Bool=false;
 public var canPause:Bool=true; public var songName:String;
 public var stages:Array<Dynamic>=[];
 public var members:Array<Dynamic>=[]; public var variables:Registry=new Registry();
 public var boyfriend:Dynamic; public var dad:Dynamic; public var gf:Dynamic;
 public var boyfriendGroup:Dynamic; public var dadGroup:Dynamic; public var gfGroup:Dynamic;
 public var unspawnNotes:Array<Dynamic>=[]; public var camGame:Dynamic; public var camHUD:Dynamic;
 public var camOther:Dynamic; public var camFollow:Dynamic;
 public var defaultCamZoom:Float=.5;
 public function new(label:String) {
  this.label=label;songName='name:'+label;
  variables.set('item','map:'+label);
  boyfriend={label:'bf:'+label};dad={label:'dad:'+label};gf={label:'gf:'+label};
  boyfriendGroup={};dadGroup={};gfGroup={};camGame={};camHUD={};camOther={};camFollow={};
  members=[gfGroup,dadGroup,boyfriendGroup];
 }
 public function getStageObject(name:String):Dynamic return 'wrong-direct';
 public function add(value:Dynamic):Dynamic {members.push(value);return value;}
 public function insert(index:Int,value:Dynamic):Dynamic {members.insert(index,value);return value;}
 public function remove(value:Dynamic,splice:Bool=false):Dynamic {members.remove(value);return value;}
}
"""
PLAY = """package states; import Scene;
class PlayState extends Scene {
 public static var instance:PlayState;public static var SONG:Dynamic={gfVersion:''};
 public static var isStoryMode:Bool=true;public static var seenCutscene:Bool=true;
 public var startCallback:Dynamic;public var endCallback:Dynamic;
 public var calls:Array<String>=[];
 public function new(label:String) super(label);
 public function setStartCallback(value:Dynamic):Void startCallback=value;
 public function setEndCallback(value:Dynamic):Void endCallback=value;
 public function startCountdown():Bool {calls.push('start:'+label);return true;}
 public function endSong():Bool {calls.push('end:'+label);return true;}
 public function moveCameraSection():Void calls.push('section:'+label);
 public function moveCamera(dad:Bool):Void calls.push('camera:'+label+':'+dad);
}
"""
MAIN = """import states.PlayState; import flixel.FlxBasic;
@:access(backend.BaseStage)
@:access(PsychBaseStageCompat)
class Main {
 static function main() {
  var a=new PlayState('A'), b=new PlayState('B'), menu=new Scene('menu');
  FlxG.state=a;PlayState.instance=b;
  STAGE_SETUP
  var log:Array<String>=[];
  for(scene in [cast(a,Scene),menu,cast(b,Scene)]) {
   FlxG.state=scene;
   log.push('state:'+(stage.game==scene)+':'+stage.onPlayState+':'+stage.songName);
   stage.inCutscene=true;stage.canPause=false;
   log.push('fields:'+scene.inCutscene+':'+scene.canPause+':'+stage.isStoryMode+':'+stage.seenCutscene);
   log.push('zoom:'+stage.set_defaultCamZoom(5)+':'+scene.defaultCamZoom);
   log.push('map:'+stage.getStageObject('item')+':'+stage.getStageObject('missing'));
   log.push('actors:'+(stage.boyfriend==scene.boyfriend)+':'+(stage.dadGroup==scene.dadGroup)+':'+(stage.gfGroup==scene.gfGroup));
   log.push('cameras:'+(stage.camHUD==scene.camHUD)+':'+(stage.camFollow==scene.camFollow));
   var object=new FlxBasic();
   log.push('add:'+(stage.add(object)==object)+':'+(scene.members.indexOf(object)>=0));
   log.push('remove:'+(stage.remove(object,true)==object)+':'+(scene.members.indexOf(object)<0));
   stage.addBehindBF(object);
   log.push('behind:'+(scene.members.indexOf(object)==scene.members.indexOf(scene.boyfriendGroup)-1));
   stage.remove(object,true);
   PlayState.instance.startCallback=null;PlayState.instance.endCallback=null;
   var fn=function() {};
   stage.setStartCallback(fn);stage.setEndCallback(fn);
   log.push('callbacks:'+(PlayState.instance.startCallback==fn)+':'+(PlayState.instance.endCallback==fn));
   log.push('returns:'+stage.startCountdown()+':'+stage.endSong());
   stage.moveCameraSection();stage.moveCamera(true);
   log.push('calls:'+PlayState.instance.calls.join(','));PlayState.instance.calls=[];
   stage.setDefaultGF('new-gf');log.push('gf:'+PlayState.SONG.gfVersion);
   PlayState.SONG.gfVersion='kept';stage.setDefaultGF('other');log.push('kept:'+PlayState.SONG.gfVersion);
   PlayState.SONG={gfVersion:''};PlayState.instance=a;
  }
  Sys.println(log.join('|'));
 }
}
"""

class PsychStageContextTest(unittest.TestCase):
 def test_live_state_instance_and_static_roots_match_pinned_source(self):
  donor=ROOT.parent/'fnf_sources/FNF-PsychEngine/source/backend/BaseStage.hx'
  if not donor.is_file(): self.skipTest('pinned Psych source not mounted')
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
   base=Path(directory);outputs=[]
   for native in [True,False]:
    folder=base/('oracle' if native else 'actual');folder.mkdir();(folder/'states').mkdir()
    (folder/'Registry.hx').write_text('class Registry {var values:Map<String,Dynamic>=new Map();public function new() {} public function set(key:String,value:Dynamic):Void values.set(key,value); public function get(key:String):Dynamic return values.get(key);}',encoding='utf-8')
    (folder/'Scene.hx').write_text(STATE,encoding='utf-8');(folder/'states/PlayState.hx').write_text(PLAY,encoding='utf-8')
    (folder/'FlxG.hx').write_text("class FlxG {public static var state:Dynamic;public static var log={error:function(message:String) {throw message;}};}",encoding='utf-8')
    if native:
     (folder/'flixel').mkdir();(folder/'backend').mkdir()
     (folder/'flixel/FlxBasic.hx').write_text('package flixel; class FlxBasic {public function new() {} public function destroy():Void {}}',encoding='utf-8')
     source=re.sub(r'^import .*?;\s*','',donor.read_text(encoding='utf-8'),flags=re.M)
     source=source.replace('package backend;',"""package backend;
import flixel.FlxBasic; import states.PlayState; import FlxG;
typedef FlxObject=Dynamic;typedef FlxSubState=Dynamic;typedef FlxSpriteGroup=Dynamic;
typedef FlxCamera=Dynamic;typedef Note=Dynamic;typedef Character=Dynamic;typedef EventNote=Dynamic;
""")
     (folder/'backend/BaseStage.hx').write_text(source,encoding='utf-8')
     setup='var stage=new backend.BaseStage();'
     main=MAIN.replace('@:access(PsychBaseStageCompat)','')
    else:
     setup="""var stage=new PsychBaseStageCompat(a);
  stage.attachContext(new SourceStageContext(function() return FlxG.state,function() return PlayState.instance,
   function(value) return Std.isOfType(value,PlayState),function(name) return Reflect.field(PlayState,name)));
  stage.beginPostCreate();"""
     main=MAIN.replace('@:access(backend.BaseStage)','')
    (folder/'Main.hx').write_text(main.replace('STAGE_SETUP',setup),encoding='utf-8')
    command=[*HAXE_COMMAND]
    if not native: command+=['-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-ex/git/src'),*FLIXEL_ARGS]
    args=['-cp',str(folder),'--run','Main']
    if native: args=['-cp',str(folder),'-main','Main','-neko',str(folder/'oracle.n')]
    result=subprocess.run(command+args,cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=90)
    self.assertEqual(result.returncode,0,result.stdout+result.stderr)
    if native:
     result=subprocess.run([str(ROOT/('.tools/neko/neko.exe' if os.name=='nt' else '.tools/neko/neko')),str(folder/'oracle.n')],cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=30)
    self.assertEqual(result.returncode,0,str(native)+': '+result.stdout+result.stderr);outputs.append(result.stdout)
   self.assertEqual(outputs[1],outputs[0])

 def test_cached_actor_views_and_failed_creation_keep_state_ownership(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
   base=Path(directory);owner=base/'owner';module=owner/'source/demo/Broken.hx';module.parent.mkdir(parents=True)
   module.write_text("""package demo;import backend.BaseStage;import flixel.FlxBasic;
class Broken extends BaseStage {override public function create():Void {add(new FlxBasic());throw 'failed create';}}
""",encoding='utf-8')
   (base/'Main.hx').write_text("""import flixel.FlxBasic;import flixel.math.FlxPoint;
class Host {
 public var stages:Array<Dynamic>=[];public var members:Array<Dynamic>=[];public var dad:Dynamic;
 public var lastAdded:Dynamic;
 public function new() dad={x:0.0,y:0.0,scrollFactor:new FlxPoint(1,1),cameras:null};
 public function add(value:Dynamic):Dynamic {lastAdded=value;members.push(value);return value;}
 public function remove(value:Dynamic,splice:Bool=false):Dynamic {members.remove(value);return value;}
}
class Main {
 static function main() {
  var a=new Host(),b=new Host();var current=a;
  var context=new SourceStageContext(function() return current,function() return a,function(value) return value==a,function(name) return null);
  var view=new PsychBaseStageCompat(a);view.attachContext(context);
  var first=view.dadGroup;current=b;var second=view.dadGroup;
  if(first==second||first.actor()!=a.dad||second.actor()!=b.dad) throw 'actor views retargeted across states';
  current=a;if(view.dadGroup!=first) throw 'returning to a state lost its native group identity';
  current=b;
  var bindings:Map<String,Dynamic>=['flixel.FlxBasic'=>FlxBasic];
  var runtime=new PsychCompiledStageRuntime(Sys.args()[0],'demo.Broken',a,bindings,null,context);
  if(runtime.create()) throw 'failed constructor was accepted';
  if(b.stages.length!=0||b.members.length!=0||b.lastAdded==null||b.lastAdded.exists) throw 'failed constructor did not clean its active scene';
  if(a.stages.length!=0||a.members.length!=0||a.lastAdded!=null) throw 'failed constructor changed its asset owner scene';
  view.destroy();
 }
}
""",encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(base),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-ex/git/src'),*FLIXEL_ARGS,'--run','Main',str(owner)],cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=90)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__': unittest.main()
