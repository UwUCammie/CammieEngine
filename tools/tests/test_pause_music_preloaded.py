"""Opening the pause menu neither probes the disk nor decodes its track."""
from haxe_test_support import HAXE_COMMAND, FixturePath

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class PauseMusicPreloadedTest(unittest.TestCase):
    def test_track_choice_is_made_once_and_reused_by_the_menu(self):
        fixture = r'''class PauseMusicFixture {
 static function fail(message:String):Void throw message;
 static function main() {
  var present:Map<String, Bool> = ["assets/music/breakfast.ogg" => true, "assets/music/breakfast-pixel.ogg" => true];
  var probes = 0;
  function exists(path:String):Bool { probes++; return present.exists(path); }

  // Loading pass.
  var loaded = PauseMusicTrack.pathFor("-pixel", ".ogg", 4, exists);
  if (loaded != "assets/music/breakfast-pixel.ogg") fail("suffixed track was not chosen: " + loaded);
  var afterLoad = probes;
  // Every later pause in the same song.
  for (i in 0...20)
   if (PauseMusicTrack.pathFor("-pixel", ".ogg", 4, exists) != loaded) fail("the choice changed between pauses");
  if (probes != afterLoad) fail("opening the menu probed the disk " + (probes - afterLoad) + " times");

  // A script changing the suffix mid-song still gets the right track.
  if (PauseMusicTrack.pathFor("-missing", ".ogg", 4, exists) != "assets/music/breakfast.ogg")
   fail("a missing suffixed track did not fall back to the stock one");
  if (PauseMusicTrack.pathFor("", ".ogg", 4, exists) != "assets/music/breakfast.ogg") fail("empty suffix");
  if (PauseMusicTrack.pathFor(null, ".ogg", 4, exists) != "assets/music/breakfast.ogg") fail("null suffix");

  // A library change can add the track, so the choice is made again.
  PauseMusicTrack.pathFor("-late", ".ogg", 4, exists);
  present.set("assets/music/breakfast-late.ogg", true);
  if (PauseMusicTrack.pathFor("-late", ".ogg", 5, exists) != "assets/music/breakfast-late.ogg")
   fail("a track added by an import was not picked up");

  PauseMusicTrack.forget();
  var before = probes;
  PauseMusicTrack.pathFor("-late", ".ogg", 5, exists);
  if (probes == before) fail("forget kept the remembered choice");

  // The random start needs a length; a track that cannot report one starts at 0.
  if (PauseMusicTrack.latestStart(120000) != 60000) fail("half length");
  if (PauseMusicTrack.latestStart(0) != 0 || PauseMusicTrack.latestStart(-5) != 0
   || PauseMusicTrack.latestStart(Math.NaN) != 0) fail("unknown length must start from the beginning");
  Sys.println("OK");
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (FixturePath(folder) / "PauseMusicFixture.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"), "--run", "PauseMusicFixture"],
                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def test_pause_menu_streams_the_track_chosen_at_load(self):
        pause = (ROOT / "source/PauseSubState.hx").read_text(encoding="utf-8")
        start = pause.index("public function new(x:Float, y:Float, camera:FlxCamera)")
        constructor = pause[start:pause.index("function codenameInitPauseScript()")]
        self.assertIn("PauseMusicTrack.pathFor(HxcCompatRuntime.pauseMusicSuffix, TitleState.soundExt,", constructor)
        self.assertIn("FNFAssets.getMusic(pauseTrack)", constructor)
        self.assertIn("PauseMusicTrack.latestStart(pauseMusic.length)", constructor)
        # The old constructor decoded the whole file from a path string.
        self.assertNotIn("loadEmbedded('assets/music/' + pauseTrack", constructor)
        self.assertNotIn("if (!FNFAssets.exists('assets/music/' + pauseTrack))", constructor)
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        preload = play[play.index("function preloadHitFeedback():Void"):]
        self.assertIn("PauseMusicTrack.pathFor(HxcCompatRuntime.pauseMusicSuffix, TitleState.soundExt,", preload[:900])
        self.assertLess(play.index("preloadHitFeedback();"), play.index("markLoadPhase('stage_loaded')"))


if __name__ == "__main__":
    unittest.main()
