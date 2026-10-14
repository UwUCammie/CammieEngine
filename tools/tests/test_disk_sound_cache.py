"""Disk sounds are decoded once and shared, with a bounded lifetime."""
from haxe_test_support import HAXE_COMMAND, FixturePath

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run_fixture(name, source):
    with tempfile.TemporaryDirectory() as folder:
        (FixturePath(folder) / (name + ".hx")).write_text(source, newline='\n')
        return subprocess.run(
            [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"), "--run", name],
            cwd=ROOT, capture_output=True, text=True, timeout=60)


class DiskSoundCacheTest(unittest.TestCase):
    def test_repeat_requests_share_one_decode_until_cleared(self):
        fixture = r'''class DiskSoundCacheFixture {
 static function fail(message:String):Void throw message;
 static function main() {
  var cache = new DiskSoundCache<String>();
  var loads = 0;
  var size = 2000.0;
  function request(path:String, useCache:Bool, epoch:Int, pin:Bool = false):String
   return cache.getOrLoad(path, useCache, epoch, function() return size,
    function() { loads++; return "decoded-" + loads; }, pin);

  var first = request("/game/assets/sounds/../sounds/hit.ogg", true, 0);
  for (i in 0...50)
   if (request("/game/assets/sounds/hit.ogg", true, 0) != first) fail("a repeat request decoded again");
  if (loads != 1 || cache.count() != 1) fail("expected one decode for the same file, got " + loads);

  if (request("/game/assets/sounds/hit.ogg", false, 0) != "decoded-2" || loads != 2)
   fail("useCache=false did not decode fresh");
  if (request("/game/assets/sounds/hit.ogg", true, 0) != first || loads != 2)
   fail("an uncached read replaced the shared sound");

  // A long track is handed back but not kept unless it was asked for by name.
  size = DiskSoundCache.AUTO_KEEP_MAX_FILE_BYTES + 1;
  var song = request("/game/assets/music/song.ogg", true, 0);
  if (request("/game/assets/music/song.ogg", true, 0) == song) fail("a large file was kept without a precache");
  var pinned = request("/game/assets/music/cue.ogg", true, 0, true);
  var before = loads;
  if (request("/game/assets/music/cue.ogg", true, 0) != pinned || loads != before)
   fail("a precached sound was decoded again on play");
  if (cache.peek("/game/assets/music/cue.ogg", 0) != pinned) fail("peek missed the precached sound");

  // The library changing drops everything, so replaced files are re-read.
  size = 2000;
  var afterImport = request("/game/assets/sounds/hit.ogg", true, 1);
  if (afterImport == first) fail("a sound survived a library change");
  if (cache.peek("/game/assets/music/cue.ogg", 1) != null) fail("a pinned sound survived a library change");

  cache.clear();
  if (cache.count() != 0) fail("clear left entries behind");
  if (request("/game/assets/sounds/hit.ogg", true, 1) == afterImport) fail("clear did not evict");

  // Retained size is bounded: going past the cap drops the store, never grows it.
  cache.clear();
  size = DiskSoundCache.AUTO_KEEP_MAX_FILE_BYTES;
  var files = Std.int(DiskSoundCache.MAX_RETAINED_FILE_BYTES / size) + 8;
  for (i in 0...files) request("/game/assets/sounds/s" + i + ".ogg", true, 1);
  if (cache.count() > Std.int(DiskSoundCache.MAX_RETAINED_FILE_BYTES / size))
   fail("the cache grew past its byte budget: " + cache.count());

  // A file that cannot be measured is treated as large.
  cache.getOrLoad("/game/assets/sounds/odd.ogg", true, 1, function():Float throw "no stat",
   function() { loads++; return "odd-" + loads; });
  if (cache.peek("/game/assets/sounds/odd.ogg", 1) != null) fail("an unmeasured file was kept");
  Sys.println("OK");
 }
}'''
        result = run_fixture("DiskSoundCacheFixture", fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def test_engine_sound_paths_route_through_the_shared_cache(self):
        assets = (ROOT / "source/FNFAssets.hx").read_text(encoding="utf-8")
        self.assertIn("SongLoadingWork.complete(diskSound(path, useCache, false))", assets)
        self.assertIn("public static function precacheSound(id:String)", assets)
        self.assertIn("public static function clearSoundCache()", assets)
        # Streamed music keeps its own cursor per call and must not be shared.
        music = assets[assets.index("public static function getMusic("):assets.index("public static function getSound(")]
        self.assertIn("NativeVorbisSound.load(path)", music)
        self.assertNotIn("diskSound(", music)
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        self.assertNotIn('FlxG.sound.play(FNFAssets.getSound("assets/sounds/hitSound.ogg"))', play)
        self.assertNotIn("FlxG.sound.play(FNFAssets.getSound('assets/sounds/hitSound.ogg'))", play)
        # Every hit sound goes through one route that decodes each file once per song.
        self.assertNotIn("playHitSound();", play)
        feedback = play[play.index("function feedbackSound(name:String):Sound {"):]
        feedback = feedback[:feedback.index("function feedbackOwnerSoundPath(")]
        self.assertIn("if (feedbackSounds.exists(requested)) return feedbackSounds.get(requested);", feedback)
        self.assertIn("FNFAssets.precacheSound(path)", feedback)
        self.assertNotIn("getSound(", feedback)
        self.assertIn("hscriptSoundCache.set(resolved, FNFAssets.getSound(resolved))", play)
        self.assertIn("FNFAssets.precacheSound(resolved)", play)
        teardown = play[play.index("public static function clearHscriptSoundCache()"):]
        self.assertIn("FNFAssets.clearSoundCache();", teardown[:600])


if __name__ == "__main__":
    unittest.main()
