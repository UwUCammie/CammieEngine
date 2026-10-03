"""Narrow Iris fixture for source globals, String calls, and missing-call diagnostics."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

from tools.haxe_flixel_math_stubs import write_flixel_point_stub


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"
IRIS = ROOT / ".haxelib" / "hscript-iris" / "1,1,3"


class NightmareVisionStringCallTest(unittest.TestCase):
    def test_source_string_globals_shadow_parent_and_keep_string_calls(self):
        if not HAXE.is_file() or not (IRIS / "crowplexus/hscript/Parser.hx").is_file():
            self.skipTest("portable Haxe or pinned hscript-iris 1.1.3 is unavailable")

        fixture = r'''import crowplexus.iris.Iris;

class SongFixture {
 public var song:String;
 public var bpm:Float;
 public var speed:Float;
 public function new(song:String, bpm:Float, speed:Float) {
  this.song = song; this.bpm = bpm; this.speed = speed;
 }
}
class PlayStateFixture {
 public static var SONG:SongFixture;
}
class FlxText { public function new() {} }
class ParentState {
 public var songName:FlxText;
 public function new() { this.songName = new FlxText(); }
}
class NotAString { public function new() {} }

class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  PlayStateFixture.SONG = new SongFixture("Try Harder", 128, 1.25);
  var interp = new NightmareVisionScriptInterp(new ParentState());
  interp.variables.set("PlayState", PlayStateFixture);
  // Match the source FunkinScript preset: chart values are script globals,
  // even though the native PlayState parent has a FlxText named songName.
  interp.variables.set("bpm", PlayStateFixture.SONG.bpm);
  interp.variables.set("scrollSpeed", PlayStateFixture.SONG.speed);
  interp.variables.set("songName", PlayStateFixture.SONG.song);
  var parser = new NightmareVisionScriptParser();
  interp.execute(parser.parseString(
   "literalLower = 'MiXeD'.toLowerCase();\n"
   + "staticSongLower = PlayState.SONG.song.toLowerCase();\n"
   + "globalSongNameLower = songName.toLowerCase();\n"
   + "globalBpm = bpm;\n"
   + "globalScrollSpeed = scrollSpeed;\n"
   + "function lowerEventValue(value1) return value1.toLowerCase();\n"
   + "function lowerSongName() return songName.toLowerCase();\n"
   + "function lowerInvalidReceiver(value) return value.toLowerCase();\n",
   "nmv-string-call-fixture"));

  check(interp.variables.get("literalLower") == "mixed",
   "Iris did not call toLowerCase on a string literal");
  check(interp.variables.get("staticSongLower") == "try harder",
   "Iris did not reflect PlayState.SONG.song as a String");
  check(interp.variables.get("globalSongNameLower") == "try harder",
   "source songName String did not shadow the parent's FlxText field");
  check(interp.variables.get("globalBpm") == 128
   && interp.variables.get("globalScrollSpeed") == 1.25,
   "source chart timing globals did not preserve active SONG fields");
  check(interp.callCallback(interp.variables.get("lowerSongName"), []) == "try harder",
   "callback did not retain the source songName String binding");
  var eventResult = interp.callCallback(interp.variables.get("lowerEventValue"), ["MiXeD"]);
  check(eventResult == "mixed", "callback String argument lost its native String method");

  var previousError = Iris.error;
  var captured:Array<String> = [];
  Iris.error = function(message:Dynamic, ?pos:haxe.PosInfos):Void captured.push(Std.string(message));
  interp.variables.remove("songName");
  var parentResult:Dynamic = null;
  try parentResult = interp.callCallback(interp.variables.get("lowerSongName"), [])
  catch (error:Dynamic) {
   Iris.error = previousError;
   throw error;
  }
  var invalidResult:Dynamic = null;
  try invalidResult = interp.callCallback(interp.variables.get("lowerInvalidReceiver"), [new NotAString()])
  catch (error:Dynamic) {
   Iris.error = previousError;
   throw error;
  }
  Iris.error = previousError;
  check(parentResult == null && invalidResult == null && captured.length == 2
   && captured[0].indexOf("Unknown function: toLowerCase") >= 0
   && captured[0].indexOf("FlxText") >= 0
   && captured[0].indexOf("isString=false") >= 0
   && captured[0].indexOf("value=<non-string>") >= 0
   && captured[1].indexOf("Unknown function: toLowerCase") >= 0
   && captured[1].indexOf("receiverType=") >= 0
   && captured[1].indexOf("isString=false") >= 0
   && captured[1].indexOf("value=<non-string>") >= 0,
   "parent FlxText collision or non-string call lost its receiver evidence: "
   + captured.join(" | ") + " parentResult=" + Std.string(parentResult)
   + " invalidResult=" + Std.string(invalidResult));
  interp.release();
}
}'''

        runtime_stub = '''class HxcCompatRuntime {
 public static function getZIndex(target:Dynamic):Dynamic return 0;
 public static function setZIndex(target:Dynamic, value:Dynamic, ?op:String='='):Dynamic return value;
}'''

        with tempfile.TemporaryDirectory(prefix="nmv-string-call-", dir=ROOT / "tmp") as scratch:
            play_state = (ROOT / "source/PlayState.hx").read_text()
            for source_binding in ("'bpm' => SONG.bpm", "'scrollSpeed' => SONG.speed",
                "'songName' => SONG.song"):
                self.assertIn(source_binding, play_state,
                    f"NMV host must seed source chart global {source_binding} before parent lookup")
            work = Path(scratch)
            write_flixel_point_stub(work)
            (work / "Main.hx").write_text(fixture, newline='\n')
            (work / "HxcCompatRuntime.hx").write_text(runtime_stub, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(IRIS),
                 "-cp", str(work), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
