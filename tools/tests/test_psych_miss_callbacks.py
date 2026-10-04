"""Exercise the shared Psych miss callback router and donor stop semantics."""
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
  var calls:Array<Call> = [];
  var result:Dynamic = ScriptCallbackResult.CONTINUE;
  var broadcast = function(name:String,args:Array<Dynamic>,family:String):Dynamic {
   calls.push(new Call(name,args,family));
   return result;
  };

  PsychMissCallbacks.dispatch(null,3,99,broadcast);
  eq(calls.length,1,'empty press dispatch count');
  eq(calls[0].name,'noteMissPress','empty press callback name');
  eq(calls[0].family,'Scripts','empty press callback family');
  eq(calls[0].args.length,1,'empty press callback argument count');
  eq(calls[0].args[0],3,'empty press direction');

  calls=[];
  var note = new FakeNote(2,'Hurt Note',true);
  var argsSeen:Array<Dynamic> = null;
  var ordered = function(name:String,args:Array<Dynamic>,family:String):Dynamic {
   calls.push(new Call(name,args,family));
   if (family == 'Luas') argsSeen=args;
   return ScriptCallbackResult.STOP_LUA;
  };
  PsychMissCallbacks.dispatch(note,0,7,ordered);
  eq(calls.length,2,'STOP_LUA still invokes HScript');
  eq(calls[0].name,'noteMiss','Lua callback name');
  eq(calls[0].family,'Luas','Lua callback family');
  eq(argsSeen.length,4,'Lua callback argument count');
  eq(argsSeen[0],7,'Lua group slot');
  eq(argsSeen[1],2,'Lua note data');
  eq(argsSeen[2],'Hurt Note','Lua reads the script-facing noteType accessor');
  eq(argsSeen[3],true,'Lua sustain flag');
  eq(calls[1].name,'noteMiss','HScript callback name');
  eq(calls[1].family,'HScript','HScript callback family');
  eq(calls[1].args.length,1,'HScript callback argument count');
  check(calls[1].args[0] == note,'HScript receives the original live Note');

  for (stop in [ScriptCallbackResult.STOP, ScriptCallbackResult.STOP_HSCRIPT,
      ScriptCallbackResult.STOP_ALL]) {
   calls=[]; result=stop;
   PsychMissCallbacks.dispatch(note,0,0,broadcast);
   eq(calls.length,1,'cross-family stop suppresses HScript: ' + stop);
   eq(calls[0].family,'Luas','Lua dispatch occurs before stop decision');
  }

  for (pass in [null, ScriptCallbackResult.CONTINUE, 'ordinary-result']) {
   calls=[]; result=pass;
   PsychMissCallbacks.dispatch(note,0,0,broadcast);
   eq(calls.length,2,'non-cross-family return permits HScript: ' + Std.string(pass));
   eq(calls[1].family,'HScript','HScript follows Lua for non-stop values');
  }
 }
}'''


class PsychMissCallbacksTest(unittest.TestCase):
    def test_router_arguments_and_lua_hscript_stops(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(MAIN, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_callback_order_and_stop_conditions_match_pinned_psych_donor(self):
        play = DONOR_PLAY_STATE.read_text(encoding="utf-8")
        miss = play[play.index("function noteMiss("):play.index("function noteMissPress(")]
        self.assertIn("callOnLuas('noteMiss', [", miss)
        self.assertIn("daNote.noteType", miss)
        self.assertIn("Function_StopHScript", miss)
        self.assertIn("Function_StopAll", miss)
        self.assertIn("callOnHScript('noteMiss', [daNote])", miss)
        press = play[play.index("function noteMissPress("):play.index("function noteMissCommon(")]
        self.assertIn("callOnScripts('noteMissPress', [direction])", press)


if __name__ == "__main__":
    unittest.main()
