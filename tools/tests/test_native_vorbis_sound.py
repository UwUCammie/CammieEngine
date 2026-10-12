"""Shared local Vorbis streaming preserves fallbacks and owns failed opens."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
ROOT = Path(__file__).resolve().parents[2]

class NativeVorbisSoundTest(unittest.TestCase):
    def test_stream_instances_fallbacks_and_failed_open_cleanup(self):
        with tempfile.TemporaryDirectory(prefix="vorbis-loader-", dir=ROOT / "tmp") as folder:
            root = FixturePath(folder)
            files = {
                "openfl/media/Sound.hx": r'''package openfl.media;
class Sound {
 public static var mode:Int = 0;
 public var buffer:lime.media.AudioBuffer;
 public function new(buffer) this.buffer = buffer;
 public static function fromAudioBuffer(buffer:lime.media.AudioBuffer):Sound {
  if (mode == 1) return null;
  if (mode == 2) throw "sound failure";
  return new Sound(buffer);
 }
}''',
                "lime/media/AudioBuffer.hx": r'''package lime.media;
class AudioBuffer {
 public static var mode:Int = 0;
 public var file:lime.media.vorbis.VorbisFile;
 public function new(file) this.file = file;
 public static function fromVorbisFile(file:lime.media.vorbis.VorbisFile):AudioBuffer {
  if (mode == 1) return null;
  if (mode == 2) throw "buffer failure";
  return new AudioBuffer(file);
 }
}''',
                "lime/media/vorbis/VorbisFile.hx": r'''package lime.media.vorbis;
class VorbisFile {
 public static var opens:Int = 0;
 public static var closes:Int = 0;
 public static var mode:Int = 0;
 public function new() {}
 public static function fromFile(path:String):VorbisFile {
  opens++;
  if (mode == 1) return null;
  if (mode == 2) throw "open failure";
  return new VorbisFile();
 }
 public function clear():Void closes++;
}''',
                "Main.hx": r'''import lime.media.vorbis.VorbisFile;
import lime.media.AudioBuffer;
import openfl.media.Sound;
class Main {
 static function check(ok:Bool,message:String):Void if (!ok) throw message;
 static function main():Void {
  var path = "music.OGG";
  check(NativeVorbisSound.load(null) == null,"null fallback");
  check(NativeVorbisSound.load("music.wav") == null,"other formats fallback");
  check(NativeVorbisSound.load("missing.ogg") == null,"missing fallback");
  check(NativeVorbisSound.load("directory.ogg") == null,"directory fallback");
  check(VorbisFile.opens == 0,"invalid paths are never opened");
  #if lime_vorbis
  var a = NativeVorbisSound.load(path);
  var b = NativeVorbisSound.load(path);
  check(a != null && b != null && a.buffer.file != b.buffer.file,"separate playback cursors");
  check(VorbisFile.closes == 0,"successful stream remains alive for playback");
  for (mode in 1...3) {
   AudioBuffer.mode = mode;
   check(NativeVorbisSound.load(path) == null,"failed buffer falls back");
  }
  AudioBuffer.mode = 0;
  for (mode in 1...3) {
   Sound.mode = mode;
   check(NativeVorbisSound.load(path) == null,"failed sound falls back");
  }
  Sound.mode = 0;
  check(VorbisFile.closes == 4,"every partially opened stream closed exactly once");
  for (mode in 1...3) {
   VorbisFile.mode = mode;
   check(NativeVorbisSound.load(path) == null,"failed open falls back");
  }
  check(VorbisFile.closes == 4,"failed opens have no owned stream to close");
  #else
  check(NativeVorbisSound.load(path) == null,"unsupported platform uses ordinary loader");
  check(VorbisFile.opens == 0,"unsupported platform never opens stream");
  #end
 }
}'''
            }
            for name, content in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            (root / "music.OGG").write_bytes(b"fixture")
            (root / "music.wav").write_bytes(b"fixture")
            (root / "directory.ogg").mkdir()
            for defines in ([], ["-D", "lime_vorbis"]):
                result = subprocess.run([*HAXE_COMMAND,"-cp",str(ROOT / "source"),"-cp",str(root),*defines,"--main","Main","--interp"],cwd=str(root),capture_output=True,text=True,timeout=60)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__ == "__main__":
    unittest.main()
