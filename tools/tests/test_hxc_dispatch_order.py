"""V-Slice scopes hear events in V-Slice's order, and stopPropagation() ends the broadcast."""

import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND


ROOT = Path(__file__).resolve().parents[2]

LOW_MODULE = '''
class EarlyModule extends Module {
    function new() { super("early-module", 5, {state: PlayState}); }
    override function onUpdate(event) {}
}
'''

PLAIN_MODULE = '''
class PlainModule extends Module {
    function new() { super("plain-module"); }
    override function onUpdate(event) {}
}
'''

STOPPING_SONG = '''
class StoppingSong extends Song {
    var quiet:Bool = true;
    function new() { super("stopping-song"); }
    override function onNoteGhostMiss(event) {
        super.onNoteGhostMiss(event);
        if (quiet) {
            event.cancel();
            event.stopPropagation();
        }
    }
    override function onNoteMiss(event) {
        super.onNoteMiss(event);
        event.shouldPropagate = false;
    }
}
'''


def run_fixture(body):
    fixture = f'''import hscript.Interp;
import hscript.Parser;
class DispatchOrderFixture {{
    static function fail(message:String):Void throw message;
    static function main() {{
{body}
        Sys.println("ok");
    }}
}}
'''
    with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
        (Path(directory) / "DispatchOrderFixture.hx").write_text(fixture, newline="\n")
        return subprocess.run(
            [*HAXE_COMMAND, "-cp", directory, "-cp", str(ROOT / "source"),
             "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
             "-main", "DispatchOrderFixture", "--interp"],
            cwd=ROOT, capture_output=True, text=True, timeout=300,
        )


