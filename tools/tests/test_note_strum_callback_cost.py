"""Absent legacy strum callbacks need no per-note actor resolution."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class NoteStrumCallbackCostTest(unittest.TestCase):
    def test_optional_callback_keeps_bounds_and_one_shot_semantics(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        start = source.index("\tinline function dispatchNoteStrumCallback(")
        method = source[start:source.index("\n\tfunction getHaxeActor(", start)]
        self.assertIn("dispatchNoteStrumCallback(daNote);", source)
        fixture = '''class Note {
 public var noteStrum:Null<String>;
 public var y:Float;
 public function new(y:Float, ?hook:String) {this.y=y;noteStrum=hook;}
}
class Main {
 var lookups=0;
 var calls:Array<String>=[];
 function new() {}
 function getHaxeActor(who:Dynamic):Dynamic {lookups++;return {y:100.0};}
 function callHscript(name:String,args:Array<Dynamic>,scope:String):Void {
  if(scope != "modchart" || args.length != 0) throw "legacy callback payload changed";
  calls.push(name);
 }
''' + method + '''
 static function check(ok:Bool,text:String):Void if(!ok) throw text;
 static function main():Void {
  var state=new Main();
  for(i in 0...6000) state.dispatchNoteStrumCallback(new Note(i));
  check(state.lookups==0,"ordinary notes resolved an unused actor");
  var early=new Note(79,"early");
  state.dispatchNoteStrumCallback(early);
  check(early.noteStrum=="early" && state.calls.length==0,"callback fired before range");
  var low=new Note(80,"low"), high=new Note(120,"high");
  state.dispatchNoteStrumCallback(low);
  state.dispatchNoteStrumCallback(high);
  state.dispatchNoteStrumCallback(low);
  check(state.lookups==3,"one actor lookup per enabled check was not preserved");
  check(state.calls.join(",")=="low,high" && low.noteStrum==null && high.noteStrum==null,
   "inclusive range or one-shot callback changed");
  var late=new Note(121,"late");
  state.dispatchNoteStrumCallback(late);
  check(late.noteStrum=="late" && state.calls.length==2,"callback fired after range");
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(fixture, newline="\n")
            result = subprocess.run([*HAXE_COMMAND, "-cp", folder, "--run", "Main"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
