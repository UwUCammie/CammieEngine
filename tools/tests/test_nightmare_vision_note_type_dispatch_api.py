"""Exercise NMV's stage/event callNoteTypeScript selection contract."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

from tools.haxe_flixel_math_stubs import write_flixel_point_stub


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"
IRIS = ROOT / ".haxelib" / "hscript-iris" / "1,1,3"


class NightmareVisionNoteTypeDispatchApiTest(unittest.TestCase):
    def test_stage_and_event_target_one_note_type_and_keep_return_semantics(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            write_flixel_point_stub(work)
            (work / "Main.hx").write_text(r'''
import NightmareVisionScriptDiscovery.NightmareVisionScriptEntry;
import NightmareVisionScriptDiscovery.NightmareVisionScriptPlan;

class Main {
 static var log:Array<String> = [];
 static var reports:Array<String> = [];
 static var sources:Map<String, String> = new Map();
 static var host:NightmareVisionGameplayScripts;
 static var eventBeforeLoadUsedMainFields:Bool = false;

 static function fail(message:String):Void throw message;
 static function eq(actual:Dynamic, expected:Dynamic, label:String):Void {
  if (actual != expected) fail(label + ': expected ' + expected + ', got ' + actual);
 }
 static function entry(scope:String, name:String, relative:String):NightmareVisionScriptEntry {
  return {scope:scope, name:name, relative:relative, path:'owner/' + relative};
 }
 static function main():Void {
  var plan:NightmareVisionScriptPlan = {
   root:'owner', baseAssetsRoot:'', song:'song', stage:'stage', coverageNotes:[],
   scripts:[
    entry('stage', 'stage', 'data/stages/stage.hx'),
    entry('event', 'Fade', 'data/events/Fade.hx'),
    entry('notetype', 'Ice Note', 'data/notetypes/Ice Note.hx'),
    entry('notetype', 'Other Note', 'data/notetypes/Other Note.hx')
   ]
  };
  sources.set('owner/data/stages/stage.hx', '
   function onLoad() {
    record("stage:onLoad");
    var missingType = callNoteTypeScript("Absent Note", "forcebreak", []);
    var missingCallback = callNoteTypeScript("Ice Note", "absentCallback", []);
    var callbackError = callNoteTypeScript("Ice Note", "fail", ["stage"]);
    var stopped = callNoteTypeScript("Ice Note", "forcebreak", ["stage"]);
    var missingEvent = callEventScript("Absent Event", "onTrigger", []);
    var missingEventCallback = callEventScript("Fade", "absentCallback", []);
    var eventStopped = callEventScript("Fade", "onTrigger", ["stage-event"]);
    record("stage:results:" + missingType + "," + missingCallback + "," + callbackError + ","
     + stopped + "," + missingEvent + "," + missingEventCallback + "," + eventStopped);
   }
   function onUpdate() { record("stage:update"); }
   function onDestroy() { record("stage:destroy"); }
  ');
  sources.set('owner/data/events/Fade.hx', '
   function onLoad() {
    if (!isMainGroupShared()) throw "event onLoad was rebound before completion";
    record("event:onLoad");
   }
   function onUpdate() { record("event:update"); }
   function onTrigger(origin) {
    var stopped = callNoteTypeScript("Ice Note", "forcebreak", [origin]);
    record("event:result:" + stopped);
    return stopped;
   }
   function onDestroy() { record("event:destroy"); }
  ');
  sources.set('owner/data/notetypes/Ice Note.hx', '
   function onLoad() {
    if (!isMainGroupShared()) throw "note-type onLoad was rebound before completion";
    record("ice:onLoad");
   }
   function onUpdate() { record("ice:update"); }
   function fail(origin) { record("ice:fail:" + origin); throw "fixture failure"; }
   function forcebreak(origin) { record("ice:" + origin); return Function_Stop; }
   function onDestroy() { record("ice:destroy"); }
  ');
  sources.set('owner/data/notetypes/Other Note.hx', '
   function onLoad() {
    if (!isMainGroupShared()) throw "note-type onLoad was rebound before completion";
    record("other:onLoad");
   }
   function onUpdate() { record("other:update"); }
   function forcebreak(origin) { record("other:" + origin); return Function_Continue; }
   function onDestroy() { record("other:destroy"); }
  ');

  host = new NightmareVisionGameplayScripts({}, plan,
   function(path:String):String {
    if (!sources.exists(path)) throw 'unexpected source read: ' + path;
    return sources.get(path);
   },
   function(interp:NightmareVisionScriptInterp, entry:NightmareVisionScriptEntry,
    actor:Dynamic):Void {
    interp.variables.set('record', function(value:String):Dynamic { log.push(value); return null; });
    interp.variables.set('Function_Continue', NightmareVisionScriptGroup.CONTINUE_FUNC);
    interp.variables.set('Function_Stop', NightmareVisionScriptGroup.STOP_FUNC);
    interp.variables.set('Function_Halt', NightmareVisionScriptGroup.HALT_FUNC);
   },
   function(name:String, phase:String, error:Dynamic):Void
    reports.push(name + '#' + phase + ':' + Std.string(error)),
   function(interp:NightmareVisionScriptInterp, entry:NightmareVisionScriptEntry):Void {
    if (entry.scope == 'event')
     eventBeforeLoadUsedMainFields = interp.sharedFields == host.group.sharedFields;
    interp.variables.set('isMainGroupShared', function():Bool
     return interp.sharedFields == host.group.sharedFields);
   });

  // Stage module dispatch is available during onLoad and only registers the
  // requested note type. Missing targets/callbacks and callback exceptions
  // match the source CONTINUE behavior; a STOP result survives the wrapper.
  host.loadScope('stage');
  eq(log.join('|'), 'stage:onLoad|ice:onLoad|ice:fail:stage|ice:stage|event:onLoad|ice:stage-event|'
   + 'event:result:1|stage:results:0,0,0,1,0,0,1',
   'stage callback ordering/selection');
  eq(reports.length, 1, 'callback error report count');
  if (reports[0].indexOf('Ice Note#fail:') != 0) fail('callback error attribution: ' + reports[0]);

  // Source inserts the event into the main group and then its specialized
  // registry. Both references must identify one script; the second add changes
  // its sharedFields only after execute/onLoad has completed.
  var eventModule = host.eventGroup.getScript('Fade');
  eq(eventBeforeLoadUsedMainFields, true, 'event beforeLoad did not use main shared fields');
  eq(eventModule, host.group.getScript('Fade'), 'event registry copied instead of sharing its module');
  eq(eventModule.interp.sharedFields == host.eventGroup.sharedFields, true,
   'event registry did not apply its own shared fields');
  eq(eventModule.interp.sharedFields == host.group.sharedFields, false,
   'event registry kept main shared fields after registration');

  // Load a second type before an event's targeted call. It must not receive
  // the selected type callback just because both modules share the main group.
  host.loadNoteTypes('Other Note');
  var iceModule = host.noteTypeGroup.getScript('Ice Note');
  var otherModule = host.noteTypeGroup.getScript('Other Note');
  eq(iceModule, host.group.getScript('Ice Note'), 'note-type registry copied its module');
  eq(otherModule, host.group.getScript('Other Note'), 'note-type registry copied its module');
  eq(iceModule.interp.sharedFields == host.noteTypeGroup.sharedFields, true,
   'note-type registry did not apply its own shared fields');
  eq(otherModule.interp.sharedFields == host.noteTypeGroup.sharedFields, true,
   'other note-type registry did not apply its own shared fields');
  eq(host.noteTypeExclusions().join(','), 'Ice Note,Other Note', 'loaded type exclusion names');

  eq(host.call('onUpdate'), NightmareVisionScriptGroup.CONTINUE_FUNC,
   'main lifecycle call return');
  eq(log.slice(-4).join('|'), 'stage:update|ice:update|event:update|other:update',
   'main group did not broadcast once in source registration order');
  eq(host.callEvent('Fade', 'onTrigger', ['event']), NightmareVisionScriptGroup.STOP_FUNC,
   'event did not preserve selected callback STOP');
  eq(log.slice(-2).join('|'), 'ice:event|event:result:1',
   'event callback broadcast to a different note type');
  if (log.indexOf('other:stage') >= 0 || log.indexOf('other:event') >= 0)
   fail('targeted callback reached Other Note: ' + log.join('|'));

  var stageModule = host.group.getScript('data/stages/stage.hx');
  var stageDispatcher:Dynamic = stageModule.interp.variables.get('callNoteTypeScript');
  var eventNoteTypeDispatcher:Dynamic = eventModule.interp.variables.get('callNoteTypeScript');
  var eventScriptDispatcher:Dynamic = eventModule.interp.variables.get('callEventScript');
  var stageEventDispatcher:Dynamic = stageModule.interp.variables.get('callEventScript');
  var previousLog = log.join('|');
  host.destroy();
  eq(log.slice(-4).join('|'), 'stage:destroy|ice:destroy|event:destroy|other:destroy',
   'main-group teardown order omitted or duplicated a registered script');
  eq(host.group.released && host.eventGroup.released && host.noteTypeGroup.released, true,
   'teardown did not release every registry');
  eq(eventModule.released && eventModule.interp == null, true,
   'same event module was not safely destroyed through both registries');
  eq(Reflect.callMethod(null, stageDispatcher, ['Ice Note', 'forcebreak', ['after-destroy']]),
   NightmareVisionScriptGroup.CONTINUE_FUNC, 'stage dispatcher survived teardown');
  eq(Reflect.callMethod(null, eventNoteTypeDispatcher, ['Ice Note', 'forcebreak', ['after-destroy']]),
   NightmareVisionScriptGroup.CONTINUE_FUNC, 'event note-type dispatcher survived teardown');
  eq(Reflect.callMethod(null, eventScriptDispatcher, ['Fade', 'onTrigger', ['after-destroy']]),
   NightmareVisionScriptGroup.CONTINUE_FUNC, 'event event-script dispatcher survived teardown');
  eq(Reflect.callMethod(null, stageEventDispatcher, ['Fade', 'onTrigger', ['after-destroy']]),
   NightmareVisionScriptGroup.CONTINUE_FUNC, 'stage event-script dispatcher survived teardown');
  eq(log.length, previousLog.split('|').length + 4, 'teardown dispatch invoked a callback');
 }
}
''', encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(IRIS), "-cp", str(work),
                 "--main", "Main", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_playstate_seeds_the_nmvs_public_dispatch_method(self):
        source = (ROOT / "source" / "PlayState.hx").read_text()
        self.assertIn(
            "@:keep public function callNoteTypeScript(noteType:String, callback:String, args:Array<Dynamic>):Dynamic",
            source,
        )
        self.assertIn("nightmareVisionScripts.callNoteType(noteType, callback, args)", source)
        self.assertIn("interp.variables.set('callNoteTypeScript', callNoteTypeScript);", source)
        self.assertIn(
            "@:keep public function callEventScript(name:String, callback:String, args:Array<Dynamic>):Dynamic",
            source,
        )
        self.assertIn("nightmareVisionScripts.callEvent(name, callback, args)", source)
        self.assertIn("interp.variables.set('callEventScript', callEventScript);", source)


if __name__ == "__main__":
    unittest.main()
