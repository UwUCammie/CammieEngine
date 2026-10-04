"""The ordinary-title profiling path is explicit, silent and bounded."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class RuntimeStartupProbeTest(unittest.TestCase):
    def test_disabled_probe_does_no_work_and_enabled_probe_exits_after_intro_draw(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            (work / "RuntimeStartupProbe.hx").write_text(
                (ROOT / "source/RuntimeStartupProbe.hx").read_text(), newline="\n")
            (work / "flixel").mkdir()
            (work / "flixel/FlxG.hx").write_text('''package flixel;
class Signal {
 public var listeners:Array<Void->Void> = [];
 public function new() {}
 public function add(callback:Void->Void):Void listeners.push(callback);
}
class FlxG {
 public static var autoPause:Bool = true;
 public static var sound = {muted:false};
 public static var signals = {preUpdate:new Signal(), postDraw:new Signal()};
}
''', newline="\n")
            (work / "Main.hx").write_text('''@:access(RuntimeStartupProbe)
class Main {
 static function check(ok:Bool, text:String):Void if (!ok) throw text;
 static function main():Void {
  RuntimeStartupProbe.begin();
  RuntimeStartupProbe.mark("disabled");
  RuntimeStartupProbe.mute();
  RuntimeStartupProbe.install();
  check(!flixel.FlxG.sound.muted && flixel.FlxG.autoPause,
   "ordinary launches changed audio or focus behavior");
  check(flixel.FlxG.signals.postDraw.listeners.length == 0,
   "ordinary launch installed a profiling callback");
  RuntimeStartupProbe.requested = true;
  RuntimeStartupProbe.logPath = Sys.args()[0];
  RuntimeStartupProbe.startedAt = RuntimeStartupProbe.previousAt = haxe.Timer.stamp();
  RuntimeStartupProbe.mark("enabled");
  RuntimeStartupProbe.install();
  check(flixel.FlxG.sound.muted && !flixel.FlxG.autoPause,
   "startup profile was audible or paused");
  check(flixel.FlxG.signals.postDraw.listeners.length == 1,
   "startup profile did not install one draw observer");
  RuntimeStartupProbe.afterDraw();
  check(!RuntimeStartupProbe.finished, "profile ended before title assets loaded");
  RuntimeStartupProbe.titleIntroReady();
  RuntimeStartupProbe.afterDraw();
  throw "profile did not exit after the complete title draw";
 }
}
''', newline="\n")
            log = work / "startup.log"
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(work), "--run", "Main", str(log)],
                                    cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            text = log.read_text()
            self.assertNotIn('"phase":"disabled"', text)
            self.assertEqual(text.count('"phase":"first_draw"'), 1)
            self.assertEqual(text.count('"phase":"startup_complete"'), 1)


if __name__ == "__main__":
    unittest.main()
