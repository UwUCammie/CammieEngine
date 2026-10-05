"""Executable probes for the Psych and Nightmare Vision source input adapters."""

from haxe_test_support import HAXE_COMMAND

from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    """Extract one Haxe method, ignoring braces inside comments and strings."""
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


class SourceInputLifecycleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        play = (ROOT / "source/PlayState.hx").read_text()
        cls.receptor_helper = extract_method(play, "function setSourceInputReceptor(")
        cls.invalidate_helper = extract_method(play, "function invalidateSourceInputNote(")
        cls.psych_press = extract_method(play, "function psychSourceKeyPressed(")
        cls.psych_release = extract_method(play, "function psychSourceKeyReleased(")
        cls.nv_press = extract_method(play, "function nightmareVisionSourceKeyPressed(")
        cls.nv_release = extract_method(play, "function nightmareVisionSourceKeyReleased(")
        cls.update = extract_method(play, "override public function update(elapsed:Float)")
        cls.key_shit = extract_method(play, "private function keyShit(")
        cls.dispatch_psych_edges = extract_method(play, "function dispatchPsychInputEdges(")

    def test_extracted_handlers_preserve_input_contracts(self):
        fixture = r'''
class Note {
 public static inline var NOTE_AMOUNT:Int = 4;
 public var noteData:Int = 0;
 public var mustPress:Bool = true;
 public var alive:Bool = true;
 public var canBeHit:Bool = true;
 public var tooLate:Bool = false;
 public var wasGoodHit:Bool = false;
 public var blockHit:Bool = false;
 public var isSustainNote:Bool = false;
 public var isLiftNote:Bool = false;
 public var lowPriority:Bool = false;
 public var strumTime:Float = 100;
 public var codenameInputLine:Dynamic = null;
 public var sourcePlayfieldIndex:Int = 0;
 public var hitPriority:Int = 1;
 public var destroyed:Bool = false;
 public function new(key:Int = 0, side:Bool = true) {
  noteData = key; mustPress = side;
 }
 public function kill():Void alive = false;
 public function destroy():Void destroyed = true;
}
class NoteGroup {
 public var members:Array<Note> = [];
 public function new() {}
 public function remove(note:Note, splice:Bool = false):Note {
  members.remove(note);
  return note;
 }
}
class InputActor {
 public var stunned:Bool = false;
 public var holdTimer:Float = 7;
 public function new() {}
}
class InputField {
 public var ID:Int=0;
 public var strumline:InputFixtureStrumline;
 public var input:Bool = true;
 public var playAnims:Bool = true;
 public function new() {}
 public function canInput():Bool return input;
}
class InputPrefsView { public var ghostTapping:Bool = false; public function new() {} }
class InputPrefs { public var view:InputPrefsView = new InputPrefsView(); public function new() {} }
class InputFixtureReceptor {
 public var ID:Int;
 public var animation:Dynamic = {curAnim:{name:'static'}};
 public var resetAnim:Float = 4;
 public var holding:Bool = false;
 var lineName:String;
 var events:Array<String>;
 public function new(ID:Int, lineName:String, events:Array<String>) {
  this.ID = ID; this.lineName = lineName; this.events = events;
 }
 public function playAnim(name:String, ?force:Bool):Void {
  animation.curAnim.name = name;
  events.push('receptor:' + lineName + ':' + ID + ':' + name);
 }
}
class InputFixtureStrumline {
 public var members:Array<InputFixtureReceptor> = [];
 var lineName:String;
 var events:Array<String>;
 public function new(lineName:String, events:Array<String>) {
  this.lineName = lineName; this.events = events;
  for (lane in 0...4) members.push(new InputFixtureReceptor(lane, lineName, events));
 }
 public function forEachReceptor(callback:InputFixtureReceptor->Void):Void
  for (receptor in members) callback(receptor);
 public function endNoteHoldCoverAtLane(key:Int):Void
  events.push('holdcover:' + lineName + ':' + key);
}
class PsychRuntimeBindings {
 public static function dispatch(host:InputFixture, name:String, args:Array<Dynamic>,
   family:String = 'Scripts', ignoreStops:Bool = false,
   ?hscriptArgs:Array<Dynamic>):Dynamic {
  host.events.push('psych:' + name);
  host.psychArgs.set(name, args.copy());
  if (name == 'onKeyPressPre')
   host.pressPreSawNoJudgement = host.hits.length == 0;
  if (name == 'onKeyPress' && args.length > 0) {
   var key:Int = cast args[0];
   host.pressPostSawState = host.hits.length > 0
    && host.playerStrums.members[key].animation.curAnim.name == 'pressed';
  }
  if (name == 'onKeyRelease' && args.length > 0) {
   var key:Int = cast args[0];
   host.releasePostSawState = host.playerStrums.members[key].animation.curAnim.name == 'static';
  }
  return host.psychReturns.get(name);
 }
}
class InputFixture {
 public var events:Array<String> = [];
 public var notes:NoteGroup = new NoteGroup();
 public var strumsBlocked:Array<Bool> = [false, false, false, false];
 public var playerStrums:InputFixtureStrumline;
 public var enemyStrums:InputFixtureStrumline;
 public var boyfriend:InputActor = new InputActor();
 public var opponentActor:InputActor = new InputActor();
 public var fields:Array<InputField> = [new InputField(), new InputField()];
 public var nightmareVisionFields:Array<InputField>;
 public var nightmareVisionPrefs:InputPrefs = new InputPrefs();
 public var ghostTapping:Bool = false;
 public function sourceLivePreference(name:String, fallback:Bool):Bool return fallback;
 public var keysPressed:Array<Int> = [];
 public var demoMode:Bool = false;
 public var paused:Bool = false;
 public var inCutscene:Bool = false;
 public var generatedMusic:Bool = true;
 public var endingSong:Bool = false;
 public var startedCountdown:Bool = true;
 public var disableKeys:Bool = false;
 public var compatEventVideoControlsDisabled:Bool = false;
 public var hxcVideoControlsDisabled:Bool = false;
 public var hits:Array<Note> = [];
 public var misses:Array<String> = [];
 public var psychReturns:Map<String, Dynamic> = [];
 public var psychArgs:Map<String, Array<Dynamic>> = [];
 public var nightmareReturns:Map<String, Dynamic> = [];
 public var nightmareArgs:Map<String, Array<Dynamic>> = [];
 public var pressPreSawNoJudgement:Bool = false;
 public var pressPostSawState:Bool = false;
 public var releasePostSawState:Bool = false;
 public var nvPressPostSawState:Bool = false;
 public var nvReleasePostSawState:Bool = false;
 public function new() {
  playerStrums = new InputFixtureStrumline('player', events);
  enemyStrums = new InputFixtureStrumline('enemy', events);
  nightmareVisionFields=fields;
  fields[0].ID=0;fields[0].strumline=playerStrums;
  fields[1].ID=1;fields[1].strumline=enemyStrums;
 }
 function getOpponentSinger():InputActor return opponentActor;
 function getInputStrumline(line:Dynamic, playerOne:Bool):InputFixtureStrumline
  return playerOne ? playerStrums : enemyStrums;
 function getNightmareVisionField(id:Int):InputField return fields[id];
 function goodNoteHit(note:Note, playerOne:Bool):Void {
  hits.push(note); note.wasGoodHit = true;
  events.push('hit:' + note.noteData + ':' + playerOne);
 }
 function noteMiss(direction:Int, playerOne:Bool, note:Null<Note>, playMissSound:Bool):Void {
  misses.push(direction + ':' + playerOne);
  events.push('miss:' + direction + ':' + playerOne);
 }
 function callNightmareVision(name:String, args:Array<Dynamic>):Dynamic {
  events.push('nv:' + name);
  nightmareArgs.set(name, args.copy());
  if (name == 'onKeyPress' && args.length > 0) {
   var key:Int = cast args[0];
   nvPressPostSawState = playerStrums.members[key].animation.curAnim.name == 'pressed'
    && playerStrums.members[key].holding && enemyStrums.members[key].holding;
  }
  if (name == 'onKeyRelease' && args.length > 0) {
   var key:Int = cast args[0];
   nvReleasePostSawState = playerStrums.members[key].animation.curAnim.name == 'static'
    && !playerStrums.members[key].holding && !enemyStrums.members[key].holding;
  }
  return nightmareReturns.get(name);
 }
 public function exercisePsychPress(key:Int, playerOne:Bool):Void psychSourceKeyPressed(key, playerOne);
 public function exercisePsychRelease(key:Int, playerOne:Bool):Void psychSourceKeyReleased(key, playerOne);
 public function exerciseNvPress(key:Int):Void nightmareVisionSourceKeyPressed(key);
 public function exerciseNvRelease(key:Int):Void nightmareVisionSourceKeyReleased(key);
''' + self.receptor_helper.replace("Strumline.StrumNote", "InputFixtureReceptor") + '\n' \
    + self.psych_press + '\n' + self.psych_release + '\n' + self.nv_press + '\n' \
    + self.nv_release + '\n' + self.invalidate_helper + r'''
}
class Main {
 static function check(condition:Bool, message:String):Void if (!condition) throw message;
 static function at(events:Array<String>, value:String):Int return events.indexOf(value);
 static function has(events:Array<String>, value:String):Bool return events.indexOf(value) >= 0;
 static function pressState(result:Dynamic):InputFixture {
  var state = new InputFixture();
  state.ghostTapping = true;
  state.psychReturns.set('onKeyPressPre', result);
  state.notes.members.push(new Note(2, true));
  return state;
 }
 static function main():Void {
  // Only Psych Function_Stop cancels the press. Other stop families and ordinary
  // return values still reach judgement, receptor feedback, and the post hook.
  var cancelled = pressState(ScriptCallbackResult.STOP);
  cancelled.exercisePsychPress(2, true);
  check(cancelled.hits.length == 0 && cancelled.events.length == 1
   && cancelled.events[0] == 'psych:onKeyPressPre', 'exact Psych STOP must cancel the press');
  check(cancelled.playerStrums.members[2].animation.curAnim.name == 'static',
   'cancelled press must leave receptor feedback untouched');
  check(cancelled.pressPreSawNoJudgement, 'press Pre must run before judgement');
  check(cancelled.keysPressed.length == 0, 'pre-cancelled key must not enter keysPressed');

  for (result in [ScriptCallbackResult.STOP_LUA, ScriptCallbackResult.STOP_HSCRIPT,
      ScriptCallbackResult.STOP_ALL, 'ordinary-value']) {
   var state = pressState(result);
   state.exercisePsychPress(2, true);
   check(state.hits.length == 1 && state.hits[0].wasGoodHit,
    'non-STOP return incorrectly cancelled note judgement');
   check(at(state.events, 'psych:onKeyPressPre') < at(state.events, 'hit:2:true')
    && at(state.events, 'hit:2:true') < at(state.events, 'receptor:player:2:pressed')
    && at(state.events, 'receptor:player:2:pressed') < at(state.events, 'psych:onKeyPress'),
    'Psych press callbacks/judgement/receptor order changed');
   check(state.pressPostSawState, 'onKeyPress must observe judged note and pressed receptor');
   check(state.psychArgs.get('onKeyPress').length == 1
    && state.psychArgs.get('onKeyPress')[0] == 2, 'Psych key callback payload changed');
   check(state.keysPressed.length == 1 && state.keysPressed[0] == 2,
    'accepted source input must record its lane before returning');
   state.exercisePsychPress(2, true);
   check(state.keysPressed.length == 1, 'keysPressed must retain unique lane history');
  }

  // Each key is judged independently: a note on another lane cannot suppress
  // an empty-lane ghost callback, and Psych excludes sustain-only lanes as taps.
  var chord = new InputFixture();
  chord.ghostTapping = true;
  chord.notes.members.push(new Note(0, true));
  chord.exercisePsychPress(1, true);
  check(chord.hits.length == 0 && has(chord.events, 'psych:onGhostTap')
   && chord.psychArgs.get('onGhostTap')[0] == 1,
   'an unrelated chord lane suppressed its own ghost callback');
  var sustainOnly = new InputFixture();
  sustainOnly.ghostTapping = true;
  var tail = new Note(1, true); tail.isSustainNote = true;
  sustainOnly.notes.members.push(tail);
  sustainOnly.exercisePsychPress(1, true);
  check(sustainOnly.hits.length == 0 && has(sustainOnly.events, 'psych:onGhostTap'),
   'Psych sustain-only lane must remain a ghost tap');
  var noGhost = new InputFixture();
  noGhost.ghostTapping = false;
  noGhost.exercisePsychPress(3, true);
  check(!has(noGhost.events, 'psych:onGhostTap') && noGhost.misses.length == 1
   && noGhost.misses[0] == '3:true', 'disabled Psych ghost tapping must route to noteMissPress');

  // Rejected Psych press guards run before script callbacks and side effects.
  var rejected:Array<InputFixture> = [];
  var guarded = new InputFixture(); guarded.demoMode = true; rejected.push(guarded);
  guarded = new InputFixture(); guarded.paused = true; rejected.push(guarded);
  guarded = new InputFixture(); guarded.inCutscene = true; rejected.push(guarded);
  guarded = new InputFixture(); guarded.generatedMusic = false; rejected.push(guarded);
  guarded = new InputFixture(); guarded.endingSong = true; rejected.push(guarded);
  guarded = new InputFixture(); guarded.boyfriend.stunned = true; rejected.push(guarded);
  for (state in rejected) {
   state.exercisePsychPress(0, true);
   check(state.events.length == 0 && state.hits.length == 0 && state.misses.length == 0,
    'rejected Psych press guard leaked callbacks or gameplay effects');
  }
  var invalidPress = new InputFixture();
  invalidPress.exercisePsychPress(-1, true);
  invalidPress.exercisePsychPress(Note.NOTE_AMOUNT, true);
  check(invalidPress.events.length == 0, 'out-of-range Psych press must be rejected');

  // Release always ends the physical hold cover before the gate. Exact STOP
  // suppresses only static receptor reset and onKeyRelease.
  var releaseStop = new InputFixture();
  releaseStop.psychReturns.set('onKeyReleasePre', ScriptCallbackResult.STOP);
  releaseStop.playerStrums.members[1].animation.curAnim.name = 'confirm';
  releaseStop.exercisePsychRelease(1, true);
  check(releaseStop.events[0] == 'holdcover:player:1'
   && releaseStop.events[1] == 'psych:onKeyReleasePre'
   && releaseStop.playerStrums.members[1].animation.curAnim.name == 'confirm'
   && !has(releaseStop.events, 'psych:onKeyRelease'),
   'pre-cancelled release must still end hold cover without receptor reset');
  var releasePass = new InputFixture();
  releasePass.psychReturns.set('onKeyReleasePre', ScriptCallbackResult.STOP_HSCRIPT);
  releasePass.playerStrums.members[1].animation.curAnim.name = 'confirm';
  releasePass.exercisePsychRelease(1, true);
  check(at(releasePass.events, 'holdcover:player:1') < at(releasePass.events, 'psych:onKeyReleasePre')
   && at(releasePass.events, 'psych:onKeyReleasePre') < at(releasePass.events, 'receptor:player:1:static')
   && at(releasePass.events, 'receptor:player:1:static') < at(releasePass.events, 'psych:onKeyRelease')
   && releasePass.releasePostSawState,
   'non-STOP release must reset receptor before the post callback');
  var notStarted = new InputFixture(); notStarted.startedCountdown = false;
  notStarted.exercisePsychRelease(1, true);
  check(notStarted.events.length == 1 && notStarted.events[0] == 'holdcover:player:1',
   'pre-countdown physical release must clear hold cover without script callbacks');
  var invalidRelease = new InputFixture();
  invalidRelease.exercisePsychRelease(4, true);
  check(invalidRelease.events.length == 0, 'out-of-range release must not touch a hold cover');
  var cutsceneRelease = new InputFixture(); cutsceneRelease.inCutscene = true;
  cutsceneRelease.exercisePsychRelease(1, true);
  check(has(cutsceneRelease.events, 'psych:onKeyReleasePre')
   && has(cutsceneRelease.events, 'psych:onKeyRelease')
   && cutsceneRelease.playerStrums.members[1].animation.curAnim.name == 'static',
   'physical key release must still dispatch during cutscene handoff');

  // Nightmare Vision broadcasts ghost taps even when its preference is on;
  // the preference changes only miss fanout. Return values do not cancel input.
  for (enabled in [true, false]) {
   var nv = new InputFixture();
   nv.nightmareVisionPrefs.view.ghostTapping = enabled;
   nv.nightmareReturns.set('onGhostTap', ScriptCallbackResult.STOP);
   nv.exerciseNvPress(0);
   check(has(nv.events, 'nv:onGhostTap'), 'NV ghost hook must ignore ghost preference');
   check(at(nv.events, 'nv:onGhostTap') < at(nv.events, 'nv:onKeyPress')
    && at(nv.events, 'nv:onKeyPress') < at(nv.events, 'nv:onInputPress')
    && nv.nvPressPostSawState,
    'NV press callbacks must follow lane receptor state');
   check(nv.misses.length == (enabled ? 0 : 2)
    && has(nv.events, 'nv:noteMissPress') == !enabled,
    'NV ghost preference must gate only miss callbacks');
   if (!enabled)
    check(at(nv.events, 'nv:onGhostTap') < at(nv.events, 'miss:0:true')
     && at(nv.events, 'miss:1:false') < at(nv.events, 'nv:noteMissPress'),
     'NV ghost/miss direction fanout order changed');
  }

  var nvSustain = new InputFixture();
  nvSustain.nightmareVisionPrefs.view.ghostTapping = false;
  var nvTail = new Note(0, true); nvTail.isSustainNote = true;
  nvTail.sourcePlayfieldIndex = 0;
  nvSustain.notes.members.push(nvTail);
  nvSustain.exerciseNvPress(0);
  check(!has(nvSustain.events, 'nv:onGhostTap') && !has(nvSustain.events, 'nv:noteMissPress')
   && nvSustain.misses.length == 0,
   'eligible NV sustain occupancy must suppress ghost and miss callbacks');

  // A key with no enabled field has no ghost event, while the source key-up
  // notification remains available. An active key-up resets state first.
  var noField = new InputFixture();
  noField.fields[0].input = false; noField.fields[1].input = false;
  noField.exerciseNvPress(0);
  check(!has(noField.events, 'nv:onGhostTap') && has(noField.events, 'nv:onKeyPress'),
   'NV requires an eligible input field for ghost taps but still notifies the key edge');
  var invalidNv = new InputFixture();
  invalidNv.exerciseNvPress(4); invalidNv.exerciseNvRelease(4);
  check(invalidNv.events.length == 0, 'out-of-range NV keys must be rejected');
  var nvRelease = new InputFixture();
  nvRelease.nightmareReturns.set('onKeyRelease', ScriptCallbackResult.STOP);
  nvRelease.playerStrums.members[2].holding = true;
  nvRelease.enemyStrums.members[2].holding = true;
  nvRelease.exerciseNvRelease(2);
  check(at(nvRelease.events, 'holdcover:player:2') < at(nvRelease.events, 'receptor:player:2:static')
   && at(nvRelease.events, 'receptor:enemy:2:static') < at(nvRelease.events, 'nv:onKeyRelease')
   && at(nvRelease.events, 'nv:onKeyRelease') < at(nvRelease.events, 'nv:onInputRelease')
   && nvRelease.nvReleasePostSawState,
   'NV key-up must clear hold/receptor state before ignored-return callbacks');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            fixture = fixture.replace("Strumline.StrumNote", "InputFixtureReceptor")
            (temp / "Main.hx").write_text(fixture, newline="\n")
            for name in ("SourceInputNotes.hx", "ScriptCallbackResult.hx"):
                (temp / name).write_text((ROOT / "source" / name).read_text(), newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_input_loop_routes_each_pressed_lane_to_source_handlers(self):
        route = self.update.index("if (usesPsychSourceInput()) dispatchPsychInputEdges();")
        self.assertLess(route, self.update.index("if (!inCutscene && !demoMode && !disableKeys", route))
        self.assertIn("if (pressed[key]) psychSourceKeyPressed(key, playerOne);",
                      self.dispatch_psych_edges)
        self.assertIn("if (released[key]) psychSourceKeyReleased(key, playerOne);",
                      self.dispatch_psych_edges)
        route = self.key_shit.index("if (sourceLine == null && usesPsychSourceInput())")
        self.assertLess(route, self.key_shit.index("controlArray = [for (_ in controlArray) false];"))
        self.assertLess(route, self.key_shit.index("releaseArray = [for (_ in releaseArray) false];"))
        self.assertIn("for (key in 0...holdArray.length) if (strumsBlocked[key] == true) holdArray[key] = false;",
                      self.key_shit)
        self.assertIn("nightmareVisionSourceKeyPressed(key)", self.update)
        self.assertIn("nightmareVisionSourceKeyReleased(key)", self.update)


if __name__ == "__main__":
    unittest.main()
