"""Portable contract tests for PCM song-audio normalization."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class SongAudioNormalizerTest(unittest.TestCase):
    def test_pcm_copy_gain_diagnostics_and_metadata_cache_invalidation(self):
        sound_stub = r'''package openfl.media;
import lime.media.AudioBuffer;
class Sound {
  public var __buffer:AudioBuffer;
  public function new() {}
  public static function fromAudioBuffer(buffer:AudioBuffer):Sound {
    var sound = new Sound();
    sound.__buffer = buffer;
    return sound;
  }
}'''
        buffer_stub = r'''package lime.media;
import lime.utils.UInt8Array;
class AudioBuffer {
  public var bitsPerSample:Int;
  public var channels:Int;
  public var sampleRate:Int;
  public var data:UInt8Array;
  public function new() {}
}'''
        uint8_stub = r'''package lime.utils;
import haxe.io.Bytes;
class UInt8Array {
  public var byteLength(default, null):Int;
  public var byteOffset(default, null):Int = 0;
  final bytes:Bytes;
  public function new(bytes:Bytes) {
    this.bytes = bytes;
    byteLength = bytes.length;
  }
  public function toBytes():Bytes return bytes;
  public static function fromBytes(bytes:Bytes):UInt8Array {
    return new UInt8Array(bytes);
  }
}'''
        assets_stub = r'''class FNFAssets {
  public static function resolveCaseInsensitivePath(path:String):String return path;
}'''
        main = r'''import haxe.io.Bytes;
import lime.media.AudioBuffer;
import lime.utils.UInt8Array;
import openfl.media.Sound;
import sys.FileSystem;
import sys.io.File;

class TestSongAudioNormalizer {
  static function check(value:Bool, message:String):Void {
    if (!value) throw message;
  }

  static function close(a:Float, b:Float, tolerance:Float = 0.0005):Bool {
    return Math.abs(a - b) <= tolerance;
  }

  static function pcm(samples:Array<Int>):Bytes {
    var bytes = Bytes.alloc(samples.length * 2);
    for (i in 0...samples.length) {
      var value = samples[i] & 0xFFFF;
      bytes.set(i * 2, value & 0xFF);
      bytes.set(i * 2 + 1, (value >> 8) & 0xFF);
    }
    return bytes;
  }

  static function samples(data:Bytes):Array<Int> {
    var result:Array<Int> = [];
    for (i in 0...Std.int(data.length / 2)) {
      var value = (data.get(i * 2) & 0xFF) | ((data.get(i * 2 + 1) & 0xFF) << 8);
      if ((value & 0x8000) != 0) value -= 0x10000;
      result.push(value);
    }
    return result;
  }

  static function copyBytes(data:Bytes):Bytes {
    var copy = Bytes.alloc(data.length);
    copy.blit(0, data, 0, data.length);
    return copy;
  }

  static function sameBytes(a:Bytes, b:Bytes):Bool {
    if (a == null || b == null || a.length != b.length) return false;
    for (i in 0...a.length) if (a.get(i) != b.get(i)) return false;
    return true;
  }

  static function sound(data:Bytes, bits:Int = 16):Sound {
    var buffer = new AudioBuffer();
    buffer.bitsPerSample = bits;
    buffer.channels = 1;
    buffer.sampleRate = 1000;
    buffer.data = UInt8Array.fromBytes(data);
    return Sound.fromAudioBuffer(buffer);
  }

  static function assertScaled(input:Bytes, output:Bytes, direction:Int, label:String):Void {
    var before = samples(input);
    var after = samples(output);
    check(before.length == after.length, label + ': sample count changed');
    var expectedRatio:Null<Float> = null;
    var checked = 0;
    for (i in 0...before.length) {
      if (before[i] == 0) continue;
      var ratio = after[i] / before[i];
      check(direction > 0 ? ratio > 1 : ratio < 1, label + ': wrong gain direction');
      if (expectedRatio == null) expectedRatio = ratio;
      check(close(ratio, expectedRatio), label + ': waveform was not scaled uniformly');
      checked++;
    }
    check(checked > 0, label + ': no nonzero samples were checked');
  }

  static function main():Void {
    var quietPath = 'normalizer-quiet-key.dat';
    var loudPath = 'normalizer-loud-key.dat';
    var silencePath = 'normalizer-silence-key.dat';
    var unsupportedPath = 'normalizer-unsupported-key.dat';
    var streamingPath = 'normalizer-streaming-key.dat';
    File.saveContent(quietPath, 'quiet source file metadata');
    File.saveContent(loudPath, 'loud source file metadata');
    File.saveContent(silencePath, 'silence source file metadata');
    File.saveContent(unsupportedPath, 'unsupported source file metadata');
    File.saveContent(streamingPath, 'streaming source file metadata');

    // Disabled normalization preserves identity and does not require a file.
    var disabled = sound(pcm([4096, -2048, 1024, -512]));
    check(SongAudioNormalizer.prepare(disabled, 'missing-disabled.wav', false) == disabled,
      'disabled option replaced the original Sound');

    // Quiet source audio receives positive gain in a private Sound/PCM copy.
    var quietBytes = pcm([5000, -4000, 3500, -3000]);
    var quiet = sound(quietBytes);
    var quietSnapshot = copyBytes(quietBytes);
    var louder = SongAudioNormalizer.prepare(quiet, quietPath, true);
    check(louder != quiet, 'positive gain did not produce a fresh Sound');
    check(sameBytes(quiet.__buffer.data.toBytes(), quietSnapshot),
      'normalization modified original PCM');
    assertScaled(quietBytes, louder.__buffer.data.toBytes(), 1, 'positive gain');

    // Repeating from the same original must produce the same one-time-scaled PCM.
    var louderAgain = SongAudioNormalizer.prepare(quiet, quietPath, true);
    check(louderAgain != quiet, 'cached gain did not produce a private Sound');
    check(sameBytes(louderAgain.__buffer.data.toBytes(), louder.__buffer.data.toBytes()),
      'repeated preparation compounded or changed normalization');
    check(sameBytes(quiet.__buffer.data.toBytes(), quietSnapshot),
      'repeated preparation changed original PCM');

    // Loud source audio is attenuated with the same waveform shape.
    var loudBytes = pcm([24576, -18000, 12000, -8000]);
    var loud = sound(loudBytes);
    var quieter = SongAudioNormalizer.prepare(loud, loudPath, true);
    check(quieter != loud, 'attenuation did not produce a fresh Sound');
    assertScaled(loudBytes, quieter.__buffer.data.toBytes(), -1, 'attenuation');
    check(sameBytes(loud.__buffer.data.toBytes(), loudBytes),
      'attenuation modified original PCM');

    // Silence has unity gain and needs no replacement buffer.
    var silenceBytes = pcm([0, 0, 0, 0]);
    var silence = sound(silenceBytes);
    check(SongAudioNormalizer.prepare(silence, silencePath, true) == silence,
      'silence did not retain unity gain');

    // Unsupported PCM and streaming/no-PCM inputs return the authored Sound.
    var unsupported = sound(pcm([4096, -2048]), 24);
    check(SongAudioNormalizer.prepare(unsupported, unsupportedPath, true) == unsupported,
      'unsupported PCM replaced the original Sound');
    var streaming = sound(pcm([4096, -2048]));
    streaming.__buffer.data = null;
    check(SongAudioNormalizer.prepare(streaming, streamingPath, true) == streaming,
      'missing PCM replaced the original Sound');

    // Change real file metadata and source PCM. A stale cached gain would still
    // attenuate these newly quiet samples using the previous loud-file gain.
    var changedBytes = pcm([5000, -4000, 3500, -3000]);
    loud.__buffer.data = UInt8Array.fromBytes(changedBytes);
    File.saveContent(loudPath, 'changed loud file metadata with a different size');
    var recomputed = SongAudioNormalizer.prepare(loud, loudPath, true);
    check(recomputed != loud, 'changed file metadata did not produce a fresh Sound');
    assertScaled(changedBytes, recomputed.__buffer.data.toBytes(), 1, 'metadata invalidation');

    FileSystem.deleteFile(quietPath);
    FileSystem.deleteFile(loudPath);
    FileSystem.deleteFile(silencePath);
    FileSystem.deleteFile(unsupportedPath);
    FileSystem.deleteFile(streamingPath);
  }
}'''

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            root = Path(work)
            files = {
                "TestSongAudioNormalizer.hx": main,
                "FNFAssets.hx": assets_stub,
                "openfl/media/Sound.hx": sound_stub,
                "lime/media/AudioBuffer.hx": buffer_stub,
                "lime/utils/UInt8Array.hx": uint8_stub,
            }
            for relative, contents in files.items():
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(contents, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", work, "-D", "lime",
                 "--main", "TestSongAudioNormalizer", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=60,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        diagnostics = result.stdout + result.stderr
        self.assertIn("[song-audio-normalization] Could not analyze", diagnostics)
        self.assertIn("supports only 8-bit or 16-bit PCM", diagnostics)
        self.assertIn("Decoded PCM unavailable", diagnostics)


if __name__ == "__main__":
    unittest.main()
