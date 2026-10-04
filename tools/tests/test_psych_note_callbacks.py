"""Pin the shared Psych hit callback ABI against executable helpers and donor source."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
DONOR_PLAY_STATE = ROOT.parent / "fnf_sources/FNF-PsychEngine/source/states/PlayState.hx"

MAIN = r'''package;
class FakeNote {
 public var noteData:Int;
 public var isSustainNote:Bool;
 var authoredKind:String;
 public var noteType(get, set):String;
 function get_noteType():String return authoredKind;
 function set_noteType(value:String):String { authoredKind=value; return value; }
 public function new(data:Int, kind:String, sustain:Bool) {
  noteData=data; authoredKind=kind; isSustainNote=sustain;
 }
}
class Call {
 public var name:String; public var args:Array<Dynamic>; public var family:String;
 public function new(name:String,args:Array<Dynamic>,family:String) {
  this.name=name; this.args=args; this.family=family;
 }
}
class Main {
 static function check(value:Bool,message:String):Void if (!value) throw message;
 static function eq(actual:Dynamic,expected:Dynamic,message:String):Void
  if (actual != expected) throw message + ': expected ' + Std.string(expected) + ', got ' + Std.string(actual);
 static function main():Void {
  var note = new FakeNote(-2,'Authored Hurt Type',true);
  var calls:Array<Call> = [];
  var luaResult:Dynamic=ScriptCallbackResult.CONTINUE;
  var hscriptResult:Dynamic='hscript-result';
  var broadcast = function(name:String,args:Array<Dynamic>,family:String):Dynamic {
   calls.push(new Call(name,args,family));
   return family=='Luas'?luaResult:hscriptResult;
  };

  var returned=PsychNoteCallbacks.dispatch('goodNoteHit',note,8,2,broadcast);
  eq(returned,hscriptResult,'generic router returns the HScript result');
  eq(calls.length,2,'generic router dispatches both families');
  eq(calls[0].name,'goodNoteHit','good-hit callback name');
  eq(calls[0].family,'Luas','Lua callback family');
  eq(calls[0].args.length,4,'Lua scalar arity');
  eq(calls[0].args[0],8,'Lua group slot');
  eq(calls[0].args[1],2,'caller-supplied normalized lane');
  eq(calls[0].args[2],'Authored Hurt Type','Lua reads the noteType property');
  eq(calls[0].args[3],true,'Lua sustain value');
  eq(calls[1].family,'HScript','HScript callback family');
  eq(calls[1].args.length,1,'HScript callback arity');
  check(calls[1].args[0]==note,'HScript receives the original live Note');

  for (stop in [ScriptCallbackResult.STOP, ScriptCallbackResult.STOP_HSCRIPT,
      ScriptCallbackResult.STOP_ALL]) {
   calls=[]; luaResult=stop;
   returned=PsychNoteCallbacks.dispatch('opponentNoteHit',note,3,2,broadcast);
   eq(returned,stop,'cross-family stop is returned to the caller');
   eq(calls.length,1,'cross-family stop suppresses HScript: '+stop);
   eq(calls[0].name,'opponentNoteHit','opponent callback name');
   eq(calls[0].family,'Luas','Lua dispatch occurs before stop decision');
  }

  for (pass in [null,ScriptCallbackResult.CONTINUE,ScriptCallbackResult.STOP_LUA,'ordinary-result']) {
   calls=[]; luaResult=pass; hscriptResult='after-'+Std.string(pass);
   returned=PsychNoteCallbacks.dispatch('goodNoteHit',note,0,-2,broadcast);
   eq(calls.length,2,'Lua-only stop or non-stop permits HScript: '+Std.string(pass));
   eq(calls[1].family,'HScript','HScript follows Lua for '+Std.string(pass));
   eq(calls[1].args[0],note,'HScript Note identity after '+Std.string(pass));
   eq(returned,hscriptResult,'generic router returns final family result');
  }

  // A pre-hook can mutate the Note before post-hit dispatch. Lua keeps the
  // donor's pre-captured scalar ABI while HScript observes the live object.
  var changedNote = new FakeNote(-2,'Before Pre Hook',true);
  var capturedLua:Array<Dynamic>=[5,2,'Before Pre Hook',true];
  changedNote.noteData=-3;
  changedNote.noteType='After Pre Hook';
  changedNote.isSustainNote=false;
  var luaSnapshot:Array<Dynamic>=null;
  var hscriptNote:Dynamic=null;
  var mutationBroadcast = function(name:String,args:Array<Dynamic>,family:String):Dynamic {
   calls.push(new Call(name,args,family));
   if (family=='Luas') luaSnapshot=args else hscriptNote=args[0];
   return ScriptCallbackResult.CONTINUE;
  };
  calls=[];
  PsychNoteCallbacks.dispatch('goodNoteHit',changedNote,5,2,mutationBroadcast,capturedLua);
  check(luaSnapshot==capturedLua,'router replaced donor-captured Lua argument array');
  eq(luaSnapshot[0],5,'captured Lua slot after pre-hook mutation');
  eq(luaSnapshot[1],2,'captured Lua lane after pre-hook mutation');
  eq(luaSnapshot[2],'Before Pre Hook','captured Lua note type after pre-hook mutation');
  eq(luaSnapshot[3],true,'captured Lua sustain after pre-hook mutation');
  check(hscriptNote==changedNote,'HScript lost the live Note after pre-hook mutation');
  eq(Reflect.getProperty(hscriptNote,'noteData'),-3,'HScript did not see mutated live lane');
  eq(Reflect.getProperty(hscriptNote,'noteType'),'After Pre Hook','HScript did not see mutated live note type');
  eq(Reflect.getProperty(hscriptNote,'isSustainNote'),false,'HScript did not see mutated live sustain state');

  calls=[]; luaResult=ScriptCallbackResult.CONTINUE;
  var miss = new FakeNote(1,'Hurt Note',false);
  PsychMissCallbacks.dispatch(miss,0,12,broadcast);
  eq(calls.length,2,'miss wrapper delegates real Notes to generic router');
  eq(calls[0].name,'noteMiss','miss callback spelling preserved');
  eq(calls[0].args[0],12,'miss Lua ABI keeps the group slot');
  eq(calls[0].args[1],1,'miss Lua ABI keeps noteData as authored');
  eq(calls[1].args[0],miss,'miss HScript ABI keeps the live Note');

  calls=[];
  PsychMissCallbacks.dispatch(null,3,99,broadcast);
  eq(calls.length,1,'empty press remains a single family dispatch');
  eq(calls[0].name,'noteMissPress','empty press callback remains distinct');
  eq(calls[0].family,'Scripts','empty press keeps Scripts broadcast family');
  eq(calls[0].args[0],3,'empty press keeps lane argument');

  calls=[];
  eq(PsychNoteCallbacks.dispatch('goodNoteHit',null,0,0,broadcast),null,
   'generic helper does not fabricate a callback for a missing Note');
  eq(calls.length,0,'null Note does not dispatch');
  eq(PsychNoteCallbacks.dispatch('goodNoteHit',note,0,0,null),null,
   'generic helper tolerates an unavailable broadcaster');

  Sys.println('OK');
 }
}'''


class PsychNoteCallbacksTest(unittest.TestCase):
    def test_generic_note_router_and_miss_compatibility_wrapper(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(MAIN, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_successful_hit_hooks_match_pinned_donor_order_and_lanes(self):
        source = DONOR_PLAY_STATE.read_text(encoding="utf-8")
        opponent = source[source.index("function opponentNoteHit("):source.index("public function goodNoteHit(")]
        good = source[source.index("public function goodNoteHit("):source.index("public function invalidateNote(")]
        for name, method in (("opponentNoteHit", opponent), ("goodNoteHit", good)):
            self.assertIn(f"callOnLuas('{name}Pre', [", method)
            self.assertIn(f"callOnHScript('{name}Pre', [note])", method)
            self.assertIn(f"callOnLuas('{name}', [", method)
            self.assertIn(f"callOnHScript('{name}', [note])", method)
            self.assertIn("Function_StopHScript", method)
            self.assertIn("Function_StopAll", method)
            self.assertLess(method.index("stagesFunc(function(stage:BaseStage) stage." + name + "(note))"),
                            method.index(f"callOnLuas('{name}', ["))
            self.assertLess(method.index(f"callOnHScript('{name}', [note])"),
                            method.index("invalidateNote(note)"))
            self.assertRegex(method, r"if\s*\(!note\.isSustainNote\)\s*invalidateNote\(note\);")

        self.assertIn("var leData:Int = Math.round(Math.abs(note.noteData));", good)
        self.assertIn("Math.abs(note.noteData), note.noteType, note.isSustainNote", opponent)
        self.assertIn("note.wasGoodHit = true;", good)
        self.assertLess(good.index("note.wasGoodHit = true;"), good.index("stagesFunc(function(stage:BaseStage) stage.goodNoteHit(note))"))


if __name__ == "__main__":
    unittest.main()
