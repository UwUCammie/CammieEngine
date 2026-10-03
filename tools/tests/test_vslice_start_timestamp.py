"""V-Slice's startTimestamp must describe the launch seek used by native play."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
PLAY_STATE = ROOT / "source/PlayState.hx"
HAXE = ROOT / ".tools/haxe/haxe"


def extract_function(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unclosed function {signature}")


class VSliceStartTimestampTest(unittest.TestCase):
    def test_launch_seek_is_captured_once_and_used_by_notes_and_transport(self):
        source = PLAY_STATE.read_text()
        consume = extract_function(source, "\tstatic function consumeStartingPosition()")
        create_start = source.index("override public function create()")
        create_end = source.index("var psychCameraRoot", create_start)
        create_head = source[create_start:create_end]
        capture_at = source.index("startTimestamp = consumeStartingPosition();", create_start)
        self.assertIn("startTimestamp = consumeStartingPosition();", create_head)
        self.assertLess(capture_at, create_end)
        self.assertIn("if (daStrumTime >= startTimestamp)", source)
        self.assertIn("Conductor.songPosition = startTimestamp;", source)

        fixture = f'''class TimestampHarness {{
 public static var startingPosition:Float = 0;
 public var startTimestamp:Float = 0;
 public function new() {{}}
{consume}
 public function capture():Void startTimestamp = consumeStartingPosition();
}}
class Main {{
 static function fail(message:String):Void throw message;
 static function main():Void {{
  var state = new TimestampHarness();
  TimestampHarness.startingPosition = 31250;
  state.capture();
  if (state.startTimestamp != 31250 || TimestampHarness.startingPosition != 0)
   fail('editor seek was not captured and consumed');
  TimestampHarness.startingPosition = 0;
  state.capture();
  if (state.startTimestamp != 0 || TimestampHarness.startingPosition != 0)
   fail('default launch did not start at zero');
  TimestampHarness.startingPosition = Math.NaN;
  state.capture();
  if (state.startTimestamp != 0 || TimestampHarness.startingPosition != 0)
   fail('invalid launch timestamp was not normalized');
 }}
}}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_chart_editor_launch_seek_feeds_the_native_one_shot(self):
        editor = (ROOT / "source/ChartingState.hx").read_text()
        self.assertIn("PlayState.startingPosition = Conductor.songPosition;", editor)
        self.assertIn("LoadingState.loadAndSwitchState(new PlayState());", editor)


if __name__ == "__main__":
    unittest.main()
