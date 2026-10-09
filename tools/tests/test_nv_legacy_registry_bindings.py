"""Exercise writable historical arrays through real Iris and native script loaders."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from tools.haxe_flixel_math_stubs import write_flixel_point_stub
ROOT=Path(__file__).resolve().parents[2]
MAIN=r'''class Host {public static var instance:Host;public function new(){}}
class Main {
 static function check(b:Bool,m:String){if(!b)throw m;}
 static function run(i:NightmareVisionScriptInterp,text:String):Dynamic return i.execute(new NightmareVisionScriptParser().parseString(text,'registry-api'));
 static function scope(s:Host,r:NightmareVisionLegacyScriptRegistry):NightmareVisionScriptInterp {
  var i=new NightmareVisionScriptInterp(s);i.bindClassParent(Host);
  i.variables.set('game',s);i.variables.set('PlayState',Host);i.bindImport('meta.states.PlayState',Host);
  i.variables.set('Reflect',i.sourceClassScope().reflectFacade());
  NightmareVisionLegacyRegistryBindings.install(i,s,Host,r);return i;
 }
 static function main(){
  var a=new Host(),b=new Host();Host.instance=a;
  var registry=new NightmareVisionLegacyScriptRegistry(),other=new NightmareVisionLegacyScriptRegistry();
  var i=scope(a,registry),j=scope(b,other);var errors:Array<String>=[];var log:Array<String>=[];
  var group=new NightmareVisionScriptGroup(a,function(n,c,e)errors.push(Std.string(e)));
  group.onRegistered=function(s)registry.add(s);group.onRemoved=registry.remove;
  var add=function(name:String,code:String):NightmareVisionScriptModule return group.loadSource(name,code,function(s){s.variables.set('record',function()log.push(name));s.variables.set('mutate',null);});
  var first=add('first','function probe(){record();if(mutate!=null)mutate();return "first";}');
  var luaInterp=new hscript.Interp();var lua=new NightmareVisionLegacyLuaScript('lua',luaInterp,function(n,args){log.push('lua');return 'lua';});registry.add(lua,true);
  var second=add('second','function probe(){record();return "second";}');
  for(s in [i,j]){s.variables.set('first',first);s.variables.set('second',second);s.variables.set('lua',lua);}
  i.variables.set('saved',null);run(i,'saved=funkyScripts;if(saved!=game.funkyScripts||saved!=PlayState.funkyScripts||saved!=Reflect.getProperty(game,"funkyScripts"))throw "array aliases";');
  run(i,'if(callOnScripts("probe",[])!="second")throw "combined return";');check(log.join(',')=='first,lua,second','registration order');log.resize(0);
  run(i,'if(callOnLuas("probe",[])!="lua"||callOnHScripts("probe",[])!="second")throw "family return";');
  check(log.join(',')=='lua,first,second','independent family order');
  run(i,'setOnScripts("sharedValue",17);');check(first.get('sharedValue')==17&&lua.get('sharedValue')==17,'shared setters');
  run(i,'Reflect.setProperty(game,"funkyScripts",[second,first]);if(funkyScripts==saved||saved.length!=3||PlayState.funkyScripts!=funkyScripts)throw "replacement identity";');
  check(registry.funkyScripts.length==2&&registry.hscriptArray.length==2&&registry.luaArray.length==1,'replacement does not rewrite families');
  run(j,'PlayState.funkyScripts=[lua];');check(other.funkyScripts.length==1&&registry.funkyScripts.length==2,'owner class isolation');
  run(i,'game.funkyScripts=saved;');
  for(form in ['callScript(first,"probe",[]);','game.callScript(lua,"probe",[]);','PlayState.callScript("second","probe",[]);','Reflect.callMethod(game,Reflect.field(game,"callScript"),[[first,second],"probe",[]]);'])run(i,form);
  run(i,'first.scriptName="renamed";if(callScript("first","probe",[])!=0||callScript("renamed","probe",[])!="first")throw "mutable script name";');
  var once=false;first.set('mutate',function(){if(once)return;once=true;add('late','function probe(){record();return "late";}');});
  log.resize(0);check(registry.callOnScripts('probe',[])=='late'&&log.join(',')=='first,lua,second,late','callback load visits appended module');
  first.set('mutate',function()group.removeScript(second));log.resize(0);registry.callOnScripts('probe',[]);
  check(log.join(',')=='first,lua,late'&&registry.hscriptArray.indexOf(second)<0,'callback removal reaches family arrays');
  first.set('mutate',null);
  var failed=group.loadSource('broken','throw "fixture failure";');check(failed==null&&registry.funkyScripts.length==3,'failed top level registration removed');
  check(errors.length==1,'unexpected script error');group.destroy();check(registry.hscriptArray.length==0&&registry.funkyScripts.length==1,'group teardown unregisters existing modules');
  i.release();run(j,'if(funkyScripts.length!=1)throw "other owner destroyed";');j.release();
 }
}'''
class RegistryBindingsTest(unittest.TestCase):
 def test_real_aliases_load_remove_and_owner_isolation(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder);write_flixel_point_stub(work);(work/'Main.hx').write_text(MAIN)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
