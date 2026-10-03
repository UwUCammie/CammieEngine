"""Psych song-position reads stay numeric before chart playback initializes."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class ConductorPositionDefaultsTest(unittest.TestCase):
    def test_song_position_callback_starts_at_zero(self):
        source = (ROOT / "source/Conductor.hx").read_text()
        match = re.search(
            r"public static var songPosition:Float\s*=\s*([^;]+);", source
        )
        self.assertIsNotNone(match, "songPosition must have an explicit default")
        declaration = match.group(0)
        self.assertEqual(match.group(1).strip(), "0")

        fixture = """
class Conductor {
    __SONG_POSITION__
}

class Fixture {
    static function main() {
        var getSongPosition = function():Float return Conductor.songPosition;
        if (getSongPosition() != 0)
            throw "song clock is not initialized for pre-play callbacks";
    }
}
""".replace("__SONG_POSITION__", declaration)

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Fixture.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "Fixture", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
