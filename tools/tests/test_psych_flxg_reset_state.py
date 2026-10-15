"""Psych FlxG.resetState() during a song takes the song retry path.

Psych scripts see FlxG through PsychFlxGCompat, whose unknown fields fall back
to Flixel. FlxG.resetState() therefore reset the state directly and skipped
PlayState's retry path (no song retry callbacks, held assets dropped).
"""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
FLIXEL_ARGS = [
    "-lib", "openfl", "-lib", "lime", "-lib", "flixel",
    "-D", "FLX_STANDARD_ASSETS_DIRECTORY", "-D", "FLX_DEFAULT_SOUND_EXT=ogg",
    "-D", "FLX_SOUND_SYSTEM", "-D", "FLX_GAMEINPUT_API",
]

PLAYSTATE_STUB = '''class PlayState {
 public static var resets:Int = 0;
 @:keep public static function resetCurrentState():Void resets++;
}
'''


class PsychFlxGResetStateTest(unittest.TestCase):
    def test_script_reset_state_goes_through_play_state(self):
        fixture = r'''import hscript.Interp;
import hscript.Parser;
import PsychFlxCameraCompat.PsychFlxGCompat;
class PsychResetStateProbe {
 static function main():Void {
  PlayState.resets = 0;
  var interp = new Interp();
  interp.variables.set('FlxG', PsychFlxGCompat);
  interp.execute(new Parser().parseString('FlxG.resetState();'));
  if (PlayState.resets != 1) throw 'Psych FlxG.resetState skipped the song retry path';
  Sys.println('reset-ok');
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "PsychResetStateProbe.hx").write_text(fixture, encoding="utf-8", newline='\n')
            Path(folder, "PlayState.hx").write_text(PLAYSTATE_STUB, encoding="utf-8", newline='\n')
            env = dict(os.environ)
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
            env["PATH"] = os.pathsep.join(
                [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
            )
            # Later class paths win, so the stub PlayState in the fixture folder
            # replaces the real one.
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), "-cp", folder,
                 *FLIXEL_ARGS, "--run", "PsychResetStateProbe"],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('reset-ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
