"""Coverage for the vendored-hscript null-safety patches.

Ported scripts chain optional donor lookups (`obj.member.field + 5`). Two
engine layers keep that survivable on hxcpp:
1. The vendored hscript Interp degrades null-object field reads/writes to
   diagnosed no-ops, and null-operand arithmetic/ordering binops return
   null/false instead of dereferencing the null vtable (a hard SIGSEGV).
2. HxcCompat lowers `currentStage._data.characters.<role>` to the native
   StageHelper slot snapshot so those chains carry real numbers.
"""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"
RUN_SH = ROOT / "run.sh"
RUN_BAT = ROOT / "run.bat"
PATCHER = ROOT / "tools/patch_hscript_compat.py"


def hx_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


class HscriptNullSafetyTest(unittest.TestCase):
    def test_null_access_diagnostics_are_scoped_to_source_and_callback(self):
        fixture = '''import hscript.Parser;
import hscript.Interp;
class NullAccessContextProbe {
 static function main() {
  var program = new Parser().parseString("missing.readField; missing.writeField = 1; missing.callMethod();");
  var interp = new Interp();
  interp.variables.set("missing", null);
  interp.variables.set("__compatDiagnosticSource", "scripts/songs/probe.hxc");
  for (callback in ["onUpdate", "onUpdate", "stepHit"]) {
   interp.variables.set("__compatDiagnosticCallback", callback);
   interp.execute(program);
  }
 }
}
'''
        with tempfile.TemporaryDirectory(prefix="hscript-null-access-context-") as folder:
            (Path(folder) / "NullAccessContextProbe.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", str(HSCRIPT), "-cp", folder,
                 "-main", "NullAccessContextProbe", "--interp"],
                text=True, capture_output=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for access in (
                'read to "readField"', 'write to "writeField"',
                'call to "callMethod"'):
            for callback in ("onUpdate", "stepHit"):
                diagnostic = ('[hscript-null-access] ' + access
                              + ' on a null object was ignored so the script can continue '
                              + '(scripts/songs/probe.hxc#' + callback + ')')
                self.assertEqual(result.stdout.count(diagnostic), 1,
                                 result.stdout + result.stderr)
        self.assertEqual(result.stdout.count('[hscript-null-access]'), 6,
                         result.stdout + result.stderr)

    def test_build_scripts_use_the_shared_null_context_patcher(self):
        run_script = RUN_SH.read_text()
        windows_script = RUN_BAT.read_text()
        patcher = PATCHER.read_text()
        self.assertIn("python3 tools/patch_hscript_compat.py", run_script)
        self.assertIn("tools\\patch_hscript_compat.py", windows_script)
        self.assertIn('"name": \'null-access diagnostic context\'', patcher)
        self.assertIn('variables.get("__compatDiagnosticSource")', patcher)
        self.assertIn('variables.get("__compatDiagnosticCallback")', patcher)
        self.assertLess(patcher.index('"name": \'null-access diagnostic context\''),
                        patcher.index('"name": \'null-operand guards\''))

    def test_operand_warnings_are_scoped_without_changing_null_result(self):
        fixture = '''import hscript.Parser;
import hscript.Interp;
class WarningContextProbe {
 static function main() {
  var program = new Parser().parseString("result = absent + 1;");
  for (source in ['first.lua', 'second.lua']) {
   var interp = new Interp();
   interp.variables.set('absent', null);
   interp.variables.set('__compatDiagnosticSource', source);
   for (callback in ['onUpdate', 'onUpdate', 'onTimerCompleted']) {
    interp.variables.set('__compatDiagnosticCallback', callback);
    interp.variables.set('result', 42);
    interp.execute(program);
    if (interp.variables.get('result') != null) throw 'operator semantics changed';
   }
  }
 }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'WarningContextProbe.hx').write_text(fixture)
            result = subprocess.run(
                [str(HAXE), '-cp', str(HSCRIPT), '-cp', folder,
                 '-main', 'WarningContextProbe', '--interp'],
                text=True, capture_output=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count('[hscript-null-operand]'), 4)
        for source in ('first.lua', 'second.lua'):
            for callback in ('onUpdate', 'onTimerCompleted'):
                self.assertEqual(result.stdout.count(source + '#' + callback), 1)

    def _run_interp(self, program: str) -> str:
        fixture = f'''import hscript.Parser;
