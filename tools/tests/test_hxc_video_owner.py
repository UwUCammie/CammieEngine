"""Execute the HXC video resolver against two installed import owners."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

from tools.tests.test_psych_character_scope import extract_method

ROOT = Path(__file__).resolve().parents[2]


class HxcVideoOwnerTest(unittest.TestCase):
    def test_selected_owner_cannot_play_sibling_or_symlinked_video(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        resolver = extract_method(source, "public function hxcResolveImportedVideoPath(")
        fixture = '''import haxe.io.Path;
import sys.FileSystem;
using StringTools;
class FNFAssets {
 public static function exists(path:String):Bool return FileSystem.exists(path);
 public static function isInScope(path:String):Bool return true;
}
class CompatScriptManifest {
 public static function selectedRoot(_manifest:Dynamic):String return "assets/imported_mods/owner-a";
}
class Main {
 public function new() {}
 public function getCompatScriptManifest():Dynamic return {};
''' + resolver + '''
 static function check(value:Bool, reason:String):Void if (!value) throw reason;
 static function main():Void {
  var owner="assets/imported_mods/owner-a";
  var state=new Main();
  check(state.hxcResolveImportedVideoPath(owner+"/videos/clip.mp4", owner)
   ==owner+"/videos/clip.mp4", "selected owner clip missing");
  check(state.hxcResolveImportedVideoPath("assets/imported_mods/owner-b/videos/clip.mp4", owner)
   ==null, "sibling owner video was borrowed");
  check(state.hxcResolveImportedVideoPath(owner+"/videos/escape.mp4", owner)
   ==null, "symlink escaped selected owner");
  check(state.hxcResolveImportedVideoPath(owner+"/videos/../videos/clip.mp4", owner)
   ==null, "traversal was accepted");
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            base = Path(scratch)
            a = base / "assets/imported_mods/owner-a/videos"
            b = base / "assets/imported_mods/owner-b/videos"
            a.mkdir(parents=True)
            b.mkdir(parents=True)
            (a / "clip.mp4").write_bytes(b"a")
            (b / "clip.mp4").write_bytes(b"b")
            (a / "escape.mp4").symlink_to(b / "clip.mp4")
            (base / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                                     "-cp", str(base), "-main", "Main", "--interp"],
                                    cwd=base, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
