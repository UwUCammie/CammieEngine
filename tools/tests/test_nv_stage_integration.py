"""Connected real Stage/Class/script/native-container integration."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from nv_stage_fixture_support import nv_stage_fixture_files
ROOT=Path(__file__).resolve().parents[2]

def integration_files():
 files=nv_stage_fixture_files()
 paths=files['NightmareVisionPaths.hx']
 paths=paths.replace('class NightmareVisionPaths {','class NightmareVisionPaths implements NightmareVisionScriptPaths {public var scriptInstances(default,null):Map<String,NightmareVisionScriptModule>=[];')
 paths=paths.replace('public var scriptExtensions=', 'public var scriptExtensions(default,null)=')
 paths=paths.replace('getPath(p:String,?a:Dynamic,?b:Bool)', 'getPath(p:String,?a:String,b:Bool=false)')
 files['NightmareVisionPaths.hx']=paths
 files['NightmareVisionStageData.hx']='class NightmareVisionStageData {public static function load(r:String,n:String):Dynamic return StageIO.current.data;public static function getLegacyStageFile(r:String,n:String):Dynamic return n=="missing"?null:StageIO.current.data;public static function getLegacyTemplateStageFile():Dynamic return StageIO.current.data;public static function getTemplateStageFile():Dynamic return StageIO.current.data;}'
 files['HxcCompatRuntime.hx']='class HxcCompatRuntime {public static function getZIndex(o:Dynamic):Int return o.zIndex;public static function setZIndex(o:Dynamic,v:Int):Int return o.zIndex=v;}'
 character=files['Character.hx'].replace('class Character extends flixel.FlxSprite {','class Character extends animate.FlxAnimate {public function enableNightmareVisionStageSprite():Void {}public function loadAtlas(p:String):Void {}public function addAnimByPrefix(n:String,p:String,f:Int=24,l:Bool=true,x:Bool=false,y:Bool=false):Void {}public function addAnimByIndices(n:String,p:String,i:Array<Int>,f:Int=24,l:Bool=true,x:Bool=false,y:Bool=false):Void {}public function addOffset(n:String,x:Float,y:Float):Void {}public function playAnim(n:String):Void {}')
 files['Character.hx']=character
 from test_source_event_preparation import extract_method
 native=(ROOT/'.haxelib/flixel/6,1,2/flixel/group/FlxGroup.hx').read_text()
 insert=extract_method(native,'public function insert(')
 files['flixel/group/FlxGroup.hx']=files['flixel/group/FlxGroup.hx'].replace('public function onMemberAdd(',insert+'public function onMemberAdd(')
 return files

class StageIntegrationTest(unittest.TestCase):
 def run_haxe(self,main,cpp=True,overrides=None):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
   files=integration_files();files.update(overrides or {});files['Main.hx']=main
   for name,code in files.items():
    path=Path(tmp)/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(code.replace('FIXTURE_ROOT',Path(tmp).as_posix()),encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',tmp,'-main','Main','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=45)
   self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-5000:])
   if not cpp:return
   env=os.environ.copy();env['HAXELIB_PATH']=str(ROOT/'.haxelib');env['NEKOPATH']=str(ROOT/'.tools/neko');env['PATH']=str(ROOT/'.tools/haxe')+os.pathsep+env['NEKOPATH']+os.pathsep+env.get('PATH','')
   exported=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',tmp,'-main','Main','-cpp',str(Path(tmp)/'cpp'),'-D','no-compilation'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=45)
   self.assertEqual(exported.returncode,0,(exported.stdout+exported.stderr)[-5000:])
   generated=(Path(tmp)/'cpp/src/NightmareVisionStageBindings.cpp').read_text(encoding='utf-8')
   self.assertRegex(generated,r'::Dynamic\s+_hx_run\(::hx::Class type,')
   self.assertNotRegex(generated,r'::NightmareVisionStage\s+_hx_run\(::hx::Class type,')
 def test_actual_owner_factory_script_phases_and_sole_container_membership(self):
  self.run_haxe(r'''
import flixel.group.FlxContainer.FlxTypedContainer;
import flixel.FlxBasic;
class Scene extends FlxTypedContainer<FlxBasic> {
 public var stage:NightmareVisionStage;
 public function new(){super();}
}
class Main {
 static function check(v:Bool,m:String):Void {if(!v)throw m;}
 static function main() {
  var io=new StageIO();var paths=io.paths;NightmareVisionSpriteRegistry.enterSession(paths.root);
  var lease=NightmareVisionSpriteRegistry.setup(paths);var scene=new Scene();
  var group=new NightmareVisionScriptGroup(scene);
  var configure:NightmareVisionScriptInterp->Void=null;
  configure=function(i) {
   i.variables.set("scene",scene);i.variables.set("group",group);i.variables.set("Reflect",Reflect);
   NightmareVisionScriptBindings.install(i,{paths:paths,requireActive:lease.requireActive,parent:function()return scene,
    read:function(p)return io.source,configure:configure,report:function(n,p,e) {throw n+"#"+p+":"+e;}});
  };
  var loader=function(path:String,shared:Map<String,Dynamic>) return NightmareVisionScriptModule.fromSource(path,io.source,scene,shared,configure,function(n,p,e){});
  var interpreter=new NightmareVisionScriptInterp(scene);configure(interpreter);
  NightmareVisionStageBindings.install(interpreter,paths,function()return false,loader);
  io.data.stageObjects=[{id:"prop",scale:[1,1],scrollFactor:[1,1],position:[7,9]}];
  scene.stage=new NightmareVisionStage("fixture",NightmareVisionStageBindings.owner(interpreter,paths,function()return false,loader));
  scene.stage.buildStage();check(scene.stage.members.length==1,"data object native member");
  io.scriptFiles.set("data/stages/fixture/script.hx",true);
  io.source='var registeredBefore=group.exists(script.name); var rootAddBefore=add; function onLoad() { publicLoad(); } function info() return [registeredBefore,Reflect.compareMethods(rootAddBefore,scene.add),stage==scene.stage,prop==stage.objects.get("prop")];';
  interpreter.variables.set("publicLoad",function(){});
  // Stage injection happens after top-level, and the registered object is same handle.
  configure=function(i) {
   i.variables.set("scene",scene);i.variables.set("group",group);i.variables.set("Reflect",Reflect);i.variables.set("publicLoad",function(){});
   i.variables.set("add",scene.add);
   NightmareVisionScriptBindings.install(i,{paths:paths,requireActive:lease.requireActive,parent:function()return scene,
    read:function(p)return io.source,configure:configure,report:function(n,p,e) {throw n+"#"+p+":"+e;}});
  };
  check(scene.stage.runScript(group),"source script run");
  var module=scene.stage.script;check(group.members.length==0,"run and onLoad remain unregistered");
  var state:Array<Dynamic>=module.call("info").returnValue;
  check(state[0]==false&&state[1]==true&&state[2]==true&&state[3]==true,"top-level vs injected source fields");
  check(group.addScript(module)&&group.members[0]==scene.stage.script,"actual module identity");
  scene.add(scene.stage);var actors=new flixel.group.FlxSpriteGroup();scene.stage.add(actors);
  check(scene.members.length==1&&scene.members[0]==scene.stage&&actors.container==scene.stage,"one scene owner");
  scene.stage.remove(actors,true);check(actors.container==null,"native detach transfers ownership");
  scene.stage.add(actors);check(scene.members.indexOf(actors)<0,"no flattened group update/draw");
  check(scene.stage.runScript(group)&&scene.stage.script.name==module.name+"_1"&&group.addScript(scene.stage.script),"repeated source run uses instance suffix");
  var probe={scale:{x:1.},literal:0};NightmareVisionStageBindings.setNestedProperty(probe,"scale.x",2.);check(probe.scale.x==2.,"actual nested source setter");
  interpreter.sourceClassScope().bindRuntimeClass("CapturedSprite",NightmareVisionFlxSprite);
  var constructions=0;
  interpreter.bindConstructorFactory(NightmareVisionFlxSprite,function(args) {
   constructions++;return new NightmareVisionFlxSprite(0,0,null,paths);
  },null);
  var retainedOwner=NightmareVisionStageBindings.owner(interpreter,paths,function()return false,loader);
  var retained=new NightmareVisionStage("retained",retainedOwner);
  interpreter.release();
  io.data.stageObjects=[{id:"captured",customInstance:"CapturedSprite",scale:[1,1],scrollFactor:[1,1],position:[0,0]}];
  retained.buildStage();check(constructions==1&&Std.isOfType(retained.objects.get("captured"),NightmareVisionFlxSprite),"retained factory survives interpreter release");
  io.scriptFiles.set("data/stages/retained/script.hx",true);
  io.source="function marker() return 91;";
  check(retained.runScript(group)&&retained.script.call("marker").returnValue==91,"retained script loader survives interpreter release");
  var before=io.calls.length;NightmareVisionSpriteRegistry.enterSession("other");var error:Dynamic=null;
  try retained.buildStage() catch(e:Dynamic)error=e;
  check(error!=null&&io.calls.length==before&&constructions==1,"retained Stage rejects exited owner before construction IO");
  error=null;try retained.runScript(group) catch(e:Dynamic)error=e;
  check(error!=null&&io.calls.length==before,"retained script loader rejects exited owner before IO");
  retained.script.destroy();retained.destroy();
  var oldMembers=scene.members.copy();error=null;
  try new NightmareVisionStage("fixture",retainedOwner) catch(e:Dynamic)error=e;
  check(error!=null&&scene.members.length==oldMembers.length,"stale source Stage ctor fails before mounting/IO");
  group.destroy();scene.destroy();interpreter.release();NightmareVisionSpriteRegistry.enterSession(null);
 }
}
''')

 def test_actual_host_swap_transfers_only_mounted_owned_groups_and_current_script(self):
  from test_source_event_preparation import extract_method
  method=extract_method((ROOT/'source/PlayState.hx').read_text(),'function swapNightmareVisionStage(')
  helpers={'StageHelper.hx': 'class StageHelper {public var stageData:Dynamic;public var defaultZoom:Float;public function new(n:String){}public function getInfo(r:String):Dynamic return {x:0.,y:0.};}',
   'NightmareVisionStageData.hx':'class NightmareVisionStageData {public static function normalizeStageId(n:String):String return n==null?"":StringTools.trim(n);public static function load(r:String,n:String):Dynamic return n=="missing"?null:StageIO.current.data;public static function getLegacyStageFile(r:String,n:String):Dynamic return n=="missing"?null:StageIO.current.data;public static function getLegacyTemplateStageFile():Dynamic return StageIO.current.data;public static function getTemplateStageFile():Dynamic return StageIO.current.data;}'}
  main=r'''
import flixel.FlxBasic;import flixel.group.FlxContainer.FlxTypedContainer;
class Host extends FlxTypedContainer<FlxBasic> {
 public var stage:flixel.group.FlxGroup.FlxTypedGroup<FlxBasic>;public var curStage:StageHelper;public var defaultCamZoom=1.;
 public var nightmareVisionPaths:NightmareVisionPaths;public var nightmareVisionPrefs={view:{globalAntialiasing:false}};
 public var nightmareVisionPlugins:Dynamic;public var nightmareVisionActiveMods:Dynamic;public var nightmareVisionActiveDifficulty:Dynamic;
 public var nightmareVisionStageConstructionInterp:NightmareVisionScriptInterp;public var nightmareVisionScripts:{group:NightmareVisionScriptGroup};
 public var boyfriendPosition=new flixel.math.FlxPoint();public var dadPosition=new flixel.math.FlxPoint();public var gfPosition=new flixel.math.FlxPoint();
 public var supported:Array<NightmareVisionCharacterGroup>=[];public var camerasApplied=0;
 public function new(p:NightmareVisionPaths){super();nightmareVisionPaths=p;nightmareVisionStageConstructionInterp=new NightmareVisionScriptInterp();nightmareVisionScripts={group:new NightmareVisionScriptGroup(this)};}
 public function isNightmareVisionRoleGroup(o:Dynamic):Bool return supported.indexOf(cast o)>=0;
 public function applyPsychStageCameraOffsets(d:Dynamic):Void camerasApplied++;
 public function refreshNightmareVisionStage():Void {}
 static function loadNightmareVisionStageFile(p:NightmareVisionPaths,prefs:Dynamic,plugins:Dynamic,mods:Dynamic,difficulty:Dynamic,lease:NightmareVisionSpriteOwner,path:String,shared:Map<String,Dynamic>):NightmareVisionScriptModule {
  lease.requireActive();return StageIO.current.load(path,shared);
 }
'''+method.replace('function swapNightmareVisionStage','public function swapNightmareVisionStage')+r'''
}
class Main {static function ok(v:Bool,m:String):Void {if(!v)throw m;}static function main(){
 var io=new StageIO();NightmareVisionSpriteRegistry.enterSession(io.paths.root);var lease=NightmareVisionSpriteRegistry.setup(io.paths);var host=new Host(io.paths);
 var owner=NightmareVisionStageBindings.owner(host.nightmareVisionStageConstructionInterp,io.paths,function()return false,io.load);
 var old=new NightmareVisionStage("old",owner);host.stage=old;io.data.stageObjects=[{id:"oldProp"}];old.buildStage();var prop=old.members[0];
 var groupOwner:NightmareVisionCharacterGroupOwner={construct:function(n,p)return new Character(0,0,n,p),scene:function()return null,spriteOwner:lease};
 var role=new NightmareVisionCharacterGroup(100,200,cast 0,groupOwner);var actor=role.addToList("cached");role.parent=actor;role.alpha=.6;
 var detached=new NightmareVisionCharacterGroup(11,13,cast 1,groupOwner);var unmounted=detached.addToList("unmounted");var mapOnly=new Character(0,0,"map-only");role.map.set("map-only",mapOnly);
 host.supported=[role,detached];old.add(role);host.add(new FlxBasic());host.add(old);host.add(new FlxBasic());var originalSlot=host.members.indexOf(old);
 var teardown=0;var module=host.nightmareVisionScripts.group.loadSource("old-module","function onDestroy() teardown();",function(i)i.variables.set("teardown",function()teardown++));old.script=module;
 var before=io.calls.length;ok(!host.swapNightmareVisionStage("missing")&&teardown==0&&host.stage==old&&old.members.indexOf(role)>=0,"unavailable does not mutate callbacks/ownership");
 io.scriptFiles.set("data/stages/next/script.hx",true);io.source="function onLoad() io.tick();";io.data.stageObjects=[{id:"newProp"}];var x=actor.x,y=actor.y;
 ok(host.swapNightmareVisionStage("next"),"available source host swap");
 ok(teardown==1&&module.released&&prop.destroyed==1,"registered module lifecycle and old props once");
 ok(host.members[originalSlot]==host.stage&&host.stage.members.indexOf(role)>=0&&role.container==host.stage&&host.members.indexOf(role)<0,"outer slot and sole native ownership");
 ok(actor.x==x&&actor.y==y&&role.x==100&&role.y==200&&role.alpha==.6&&role.map.get("cached")==actor&&actor.destroyed==0,"cache/transform preserved");
 ok(detached.container==null&&unmounted.destroyed==0&&mapOnly.destroyed==0&&host.stage.members.indexOf(detached)<0,"unmounted/map-only refs neither adopted nor destroyed");
 ok(host.nightmareVisionScripts.group.members.length==1&&host.nightmareVisionScripts.group.members[0]==(cast host.stage:NightmareVisionStage).script,"new actual script registered");
 host.nightmareVisionScripts.group.destroy();host.destroy();detached.destroy();mapOnly.destroy();host.nightmareVisionStageConstructionInterp.release();NightmareVisionSpriteRegistry.enterSession(null);
}}
'''
  self.run_haxe(main,cpp=False,overrides=helpers)
  # Execute the same host replacement method with the historical scene layout.
  legacy=main.replace('var io=new StageIO();NightmareVisionSpriteRegistry', 'var io=new StageIO();io.paths.root="FIXTURE_ROOT";sys.io.File.saveContent(io.paths.root+"/"+NightmareVisionStageProfile.FILE_NAME,haxe.Json.stringify({version:1,owner:io.paths.root,stageApi:"legacy-group"}));NightmareVisionSpriteRegistry')
  legacy=legacy.replace('function()return false,io.load);', 'function()return false,io.load,true);')
  legacy=legacy.replace('var old=new NightmareVisionStage("old",owner);host.stage=old;io.data.stageObjects=[{id:"oldProp"}];old.buildStage();var prop=old.members[0];', 'var old=new NightmareVisionLegacyStage("old",owner);host.stage=old;var prop=new FlxBasic();old.add(prop);var frontProp=new FlxBasic();old.foreground.add(frontProp);')
  legacy=legacy.replace('old.add(role);host.add(new FlxBasic());host.add(old);host.add(new FlxBasic());', 'host.add(new FlxBasic());host.add(old);host.add(role);host.add(old.foreground);host.add(new FlxBasic());')
  legacy=legacy.replace('old.script=module;', 'old.stageScripts.push(module);old.hscriptArray.push(module);')
  legacy=legacy.replace('old.members.indexOf(role)>=0', 'host.members.indexOf(role)>=0')
  legacy=legacy.replace('data/stages/next/script.hx', 'stages/next.hx')
  legacy=legacy.replace('host.stage.members.indexOf(role)>=0&&role.container==host.stage&&host.members.indexOf(role)<0', 'host.stage.members.indexOf(role)<0&&role.container==host&&host.members.indexOf(role)==originalSlot+1&&host.members[originalSlot+2]==NightmareVisionStageScene.foreground(host.stage)&&frontProp.destroyed==1')
  legacy=legacy.replace('(cast host.stage:NightmareVisionStage).script', '(cast host.stage:NightmareVisionLegacyStage).stageScripts[0]')
  self.run_haxe(legacy,cpp=False,overrides=helpers)
