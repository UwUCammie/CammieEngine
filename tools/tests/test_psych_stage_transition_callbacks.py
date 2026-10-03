"""Psych source stage start/end hooks retain native transition semantics."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"Unclosed source method: {marker}")


class PsychStageTransitionCallbacksTest(unittest.TestCase):
    def test_source_callbacks_register_once_and_recover_from_errors(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        methods = "\n".join(method(source, marker) for marker in (
            "@:keep public function setStartCallback(",
            "@:keep public function setEndCallback(",
            "function runPsychStageStartCallback(",
            "function runPsychStageEndCallback(",
        ))
        self.assertIn("if (psychCompiledStageCreated && runPsychStageStartCallback())", source)
        self.assertIn("if (runPsychStageEndCallback()) return;", source)
        self.assertIn("PsychOwnerPaths.create(ownerRoot, psychStageLibrary)", source)
        self.assertIn("videoCutscene = clip;", source)
        self.assertIn("var callback = clip.skipRequested ? clip.onSkip : clip.finishCallback;", source)
        self.assertIn("skipHoldSeconds: 1", source)
        self.assertIn("PsychControlsCompat.instance.pressed('accept')", source)
        self.assertIn("public var cameraSpeed(get, set):Float", source)
        self.assertIn("function set_cameraSpeed(value:Float):Float return camSpeed = value;", source)
        self.assertIn("public function moveCameraSection(?sec:Null<Int>):Void", source)
        self.assertIn("psychCameraCompatibilityActive && isCameraOnForcedPos", source)
        self.assertIn("if (psychCompiledStageRuntime != null && psychCompiledStageRuntime.active)\n\t\t\twatchedCutscene = true;", source)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(
                """class RuntimeSmokeHarness { public static function enabled():Bool return false; }
@:access(StageHost)
class Main {
 static function check(ok:Bool,label:String):Void if(!ok) throw label;
 static function main():Void {
  var host=new StageHost();
  var starts=0;
  host.setStartCallback(function() starts++);
  check(host.runPsychStageStartCallback() && starts==1,'authored intro runs');
  check(!host.runPsychStageStartCallback() && starts==1,'intro repeats');
  var ends=0;
  host.setEndCallback(function() ends++);
  check(host.runPsychStageEndCallback() && ends==1 && host.psychStageCutsceneEnding,
   'authored ending runs with video handoff');
  check(!host.runPsychStageEndCallback() && ends==1,'ending repeats');
  host.endForReal();
  check(!host.psychStageCutsceneEnding,'ending mode survives next song');
  host.setStartCallback(function() throw 'intro failure');
  check(host.runPsychStageStartCallback() && host.countdowns==1,'intro failure recovery');
  host.setEndCallback(function() throw 'outro failure');
  check(host.runPsychStageEndCallback() && host.endings==2,'outro failure recovery');
 }
}
class StageHost {
 var psychStageStartCallback:Dynamic=null;
 var psychStageEndCallback:Dynamic=null;
 public var psychStageCutsceneEnding:Bool=false;
 public var countdowns:Int=0;
 public var endings:Int=0;
 public function new() {}
 public function startCountdown():Void countdowns++;
 public function endForReal():Void { endings++;psychStageCutsceneEnding=false; }
""" + methods + "\n}\n", encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
