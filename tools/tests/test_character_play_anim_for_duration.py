"""Pin the shared Character timed animation API and its forced animation gate."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def function_body(source, name):
    marker = "function " + name + "("
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    quote = None
    escaped = False
    line_comment = False
    block_comment = False
    index = opening
    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
                index += 1
        elif quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char == "/" and next_char == "/":
            line_comment = True
            index += 1
        elif char == "/" and next_char == "*":
            block_comment = True
            index += 1
        elif char in ('"', "'"):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
        index += 1
    raise AssertionError("unterminated function " + name)


class CharacterPlayAnimForDurationTest(unittest.TestCase):
    def test_forced_animation_blocks_dance_and_sing_until_timer_expires(self):
        source = (ROOT / "source/Character.hx").read_text()
        helper = function_body(source, "playAnimForDuration")
        play = function_body(source, "playAnim")
        self.assertIn("@:keep public function playAnimForDuration", source)
        self.assertIn("if (!canPlayAnimations) return;", play)
        self.assertIn("forcedAnimationTimer.cancel();", source)

        fixture = r'''class FlxTimer {
 public var duration:Float=0;
 public var starts:Int=0;
 var completion:Dynamic;
 public function new() {}
 public function start(duration:Float=1, ?completion:Dynamic,
  loops:Int=1):FlxTimer {
  this.duration=Math.abs(duration); this.completion=completion; starts++; return this;
 }
 public function cancel():Void completion=null;
 public function destroy():Void completion=null;
 public function expire():Void {
  var callback=completion; completion=null;
  if(callback!=null) Reflect.callMethod(null,callback,[this]);
 }
}
class Main {
 var canPlayAnimations:Bool=true;
 var forcedAnimationTimer:FlxTimer=new FlxTimer();
 var current:String='idle';
 var played:Array<String>=[];
 function new() {}
 function playAnim(name:String,force:Bool=false,reversed:Bool=false,frame:Int=0):Void {
  if(!canPlayAnimations)return;
  current=name; played.push(name);
 }
 function sing():Void playAnim('singLEFT',true);
 function dance():Void playAnim('danceLeft',true);
 HELPER
 static function check(ok:Bool,message:String):Void if(!ok)throw message;
 static function main():Void {
  var actor=new Main();
  actor.playAnimForDuration('cheer');
  check(actor.current=='cheer' && actor.canPlayAnimations,
   'non-forced request did not play without locking later animation');
  check(actor.forcedAnimationTimer.duration==0.6,
   'default source duration changed');
  actor.forcedAnimationTimer.expire();
  check(actor.canPlayAnimations,'non-forced timer changed animation availability');

  actor.playAnimForDuration('sad',1.25,true);
  check(actor.current=='sad' && !actor.canPlayAnimations,
   'forced request did not start then lock the requested animation');
  check(actor.forcedAnimationTimer.duration==1.25,'forced duration was not retained');
  actor.sing();
  actor.dance();
  actor.playAnim('idle',true);
  check(actor.current=='sad','dance or sing interrupted the forced animation');

  actor.forcedAnimationTimer.expire();
  check(actor.canPlayAnimations,'timer completion did not release the forced lock');
  actor.sing();
  check(actor.current=='singLEFT','sing stayed blocked after the forced duration');
  actor.dance();
  check(actor.current=='danceLeft','dance stayed blocked after the forced duration');

  actor.playAnimForDuration('sad-again',1,true);
  var starts=actor.forcedAnimationTimer.starts;
  actor.playAnimForDuration('cheer',0.2);
  check(actor.current=='sad-again' && actor.forcedAnimationTimer.starts==starts+1
   && actor.forcedAnimationTimer.duration==0.2,
   "non-forced helper did not restart the donor's shared timer while playback was locked");
  actor.forcedAnimationTimer.expire();
  check(!actor.canPlayAnimations && actor.current=='sad-again',
   'non-forced timer completion unexpectedly released a forced lock');
  actor.playAnimForDuration('recover',0.3,true);
  actor.forcedAnimationTimer.expire();
  check(actor.canPlayAnimations && actor.current=='recover',
   'new forced request did not restart and later release a replaced timer');

  actor.playAnimForDuration('first-special',0.5,true);
  actor.playAnimForDuration('second-special',2,true);
  check(actor.current=='second-special' && !actor.canPlayAnimations
   && actor.forcedAnimationTimer.duration==2,
   'later forced request did not replace the earlier animation and duration');
  actor.forcedAnimationTimer.expire();
  check(actor.canPlayAnimations,'replacement forced timer failed to unlock');
 }
}'''.replace("HELPER", helper)

        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            (work / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_nightmare_vision_bopper_exposes_the_inherited_sprite_helper(self):
        bopper = (ROOT / "source/NightmareVisionBopper.hx").read_text()
        self.assertIn("extends NightmareVisionFunkinSprite", bopper)
        source = (ROOT / "source/NightmareVisionFunkinSprite.hx").read_text()
        helper = function_body(source, "playAnimForDuration")
        play = function_body(source, "playAnim")
        self.assertIn("public function playAnimForDuration", source)
        self.assertIn("if (!canPlayAnimations) return;", play)

        fixture = r'''class FlxTimer {
 public var duration:Float=0;
 var completion:Dynamic;
 public function new() {}
 public function start(duration:Float=1, ?completion:Dynamic,
  loops:Int=1):FlxTimer {
  this.duration=Math.abs(duration); this.completion=completion; return this;
 }
 public function cancel():Void completion=null;
 public function destroy():Void completion=null;
 public function expire():Void {
  var callback=completion; completion=null;
  if(callback!=null) Reflect.callMethod(null,callback,[this]);
 }
}
class Main {
 var canPlayAnimations:Bool=true;
 var forcedAnimationTimer:FlxTimer=new FlxTimer();
 var current:String='idle';
 function new() {}
 function playAnim(name:String,forced:Bool=false,reversed:Bool=false,frame:Int=0):Void {
  if(!canPlayAnimations)return;
  current=name;
 }
 function sing():Void playAnim('singLEFT',true);
 function dance():Void playAnim('danceLeft',true);
 HELPER
 static function check(ok:Bool,message:String):Void if(!ok)throw message;
 static function main():Void {
  var actor=new Main();
  actor.playAnimForDuration('hey',0.75,true);
  actor.sing(); actor.dance();
  check(actor.current=='hey' && !actor.canPlayAnimations,
   'Bopper sing or dance interrupted a forced sprite animation');
  check(actor.forcedAnimationTimer.duration==0.75,'Bopper duration changed');
  actor.forcedAnimationTimer.expire();
  check(actor.canPlayAnimations,'Bopper timer did not release its animation gate');
  actor.playAnim('idle');
  check(actor.current=='idle','Bopper playAnim remained locked after expiry');
 }
}'''.replace("HELPER", helper)

        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            (work / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
