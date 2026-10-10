"""Compile the native NV state wrappers against a recording Flixel fixture."""
import subprocess
import shutil
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]


FIXTURES = {
    "FixtureLog.hx": r'''class FixtureLog {
 public static var entries:Array<String> = [];
 public static function add(value:String):Void entries.push(value);
}''',
    "flixel/FlxG.hx": r'''package flixel;
import FixtureLog;
class FlxG {
 public static var sound:FixtureSoundManager = new FixtureSoundManager();
 public static var state:FlxState;
}
class FixtureSoundManager {
 public var music:FixtureMusic;
 public function new() music = new FixtureMusic();
}
class FixtureMusic {
 public var fadeTween:FixtureTween;
 public var onComplete:Void->Void;
 public function new() fadeTween = new FixtureTween();
}
class FixtureTween { public function new() {} public function cancel():Void FixtureLog.add('musicFadeCancel'); }
''',
    "flixel/FlxState.hx": r'''package flixel;
import FixtureLog;
class FlxState {
 public var transIn:Dynamic;
 public var transOut:Dynamic;
 public function new() { transIn='hostIn'; transOut='hostOut'; }
 public function create():Void {}
 public function update(elapsed:Float):Void {}
 public function closeSubState():Void FixtureLog.add('nativeCloseSubState');
 public function startOutro(onOutroComplete:Void->Void):Void {
  FixtureLog.add('nativeOutro'); onOutroComplete();
 }
 public function destroy():Void FixtureLog.add('nativeDestroy');
}
''',
    "flixel/FlxBasic.hx": r'''package flixel;
class FlxBasic {}''',
    "flixel/util/FlxSort.hx": r'''package flixel.util;
class FlxSort {
 public static inline var ASCENDING:Int=1;
 public static function byValues(order:Int, first:Float, second:Float):Int
  return first < second ? -order : first > second ? order : 0;
}''',
    "flixel/addons/ui/FlxUIState.hx": r'''package flixel.addons.ui;
import FixtureLog;
class FlxUIState extends flixel.FlxState {
 override public function create():Void { FixtureLog.add('nativeCreate'); }
 override public function update(elapsed:Float):Void { FixtureLog.add('nativeUpdate'); }
}
''',
    "crowplexus/hscript/Expr.hx": r'''package crowplexus.hscript;
class Expr { public function new() {} }''',
    "NightmareVisionScriptParser.hx": r'''class NightmareVisionScriptParser {
 public function new() {}
 public function parseString(source:String, name:String):crowplexus.hscript.Expr
  return new crowplexus.hscript.Expr();
}''',
    "FixtureScriptGroup.hx": r'''import FixtureLog;
class FixtureScriptGroup extends NightmareVisionScriptGroup {
 public function new(parent:Dynamic, report:String->String->Dynamic->Void) {
  super(parent, report);
 }
 override public function call(event:String, ?args:Array<Dynamic>,
  ignoreStops:Bool=false, ?exclusions:Array<String>):Dynamic {
  FixtureLog.add('groupCall:' + event);
  return super.call(event, args, ignoreStops, exclusions);
 }
}''',
    "HxcCompatRuntime.hx": r'''class HxcCompatRuntime {
 public static function getZIndex(target:Dynamic):Dynamic {
  var value=Reflect.field(target, 'zIndex'); return value == null ? 0 : value;
 }
}''',
    "NightmareVisionScriptInterp.hx": r'''class NightmareVisionScriptInterp {
 public var parent:Dynamic;
 public var sharedFields:Map<String,Dynamic>;
 public var variables:Map<String,Dynamic> = new Map();
 public function new(?parent:Dynamic, ?sharedFields:Map<String,Dynamic>) {
  this.parent=parent; this.sharedFields=sharedFields;
 }
 public function release():Void { variables.clear(); parent=null; sharedFields=null; }
}''',
    "NightmareVisionScriptModule.hx": r'''class NightmareVisionScriptModule {
 public var name:String;
 public var interp:NightmareVisionScriptInterp;
 public var initialized:Bool=true;
 public var parsingException:Dynamic=null;
 public var released:Bool=false;
 final report:String->String->Dynamic->Void;
 public function new(name:String, interp:NightmareVisionScriptInterp,
  report:String->String->Dynamic->Void) {
  this.name=name; this.interp=interp; this.report=report;
 }
 public function parsingFailed():Bool return parsingException != null;
 public function executeProgram(value:crowplexus.hscript.Expr):Bool return true;
 public function exists(callback:String):Bool
  return !released && interp != null && interp.variables.exists(callback);
 public function callValue(callback:String, ?args:Array<Dynamic>, ?receiver:Dynamic):Dynamic {
  if (!exists(callback)) return null;
  var method=interp.variables.get(callback);
  try return Reflect.callMethod(receiver, method, args == null ? [] : args)
  catch (error:Dynamic) { report(name, callback, error); return null; }
 }
 public function destroy():Void {
  if (released) return;
  released=true;
  if (interp != null) interp.release();
  interp=null;
  FixtureLog.add('moduleDestroy:' + name);
 }
}''',
    "NightmareVisionStateFixtureMain.hx": r'''import FixtureLog;
import NightmareVisionMusicBeatState.NightmareVisionMusicBeatStateHost;
import NightmareVisionMusicBeatState.NightmareVisionMusicBeatTiming;

class NightmareVisionStateFixtureMain {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function count(value:String):Int {
  var result=0;
  for (entry in FixtureLog.entries) if (entry == value) result++;
  return result;
 }
 static function addCallback(script:NightmareVisionScriptModule, name:String,
  result:Dynamic, ?callback:Void->Void):Void {
  script.interp.variables.set(name, Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic {
   FixtureLog.add('script:' + name + ':' + script.name);
   if (callback != null) callback();
   return result;
  }));
 }
 static function main():Void {
 var session:Dynamic={released:false};
 var scriptRef:NightmareVisionScriptModule=null;
 var failedHandle:NightmareVisionScriptModule=null;
  var host:NightmareVisionMusicBeatStateHost={
   session:session,
   createStateFactory:function(name:String):(Void->flixel.FlxState) {
    return function():flixel.FlxState return null;
   },
   createScriptGroup:function(parent:Dynamic):NightmareVisionScriptGroup {
    return new FixtureScriptGroup(parent,
     function(name:String, callback:String, error:Dynamic):Void
      FixtureLog.add('report:' + callback));
   },
   createStateScript:function(name:String, parent:Dynamic,
    group:NightmareVisionScriptGroup):NightmareVisionStateScriptLoadResult {
    check(group.parent == parent, 'group parent must be bound before script creation');
    var sourcePath='/owner/scripts/states/' + name + '.hscript';
    if (group.exists(sourcePath)) return AlreadyLoaded(sourcePath);
    if (name == 'MissingState') return Missing(sourcePath);
    var interp=new NightmareVisionScriptInterp(parent, group.sharedFields);
    var script=new NightmareVisionScriptModule(name, interp,
     function(name:String, callback:String, error:Dynamic):Void
      FixtureLog.add('report:' + callback));
    addCallback(script, 'onLoad', 0, function():Void
     check(interp.parent == parent, 'onLoad must see the state parent'));
    addCallback(script, 'onCreate', 0);
    addCallback(script, 'onCreatePost', 0);
    addCallback(script, 'onBeatHit', NightmareVisionScriptGroup.HALT_FUNC);
    addCallback(script, 'onStepHit', NightmareVisionScriptGroup.STOP_FUNC);
    addCallback(script, 'onUpdate', NightmareVisionScriptGroup.STOP_FUNC);
    addCallback(script, 'onUpdatePost', 0);
    addCallback(script, 'onCloseSubState', 0);
    addCallback(script, 'onDestroy', 0);
    if (name == 'BrokenState') {
     script.initialized=false;
     script.parsingException='syntax error';
     failedHandle=script;
     return ParseFailed(sourcePath, script);
    }
    scriptRef=script;
    group.parent={name:'scriptMutatedGroupParent'};
    return Loaded(sourcePath, name, script);
   },
   failedScriptState:function(name:String):Void FixtureLog.add('fallback:' + name),
   report:function(name:String, callback:String, error:Dynamic):Void
    FixtureLog.add('hostReport:' + callback),
   callPlugins:function(event:String, args:Array<Dynamic>):Dynamic {
    FixtureLog.add('plugin:' + event);
    return NightmareVisionScriptGroup.CONTINUE_FUNC;
   },
   getControls:function():Dynamic return 'ownerControls',
   timing:function():NightmareVisionMusicBeatTiming return {step:4, decimalStep:4.25},
   sectionBeats:function(section:Int):Float return 4,
   sectionCount:function():Int return 0,
   hasSection:function(index:Int):Bool return false,
   hasSong:function():Bool return false,
   openTransition:function(state:Dynamic, incoming:Bool, ?complete:Void->Void):Bool {
    FixtureLog.add('transition:' + (incoming ? 'incoming' : 'outgoing'));
    return false;
   },
   releaseStateResources:function(state:Dynamic):Void FixtureLog.add('releaseStateResources'),
   cancelMenuVocals:function():Void FixtureLog.add('cancelMenuVocals')
  };

  var state=new NightmareVisionScriptedState('FixtureState', host);
  check(state.sourceSession == session && state.scripted, 'captured session and state script must be retained');
  check(state.transIn == null && state.transOut == null,
   'native base must clear inherited host transitions');
  check(scriptRef.interp.parent == state, 'script module must capture this state as parent');
  check(scriptRef.name == 'FixtureState', 'state fromFile receives the selected script name');
  var observerInterp=new NightmareVisionScriptInterp(state, state.scriptGroup.sharedFields);
  var observer=new NightmareVisionScriptModule('observer', observerInterp,
   function(name:String, callback:String, error:Dynamic):Void throw error);
  addCallback(observer, 'onBeatHit', 0);
  addCallback(observer, 'onStepHit', 0);
  addCallback(observer, 'onUpdate', 0);
  addCallback(observer, 'onCloseSubState', 0);
  addCallback(observer, 'onDestroy', 0);
  check(state.scriptGroup.addScript(observer), 'second state script should join the group');

  check(FixtureLog.entries[0] == 'groupCall:onLoad'
   && FixtureLog.entries[1] == 'script:onLoad:FixtureState',
   'onLoad must run in the scripted state constructor');
  state.create();
  check(FixtureLog.entries.slice(2, 7).join(',') ==
   'nativeCreate,transition:incoming,plugin:onStateCreate,groupCall:onCreate,script:onCreate:FixtureState',
   'create lifecycle must follow source ordering');
  check(FixtureLog.entries.indexOf('script:onCreatePost:FixtureState') < 0,
   'generic ScriptedState must not invent onCreatePost');

  state.update(0.125);
  var entries=FixtureLog.entries;
  check(entries.indexOf('script:onBeatHit:FixtureState') < entries.indexOf('plugin:onBeatHit'),
   'script beat callback must precede persistent plugins');
  var beatIndex=entries.indexOf('script:onBeatHit:FixtureState');
  check(entries[beatIndex + 1] == 'plugin:onBeatHit'
   && entries[beatIndex + 3] == 'script:onStepHit:FixtureState',
   'beat callback must precede the same-step callback');
  check(entries.indexOf('script:onBeatHit:observer') < 0,
   'HALT must stop the current group broadcast while allowing native beat handling');
  check(entries.indexOf('script:onStepHit:observer') > entries.indexOf('script:onStepHit:FixtureState'),
   'STOP must continue ScriptGroup broadcasting');
  check(count('script:onStepHit:FixtureState') == 4 && count('plugin:onStepHit') == 4,
   'timing catch-up must dispatch every crossed step and plugin hook');
  check(entries.indexOf('script:onUpdate:observer') > entries.indexOf('script:onUpdate:FixtureState'),
   'STOP from onUpdate must continue ScriptGroup broadcasting');
  check(entries.indexOf('script:onUpdate:observer') < entries.indexOf('nativeUpdate'),
   'onUpdate must run before native child updates');
  check(entries.indexOf('script:onUpdatePost:FixtureState') < 0,
   'generic MusicBeatState must not invent onUpdatePost');

  state.closeSubState();
  check(entries.indexOf('script:onCloseSubState:FixtureState') < entries.indexOf('nativeCloseSubState'),
   'substate close callback must run before native close');
  var outroComplete=false;
  state.startOutro(function():Void outroComplete=true);
  check(entries.indexOf('musicFadeCancel') < entries.indexOf('transition:outgoing'),
   'outro must cancel the menu music fade first');
  check(entries.indexOf('cancelMenuVocals') < entries.indexOf('transition:outgoing'),
   'outro must cancel menu vocal fade before transition');
  check(outroComplete, 'unhandled source transition must delegate to native completion');
  check(flixel.FlxG.sound.music.onComplete == null, 'music completion callback must be cleared');

  check(state.initStateScript('MissingState') && state.scripted
   && state.scriptName=='MissingState',
   'missing reload updates scriptName, calls onLoad, and retains a prior scripted flag');
  var parseReloadStart=count('groupCall:onLoad');
  check(!state.initStateScript('BrokenState') && state.scripted
   && state.scriptName=='BrokenState' && failedHandle.released
   && count('groupCall:onLoad')==parseReloadStart,
   'parse-failed reload returns false, releases its handle, skips onLoad, and retains the scripted flag');

  state.destroy();
  check(entries.indexOf('script:onDestroy:FixtureState') < entries.indexOf('moduleDestroy:FixtureState'),
   'onDestroy must run before the source interpreter is released');
  check(entries.indexOf('releaseStateResources') < entries.indexOf('nativeDestroy'),
   'state-local cleanup must run before native destruction');
  check(session.released == false, 'state destruction must leave the family session to its factory owner');
  check(scriptRef.released && observer.released, 'state interpreter group must be released');
  var destroyedLength=entries.length;
  state.destroy();
  check(entries.length == destroyedLength, 'repeated destroy must be idempotent');

  var repeated=new NightmareVisionMusicBeatState(host);
  repeated.scriptName='prior';
  var sourcePath='/owner/scripts/states/PathLoaded.hscript';
  var pathModule=new NightmareVisionScriptModule(sourcePath,
   new NightmareVisionScriptInterp(repeated, repeated.scriptGroup.sharedFields),
   function(name:String, callback:String, error:Dynamic):Void {});
  check(repeated.scriptGroup.addScript(pathModule), 'path-named source module should register');
  var loadedBefore=scriptRef;
  var onLoadBefore=count('groupCall:onLoad');
  check(repeated.initStateScript('PathLoaded') && repeated.scriptName=='prior'
   && count('groupCall:onLoad')==onLoadBefore && scriptRef==loadedBefore,
   'state group lookup uses resolved file path and returns before name, load, or onLoad changes');
  repeated.destroy();

  var missingBase=new NightmareVisionMusicBeatState(host);
  var missingStart=entries.length;
  check(!missingBase.initStateScript('MissingState')
   && missingBase.scriptName=='MissingState'
   && FixtureLog.entries.indexOf('groupCall:onLoad', missingStart)>=missingStart,
   'missing state script retains its name and calls empty-group onLoad');
  missingBase.destroy();

  var failedBase=new NightmareVisionMusicBeatState(host);
  var failedStart=entries.length;
  check(!failedBase.initStateScript('BrokenState')
   && failedBase.scriptName=='BrokenState' && failedHandle.released
   && FixtureLog.entries.indexOf('groupCall:onLoad', failedStart)<failedStart,
   'parse failure releases its handle and returns before onLoad');
  failedBase.destroy();

  host.createStateScript=function(name:String, parent:Dynamic,
   group:NightmareVisionScriptGroup):NightmareVisionStateScriptLoadResult
    return Missing('/owner/scripts/states/' + name + '.hscript');
  var failedStart=entries.length;
  var failed=new NightmareVisionScriptedState('MissingState', host);
  check(!failed.scripted && entries[failedStart] == 'groupCall:onLoad',
   'failed script still constructs and broadcasts empty onLoad');
  failed.create();
  check(entries[failedStart + 1] == 'nativeCreate'
   && entries[failedStart + 4] == 'fallback:MissingState',
   'failed script requests its owner fallback after base create');
  check(entries.indexOf('script:onCreate:MissingState') < 0,
   'failed script must not receive onCreate');
  failed.destroy();

  var beforeCreate=new NightmareVisionMusicBeatState(host);
  var releaseCount=count('releaseStateResources');
  beforeCreate.destroy();
  check(count('releaseStateResources') == releaseCount + 1,
   'redirected uncreated state must release only its state-local resources');
  check(session.released == false,
   'uncreated candidate destruction must keep the family session alive');
 }
}
''',
}


class NightmareVisionScriptedStateTest(unittest.TestCase):
    def test_constructor_lifecycle_timing_cancellation_and_session_ownership(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            for relative, contents in FIXTURES.items():
                target = work / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(contents, encoding="utf-8")
            for source_name in (
                "NightmareVisionMusicBeatState.hx", "SourceBeatSections.hx",
                "NightmareVisionStateScriptLoadResult.hx",
                "NightmareVisionScriptedState.hx",
                "NightmareVisionScriptBroadcast.hx", "NightmareVisionScriptGroup.hx",
            ):
                shutil.copyfile(ROOT / "source" / source_name, work / source_name)
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work),
                 "--main", "NightmareVisionStateFixtureMain", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
