"""Exercise frame/offset pairing in the legacy player-facing orientation path."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CharacterAnimationOrientationTest(unittest.TestCase):
    def test_frame_swaps_carry_offsets_and_preserve_missing_keys(self):
        source = (ROOT / "source/Character.hx").read_text()
        constructor = source.split("if (codenameCharacterMeta == null && psychAuthoredFlipX == null && isPlayer && !noFlip)", 1)[1]
        self.assertIn("CharacterAnimationOrientation.swapAll(animation.getNameList()", constructor)
        self.assertNotIn("animation.getByName('singRIGHT') != null", constructor)

        fixture = r'''class Main {
 static function check(ok:Bool, label:String):Void if (!ok) throw label;
 static function main():Void {
  var frames:Map<String, Array<Int>> = [
   "singLEFT" => [1, 2], "singRIGHT" => [3, 4],
   "singLEFTmiss" => [5], "singRIGHTmiss" => [6],
   "singLEFT-hold" => [7], "singRIGHT-hold" => [8],
   "singLEFT-alt" => [9], "singRIGHT-alt" => [10]
  ];
  var offsets:Map<String, Array<Dynamic>> = [
   "singLEFT" => [10, 11], "singRIGHT" => [20, 21],
   "singLEFTmiss" => [30, 31], "singRIGHTmiss" => [40, 41],
   "singLEFT-hold" => [50, 51], "singRIGHT-hold" => [60, 61],
   "singLEFT-alt" => [-30, 15], "singRIGHT-alt" => [-1, -24]
  ];
  var get = function(name:String):Array<Int> return frames.get(name);
  var set = function(name:String, value:Array<Int>):Void frames.set(name, value);
  check(CharacterAnimationOrientation.swapAll(["singRIGHT", "singRIGHTmiss", "singRIGHT-hold", "singRIGHT-alt"],
   get, set, offsets) == 4, "paired animation count");
  check(frames.get("singLEFT")[0] == 3 && frames.get("singRIGHT")[0] == 1, "sing frames");
  check(offsets.get("singLEFT")[0] == 20 && offsets.get("singRIGHT")[0] == 10, "sing offsets");
  check(frames.get("singLEFTmiss")[0] == 6 && offsets.get("singLEFTmiss")[0] == 40, "miss pair");
  check(frames.get("singLEFT-hold")[0] == 8 && offsets.get("singLEFT-hold")[0] == 60, "hold pair");
  check(frames.get("singLEFT-alt")[0] == 10 && offsets.get("singLEFT-alt")[0] == -1, "alt pair");

  var altFrames:Map<String, Array<Int>> = ["singLEFT-alt" => [11], "singRIGHT-alt" => [12]];
  var altOffsets:Map<String, Array<Dynamic>> = ["singLEFT-alt" => [1, 2], "singRIGHT-alt" => [3, 4]];
  check(CharacterAnimationOrientation.swapAll(["singLEFT-alt", "singRIGHT-alt"],
   function(name:String):Array<Int> return altFrames.get(name),
   function(name:String, value:Array<Int>):Void altFrames.set(name, value), altOffsets) == 1,
   "alt-only pair skipped without base singRIGHT");
  check(altFrames.get("singLEFT-alt")[0] == 12 && altOffsets.get("singLEFT-alt")[0] == 3,
   "alt-only frame and offset mismatch");

  var unpairedFrames:Map<String, Array<Int>> = ["singRIGHT-dodge" => [13]];
  var unpairedOffsets:Map<String, Array<Dynamic>> = ["singRIGHT-dodge" => [5, 6]];
  check(CharacterAnimationOrientation.swapAll(["singRIGHT-dodge"],
   function(name:String):Array<Int> return unpairedFrames.get(name),
   function(name:String, value:Array<Int>):Void unpairedFrames.set(name, value), unpairedOffsets) == 0,
   "unpaired suffix should remain authored");
  check(unpairedFrames.get("singRIGHT-dodge")[0] == 13
   && unpairedOffsets.get("singRIGHT-dodge")[0] == 5, "unpaired suffix changed");

  var missingFrames:Map<String, Array<Int>> = ["singLEFT" => [9]];
  var oneSided:Map<String, Array<Dynamic>> = ["singLEFT" => [70, 71]];
  check(!CharacterAnimationOrientation.swapPair("singLEFT", "singRIGHT",
   function(name:String):Array<Int> return missingFrames.get(name),
   function(name:String, value:Array<Int>):Void missingFrames.set(name, value), oneSided),
   "a missing frame pair must not be swapped");
  check(oneSided.exists("singLEFT") && !oneSided.exists("singRIGHT"), "missing-frame pair changed offsets");

  var oneSidedFrames:Map<String, Array<Int>> = ["singLEFT" => [9], "singRIGHT" => [10]];
  var oneSidedOffsets:Map<String, Array<Dynamic>> = ["singRIGHT" => [80, 81]];
  CharacterAnimationOrientation.swapPair("singLEFT", "singRIGHT",
   function(name:String):Array<Int> return oneSidedFrames.get(name),
   function(name:String, value:Array<Int>):Void oneSidedFrames.set(name, value), oneSidedOffsets);
  check(oneSidedOffsets.get("singLEFT")[0] == 80 && !oneSidedOffsets.exists("singRIGHT"),
   "single authored offset did not follow its animation");
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            path = Path(scratch)
            (path / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", str(path), "--run", "Main"],
                cwd=ROOT, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
