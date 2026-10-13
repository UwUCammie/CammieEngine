"""Left Alt skips a cutscene to where the chart resumes; scenery videos are left alone."""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND, TEST_TMP
ROOT = Path(__file__).resolve().parents[2]


class CutsceneSkipTest(unittest.TestCase):
    def run_haxe(self, body):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            (Path(temp) / 'Main.hx').write_text('class Main {\n static function check(ok:Bool, m:String) { if (!ok) throw m; }\n static function main() {\n' + body + '\n }\n}', encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', temp, '--run', 'Main'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_landing_time_follows_the_chart(self):
        self.run_haxe(r"""
  var none = Math.NaN;
  check(CutsceneSkip.target(1000, 0, 8000, none, 300000) == 8000, 'cutscene without later notes should land on its end');
  check(CutsceneSkip.target(1000, 0, 8000, 20000, 300000) == 8000, 'a distant note moved the landing time');
  check(CutsceneSkip.target(1000, 0, 8000, 6000, 300000) == 6000 - CutsceneSkip.NOTE_LEAD_MS, 'landing time ignores the next player note');
  check(CutsceneSkip.target(303500, 303035, 11000, none, 310000) == 310000, 'landing time passed the end of the song');
  check(CutsceneSkip.target(9000, 0, 8000, none, 300000) == 9000, 'finished cutscene moved the song backwards');
  check(CutsceneSkip.target(1000, 0, 0, none, 300000) == 1000 && CutsceneSkip.target(1000, 0, -1, none, 300000) == 1000, 'unknown length treated as skippable');
  check(CutsceneSkip.target(1000, Math.NaN, 8000, none, 300000) == 1000, 'unknown start treated as skippable');
  check(CutsceneSkip.skippable(1000, 8000) && CutsceneSkip.skippable(1000, 1000 + CutsceneSkip.MIN_SKIP_MS), 'real cutscene refused');
  // A video behind notes is scenery: the next note is always close, so Enter keeps pausing.
  var scenery = CutsceneSkip.target(50000, 0, 200000, 50400, 300000);
  check(scenery == 50000 && !CutsceneSkip.skippable(50000, scenery), 'video behind notes treated as a cutscene');
  check(!CutsceneSkip.skippable(1000, 1200) && !CutsceneSkip.skippable(1000, Math.NaN), 'tiny or unknown jump accepted');
  check(CutsceneSkip.furthest([8000, 12000, Math.NaN, 500], 1000) == 12000 && CutsceneSkip.furthest([], 1000) == 1000, 'furthest landing time');""")

    def test_every_cutscene_route_answers_to_left_alt(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        self.assertIn('if (skipSongCutscenes(CutsceneSkipKey.pressed())) {} else', play)
        self.assertIn('seekForwardSongTime(target, false);', play)
        self.assertIn('registerSongCutscene(video, function() return video.durationMs,', play)
        cutscene = (ROOT / 'source/VideoCutscene.hx').read_text(encoding='utf-8')
        self.assertIn('} else if (CutsceneSkipKey.pressed())', cutscene)
        # Left Alt only: Enter and Space are back to their normal jobs.
        for source in (play, cutscene):
            self.assertNotIn('skipSongCutscenes(FlxG.keys', source)
        self.assertNotIn('justPressed.SPACE', cutscene)
        key = (ROOT / 'source/CutsceneSkipKey.hx').read_text(encoding='utf-8')
        self.assertIn('if (key != lime.ui.KeyCode.LEFT_ALT) return;', key)
        self.assertNotIn('RIGHT_ALT', key)
        owner = (ROOT / 'source/NightmareVisionVideoSprite.hx').read_text(encoding='utf-8')
        self.assertIn("Reflect.field(ownerState, 'registerSongCutscene')", owner)
        legacy = (ROOT / 'source/NightmareVisionLegacyVideoSprite.hx').read_text(encoding='utf-8')
        # The source's own end listeners must run on a skip, exactly as on a natural end.
        self.assertIn('video.onEndReached.dispatch();', legacy)

    def test_a_skip_press_counts_once_and_goes_stale(self):
        self.run_haxe(r"""
  check(CutsceneSkipKey.fresh(10, 10) && CutsceneSkipKey.fresh(10, 10 + CutsceneSkipKey.WINDOW), 'recent press refused');
  check(!CutsceneSkipKey.fresh(10, 10 + CutsceneSkipKey.WINDOW + 0.01) && !CutsceneSkipKey.fresh(10, 9) && !CutsceneSkipKey.fresh(Math.NEGATIVE_INFINITY, 5) && !CutsceneSkipKey.fresh(Math.NaN, 5), 'stale or missing press accepted');
  check(CutsceneSkipKey.WINDOW > 0 && CutsceneSkipKey.WINDOW <= 0.5, 'press lingers long enough to skip a later cutscene');
  check(!CutsceneSkipKey.pressed(), 'pressed without a key');
  CutsceneSkipKey.forced = true; check(CutsceneSkipKey.pressed(), 'forced press ignored'); CutsceneSkipKey.forced = false;""")

    def test_eased_camera_point_tracks_the_live_view(self):
        self.run_haxe(r"""
  check(SourceCameraFollowPointMath.origin(100, 1280, 1) == 739.5, 'point is not centred on the view');
  check(SourceCameraFollowPointMath.origin(-640, 1280, 1) == -0.5, 'negative scroll');
  check(!SourceCameraFollowPointMath.moved(10, 20, 10, 20.005) && SourceCameraFollowPointMath.moved(10, 20, 10, 21) && SourceCameraFollowPointMath.moved(11, 20, 10, 20), 'script move detection');""")
        point = (ROOT / 'source/SourceCameraFollowPoint.hx').read_text(encoding='utf-8')
        self.assertIn('camera.target == point && camera.followLerp >= 1) camera.snapToTarget();', point)
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        self.assertIn('@:keep public var camFollowPos:FlxObject = new FlxObject(0, 0, 1, 1);', play)
        self.assertIn('override public function draw():Void {\n\t\tsyncCamFollowPos();', play.replace('\r\n', '\n'))
        self.assertIn('camGame.focusOn(camFollowPos.getMidpoint());', play)


if __name__ == '__main__':
    unittest.main()
