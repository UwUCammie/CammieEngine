"""Exercise the PCM loudness analyzer with the portable Haxe interpreter."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class SongAudioLoudnessTest(unittest.TestCase):
    def test_pcm_gain_gates_limits_chunks_and_copy(self):
        fixture = r'''import haxe.io.Bytes;

class SongAudioLoudnessTestMain {
  static function check(ok:Bool, message:String):Void {
    if (!ok) throw message;
  }
  static function near(actual:Float, expected:Float, epsilon:Float, message:String):Void {
    check(Math.abs(actual - expected) <= epsilon, message + ': ' + actual + ' != ' + expected);
  }
  static function pcm16(value:Int, count:Int):Bytes {
    var bytes = Bytes.alloc(count * 2);
    for (i in 0...count) {
      bytes.set(i * 2, value & 0xFF);
      bytes.set(i * 2 + 1, (value >> 8) & 0xFF);
    }
    return bytes;
  }
  static function append(target:Bytes, values:Array<Bytes>):Void {
    var offset = 0;
    for (value in values) {
      target.blit(offset, value, 0, value.length);
      offset += value.length;
    }
  }
  static function expectFailure(action:Void->Void, label:String):Void {
    var failed = false;
    try action() catch (_:Dynamic) failed = true;
    check(failed, label + ' should fail explicitly');
  }
  static function main():Void {
    var targetRms = Math.pow(10, -18.0 / 20.0);

    var empty = new SongAudioLoudness(16, 2, 48000);
    check(empty.gain() == 1.0 && empty.gain() == 1.0, 'empty input must remain unity and idempotent');

    var silence = new SongAudioLoudness(16, 1, 48000);
    silence.addPcm(pcm16(0, 4800));
    check(silence.gain() == 1.0 && silence.samplePeak == 0, 'digital silence must remain unity');

    var trailing = new SongAudioLoudness(16, 1, 48000);
    trailing.addPcm(pcm16(6553, 1));
    near(trailing.sampleCount, 1, 0, 'partial final block sample count');
    near(trailing.gain(), targetRms / (6553.0 / 32768.0), 0.0001,
      'partial final block must contribute to measured RMS');
    near(trailing.gain(), trailing.gain(), 0, 'gain must be idempotent');

    var low = new SongAudioLoudness(16, 1, 1000);
    low.addPcm(pcm16(16, 100));
    check(low.gain() == 1.0, 'blocks below the -60 dBFS absolute gate must not be boosted');

    var gatedBytes = Bytes.alloc((50 * 3) * 2);
    append(gatedBytes, [pcm16(16384, 50), pcm16(2048, 50), pcm16(1024, 50)]);
    var gated = new SongAudioLoudness(16, 1, 1000);
    gated.addPcm(gatedBytes);
    var gatedRms = Math.sqrt((0.5 * 0.5 + 0.0625 * 0.0625) / 2.0);
    near(gated.gain(), targetRms / gatedRms, 0.001,
      'relative gate must retain the -18 dB block and reject the quieter block');

    var split = new SongAudioLoudness(16, 1, 1000);
    split.addPcm(gatedBytes, 0, 37 * 2);
    split.addPcm(gatedBytes, 37 * 2, gatedBytes.length - 37 * 2);
    near(split.gain(), gated.gain(), 0.000001, 'chunk boundaries must not change block results');
    check(split.sampleCount == gated.sampleCount, 'chunk sample count');

    var stereoBytes = Bytes.alloc(50 * 2 * 2);
    for (frame in 0...50) {
      stereoBytes.set(frame * 4, 0x00);
      stereoBytes.set(frame * 4 + 1, 0x40);
      stereoBytes.set(frame * 4 + 2, 0);
      stereoBytes.set(frame * 4 + 3, 0);
    }
    var stereo = new SongAudioLoudness(16, 2, 1000);
    stereo.addPcm(stereoBytes);
    near(stereo.gain(), targetRms / (0.5 / Math.sqrt(2)), 0.001,
      'channel samples must share the RMS denominator');

    var peakBytes = Bytes.alloc(500 * 2);
    peakBytes.set(0, 0x00);
    peakBytes.set(1, 0x80);
    var peakLimited = new SongAudioLoudness(16, 1, 10000);
    peakLimited.addPcm(peakBytes);
    near(peakLimited.gain(), 0.95, 0.00001, 'sample peak ceiling must limit gain');

    var quiet = new SongAudioLoudness(16, 1, 1000);
    quiet.addPcm(pcm16(1000, 50));
    check(quiet.gain() > 1, 'normalization should boost a quiet audible signal');
    var original = pcm16(1000, 50);
    var originalFirst = original.get(0);
    var scaled = quiet.applyGain(original, 0, original.length, quiet.gain());
    check(scaled != original && original.get(0) == originalFirst,
      'gain application must allocate a playback copy and leave the source buffer intact');
    near((scaled.get(0) | ((scaled.get(1) & 0xFF) << 8)) / 32768.0,
      targetRms, 0.001, 'scaled PCM target level');

    var unsigned8 = Bytes.alloc(100);
    for (i in 0...unsigned8.length) unsigned8.set(i, 255);
    var eightBit = new SongAudioLoudness(8, 1, 1000);
    eightBit.addPcm(unsigned8);
    near(eightBit.gain(), targetRms / (127.0 / 128.0), 0.001, 'unsigned 8-bit decode');
    var scaled8 = eightBit.applyGain(unsigned8, 0, unsigned8.length, eightBit.gain());
    check(unsigned8.get(0) == 255 && scaled8.get(0) < 255,
      '8-bit gain application must preserve source and scale unsigned PCM');

    expectFailure(function() new SongAudioLoudness(24, 2, 48000), 'unsupported bit depth');
    expectFailure(function() new SongAudioLoudness(16, 0, 48000), 'zero channels');
    expectFailure(function() new SongAudioLoudness(16, 2, 0), 'zero sample rate');
    expectFailure(function() new SongAudioLoudness(16, 1, 48000).addPcm(pcm16(1, 1), 0, 1),
      'non-sample-aligned PCM range');
    expectFailure(function() quiet.applyGain(original, 0, original.length, Math.NaN), 'non-finite gain');
  }
}
'''
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            (temp / "SongAudioLoudnessTestMain.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"), "-cp", folder,
                 "-main", "SongAudioLoudnessTestMain", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
