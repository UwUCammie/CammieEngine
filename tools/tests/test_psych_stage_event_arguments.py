"""Check the source Psych event values forwarded to compiled stages."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for position in range(opening, len(source)):
        if source[position] == "{":
            depth += 1
        elif source[position] == "}":
            depth -= 1
            if depth == 0:
                return source[start:position + 1]
    raise AssertionError(marker)


class PsychStageEventArgumentsTest(unittest.TestCase):
    def test_hey_duration_is_normalized_before_stage_callback(self):
        play = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("psychCompiledStageEventFloat2(Std.string(name), value2)", play)
        self.assertIn("PsychHeyEventCompat.target(e.v1)", play)
        self.assertIn("cheerActor.heyTimer = duration;", play)
        self.assertIn("boyfriend.heyTimer = duration;", play)
        fixture = r'''
class Main {
 public function new() {}
__FLOAT__
__EVENT_FLOAT__
 static function check(ok:Bool, label:String):Void if(!ok) throw label;
 public static function main():Void {
  var state=new Main();
  check(state.psychCompiledStageEventFloat2('Hey!', '') == 0.6, 'empty Hey duration');
  check(state.psychCompiledStageEventFloat2('Hey!', null) == 0.6, 'null Hey duration');
  check(state.psychCompiledStageEventFloat2('Hey!', '0') == 0.6, 'zero Hey duration');
  check(state.psychCompiledStageEventFloat2('Hey!', '-1') == 0.6, 'negative Hey duration');
  check(state.psychCompiledStageEventFloat2('Hey!', '1.2') == 1.2, 'authored Hey duration');
  check(state.psychCompiledStageEventFloat2('Other Event', '') == null, 'other event null');
  check(PsychHeyEventCompat.target('0') == 0, 'boyfriend target');
  check(PsychHeyEventCompat.target('1') == 1, 'girlfriend target');
  check(PsychHeyEventCompat.target('2') == 2, 'both target');
  check(PsychHeyEventCompat.target(' boyfriend ') == 0, 'trimmed target');
 }
}
'''.replace("__FLOAT__", method(play, "function psychCompiledStageFloat(value:Dynamic)")) \
   .replace("__EVENT_FLOAT__", method(play, "function psychCompiledStageEventFloat2(name:String"))
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            folder = Path(scratch)
            (folder / "Main.hx").write_text(fixture)
            (folder / "PsychHeyEventCompat.hx").write_text(
                (ROOT / "source/PsychHeyEventCompat.hx").read_text())
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(folder), "--run", "Main"],
                cwd=ROOT, text=True, capture_output=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
