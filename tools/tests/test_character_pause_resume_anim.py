"""Verify Character forwards source pause/resume animation calls."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"


class CharacterPauseResumeAnimTest(unittest.TestCase):
    def test_character_animation_pause_and_resume_forward_to_controller(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        source = (ROOT / "source/Character.hx").read_text()
        methods = []
        for name in ("pauseAnim", "resumeAnim"):
            match = re.search(
                rf"\t@:keep public function {name}\(\):Void animation\.{name.removesuffix('Anim')}\(\);",
                source,
            )
            self.assertIsNotNone(match, f"Character.{name} must retain the source animation API")
            methods.append(match.group(0).strip())

        fixture = """class AnimationStub {
 public var paused:Int = 0;
 public var resumed:Int = 0;
 public function new() {}
 public function pause():Void paused++;
 public function resume():Void resumed++;
}
class CharacterHarness {
 public var animation:AnimationStub;
 public function new() animation = new AnimationStub();
 %s
 %s
}
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var actor = new CharacterHarness();
  actor.pauseAnim(); actor.pauseAnim();
  actor.resumeAnim();
  check(actor.animation.paused == 2 && actor.animation.resumed == 1,
   "Character pause/resume did not forward each call to its animation controller");
 }
}""" % tuple(methods)

        with tempfile.TemporaryDirectory(prefix="character-pause-resume-", dir=ROOT / "tmp") as scratch:
            work = Path(scratch)
            (work / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
