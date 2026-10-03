"""Psych compiled stages get donor FlxAnimate cursor fields on the native adapter."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
FLIXEL_ARGS = [
    "-lib", "openfl", "-lib", "lime", "-lib", "flixel", "-lib", "flixel-animate",
    "-D", "FLX_STANDARD_ASSETS_DIRECTORY", "-D", "FLX_DEFAULT_SOUND_EXT=ogg",
    "-D", "FLX_SOUND_SYSTEM", "-D", "FLX_GAMEINPUT_API",
]


def haxe_env():
    env = dict(os.environ)
    env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
    env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
    env["PATH"] = os.pathsep.join(
        [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
    )
    return env


class PsychFlxAnimateCompatTest(unittest.TestCase):
    def test_stage_bindings_use_the_adapter_for_all_flxanimate_names(self):
        source = (ROOT / "source/PsychCompiledStageBindings.hx").read_text(encoding="utf-8")
        self.assertIn("bind(bindings, 'FlxAnimate', PsychFlxAnimateCompat);", source)
        self.assertIn("bind(bindings, 'animate.FlxAnimate', PsychFlxAnimateCompat);", source)
        self.assertIn("bind(bindings, 'flxanimate.PsychFlxAnimate', PsychFlxAnimateCompat);", source)

    def test_psych_lua_animate_apis_are_bound_to_the_tagged_owner_bridge(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        for name, helper in [
            ("addAnimationBySymbolIndices", "compatAddAnimationBySymbolIndices"),
            ("playAnim", "compatPlayAnim"),
        ]:
            self.assertIn(f"interp.variables.set('{name}', {helper});", source)
        self.assertIn("compatMakeFlxAnimateSprite(psychScriptOwner, tag, x, y, loadFolder)", source)
        self.assertIn("compatLoadAnimateAtlas(psychScriptOwner, tag, folderOrImage", source)
        self.assertIn("function compatMakeFlxAnimateSprite(ownerRoot:Null<String>", source)
        self.assertIn("function compatLoadAnimateAtlas(ownerRoot:Null<String>", source)
        self.assertIn("var paths = PsychOwnerPaths.create(ownerRoot);", source)
        self.assertIn("sprite.anim.addBySymbolIndices(name, symbol, animationIndices, framerate, looped);", source)
        self.assertIn("(cast object : PsychModchartAnimateSprite).playAnim", source)

    def test_psych_modchart_animate_sprite_play_surface(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            base = Path(folder)
            (base / "PsychModchartAnimateProbe.hx").write_text(
                r'''import openfl.display.BitmapData;
class PsychModchartAnimateProbe {
 static function check(ok:Bool, label:String):Void if (!ok) throw label;
 static function main():Void {
  var sprite = new PsychModchartAnimateSprite();
  sprite.loadGraphic(new BitmapData(3, 1, false, 0xFFFFFFFF), true, 1, 1);
  sprite.anim.add("probe", [0, 1, 2], 24, false);
  sprite.addOffset("probe", 7, 9);
  sprite.playAnim("probe", true, false, 1);
  check(sprite.anim.curAnim != null && sprite.anim.curAnim.name == "probe", "tag animation played");
  check(sprite.anim.curAnim.curFrame == 1, "optional start frame reached the FlxAnimate controller");
  check(sprite.offset.x == 7 && sprite.offset.y == 9, "Psych per-animation offsets applied");
  sprite.destroy();
 }
}''',
                encoding="utf-8",
             newline='\n')
            command = [
                *HAXE_COMMAND,
                "-cp", str(ROOT / "source"),
                "-cp", str(base),
                *FLIXEL_ARGS,
                "--run", "PsychModchartAnimateProbe",
            ]
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=haxe_env(),
                text=True,
                capture_output=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_psych_animate_adapter_preserves_authoring_space_by_default(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            base = Path(folder)
            (base / "PsychFlxAnimateOriginProbe.hx").write_text(
                r'''class PsychFlxAnimateOriginProbe {
 static function check(ok:Bool, label:String):Void if (!ok) throw label;
 static function main():Void {
  var sprite = new PsychFlxAnimateCompat(1340, 370);
  check(sprite.applyStageMatrix, "Psych Animate preserves authored atlas origin by default");
  sprite.applyStageMatrix = false;
  check(!sprite.applyStageMatrix, "script can explicitly opt out of authored atlas origin");
  sprite.destroy();
 }
}''',
                encoding="utf-8",
             newline='\n')
            command = [
                *HAXE_COMMAND,
                "-cp", str(ROOT / "source"),
                "-cp", str(base),
                *FLIXEL_ARGS,
                "--run", "PsychFlxAnimateOriginProbe",
            ]
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=haxe_env(),
                text=True,
                capture_output=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_native_controller_exposes_psych_cursor_and_length_aliases(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            base = Path(folder)
            (base / "PsychFlxAnimateProbe.hx").write_text(
                r'''import openfl.display.BitmapData;
class PsychFlxAnimateProbe {
 static function check(ok:Bool, label:String):Void if (!ok) throw label;
 static function main():Void {
  var sprite = new PsychFlxAnimateCompat();
  sprite.loadGraphic(new BitmapData(3, 1, false, 0xFFFFFFFF), true, 1, 1);
  sprite.anim.add("probe", [2, 0, 1], 24, false);
  sprite.anim.play("probe", true, false, 1);
  var controller:Dynamic = sprite.anim;
  check(Reflect.getProperty(controller, "length") == 3, "Psych animation length alias");
  check(Reflect.getProperty(controller, "curFrame") == 1, "Psych current frame alias");
  check(sprite.animation.frameIndex == 0, "fixture starts on mapped atlas frame");
  Reflect.setProperty(controller, "curFrame", Reflect.getProperty(controller, "length") - 1);
  check(Reflect.getProperty(controller, "curFrame") == 2, "Psych current frame write");
  check(sprite.animation.frameIndex == 1, "write uses clip's mapped atlas frame");
  sprite.destroy();
 }
}''',
                encoding="utf-8",
             newline='\n')
            command = [
                *HAXE_COMMAND,
                "-cp", str(ROOT / "source"),
                "-cp", str(base),
                *FLIXEL_ARGS,
                "--run", "PsychFlxAnimateProbe",
            ]
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=haxe_env(),
                text=True,
                capture_output=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_native_controller_bridges_psych_completion_signal_arity_and_membership(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            base = Path(folder)
            (base / "PsychFlxAnimateCompletionProbe.hx").write_text(
                r'''import openfl.display.BitmapData;
class PsychFlxAnimateCompletionProbe {
 static function check(ok:Bool, label:String):Void if (!ok) throw label;
 static function main():Void {
  var sprite = new PsychFlxAnimateCompat();
  sprite.loadGraphic(new BitmapData(3, 1, false, 0xFFFFFFFF), true, 1, 1);
  sprite.anim.add("probe", [0, 1, 2], 24, false);
  sprite.anim.play("probe", true);
  var controller:Dynamic = sprite.anim;
  var onComplete:Dynamic = Reflect.getProperty(controller, "onComplete");
  var completed = 0;
  var finishCanAnimation = function():Void completed++;
  onComplete.add(finishCanAnimation);
  onComplete.add(finishCanAnimation);
  check(onComplete.has(finishCanAnimation), "Psych onComplete.has after add");
  controller.update(1.0);
  check(completed == 1, "Psych no-argument onComplete callback");
  onComplete.remove(finishCanAnimation);
  check(!onComplete.has(finishCanAnimation), "Psych onComplete.remove");

  var stressCalls = 0;
  var picoStressCycle = function():Void stressCalls++;
  onComplete.add(picoStressCycle);
  check(onComplete.has(picoStressCycle), "Tank onComplete.has before removal");
  onComplete.remove(picoStressCycle);
  check(!onComplete.has(picoStressCycle), "Tank onComplete.has after removal");
  sprite.anim.play("probe", true);
  controller.update(1.0);
  check(stressCalls == 0, "removed Psych completion listener is not called");
  sprite.destroy();
 }
}''',
                encoding="utf-8",
             newline='\n')
            command = [
                *HAXE_COMMAND,
                "-cp", str(ROOT / "source"),
                "-cp", str(base),
                *FLIXEL_ARGS,
                "--run", "PsychFlxAnimateCompletionProbe",
            ]
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=haxe_env(),
                text=True,
                capture_output=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
