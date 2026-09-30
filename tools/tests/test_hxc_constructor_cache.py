"""Offscreen constructor sound cache boundary, with a stub native decoder."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


@unittest.skipUnless(HAXE.is_file(), "portable Haxe toolchain unavailable")
class HxcConstructorCacheTest(unittest.TestCase):
    def test_sound_decode_is_root_scoped_and_retained(self):
        with tempfile.TemporaryDirectory(prefix="hxc-constructor-cache-", dir=ROOT / "tmp") as folder:
            work = Path(folder)
            for name in ("one", "two"):
                sound = work / "assets/imported_mods" / name / "sounds/cue.ogg"
                sound.parent.mkdir(parents=True)
                sound.write_bytes(b"fixture")
            for index in range(33):
                (work / "assets/imported_mods/one/sounds" / f"extra{index}.ogg").write_bytes(b"fixture")
            (work / "FNFAssets.hx").write_text('''class FNFAssets {
  public static var calls:Array<String> = [];
  public static var imageCalls:Array<String> = [];
  public static function exists(path:String):Bool return sys.FileSystem.exists(path);
  public static function getSound(path:String):Dynamic {
    calls.push(path);
    return {path: path};
  }
  public static function getBitmapData(path:String):Dynamic {
    imageCalls.push(path);
    return {path: path};
  }
}
''')
            (work / "DynamicSound.hx").write_text('''class DynamicSound {
  public var embedded:Dynamic;
  public var volume:Float = 1;
  public function new() {}
  public function loadEmbedded(value:Dynamic, looped:Bool, autoDestroy:Bool, ?onComplete:Dynamic):Dynamic {
    embedded = value;
    return this;
  }
}
''')
            (work / "flixel").mkdir()
            (work / "flixel/FlxG.hx").write_text('''package flixel;
class FlxG {
  public static var sound:SoundSystem = new SoundSystem();
}
class SoundSystem {
  public var played:Dynamic;
  public function new() {}
  public function play(value:Dynamic, volume:Float):Dynamic {
    played = value;
    return value;
  }
}
''')
            (work / "CacheProbe.hx").write_text('''class CacheProbe {
  static function fail(message:String):Void throw message;
  static function main() {
    var nativeSound = flixel.FlxG.sound;
    var dynamicClass = DynamicSound;
    var one = HxcCompatRuntime.cacheFunkinSound("assets/imported_mods/one", "cue");
    var again = HxcCompatRuntime.cacheFunkinSound("assets/imported_mods/one", "cue");
    var two = HxcCompatRuntime.cacheFunkinSound("assets/imported_mods/two", "cue");
    if (one == null || two == null || one != again || one == two)
      fail("sound cache did not retain independent decoded objects");
    if (FNFAssets.calls.length != 2) fail("expected one decode per root");
    var played = HxcCompatRuntime.freeplayPlaySound("assets/imported_mods/one/sounds/cue.ogg");
    if (played != one || FNFAssets.calls.length != 2) fail("sound playback missed decoded cache");
    var loaded:Dynamic = HxcCompatRuntime.loadFunkinSound("assets/imported_mods/one", "cue");
    if (loaded == null || loaded.embedded != one || FNFAssets.calls.length != 2)
      fail("scoped FunkinSound load missed decoded cache");
    var fullPath:Dynamic = HxcCompatRuntime.loadFunkinSound("assets/imported_mods/one",
      "assets/imported_mods/one/sounds/cue.ogg");
    if (fullPath == null || fullPath.embedded != one || FNFAssets.calls.length != 2)
      fail("resolved Paths.sound path missed decoded cache");
    var foreign:Dynamic = HxcCompatRuntime.loadFunkinSound("assets/imported_mods/two",
      "assets/imported_mods/one/sounds/cue.ogg");
    if (foreign != null && foreign.embedded == one)
      fail("another root reused a cached sound");
    if (HxcCompatRuntime.cacheFunkinSound("assets/imported_mods/one", "../two/sounds/cue") != null
      || HxcCompatRuntime.cacheFunkinSound("assets", "cue") != null
      || HxcCompatRuntime.cacheFunkinSound("assets/imported_mods/one", "missing") != null)
      fail("invalid or missing sound crossed the root boundary");
    if (FNFAssets.calls.length != 2) fail("rejected sound was decoded");
    for (i in 0...33)
      HxcCompatRuntime.cacheFunkinSound("assets/imported_mods/one", "extra" + i);
    var before = FNFAssets.calls.length;
    HxcCompatRuntime.cacheFunkinSound("assets/imported_mods/one", "cue");
    if (FNFAssets.calls.length != before + 1) fail("oldest cache entry was not evicted");
    if (HxcCompatRuntime.cacheFunkinTexture("assets/imported_mods/one", "cue") != null
      || FNFAssets.imageCalls.length != 0)
      fail("image prewarm decoded a sound or used a fallback asset");
  }
}
''')
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(work),
                 "-main", "CacheProbe", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
