"""Historical Stage grouping/callbacks, isolated from the modern container preset."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from test_nv_stage_integration import integration_files
ROOT = Path(__file__).resolve().parents[2]
MAIN = r'''
import flixel.FlxBasic;
class Main {
 static function ok(value:Bool,message:String) {if(!value)throw message;}
 static function main() {
  var io=new StageIO();io.data=null;
  var owner=io.owner();owner.template=function()return cast NightmareVisionStageData.getLegacyTemplateStageFile();
  owner.scriptPath=function(n)return n+".hscript";
  var stage=new NightmareVisionLegacyStage(null,owner);
  ok(stage.curStage=="stage" && stage.stageData.directory=="" && !stage.stageData.isPixelStage && stage.stageData.boyfriend[0]==500,"historical null/default contract");
  io.source='function onLoad(bg,fg){ if(stage!=bg || foreground!=fg || stage.hscriptArray.length!=1) throw "binding order"; add(new FlxBasic()); foreground.add(new FlxBasic()); io.tick(); } function onDestroy(){io.tick();}';
  var load=owner.fromFile;
  owner.fromFile=function(p,s){var script=NightmareVisionScriptModule.fromSource(p,io.source,null,s,function(i){i.variables.set("io",io);i.variables.set("FlxBasic",FlxBasic);},function(n,c,e){throw Std.string(e);});io.loaded=script;return script;};
  io.scriptFiles.set("stages/stage.hscript",true);
  var group=new NightmareVisionScriptGroup();NightmareVisionStageScene.load(stage,group);
  ok(group.members.length==1&&group.members[0]==io.loaded,"legacy stage module joins shared callback group");
  ok(stage.members.length==1 && stage.foreground.members.length==1 && stage.stageScripts[0]==stage.hscriptArray[0],"separate foreground and script ownership");
  var fg=stage.foreground.members[0];var bg=stage.members[0];
  ok(fg.container==null && bg.container==null && io.calls.length==1,"legacy group must not steal container ownership or duplicate callback");

  var scene=new flixel.group.FlxContainer.FlxTypedContainer<FlxBasic>();
  var gf=new FlxBasic();var dad=new FlxBasic();var bf=new FlxBasic();
  NightmareVisionStageScene.mount(scene,stage,[gf,dad,bf]);
  ok(scene.members.length==5&&scene.members[0]==stage&&scene.members[1]==gf&&scene.members[2]==dad&&scene.members[3]==bf&&scene.members[4]==stage.foreground,"legacy default scene order");
  ok(stage.members.length==1&&gf.container==scene&&bg.container==null,"separate source scene ownership");
  var between=new FlxBasic();NightmareVisionStageScene.insertBehind(scene,stage,bf,between);
  ok(scene.members.indexOf(between)+1==scene.members.indexOf(bf),"legacy addBehind inserts into scene");
  scene.remove(stage,true);scene.remove(stage.foreground,true);
  var script=io.loaded;NightmareVisionStageScene.releaseScripts(stage,group);stage.destroy();
  ok(script.released && bg.destroyed==1 && fg.destroyed==0 && io.calls.length==2&&group.members.length==0,"group calls onDestroy once; stage releases without duplicate callback");
  stage.foreground.destroy();scene.destroy();ok(fg.destroyed==1&&gf.destroyed==1&&dad.destroyed==1&&bf.destroyed==1,"foreground and actors scene teardown exactly once");
  var failed=false;try stage.buildStage()catch(e:Dynamic)failed=true;ok(failed,"destroyed stage reentered IO");
  var missing=new NightmareVisionLegacyStage("missing",owner);missing.buildStage();ok(missing.stageScripts.length==0,"missing script must not manufacture a module");
  io.scriptFiles.set("stages/lua.hscript",true);owner.scriptPath=function(n)return "stages/lua.lua";io.scriptFiles.set("stages/lua.lua",true);
  var lua=new NightmareVisionLegacyStage("lua",owner);lua.buildStage();ok(lua.stageScripts.length==0&&io.warn.length==1,"unsupported Lua must be diagnosed without interpreting it as HScript");
  io.active=false;failed=false;try new NightmareVisionLegacyStage("stale",owner)catch(e:Dynamic)failed=true;ok(failed,"constructor must reject released owner");io.active=true;
  var paths=io.paths;io.scriptFiles.clear();io.scriptFiles.set("core/stages/order.hx",true);io.scriptFiles.set("mod/stages/order.hscript",true);
  ok(NightmareVisionStageBindings.legacyScriptPath("stages/order",paths)=="core/stages/order.hx","extensions precede owner/core fallback");
  io.scriptFiles.set("mod/stages/order.hx",true);ok(NightmareVisionStageBindings.legacyScriptPath("stages/order",paths)=="mod/stages/order.hx","owner wins within an extension");
  io.scriptFiles.clear();ok(NightmareVisionStageBindings.legacyScriptPath("stages/order",paths)==null,"absent source path");
  var module=NightmareVisionScriptModule.fromSource("explicit-stage", 'addHaxeLibrary("Stage", "gameObjects"); result=new Stage("direct");', null,null,function(i){NightmareVisionStageBindings.install(i,paths,function()return false,load);},function(n,c,e){throw Std.string(e);});
  ok(Std.isOfType(module.get("result"),NightmareVisionLegacyStage),"qualified legacy library constructor factory");
  ok(module.interp.resolveSourceImport("funkin.objects.Stage",true)==NightmareVisionStage,"modern qualified class retained");
  var second=NightmareVisionScriptModule.fromSource("modern-stage", 'result=new Stage("direct");',null,null,function(i){NightmareVisionStageBindings.install(i,paths,function()return false,load);},function(n,c,e){throw Std.string(e);});
  ok(Std.isOfType(second.get("result"),NightmareVisionStage),"modern default preset retained");
  var installed="__WORK__/profile";sys.FileSystem.createDirectory(installed);paths.root=installed;
  sys.io.File.saveContent(installed+"/"+NightmareVisionStageProfile.FILE_NAME,haxe.Json.stringify({version:1,owner:installed,stageApi:"legacy-group"}));
  var auto=NightmareVisionScriptModule.fromSource("profile-stage",'result=new Stage("direct");',null,null,function(i){NightmareVisionStageBindings.install(i,paths,function()return false,load);},function(n,c,e){throw Std.string(e);});
  ok(Std.isOfType(auto.get("result"),NightmareVisionLegacyStage),"owner profile selects legacy default constructor");

 }
}
'''
class NVLegacyStageTest(unittest.TestCase):
 def test_legacy_groups_callbacks_explicit_binding_and_lifetime(self):
  files=integration_files();files['Main.hx']=MAIN
  del files['NightmareVisionStageData.hx']
  files['NightmareVisionPaths.hx']=files['NightmareVisionPaths.hx'].replace('public function getPath(p:String,?a:String,b:Bool=false):String return p;', 'public function getPath(p:String,?parent:String,check:Bool=false):String return check && exists("mod/"+p)?"mod/"+p:"core/"+p;')
  # StageData executes production code; no filesystem stage read in this fixture.
  files['CoolUtil.hx']='class CoolUtil {public static function parseJson(s:String):Dynamic return haxe.Json.parse(s);}'
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
   work=Path(directory)
   for name,source in files.items():
    p=work/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(source.replace('__WORK__',work.as_posix()),encoding='utf-8')
   env=os.environ.copy();env['HAXELIB_PATH']=str(ROOT/'.haxelib');env['NEKOPATH']=str(ROOT/'.tools/neko');env['PATH']=str(ROOT/'.tools/haxe')+os.pathsep+env['NEKOPATH']+os.pathsep+env.get('PATH','')
   cmd=[*HAXE_COMMAND,'-D','flixel','-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',directory,'-main','Main']
   for target in [['--interp'],['-cpp',str(work/'cpp'),'-D','no-compilation']]:
    result=subprocess.run(cmd+target,cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
    self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-6000:])
   self.assertIn('flixel::group::FlxTypedGroup_obj', (work/'cpp/include/NightmareVisionLegacyStage.h').read_text())
if __name__=='__main__':unittest.main()
