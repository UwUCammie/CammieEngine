"""Executable lifecycle tests for the Flixel-free HXC death-quote controller."""
from haxe_test_support import HAXE_COMMAND

import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class HxcDeathQuotePlaybackTest(unittest.TestCase):
    def test_audio_sequence_completion_and_cancellation(self):
        if not HAXE.exists():
            self.skipTest("portable Haxe interpreter is not installed")

        main = r'''import HxcDeathQuotePlayback.HxcDeathQuotePlaybackActions;

class Probe {
  public var events:Array<String> = [];
  public var completion:Void->Void;
  public var canFade:Bool = true;
  public var stopped:Int = 0;

  public function new() {}

  public function actions():HxcDeathQuotePlaybackActions {
    return {
      startLoopMusic: function(volume:Float) events.push("music:" + volume),
      playDeathLoop: function() events.push("deathLoop"),
      playQuote: function(path:String, done:Void->Void):Dynamic {
        events.push("quote:" + path);
        completion = done;
        return "quote-handle";
      },
      canFadeLoopMusic: function() {
        events.push("canFade:" + canFade);
        return canFade;
      },
      fadeLoopMusic: function(duration:Float, from:Float, to:Float)
        events.push("fade:" + duration + ":" + from + ":" + to),
      stopQuote: function(handle:Dynamic) {
        if (handle != "quote-handle") throw "wrong quote handle: " + handle;
        stopped++;
        events.push("stopQuote");
      }
    };
  }
}

class ImmediateProbe extends Probe {
  override public function actions():HxcDeathQuotePlaybackActions {
    return {
      startLoopMusic: function(volume:Float) events.push("music:" + volume),
      playDeathLoop: function() events.push("deathLoop"),
      playQuote: function(path:String, done:Void->Void):Dynamic {
        events.push("quote:" + path);
        done();
        return "quote-handle";
      },
      canFadeLoopMusic: function() { events.push("canFade:" + canFade); return canFade; },
      fadeLoopMusic: function(duration:Float, from:Float, to:Float)
        events.push("fade:" + duration + ":" + from + ":" + to),
      stopQuote: function(handle:Dynamic) { stopped++; events.push("stopQuote"); }
    };
  }
}

class Main {
  static function check(value:Bool, message:String):Void {
    if (!value) throw message;
  }

  static function main() {
    var missing = new Probe();
    var missingPlayback = new HxcDeathQuotePlayback(missing.actions());
    check(!missingPlayback.start(true, null), "null quote took over native behavior");
    check(missing.events.length == 0 && !missingPlayback.hasStarted,
      "null quote invoked actions or latched playback");

    var early = new Probe();
    var playback = new HxcDeathQuotePlayback(early.actions());
    check(!playback.start(false, "death/line"), "quote started before firstDeath finished");
    check(early.events.length == 0 && !playback.hasStarted, "early check changed playback state");
    check(playback.start(true, "death/line"), "finished death did not start quote");
    check(early.events.join(",") == "music:0.2,deathLoop,quote:death/line",
      "wrong start order/volume: " + early.events.join(","));
    check(playback.hasStarted, "start state not recorded");
    check(!playback.start(true, "death/second"), "quote started more than once");
    check(early.events.length == 3, "duplicate start ran audio actions");

    var done = early.completion;
    done();
    done();
    check(playback.hasCompleted, "completion state not recorded");
    check(early.events.join(",") == "music:0.2,deathLoop,quote:death/line,canFade:true,fade:4:0.2:1",
      "completion fade differed from V-Slice contract: " + early.events.join(","));
    playback.cancel();
    check(early.stopped == 0, "completed quote was stopped again");

    var ending = new Probe();
    ending.canFade = false;
    var endingPlayback = new HxcDeathQuotePlayback(ending.actions());
    check(endingPlayback.start(true, "death/line"), "no-ending quote failed to start");
    ending.completion();
    check(ending.events.join(",") == "music:0.2,deathLoop,quote:death/line,canFade:false",
      "fade ran after the music/ending guard failed: " + ending.events.join(","));

    var cancelled = new Probe();
    var cancelledPlayback = new HxcDeathQuotePlayback(cancelled.actions());
    check(cancelledPlayback.start(true, "death/line"), "cancel fixture did not start");
    var staleCompletion = cancelled.completion;
    cancelledPlayback.cancel();
    cancelledPlayback.cancel();
    staleCompletion();
    check(!cancelledPlayback.isActive && cancelled.stopped == 1,
      "cancel did not stop the quote exactly once");
    check(cancelled.events.join(",") == "music:0.2,deathLoop,quote:death/line,stopQuote",
      "stale completion ran after cancellation: " + cancelled.events.join(","));

    var destroyed = new Probe();
    var destroyedPlayback = new HxcDeathQuotePlayback(destroyed.actions());
    check(destroyedPlayback.start(true, "death/line"), "destroy fixture did not start");
    var destroyedCompletion = destroyed.completion;
    destroyedPlayback.destroy();
    destroyedCompletion();
    check(!destroyedPlayback.isActive && destroyed.stopped == 1,
      "destroy did not stop and invalidate the quote");

    var immediate = new ImmediateProbe();
    var immediatePlayback = new HxcDeathQuotePlayback(immediate.actions());
    check(immediatePlayback.start(true, "death/line"), "synchronous completion fixture failed");
    check(immediate.events.join(",") == "music:0.2,deathLoop,quote:death/line,canFade:true,fade:4:0.2:1",
      "synchronous completion retained a stale quote handle");
    immediatePlayback.destroy();
    check(immediate.stopped == 0, "completed synchronous quote was stopped on destroy");

    Sys.println("hxc-death-quote-playback-ok");
  }
}'''

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            (temp / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(temp), "-main", "Main", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("hxc-death-quote-playback-ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
