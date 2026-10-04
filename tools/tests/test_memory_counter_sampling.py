"""Pin the display-only memory counter's bounded sampling behavior."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = Path(HAXE_COMMAND[0])


class MemoryCounterSamplingTest(unittest.TestCase):
    def test_visible_counter_samples_twice_per_second_and_skips_equal_text(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        files = {
            "MemoryCounter.hx": (ROOT / "source/MemoryCounter.hx").read_text(),
            "Main.hx": r'''class FakeFPS {
 public var visible:Bool = false;
 public function new() {}
}
@:access(MemoryCounter)
class Main {
 public static var fpsCounter:FakeFPS = new FakeFPS();
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var counter = new MemoryCounter();
  counter.visible = false;
  counter.sampleAt(0);
  check(openfl.system.System.reads == 0,
   "hidden counter queried the native heap");

  counter.visible = true;
  openfl.system.System.value = 10 * 1024 * 1024;
  counter.sampleAt(10);
  check(openfl.system.System.reads == 1 && counter.textWrites == 1,
   "visible counter did not take its first sample");
  check(counter.text.indexOf("MEM: 10 MB") >= 0
   && counter.text.indexOf("MEM peak: 10 MB") >= 0,
   "first memory sample was not displayed");

  counter.sampleAt(509);
  check(openfl.system.System.reads == 1,
   "counter sampled before the 500 ms interval elapsed");
  counter.sampleAt(510);
  check(openfl.system.System.reads == 2 && counter.textWrites == 1,
   "equal memory text caused a redundant TextField write");

  openfl.system.System.value = 12 * 1024 * 1024;
  counter.sampleAt(1010);
  check(counter.text.indexOf("MEM peak: 12 MB") >= 0,
   "memory peak did not rise with the sampled heap");
  openfl.system.System.value = 7 * 1024 * 1024;
  counter.sampleAt(1510);
  check(counter.text.indexOf("MEM: 7 MB") >= 0
   && counter.text.indexOf("MEM peak: 12 MB") >= 0,
   "memory peak fell with the current sample");

  var writesBeforeHide = counter.textWrites;
  counter.visible = false;
  counter.sampleAt(1520);
  check(openfl.system.System.reads == 4 && counter.textWrites == writesBeforeHide,
   "hidden counter performed heap or text work");
  counter.visible = true;
  counter.sampleAt(1521);
  check(openfl.system.System.reads == 5,
   "counter waited for the old cadence after becoming visible");

  Main.fpsCounter.visible = true;
  counter.sampleAt(2021);
  check(counter.text.indexOf("\n\nMEM:") == 0,
   "memory overlay no longer follows both FPS display lines");
 }
}''',
            "openfl/events/Event.hx": '''package openfl.events;
class Event { public static inline var ENTER_FRAME:String = "enterFrame"; }
''',
            "openfl/display/FPS.hx": '''package openfl.display;
class FPS {}
''',
            "openfl/text/TextFormat.hx": '''package openfl.text;
class TextFormat {
 public function new(_font:String, _size:Int, _color:Int) {}
}
''',
            "openfl/text/TextField.hx": '''package openfl.text;
class TextField {
 public var x:Float = 0;
 public var y:Float = 0;
 public var width:Float = 0;
 public var height:Float = 0;
 public var selectable:Bool = true;
 public var visible:Bool = true;
 public var defaultTextFormat:TextFormat;
 public var text(get, set):String;
 public var textWrites(default, null):Int = 0;
 var storedText:String = "";
 public function new() {}
 function get_text():String return storedText;
 function set_text(value:String):String {
  textWrites++;
  storedText = value;
  return value;
 }
 public function addEventListener(_type:String, _listener:Dynamic->Void):Void {}
}
''',
            "openfl/system/System.hx": '''package openfl.system;
class System {
 public static var value:Float = 0;
 public static var reads:Int = 0;
 public static var totalMemoryNumber(get, never):Float;
 static function get_totalMemoryNumber():Float { reads++; return value; }
}
''',
            "haxe/Timer.hx": '''package haxe;
class Timer { public static function stamp():Float return 0; }
''',
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            for filename, content in files.items():
                target = work / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
