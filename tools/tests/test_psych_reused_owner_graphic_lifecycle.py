"""Exercise same-tag owner sprite replacement through translated Psych Lua."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND


ROOT = Path(__file__).resolve().parents[2]
HAXESCRIPT = ROOT / ".haxelib/hscript/2,5,0"
DONOR_SCRIPT = (
    ROOT.parent
    / "fnf_example_mods/psych/shadow_wizard_money_gang_we_love_casting_spells/"
    / "Shadow Wizard Money Gang, We Love Casting Spells/custom_events/subtitlesFNF.lua"
)


def extract_method(source, marker):
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        depth += (source[index] == "{") - (source[index] == "}")
        if depth == 0:
            return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


FIXTURE = r'''import LuaCompat;
import LuaCompatInterp;

class FakeBitmap {
  public var width:Int = 300;
  public var height:Int = 150;
  public function new() {}
}

class FakeGraphic {
  public var key:String;
  public var bitmap:FakeBitmap = new FakeBitmap();
  public var useCount:Int = 0;
  public var destroyed:Bool = false;
  public function new(key:String) this.key = key;
  public function destroy():Void {
    destroyed = true;
    bitmap.width = 0;
    bitmap.height = 0;
  }
}

class FNFAssets {
  static var cache:Map<String, FakeGraphic> = new Map();
  public static var created:Array<FakeGraphic> = [];
  public static function clear():Void {
    cache = new Map();
    created = [];
  }
  public static function exists(_path:String):Bool return false;
  public static function getBitmapData(_path:String):Dynamic return null;
  public static function getFlxGraphic(path:String):FakeGraphic {
    var graphic = cache.get(path);
    if (graphic == null || graphic.destroyed) {
      graphic = new FakeGraphic(path);
      cache.set(path, graphic);
      created.push(graphic);
    }
    return graphic;
  }
  public static function release(graphic:FakeGraphic):Void {
    if (graphic.useCount <= 0 && !graphic.destroyed) {
      graphic.destroy();
      if (cache.get(graphic.key) == graphic) cache.remove(graphic.key);
    }
  }
}

class PsychOwnerPaths {
  public static function create(owner:String):Dynamic {
    var proxy:Dynamic = {};
    Reflect.setField(proxy, 'image', function(key:String):Dynamic
      return FNFAssets.getFlxGraphic(owner + '/images/' + key + '.png'));
    return proxy;
  }
}

class PsychOwnerAssetPath {
  public static function ownerReferenceAllowed(_owner:String, _path:String):Bool return true;
}
class CompatScriptManifest { public static inline var ROOT_PREFIX:String = 'assets/imported_mods'; }
class RuntimeSmokeHarness {
  public static function enabled():Bool return false;
  public static function markStep(_value:String):Void {}
}
class PsychGlobalPackImporter {
  public static function defaultProvider():String return '';
}

class FlxSprite {
  public var x:Float;
  public var y:Float;
  public var alpha:Float = 1;
  public var graphic:FakeGraphic;
  public var width:Float = 0;
  public var height:Float = 0;
  public var frameWidth:Int = 0;
  public var frameHeight:Int = 0;
  public var frameCount:Int = 0;
  public var destroyed:Bool = false;
  public function new(x:Float = 0, y:Float = 0) { this.x = x; this.y = y; }
  public function loadGraphic(value:Dynamic, animated:Bool = false,
      requestedWidth:Int = 0, requestedHeight:Int = 0):FlxSprite {
    var next:FakeGraphic = cast value;
    if (graphic != next) {
      releaseGraphic();
      graphic = next;
      if (graphic != null) graphic.useCount++;
    }
    if (graphic == null || graphic.destroyed || graphic.bitmap == null) {
      width = 0; height = 0; frameWidth = 0; frameHeight = 0; frameCount = 1;
      return this;
    }
    if (animated && (requestedWidth > 0 || requestedHeight > 0)) {
      frameWidth = requestedWidth > 0 ? requestedWidth : graphic.bitmap.width;
      frameHeight = requestedHeight > 0 ? requestedHeight : graphic.bitmap.height;
      width = frameWidth; height = frameHeight;
      frameCount = Std.int(graphic.bitmap.width / frameWidth)
        * Std.int(graphic.bitmap.height / frameHeight);
    } else {
      frameWidth = graphic.bitmap.width;
      frameHeight = graphic.bitmap.height;
      width = graphic.bitmap.width; height = graphic.bitmap.height; frameCount = 1;
    }
    return this;
  }
  function releaseGraphic():Void {
    if (graphic == null) return;
    graphic.useCount--;
    FNFAssets.release(graphic);
    graphic = null;
  }
  public function destroy():Void {
    if (destroyed) return;
    destroyed = true;
    releaseGraphic();
  }
}

class Fixture {
  var haxeSprites:Map<String, FlxSprite> = new Map();
  var haxeSpriteAtlasNames:Map<String, String> = new Map();
  var haxeSpriteAtlasNamesByObject:Map<FlxSprite, Array<String>> = new Map();
  var members:Array<Dynamic> = [];
  var psychGlobalProviderSpriteMarked:Bool = false;
  var psychGlobalProviderFirstSpriteTag:String = '';
  var psychGlobalProviderFirstSprite:Dynamic = null;
  var endingSong:Bool = false;
  var canPause:Bool = true;
  public function new() {}
  function compatPropertyRoot(name:String):Dynamic return haxeSprites.get(name);
  function compatPsychOwnerFallbackAllowed(_owner:String, _reference:String):Bool return true;
  function compatPsychAssetKey(value:String, extension:String):String {
    return StringTools.endsWith(value.toLowerCase(), extension)
      ? value.substr(0, value.length - extension.length) : value;
  }
  function compatPsychPathCall(owner:String, method:String, args:Array<Dynamic>):Dynamic {
    if (method != 'image') return null;
    var paths = PsychOwnerPaths.create(owner);
    return Reflect.callMethod(paths, Reflect.field(paths, 'image'), args);
  }
  function remove(sprite:Dynamic, splice:Bool):Dynamic {
    if (splice) members.remove(sprite);
    return sprite;
  }
  function markPsychGlobalProviderSpritePhase(_sprite:Dynamic, _phase:String, ?_detail:String):Void {}

__EXTRACTED_METHODS__

  static function check(value:Bool, message:String):Void if (!value) throw message;

  function testTranslatedReuse():Void {
    FNFAssets.clear();
    var owner = 'assets/imported_mods/owner-a';
    var source = sys.io.File.getContent('repro.lua');
    var translated = LuaCompat.translate(source, 'subtitlesFNF.lua');
    check(translated.supported, 'real donor helper did not translate: ' + translated.diagnostics.join(' | '));

    var interp = new LuaCompatInterp();
    interp.variables.set('makeLuaSprite', function(tag:String, image:String, x:Float, y:Float):Void {
      compatMakeLuaSpriteForOwner(owner, tag, image, x, y);
    });
    interp.variables.set('getProperty', function(path:String):Dynamic {
      var parts = path.split('.');
      var object = haxeSprites.get(parts[0]);
      if (object == null || parts.length < 2) return null;
      return parts[1] == 'width' ? object.width : parts[1] == 'height' ? object.height : null;
    });
    interp.variables.set('loadGraphic', function(name:String, image:String,
        gridWidth:Int = 0, gridHeight:Int = 0):Void {
      compatLoadGraphicForOwner(owner, name, image, gridWidth, gridHeight);
    });
    interp.variables.set('setProperty', function(_path:String, _value:Dynamic):Void {});
    interp.variables.set('addAnimation', function(_tag:String, _name:String,
        _frames:Array<Int>, _looped:Bool):Void {});
    interp.variables.set('playAnim', function(_tag:String, _name:String):Void {});
    interp.variables.set('setObjectCamera', function(_tag:String, _camera:String):Void {});
    interp.variables.set('addLuaSprite', function(_tag:String):Void {});
    interp.execute(new hscript.Parser().parseString(translated.hscript));

    var current = haxeSprites.get('funnyIcon');
    check(current != null && !current.destroyed, 'repeated donor call lost the current sprite');
    check(current.frameWidth == 150 && current.frameHeight == 150 && current.frameCount == 2,
      'reused icon stayed unchopped after the previous sprite released the cached graphic: '
        + current.frameWidth + 'x' + current.frameHeight + ' count=' + current.frameCount);
    check(FNFAssets.created.length == 2,
      'the last-use cache entry was not reloaded after same-tag sprite destruction');
    check(FNFAssets.created[0].destroyed && !FNFAssets.created[1].destroyed,
      'same-image replacement did not retire then replace the released graphic');
  }

  public static function main():Void {
    var fixture = new Fixture();
    fixture.testTranslatedReuse();
    Sys.println('ok');
  }
}
'''


class PsychReusedOwnerGraphicLifecycleTest(unittest.TestCase):
    @unittest.skipUnless(DONOR_SCRIPT.is_file(), "pinned Psych donor checkout is unavailable")
    def test_real_translated_subtitle_helper_reloads_graphic_after_last_use_release(self):
        donor = DONOR_SCRIPT.read_text(encoding="utf-8")
        start = donor.index("function makeLuaIcon(")
        end = donor.index("\nend", start) + len("\nend")
        source = donor[start:end] + "\n"
        source += "makeLuaIcon('funnyIcon', 'icons/icon-shadWiz', 0, 590)\n"
        source += "makeLuaIcon('funnyIcon', 'icons/icon-shadWiz', 0, 590)\n"

        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        markers = (
            "function compatFindObject(",
            "function compatForgetSpriteAtlas(",
            "function compatLoadGraphic(",
            "function compatMakeLuaSprite(",
            "function compatMakeLuaSpriteForOwner(",
            "function compatRemoveLuaSprite(",
            "function compatLoadGraphicForOwner(",
        )
        methods = "\n".join(extract_method(play_state, marker) for marker in markers)
        fixture = FIXTURE.replace("__EXTRACTED_METHODS__", methods)

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            (temp / "Fixture.hx").write_text(fixture, encoding="utf-8", newline="\n")
            (temp / "repro.lua").write_text(source, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(HAXESCRIPT),
                 "-cp", str(temp), "-main", "Fixture", "--interp"],
                cwd=temp, capture_output=True, text=True, timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "ok")


if __name__ == "__main__":
    unittest.main()
