"""Psych same-tag construction retires the previous live object."""
import subprocess
import tempfile
import unittest
import re
from pathlib import Path

from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]


def extract_method(source, marker):
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        depth += (source[index] == "{") - (source[index] == "}")
        if depth == 0:
            return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class PsychTaggedObjectReplacementTest(unittest.TestCase):
    def test_all_tagged_constructors_replace_old_state_members(self):
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        methods = {
            "compatMakeLuaSprite": "function compatMakeLuaSprite(",
            "compatMakeLuaSpriteForOwner": "function compatMakeLuaSpriteForOwner(",
            "compatMakeAnimatedLuaSprite": "function compatMakeAnimatedLuaSprite(",
            "compatMakeAnimatedLuaSpriteForOwner": "function compatMakeAnimatedLuaSpriteForOwner(",
            "compatMakeLuaText": "function compatMakeLuaText(",
        }
        for name, marker in methods.items():
            body = extract_method(play_state, marker)
            cleanup = body.find("compatRemoveLuaSprite(tag)")
            constructors = [match.start() for match in re.finditer(r"new Flx(?:Sprite|Text)", body)]
            self.assertGreaterEqual(cleanup, 0, f"{name} does not clean an existing tag")
            self.assertTrue(constructors, f"{name} no longer constructs a tagged object")
            for constructor in constructors:
                previous_cleanup = body.rfind("compatRemoveLuaSprite(tag)", 0, constructor)
                self.assertGreaterEqual(previous_cleanup, 0, f"{name} cleans after construction")

        flx_animate = extract_method(play_state, "function compatMakeFlxAnimateSprite(")
        self.assertLess(flx_animate.find("compatRemoveLuaSprite(tag)"), flx_animate.find("new PsychModchartAnimateSprite"))

        extracted = "\n".join(extract_method(play_state, marker) for marker in (
            "function markPsychGlobalProviderSpritePhase(",
            "function compatMakeLuaSprite(",
            "function compatMakeLuaSpriteForOwner(",
            "function compatRemoveLuaSprite(",
        ))
        fixture = r'''import haxe.ds.Map;

class RuntimeSmokeHarness {
 public static function enabled():Bool return false;
 public static function markStep(_value:String):Void {}
}
class PsychGlobalPackImporter {
 public static function defaultProvider():String return '';
}
class FNFAssets {
 public static function exists(_path:String):Bool return false;
 public static function getBitmapData(_path:String):Dynamic return null;
}
class FlxSprite {
 public var x:Float;
 public var y:Float;
 public var alpha:Float = 1;
 public var graphic:Dynamic;
 public var destroyed:Bool = false;
 public function new(x:Float = 0, y:Float = 0) { this.x = x; this.y = y; }
 public function loadGraphic(value:Dynamic):FlxSprite { graphic = value; return this; }
 public function destroy():Void destroyed = true;
}
class Fixture {
 var haxeSprites:Map<String, FlxSprite> = new Map();
 var haxeSpriteAtlasNames:Map<String, String> = new Map();
 var members:Array<Dynamic> = [];
 var psychGlobalProviderSpriteMarked:Bool = false;
 var psychGlobalProviderFirstSpriteTag:String = '';
 var psychGlobalProviderFirstSprite:Dynamic = null;
 var endingSong:Bool = false;
 var canPause:Bool = true;

 public function new() {}
 function compatForgetSpriteAtlas(_sprite:Dynamic):Void {}
 function compatPsychOwnerFallbackAllowed(_owner:String, _reference:String):Bool return true;
 function compatPsychAssetKey(value:String, _extension:String):String return value;
 function compatPsychPathCall(_owner:String, _method:String, _args:Array<Dynamic>):Dynamic return {owner: _owner};
 function remove(sprite:Dynamic, splice:Bool):Dynamic {
  if (splice) members.remove(sprite);
  return sprite;
 }
''' + extracted + r'''

 static function check(ok:Bool, message:String):Void {
  if (!ok) throw 'assertion failed: ' + message;
 }
 public static function main():Void {
  var harness = new Fixture();
  var previous = new FlxSprite(0, 0);
  harness.haxeSprites.set('funnyIcon', previous);
  harness.haxeSpriteAtlasNames.set('funnyIcon', 'old-atlas');
  harness.members.push(previous);

  var current = harness.compatMakeLuaSpriteForOwner('song-owner', 'funnyIcon', 'icons/icon-greenWiz', 0, 590);
  check(previous.destroyed, 'same-tag replacement did not destroy the prior sprite');
  check(harness.members.length == 0, 'same-tag replacement left prior sprite in the state');
  check(harness.haxeSprites.get('funnyIcon') == current, 'tag registry does not point to replacement');
  check(!harness.haxeSpriteAtlasNames.exists('funnyIcon'), 'stale atlas-name cache survived replacement');
  harness.members.push(current);

  var later = harness.compatMakeLuaSpriteForOwner('song-owner', 'funnyIcon', 'icons/icon-shadWiz', 0, 590);
  check(current.destroyed, 'a second replacement did not destroy the previous live sprite');
  check(harness.members.length == 0, 'a second replacement left a stale rendered sprite');
  check(harness.haxeSprites.get('funnyIcon') == later, 'second replacement did not own the tag');
  harness.members.push(later);
  check(harness.members.length == 1 && harness.members[0] == later,
   'only the current tagged sprite remains in state members after re-add');

  var unowned = harness.compatMakeLuaSprite('funnyIcon', '', 0, 590);
  check(later.destroyed && harness.members.length == 0,
   'unowned static constructor did not retire the current tagged sprite');
  check(harness.haxeSprites.get('funnyIcon') == unowned, 'unowned constructor did not register replacement');
 }
}'''
        with tempfile.TemporaryDirectory(prefix="psych-tag-replacement-") as temp_dir:
            temp = Path(temp_dir)
            (temp / "Fixture.hx").write_text(fixture, encoding="utf-8")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(temp), "-main", "Fixture", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