class HxcDispatchOrderTest(unittest.TestCase):
    def check(self, body):
        result = run_fixture(body)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok", result.stdout)

    def test_scopes_are_ordered_like_vslice_and_other_scopes_keep_their_slots(self):
        self.check('''
        var order = new ScriptDispatchOrder();
        order.register("char", "character");
        order.register("modB", "module", 1000, "b-module");
        order.register("stage", "stage");
        order.register("song", "song-script");
        order.register("modZ", "module", 1, "z-module");
        order.register("modA", "module", 1000, "a-module");
        order.register("kind", "note-kind");
        order.register("event", "song-event");
        var live:Map<String, Int> = [for (key in ["psych", "char", "modB", "lua", "stage", "song",
            "modZ", "modA", "kind", "event", "plain"]) key => 1];
        var keys = ["psych", "char", "modB", "lua", "stage", "song", "modZ", "modA", "kind", "event", "plain"];
        order.arrange(keys, live);
        var expected = "psych,modZ,modA,lua,modB,song,event,kind,stage,char,plain";
        if (keys.join(",") != expected) fail("order " + keys.join(","));
        // A removed scope gives its slot to the next one in order.
        order.remove("modA");
        var fewer = ["char", "psych", "song", "modB", "modZ"];
        live = [for (key in fewer) key => 1];
        order.arrange(fewer, live);
        if (fewer.join(",") != "modZ,psych,modB,song,char") fail("after remove " + fewer.join(","));
        // A registered key the table no longer holds never takes a live slot.
        var stale = ["char", "modB"];
        live = [for (key in stale) key => 1];
        order.arrange(stale, live);
        if (stale.join(",") != "modB,char") fail("stale " + stale.join(","));
        // The sorted list is shared until a scope is added or removed.
        var first = order.orderedKeys();
        if (order.orderedKeys() != first) fail("order rebuilt without a change");
        order.register("late", "module", 0, "late");
        if (order.orderedKeys()[0] != "late") fail("re-sort after add");
        order.clear();
        var untouched = ["b", "a"];
        order.arrange(untouched, live);
        if (untouched.join(",") != "b,a") fail("empty order moved keys");
        if (ScriptDispatchOrder.familyRank("module") >= ScriptDispatchOrder.familyRank("song")) fail("module rank");
        if (ScriptDispatchOrder.familyRank("cutscene") <= ScriptDispatchOrder.familyRank("character")) fail("unknown rank");
        ''')

    def test_module_priority_is_read_from_the_constructor(self):
        self.check(f'''
        var early = HxcCompat.analyze({json.dumps(LOW_MODULE)}, "scripts/modules/early.hxc");
        if (early.kind != "module" || early.modulePriority != 5) fail("early priority " + early.modulePriority);
        var plain = HxcCompat.analyze({json.dumps(PLAIN_MODULE)}, "scripts/modules/plain.hxc");
        if (plain.modulePriority != ScriptDispatchOrder.DEFAULT_MODULE_PRIORITY) fail("default priority " + plain.modulePriority);
        var song = HxcCompat.analyze({json.dumps(STOPPING_SONG)}, "scripts/songs/stopping.hxc");
        if (song.modulePriority != null) fail("song has a module priority");
        ''')

    def test_stop_propagation_is_routed_and_marks_the_event(self):
        self.check(f'''
        var payload = EngineCompat.hxcLifecyclePayload("update", {{}});
        if (Reflect.field(payload, "shouldPropagate") != true) fail("new event does not propagate");
        if (EngineCompat.hxcPayloadStopped(payload)) fail("new event stopped");
        Reflect.callMethod(payload, Reflect.field(payload, "stopEventPropagation"), []);
        if (!EngineCompat.hxcPayloadStopped(payload)) fail("stopEventPropagation ignored");
        var noteArgs:Array<Dynamic> = [null, true, 2, EngineCompat.hxcLifecyclePayload("noteMiss", {{}})];
        if (EngineCompat.hxcPayloadIn(noteArgs) != noteArgs[3]) fail("event object not found in arguments");
        if (EngineCompat.hxcPayloadIn([1.5]) != null) fail("number taken for an event");

        var result = HxcCompat.translate({json.dumps(STOPPING_SONG)}, "scripts/songs/stopping.hxc");
        for (name in ["noteGhostMiss", "noteMiss"])
            if (result.canonicalCallbacks.indexOf(name) < 0) fail("not routed: " + name);
        for (finding in (cast result.diagnostics:Array<Dynamic>))
            if (finding.code == "unsupported-hxc-payload-field" || finding.code == "unsupported-hxc-callback-body")
                fail("diagnosed: " + finding.message);
        var interp = new Interp();
        interp.variables.set("trace", function(value:Dynamic) {{}});
        interp.execute(new Parser().parseString(result.generatedHscript));
        var ghost = EngineCompat.hxcLifecyclePayload("noteGhostMiss", {{}});
        Reflect.callMethod(null, interp.variables.get("noteGhostMiss"), [ghost]);
        if (!EngineCompat.hxcPayloadCanceled(ghost) || !EngineCompat.hxcPayloadStopped(ghost)) fail("ghost miss not stopped");
        var miss = EngineCompat.hxcLifecyclePayload("noteMiss", {{}});
        Reflect.callMethod(null, interp.variables.get("noteMiss"), [miss]);
        if (!EngineCompat.hxcPayloadStopped(miss) || EngineCompat.hxcPayloadCanceled(miss)) fail("field write not read as a stop");
        ''')

    def test_broadcast_runs_hxc_scopes_in_order_and_stops_where_asked(self):
        # Runs PlayState's own broadcast code against stand-in scopes.
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8", errors="ignore")
        start = source.index("\tfunction callAllHScript(")
        dispatch = source[start:source.index("\n\t/** Psych spawn broadcasts", start)]
        notes_start = source.index("\tfunction callHxcNoteHScript(")
        notes = source[notes_start:source.index("\n\t/** A NoteKind interpreter", notes_start)]
        fixture = """class FakeInterp {
  public var variables:Map<String,Dynamic> = []; public function new() {}
}
class LuaCompatInterp extends FakeInterp {}
typedef Interp = FakeInterp;
class ScriptCallbackResult {
  public static var STOP_LUA = 'a'; public static var STOP_HSCRIPT = 'b'; public static var STOP_ALL = 'c';
}
class EngineCompat {
  public static function callbackNames(name:String):Array<String> return [name];
  public static function canonicalCallback(name:String):String return name;
  public static function hxcPayloadIn(args:Array<Dynamic>):Dynamic {
    var last:Dynamic = args == null || args.length == 0 ? null : args[args.length - 1];
    return last != null && Reflect.hasField(last, 'shouldPropagate') ? last : null;
  }
  public static function hxcPayloadStopped(payload:Dynamic):Bool
    return payload != null && Reflect.field(payload, 'shouldPropagate') == false;
}
class State {
  public var hscriptStates:Map<String,FakeInterp> = [];
  public var hxcPayloadStates:Map<String,Bool> = [];
  public var hxcDispatchOrder = new ScriptDispatchOrder();
  public var hxcScriptEventScopes:Map<String,Bool> = [];
  public var lastHxcCallPayload:Dynamic = null;
  public var defaultPsychGlobalScopes:Array<String> = [];
  public var hxcCharacterScopeNames:Map<String,String> = [];
  public var hxcNoteKindScopes:Map<String,String> = [];
  public var received:Array<String> = [];
  public function new() {}
  function hxcCharacterScopeOwnsNote(scope:String, args:Array<Dynamic>):Bool return true;
  function hxcNoteKindScopeOwnsNote(scope:String, args:Array<Dynamic>):Bool return true;
  function callHscript(name:String, args:Array<Dynamic>, usehaxe:String, optional:Bool, ?returnValues:Array<Dynamic>):Bool {
    var hook:Dynamic = hscriptStates.get(usehaxe).variables.get(name);
    if (hook == null) return false;
    received.push(usehaxe + ':' + name);
    var payload:Dynamic = args[args.length - 1];
    hook(payload);
    lastHxcCallPayload = hxcPayloadStates.get(usehaxe) == true ? payload : null;
    return true;
  }
""" + dispatch.replace("function callAllHScript(", "public function callAllHScript(", 1) + notes.replace("function callHxcNoteHScript(", "public function callHxcNoteHScript(", 1) + """
}
class Main {
  static function scope(state:State, key:String, family:String, ?priority:Int):FakeInterp {
    var interp = new FakeInterp();
    interp.variables.set('noteGhostMiss', function(event:Dynamic) {});
    state.hscriptStates.set(key, interp);
    state.hxcPayloadStates.set(key, family != null);
    if (family != null) state.hxcDispatchOrder.register(key, family, priority, key);
    return interp;
  }
  static function event():Dynamic {
    var payload:Dynamic = {shouldPropagate: true};
    payload.stopPropagation = function() payload.shouldPropagate = false;
    return payload;
  }
  static function main() {
    var state = new State();
    scope(state, 'character', 'character');
    scope(state, 'song', 'song-script');
    scope(state, 'late-module', 'module', 1000);
    scope(state, 'psych', null);
    scope(state, 'early-module', 'module', 1);
    state.callAllHScript('noteGhostMiss', [event()]);
    var hxc = [for (entry in state.received) if (entry.indexOf('psych') < 0) entry];
    if (hxc.join(',') != 'early-module:noteGhostMiss,late-module:noteGhostMiss,song:noteGhostMiss,character:noteGhostMiss')
      throw 'order ' + state.received.join(',');
    // The song stops the event: the character never hears it, Psych still does.
    state.hscriptStates.get('song').variables.set('noteGhostMiss', function(e:Dynamic) e.stopPropagation());
    state.received = [];
    state.callAllHScript('noteGhostMiss', [event()]);
    if (state.received.indexOf('character:noteGhostMiss') >= 0) throw 'stop ignored ' + state.received.join(',');
    if (state.received.indexOf('psych:noteGhostMiss') < 0) throw 'non-HXC scope lost the event';
    if (state.received.indexOf('late-module:noteGhostMiss') < 0) throw 'scope before the stop skipped';
    // The note path stops the same way.
    state.received = [];
    state.callHxcNoteHScript('noteGhostMiss', [null, event()]);
    if (state.received.join(',') != 'early-module:noteGhostMiss,late-module:noteGhostMiss,song:noteGhostMiss')
      throw 'note path ' + state.received.join(',');
    // onScriptEvent hears it first; a stop there skips the scope's own hook.
    // Later scopes still hear onScriptEvent (V-Slice calls it on every target)
    // but never the hook itself.
    state.hscriptStates.get('early-module').variables.set('scriptEvent', function(e:Dynamic) e.stopPropagation());
    state.hxcScriptEventScopes.set('early-module', true);
    state.hscriptStates.get('character').variables.set('scriptEvent', function(e:Dynamic) {});
    state.hxcScriptEventScopes.set('character', true);
    state.received = [];
    state.callAllHScript('noteGhostMiss', [event()]);
    var heard = [for (entry in state.received) if (entry.indexOf('psych') < 0) entry];
    if (heard.join(',') != 'early-module:scriptEvent,character:scriptEvent') throw 'catch-all ' + state.received.join(',');
    state.received = [];
    state.callHxcNoteHScript('noteGhostMiss', [null, event()]);
    if (state.received.join(',') != 'early-module:scriptEvent,character:scriptEvent')
      throw 'note catch-all ' + state.received.join(',');
    // A stop made by an earlier dispatch of the same note event does not cut
    // this one short.
    state.hxcScriptEventScopes.remove('early-module');
    state.hxcScriptEventScopes.remove('character');
    state.hscriptStates.get('song').variables.set('noteGhostMiss', function(e:Dynamic) {});
    var stale = event();
    stale.stopPropagation();
    state.received = [];
    state.callHxcNoteHScript('noteGhostMiss', [null, stale]);
    if (state.received.join(',') != 'early-module:noteGhostMiss,late-module:noteGhostMiss,song:noteGhostMiss,character:noteGhostMiss')
      throw 'earlier stop ' + state.received.join(',');
    Sys.println('ok');
  }
}"""
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            (Path(directory) / "Main.hx").write_text(fixture, newline="\n")
            (Path(directory) / "ScriptDispatchOrder.hx").write_text(
                (ROOT / "source/ScriptDispatchOrder.hx").read_text(encoding="utf-8"), newline="\n")
            result = subprocess.run([*HAXE_COMMAND, "-cp", directory, "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok", result.stdout)

    def test_playstate_broadcasts_in_order_and_honours_a_stop(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8", errors="ignore")
        borrow = source[source.index("function borrowHscriptKeys("):source.index("function releaseHscriptKeys(")]
        self.assertIn("hxcDispatchOrder.arrange(keys, hscriptStates);", borrow)
        broadcast = source[source.index("function callAllHScript("):source.index("var hscriptKeyPool")]
        self.assertIn("if (hxc && stopHxc)", broadcast)
        self.assertIn("EngineCompat.hxcPayloadStopped(lastHxcCallPayload)", broadcast)
        # onScriptEvent hears the event before its own hook.
        self.assertLess(broadcast.index("callHscript('scriptEvent'"), broadcast.index("callHscript(func_name"))
        notes = source[source.index("function callHxcNoteHScript("):source.index("function hxcNoteKindScopeOwnsNote(")]
        self.assertIn("EngineCompat.hxcPayloadStopped(payload)", notes)
        self.assertRegex(notes, r"if \(!stoppedBefore && EngineCompat\.hxcPayloadStopped\(payload\)\)\s+stopped = true;")
        self.assertRegex(notes, r"if \(stopped\)\s+continue;\s+if \(hscriptDefinesCallback")
        # Every HXC scope is placed when it is loaded and forgotten when it goes.
        made = source[source.index("function makeHaxeState("):]
        self.assertIn("registerHxcDispatchScope(usehaxe, path + filename", made)
        self.assertIn("forgetHxcDispatchScope(usehaxe);", made)
        stages = source[source.index("function clearHxcStageScopes("):]
        self.assertIn("forgetHxcDispatchScope(scope);", stages[:stages.index("hxcStageScopes.resize(0);")])
        # The payload of the last call is recorded after the call returns, so a
        # broadcast started inside the callback cannot replace it.
        call = source[source.index("function callHscript("):source.index("function callAllHScript(")]
        self.assertLess(call.index("returned = method("), call.index("lastHxcCallPayload = hxcCallPayload;"))


if __name__ == "__main__":
    unittest.main()
