"""Global V-Slice modules may construct the base-game colour shaders by name."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''class Main {
 static function main() {
  for (shader in ['AdjustColorShader', 'DropShadowShader']) {
   var source = "class Tint extends Module { function new() { super('tint'); } "
    + "override function onSongStart(event) { var shader = new " + shader + "(); PlayState.instance.camGame.filters = []; } }";
   var result = HxcCompat.analyze(source, 'scripts/modules/Tint.hxc');
   if (result.kind != 'module' || !result.moduleSafe)
    throw shader + ' made the module unsafe: ' + result.moduleSafetyReasons.join(',');
   if (result.generatedHscript.indexOf('new ' + shader + '()') < 0)
    throw shader + ' construction was not kept: ' + result.generatedHscript;
  }
  // An unknown class name must still keep the module out of execution.
  var unknown = HxcCompat.analyze("class Tint extends Module { function new() { super('tint'); } "
   + "override function onSongStart(event) { var shader = new NotARealShader(); } }", 'scripts/modules/Tint.hxc');
  if (unknown.moduleSafe)
   throw 'an unknown root was accepted';
 }
}
'''


class HxcModuleShaderRootsTest(unittest.TestCase):
    def test_base_game_shaders_are_known_module_roots(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'Main.hx').write_text(MAIN, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
