"""Owner-scoped Codename pause and game-over script hooks."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class CodenameSubStateHooksTest(unittest.TestCase):
    def test_pause_creation_event_cancellation_abi(self):
        fixture = '''
class Main {
  static function main():Void {
    var options = ["Resume", "Restart Song"];
    var event = new CodenamePauseCreationEvent(options, "breakfast");
    if (event.cancelled || event.canceled || event.music != "breakfast"
      || event.options.length != 2) throw "initial pause event";
    event.cancel();
    if (!event.cancelled || !event.canceled) throw "pause cancellation alias";
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            (Path(work) / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", work,
                 "--run", "Main"],
                cwd=ROOT, text=True, capture_output=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_substate_runtime_is_active_owner_and_scope_bound(self):
        runtime = (ROOT / "source/CodenameModSubStateRuntime.hx").read_text()
        self.assertIn("CodenameModRuntime.isActiveOwner(ownerRoot)", runtime)
        self.assertIn("CodenameScriptDiscovery.scopedResolution(ownerRoot, scriptPath)", runtime)
        self.assertIn("CodenameScriptParser.prepare(source, bindings, resolution.relative)", runtime)
        self.assertIn("call('create', [event]);", runtime)
        self.assertIn("call('postCreate', []);", runtime)
        self.assertIn("public function update(elapsed:Float):Void call('update', [elapsed]);", runtime)
        self.assertIn("call('destroy', []);", runtime)
        self.assertIn("interp.release();", runtime)
        self.assertIn("interp.flxG.stateSwitch", runtime)
        self.assertIn("interp.claimSceneObject(basic);", runtime)
        self.assertIn("hasScript(ownerRoot:String, scriptPath:String):Bool", runtime)

    def test_pause_and_gameover_hooks_preserve_native_fallback_and_cleanup(self):
        pause = (ROOT / "source/PauseSubState.hx").read_text()
        gameover = (ROOT / "source/GameOverSubstate.hx").read_text()
        self.assertIn("var path = 'data/scripts/pause.hx';", pause)
        self.assertIn("var path = 'data/scripts/jump.hx';", gameover)
        self.assertIn("CodenameModSubStateRuntime.hasScript(owner, path)", pause)
        self.assertIn("CodenameModSubStateRuntime.hasScript(owner, path)", gameover)
        self.assertIn("codenamePauseRuntime.create(event)", pause)
        self.assertIn("codenameGameOverRuntime.create(event)", gameover)
        self.assertIn("if (codenamePauseCancelled)\n\t\t\treturn;", pause)
        self.assertIn("if (codenameGameOverCancelled)\n\t\t\treturn;", gameover)
        self.assertIn("codenamePauseRuntime.destroy();", pause)
        self.assertIn("codenameGameOverRuntime.destroy();", gameover)
        self.assertIn("nativePauseBackdrop.visible = false", pause)
        self.assertIn("bf.visible = false", gameover)

    def test_pause_parent_disabler_restores_captured_work_idempotently(self):
        source = (ROOT / "source/CodenameParentDisabler.hx").read_text()
        self.assertIn("FlxTween.globalManager._tweens = []", source)
        self.assertIn("FlxTimer.globalManager._timers = []", source)
        self.assertIn("camera.active = false", source)
        self.assertIn("sound.pause();", source)
        self.assertIn("if (!restored)", source)
        self.assertIn("FlxTween.globalManager._tweens.indexOf(tween) < 0", source)
        self.assertIn("FlxTimer.globalManager._timers.indexOf(timer) < 0", source)
        self.assertIn("sound.play();", source)


if __name__ == "__main__":
    unittest.main()
