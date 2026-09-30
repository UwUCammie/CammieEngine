"""Imported Psych stage GameOverSubstate writes reach native per-song settings."""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PsychGameOverClassCompatTest(unittest.TestCase):
    def test_compiled_stage_binds_the_per_song_class_surface(self):
        source = (ROOT / "source/PsychCompiledStageBindings.hx").read_text(encoding="utf-8")
        self.assertIn("new PsychGameOverClassCompat(PlayState.instance, PlayState.SONG)", source)
        self.assertIn("bind(bindings, 'substates.GameOverSubstate', gameOverClass);", source)

    def test_source_death_delay_routes_to_native_transition(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        self.assertIn("'endsoundname', 'deathdelay'", source)
        self.assertIn("psychGameOverDeathDelaySeconds = delay;", source)
        self.assertIn("public function psychGameOverDeathDelay():Float", source)
        self.assertIn("new FlxTimer().start(deathDelay", source)
        self.assertIn("function runPsychGameOverTransition():Void", source)
        self.assertIn("if (psychGameOverTransitionPending)", source)

    def test_source_style_static_writes_route_to_native_bridge(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder)
            (path / "PsychGameOverClassProbe.hx").write_text(r'''import hscript.Parser;
import hscript.Interp;
class PsychGameOverHost {
 public var calls:Array<String> = [];
 public function new() {}
 public function setPsychClassProperty(className:String, field:String, value:Dynamic):Void
  calls.push(className + ":" + field + ":" + Std.string(value));
}
class PsychGameOverClassProbe {
 static function check(ok:Bool, label:String):Void if (!ok) throw label;
 static function main():Void {
  var host = new PsychGameOverHost();
  var sourceClass = new PsychGameOverClassCompat(host, {gameOverChar:"pico-dead"});
  check(sourceClass.characterName == "pico-dead", "chart character default");
  check(host.calls.length == 0, "construction must not overwrite prior stage state");
  var interp = new Interp();
  interp.variables.set("GameOverSubstate", sourceClass);
  interp.execute(new Parser().parseString("GameOverSubstate.deathSoundName = 'custom-loss'; GameOverSubstate.characterName = 'custom-death';"));
  check(host.calls[0] == "GameOverSubstate:deathSoundName:custom-loss", "death sound did not reach native bridge");
  check(host.calls[1] == "GameOverSubstate:characterName:custom-death", "death actor did not reach native bridge");
  check(sourceClass.deathSoundName == "custom-loss" && sourceClass.characterName == "custom-death", "source readback");
  interp.execute(new Parser().parseString("GameOverSubstate.deathDelay = 0.15;"));
  check(host.calls[2] == "GameOverSubstate:deathDelay:0.15", "death delay did not reach native bridge");
  check(sourceClass.deathDelay == 0.15, "death delay source readback");
  sourceClass.resetVariables();
  check(sourceClass.characterName == "pico-dead" && sourceClass.deathSoundName == "fnf_loss_sfx", "source defaults");
  check(sourceClass.deathDelay == 0, "death delay did not reset");
  check(host.calls[host.calls.length - 1] == "GameOverSubstate:deathDelay:0", "reset did not clear native delay");
  var invalid = false;
  try sourceClass.deathDelay = -0.15 catch (error:Dynamic)
   invalid = Std.string(error).indexOf("finite nonnegative number") >= 0;
  check(invalid, "negative death delay was accepted");
 }
}''', encoding="utf-8")
            env = dict(os.environ)
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", str(path), "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "--run", "PsychGameOverClassProbe"],
                cwd=ROOT, env=env, text=True, capture_output=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
