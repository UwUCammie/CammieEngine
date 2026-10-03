"""Psych source stage enum-abstract blend-mode bindings."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
import os


ROOT = Path(__file__).resolve().parents[2]


class PsychCompiledStageBlendModesTest(unittest.TestCase):
    @unittest.skipIf(not (ROOT / 'tmp/psych-archive-source/FNF-PsychEngine-main/source/states/stages/PhillyBlazin.hx').is_file(), 'private Psych archive fixture is unavailable')
    def test_unqualified_blend_abstract_constants_are_bound_for_hscript(self):
        bindings = (ROOT / "source/PsychCompiledStageBindings.hx").read_text()
        self.assertIn("for (constant in Reflect.fields(blendModes))", bindings)
        self.assertIn(
            "bindings.set(constant, Reflect.field(blendModes, constant));", bindings
        )
        self.assertIn("MULTIPLY: BlendMode.MULTIPLY", (ROOT / "source/CodenameImportBindings.hx").read_text())
        self.assertIn("foregroundMultiply.blend = MULTIPLY", (
            ROOT / "tmp/psych-archive-source/FNF-PsychEngine-main/source/states/stages/PhillyBlazin.hx"
        ).read_text())

        fixture = '''import hscript.Interp;
import hscript.Parser;
class Main {
  static function main() {
    var blendModes:Dynamic = {ADD:'add', MULTIPLY:'multiply', SCREEN:'screen'};
    var bindings:Map<String, Dynamic> = new Map();
    for (constant in Reflect.fields(blendModes))
      bindings.set(constant, Reflect.field(blendModes, constant));
    var interp = new Interp();
    for (constant in bindings.keys())
      interp.variables.set(constant, bindings.get(constant));
    var stageBlend = interp.execute(new Parser().parseString('MULTIPLY'));
    if (stageBlend != 'multiply')
      throw 'unqualified blend constant was not visible to HScript';
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
