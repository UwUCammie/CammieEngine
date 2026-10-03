"""Psych script interpreters receive the shared story and quality globals."""
from haxe_test_support import HAXE_COMMAND

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"


class PsychScopeGlobalsTest(unittest.TestCase):
    def test_shared_playstate_scope_seeds_and_evaluates_globals(self):
        play_state = (ROOT / "source/PlayState.hx").read_text()
        engine = (ROOT / "source/EngineCompat.hx").read_text()
        start = play_state.index("function makeHaxeState(")
        end = play_state.index("function makeHaxeStateUI(", start)
        make_state = play_state[start:end]
        low_quality_seed = 'interp.variables.set("lowQuality", false);'
        self.assertIn(low_quality_seed, make_state)
        self.assertIn("interp.variables.set('isStoryMode', EngineCompat.importedScriptStoryMode(isStoryMode,", play_state)
        self.assertIn("alwaysDoCutscenes, Std.isOfType(interp, LuaCompatInterp))", play_state)
        self.assertNotIn("if (isHxcSource) {\n\t\t\tvar hxcRoot", make_state[make_state.index(low_quality_seed):])

        marker = "public static function importedScriptStoryMode"
        method_start = engine.index(marker)
        brace = engine.index("{", method_start)
        depth = 0
        method_end = None
        for index in range(brace, len(engine)):
            if engine[index] == "{":
                depth += 1
            elif engine[index] == "}":
                depth -= 1
                if depth == 0:
                    method_end = index + 1
                    break
        self.assertIsNotNone(method_end)
        method = engine[method_start:method_end]

        fixture = f'''import hscript.Interp;
import hscript.Parser;
class EngineCompat {{
{method}
}}
class Main {{
  static var isStoryMode:Bool = false;
  static function seed(interp:Interp, force:Bool, lua:Bool):Void {{
    {low_quality_seed}
    interp.variables.set("isStoryMode", EngineCompat.importedScriptStoryMode(isStoryMode, force, lua));
  }}
  static function check(storyMode:Bool, force:Bool, lua:Bool, expected:Bool):Void {{
    isStoryMode = storyMode;
    var interp = new Interp();
    seed(interp, force, lua);
    if (!interp.variables.exists("lowQuality") || !interp.variables.exists("isStoryMode"))
      throw "Psych scope globals were not installed";
    var value:Dynamic = interp.execute(new Parser().parseString("!lowQuality && isStoryMode"));
    if (value != expected) throw "script context mismatch: " + value;
    if (isStoryMode != storyMode) throw "native playlist context changed";
    try interp.execute(new Parser().parseString("throw 'script failure'")) catch (_:Dynamic) {{}}
    if (isStoryMode != storyMode) throw "script failure leaked into native mode";
  }}
  static function main() {{
    check(true, false, true, true);
    check(false, false, true, false);
    check(false, true, true, true);
    check(false, true, false, false);
  }}
}}'''
        task_tmp = ROOT / "tmp"
        task_tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="psych-scope-globals-", dir=task_tmp) as folder:
            Path(folder, "Main.hx").write_text(fixture, newline='\n')
            environment = os.environ.copy()
            environment["TMPDIR"] = str(task_tmp)
            for name in ("DISPLAY", "WAYLAND_DISPLAY", "WAYLAND_SOCKET", "XAUTHORITY", "XDG_RUNTIME_DIR"):
                environment.pop(name, None)
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(HSCRIPT),
                 "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
