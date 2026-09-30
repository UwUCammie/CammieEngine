"""Source-contract tests for the Nightmare Vision callback timeline adapter."""

from pathlib import Path
import subprocess
import tempfile
import unittest
import re


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
IRIS = ROOT / ".haxelib/hscript-iris/1,1,3"


class NightmareVisionModManagerTest(unittest.TestCase):
    def test_callback_timing_order_arguments_seek_errors_and_lifecycle(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        fixture = r'''
import crowplexus.hscript.Interp;
import crowplexus.hscript.Parser;

class Main {
 static function fail(message:String):Void throw message;
 static function check(value:Bool, message:String):Void if (!value) fail(message);
 static function eq<T>(actual:T, expected:T, message:String):Void
  if (actual != expected) fail(message + ': expected ' + expected + ', got ' + actual);

 static function main() {
  var calls:Array<String> = [];
  var errors:Array<String> = [];
  var manager = new NightmareVisionModManager(function(event, error):Void {
   errors.push(Std.string(event.executionStep) + ':' + Std.string(error));
  });
  var interp = new Interp();
  var parser = new Parser();
  parser.allowTypes = true;
  parser.allowMetadata = true;
  interp.variables.set('modManager', manager);
  interp.variables.set('record', function(value:String):Void calls.push(value));

  interp.execute(parser.parseString('
   modManager.queueFuncOnce(5, () -> record("zero"));
   modManager.queueFuncOnce(5, (event, step) -> {
    record("args:" + step + ":" + event.executionStep + ":" + (event.manager == modManager)
     + ":finished=" + event.finished);
   });
   modManager.queueFunc(8, 10, (event, step) ->
    record("repeat:" + step + ":end=" + event.endStep));
  '));

  manager.updateTimeline(4.99);
  eq(calls.length, 0, 'future callbacks ran early');
  manager.updateTimeline(5);
  eq(calls.join(','), 'zero,args:5:5:true:finished=false', 'equal-step order or callback arguments changed');
  manager.updateTimeline(2);
  manager.updateTimeline(5);
  eq(calls.length, 2, 'backward seek replayed a finished one-shot callback');

  manager.updateTimeline(8);
  manager.updateTimeline(9.25);
  manager.updateTimeline(10);
  eq(calls.slice(2).join(','), 'repeat:8:end=10,repeat:9.25:end=10,repeat:10:end=10',
   'queueFunc did not repeat through its inclusive end step');
  manager.updateTimeline(10.001);
  manager.updateTimeline(9);
  eq(calls.length, 5, 'finished repeat callback ran after a backward seek');

  // Forward seek fires an overdue one-shot once, passing the live current step.
  interp.execute(parser.parseString('modManager.queueFuncOnce(20, (event, step) -> record("seek:" + step));'));
  manager.updateTimeline(25);
  manager.updateTimeline(20);
  eq(calls[calls.length - 1], 'seek:25', 'forward seek did not pass current step or callback repeated');

  // Events added by a callback are visible to the same source timeline pass.
  interp.execute(parser.parseString('modManager.queueFuncOnce(30, () -> {
   record("outer");
   modManager.queueFuncOnce(1, () -> record("nested"));
  });'));
  manager.updateTimeline(30);
  eq(calls.slice(calls.length - 2).join(','), 'outer,nested', 'nested due callback was deferred');

  // External ignoreExecution pauses an event without consuming its one-shot.
  interp.execute(parser.parseString('modManager.queueFuncOnce(40, () -> record("unpaused"));'));
  var paused = manager.timeline.events[0];
  paused.ignoreExecution = true;
  manager.updateTimeline(40);
  eq(calls[calls.length - 1], 'nested', 'ignored callback executed');
  paused.ignoreExecution = false;
  manager.updateTimeline(40);
  eq(calls[calls.length - 1], 'unpaused', 'unignored callback did not execute');
  check(paused.finished, 'one-shot event was not marked finished after callback');

  // Skipping beyond a repeating event's end retires it without a late call.
  interp.execute(parser.parseString('modManager.queueFunc(45, 48, (event, step) -> record("late-repeat"));'));
  manager.updateTimeline(49);
  manager.updateTimeline(46);
  check(calls.indexOf('late-repeat') < 0, 'repeat callback ran when first observed after endStep');

  // A failed script callback is reported once and cannot block later events.
  interp.execute(parser.parseString('
   modManager.queueFuncOnce(50, (event, step) -> { throw "callback boom"; });
   modManager.queueFuncOnce(50, () -> record("after-error"));
  '));
  manager.updateTimeline(50);
  eq(errors.length, 1, 'callback error was not reported exactly once');
  eq(calls[calls.length - 1], 'after-error', 'failed callback blocked later due events');
  manager.updateTimeline(51);
  eq(errors.length, 1, 'failed callback retried on a later update');

  // Incomplete modifier APIs fail loudly instead of looking successfully queued.
  var unsupported = false;
  try manager.queueSet(0, 'reverse', 1) catch (error:Dynamic) {
   unsupported = Std.string(error).indexOf('ModManager.queueSet is not implemented') >= 0;
  }
  check(unsupported, 'unimplemented queueSet did not produce an explicit diagnostic');
  check(NightmareVisionModManager.callbackEventClass() == NightmareVisionCallbackEvent,
   'CallbackEvent binding did not expose the source-compatible runtime event class');
  var unsupportedApis = NightmareVisionModManager.unimplementedModifierApis();
  check(unsupportedApis.indexOf('queueSet') >= 0 && unsupportedApis.indexOf('getPos') >= 0,
   'unimplemented source modifier APIs were not inventoried');
  var invalidCallback = false;
  try manager.queueFuncOnce(0, null) catch (_:Dynamic) invalidCallback = true;
  check(invalidCallback, 'invalid callback was silently accepted');

  interp.execute(parser.parseString('modManager.queueFuncOnce(99, () -> record("after-destroy"));'));
  manager.destroy();
  eq(manager.timeline.events.length, 0, 'destroy retained callbacks/interpreters');
  manager.updateTimeline(100);
  check(calls.indexOf('after-destroy') < 0, 'destroyed timeline executed a callback');
  var rejected = false;
  try manager.queueFuncOnce(100, function():Void {}) catch (_:Dynamic) rejected = true;
  check(rejected && manager.destroyed, 'destroyed manager accepted more work');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(IRIS), "-cp", str(work),
                 "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=40,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_scheduler_contract_matches_supplied_event_source(self):
        donor = ROOT.parent / "FNF-Example-Mods/misc/nightmare_vision_source_code/source/funkin/game/modchart"
        if not donor.is_dir():
            self.skipTest("supplied Nightmare Vision modchart source unavailable")
        manager = (donor / "ModManager.hx").read_text()
        callback = (donor / "events/CallbackEvent.hx").read_text()
        repeated = (donor / "events/StepCallbackEvent.hx").read_text()
        timeline = (donor / "EventTimeline.hx").read_text()
        self.assertIn("timeline.addEvent(new CallbackEvent(step, callback, this))", manager)
        self.assertIn("timeline.addEvent(new StepCallbackEvent(step, endStep, callback, this))", manager)
        self.assertIn("callback(this, curStep);", callback)
        self.assertIn("finished = true;", callback)
        self.assertIn("if (curStep <= endStep)", repeated)
        self.assertIn("if (step >= event.executionStep)", timeline)
        self.assertIn("updateSchedule(events, step);", timeline)

    def test_retained_new_dsides_manager_calls_are_supported_or_explicitly_unimplemented(self):
        donor = ROOT.parent / "FNF-Example-Mods/nightmare-vision/dsides_r_11_final/content/new-dsides"
        if not donor.is_dir():
            self.skipTest("selected Nightmare Vision owner source unavailable")
        calls = set()
        for path in donor.rglob("*.hx"):
            calls.update(re.findall(r"\bmodManager\.([A-Za-z_][A-Za-z0-9_]*)", path.read_text(errors="replace")))

        source = (ROOT / "source/NightmareVisionModManager.hx").read_text()
        match = re.search(r"unimplementedModifierApis\(\).*?return \[(.*?)\];", source, re.S)
        self.assertIsNotNone(match, "manager must keep an explicit unsupported-API inventory")
        unsupported = set(re.findall(r"'([A-Za-z_][A-Za-z0-9_]*)'", match.group(1)))
        supported = {"queueFuncOnce", "queueFunc", "receptors"}
        self.assertEqual(calls - supported - unsupported, set(),
            "retained NMV ModManager call has no real implementation or explicit unsupported diagnostic")
        self.assertTrue({"queueFuncOnce", "queueFunc"}.issubset(calls))


if __name__ == "__main__":
    unittest.main()
