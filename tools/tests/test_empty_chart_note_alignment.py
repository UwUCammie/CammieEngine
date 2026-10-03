"""Empty/event-only charts must not dereference a nonexistent first note."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

from test_psych_character_scope import extract_method

ROOT = Path(__file__).resolve().parents[2]


class EmptyChartNoteAlignmentTest(unittest.TestCase):
    def test_empty_chart_uses_loaded_receptor_width_and_keeps_normal_chart_width(self):
        play = (ROOT / "source/PlayState.hx").read_text()
        method = extract_method(play, "function initialNoteAlignmentWidth(")
        self.assertIn("defaultNoteWidth = initialNoteAlignmentWidth();", play)
        source = """typedef FixtureStrumline = {var members:Array<{width:Float}>;}
class Note { public static var swagWidth:Float = 112; }
class Main {
 var unspawnNotes:Array<Dynamic> = [];
 var playerStrums:FixtureStrumline;
 var enemyStrums:FixtureStrumline;
 public function new() {}
""" + method + """
 static function main() {
  var state = new Main();
  if (state.initialNoteAlignmentWidth() != 112) throw 'empty fallback width';
  state.playerStrums = {members:[null,{width:Math.NaN},{width:0}]};
  state.enemyStrums = {members:[{width:42}]};
  if (state.initialNoteAlignmentWidth() != 42) throw 'loaded opponent receptor fallback';
  state.playerStrums = {members:[{width:32}]};
  if (state.initialNoteAlignmentWidth() != 32) throw 'loaded player receptor pack width';
  state.unspawnNotes = [{width:78}];
  if (state.initialNoteAlignmentWidth() != 78) throw 'nonempty chart width changed';
 }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            folder = Path(work)
            (folder / "Main.hx").write_text(source, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(folder),
                                     "--run", "Main"], cwd=ROOT, text=True,
                                    capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
