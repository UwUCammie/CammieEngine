"""Execute owner-local HScript callback registration across live and future Lua scopes."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

class PsychSourceCallbackRegistryTest(unittest.TestCase):
    def test_local_global_future_owner_isolation_and_teardown(self):
        main = r'''import PsychSourceCallbackRegistry.PsychLuaCallbackFacade;
class Main {
 static function check(v:Bool, message:String):Void if(!v)throw message;
 static function invoke(f:Dynamic, args:Array<Dynamic>):Dynamic return Reflect.callMethod(null,f,args);
 static function main() {
  var registry=new PsychSourceCallbackRegistry();
  var lua=new hscript.Interp();var other=new hscript.Interp();var hx=new hscript.Interp();
  lua.variables.set('__compatDiagnosticSource','owner/a.lua');
  registry.attach('a',lua,true,invoke);registry.attach('b',other,true,invoke);registry.attach('a',hx,false,invoke);
  var bridge:Dynamic=registry.bridge('a',hx,'a.hx',lua);
  var parent:PsychLuaCallbackFacade=bridge.parentFacade('a.hx',hx);
  check(parent.scriptName=='owner/a.lua'&&!parent.closed,'parent facade not source scope');
  bridge.registerLocal('a.hx','localOnly',function(x:Int)return x+7,parent);
  check(parent.call('localOnly',[5])==12&&!other.variables.exists('localOnly'),'local callback isolation');
  bridge.registerGlobal('a.hx','shared',function(x:Int)return x*3);
  check(parent.call('shared',[4])==12&&!other.variables.exists('shared')&&!hx.variables.exists('shared'),'global Lua owner scope');
  var future=new hscript.Interp();registry.attach('a',future,true,invoke);
  check(Reflect.callMethod(null,future.variables.get('shared'),[6])==18,'future Lua missed global callback');
  var foreign:Dynamic=registry.bridge('b',other,'b.lua',other).parentFacade('b.lua',other);
  var denied=false;try bridge.registerLocal('a.hx','bad',function(){},foreign)catch(_:Dynamic)denied=true;
  check(denied&&!other.variables.exists('bad'),'foreign parent accepted');
  var plain:Dynamic=registry.bridge('a',hx,'plain.hx');
  check(plain.parentFacade('plain.hx',hx)==null,'plain HScript acquired a fake Lua parent');
  parent.set('value',42);check(lua.variables.get('value')==42,'facade set not live');
  parent.stop();check(parent.closed&&parent.call('shared',[1])==ScriptCallbackResult.CONTINUE,'closed Lua callback invoked');
  var saved:Dynamic=future.variables.get('shared');registry.release();registry.release();
  denied=false;try Reflect.callMethod(null,saved,[1])catch(_:Dynamic)denied=true;
  check(denied,'released callback owner still invoked HScript');
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            work=Path(directory)
            (work/'Main.hx').write_text(main, encoding='utf-8', newline='\n')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(work),'--run','Main'],cwd=work,capture_output=True,text=True,timeout=45)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
