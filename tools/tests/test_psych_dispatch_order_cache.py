"""Psych dispatch keeps its scope order cached but always matches the live registry."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest

from test_psych_runtime_bindings import (HSCRIPT_PRESET, HXC_RUNTIME, LUA_INTERP, PLAY_STATE,
                                         write_point_stub)

ROOT = Path(__file__).resolve().parents[2]


MAIN = r'''package;
import hscript.Interp;

class DispatchOrderFixture {
 static function check(value:Bool,message:String):Void if(!value)throw message;

 static function scope(host:PlayState,key:String,origin:String,lua:Bool,bind:Bool):Interp {
  var interp:Interp=lua?new LuaCompatInterp():new Interp();
  interp.variables.set('__psychScoreGlobals',true);
  interp.variables.set('__compatDiagnosticSource',origin);
  host.hscriptStates.set(key,interp);
  if(bind){
   var runtime=new PsychRuntimeBindings(host,interp,origin);
   runtime.install();
   host.psychRuntimeBindings.push(runtime);
  }
  return interp;
 }

 // The order before caching: runtime creation order, then sorted keys.
 static function expected(host:PlayState,family:String):String {
  var out:Array<String>=[];
  var keys=[for(key in host.hscriptStates.keys()) key];
  var seen=new Map<String,Bool>();
  for(runtime in host.psychRuntimeBindings) for(key in keys){
   var interp=host.hscriptStates.get(key);
   if(!seen.exists(key)&&interp==@:privateAccess runtime.owner&&usable(host,key,family)){out.push(key);seen.set(key,true);}
  }
  keys.sort(Reflect.compare);
  for(key in keys) if(!seen.exists(key)&&usable(host,key,family)) out.push(key);
  return out.join(',');
 }

 static function usable(host:PlayState,key:String,family:String):Bool {
  var interp=host.hscriptStates.get(key);
  if(interp==null||host.hxcPayloadStates.get(key)==true) return false;
  if(interp.variables.get('__compatClosed')==true||interp.variables.get('__psychScoreGlobals')!=true) return false;
  var lua=Std.isOfType(interp,LuaCompatInterp);
  return family=='Luas'?lua:!lua;
 }

 static function observed(host:PlayState,family:String):String {
  var events:Array<String>=[];
  for(key in host.hscriptStates.keys()){
   var label=key;
   host.hscriptStates.get(key).variables.set('probeOrder',function():Dynamic {events.push(label);return null;});
  }
  PsychRuntimeBindings.dispatch(host,'probeOrder',[],family);
  return events.join(',');
 }

 static function same(host:PlayState,message:String):Void {
  for(family in ['Luas','HScript']){
   var want=expected(host,family);
   var got=observed(host,family);
   check(want==got,message+' ('+family+'): wanted '+want+' got '+got);
  }
 }

 static function oldMatches(actual:String,requested:String):Bool {
  if(actual==null||requested==null||StringTools.trim(requested)=='') return false;
  actual=StringTools.replace(actual,'\\','/').toLowerCase();
  var path=StringTools.replace(requested,'\\','/').toLowerCase();
  return actual==path||StringTools.endsWith(actual,'/'+path)
   ||(haxe.io.Path.extension(path)==''&&(StringTools.endsWith(actual,'/'+path+'.lua')
    ||StringTools.endsWith(actual,'/'+path+'.hx')));
 }

 static function main():Void {
  var host=new PlayState();
  var zeta=scope(host,'zeta-lua','mods/zeta.lua',true,true);
  scope(host,'alpha-hx','mods/alpha.hx',false,true);
  scope(host,'mid-lua','mods/mid.lua',true,true);
  scope(host,'observer-b','engine/observer-b.hx',false,false);
  scope(host,'observer-a','engine/observer-a.lua',true,false);
  same(host,'initial order');
  same(host,'repeated order from the cache');
  // An unchanged registry must reuse the base order, not rebuild it.
  var cachedOrder=@:privateAccess PsychRuntimeBindings.orderEntries;
  PsychRuntimeBindings.dispatch(host,'probeOrder',[],'Luas');
  PsychRuntimeBindings.dispatch(host,'probeOrder',[],'HScript');
  check(cachedOrder==@:privateAccess PsychRuntimeBindings.orderEntries,'an unchanged registry rebuilt the order');

  // Registry changes that keep the map and bindings array identities.
  scope(host,'added-lua','mods/added.lua',true,true);
  same(host,'a new runtime scope');
  scope(host,'aaa-observer','engine/aaa.lua',true,false);
  same(host,'a new observer key');
  host.hscriptStates.remove('mid-lua');
  same(host,'a removed key');
  var replacement=new LuaCompatInterp();
  replacement.variables.set('__psychScoreGlobals',true);
  host.hscriptStates.set('zeta-lua',replacement);
  same(host,'a key bound to a different interpreter');
  host.hscriptStates.set('zeta-lua',zeta);
  same(host,'the original interpreter restored');

  // Flags change without any registry change; filters still apply per call.
  zeta.variables.set('__compatClosed',true);
  same(host,'a closed scope');
  zeta.variables.set('__compatClosed',false);
  host.hxcPayloadStates.set('alpha-hx',true);
  same(host,'an HXC payload scope');
  host.hxcPayloadStates.remove('alpha-hx');
  same(host,'a cleared HXC payload flag');

  // Runtimes swapped in place, then cleared the way song teardown does.
  var bindings=@:privateAccess host.psychRuntimeBindings;
  var first=bindings[0];bindings[0]=bindings[1];bindings[1]=first;
  same(host,'reordered runtimes');
  bindings.resize(0);
  same(host,'no runtimes left');
  check(@:privateAccess PsychRuntimeBindings.orderStates==null,
   'a host without runtimes stayed in the static order cache');

  // A new registry object (a new song or a probe swapping the map) rebuilds.
  var other=new PlayState();
  scope(other,'b-lua','x/b.lua',true,true);
  scope(other,'a-lua','x/a.lua',true,true);
  same(other,'a second host');
  host.hscriptStates=new Map();
  scope(host,'fresh','mods/fresh.lua',true,true);
  same(host,'a replaced map');
  @:privateAccess host.psychRuntimeBindings[0].release();
  check(@:privateAccess PsychRuntimeBindings.orderStates==null,'release kept the cached order');

  // Exclusions use the same path rules as before.
  var lua=new PlayState();
  var caller=scope(lua,'caller','Mods/Song/Caller.lua',true,true);
  scope(lua,'one','mods\\song\\One.lua',true,true);
  scope(lua,'two','mods/song/two.lua',true,true);
  var hits:Array<String>=[];
  for(key in ['caller','one','two']){
   var label=key;
   lua.hscriptStates.get(key).variables.set('hook',function():Dynamic {hits.push(label);return null;});
  }
  Reflect.callMethod(null,caller.variables.get('callOnLuas'),['hook',[],false,false,['ONE','song/two.lua']]);
  check(hits.join(',')=='caller','exclusions did not use case and separator insensitive paths: '+hits.join(','));

  var actuals=['mods/song/script.lua','Mods\\Song\\Script.LUA','mods/song/script.hx','script.lua',
   'mods/other/notscript.lua','mods/song/script.lua.bak','mods/song/script',null,''];
  var requests=['script','Script.lua','song/script','SONG\\SCRIPT.HX','mods/song/script.lua','cript',
   '','   ',null,'script.txt','/script','mods/song/script'];
  for(actual in actuals) for(request in requests)
   check(PsychRuntimeBindings.matches(actual,request)==oldMatches(actual,request),
    'path match changed for '+actual+' / '+request);
  for(index in 0...700)
   check(PsychRuntimeBindings.matches('dir/generated'+index+'.lua','generated'+index),
    'path cache overflow lost a match');

  // isRunning and get/setGlobalFromScript accept the same path forms.
  var running=new PlayState();
  var runner=scope(running,'runner','Mods/Runner.lua',true,true);
  running.compatScriptScopes.set('runner',[{scope:'runner',interp:runner,path:'Mods\\Runner.lua'}]);
  var isRunning=runner.variables.get('isRunning');
  check(Reflect.callMethod(null,isRunning,['runner'])==true,'isRunning missed an implied extension');
  check(Reflect.callMethod(null,isRunning,['MODS/RUNNER.LUA'])==true,'isRunning was case sensitive');
  check(Reflect.callMethod(null,isRunning,['unner'])==false,'isRunning matched a partial name');
  check(Reflect.callMethod(null,isRunning,[' '])==false,'isRunning matched a blank path');
  runner.variables.set('__compatClosed',true);
  check(Reflect.callMethod(null,isRunning,['runner'])==false,'isRunning reported a closed script');
  Sys.println('OK');
 }
}
'''


class PsychDispatchOrderCacheTest(unittest.TestCase):
    def test_cached_order_tracks_registry_and_paths_match_as_before(self):
        if not (ROOT / ".tools/haxe/haxe.exe").is_file() and not (ROOT / ".tools/haxe/haxe").is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        with tempfile.TemporaryDirectory(prefix="psych-dispatch-order-", dir=ROOT / "tmp") as folder:
            scratch = Path(folder)
            from psych_standard_fixture_support import write_standard_services_stub
            write_standard_services_stub(scratch)
            write_point_stub(scratch)
            (scratch / "PlayState.hx").write_text(PLAY_STATE, encoding="utf-8", newline="\n")
            (scratch / "LuaCompatInterp.hx").write_text(LUA_INTERP, encoding="utf-8", newline="\n")
            (scratch / "PsychHscriptSourceBindings.hx").write_text(HSCRIPT_PRESET, encoding="utf-8", newline="\n")
            (scratch / "PsychAchievementsIntegration.hx").write_text(
                "class PsychAchievementsIntegration {\n"
                " public static function installLua(host:Dynamic,interp:Dynamic,origin:String):Void {}\n"
                " public static function installHscript(host:Dynamic,interp:Dynamic,origin:String):Void {}\n"
                "}\n", encoding="utf-8", newline="\n")
            (scratch / "HxcCompatRuntime.hx").write_text(HXC_RUNTIME, encoding="utf-8", newline="\n")
            (scratch / "DispatchOrderFixture.hx").write_text(MAIN, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-iris/1,1,3"), "-cp", str(scratch),
                 "--run", "DispatchOrderFixture"],
                cwd=ROOT, capture_output=True, text=True, timeout=90,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
