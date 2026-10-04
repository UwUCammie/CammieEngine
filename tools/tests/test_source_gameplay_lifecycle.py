"""Executable probes and source-order checks for imported gameplay hooks.

These tests extract the small dispatch helpers from PlayState so the callback
sentinel matrix runs without starting the engine.  The larger call sites are
checked for the point where those helpers enter native gameplay.
"""

from haxe_test_support import HAXE_COMMAND

from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    """Extract a Haxe method while ignoring braces in strings and comments."""
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    quote = None
    line_comment = False
    block_comment = False
    escaped = False
    index = brace
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and following == "/":
                block_comment = False
                index += 1
        elif quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char == "/" and following == "/":
            line_comment = True
            index += 1
        elif char == "/" and following == "*":
            block_comment = True
            index += 1
        elif char in ("'", '"'):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
        index += 1
    raise AssertionError(f"unterminated Haxe method: {marker}")


def extract_braced_block(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    # Reuse the method scanner for the block's balanced brace semantics.
    synthetic = "function extracted() " + source[brace:]
    return extract_method(synthetic, "function extracted()")


class SourceGameplayLifecycleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.play = (ROOT / "source/PlayState.hx").read_text()
        cls.engine_compat = (ROOT / "source/EngineCompat.hx").read_text()
        cls.spawn_helper = extract_method(cls.play, "function dispatchPsychNoteSpawn(")
        cls.hit_helper = extract_method(cls.play, "function dispatchPsychNoteHitPre(")
        cls.countdown_helper = extract_method(cls.play, "function notifySourceCountdownStarted(")

    def compile_helper_fixture(self):
        fixture = r'''
class ScriptCallbackResult {
 public static inline var STOP:String = 'STOP';
 public static inline var STOP_LUA:String = 'STOP_LUA';
 public static inline var STOP_HSCRIPT:String = 'STOP_HSCRIPT';
 public static inline var STOP_ALL:String = 'STOP_ALL';
 public static inline var CONTINUE:String = 'CONTINUE';
}
class Note {
 public var noteData:Int = -2;
 public var coolId:String = 'Glow';
 public var noteType:String = 'Fallback';
 public var psychHitCallbackArgs:Array<Dynamic>;
 public var isSustainNote:Bool = true;
 public var strumTime:Float = 432.5;
 public function new() {}
}
class NoteGroup { public var members:Array<Note> = []; public function new() {} }
class RuntimeCall {
 public var name:String;
 public var family:String;
 public var args:Array<Dynamic>;
 public function new(name:String, family:String, args:Array<Dynamic>) {
  this.name = name; this.family = family; this.args = args;
 }
}
class EngineCompat {
 public static function psychNoteCallbackArguments(args:Array<Dynamic>,
   livePsychNotes:Array<Dynamic>):Array<Dynamic> {
  var note:Note = cast args[0];
  return [livePsychNotes.indexOf(note), Math.abs(note.noteData),
   note.coolId == null ? note.noteType : note.coolId, note.isSustainNote];
 }
}
class PsychRuntimeBindings {
 public static function hasScripts(host:PlayState):Bool return host.psychEnabled;
 public static function dispatch(host:PlayState, name:String, args:Array<Dynamic>,
   family:String = 'Scripts', ignoreStops:Bool = false,
   ?hscriptArgs:Array<Dynamic>):Dynamic {
  if (name == 'onCountdownStarted' && (!host.startedCountdown || !host.nvStarted))
   throw 'countdown globals must be published before callbacks';
  host.calls.push(new RuntimeCall(name, family, args));
  if (name == 'onCountdownStarted') host.order.push('psych:' + name);
  return family == 'Luas' ? host.luaResult : family == 'HScript'
   ? host.hscriptResult : null;
 }
}
class NVGroup {
 var host:PlayState;
 public function new(host:PlayState) this.host = host;
 public function set(name:String, value:Dynamic):Void {
  if (name == 'startedCountdown' && value == true) host.nvStarted = true;
  host.order.push('nvvar:' + name);
 }
}
class NVScripts { public var group:NVGroup; public function new(host:PlayState) group = new NVGroup(host); }
class PlayState {
 public var notes:NoteGroup = new NoteGroup();
 public var calls:Array<RuntimeCall> = [];
 public var order:Array<String> = [];
 public var psychEnabled:Bool = true;
 public var sourceScoreNightmare:Bool = false;
 function sourceScoreLedgerActive():Bool return false;
 public var startedCountdown:Bool = false;
 public var nvStarted:Bool = false;
 public var luaResult:Dynamic = ScriptCallbackResult.CONTINUE;
 public var hscriptResult:Dynamic = ScriptCallbackResult.CONTINUE;
 public var nightmareVisionScripts:NVScripts;
 public function new() nightmareVisionScripts = new NVScripts(this);
 function setAllHaxeVar(name:String, value:Dynamic):Void {
  if (name == 'startedCountdown' && value == true) startedCountdown = true;
  order.push('haxevar:' + name);
 }
 function callNightmareVision(name:String, args:Array<Dynamic>):Dynamic {
  if (name == 'onCountdownStarted' && (!startedCountdown || !nvStarted))
   throw 'countdown globals must be published before Nightmare Vision callback';
  order.push('nightmare:' + name);
  return null;
 }
''' + self.spawn_helper + '\n' + self.hit_helper + '\n' + self.countdown_helper + r'''
 public function exerciseSpawn(note:Note):Void dispatchPsychNoteSpawn(note);
 public function exerciseHit(note:Note, playerOne:Bool):Bool
  return dispatchPsychNoteHitPre(note, playerOne);
 public function exerciseCountdown():Void notifySourceCountdownStarted();
}
class Main {
 static function check(condition:Bool, message:String):Void if (!condition) throw message;
 static function expectHit(lua:Dynamic, hscript:Dynamic, expected:Bool,
   expectedFamilies:Array<String>):Void {
  var state = new PlayState();
  state.luaResult = lua;
  state.hscriptResult = hscript;
  var note = new Note();
  state.notes.members = [new Note(), note, new Note()];
  var result = state.exerciseHit(note, true);
  check(result == expected, 'unexpected pre-hit cancellation result');
  check(state.calls.length == expectedFamilies.length, 'unexpected pre-hit family count');
  for (index in 0...expectedFamilies.length)
   check(state.calls[index].family == expectedFamilies[index], 'unexpected family order');
  check(state.calls[0].name == 'goodNoteHitPre', 'player hook alias missing');
  check(state.calls[0].args.length == 4 && state.calls[0].args[0] == 1
   && state.calls[0].args[1] == 2 && state.calls[0].args[2] == 'Glow'
   && state.calls[0].args[3] == true, 'Lua scalar/live-group ABI changed');
  if (expectedFamilies.length == 2)
   check(state.calls[1].args.length == 1 && state.calls[1].args[0] == note,
    'HScript must receive the live Note');
 }
 static function main():Void {
  expectHit(ScriptCallbackResult.STOP, ScriptCallbackResult.CONTINUE, false, ['Luas']);
  expectHit(ScriptCallbackResult.STOP_HSCRIPT, ScriptCallbackResult.CONTINUE, true, ['Luas']);
  expectHit(ScriptCallbackResult.STOP_ALL, ScriptCallbackResult.CONTINUE, true, ['Luas']);
  expectHit(ScriptCallbackResult.STOP_LUA, ScriptCallbackResult.CONTINUE, true, ['Luas', 'HScript']);
  expectHit('ordinary-value', ScriptCallbackResult.CONTINUE, true, ['Luas', 'HScript']);
  expectHit('ordinary-value', ScriptCallbackResult.STOP_HSCRIPT, true, ['Luas', 'HScript']);
  expectHit('ordinary-value', ScriptCallbackResult.STOP, false, ['Luas', 'HScript']);
  var opponentState = new PlayState();
  opponentState.exerciseHit(new Note(), false);
  check(opponentState.calls[0].name == 'opponentNoteHitPre', 'opponent hook alias missing');

  var spawnState = new PlayState();
  var spawned = new Note();
  spawnState.notes.members = [new Note(), spawned];
  spawnState.luaResult = ScriptCallbackResult.STOP;
  spawnState.exerciseSpawn(spawned);
  check(spawnState.calls.length == 2, 'spawn return must not suppress either family');
  check(spawnState.calls[0].family == 'Luas' && spawnState.calls[1].family == 'HScript',
   'spawn family order changed');
  var luaArgs = spawnState.calls[0].args;
  check(luaArgs.length == 5 && luaArgs[0] == 1 && luaArgs[1] == -2
   && luaArgs[2] == 'Glow' && luaArgs[3] == true && luaArgs[4] == 432.5,
   'Psych onSpawnNote scalar ABI changed');
  check(spawnState.calls[1].args.length == 1 && spawnState.calls[1].args[0] == spawned,
   'Psych HScript onSpawnNote must receive the live Note');

  var countdownState = new PlayState();
  countdownState.exerciseCountdown();
  check(countdownState.order.join('|') ==
   'haxevar:startedCountdown|nvvar:startedCountdown|psych:onCountdownStarted|nightmare:onCountdownStarted',
   'countdown notification order changed');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_extracted_dispatch_helpers_execute_sentinel_matrix_and_payloads(self):
        self.assertIn("PsychRuntimeBindings.dispatch(this, 'onSpawnNote', args, 'Luas')",
                      self.spawn_helper)
        self.assertIn("PsychRuntimeBindings.dispatch(this, 'onSpawnNote', [note], 'HScript')",
                      self.spawn_helper)
        self.assertIn("result != ScriptCallbackResult.STOP_HSCRIPT", self.hit_helper)
        self.assertIn("result != ScriptCallbackResult.STOP_ALL", self.hit_helper)
        self.assertIn("return result != ScriptCallbackResult.STOP", self.hit_helper)
        self.compile_helper_fixture()

    def test_note_adapter_supplies_live_group_slot_and_scalar_fields(self):
        adapter = extract_method(self.engine_compat,
                                 "public static function psychNoteCallbackArguments(")
        self.assertIn("id = livePsychNotes.indexOf(note)", adapter)
        self.assertIn("Math.abs(Std.int(Std.parseFloat(Std.string(rawDirection))))", adapter)
        self.assertIn("rawType = Reflect.getProperty(note, 'coolId')", adapter)
        self.assertIn("Reflect.getProperty(note, 'isSustainNote')", adapter)
        self.assertIn("return [id, direction, noteType, sustain]", adapter)

    def test_spawn_queue_insertion_callback_and_removal_order(self):
        start = self.play.index("var dunceNote:Note = unspawnNotes[0];")
        end = self.play.index("if (smokeProfileAt > 0)", start)
        spawn_route = self.play[start:end]
        insert = spawn_route.index("notes.insert(0, dunceNote)")
        mark_spawned = spawn_route.index("dunceNote.spawned = true")
        callback = spawn_route.index("dispatchPsychNoteSpawn(dunceNote)")
        removal = spawn_route.rindex("unspawnNotes.remove(dunceNote)")
        self.assertLess(insert, mark_spawned)
        self.assertLess(mark_spawned, callback)
        self.assertLess(callback, removal)

    def test_pre_hit_is_before_native_judgement_for_manual_and_automatic_routes(self):
        hit = extract_method(self.play, "function goodNoteHit(note:Note, playerOne:Bool")
        auto = extract_method(self.play, "function dispatchHxcAutoNoteHit(")
        manual_input = extract_method(self.play, "private function keyShit(")
        update = extract_method(self.play, "override public function update(elapsed:Float)")
        self.assertIn("goodNoteHit(coolNote, playerOne)", manual_input)
        self.assertLess(hit.index("dispatchPsychNoteHitPre(note, playerOne)"),
                        hit.index("dispatchNightmareVisionNoteHitPre(note)"))
        self.assertLess(hit.index("dispatchPsychNoteHitPre(note, playerOne)"),
                        hit.index("note.rating = noteRatingAtHit(note)"))
        self.assertLess(auto.index("dispatchPsychNoteHitPre(note, playerOne)"),
                        auto.index("note.wasGoodHit = true"))
        self.assertLess(auto.index("dispatchPsychNoteHitPre(note, playerOne)"),
                        auto.index("dispatchNightmareVisionNoteHitPre(note)"))
        self.assertIn("dispatchHxcAutoNoteHit(daNote, false)", update)
        self.assertIn("dispatchHxcAutoNoteHit(daNote, true)", update)

    def test_countdown_notification_occurs_after_gate_before_skip_and_timer(self):
        countdown = extract_method(self.play, "public function startCountdown():Void")
        repeated = extract_braced_block(countdown, "if (startedCountdown)")
        self.assertIn("onStartCountdown", repeated)
        self.assertNotIn("notifySourceCountdownStarted", repeated)
        self.assertNotIn("new FlxTimer()", repeated)
        started = countdown.rindex("startedCountdown = true;")
        clock = countdown.rindex("Conductor.songPosition = -Conductor.crochet * 5;")
        notify = countdown.rindex("notifySourceCountdownStarted();")
        skipped_clock = countdown.index("if (skipCountdown) Conductor.songPosition = 0;", notify)
        timer_setup = countdown.index("RuntimeSmokeHarness.markStep('countdown:timer-setup-begin')", notify)
        self.assertLess(started, clock)
        self.assertLess(clock, notify)
        self.assertLess(notify, skipped_clock)
        self.assertLess(skipped_clock, timer_setup)

    def test_nightmare_vision_substate_hooks_are_zero_arg_notifications(self):
        opening = extract_method(self.play, "override function openSubState(")
        closing = extract_method(self.play, "override function closeSubState()")
        open_hook = "callNightmareVision('onSubstateOpen', [])"
        close_hook = "callNightmareVision('onSubstateClose', [])"
        self.assertIn(open_hook, opening)
        self.assertIn(close_hook, closing)
        self.assertLess(opening.index(open_hook), opening.index("super.openSubState(SubState)"))
        self.assertLess(closing.index(close_hook), closing.index("super.closeSubState()"))
        self.assertNotIn("return " + open_hook, opening)
        self.assertNotIn("return " + close_hook, closing)


if __name__ == "__main__":
    unittest.main()
