"""Regression coverage for the bounded split-vocal PCM decode helper."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND


ROOT = Path(__file__).resolve().parents[2]


class SongAudioDecodeBatchTest(unittest.TestCase):
    def test_threaded_pair_order_pcm_and_failure_waiting(self):
        audio_buffer_stub = r'''package lime.media;
import sys.thread.Thread;
class AudioBuffer {
  public var source:String;
  public var pcm:Array<Int>;
  public var decodedOnMain:Bool;
  public static var mainThread:Thread;
  // Read by the test only after SongAudioDecodeBatch's worker lock completes.
  public static var slowWorkerCompleted:Bool = false;
  public function new(source:String, pcm:Array<Int>, decodedOnMain:Bool) {
    this.source = source;
    this.pcm = pcm;
    this.decodedOnMain = decodedOnMain;
  }
  public static function fromFile(path:String):AudioBuffer {
    var decodedOnMain = Thread.current() == mainThread;
    if (path == 'slow-worker') {
      Sys.sleep(0.05);
      if (!decodedOnMain) slowWorkerCompleted = true;
    }
    if (path == 'main-throws' && decodedOnMain) throw 'main decode failed';
    if (path == 'throws') throw 'decode failed';
    if (path == 'missing') return null;
    return new AudioBuffer(path, path == 'player' ? [11, -12, 13] : [-21, 22, -23], decodedOnMain);
  }
}'''
        main = r'''import lime.media.AudioBuffer;
import sys.thread.Thread;

class TestSongAudioDecodeBatch {
  static function check(value:Bool, message:String):Void {
    if (!value) throw message;
  }

  static function main():Void {
    AudioBuffer.mainThread = Thread.current();
    var decoded = SongAudioDecodeBatch.decodePair('player', 'opponent');
    check(decoded != null && decoded.length == 2, 'valid pair was rejected');
    check(decoded[0].source == 'player' && decoded[1].source == 'opponent',
      'buffers no longer match source order');
    check(decoded[0].pcm.join(',') == '11,-12,13'
      && decoded[1].pcm.join(',') == '-21,22,-23',
      'decoded PCM values changed');
    check(decoded[0].decodedOnMain, 'first buffer was not decoded on the caller thread');
    check(!decoded[1].decodedOnMain, 'second buffer was not decoded on the worker thread');

    AudioBuffer.slowWorkerCompleted = false;
    check(SongAudioDecodeBatch.decodePair('main-throws', 'slow-worker') == null,
      'main-thread exception did not report an all-or-nothing failure');
    check(AudioBuffer.slowWorkerCompleted,
      'helper returned before its worker completed after main-thread failure');

    check(SongAudioDecodeBatch.decodePair('player', 'throws') == null,
      'worker exception did not report an all-or-nothing failure');
    check(SongAudioDecodeBatch.decodePair('player', 'missing') == null,
      'null decode did not report an all-or-nothing failure');
  }
}'''
        lock_stub = r'''class TestAudioDecodeLock {
  final semaphore:eval.luv.Semaphore;
  public function new() semaphore = eval.luv.Semaphore.init(0).resolve();
  public function wait():Void semaphore.wait();
  public function release():Void semaphore.post();
}'''

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work_dir:
            work = Path(work_dir)
            helper = (ROOT / "source/SongAudioDecodeBatch.hx").read_text()
            helper = helper.replace("#if (cpp && target.threaded)", "#if eval")
            helper = helper.replace("#if (cpp && target.threaded && lime_cffi)", "#if eval")
            helper = helper.replace("import sys.thread.Lock;\n", "")
            helper = helper.replace("new Lock()", "new TestAudioDecodeLock()")
            (work / "SongAudioDecodeBatch.hx").write_text(helper, newline="\n")
            target = work / "lime/media/AudioBuffer.hx"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(audio_buffer_stub, newline="\n")
            (work / "TestSongAudioDecodeBatch.hx").write_text(main, newline="\n")
            (work / "TestAudioDecodeLock.hx").write_text(lock_stub, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", work_dir,
                 "--main", "TestSongAudioDecodeBatch", "--interp"],
                cwd=work_dir, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_native_worker_is_decode_only_and_falls_back_to_main_loader(self):
        helper = (ROOT / "source/SongAudioDecodeBatch.hx").read_text()
        self.assertIn("#if (cpp && target.threaded && lime_cffi)", helper)
        worker = helper.split("Thread.create(function():Void {", 1)[1].split(
            "\n\t\t\t});", 1)[0]
        self.assertEqual(worker.count("AudioBuffer.fromFile("), 1)
        for forbidden in ("Sound", "FlxSound", "FlxG", "FNFAssets", "Assets.", "OpenAL"):
            self.assertNotIn(forbidden, worker)

        play_state = (ROOT / "source/PlayState.hx").read_text()
        loader = play_state.split("private function loadVocalTrack(", 1)[1].split(
            "private function initializeVocalTracks(", 1)[0]
        self.assertIn("prefetchedSound == null ? FNFAssets.getSound(path) : prefetchedSound", loader)
        initializer = play_state.split("private function initializeVocalTracks(", 1)[1].split(
            "private function syncVocalTrackState(", 1)[0]
        self.assertIn("if (splitPaths.length == 2 && ImportIO.current() == null)", initializer)
        self.assertIn("FNFAssets.resolveCaseInsensitivePath(entry.path)", initializer)
        self.assertIn("FileSystem.exists(absolutePath)", initializer)
        self.assertIn("FileSystem.isDirectory(absolutePath)", initializer)
        self.assertIn("extension != 'ogg' && extension != 'wav'", initializer)
        decode = initializer.index("SongAudioDecodeBatch.decodePair(")
        wrap = initializer.index("Sound.fromAudioBuffer(decoded[0])")
        load = initializer.index("loadVocalTrack(entry.path, prefetchedSound)")
        self.assertLess(decode, wrap)
        self.assertLess(wrap, load)
        self.assertIn("song-vocal-decode:parallel=1-worker:success=", initializer)


if __name__ == "__main__":
    unittest.main()
