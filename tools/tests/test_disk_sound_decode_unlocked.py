"""A disk sound decode does not hold the shared sound cache lock."""
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_native_asset_resolution import extract_method

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class DiskSoundDecodeUnlockedTest(unittest.TestCase):
    def test_decode_runs_between_lock_sections(self):
        source = (ROOT / "source/FNFAssets.hx").read_text(encoding="utf-8")
        body = extract_method(source, "static function diskSound(")
        cached = body.index("var cached = diskSounds.peek(key, epoch);")
        decode = body.index("var decoded = load();")
        store = body.index("diskSounds.getOrLoad(key, true, epoch,")
        self.assertLess(cached, decode)
        self.assertLess(decode, store)
        # every acquire is released before the decode starts
        before = body[:decode]
        self.assertEqual(before.count("soundLock.acquire()"), before.count("soundLock.release()"))
        # the store step only hands over the finished decode
        self.assertIn("function():Sound return decoded, pin)", body[store:])
        self.assertEqual(body.count("load()"), 2)  # the uncached path and the one unlocked decode

    def test_store_after_unlocked_decode_keeps_the_first_result(self):
        # The cache contract the unlocked path relies on: a second store for the
        # same file returns what is already there and drops the late decode.
        fixture = r'''class DiskSoundRaceFixture {
 static function fail(message:String):Void throw message;
 static function main() {
  var cache = new DiskSoundCache<String>();
  if (cache.peek("/game/a.ogg", 0) != null) fail("empty cache returned a sound");
  var first = cache.getOrLoad("/game/a.ogg", true, 0, function() return 10.0, function() return "thread-one");
  var second = cache.getOrLoad("/game/a.ogg", true, 0, function() return 10.0, function() return "thread-two");
  if (first != "thread-one" || second != "thread-one") fail("late decode replaced the stored one");
  if (cache.peek("/game/a.ogg", 0) != "thread-one") fail("peek after store");
  if (cache.peek("/game/a.ogg", 1) != null) fail("peek ignored a library change");
  Sys.println("OK");
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (FixturePath(folder) / "DiskSoundRaceFixture.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"), "--run", "DiskSoundRaceFixture"],
                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
