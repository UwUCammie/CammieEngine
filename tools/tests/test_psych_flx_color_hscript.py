"""Pin HScript access to FlxColor's Int-backed abstract properties."""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
FLIXEL_ARGS = [
    "-lib", "openfl", "-lib", "lime", "-lib", "flixel", "-lib", "flixel-addons",
    "-lib", "flixel-animate", "-D", "FLX_STANDARD_ASSETS_DIRECTORY",
    "-D", "FLX_DEFAULT_SOUND_EXT=ogg", "-D", "FLX_SOUND_SYSTEM", "-D", "FLX_GAMEINPUT_API",
]


def haxe_env():
    env = dict(os.environ)
    env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
    env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
    env["PATH"] = os.pathsep.join(
        [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
    )
    return env


class PsychFlxColorHscriptTest(unittest.TestCase):
    def test_int_backed_color_get_direct_write_and_compound_write(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            probe = base / "PsychFlxColorHscriptProbe.hx"
            probe.write_text(
                r'''import flixel.util.FlxColor;
import hscript.InterpEx;
import hscript.ParserEx;

class PsychFlxColorHscriptProbe {
 static function check(ok:Bool, message:String):Void {
  if (!ok) throw message;
 }
 static function main():Void {
  var seed:FlxColor=FlxColor.fromRGB(238,126,82,210);
  var expected=seed;
  expected.alphaFloat=0.25;
  expected.saturation*=0.5;
  expected.brightness*=0.5;

  var interp=new InterpEx();
  interp.variables.set('color',seed);
  var parser=new ParserEx();
  var updated=interp.execute(parser.parseString(
   'color.alphaFloat = 0.25; color.saturation *= 0.5; color.brightness *= 0.5; color'
  ));
  check(updated==expected,'HScript writes did not preserve FlxColor setter semantics');
  check(interp.variables.get('color')==expected,'updated color was not written back to its variable');
  check(seed==FlxColor.fromRGB(238,126,82,210),'color writeback mutated the original value');

  var alpha:Float=cast interp.execute(parser.parseString('color.alphaFloat'));
  var saturation:Float=cast interp.execute(parser.parseString('color.saturation'));
  check(Math.abs(alpha-0.25)<0.005,'HScript alphaFloat getter returned the wrong channel');
  check(Math.abs(saturation-expected.saturation)<0.005,'HScript saturation getter returned the wrong channel');

  interp.variables.set('seedColor',seed);
  var localUpdated=interp.execute(parser.parseString(
   'var colorButLower = seedColor; colorButLower.alphaFloat = 0.25; '
   +'colorButLower.saturation *= 0.5; colorButLower.brightness *= 0.5; colorButLower'
  ));
  check(localUpdated==expected,'local color alias did not receive setter writeback');

  var ordinary=interp.execute(parser.parseString(
   'var item = {alphaFloat: 0.75}; item.alphaFloat = 0.5; item.alphaFloat'
  ));
  check(ordinary==0.5,'ordinary reflected object property behavior changed');
 }
}''',
                encoding="utf-8",
            )
            command = [
                str(ROOT / ".tools/haxe/haxe"),
                "-cp", str(base),
                "-cp", str(ROOT / "source"),
                "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"),
                *FLIXEL_ARGS,
                "--run", "PsychFlxColorHscriptProbe",
            ]
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=haxe_env(),
                capture_output=True,
                text=True,
                timeout=90,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
