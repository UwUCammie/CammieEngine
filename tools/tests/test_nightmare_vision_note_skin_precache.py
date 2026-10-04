"""Pin NMV's owner-scoped noteskin effect atlas prewarm defaults."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from tools.tests.test_psych_character_scope import extract_method


ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionNoteSkinPrecacheTest(unittest.TestCase):
    def test_effect_atlases_use_donor_defaults_and_owner_paths(self):
        source = (ROOT / "source/NightmareVisionNoteSkin.hx").read_text()
        methods = "\n".join(extract_method(source, marker) for marker in (
            "public function precacheEffects(",
            "function effectTexture(",
        ))
        self.assertIn("DEFAULT_SPLASH_TEXTURE:String = 'UI/notes/noteSplashes'", source)
        self.assertIn("DEFAULT_SUSTAIN_SPLASH_TEXTURE:String = 'UI/notes/sustainHold'", source)
        self.assertIn("stringField('splashTexture', DEFAULT_SPLASH_TEXTURE)", source)

        fixture = r'''class FlxAtlasFrames {
 public var key:String;
 public function new(key:String) this.key=key;
}
class NightmareVisionPaths {
 public var root:String;
 public var requests:Array<String>=[];
 public function new(root:String) this.root=root;
 public function getSparrowAtlas(key:String):FlxAtlasFrames {
  requests.push(root+":"+key);
  return new FlxAtlasFrames(key);
 }
}
class NightmareVisionNoteSkin {
 public static inline var DEFAULT_SPLASH_TEXTURE:String="UI/notes/noteSplashes";
 public static inline var DEFAULT_SUSTAIN_SPLASH_TEXTURE:String="UI/notes/sustainHold";
 public var data:Dynamic;
 public var paths:NightmareVisionPaths;
 public var splashFrames:FlxAtlasFrames;
 public var effectsPrecached:Bool=false;
 public function new(paths:NightmareVisionPaths,data:Dynamic) {this.paths=paths;this.data=data;}
''' + methods + r'''
}
class Main {
 static function check(value:Bool,message:String):Void if(!value)throw message;
 static function main():Void {
  var corePaths=new NightmareVisionPaths("owner-core");
  var absent=new NightmareVisionNoteSkin(corePaths,{});
  absent.precacheEffects();
  check(corePaths.requests.join("|")=="owner-core:UI/notes/noteSplashes|owner-core:UI/notes/sustainHold",
   "missing fields did not warm the donor's two default atlases through the owner paths");
  check(absent.splashFrames.key=="UI/notes/noteSplashes" && absent.effectsPrecached,
   "the splash atlas was not retained for the first splash or the prewarm was not marked");
  absent.precacheEffects();
  check(corePaths.requests.length==2,"repeated preparation warmed the same skin more than once");

  var customPaths=new NightmareVisionPaths("owner-custom");
  var custom=new NightmareVisionNoteSkin(customPaths,
   {splashTexture:"effects/customSplash",sustainSplashTexture:"effects/customHold"});
  custom.precacheEffects();
  check(customPaths.requests.join("|")=="owner-custom:effects/customSplash|owner-custom:effects/customHold",
   "authored effect atlas paths were replaced or resolved outside the skin owner");

  var nullablePaths=new NightmareVisionPaths("owner-null");
  var nullable=new NightmareVisionNoteSkin(nullablePaths,
   {splashTexture:null,sustainSplashTexture:null});
  nullable.precacheEffects();
  check(nullablePaths.requests.join("|")=="owner-null:UI/notes/noteSplashes|owner-null:UI/notes/sustainHold",
   "explicit null fields did not use the donor defaults");

  var blankPaths=new NightmareVisionPaths("owner-blank");
  var blank=new NightmareVisionNoteSkin(blankPaths,{splashTexture:"",sustainSplashTexture:""});
  blank.precacheEffects();
  check(blankPaths.requests.join("|")=="owner-blank:|owner-blank:",
   "empty authored values should retain the donor's null-only default semantics");
 }
}
'''
        with tempfile.TemporaryDirectory(prefix="nmv-note-skin-precache-", dir=ROOT / "tmp") as scratch:
            (Path(scratch) / "Main.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(scratch), "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
