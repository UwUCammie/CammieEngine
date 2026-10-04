"""Exercise the source input candidate selectors without loading the engine."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]


MAIN = r'''package;
class Candidate {
 public var id:String;
 public var lane:Int;
 public var blocked:Bool;
 public var sustain:Bool;
 public var lift:Bool;
 public var low:Bool;
 public var strumTime:Float;
 public var hitPriority:Int;
 public function new(id:String, lane:Int, time:Float, priority:Int=0,
  low:Bool=false, sustain:Bool=false, lift:Bool=false, blocked:Bool=false) {
  this.id=id; this.lane=lane; strumTime=time; hitPriority=priority;
  this.low=low; this.sustain=sustain; this.lift=lift; this.blocked=blocked;
 }
}

class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function ids(notes:Array<Candidate>):String
  return [for (note in notes) note.id].join(",");

 static function main():Void {
  var notes:Array<Candidate> = [
   new Candidate("normal-late", 0, 30),
   new Candidate("low-late", 0, 20, 0, true),
   new Candidate("normal-early", 0, 10),
   new Candidate("low-early", 0, 5, 0, true),
   new Candidate("other-lane", 1, 1),
   new Candidate("blocked", 0, 0, 99, false, false, false, true),
   new Candidate("sustain", 0, 2, 99, false, true),
   new Candidate("lift", 0, 3, 99, false, false, true),
   null
  ];
  var psych = SourceInputNotes.psych(notes,
   function(n:Candidate):Bool return n.lane == 0 && !n.blocked,
   function(n:Candidate):Bool return n.sustain,
   function(n:Candidate):Bool return n.lift,
   function(n:Candidate):Bool return n.low,
   function(n:Candidate):Float return n.strumTime);
  check(ids(psych) == "normal-early,normal-late,low-early,low-late",
   "Psych should filter ineligible/lane-mismatched, sustain, and lift notes, then sort normal before low by time: " + ids(psych));

  var laneOne = SourceInputNotes.psych(notes,
   function(n:Candidate):Bool return n.lane == 1 && !n.blocked,
   function(n:Candidate):Bool return n.sustain,
   function(n:Candidate):Bool return n.lift,
   function(n:Candidate):Bool return n.low,
   function(n:Candidate):Float return n.strumTime);
  check(ids(laneOne) == "other-lane", "lane acceptance should isolate the requested lane");

  var nvNotes:Array<Candidate> = [
   new Candidate("early-lower-priority", 0, 1, 1),
   new Candidate("late-higher-priority", 0, 90, 2),
   new Candidate("later-tie", 0, 20, 2),
   new Candidate("earlier-tie", 0, 10, 2),
   new Candidate("blocked-top", 0, 0, 100, false, false, false, true),
   new Candidate("other-lane", 1, 0, 100),
   new Candidate("sustain-occupies-lane", 0, 4, 999, false, true),
   null
  ];
  var nv = SourceInputNotes.nightmareVision(nvNotes,
   function(n:Candidate):Bool return n.lane == 0 && !n.blocked,
   function(n:Candidate):Bool return n.sustain,
   function(n:Candidate):Int return n.hitPriority,
   function(n:Candidate):Float return n.strumTime);
  check(nv.top != null && nv.top.id == "earlier-tie",
   "Nightmare Vision should prefer priority over earlier time, then choose earliest among equal priority");
  check(nv.hasSustain, "an accepted sustain should set hasSustain without becoming top");

  var donorScanQuirk = SourceInputNotes.nightmareVision([
   new Candidate("high-priority-later", 0, 20, 2),
   new Candidate("lower-priority-earlier", 0, 10, 1)
  ],
   function(n:Candidate):Bool return n.lane == 0,
   function(n:Candidate):Bool return n.sustain,
   function(n:Candidate):Int return n.hitPriority,
   function(n:Candidate):Float return n.strumTime);
  check(donorScanQuirk.top != null && donorScanQuirk.top.id == "lower-priority-earlier",
   "the donor scan allows an earlier lower-priority candidate to replace the current top");

  var sustainOnly = SourceInputNotes.nightmareVision([new Candidate("sustain", 2, 4, 4, false, true)],
   function(n:Candidate):Bool return n.lane == 2,
   function(n:Candidate):Bool return n.sustain,
   function(n:Candidate):Int return n.hitPriority,
   function(n:Candidate):Float return n.strumTime);
  check(sustainOnly.top == null && sustainOnly.hasSustain,
   "a sustain-only lane should report occupancy without selecting a top note");

  var blockedOnly = SourceInputNotes.nightmareVision([new Candidate("blocked", 2, 4, 4, false, false, false, true)],
   function(n:Candidate):Bool return n.lane == 2 && !n.blocked,
   function(n:Candidate):Bool return n.sustain,
   function(n:Candidate):Int return n.hitPriority,
   function(n:Candidate):Float return n.strumTime);
  check(blockedOnly.top == null && !blockedOnly.hasSustain,
   "rejected candidates should not affect either result");
 }
}
'''


class SourceInputNotesTest(unittest.TestCase):
    def test_candidate_selection_rules(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(MAIN, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
