"""HXC modules that skip the next transition reach Flixel's real flags.

Module translation used to lower FlxTransitionableState.skipNextTransIn/Out to
HxcCompatRuntime fields that nothing read, so a module asking to skip the next
fade still got it. Every interpreter binds the real class now, so the module
text is left alone, and the old runtime fields forward to the real flags for
translations made before the change.
"""
import json
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"

TRANSITION_STUB = '''package flixel.addons.transition;
class FlxTransitionableState {
 public static var skipNextTransIn:Bool = false;
 public static var skipNextTransOut:Bool = false;
}
'''

MODULE = '''class SkipFadeModule extends Module {
    function new() { super("SkipFadeModule"); }
    override function onStateChangeBegin(event) {
        FlxTransitionableState.skipNextTransIn = true;
        FlxTransitionableState.skipNextTransOut = true;
    }
}
'''


class HxcTransitionSkipFlagsTest(unittest.TestCase):
    def run_main(self, main):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='hxc-skip-trans-', dir=TEST_TMP) as folder:
            root = Path(folder)
            stub = root / 'flixel/addons/transition/FlxTransitionableState.hx'
            stub.parent.mkdir(parents=True)
            stub.write_text(TRANSITION_STUB, newline='\n')
            (root / 'Main.hx').write_text(main, newline='\n')
            return subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(HSCRIPT),
                                   '-cp', str(root), '-main', 'Main', '--interp'],
                                  cwd=ROOT, capture_output=True, text=True, timeout=600)

    def test_module_keeps_the_real_flixel_flags(self):
        main = '''class Main {
 static function fail(value:String):Void throw value;
 static function main() {
  var result = HxcCompat.analyze(''' + json.dumps(MODULE) + ''', "scripts/modules/SkipFadeModule.hxc");
  var generated:String = result.generatedHscript;
  if (generated.indexOf("HxcCompatRuntime.skipNextTrans") >= 0) fail("skip flag lowered to a dead field: " + generated);
  if (generated.indexOf("FlxTransitionableState.skipNextTransIn") < 0) fail("skip flag dropped: " + generated);
  if (!result.moduleSafe) fail("module rejected: " + result.moduleSafetyReasons.join(","));
  Sys.println("module-ok");
 }
}'''
        result = self.run_main(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('module-ok', result.stdout)

    def test_old_runtime_fields_forward_to_flixel(self):
        main = '''import flixel.addons.transition.FlxTransitionableState;
class Main {
 static function fail(value:String):Void throw value;
 static function main() {
  HxcCompatRuntime.skipNextTransIn = true;
  if (!FlxTransitionableState.skipNextTransIn) fail("runtime skipNextTransIn did not reach Flixel");
  FlxTransitionableState.skipNextTransOut = true;
  if (!HxcCompatRuntime.skipNextTransOut) fail("runtime skipNextTransOut did not read Flixel");
  HxcCompatRuntime.skipNextTransIn = false;
  if (FlxTransitionableState.skipNextTransIn) fail("clearing the runtime flag left Flixel skipping");
  Sys.println("runtime-ok");
 }
}'''
        result = self.run_main(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('runtime-ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
