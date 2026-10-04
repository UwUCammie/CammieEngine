"""Execute Psych's script-broadcast ordering and callback-stop semantics."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, ROOT


class PsychScriptBroadcastTest(unittest.TestCase):
    def test_lua_then_hscript_result_and_stop_semantics(self):
        if not (ROOT / ".tools/haxe/haxe.exe").is_file() and not (ROOT / ".tools/haxe/haxe").is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        fixture = r'''class Scope {
 public var name:String;
 public var closed:Bool=false;
 public var closesOnCall:Bool=false;
 public var result:Dynamic;
 public var results:Array<Dynamic>=null;
 public function new(name:String,result:Dynamic=null) { this.name=name; this.result=result; }
}
class CallbackPayload {
 public var offset:Float;
 public function new(offset:Float) this.offset=offset;
}
class BroadcastFixture {
 static var calls:Array<String>=[];
 static var removed:Array<String>=[];
 static function nameOf(scope:Scope):String return scope.name;
 static function isClosed(scope:Scope):Bool return scope.closed;
 static function callLua(scope:Scope,name:String,args:Array<Dynamic>):Dynamic {
  calls.push('lua:'+scope.name+':'+name+':'+args.length);
  if(scope.closesOnCall) scope.closed=true;
  if(scope.results!=null && scope.results.length>0) return scope.results.shift();
  return scope.result;
 }
 static function callHScript(scope:Scope,name:String,args:Array<Dynamic>):Dynamic {
  calls.push('hscript:'+scope.name+':'+name+':'+args.length);
  if(scope.results!=null && scope.results.length>0) return scope.results.shift();
  return scope.result;
 }
 static function remove(scope:Scope):Void { removed.push(scope.name); }
 static function reset():Void { calls=[]; removed=[]; }
 static function main() {
  var lua=[new Scope('lua1',ScriptCallbackResult.STOP),new Scope('lua2','lua-last')];
  var hs=[new Scope('hs1','must-not-run')];
  var result=PsychScriptBroadcast.callOnScripts(lua,hs,'onTest',null,nameOf,isClosed,callLua,callHScript);
  if(result!='lua-last' || calls.join(',')!='lua:lua1:onTest:0,lua:lua2:onTest:0') throw 'Lua did not run first or Function_Stop stopped the broadcast';

  reset(); lua=[new Scope('lua',ScriptCallbackResult.CONTINUE)]; hs=[new Scope('hs1',ScriptCallbackResult.CONTINUE),new Scope('hs2','hscript-last')];
  result=PsychScriptBroadcast.callOnScripts(lua,hs,'onTest',[],nameOf,isClosed,callLua,callHScript);
  if(result!='hscript-last' || calls.join(',')!='lua:lua:onTest:0,hscript:hs1:onTest:0,hscript:hs2:onTest:0') throw 'excluded Lua result did not fall through to all HScript scopes';

  reset(); lua=[new Scope('stop',ScriptCallbackResult.STOP_LUA),new Scope('later','late')]; hs=[new Scope('hs','wrong')];
  result=PsychScriptBroadcast.callOnScripts(lua,hs,'hook',[],nameOf,isClosed,callLua,callHScript);
  if(result!=ScriptCallbackResult.STOP_LUA || calls.length!=1) throw 'Function_StopLua did not stop the Lua family';

  reset(); lua=[new Scope('lua1',ScriptCallbackResult.STOP_HSCRIPT),new Scope('lua2','lua-later')];
  result=PsychScriptBroadcast.callOnScripts(lua,hs,'hook',[],nameOf,isClosed,callLua,callHScript);
  if(result!='lua-later' || calls.length!=2) throw 'Function_StopHScript incorrectly stopped Lua';

  reset(); lua=[new Scope('continue',ScriptCallbackResult.CONTINUE)];
  hs=[new Scope('stop-hs',ScriptCallbackResult.STOP_HSCRIPT),new Scope('hs-later','wrong')];
  result=PsychScriptBroadcast.callOnScripts(lua,hs,'hook',[],nameOf,isClosed,callLua,callHScript);
  if(result!=ScriptCallbackResult.STOP_HSCRIPT || calls.length!=2) throw 'Function_StopHScript did not stop the HScript family';

  reset(); lua=[new Scope('continue',ScriptCallbackResult.CONTINUE)];
  hs=[new Scope('stop-lua',ScriptCallbackResult.STOP_LUA),new Scope('hs-later','last-hs')];
  result=PsychScriptBroadcast.callOnScripts(lua,hs,'hook',[],nameOf,isClosed,callLua,callHScript);
  if(result!='last-hs' || calls.length!=3) throw 'Function_StopLua incorrectly stopped HScript';

  reset(); lua=[new Scope('all-stop',ScriptCallbackResult.STOP_ALL),new Scope('later','wrong')];
  hs=[new Scope('hs','wrong')];
  result=PsychScriptBroadcast.callOnScripts(lua,hs,'hook',[],nameOf,isClosed,callLua,callHScript);
  if(result!=ScriptCallbackResult.STOP_ALL || calls.length!=1) throw 'Function_StopAll did not stop all families';

  reset(); lua=[new Scope('stop',ScriptCallbackResult.STOP_LUA),new Scope('later','lua-last')];
  result=PsychScriptBroadcast.callOnLuas(lua,'hook',[],nameOf,isClosed,callLua,null,true);
  if(result!='lua-last' || calls.length!=2) throw 'ignoreStops did not continue through Lua scopes';
  reset(); hs=[new Scope('hs-stop',ScriptCallbackResult.STOP_HSCRIPT),new Scope('hs-later','hs-last')];
  result=PsychScriptBroadcast.callOnHScript(hs,'hook',[],nameOf,callHScript,true);
  if(result!='hs-last' || calls.length!=2) throw 'ignoreStops did not continue through HScript scopes';

  reset(); lua=[new Scope('exclude','skip-me'),new Scope('kept','kept-result')]; hs=[new Scope('hs','wrong')];
  result=PsychScriptBroadcast.callOnScripts(lua,hs,'hook',[],nameOf,isClosed,callLua,callHScript,false,null,['skip-me',ScriptCallbackResult.CONTINUE]);
  if(result!='kept-result' || calls.length!=2) throw 'custom exclusions changed result selection';

  reset(); var alreadyClosed=new Scope('closed','wrong'); alreadyClosed.closed=true;
  var closes=new Scope('closes','closed-result'); closes.closesOnCall=true;
  lua=[alreadyClosed,closes,new Scope('active','active-result')];
  result=PsychScriptBroadcast.callOnLuas(lua,'hook',[],nameOf,isClosed,callLua,remove,false,['closed'],['Function_Continue']);
  if(result!='active-result' || removed.join(',')!='closed,closes' || calls.join(',')!='lua:closes:hook:0,lua:active:hook:0') throw 'closed Lua cleanup/exclusion order changed';

  reset(); hs=[new Scope('continue',ScriptCallbackResult.CONTINUE),new Scope('last','last')];
  var supplied:Array<Dynamic>=[];
  result=PsychScriptBroadcast.callOnHScript(hs,'hook',[],nameOf,callHScript,false,[],supplied);
  if(result!='last' || supplied.length!=1 || supplied[0]!=ScriptCallbackResult.CONTINUE) throw 'HScript did not always exclude/mutate Continue';

  reset();
  var fractional=PsychScriptBroadcast.callOnLuas([new Scope('fractional',321.5)],
   'eventEarlyTrigger',[],nameOf,isClosed,callLua);
  if(!Std.isOfType(fractional,Float) || fractional!=321.5)
   throw 'Lua broadcast narrowed a fractional Dynamic result';

  reset();
  var boolResult=PsychScriptBroadcast.callOnHScript([new Scope('boolean',true)],
   'eventEarlyTrigger',[],nameOf,callHScript);
  if(!Std.isOfType(boolResult,Bool) || boolResult!=true)
   throw 'HScript broadcast narrowed a boolean Dynamic result';

  reset();
  var payload=new CallbackPayload(50.25);
  var objectResult=PsychScriptBroadcast.callOnScripts([], [new Scope('object',payload)],
   'eventEarlyTrigger',[],nameOf,isClosed,callLua,callHScript);
  if(objectResult!=payload || !Std.isOfType(objectResult,CallbackPayload)
   || cast(objectResult,CallbackPayload).offset!=50.25)
   throw 'combined broadcast changed a callback object Dynamic result';
  Sys.println('OK');
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "BroadcastFixture.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder, "--run", "BroadcastFixture"],
                cwd=folder, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_broadcast_callback_results_remain_explicitly_dynamic(self):
        source = (ROOT / "source/PsychScriptBroadcast.hx").read_text()
        self.assertEqual(source.count("var value:Dynamic = invoke("), 2,
                         "both callback-family loops must keep runtime result types instead of inferring from sentinels")


if __name__ == "__main__":
    unittest.main()
