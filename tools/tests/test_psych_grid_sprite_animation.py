"""Execute Psych grid-sprite and numeric-frame animation helpers in isolation."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


FIXTURE = r'''import sys.FileSystem;

class PsychOwnerPaths {
  public static var requests:Array<String> = [];
  public static function create(owner:String):Dynamic {
    var proxy:Dynamic = {};
    Reflect.setField(proxy, 'image', function(key:String):Dynamic {
      requests.push(owner + '|' + key);
      return FNFAssets.getBitmapData(owner + '/images/' + key + '.png');
    });
    return proxy;
  }
}

class FakeAnimation {
  public var curAnim:Dynamic;
  public var adds:Array<Dynamic> = [];
  public var plays:Array<Dynamic> = [];
  public function new(?current:Dynamic) curAnim = current;
  public function add(name:String, frames:Array<Int>, fps:Float, looped:Bool):Void
    adds.push({name:name, frames:frames.copy(), fps:fps, looped:looped});
  public function play(name:String, force:Bool = false):Void {
    plays.push({name:name, force:force});
    curAnim = {name:name};
  }
}

class FlxSprite {
  public var animation:FakeAnimation;
  public var loadCalls:Array<Dynamic> = [];
  public function new(?animation:FakeAnimation) this.animation = animation;
  public function loadGraphic(graphic:Dynamic, animated:Bool = false,
      frameWidth:Int = 0, frameHeight:Int = 0):FlxSprite {
    loadCalls.push({graphic:graphic, animated:animated,
      frameWidth:frameWidth, frameHeight:frameHeight});
    return this;
  }
}

class Main {
  var objects:Map<String, Dynamic> = new Map();
  var haxeSpriteAtlasNames:Map<String, Array<String>> = new Map();
  var haxeSpriteAtlasNamesByObject:Map<FlxSprite, Array<String>> = new Map();

  public function new() {}

  function compatPropertyRoot(name:String):Dynamic return objects.get(name);

__EXTRACTED_METHODS__

  static function check(value:Bool, message:String):Void if (!value) throw message;

  function testAnimationRegistration():Void {
    var firstAnimation = new FakeAnimation();
    var first = new FlxSprite(firstAnimation);
    objects.set('grid', first);
    check(compatAddAnimation('grid', 'full', '0, 2, 5, 11'),
      'numeric frame animation registration failed');
    check(firstAnimation.adds.length == 1, 'animation was not registered exactly once');
    var added = firstAnimation.adds[0];
    check(added.name == 'full' && added.fps == 24 && added.looped == true,
      'Psych defaults for fps/looped changed');
    check(added.frames.join(',') == '0,2,5,11',
      'numeric frame ids were lost or reordered: ' + added.frames.join(','));
    check(firstAnimation.plays.length == 1 && firstAnimation.plays[0].name == 'full'
      && firstAnimation.plays[0].force == true,
      'newly registered animation did not autoplay when no animation was active');

    var prior = {name:'already-playing'};
    var secondAnimation = new FakeAnimation(prior);
    var second = new FlxSprite(secondAnimation);
    objects.set('existing', second);
    check(compatAddAnimation('existing', 'idle', [1, 4, 9], '31', false),
      'explicit numeric-frame animation registration failed');
    var secondAdded = secondAnimation.adds[0];
    check(secondAdded.fps == 31 && secondAdded.looped == false
      && secondAdded.frames.join(',') == '1,4,9',
      'explicit animation options or frame ids were not preserved');
    check(secondAnimation.curAnim == prior && secondAnimation.plays.length == 0,
      'registering an animation replaced or replayed an existing animation');

    var fractionalAnimation = new FakeAnimation();
    objects.set('fractional', new FlxSprite(fractionalAnimation));
    check(compatAddAnimation('fractional', 'slow', [0, 2], 12.5),
      'fractional numeric-frame animation registration failed');
    check(fractionalAnimation.adds[0].fps == 12.5,
      'fractional fps 12.5 was not preserved');
    check(compatAddAnimation('fractional', 'very-slow', [1], 0.5),
      'sub-one fractional animation registration failed');
    check(fractionalAnimation.adds[1].fps == 0.5,
      'fractional fps 0.5 was not preserved');

    var invalidAnimation = new FakeAnimation();
    objects.set('invalid-fps', new FlxSprite(invalidAnimation));
    check(compatAddAnimation('invalid-fps', 'fallback', [3], true, false),
      'invalid fps fallback animation registration failed');
    check(invalidAnimation.adds[0].fps == 24 && invalidAnimation.adds[0].looped == false,
      'invalid fps did not use 24 while preserving looped');
  }

  function testOwnedGraphicAndGrid():Void {
    FNFAssets.clear();
    PsychOwnerPaths.requests = [];
    var owner = 'assets/imported_mods/owner-a';
    var graphicA:Dynamic = {owner:'owner-a'};
    var graphicB:Dynamic = {owner:'owner-b'};
    FNFAssets.put(owner + '/images/sprites/grid.png', graphicA);
    FNFAssets.put('assets/imported_mods/owner-b/images/sprites/grid.png', graphicB);
    var sprite = new FlxSprite(new FakeAnimation());
    objects.set('owner-grid', sprite);
    haxeSpriteAtlasNames.set('owner-grid', ['stale atlas entry']);
    haxeSpriteAtlasNamesByObject.set(sprite, ['stale object atlas entry']);

    compatLoadGraphicForOwner(owner, 'owner-grid', 'sprites/grid.png', 0, 16);

    check(sprite.loadCalls.length == 1, 'selected-owner image was not loaded once');
    var call = sprite.loadCalls[0];
    check(call.graphic == graphicA, 'image resolution escaped the calling Psych owner');
    check(call.animated == true && call.frameWidth == 0 && call.frameHeight == 16,
      'grid load did not enable animation with authored cell dimensions');
    check(PsychOwnerPaths.requests.join('|') == owner + '|sprites/grid',
      'image resolver did not receive the calling owner and normalized key');
    check(!haxeSpriteAtlasNames.exists('owner-grid')
      && !haxeSpriteAtlasNamesByObject.exists(sprite),
      'loading a grid graphic retained stale atlas metadata');

    var foreign = new FlxSprite();
    objects.set('foreign', foreign);
    compatLoadGraphicForOwner(owner, 'foreign',
      'assets/imported_mods/owner-b/images/sprites/grid.png', 16, 0);
    compatLoadGraphicForOwner(owner, 'foreign', '../outside/grid.png', 16, 0);
    check(foreign.loadCalls.length == 0,
      'foreign or traversal source reference reached FlxSprite.loadGraphic');
    check(PsychOwnerPaths.requests.length == 1,
      'unsafe source reference reached the selected-owner image resolver');
  }

  function testMissingAssetsAndUnownedFallback():Void {
    FNFAssets.clear();
    var missing = new FlxSprite();
    objects.set('missing', missing);
    compatLoadGraphicForOwner('assets/imported_mods/owner-a', 'missing', 'not-present', 8, 8);
    compatLoadGraphicForOwner(null, 'missing', 'not-present', 8, 8);
    check(missing.loadCalls.length == 0, 'missing image asset changed the sprite');

    var fallback = new FlxSprite();
    objects.set('fallback', fallback);
    var sharedGraphic:Dynamic = {owner:'native-shared'};
    FNFAssets.put('assets/images/shared-sheet.png', sharedGraphic);
    compatLoadGraphicForOwner(null, 'fallback', 'shared-sheet', 0, 0);
    check(fallback.loadCalls.length == 1 && fallback.loadCalls[0].graphic == sharedGraphic,
      'unowned script lost legacy shared image lookup');
    check(fallback.loadCalls[0].animated == false
      && fallback.loadCalls[0].frameWidth == 0 && fallback.loadCalls[0].frameHeight == 0,
      'ordinary image load incorrectly enabled grid animation');
  }

  static function main():Void {
    var fixture = new Main();
    fixture.testAnimationRegistration();
    fixture.testOwnedGraphicAndGrid();
    fixture.testMissingAssetsAndUnownedFallback();
    Sys.println('ok');
  }
}
'''


class PsychGridSpriteAnimationTest(unittest.TestCase):
    def test_extracted_helpers_execute_numeric_frames_and_owner_grid_loads(self):
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        method_markers = (
            "public static function compatNormalizeAnimationIndices",
            "function compatAddAnimation(",
            "function compatFindObject(",
            "function compatForgetSpriteAtlas(",
            "function compatLoadGraphic(",
            "function compatLoadGraphicForOwner(",
            "function compatPsychPathCall(",
            "function compatPsychOwnerFallbackAllowed(",
            "function compatPsychAssetKey(",
        )
        methods = "\n".join(extract_method(play_state, marker) for marker in method_markers)
        fixture = FIXTURE.replace("__EXTRACTED_METHODS__", methods)

        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            (work / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            (work / "CompatScriptManifest.hx").write_text(
                "class CompatScriptManifest { public static inline var ROOT_PREFIX:String = 'assets/imported_mods'; }\n",
                encoding="utf-8", newline="\n",
            )
            (work / "RuntimeOwnerAssetIdentity.hx").write_text('''
typedef RuntimeOwnerAssetIdentityResult = { var state:String; var path:Null<String>; };
class RuntimeOwnerAssetIdentity {
 public static function lookup(_owner:String, _engine:String, _scope:String,
     _id:String, ?_expectedType:String):RuntimeOwnerAssetIdentityResult
  return {state:'no-index', path:null};
 public static function releaseOwner(_owner:String):Void {}
}
''', encoding="utf-8", newline="\n")
            (work / "FNFAssets.hx").write_text(r'''import sys.FileSystem;
class FNFAssets {
  static var assets:Map<String, Dynamic> = new Map();
  public static function clear():Void assets = new Map();
  public static function put(path:String, value:Dynamic):Void assets.set(path, value);
  public static function exists(path:String):Bool return assets.exists(path);
  public static function getBitmapData(path:String):Dynamic return assets.get(path);
  public static function resolveCaseInsensitivePath(path:String):String
    return FileSystem.exists(path) ? path : null;
}
''', encoding="utf-8", newline="\n")
            (work / "PsychOwnerAssetPath.hx").write_text(
                (ROOT / "source/PsychOwnerAssetPath.hx").read_text(encoding="utf-8"),
                encoding="utf-8", newline="\n",
            )
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "ok")

    def test_adapter_bindings_and_importer_whitelist_include_both_calls(self):
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        self.assertIn("interp.variables.set('addAnimation', compatAddAnimation);", play_state)
        self.assertIn("interp.variables.set('loadGraphic', function(name:Dynamic, image:String, gridX:Int = 0, gridY:Int = 0)",
                      play_state)
        self.assertIn("compatLoadGraphicForOwner(psychScriptOwner, name, image, gridX, gridY)", play_state)

        engine_compat = (ROOT / "source/EngineCompat.hx").read_text(encoding="utf-8")
        whitelist = extract_method(engine_compat, "public static function knownScriptFunction(").lower()
        self.assertIn("'addanimation'", whitelist)
        self.assertIn("'loadgraphic'", whitelist)


if __name__ == "__main__":
    unittest.main()
