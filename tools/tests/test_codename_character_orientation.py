"""Execute the shared Codename character orientation helper with frame/offset doubles."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameCharacterOrientationTest(unittest.TestCase):
    def test_slot_flip_and_player_offset_convention_swap_authored_right_suffixes(self):
        fixture = r'''class Main {
 static function check(ok:Bool,label:String):Void if(!ok)throw label;
 static function main():Void {
  var frames:Map<String,Array<Int>>=[
   "singLEFT"=>[1,2],"singRIGHT"=>[3,4],
   "singLEFTmiss"=>[5],"singRIGHTmiss"=>[6],
   "singLEFT-alt"=>[7],"singRIGHT-alt"=>[8],
   "singRIGHT-dodge"=>[9],
   "singLEFT-hold"=>[10],"singRIGHT-hold"=>[11],
   "singLEFT-only"=>[12]
  ];
  var offsets:Map<String,Array<Dynamic>>=[];
  offsets.set("singLEFT",[10,11]);offsets.set("singRIGHT",[20,21]);
  offsets.set("singRIGHTmiss",[30,31]);
  offsets.set("singLEFT-alt",[40,41]);offsets.set("singRIGHT-alt",[50,51]);
  offsets.set("singRIGHT-dodge",[60,61]);
  offsets.set("singLEFT-hold",[70,71]);offsets.set("singRIGHT-hold",[80,81]);
  offsets.set("singLEFT-only",[90,91]);
  var names=["singLEFT","singRIGHT","singLEFTmiss","singRIGHTmiss",
   "singLEFT-alt","singRIGHT-alt","singRIGHT-dodge","singLEFT-hold","singRIGHT-hold",
   "singLEFT-only"];
  var player=CodenameCharacterOrientation.apply(true,false,false,names,
   function(name:String):Array<Int> return frames.get(name),
   function(name:String,value:Array<Int>):Void frames.set(name,value),offsets);
  check(player,"slot flip must toggle definition flip even when native noFlip would be true");
  check(frames.get("singLEFT")[0]==3 && frames.get("singRIGHT")[0]==1,
   "mismatched playerOffsets must swap sing direction frames");
  check(frames.get("singLEFTmiss")[0]==6 && frames.get("singRIGHTmiss")[0]==5,
   "mismatched playerOffsets must swap miss direction frames");
  check(frames.get("singLEFT-alt")[0]==8 && frames.get("singRIGHT-alt")[0]==7,
   "authored singRIGHT suffixes must swap their paired frame lists");
  check(frames.get("singRIGHT-dodge")[0]==9 && frames.get("singLEFT-dodge")==null,
   "a missing frame counterpart must leave the existing frame list in place");
  check(frames.get("singLEFT-hold")[0]==11 && frames.get("singRIGHT-hold")[0]==10,
   "all authored singRIGHT suffixes, including hold, must be enumerated");
  check(frames.get("singLEFT-only")[0]==12 && frames.get("singRIGHT-only")==null,
   "left-only suffixes must not be inferred or swapped");
  check(offsets.get("singLEFT")[0]==20 && offsets.get("singRIGHT")[0]==10,
   "sing offsets must move with their swapped animations");
  check(offsets.get("singLEFTmiss")[0]==30 && !offsets.exists("singRIGHTmiss"),
   "one-sided miss offset follows switchOffset removal semantics");
  check(offsets.get("singLEFT-alt")[0]==50 && offsets.get("singRIGHT-alt")[0]==40,
   "suffix offsets must move with their paired animations");
  check(offsets.get("singLEFT-dodge")[0]==60 && !offsets.exists("singRIGHT-dodge"),
   "one-sided suffix offset follows switchOffset removal semantics");
  check(offsets.get("singLEFT-only")[0]==90 && !offsets.exists("singRIGHT-only"),
   "left-only suffix offsets must remain untouched");

  var matchingFrames:Map<String,Array<Int>>=["singLEFT-alt"=>[1],"singRIGHT-alt"=>[2]];
  var matchingOffsets:Map<String,Array<Dynamic>>=["singLEFT-alt"=>[4],"singRIGHT-alt"=>[9]];
  var matching=CodenameCharacterOrientation.apply(true,true,true,["singRIGHT-alt"],
   function(name:String):Array<Int> return matchingFrames.get(name),
   function(name:String,value:Array<Int>):Void matchingFrames.set(name,value),matchingOffsets);
  check(!matching,"matching playerOffsets still toggles the slot flip from XML true");
  check(matchingFrames.get("singLEFT-alt")[0]==1 && matchingFrames.get("singRIGHT-alt")[0]==2
   && matchingOffsets.get("singLEFT-alt")[0]==4 && matchingOffsets.get("singRIGHT-alt")[0]==9,
   "matching playerOffsets must leave direction data in place");

  var opponent=CodenameCharacterOrientation.apply(false,true,true,["singRIGHT-alt"],
   function(name:String):Array<Int> return null,
   function(name:String,value:Array<Int>):Void {},new Map());
  check(opponent,"opponent slot keeps XML flip while applying no player flip");
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            path = Path(scratch)
            (path / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(path), "--run", "Main"],
                cwd=ROOT, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
