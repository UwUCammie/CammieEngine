"""Compiled Psych FlxG camera facade forwards focusOn to its native camera."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
FLIXEL_ARGS = [
    "-lib", "openfl", "-lib", "lime", "-lib", "flixel",
    "-D", "FLX_STANDARD_ASSETS_DIRECTORY", "-D", "FLX_DEFAULT_SOUND_EXT=ogg",
    "-D", "FLX_SOUND_SYSTEM", "-D", "FLX_GAMEINPUT_API",
]


class PsychCameraFocusBridgeTest(unittest.TestCase):
    def test_hscript_focus_on_moves_the_wrapped_native_camera(self):
        fixture = r'''import hscript.Interp;
import hscript.Parser;
import flixel.FlxCamera;
import flixel.FlxG;
import flixel.math.FlxPoint;
import PsychFlxCameraCompat.PsychFlxGCompat;
class PsychCameraFocusBridgeProbe {
 static function main():Void {
  var nativeCamera = new FlxCamera(0, 0, 640, 480, 1);
  FlxG.camera = nativeCamera;
  var interp = new Interp();
  interp.variables.set('FlxG', PsychFlxGCompat);
  interp.variables.set('focusPoint', new FlxPoint(100, 80));
  interp.execute(new Parser().parseString('FlxG.camera.focusOn(focusPoint);'));
  if (nativeCamera.scroll.x != -220 || nativeCamera.scroll.y != -160)
   throw 'Psych focusOn did not reach the wrapped native camera';
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "PsychCameraFocusBridgeProbe.hx").write_text(fixture, encoding="utf-8", newline='\n')
            env = dict(os.environ)
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
            env["PATH"] = os.pathsep.join(
                [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
            )
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"),
                 *FLIXEL_ARGS, "--run", "PsychCameraFocusBridgeProbe"],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("[hscript-null-access]", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
