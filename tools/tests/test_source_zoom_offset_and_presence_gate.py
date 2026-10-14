"""The resting camera zoom takes an additive offset and presence updates can be switched off."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(marker)


class SourceZoomOffsetAndPresenceGateTest(unittest.TestCase):
    def test_resting_zoom_adds_the_offset_and_zero_changes_nothing(self):
        if not (ROOT / ".tools/haxe/haxe.exe").is_file() and not (ROOT / ".tools/haxe/haxe").is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        fixture = "class ZoomOffsetFixture {\n" + method(play, "\tpublic static function restingZoom(") + r'''
 static function main():Void {
  for (base in [0.5, 0.7, 0.9, 1.05, 1.3])
   if (restingZoom(base, 0) != base) throw 'a zero offset must leave the resting zoom untouched: ' + base;
  if (Math.abs(restingZoom(0.9, 0.25) - 1.15) > 1e-9) throw 'zoom in';
  if (Math.abs(restingZoom(0.9, -0.2) - 0.7) > 1e-9) throw 'zoom out';
  // A tween of the offset moves the target smoothly and lands back on the base.
  var last = restingZoom(1, 0.4);
  for (step in 1...9) {
   var next = restingZoom(1, 0.4 * (1 - step / 8));
   if (next >= last) throw 'tweened offset should keep falling';
   last = next;
  }
  if (last != 1) throw 'tween should end on the base zoom';
  Sys.println('OK');
 }
}
'''
        with tempfile.TemporaryDirectory(prefix="zoom-offset-", dir=ROOT / "tmp") as folder:
            scratch = Path(folder)
            (scratch / "ZoomOffsetFixture.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(scratch), "--run", "ZoomOffsetFixture"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def test_camera_decay_targets_the_offset_resting_zoom(self):
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        self.assertIn("@:keep public var defaultCamZoomAdd:Float = 0;", play)
        self.assertIn("camGame.zoom = FlxMath.lerp(restingZoom(gameplayZoomBase(), defaultCamZoomAdd), camGame.zoom,", play)
        # The offset stays out of the base itself, so reading the base back and
        # writing it again can't compound the offset.
        self.assertIn("\tfunction gameplayZoomBase():Float\n"
                      "\t\treturn baseCameraZoom != null ? baseCameraZoom : defaultCamZoom;", play)

    def test_automatic_presence_updates_check_the_switch(self):
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        self.assertIn("@:keep public var automatedDiscord:Bool = true;", play)
        update = method(play, "\tfunction updatePresence():Void {")
        self.assertLess(update.index("if (!automatedDiscord) return;"), update.index("DiscordClient.changePresence("))
        # Pause, resume and game over write presence directly, so they ask too.
        for call in ('DiscordClient.changePresence(ae', 'DiscordClient.changePresence("GAME OVER -- "',
                     'DiscordClient.changePresence(customPrecence, SONG.song'):
            self.assertIn("if (automatedDiscord) " + call, play)
            self.assertEqual(play.count(call), 1, call)


if __name__ == "__main__":
    unittest.main()
