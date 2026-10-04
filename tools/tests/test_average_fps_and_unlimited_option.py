"""Exercise the rolling FPS average and native unlimited-rate option."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class AverageFPSAndUnlimitedOptionTest(unittest.TestCase):
    def run_haxe(self, files, main="Main"):
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            for filename, content in files.items():
                target = base / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", directory, "-main", main, "--interp"],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_average_fps_uses_five_second_window_and_half_second_cadence(self):
        fake_fps = '''package openfl.display;
class FPS {
 public var currentFPS(default, null):Int = 0;
 public var text:String = "FPS: ";
 public function new(_x:Float=10, _y:Float=3, _color:Int=0xFFFFFF) {}
 @:keep private function __enterFrame(_deltaTime:Float):Void {
  // Model OpenFL updating its first line without changing the rounded value.
  currentFPS=60; text="FPS: 60";
 }
}
'''
        counter = (ROOT / "source/AverageFPSCounter.hx").read_text()
        rate = (ROOT / "source/AverageFrameRate.hx").read_text()
        self.run_haxe({
            "openfl/display/FPS.hx": fake_fps,
            "AverageFPSCounter.hx": counter,
            "AverageFrameRate.hx": rate,
            "Main.hx": '''@:access(AverageFPSCounter)
@:access(AverageFrameRate)
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var startup=new AverageFrameRate();
  for (i in 0...4)
   check(!startup.addFrameTime(100), "average refreshed before half a second");
  check(startup.currentFPS==0 && startup.sampleCount==4,
   "average should stay empty until its first scheduled refresh");
  check(startup.addFrameTime(100) && startup.currentFPS==10,
   "average did not refresh at the half-second startup boundary");
  for (i in 0...4)
   check(!startup.addFrameTime(100), "average refreshed more than once per half second");
  check(startup.addFrameTime(100) && startup.currentFPS==10,
   "average did not refresh again after another half second");

  var hitch=new AverageFrameRate();
  check(!hitch.addFrameTime(499), "average refreshed before the 500 ms boundary");
  check(hitch.addFrameTime(1), "average missed the exact 500 ms boundary");
  check(hitch.addFrameTime(600), "long hitch did not refresh the average");
  check(!hitch.addFrameTime(499),
   "average refreshed less than 500 ms after the delayed refresh");
  check(hitch.addFrameTime(1), "average missed the next full 500 ms interval");

  var hitchWindow=new AverageFrameRate();
  check(hitchWindow.addFrameTime(6000), "six-second hitch did not refresh the average");
  for (i in 0...1000)
   hitchWindow.addFrameTime(0.5);
  check(hitchWindow.sampleCount==1001 && hitchWindow.currentFPS==200,
   "long hitch time leaked into the denominator after new frames filled the window");

  var repeatedTimestamp=new AverageFrameRate();
  check(!repeatedTimestamp.addFrameTime(0) && repeatedTimestamp.sampleCount==1,
   "a frame with an unchanged clock timestamp was discarded");

  var before=startup.currentFPS;
  var beforeCount=startup.sampleCount;
  for (invalid in [-1.0, Math.NaN, Math.POSITIVE_INFINITY])
   check(!startup.addFrameTime(invalid), "invalid frame interval was accepted");
  check(startup.currentFPS==before && startup.sampleCount==beforeCount,
   "invalid frame times changed the average");

  var subMillisecond=new AverageFrameRate();
  for (i in 0...2000)
   subMillisecond.addFrameTime(0.25);
  check(subMillisecond.currentFPS==4000 && subMillisecond.sampleCount==2000,
   "average FPS lost sub-millisecond intervals at an unlimited frame rate");
  check(subMillisecond.bucketSampleCounts.length==AverageFrameRate.BUCKET_COUNT,
   "frame history storage grew with the number of rendered frames");

  var aging=new AverageFrameRate();
  for (i in 0...500)
   aging.addFrameTime(10);
  check(aging.sampleCount==500 && aging.currentFPS==100,
   "five seconds of startup samples did not produce the expected average");
  for (i in 0...255)
   aging.addFrameTime(20);
  check(aging.sampleCount==251 && aging.currentFPS==50,
   "samples older than five seconds did not age out of the average");

  var mixedRates=new AverageFrameRate();
  for (i in 0...240)
   mixedRates.addFrameTime(10);
  for (i in 0...130)
   mixedRates.addFrameTime(20);
  check(mixedRates.sampleCount==370 && mixedRates.currentFPS==74,
   "five-second average dropped older mixed-rate history as if it held only 120 frames");

  var quantizedCounter=new AverageFPSCounter();
  quantizedCounter.recordFrameAt(0);
  for (i in 0...500) {
   quantizedCounter.recordFrameAt(i);
   quantizedCounter.recordFrameAt(i + 1);
  }
  check(quantizedCounter.frameRate.sampleCount==1000 && quantizedCounter.averageFPS==2000,
   "millisecond-quantized equal timestamps capped the counter below 2000 FPS");

  var display=new AverageFPSCounter();
  display.__enterFrame(1000.0/60.0);
  check(display.currentFPS==60 && display.averageFPS==0,
   "counter did not preserve currentFPS before the first average sample");
  check(display.text=="FPS: 60\\nAvg FPS: 0",
   "base FPS text update removed or omitted the average line");
  // Use an explicit sub-millisecond timestamp rather than sleeping the eval
  // worker: Windows eval's sleep can stall under concurrent regression runs.
  display.recordFrameAt(display.lastFrameTimeMS + 0.25);
  check(display.currentFPS==60 && display.averageFPS==0 && display.frameRate.sampleCount==1,
   "counter did not retain high-resolution intervals while respecting the refresh cadence");
  display.__enterFrame(1000.0/60.0);
  check(display.text.indexOf("Avg FPS: 0") >= 0,
   "base FPS text update removed the average line before its first refresh");
 }
}'''
        })

    def test_finite_and_unlimited_modes_use_real_elapsed_time(self):
        helper = (ROOT / "source/FramerateOptionsCompat.hx").read_text()
        self.run_haxe({
            "flixel/FlxGame.hx": '''package flixel;
class FlxGame { var _maxAccumulation:Float=1; public function new() {} }
''',
            "flixel/FlxG.hx": '''package flixel;
class FlxG {
 public static var game:FlxGame;
 public static var fixedTimestep:Bool=true;
 public static var updateFramerate:Int=60;
 public static var drawFramerate:Int=60;
}
''',
            "OptionsHandler.hx": '''class OptionsHandler {
 public static inline var MAX_FPS_CAP:Int=2147483647;
 public static function sanitizeFpsCap(value:Dynamic):Int {
  if (value==null || !(Std.isOfType(value, Int) || Std.isOfType(value, Float))) return 60;
  var fps:Float=value;
  if (!Math.isFinite(fps) || fps<=0) return 60;
  return Std.int(Math.floor(Math.min(MAX_FPS_CAP, fps)+0.5));
 }
}
''',
            "FramerateOptionsCompat.hx": helper,
            "Main.hx": '''import flixel.FlxG;
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  FlxG.game=new flixel.FlxGame();
  check(FlxG.fixedTimestep, "fixture must model a fresh Flixel game");
  FramerateOptionsCompat.apply({fpsCap:1501, unlimitedFPS:false});
  check(!FlxG.fixedTimestep && FlxG.updateFramerate==1501 && FlxG.drawFramerate==1501,
   "a high finite cap must preserve elapsed time without replacing the selected cap");
  FramerateOptionsCompat.apply({fpsCap:120, unlimitedFPS:true});
  check(!FlxG.fixedTimestep && FlxG.updateFramerate==60 && FlxG.drawFramerate==0,
   "unlimited mode must update per frame and use the native uncap value");
  var accumulated:Float=Reflect.field(FlxG.game, "_maxAccumulation");
  check(Math.isFinite(accumulated) && accumulated>0,
   "uncapping the stage must leave Flixel's fixed-step backlog finite");
  FlxG.fixedTimestep=true;
  FramerateOptionsCompat.apply({fpsCap:144, unlimitedFPS:false});
  check(FlxG.updateFramerate==144 && FlxG.drawFramerate==144 && !FlxG.fixedTimestep,
   "finite cap did not restore its selected rates and variable elapsed-time mode");
 }
}'''
        })

    def test_unlimited_toggle_is_available_in_both_options_menus(self):
        savedata = (ROOT / "source/SaveDataState.hx").read_text()
        model = (ROOT / "source/CodenameOptionsMenuModel.hx").read_text()
        options = (ROOT / "source/OptionsHandler.hx").read_text()
        main = (ROOT / "source/Main.hx").read_text()
        self.assertIn('intName: "unlimitedFPS"', savedata)
        self.assertIn("{label:'Unlimited FPS', field:'unlimitedFPS', kind:'toggle'}", model)
        self.assertIn('sanitizeBool(Reflect.field(opt, "unlimitedFPS"), false)', options)
        self.assertIn("new AverageFPSCounter(10, 3, 0xFFFFFF)", main)
        self.assertIn("FramerateOptionsCompat.apply(initialOptions)", main)
        average = (ROOT / "source/AverageFPSCounter.hx").read_text()
        self.assertIn('Avg FPS: ', average)
        self.assertIn('Timer.stamp()', average)
        self.assertIn('UNLIMITED_UPDATE_FRAMERATE:Int = 60',
                      (ROOT / "source/FramerateOptionsCompat.hx").read_text())


if __name__ == "__main__":
    unittest.main()
