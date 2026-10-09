"""Compile the native NV substate base against a recording Flixel fixture."""
import shutil
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND
from test_nightmare_vision_scripted_state import FIXTURES

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''import FixtureLog;
import NightmareVisionMusicBeatState.NightmareVisionMusicBeatTiming;
import NightmareVisionMusicBeatState.NightmareVisionMusicBeatStateHost;
import NightmareVisionMusicBeatSubstate.NightmareVisionMusicBeatSubstateHost;

class FixtureSubstate extends NightmareVisionMusicBeatSubstate {
 public function new(host:NightmareVisionMusicBeatSubstateHost) super(host);
}

class FixtureSortTarget {
 public var comparator:Dynamic;
 public var order:Int;
 public function new() {}
 public function sort(comparator:Dynamic, order:Int):Void {
  this.comparator=comparator; this.order=order;
 }
}

class NightmareVisionSubstateFixtureMain {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function count(prefix:String):Int {
  var result=0;
  for (entry in FixtureLog.entries) if (StringTools.startsWith(entry, prefix)) result++;
  return result;
 }
 static function callback(script:NightmareVisionScriptModule, name:String):Void {
  script.interp.variables.set(name, Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic {
   var value=args.length == 0 ? 'none' : Std.string(args[0]);
   FixtureLog.add('script:' + name + ':' + script.name + ':' + value);
   return 0;
  }));
 }
 static function main():Void {
  var timingStep=0;
  var decimalStep=0.0;
  var createdPrefix='';
  var createdName='';
  var loadedNames:Map<String,Bool>=[];
  var moduleRef:NightmareVisionScriptModule=null;
  var host:NightmareVisionMusicBeatSubstateHost={
   session:{},
   createStateFactory:function(name:String):(Void->flixel.FlxState) {
    return function():flixel.FlxState return null;
   },
   createScriptGroup:function(parent:Dynamic):NightmareVisionScriptGroup {
    return new FixtureScriptGroup(parent,
     function(name:String, callback:String, error:Dynamic):Void FixtureLog.add('report:' + callback));
   },
   createStateScript:function(name:String, parent:Dynamic,
    group:NightmareVisionScriptGroup):NightmareVisionStateScriptLoadResult
     return Missing('/owner/scripts/states/' + name + '.hscript'),
   createSubstateScript:function(prefix:String, name:String, parent:Dynamic,
    group:NightmareVisionScriptGroup):NightmareVisionStateScriptLoadResult {
    createdPrefix=prefix; createdName=name;
    check(group.parent == parent, 'script group must be parented before script creation');
    var sourcePath='/owner/scripts/' + prefix + '/' + name + '.hscript';
    if (name == 'MissingSubstate') return Missing(sourcePath);
    var sourceName=sourcePath;
    var suffix=1;
    while (loadedNames.exists(sourceName)) {sourceName=sourcePath + '_' + suffix; suffix++;}
    loadedNames.set(sourceName,true);
    var interp=new NightmareVisionScriptInterp(parent, group.sharedFields);
    var script=new NightmareVisionScriptModule(sourceName, interp,
     function(name:String, event:String, error:Dynamic):Void FixtureLog.add('report:' + event));
    for (event in ['onLoad','onStepHit','onBeatHit','onSectionHit','onUpdate','onDestroy'])
     callback(script, event);
    moduleRef=script;
    if (name == 'BrokenSubstate') {
     script.initialized=false;
     script.parsingException='syntax error';
     return ParseFailed(sourcePath, script);
    }
    group.parent={name:'scriptMutatedGroupParent'};
    return Loaded(sourcePath, sourceName, script);
   },
   failedScriptState:function(name:String):Void FixtureLog.add('fallback:' + name),
   report:function(name:String, event:String, error:Dynamic):Void FixtureLog.add('hostReport:' + event),
   callPlugins:function(event:String, args:Array<Dynamic>):Dynamic {
    FixtureLog.add('plugin:' + event); return NightmareVisionScriptGroup.CONTINUE_FUNC;
   },
   getControls:function():Dynamic return 'ownerControls',
   timing:function():NightmareVisionMusicBeatTiming
    return {step:timingStep, decimalStep:decimalStep},
   sectionBeats:function(section:Int):Float return section == 0 ? 1 : 2,
   sectionCount:function():Int return 3,
   hasSection:function(index:Int):Bool return index >= 0 && index < 3,
   hasSong:function():Bool return true,
   openTransition:function(state:Dynamic, incoming:Bool, ?complete:Void->Void):Bool return false,
   releaseStateResources:function(state:Dynamic):Void FixtureLog.add('releaseStateResources')
  };

  var substate=new FixtureSubstate(host);
  check(substate.controls == 'ownerControls', 'controls must come from the captured source host');
  check(substate.scriptPrefix == 'substates', 'default script prefix must match MusicBeatSubstate');
  check(substate.initStateScript(), 'source substate script must initialize');
  check(createdPrefix == 'substates' && createdName == 'FixtureSubstate',
   'default script lookup must use the class name and source substate prefix');
  check(moduleRef.interp.parent == substate, 'script interpreter must capture the substate parent');
  check(FixtureLog.entries.indexOf('script:onLoad:/owner/scripts/substates/FixtureSubstate.hscript:none') >= 0,
   'default initStateScript must call onLoad after parent binding');
  check(moduleRef.name=='/owner/scripts/substates/FixtureSubstate.hscript',
   'substate fromFile omits the source name so the resolved path becomes module.name');

  timingStep=1; decimalStep=1.5;
  substate.update(0.1);
  timingStep=4; decimalStep=4.25;
  var beforeJump=FixtureLog.entries.length;
  substate.update(0.2);
  var jumpEntries=FixtureLog.entries.slice(beforeJump);
  check(jumpEntries.indexOf('script:onBeatHit:/owner/scripts/substates/FixtureSubstate.hscript:1') < jumpEntries.indexOf('script:onStepHit:/owner/scripts/substates/FixtureSubstate.hscript:4'),
   'a changed beat step calls onBeatHit before onStepHit');
  check(count('script:onStepHit:/owner/scripts/substates/FixtureSubstate.hscript:') == 2,
   'a multi-step jump must dispatch one substate step callback, not catch up each step');
  check(count('script:onSectionHit:/owner/scripts/substates/FixtureSubstate.hscript:') == 1,
   'forward section crossing must call onSectionHit');
  check(jumpEntries.indexOf('script:onUpdate:/owner/scripts/substates/FixtureSubstate.hscript:0.2') < jumpEntries.indexOf('nativeSubstateUpdate'),
   'onUpdate must run before native child updates');
  check(substate.curBeat == 1 && substate.curStep == 4,
   'current beat and step must follow the owner timing callback');

  timingStep=8; decimalStep=8.5; substate.update(0.3);
  timingStep=2; decimalStep=2.25; substate.update(0.4);
  check(count('script:onStepHit:/owner/scripts/substates/FixtureSubstate.hscript:') == 4,
   'forward, jump and rollback step changes each dispatch once');
  check(substate.curSection == 0,
   'rollback must recompute the section cursor from source section data');
  check(count('plugin:') == 0, 'source substates do not dispatch state plugin hooks');

  var target=new FixtureSortTarget();
  substate.refreshZ(target);
  var lower:Dynamic={zIndex:1};
  var higher:Dynamic={zIndex:2};
  check(target.order == flixel.util.FlxSort.ASCENDING
   && Reflect.callMethod(target, target.comparator, [target.order, lower, higher]) < 0,
   'refreshZ must sort using the owner-aware zIndex view');

  var destroyIndex=FixtureLog.entries.length;
  substate.destroy();
  check(FixtureLog.entries.indexOf('script:onDestroy:/owner/scripts/substates/FixtureSubstate.hscript:none') > destroyIndex
   && FixtureLog.entries.indexOf('moduleDestroy:/owner/scripts/substates/FixtureSubstate.hscript') > FixtureLog.entries.indexOf('script:onDestroy:/owner/scripts/substates/FixtureSubstate.hscript:none')
   && FixtureLog.entries.indexOf('nativeDestroy') > FixtureLog.entries.indexOf('moduleDestroy:/owner/scripts/substates/FixtureSubstate.hscript'),
   'onDestroy must run before interpreter and native substate teardown');
  var destroyedLength=FixtureLog.entries.length;
  check(count('releaseStateResources')==1, 'unattached substate resources retire with the source group');
  substate.destroy();
  check(FixtureLog.entries.length == destroyedLength, 'repeated destroy must be idempotent');

  var missing=new FixtureSubstate(host);
  var missingStart=FixtureLog.entries.length;
  check(!missing.initStateScript('MissingSubstate'), 'missing source script must remain uninitialized');
  check(FixtureLog.entries.indexOf('groupCall:onLoad', missingStart) >= missingStart,
   'missing source script still calls the empty onLoad group when requested');
  missing.destroy();

  var repeated=new FixtureSubstate(host);
  check(repeated.initStateScript('FixtureSubstate', false), 'first repeated-load handle should initialize');
  var retained=repeated.scriptGroup.getScript('/owner/scripts/substates/FixtureSubstate.hscript');
  var beforeDuplicateDestroy=count('moduleDestroy:/owner/scripts/substates/FixtureSubstate.hscript');
  check(repeated.initStateScript('FixtureSubstate')
   && repeated.scriptGroup.getScript('/owner/scripts/substates/FixtureSubstate.hscript')==retained
   && repeated.scriptGroup.getScript('/owner/scripts/substates/FixtureSubstate.hscript_1')!=null
   && count('moduleDestroy:/owner/scripts/substates/FixtureSubstate.hscript')==beforeDuplicateDestroy,
   'substate repeats fromFile with the path name, and the source VM registers its suffixed repeated handle');
  check(repeated.initStateScript('MissingSubstate') && repeated.scripted
   && repeated.scriptName=='MissingSubstate',
   'missing substate reload calls onLoad and retains a prior scripted flag');
  var repeatedOnLoads=count('groupCall:onLoad');
  check(!repeated.initStateScript('BrokenSubstate') && repeated.scripted
   && repeated.scriptName=='BrokenSubstate'
   && count('groupCall:onLoad')==repeatedOnLoads,
   'parse-failed substate reload skips onLoad while retaining its prior scripted flag');
  repeated.destroy();

  var parseFailed=new FixtureSubstate(host);
  var parseStart=FixtureLog.entries.length;
  check(!parseFailed.initStateScript('BrokenSubstate')
   && FixtureLog.entries.indexOf('groupCall:onLoad', parseStart)<parseStart,
   'substate parse failure returns before onLoad');
  parseFailed.destroy();
 }
}
'''


class NightmareVisionMusicBeatSubstateTest(unittest.TestCase):
    def test_source_timing_script_callbacks_and_teardown(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            fixtures = dict(FIXTURES)
            fixtures["flixel/FlxSubState.hx"] = r'''package flixel;
import FixtureLog;
class FlxSubState extends FlxState {
 override public function update(elapsed:Float):Void FixtureLog.add('nativeSubstateUpdate');
}'''
            fixtures["NightmareVisionSubstateFixtureMain.hx"] = MAIN
            for relative, contents in fixtures.items():
                target = work / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(contents, encoding="utf-8")
            for source_name in (
                "NightmareVisionMusicBeatState.hx",
                "NightmareVisionMusicBeatSubstate.hx",
                "NightmareVisionStateScriptLoadResult.hx",
                "NightmareVisionScriptBroadcast.hx", "NightmareVisionScriptGroup.hx", "SourceScriptRegistrationOrder.hx",
            ):
                shutil.copyfile(ROOT / "source" / source_name, work / source_name)
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work),
                 "--main", "NightmareVisionSubstateFixtureMain", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