import hscript.Interp;
class NullSafetyProbe {{
  static function main() {{
    var parser = new Parser();
    var program = parser.parseString({hx_string(program)});
    var interp = new Interp();
    interp.variables.set("nothing", null);
    interp.variables.set("report", function(arithmetic, comparison, compound) {{
      Sys.println("arithmetic=" + arithmetic);
      Sys.println("comparison=" + comparison);
      Sys.println("compound=" + compound);
    }});
    interp.execute(program);
  }}
}}
'''
        with tempfile.TemporaryDirectory(prefix="hscript-null-safety-", dir=ROOT / "tmp") as folder:
            path = Path(folder) / "NullSafetyProbe.hx"
            path.write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", str(HSCRIPT), "-cp", folder, "--run", "NullSafetyProbe"],
                cwd=folder, capture_output=True, text=True, timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def test_null_operand_binops_degrade_instead_of_crashing(self):
        output = self._run_interp(
            "var out = nothing.field + 5;"
            "var cmp = nothing.other > 3;"
            "var acc = 10;"
            "acc += nothing.field;"
            "report(out, cmp, acc);"
        )
        # The whole closure must finish; null operands become null/false, which
        # the scripts' own null checks (and the engine's diagnostics) can see.
        self.assertIn("arithmetic=null", output)
        self.assertIn("comparison=false", output)
        self.assertIn("compound=null", output)
        self.assertIn("hscript-null-access", output)
        self.assertIn("hscript-null-operand", output)

    def _run_interp_with_observer(self, program: str) -> str:
        """Run a program whose `snapshot(...)` call prints each argument value."""
        fixture = f'''import hscript.Parser;
import hscript.Interp;
class NullSafetyProbe {{
  static function main() {{
    var parser = new Parser();
    var program = parser.parseString({hx_string(program)});
    var interp = new Interp();
    interp.variables.set("nothing", null);
    interp.variables.set("snapshot", Reflect.makeVarArgs(function(args:Array<Dynamic>) {{
      var parts:Array<String> = [];
      for (a in args) parts.push(a == null ? "null" : Std.string(a));
      Sys.println("snapshot[" + parts.join(",") + "]");
    }}));
    interp.execute(program);
  }}
}}
'''
        with tempfile.TemporaryDirectory(prefix="hscript-null-safety-", dir=ROOT / "tmp") as folder:
            path = Path(folder) / "NullSafetyProbe.hx"
            path.write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", str(HSCRIPT), "-cp", folder, "--run", "NullSafetyProbe"],
                cwd=folder, capture_output=True, text=True, timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def test_null_index_read_degrades_instead_of_crashing(self):
        # hellNote's `splashData.getSplashOffsets()[0]` chains an index over a
        # missing donor lookup; the index must degrade like field reads do.
        output = self._run_interp_with_observer(
            "var v = nothing.splashOffsets[0] * 2;"
            "snapshot(v);"
        )
        self.assertIn("snapshot[null]", output)
        self.assertIn("hscript-null-access", output)
        self.assertIn("hscript-null-operand", output)

    def test_compound_field_assign_with_null_operand_keeps_previous_value(self):
        # `splash.x += null` must not write null into the native field: the
        # compound assign keeps the previous value instead of nulling it.
        output = self._run_interp_with_observer(
            "var o = {x: 5.0};"
            "o.x += nothing.missing;"
            "snapshot(o.x);"
        )
        self.assertIn("snapshot[5]", output)
        self.assertIn("hscript-null-operand", output)

    def test_stage_data_lowering_replaces_null_chain(self):
        fixture = f'''class StageDataProbe {{
  static function main() {{
    var result = HxcCompat.analyze({hx_string(self.DONOR)}, {hx_string("/donor/scripts/songs/probe.hxc")});
    Sys.println(result.generatedHscript);
  }}
}}
'''
        with tempfile.TemporaryDirectory(prefix="hxc-stage-data-", dir=ROOT / "tmp") as folder:
            path = Path(folder) / "StageDataProbe.hx"
            path.write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(HSCRIPT), "-cp", folder,
                 "--run", "StageDataProbe"],
                cwd=folder, capture_output=True, text=True, timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = result.stdout + result.stderr
        self.assertIn('HxcCompatRuntime.stageCharacterData("dad")', output)
        # The raw donor chain must not survive into the generated script.
        self.assertNotIn("_data.characters", output)

    DONOR = """
import funkin.play.PlayState;

class ProbeSong extends Module {
  public function new() { super('probe'); }

  public function placeExtraOpp() {
    var stageCharData = PlayState.instance.currentStage._data.characters.dad;
    var extraX = (stageCharData.position[0]) - 250;
    var extraY = (stageCharData.position[1]) + 30;
  }
}
"""


if __name__ == "__main__":
    unittest.main()
