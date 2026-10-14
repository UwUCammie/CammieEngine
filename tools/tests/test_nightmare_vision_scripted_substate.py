"""Compile the NV scripted substate wrapper against a recording Flixel fixture."""
import shutil
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND
from test_nightmare_vision_scripted_state import FIXTURES

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''import FixtureLog;
import NightmareVisionMusicBeatState.NightmareVisionMusicBeatTiming;
import NightmareVisionMusicBeatSubstate.NightmareVisionMusicBeatSubstateHost;

class ScriptedSubstateFixtureMain {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var requested:Array<String>=[];
  var host:NightmareVisionMusicBeatSubstateHost={
   session:{},
   createStateFactory:function(name:String):(Void->flixel.FlxState) return function():flixel.FlxState return null,
   createScriptGroup:function(parent:Dynamic):NightmareVisionScriptGroup
    return new FixtureScriptGroup(parent, function(name:String, callback:String, error:Dynamic):Void
     FixtureLog.add('report:' + callback)),
   createStateScript:function(name:String, parent:Dynamic, group:NightmareVisionScriptGroup):NightmareVisionStateScriptLoadResult
    return Missing(name),
   createSubstateScript:function(prefix:String, name:String, parent:Dynamic,
    group:NightmareVisionScriptGroup):NightmareVisionStateScriptLoadResult {
    requested.push(prefix + '/' + name);
    var sourcePath='/owner/scripts/' + prefix + '/' + name + '.hx';
    if (name == 'Nowhere') return Missing(sourcePath);
    var interp=new NightmareVisionScriptInterp(parent, group.sharedFields);
    var script=new NightmareVisionScriptModule(sourcePath, interp,
     function(name:String, callback:String, error:Dynamic):Void FixtureLog.add('report:' + callback));
    for (event in ['onLoad', 'onCreate']) {
     var captured=event;
     interp.variables.set(event, Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic {
      check(interp.parent == parent, captured + ' must see the substate as parent');
      FixtureLog.add('script:' + captured);
      return 0;
     }));
    }
    // A script may repoint its group while loading; the wrapper must rebind it.
    group.parent={name:'scriptMutatedGroupParent'};
    return Loaded(sourcePath, sourcePath, script);
   },
   failedScriptState:function(name:String):Void FixtureLog.add('fallback:' + name),
   report:function(name:String, callback:String, error:Dynamic):Void FixtureLog.add('hostReport:' + callback),
   callPlugins:function(event:String, args:Array<Dynamic>):Dynamic return NightmareVisionScriptGroup.CONTINUE_FUNC,
   getControls:function():Dynamic return null,
   timing:function():NightmareVisionMusicBeatTiming return {step:0, decimalStep:0},
   sectionBeats:function(section:Int):Float return 4,
   sectionCount:function():Int return 0,
   hasSection:function(index:Int):Bool return false,
   hasSong:function():Bool return false,
   openTransition:function(state:Dynamic, incoming:Bool, ?complete:Void->Void):Bool return false,
   releaseStateResources:function(state:Dynamic):Void FixtureLog.add('releaseStateResources')
  };

  var pause=new NightmareVisionScriptedSubstate('Pause', host);
  check(requested.join(',') == 'substates/Pause', 'the script is looked up under scripts/substates by name');
  check(pause.scripted && pause.scriptName == 'Pause', 'a found script marks the substate as scripted');
  check(pause.scriptGroup.parent == pause, 'the group parent is rebound to the substate after loading');
  check(FixtureLog.entries.indexOf('script:onLoad') >= 0 && FixtureLog.entries.indexOf('script:onCreate') < 0,
   'onLoad runs in the constructor, onCreate waits for create');
  check(FixtureLog.entries.filter(function(entry) return entry == 'script:onLoad').length == 1,
   'onLoad runs exactly once');
  pause.create();
  check(FixtureLog.entries.indexOf('script:onCreate') > FixtureLog.entries.indexOf('script:onLoad'),
   'create calls onCreate after the base create');
  check(FixtureLog.entries.indexOf('fallback:Pause') < 0, 'a loaded script never takes the failure path');
  pause.destroy();

  var start=FixtureLog.entries.length;
  var missing=new NightmareVisionScriptedSubstate('Nowhere', host);
  check(!missing.scripted && missing.scriptName == 'Nowhere', 'a missing script leaves the substate unscripted');
  check(FixtureLog.entries.indexOf('groupCall:onLoad', start) >= start, 'the empty group still gets onLoad');
  missing.create();
  check(FixtureLog.entries.indexOf('fallback:Nowhere', start) > start,
   'a missing script hands its name to the owner failure path');
  missing.destroy();
 }
}
'''


class NightmareVisionScriptedSubstateTest(unittest.TestCase):
    def test_constructor_onload_create_oncreate_and_missing_script_failure(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            fixtures = dict(FIXTURES)
            fixtures["flixel/FlxSubState.hx"] = r'''package flixel;
class FlxSubState extends FlxState {}'''
            fixtures["ScriptedSubstateFixtureMain.hx"] = MAIN
            for relative, contents in fixtures.items():
                target = work / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(contents, encoding="utf-8")
            for source_name in (
                "NightmareVisionMusicBeatState.hx", "SourceBeatSections.hx",
                "NightmareVisionMusicBeatSubstate.hx", "NightmareVisionScriptedSubstate.hx",
                "NightmareVisionStateScriptLoadResult.hx",
                "NightmareVisionScriptBroadcast.hx", "NightmareVisionScriptGroup.hx",
            ):
                shutil.copyfile(ROOT / "source" / source_name, work / source_name)
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work),
                 "--main", "ScriptedSubstateFixtureMain", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
