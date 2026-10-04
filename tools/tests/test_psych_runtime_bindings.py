"""Exercise Psych runtime APIs through the real bindings and Iris bridge."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


PLAY_STATE = r'''package;
import hscript.Interp;

class PlayState {
 public var hscriptStates:Map<String, Interp> = [];
 public var hxcPayloadStates:Map<String, Bool> = [];
 public var psychRuntimeBindings:Array<PsychRuntimeBindings> = [];
 public var psychSourceCallbacks:PsychSourceCallbackRegistry;
 public var psychScriptVariables:Map<String, Dynamic> = [];
 public var compatScriptScopes:Map<String, Array<{scope:String, interp:Interp, path:String}>> = [];
 public var callEvents:Array<String> = [];
 public var sourceArgumentFlags:Array<Bool> = [];
 public var callArgumentArrays:Array<Array<Dynamic>> = [];
 public var addEvents:Array<Array<Dynamic>> = [];
 public var removeEvents:Array<Array<Dynamic>> = [];

 public function new() psychSourceCallbacks = new PsychSourceCallbackRegistry();

 public function compatPsychOwnerForScript(origin:String):String {
  if (origin != null && origin.indexOf('owner-b/') == 0) return 'assets/imported_mods/owner-b';
  return 'assets/imported_mods/owner-a';
 }

 public function compatAddLuaScript(path:String, ignoreAlreadyRunning:Bool=false,
  callerPath:String=null, hscript:Bool=false):Bool {
  addEvents.push([path, ignoreAlreadyRunning, callerPath, hscript]);
  return true;
 }

 public function compatRemoveLuaScript(path:String, callerPath:String=null,
  hscript:Bool=false):Bool {
  removeEvents.push([path, callerPath, hscript]);
  return true;
 }

 public function callHscript(name:String, args:Array<Dynamic>, scope:String,
  optional:Bool=false, ?returnValues:Array<Dynamic>, sourceArguments:Bool=false):Bool {
  sourceArgumentFlags.push(sourceArguments);
  callArgumentArrays.push(args);
  var interp = hscriptStates.get(scope);
  if (interp != null) interp.variables.set('__compatLastResult', null);
  if (interp == null || interp.variables.get('__compatClosed') == true) return false;
  var callback = interp.variables.get(name);
  if (!Reflect.isFunction(callback)) return false;
  try {
   var values = args == null ? [] : args;
   var result = Std.isOfType(interp, SourceIrisBridge)
    ? (cast interp:SourceIrisBridge).callFunction(name, values)
    : Reflect.callMethod(null, callback, values);
   interp.variables.set('__compatLastResult', result);
   if (returnValues != null) returnValues.push(result);
   callEvents.push(scope + ':' + name);
   return true;
  } catch (_:Dynamic) {
   return false;
  }
 }
}
'''


LUA_INTERP = r'''package;
class LuaCompatInterp extends hscript.Interp {
 public function new() super();
}
'''


# This is the narrow host-preset seam. Registration still runs through the
# production PsychSourceCallbackRegistry and SourceIrisBridge implementations.
HSCRIPT_PRESET = r'''package;
import hscript.Interp;

class PsychHscriptSourceBindings {
 final origin:String;
 final interp:Interp;
 final callbackBridge:Dynamic;
 public function new(_host:PlayState, interp:Interp, origin:String, callbackBridge:Dynamic) {
  this.origin=origin;this.interp=interp;this.callbackBridge=callbackBridge;
 }
 public function install():Void {
  var bridge=callbackBridge;
  var parent=Reflect.callMethod(bridge, Reflect.field(bridge,'parentFacade'), [origin,interp]);
  interp.variables.set('parentLua',parent);
  interp.variables.set('createCallback',function(name:String,callback:Dynamic,?target:Dynamic):Void {
   var destination=target==null?parent:target;
   Reflect.callMethod(bridge,Reflect.field(bridge,'registerLocal'),[origin,name,callback,destination]);
  });
  interp.variables.set('createGlobalCallback',function(name:String,callback:Dynamic):Void {
   Reflect.callMethod(bridge,Reflect.field(bridge,'registerGlobal'),[origin,name,callback]);
  });
 }
}
'''


HXC_RUNTIME = r'''package;
class HxcCompatRuntime {
 public static function getZIndex(_target:Dynamic):Dynamic return 0;
 public static function setZIndex(_target:Dynamic,value:Dynamic,?_op:String='='):Dynamic return value;
}
'''


def write_point_stub(classpath: Path) -> None:
    point = classpath / "flixel" / "math" / "FlxPoint.hx"
    point.parent.mkdir(parents=True, exist_ok=True)
    point.write_text(r'''package flixel.math;
class FlxPoint {
 public var x:Float; public var y:Float;
 public function new(x:Float=0,y:Float=0){this.x=x;this.y=y;}
 public static function weak(x:Float=0,y:Float=0):FlxPoint return new FlxPoint(x,y);
 public function set(x:Float=0,y:Float=0):FlxPoint {this.x=x;this.y=y;return this;}
 public function copyFrom(point:FlxPoint):FlxPoint return set(point.x,point.y);
}
class FlxCallbackPoint extends FlxPoint {
 final callback:FlxPoint->Void;
 public function new(setXCallback:FlxPoint->Void,?setYCallback:FlxPoint->Void,?setXYCallback:FlxPoint->Void){
  super();callback=setXYCallback!=null?setXYCallback:setXCallback;
 }
 override public function set(x:Float=0,y:Float=0):FlxCallbackPoint {super.set(x,y);if(callback!=null)callback(this);return this;}
}
''', encoding="utf-8", newline="\n")


MAIN = r'''package;
import hscript.Interp;

class PsychRuntimeBindingsFixture {
 static function check(value:Bool,message:String):Void if(!value)throw message;
 static function invoke(interp:Interp,name:String,args:Array<Dynamic>):Dynamic
  return Reflect.callMethod(null,interp.variables.get(name),args);

 static function addScope(host:PlayState,key:String,origin:String,lua:Bool):Interp {
  var interp:Interp=lua?new LuaCompatInterp():new Interp();
  interp.variables.set('__psychScoreGlobals',true);
  interp.variables.set('__compatDiagnosticSource',origin);
  host.hscriptStates.set(key,interp);
  var runtime=new PsychRuntimeBindings(host,interp,origin);
  runtime.install();
  host.psychRuntimeBindings.push(runtime);
  return interp;
 }

 static function setResult(interp:Interp,name:String,label:String,result:Dynamic,
  events:Array<String>):Void {
  interp.variables.set(name,function():Dynamic {events.push(label);return result;});
 }

 static function callWith(interp:Interp,name:String,hook:String,args:Array<Dynamic>,
  ignoreStops:Bool,ignoreSelf:Bool,exclusions:Array<String>,excludeValues:Array<Dynamic>):Dynamic {
  return invoke(interp,name,[hook,args,ignoreStops,ignoreSelf,exclusions,excludeValues]);
 }

 static function main():Void {
  var host=new PlayState();
  // Runtime bindings are registered in source-creation order. The APIs must
  // use that order even though the host registry itself is a StringMap.
  var luaOwner=addScope(host,'lua-owner','owner-a/owner.lua',true);
  var luaFirst=addScope(host,'lua-first','owner-a/lua-first.lua',true);
  var hscriptFirst=addScope(host,'hscript-first','owner-a/hscript-first.hx',false);
  var luaSecond=addScope(host,'lua-second','owner-a/lua-second.lua',true);
  var hscriptSecond=addScope(host,'hscript-second','owner-a/hscript-second.hx',false);
  var luaOtherOwner=addScope(host,'lua-other-owner','owner-b/owner.lua',true);
  var closedLua=addScope(host,'closed-lua','owner-a/closed.lua',true);
  closedLua.variables.set('__compatClosed',true);

  var events:Array<String>=[];
  setResult(luaOwner,'order','lua-owner','owner',events);
  setResult(luaFirst,'order','lua-first','first',events);
  setResult(luaSecond,'order','lua-second','second',events);
  var order=callWith(luaOwner,'callOnScripts','order',[],false,true,null,null);
  check(order=='second'&&events.join(',')=='lua-first,lua-second',
   'callOnScripts did not exclude self or preserve Lua creation order');

  events=[];
  setResult(luaOwner,'order','lua-owner','owner',events);
  setResult(luaFirst,'order','lua-first','first',events);
  setResult(luaSecond,'order','lua-second','second',events);
  order=callWith(luaOwner,'callOnScripts','order',[],false,false,null,null);
  check(order=='second'&&events.join(',')=='lua-owner,lua-first,lua-second',
   'ignoreSelf=false did not include the caller in creation order');

  events=[];
  for(scope in [luaFirst,luaSecond,luaOwner])
   setResult(scope,'fallback','lua:'+Std.string(scope.variables.get('__compatDiagnosticSource')),
    ScriptCallbackResult.CONTINUE,events);
  setResult(hscriptFirst,'fallback','hscript-first',ScriptCallbackResult.CONTINUE,events);
  setResult(hscriptSecond,'fallback','hscript-second','hscript-last',events);
  var fallback=invoke(luaOwner,'callOnScripts',['fallback']);
  check(fallback=='hscript-last'
   &&events.join(',')=='lua:owner-a/lua-first.lua,lua:owner-a/lua-second.lua,hscript-first,hscript-second',
   'default Continue handling or Lua-first HScript fallback changed');

  // A failed/missing runtime callback must not leak the scope's previous
  // __compatLastResult into this broadcast. Lua's donor call returns Continue
  // when the function is absent, which leads to the same HScript fallback.
  events=[];
  luaFirst.variables.set('__compatLastResult','stale-lua-result');
  luaSecond.variables.set('__compatLastResult','stale-lua-result');
  setResult(hscriptFirst,'missing-hook','hscript-first',ScriptCallbackResult.CONTINUE,events);
  setResult(hscriptSecond,'missing-hook','hscript-second','fallback-after-missing',events);
  var missingFallback=invoke(luaOwner,'callOnScripts',['missing-hook']);
  check(missingFallback=='fallback-after-missing'
   &&events.join(',')=='hscript-first,hscript-second',
   'missing Lua callbacks reused a stale result or failed to fall back');
  var missingLua=callWith(luaOwner,'callOnLuas','never-installed',[],false,true,null,null);
  check(missingLua==ScriptCallbackResult.CONTINUE,
   'an absent Lua callback did not preserve the family Continue result');

  events=[];
  setResult(luaFirst,'skip','lua-first','filtered',events);
  setResult(luaSecond,'skip','lua-second','filtered',events);
  setResult(hscriptFirst,'skip','hscript-first',ScriptCallbackResult.CONTINUE,events);
  setResult(hscriptSecond,'skip','hscript-second','hscript-after-filter',events);
  var custom=callWith(luaOwner,'callOnScripts','skip',[],false,true,
   ['lua-first.lua','hscript-first.hx'],['filtered',ScriptCallbackResult.CONTINUE]);
  check(custom=='hscript-after-filter'&&events.join(',')=='lua-second,hscript-second',
   'custom path/value exclusions did not filter scopes and results: '+Std.string(custom)+' / '+events.join(','));

  events=[];
  setResult(luaFirst,'stop','lua-first',ScriptCallbackResult.STOP_LUA,events);
  setResult(luaSecond,'stop','lua-second','must-not-run',events);
  setResult(hscriptFirst,'stop','hscript-first','must-not-fallback',events);
  var stopped=callWith(luaOwner,'callOnScripts','stop',[],false,true,null,null);
  check(stopped==ScriptCallbackResult.STOP_LUA&&events.join(',')=='lua-first',
   'Function_StopLua did not stop the Lua family and suppress fallback');

  events=[];
  setResult(luaFirst,'generic-stop','lua-first',ScriptCallbackResult.STOP,events);
  setResult(luaSecond,'generic-stop','lua-second','after-generic-stop',events);
  var genericStop=callWith(luaOwner,'callOnLuas','generic-stop',[],false,true,null,null);
  check(genericStop=='after-generic-stop'&&events.join(',')=='lua-first,lua-second',
   'Function_Stop incorrectly stopped a source Lua family');

  events=[];
  setResult(luaFirst,'ignore-stop','lua-first',ScriptCallbackResult.STOP_LUA,events);
  setResult(luaSecond,'ignore-stop','lua-second','after-ignored-stop',events);
  var ignored=callWith(luaOwner,'callOnLuas','ignore-stop',[],true,true,null,null);
  check(ignored=='after-ignored-stop'&&events.join(',')=='lua-first,lua-second',
   'ignoreStops did not continue past a family stop');

  events=[];
  setResult(hscriptFirst,'hstop','hscript-first',ScriptCallbackResult.STOP_HSCRIPT,events);
  setResult(hscriptSecond,'hstop','hscript-second','must-not-run',events);
  var hstop=callWith(luaOwner,'callOnHScript','hstop',[],false,true,null,null);
  check(hstop==ScriptCallbackResult.STOP_HSCRIPT&&events.join(',')=='hscript-first',
   'Function_StopHScript did not stop the HScript family');

  events=[];
  setResult(luaFirst,'all-stop','lua-first',ScriptCallbackResult.STOP_ALL,events);
  setResult(luaSecond,'all-stop','lua-second','must-not-run',events);
  setResult(hscriptFirst,'all-stop','hscript-first','must-not-fallback',events);
  var allStop=callWith(luaOwner,'callOnScripts','all-stop',[],false,true,null,null);
  check(allStop==ScriptCallbackResult.STOP_ALL&&events.join(',')=='lua-first',
   'Function_StopAll did not stop source dispatch');

  // Native lifecycle dispatch shares the same creation-ordered Psych scopes,
  // gives Lua scalar arguments first, then gives HScript its live object ABI.
  var unmarked=new Interp();
  unmarked.variables.set('dispatch-args',function(_index:Int,_noteType:String):Dynamic {
   throw 'an unmarked/native scope received a Psych lifecycle callback';
  });
  host.hscriptStates.set('unmarked-native',unmarked);
  var hxcScope=new Interp();
  hxcScope.variables.set('__psychScoreGlobals',true);
  hxcScope.variables.set('dispatch-args',function(_note:Dynamic):Dynamic {
   throw 'an HXC payload received a Psych lifecycle callback';
  });
  host.hscriptStates.set('psych-owned-hxc',hxcScope);
  host.hxcPayloadStates.set('psych-owned-hxc',true);
  var liveNote:Dynamic={noteData:2,marker:'live-note'};
  events=[];
  luaFirst.variables.set('dispatch-args',function(index:Int,noteType:String):Dynamic {
   check(index==5&&noteType=='Alt Animation','Lua lifecycle args were changed');
   events.push('lua-first');return ScriptCallbackResult.CONTINUE;
  });
  luaSecond.variables.set('dispatch-args',function(index:Int,noteType:String):Dynamic {
   check(index==5&&noteType=='Alt Animation','later Lua lifecycle args were changed');
   events.push('lua-second');return ScriptCallbackResult.CONTINUE;
  });
  hscriptFirst.variables.set('dispatch-args',function(note:Dynamic):Dynamic {
   check(note==liveNote,'HScript did not receive the live lifecycle object');
   events.push('hscript-first');return ScriptCallbackResult.CONTINUE;
  });
  hscriptSecond.variables.set('dispatch-args',function(note:Dynamic):Dynamic {
   check(note==liveNote,'later HScript did not receive the live lifecycle object');
   events.push('hscript-second');return 'hscript-last';
  });
  var sourceFlagStart=host.sourceArgumentFlags.length;
  var dispatched=PsychRuntimeBindings.dispatch(host,'dispatch-args',[5,'Alt Animation'],
   'Scripts',false,[liveNote]);
  check(dispatched=='hscript-last'
   &&events.join(',')=='lua-first,lua-second,hscript-first,hscript-second',
   'shared lifecycle dispatch lost source order, Lua-first fallback, split args, or Psych filtering');
  check(host.sourceArgumentFlags.length>sourceFlagStart,
   'shared lifecycle dispatch did not invoke HScript callbacks');
  for(index in sourceFlagStart...host.sourceArgumentFlags.length)
   check(host.sourceArgumentFlags[index],
    'shared lifecycle dispatch did not mark its donor-prepared arguments as raw');

  // Game-over observers installed by the host use Psych globals but are not
  // source-created scopes. They remain in ordinary broadcasts; the explicit
  // source-state exclusion filters only those exact host scope keys.
  var gameOverHost=new PlayState();
  var gameOverLua=addScope(gameOverHost,'source-gameover-lua','owner-a/gameover.lua',true);
  var gameOverHscript=addScope(gameOverHost,'source-gameover-hscript','owner-a/gameover.hx',false);
  var hostObserverKey='host-default-results-observer';
  var hostObserver=new Interp();
  hostObserver.variables.set('__psychScoreGlobals',true);
  hostObserver.variables.set('__compatDiagnosticSource','engine-installed/default-results.hx');
  gameOverHost.hscriptStates.set(hostObserverKey,hostObserver);
  var gameOverEvents:Array<String>=[];
  setResult(gameOverLua,'source-gameover-probe','source-lua',ScriptCallbackResult.CONTINUE,gameOverEvents);
  setResult(gameOverHscript,'source-gameover-probe','source-hscript',ScriptCallbackResult.CONTINUE,gameOverEvents);
  setResult(hostObserver,'source-gameover-probe','host-observer',ScriptCallbackResult.CONTINUE,gameOverEvents);
  PsychRuntimeBindings.dispatch(gameOverHost,'source-gameover-probe',[],'Scripts',true);
  check(gameOverEvents.join(',')=='source-lua,source-hscript,host-observer',
   'ordinary Psych dispatch stopped including host-installed observer scopes');
  gameOverEvents.resize(0);
  PsychRuntimeBindings.dispatch(gameOverHost,'source-gameover-probe',[],'Scripts',true,null,[hostObserverKey]);
  check(gameOverEvents.join(',')=='source-lua,source-hscript',
   'explicit scope-key exclusion removed source callbacks or retained the host observer: '+gameOverEvents.join(','));

  events=[];
  luaFirst.variables.set('dispatch-luas-only',function(value:Int):Dynamic {
   check(value==9,'Luas family changed its argument');events.push('lua-first');return 'lua-first-result';
  });
  luaSecond.variables.set('dispatch-luas-only',function(value:Int):Dynamic {
   check(value==9,'later Luas family changed its argument');events.push('lua-second');return 'lua-last';
  });
  hscriptFirst.variables.set('dispatch-luas-only',function(_note:Dynamic):Dynamic {
   throw 'Luas family invoked HScript';
  });
  var luasOnly=PsychRuntimeBindings.dispatch(host,'dispatch-luas-only',[9],'Luas');
  check(luasOnly=='lua-last'&&events.join(',')=='lua-first,lua-second',
   'shared Luas dispatch crossed into HScript or changed Lua order');

  // callHscript returns false on a missing/throwing callback. That failure
  // must be null inside the broadcast so stale scope results cannot suppress
  // the donor's Continue-triggered HScript fallback.
  events=[];
  luaFirst.variables.set('__compatLastResult','stale-before-dispatch-error');
  luaFirst.variables.set('dispatch-error',function():Dynamic throw 'fixture callback error');
  hscriptFirst.variables.set('dispatch-error',function():Dynamic {
   events.push('hscript-after-error');return 'recovered-after-error';
  });
  var afterError=PsychRuntimeBindings.dispatch(host,'dispatch-error',[]);
  check(afterError=='recovered-after-error'&&events.join(',')=='hscript-after-error'
   &&luaFirst.variables.get('__compatLastResult')==null,
   'failed lifecycle callback reused a stale result instead of falling back');

  var nativeOnlyHost=new PlayState();
  var nativeOnly=new Interp();
  nativeOnly.variables.set('__compatDiagnosticSource','native.hx');
  nativeOnlyHost.hscriptStates.set('native-only',nativeOnly);
  check(!PsychRuntimeBindings.hasScripts(nativeOnlyHost),
   'hasScripts included an unmarked native interpreter');
  nativeOnly.variables.set('__psychScoreGlobals',true);
  check(PsychRuntimeBindings.hasScripts(nativeOnlyHost),
   'hasScripts ignored an active Psych-marked interpreter');
  nativeOnly.variables.set('__compatClosed',true);
  check(!PsychRuntimeBindings.hasScripts(nativeOnlyHost),
   'hasScripts included a closed Psych interpreter');
  nativeOnly.variables.set('__compatClosed',false);
  nativeOnlyHost.hxcPayloadStates.set('native-only',true);
  check(!PsychRuntimeBindings.hasScripts(nativeOnlyHost),
   'hasScripts included an HXC payload even when it carried Psych globals');

  // getRunningScripts is deliberately a Lua diagnostic list, not a list of
  // every HScript or closed runtime scope.
  var running:Array<String>=invoke(luaOwner,'getRunningScripts',[]);
  check(running.contains('owner-a/owner.lua')&&running.contains('owner-b/owner.lua')
   &&!running.contains('owner-a/hscript-first.hx')&&!running.contains('owner-a/closed.lua'),
   'getRunningScripts included a non-Lua or closed interpreter');

  // callScript searches Lua scopes in creation order and selects the first
  // matching script path; HScript scopes cannot shadow that lookup.
  var firstMatch=addScope(host,'lua-match-first','owner-a/path-one/same.lua',true);
  var secondMatch=addScope(host,'lua-match-second','owner-a/path-two/same.lua',true);
  var hscriptMatch=addScope(host,'hscript-match','owner-a/same.lua',false);
  events=[];
  setResult(firstMatch,'specific','first-match','first-result',events);
  setResult(secondMatch,'specific','second-match','second-result',events);
  setResult(hscriptMatch,'specific','hscript-match','hscript-result',events);
  host.compatScriptScopes.set('same-identity',[
   {scope:'hscript-match',interp:hscriptMatch,path:'owner-a/same.lua'},
   {scope:'lua-match-first',interp:firstMatch,path:'owner-a/path-one/same.lua'},
   {scope:'lua-match-second',interp:secondMatch,path:'owner-a/path-two/same.lua'}
  ]);
  var specific=invoke(luaOwner,'callScript',['same','specific']);
  check(specific=='first-result'&&events.join(',')=='first-match',
   'callScript did not select the first matching Lua registration only');

  var callerPayload:Dynamic={note:'raw-live-note',meta:{keep:true}};
  var callerArgs:Array<Dynamic>=[callerPayload,'preserve-me'];
  var targetedValues:Array<Dynamic>=null;
  firstMatch.variables.set('goodNoteHit',function(note:Dynamic,tag:String):Dynamic {
   targetedValues=[note,tag];return 'targeted-raw-result';
  });
  var targetCallStart=host.callArgumentArrays.length;
  var targetFlagStart=host.sourceArgumentFlags.length;
  var targeted=invoke(luaOwner,'callScript',['path-one/same.lua','goodNoteHit',callerArgs]);
  check(targeted=='targeted-raw-result'&&targetedValues!=null
   &&targetedValues[0]==callerPayload&&targetedValues[1]=='preserve-me',
   'callScript projected or changed the caller-supplied note callback payload');
  check(host.callArgumentArrays.length==targetCallStart+1
   &&host.callArgumentArrays[targetCallStart]==callerArgs,
   'callScript did not forward the original caller argument array');
  check(host.sourceArgumentFlags.length==targetFlagStart+1
   &&host.sourceArgumentFlags[targetFlagStart],
   'targeted callScript did not mark caller arguments as source-prepared');
  check(callerArgs.length==2&&callerArgs[0]==callerPayload&&callerArgs[1]=='preserve-me',
   'targeted callScript mutated the caller-owned argument array');

  secondMatch.variables.set('__compatLastResult','later-match-must-not-run');
  firstMatch.variables.set('__compatLastResult','stale-specific-result');
  var missingSpecific=invoke(luaOwner,'callScript',['same','never-installed']);
  check(missingSpecific==ScriptCallbackResult.CONTINUE
   &&secondMatch.variables.get('__compatLastResult')=='later-match-must-not-run',
   'callScript missing callback did not return Continue or fell through to a later match');

  firstMatch.variables.set('returnsNull',function():Dynamic return null);
  firstMatch.variables.set('__compatLastResult','stale-before-null');
  var nullSpecific=invoke(luaOwner,'callScript',['same','returnsNull']);
  check(nullSpecific==ScriptCallbackResult.CONTINUE
   &&secondMatch.variables.get('__compatLastResult')=='later-match-must-not-run',
   'callScript did not normalize a null Lua result to Continue');

  firstMatch.variables.set('throws',function():Dynamic throw 'fixture Lua callback error');
  firstMatch.variables.set('__compatLastResult','stale-before-error');
  var failedSpecific=invoke(luaOwner,'callScript',['same','throws']);
  check(failedSpecific==ScriptCallbackResult.CONTINUE
   &&secondMatch.variables.get('__compatLastResult')=='later-match-must-not-run',
   'callScript failure did not return Continue or fell through to a later match');

  var noScript=invoke(luaOwner,'callScript',['not-loaded-anywhere','specific']);
  check(noScript==null,'callScript should return null only when no Lua path matches');

  // The embedded source module is a real SourceIrisBridge and callbacks are
  // registered through the production per-owner callback registry.
  var runA=luaOwner.variables.get('runHaxeCode');
  Reflect.callMethod(null,runA,[
   'persistent = 5; function twice(value) return persistent + value; '
    +'createCallback("localFromHaxe", function(value) return value + 8); '
    +'createGlobalCallback("ownerGlobal", function(value) return value * 2); '
    +'createGlobalCallback("brokenFromHaxe", function() { var inner = 1; throw "fixture callback failure"; });'
  ]);
  Reflect.callMethod(null,runA,['persistent += 1; twice(3);']);
  check(Reflect.callMethod(null,luaOwner.variables.get('runHaxeFunction'),['twice',[4]])==10,
   'embedded HScript function/global state was not persistent');
  check(luaOwner.variables.exists('localFromHaxe')&&!luaFirst.variables.exists('localFromHaxe')
   &&luaOwner.variables.exists('ownerGlobal')&&luaFirst.variables.exists('ownerGlobal'),
   'local/global callback scopes were not separated within the owner');

  var futureLua=addScope(host,'lua-future','owner-a/future.lua',true);
  var futureOtherOwner=addScope(host,'lua-future-b','owner-b/future.lua',true);
  check(futureLua.variables.exists('ownerGlobal')&&!futureLua.variables.exists('localFromHaxe')
   &&!futureOtherOwner.variables.exists('ownerGlobal'),
   'future Lua did not receive only its owner global callback');
  check(Reflect.callMethod(null,futureLua.variables.get('ownerGlobal'),[6])==12,
   'future Lua global callback did not execute');

  var runB=luaOtherOwner.variables.get('runHaxeCode');
  Reflect.callMethod(null,runB,[
   'persistent = 100; function twice(value) return persistent + value; '
    +'createGlobalCallback("ownerGlobal", function(value) return value * 5);'
  ]);
  check(Reflect.callMethod(null,runB,['twice(1);'])==101
   &&Reflect.callMethod(null,luaOwner.variables.get('runHaxeFunction'),['twice',[4]])==10
   &&Reflect.callMethod(null,luaOwner.variables.get('ownerGlobal'),[3])==6,
   'embedded functions or same-named globals crossed owner boundaries');

  var callbackFailed=false;
  try Reflect.callMethod(null,luaOwner.variables.get('brokenFromHaxe'),[])
  catch(_:Dynamic) callbackFailed=true;
  check(callbackFailed&&Reflect.callMethod(null,luaOwner.variables.get('runHaxeFunction'),['twice',[5]])==11,
   'embedded callback failure did not restore the Iris execution frame');

  var missingImport=false;
  try Reflect.callMethod(null,runA,['import definitely.missing.PsychBinding;'])
  catch(error:Dynamic) missingImport=Std.string(error).indexOf('definitely.missing.PsychBinding')>=0;
  check(missingImport&&Reflect.callMethod(null,runA,['afterImportFailure = 33; afterImportFailure;'])==33,
   'missing import diagnostic or subsequent embedded execution recovery failed');

  Sys.println('OK');
 }
}
'''


class PsychRuntimeBindingsTest(unittest.TestCase):
    def test_runtime_broadcast_dispatch_and_embedded_source_callbacks(self):
        if not (ROOT / ".tools/haxe/haxe.exe").is_file() and not (ROOT / ".tools/haxe/haxe").is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        with tempfile.TemporaryDirectory(prefix="psych-runtime-bindings-", dir=ROOT / "tmp") as folder:
            scratch = Path(folder)
            write_point_stub(scratch)
            (scratch / "PlayState.hx").write_text(PLAY_STATE, encoding="utf-8", newline="\n")
            (scratch / "LuaCompatInterp.hx").write_text(LUA_INTERP, encoding="utf-8", newline="\n")
            (scratch / "PsychHscriptSourceBindings.hx").write_text(HSCRIPT_PRESET, encoding="utf-8", newline="\n")
            (scratch / "HxcCompatRuntime.hx").write_text(HXC_RUNTIME, encoding="utf-8", newline="\n")
            (scratch / "PsychRuntimeBindingsFixture.hx").write_text(MAIN, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-iris/1,1,3"), "-cp", str(scratch),
                 "--run", "PsychRuntimeBindingsFixture"],
                cwd=ROOT, capture_output=True, text=True, timeout=90,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
