"""Run current PlayState Psych hit routing and finish methods in a small host."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    """Extract one Haxe method while ignoring braces inside comments and strings."""
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    quote = None
    line_comment = block_comment = escaped = False
    index = brace
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char in "\r\n":
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


NOTE = r'''package;
class FixtureNote {
 public var noteData:Float=0;
 public var noteType:String='';
 public var isSustainNote:Bool=false;
 public var psychHitDispatched:Bool=false;
 public var psychHitCallbackArgs:Array<Dynamic>=null;
 public var hitByOpponent:Bool=false;
 public var wasGoodHit:Bool=false;
 public var noteHit:String=null;
 public var noteStrum:String=null;
 public var y:Float=0;
 public var killed:Bool=false;
 public var destroyed:Bool=false;
 public var alive:Bool=true;
 public var ignoreNote:Bool=false;
 public var autoHitSuppressed:Bool=false;
 public var hitCausesMiss:Bool=false;
 public var canMiss:Bool=false;
 public var sourcePlayfieldIndex:Int=0;
 public var codenameInputLine:Dynamic=null;
 public var rating:Dynamic=null;
 public var events:Array<String>;
 public function new(events:Array<String>) this.events=events;
 public function kill():Void {killed=true;alive=false;events.push('kill');}
 public function destroy():Void {destroyed=true;events.push('destroy');}
}
'''

HOST = r'''package;
class NoteGroup {
 public var members:Array<FixtureNote>=[];
 public function new() {}
 public function remove(note:FixtureNote,_splice:Bool):Void {members.remove(note);}
}
class Signal {
 final events:Array<String>; final name:String;
 public function new(events:Array<String>,name:String){this.events=events;this.name=name;}
 public function trigger(_note:FixtureNote):Void events.push('signal:'+name);
}
class PlayState {
 public var sourceOwner:Bool=true;
 public var sourceScoreNightmare:Bool=false;
 public var hasPsychScripts:Bool=true;
 public var demoMode:Bool=false;
 public var currentAutoNote:FixtureNote=null;
 public var autoHxcCancel:Bool=false;
 public var preWasGoodHit:Array<Bool>=[];
 public var hxcNoteCallbacks:Array<String>=[];
 public var missCalls:Int=0;
 public var hazardSplashCalls:Int=0;
 public var hitHealthCalls:Int=0;
 public var popupCalls:Int=0;
 public var notes:NoteGroup=new NoteGroup();
 public var events:Array<String>=[];
 public var broadcasts:Array<Dynamic>=[];
 public var stages:Array<Array<Dynamic>>=[];
 public var ownerCalls:Array<Array<Dynamic>>=[];
 public var dispatchResults:Map<String,Dynamic>=[];
 public var hxcStrumlineNoteSurface:Dynamic=null;
 public var nightmareVisionScripts:Dynamic=null;
 public var downscroll:Bool=false;
 public var player1GoodHitSignal:Signal;
 public var player2GoodHitSignal:Signal;
 public function new() {
  player1GoodHitSignal=new Signal(events,'player1');
  player2GoodHitSignal=new Signal(events,'player2');
 }
 public function sourceScoreLedgerActive():Bool return sourceOwner;
 public function getNightmareVisionField(_index:Int):Dynamic return {playerControls:false,autoPlayed:false};
 public function nightmareVisionFieldForNote(note:FixtureNote):Dynamic
  return note == null ? null : getNightmareVisionField(note.sourcePlayfieldIndex);
 public function nightmareVisionRemoveFieldNoteMembership(_note:FixtureNote):Void {}
 public function dispatchPsychCompiledStage(name:String,args:Array<Dynamic>):Void {
  stages.push([name,args]);events.push('stage:'+name);
 }
 public function restoreSourceHitVocals(_note:FixtureNote,playerOne:Bool):Void
  events.push('restore:'+(playerOne?'player':'opponent'));
 public function dispatchNightmareVisionNoteHit(_note:FixtureNote):Void events.push('nightmare-hit');
 public function callAllHScript(name:String,args:Array<Dynamic>,_skipHxc:Bool,
  ?returnValues:Array<Dynamic>,?hxcArgs:Array<Dynamic>,?skipPsych:Bool=false):Void {
  ownerCalls.push([name,args,skipPsych]);events.push('all:'+name);
 }
 public function callHscript(name:String,_args:Array<Dynamic>,_scope:String):Bool {
  events.push('modchart:'+name);return true;
 }
 public function getHaxeActor(_id:String):Dynamic return null;
 public function dispatchNightmareVisionNoteHitPre(_note:FixtureNote):Void events.push('nightmare-pre-hit');
 public function judgeSourceNote(_note:FixtureNote):Dynamic {events.push('judge-source');return null;}
 public function callHxcNoteHScript(name:String,args:Array<Dynamic>):Void {
  hxcNoteCallbacks.push(name);events.push('hxc:'+name);
  if (autoHxcCancel && args != null && args.length > 3 && args[3] != null)
   Reflect.setProperty(args[3],'eventCanceled',true);
 }
 public function noteMiss(direction:Float,playerOne:Bool,note:FixtureNote):Void {
  missCalls++;events.push('miss:'+Std.string(direction)+':'+playerOne);
  if (sourceScoreLedgerActive()) PsychMissCallbacks.dispatch(note,Std.int(direction),
   note==null?-1:notes.members.indexOf(note),
   function(name,args,family) return PsychRuntimeBindings.dispatch(this,name,args,family));
 }
 public function setVocalsVolume(_volume:Float):Void events.push('vocal-write');
 public function splashHitCausesMissNote(_note:FixtureNote):Void {hazardSplashCalls++;events.push('hazard-splash');}

 __EXTRACTED_METHODS__
}

class PsychRuntimeBindings {
 public static function hasScripts(host:PlayState):Bool return host.hasPsychScripts;
 public static function dispatch(host:PlayState,name:String,args:Array<Dynamic>,family:String):Dynamic {
  host.broadcasts.push({name:name,args:args,family:family});
  host.events.push(family+':'+name);
  if (name=='goodNoteHitPre' || name=='opponentNoteHitPre')
   host.preWasGoodHit.push(host.currentAutoNote==null?false:host.currentAutoNote.wasGoodHit);
  return host.dispatchResults.exists(family)?host.dispatchResults.get(family):ScriptCallbackResult.CONTINUE;
 }
}
class EngineCompat {
 public static function psychNoteCallbackArguments(args:Array<Dynamic>,?livePsychNotes:Array<Dynamic>):Array<Dynamic> {
  var note=args==null||args.length==0?null:args[0];
  var slot=livePsychNotes==null?-1:livePsychNotes.indexOf(note);
  return [slot,Reflect.getProperty(note,'noteData'),Reflect.getProperty(note,'noteType'),
   Reflect.getProperty(note,'isSustainNote')];
 }
 public static function hxcNoteCallbackPayload(_args:Array<Dynamic>,_name:String):Dynamic
  return {eventCanceled:false,canceled:false,cancelled:false,judgement:null};
 public static function hxcApplyNoteCallbackPayload(_event:Dynamic):Void {}
}
'''


MAIN = r'''package;
class SourceHitLifecycleFixture {
 static function check(value:Bool,message:String):Void if(!value)throw message;
 static function eq(actual:Dynamic,expected:Dynamic,message:String):Void
  if(actual!=expected)throw message+': expected '+Std.string(expected)+', got '+Std.string(actual);
 static function call(host:PlayState,family:String):Array<Dynamic> {
  for(row in host.broadcasts) if(row.family==family) return row.args;
  return null;
 }
 static function main():Void {
  var host=new PlayState();
  var note=new FixtureNote(host.events);note.noteData=-2.6;note.noteType='Before pre';note.isSustainNote=true;
  host.notes.members=[note];
  check(host.dispatchPsychNoteHitPre(note,true),'ordinary pre result should permit hit');
  var captured=note.psychHitCallbackArgs;
  check(captured!=null&&captured.length==4,'player pre did not retain Lua ABI snapshot');
  eq(captured[0],0,'pre group slot');eq(captured[1],3,'good-hit lane rounds abs');
  eq(captured[2],'Before pre','pre note type');eq(captured[3],true,'pre sustain');

  // The Note can change between pre and post; Lua uses the original snapshot,
  // with only its group slot refreshed, while HScript keeps the live object.
  note.noteData=-1;note.noteType='After pre';note.isSustainNote=false;
  var other=new FixtureNote(host.events);host.notes.members=[other,note];
  host.broadcasts=[];host.events=[];note.events=host.events;
  host.finishGoodNoteHit(note,true,null);
  var lua=call(host,'Luas');
  eq(lua[0],1,'post Lua slot uses the current Note group index');
  eq(lua[1],3,'post Lua lane preserves pre-captured lane');
  eq(lua[2],'Before pre','post Lua type preserves pre-captured type');
  eq(lua[3],true,'post Lua sustain preserves pre-captured flag');
  var hscript=call(host,'HScript');
  check(hscript!=null&&hscript.length==1&&hscript[0]==note,
   'post HScript receives the live Note identity');
  eq(Reflect.getProperty(hscript[0],'noteData'),-1,'HScript sees current lane');
  eq(Reflect.getProperty(hscript[0],'noteType'),'After pre','HScript sees current note type');
  check(!Reflect.getProperty(hscript[0],'isSustainNote'),'HScript sees current sustain state');
  check(note.psychHitDispatched&&note.wasGoodHit&&!note.hitByOpponent,
   'player source hit was marked once as a successful head');
  check(note.killed&&note.destroyed&&!host.notes.members.contains(note),
   'source head retires after its callbacks');
  check(host.events.indexOf('stage:goodNoteHit')<host.events.indexOf('Luas:goodNoteHit')
   &&host.events.indexOf('Luas:goodNoteHit')<host.events.indexOf('HScript:goodNoteHit')
   &&host.events.indexOf('HScript:goodNoteHit')<host.events.indexOf('kill'),
   'compiled stage, Psych families, and disposal order changed');
  check(host.ownerCalls.length==2&&host.ownerCalls[0][2]==true&&host.ownerCalls[1][2]==true,
   'source-owned callbacks do not rebroadcast Psych hooks through native HScript');
  var count=host.broadcasts.length;host.dispatchPsychNoteHit(note,true);
  eq(host.broadcasts.length,count,'post-hit dedup prevents repeated notifications');

  // Cross-family stop results suppress only the second script family; they do
  // not undo the already-finished judgement or prevent head retirement.
  host=new PlayState();note=new FixtureNote(host.events);note.noteData=2;host.notes.members=[note];
  host.dispatchResults.set('Luas',ScriptCallbackResult.STOP_ALL);
  host.finishGoodNoteHit(note,true,null);
  check(note.wasGoodHit&&note.killed&&note.destroyed,'post STOP_ALL canceled judgement or disposal');
  check(call(host,'HScript')==null,'post STOP_ALL did not suppress HScript');

  // Opponent lane ABI is abs without good-hit rounding, and opponent ownership
  // is published before source script callbacks.
  host=new PlayState();note=new FixtureNote(host.events);note.noteData=-2.6;host.notes.members=[note];
  host.finishGoodNoteHit(note,false,null);
  lua=call(host,'Luas');
  eq(lua[0],0,'opponent Lua group slot');eq(lua[1],2.6,'opponent lane keeps abs value without rounding');
  check(note.hitByOpponent&&note.psychHitDispatched,'opponent hit flag is set before notification');
  eq(host.stages[0][0],'opponentNoteHit','opponent compiled stage callback');

  // Source sustains live for subsequent frames. Native sustain retirement is
  // preserved when no source score owner is active.
  host=new PlayState();note=new FixtureNote(host.events);note.isSustainNote=true;host.notes.members=[note];
  host.finishGoodNoteHit(note,true,null);
  check(note.wasGoodHit&&!note.killed&&!note.destroyed&&host.notes.members.contains(note),
   'source sustain was disposed before its later frames');
  host=new PlayState();note=new FixtureNote(host.events);note.noteData=-1;note.isSustainNote=true;
  host.notes.members=[note];host.finishGoodNoteHit(note,false,null);
  check(note.wasGoodHit&&note.hitByOpponent&&note.psychHitDispatched
   &&!note.killed&&!note.destroyed&&host.notes.members.contains(note),
   'opponent source sustain was disposed or missed its lifecycle flags');
  var opponentSustainCalls=host.broadcasts.length;
  host.dispatchPsychNoteHit(note,false);
  eq(host.broadcasts.length,opponentSustainCalls,
   'opponent sustain did not deduplicate repeated lifecycle notification');
  host=new PlayState();host.sourceOwner=false;note=new FixtureNote(host.events);note.isSustainNote=true;
  host.notes.members=[note];host.finishGoodNoteHit(note,true,null);
  check(note.killed&&note.destroyed&&!host.notes.members.contains(note),
   'native finish no longer retires sustain notes');
  check(host.stages.length==1&&host.broadcasts.length==0,
   'native finish lost compiled-stage callback or gained Psych dispatch');
  check(host.ownerCalls.length==2&&host.ownerCalls[0][2]==false&&host.ownerCalls[1][2]==false,
   'native owner callbacks no longer receive the native Psych family route');

  // Pre gate specifics: family stops, captured player args, and no-script
  // native fallthrough stay separate from post-dispatch stop semantics.
  host=new PlayState();note=new FixtureNote(host.events);note.noteData=-2.6;host.notes.members=[note];
  host.dispatchResults.set('Luas',ScriptCallbackResult.STOP_LUA);
  check(host.dispatchPsychNoteHitPre(note,true),'STOP_LUA incorrectly canceled pre-hit judgement');
  eq(host.broadcasts.length,2,'STOP_LUA pre result permits HScript fallback');
  eq(call(host,'HScript')[0],note,'pre HScript receives live Note');
  eq(note.psychHitCallbackArgs[1],3,'player pre scalar lane rounded');
  host=new PlayState();note=new FixtureNote(host.events);note.noteData=-2.6;host.notes.members=[note];
  host.dispatchResults.set('Luas',ScriptCallbackResult.STOP_HSCRIPT);
  check(host.dispatchPsychNoteHitPre(note,false),'STOP_HSCRIPT incorrectly canceled pre-hit judgement');
  eq(host.broadcasts.length,1,'STOP_HSCRIPT pre result did not stop HScript family');
  eq(call(host,'Luas')[1],2.6,'opponent pre scalar lane is absolute without rounding');
  host=new PlayState();note=new FixtureNote(host.events);host.notes.members=[note];
  host.dispatchResults.set('Luas',ScriptCallbackResult.STOP);
  check(!host.dispatchPsychNoteHitPre(note,true),'Function_Stop did not cancel pre-hit judgement');
  eq(host.broadcasts.length,1,'Function_Stop pre result incorrectly invoked HScript');
  host=new PlayState();host.hasPsychScripts=false;note=new FixtureNote(host.events);host.notes.members=[note];
  check(host.dispatchPsychNoteHitPre(note,true)&&host.broadcasts.length==0,
   'no-source pre path failed to fall through to native judgement');
  Sys.println('OK');
 }
}'''


AUTO_MAIN = r'''package;
class SourceAutoHitLifecycleFixture {
 static function check(value:Bool,message:String):Void if(!value)throw message;
 static function eq(actual:Dynamic,expected:Dynamic,message:String):Void
  if(actual!=expected)throw message+': expected '+Std.string(expected)+', got '+Std.string(actual);
 static function named(host:PlayState,name:String):Int {
  var count=0;for(row in host.broadcasts)if(row.name==name)count++;return count;
 }
 static function main():Void {
  // A source-controlled player auto attempt enters Pre with the pending flag
  // clear, then is accepted. hitCausesMiss itself is not an auto suppressor.
  var host=new PlayState();host.demoMode=true;
  var note=new FixtureNote(host.events);note.wasGoodHit=true;note.hitCausesMiss=true;
  host.currentAutoNote=note;host.notes.members=[note];
  check(host.dispatchHxcAutoNoteHit(note,true),
   'Psych auto hitCausesMiss was suppressed as a generic arbitrary auto miss');
  check(host.preWasGoodHit.length==2&&!host.preWasGoodHit[0]&&!host.preWasGoodHit[1],
   'player Pre did not see wasGoodHit cleared before its Lua/HScript callbacks');
  check(note.wasGoodHit&&!note.autoHitSuppressed,
   'accepted player auto Pre was not marked hit afterward');
  check(host.hitHealthCalls==0&&host.popupCalls==0,
   'auto pre/HXC callback changed hit-health or score-popup counters');

  // Match the real update branch after its HXC preflight, then exercise both
  // extracted note-miss and finish methods. The hazard must miss once and
  // still receive the donor's successful good-hit post callback exactly once.
  check(host.dispatchHitCausesMiss(note,true),
   'accepted already-marked Psych hazard did not enter the miss route');
  host.finishGoodNoteHit(note,true,null,false);
  eq(host.missCalls,1,'Psych auto hazard miss callback count');
  eq(host.hazardSplashCalls,1,'Psych auto hazard splash callback count');
  eq(named(host,'goodNoteHit'),2,'goodNoteHit post family count');
  eq(named(host,'noteMiss'),2,'noteMiss Lua/HScript family count');
  check(note.psychHitDispatched&&note.wasGoodHit&&note.killed&&note.destroyed,
   'hazard did not complete the one-time hit post route and head disposal');
  check(host.hitHealthCalls==0&&host.popupCalls==0,
   'hitCausesMiss auto route granted hit health or displayed a hit popup');

  // HXC cancellation continues to veto its original auto route and prevents
  // both the miss and post-hit sequence from being synthesized afterward.
  host=new PlayState();host.demoMode=true;host.autoHxcCancel=true;
  note=new FixtureNote(host.events);note.wasGoodHit=true;note.hitCausesMiss=true;
  host.currentAutoNote=note;host.notes.members=[note];
  check(!host.dispatchHxcAutoNoteHit(note,true),'HXC cancellation did not veto auto hit');
  check(!note.wasGoodHit&&note.autoHitSuppressed&&!note.psychHitDispatched,
   'HXC cancellation no longer leaves the note pending and suppressed');
  eq(host.missCalls,0,'HXC-canceled hit still dispatched a miss');
  eq(named(host,'goodNoteHit'),0,'HXC-canceled hit dispatched Psych good post');

  // Controlled Psych auto skips ignoreNote, but not arbitrary hazard flags.
  host=new PlayState();host.demoMode=true;note=new FixtureNote(host.events);
  note.wasGoodHit=true;note.ignoreNote=true;host.currentAutoNote=note;host.notes.members=[note];
  check(!host.dispatchHxcAutoNoteHit(note,true),'controlled Psych auto accepted ignoreNote');
  check(note.autoHitSuppressed&&!note.wasGoodHit&&host.preWasGoodHit.length==0,
   'ignoreNote did not suppress before source Pre');

  // Opponent Pre retains the already-pending hit flag; only player Pre clears
  // it so a canceled player attempt can be retried.
  host=new PlayState();note=new FixtureNote(host.events);note.wasGoodHit=true;
  host.currentAutoNote=note;host.notes.members=[note];
  check(host.dispatchHxcAutoNoteHit(note,false),'opponent auto hit unexpectedly canceled');
  check(host.preWasGoodHit.length==2&&host.preWasGoodHit[0]&&host.preWasGoodHit[1],
   'opponent Pre did not retain wasGoodHit=true');
  Sys.println('OK');
 }
}'''


class SourceHitLifecycleTest(unittest.TestCase):
    def test_extracted_hit_and_finish_methods_preserve_source_and_native_lifecycles(self):
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        markers = (
            "function dispatchPsychNoteHitPre(",
            "function dispatchPsychNoteHit(",
            "function finishGoodNoteHit(",
        )
        methods = "\n".join(
            extract_method(play_state, marker).replace(marker, "public " + marker, 1)
            .replace("note:Note", "note:FixtureNote")
            for marker in markers
        )
        fixture = HOST.replace("__EXTRACTED_METHODS__", methods)
        with tempfile.TemporaryDirectory(prefix="source-hit-lifecycle-", dir=ROOT / "tmp") as directory:
            work = FixturePath(directory)
            (work / "FixtureNote.hx").write_text(NOTE, encoding="utf-8", newline="\n")
            (work / "PlayState.hx").write_text(fixture, encoding="utf-8", newline="\n")
            (work / "SourceHitLifecycleFixture.hx").write_text(MAIN, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "--main", "SourceHitLifecycleFixture", "--interp"],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=90,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_extracted_hxc_auto_hit_and_hazard_routes_preserve_gates(self):
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        markers = (
            "function dispatchPsychNoteHitPre(",
            "function dispatchPsychNoteHit(",
            "function finishGoodNoteHit(",
            "function dispatchHxcAutoNoteHit(",
            "function dispatchHitCausesMiss(",
        )
        methods = "\n".join(
            extract_method(play_state, marker).replace(marker, "public " + marker, 1)
            .replace("note:Note", "note:FixtureNote")
            for marker in markers
        )
        fixture = HOST.replace("__EXTRACTED_METHODS__", methods)
        with tempfile.TemporaryDirectory(prefix="source-auto-hit-lifecycle-", dir=ROOT / "tmp") as directory:
            work = FixturePath(directory)
            (work / "FixtureNote.hx").write_text(NOTE, encoding="utf-8", newline="\n")
            (work / "PlayState.hx").write_text(fixture, encoding="utf-8", newline="\n")
            (work / "SourceAutoHitLifecycleFixture.hx").write_text(AUTO_MAIN, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "--main", "SourceAutoHitLifecycleFixture", "--interp"],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=90,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

        # Pin the narrow auto-pending loop slice without importing the rest of
        # update(), whose native HaxeFlixel graph is unrelated to this contract.
        opponent_start = play_state.index(
            "if (!sourceScoreNightmare && !daNote.mustPress && daNote.wasGoodHit && !daNote.nightmareVisionHitDispatched"
        )
        player_start = play_state.index(
            "} else if (!sourceScoreNightmare && daNote.mustPress && daNote.wasGoodHit && !daNote.nightmareVisionHitDispatched",
            opponent_start,
        )
        opponent_loop = play_state[opponent_start:player_start]
        self.assertLess(
            opponent_loop.index("sourceScoreLedgerActive() && !sourceScoreNightmare && daNote.ignoreNote"),
            opponent_loop.rindex("dispatchHxcAutoNoteHit(daNote, false)"),
            "source opponent ignoreNote gate must run before its Pre callbacks",
        )
        player_stop = play_state.index("var singer = noteSingerForSide(daNote, true)", player_start)
        player_loop = play_state[player_start:player_stop]
        helper_call = player_loop.rindex("if (!dispatchHxcAutoNoteHit(daNote, true))")
        hazard_gate = player_loop.index("if (sourceScoreLedgerActive() && !sourceScoreNightmare && daNote.hitCausesMiss)")
        miss_call = player_loop.index("dispatchHitCausesMiss(daNote, true)", hazard_gate)
        finish_call = player_loop.index("finishGoodNoteHit(daNote, true, null, false)", hazard_gate)
        score_call = player_loop.index("scoreSourceAutoNote(daNote, true)", hazard_gate)
        self.assertLess(helper_call, hazard_gate)
        self.assertLess(hazard_gate, miss_call)
        self.assertLess(miss_call, finish_call)
        self.assertLess(finish_call, score_call)


if __name__ == "__main__":
    unittest.main()
