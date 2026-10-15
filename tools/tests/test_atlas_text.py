"""V-Slice AtlasText as a base-game class: owner fonts first, the engine alphabet when a font is missing."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

STUBS = {
    'flixel/graphics/frames/FlxAtlasFrames.hx': '''package flixel.graphics.frames;
class Rect { public var height:Float; public function new(h:Float) height = h; }
class Frame { public var name:String; public var frame:Rect; public function new(n:String, h:Float) { name = n; frame = new Rect(h); } }
class Parent { public var destroyOnNoUse = true; public var persist = false; public var bitmap:Dynamic = 'bitmap'; public function new() {} }
class FlxAtlasFrames {
 public static var loaded:Array<String> = [];
 public var frames:Array<Frame> = [];
 public var parent = new Parent();
 public function new(names:Array<String>, height:Float) for (n in names) frames.push(new Frame(n + '0000', height));
 public static function fromSparrow(png:Dynamic, xml:Dynamic):FlxAtlasFrames {
  loaded.push(png);
  return new FlxAtlasFrames(['A bold', 'B bold', 'H bold', 'I bold', 'a lowercase', 'A capital', 'J captial', 'period bold'], 70);
 }
}''',
    'flixel/FlxSprite.hx': '''package flixel;
class Anim { public var name:String; public var prefix:String; public function new(n, p) { name = n; prefix = p; } }
class Animation {
 public var owner:FlxSprite; public var anims:Map<String, Anim> = []; public var current:String;
 public function new(o) owner = o;
 public function addByPrefix(name:String, prefix:String, fps:Int):Void {
  if (owner.frames == null) return;
  for (f in owner.frames.frames) if (StringTools.startsWith(f.name, prefix)) { anims.set(name, new Anim(name, prefix)); return; }
 }
 public function exists(name:String):Bool return anims.exists(name);
 public function remove(name:String):Void anims.remove(name);
 public function play(name:String, force:Bool = false):Void current = anims.get(name).prefix;
}
class FlxSprite {
 public var x:Float = 0; public var y:Float = 0; public var width:Float = 0; public var height:Float = 0;
 public var alpha:Float = 1; public var alive = true; public var exists = true;
 public var frames(default, set):flixel.graphics.frames.FlxAtlasFrames;
 public var animation:Animation;
 public function new(x:Float = 0, y:Float = 0) { this.x = x; this.y = y; animation = new Animation(this); }
 function set_frames(f) return frames = f;
 public function updateHitbox():Void { width = animation.current == null ? 0 : 50; height = animation.current == null ? 0 : 60; }
 public function revive():Void { alive = true; exists = true; }
 public function kill():Void { alive = false; exists = false; }
 public function destroy():Void {}
}''',
    'flixel/group/FlxSpriteGroup.hx': '''package flixel.group;
class Members<T:flixel.FlxSprite> {
 public var members:Array<T> = []; public function new() {}
 public function countLiving():Int { if (members.length == 0) return -1; var n = 0; for (m in members) if (m.alive) n++; return n; }
 public function kill():Void for (m in members) m.kill();
}
class FlxTypedSpriteGroup<T:flixel.FlxSprite> {
 public var x:Float = 0; public var y:Float = 0;
 public var group:Members<T> = new Members<T>();
 public function new(x:Float = 0, y:Float = 0) { this.x = x; this.y = y; }
 public function add(sprite:T):T {
  sprite.x += x; sprite.y += y;
  if (group.members.indexOf(sprite) < 0) group.members.push(sprite);
  return sprite;
 }
}''',
    'FNFAssets.hx': 'class FNFAssets { public static function exists(path:String):Bool return false; }',
    'HxcStateFactory.hx': 'class HxcStateFactory { public static var root = ""; public static function menuSessionRoot():String return root; }',
    'HxcStateAssetScope.hx': '''class HxcStateAssetScope {
 public static var asked:Array<String> = [];
 public static function paths(root:String):Dynamic return {getSparrowAtlas: function(key:String) {
  asked.push(root + ':' + key);
  return key == 'fonts/menu' ? new flixel.graphics.frames.FlxAtlasFrames(['H', 'I', '-period-'], 40) : null;
 }};
}''',
}

MAIN = r'''class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function prefixes(text:AtlasText):Array<String> {
  var out = [];
  for (m in text.group.members) if (m.alive) out.push(m.animation.current);
  return out;
 }
 static function main() {
  // V-Slice's bold font is not shipped: the engine alphabet bold letters stand in, upper case only.
  var bold = new AtlasText(10, 0, 'hi.', 'bold');
  check(bold.font.engineAlphabetStyle && bold.caseAllowed == 'Upper', 'bold falls back to the engine alphabet');
  check(prefixes(bold).join(',') == 'H bold,I bold,period bold', 'bold letters: ' + prefixes(bold));
  check(bold.group.members[0].x == 10 && bold.group.members[1].x == 60, 'letters are laid out left to right from the text x');
  bold.text = 'hi. ab';
  check(prefixes(bold).length == 5 && bold.group.members[3].x == 10 + 150 + 40, 'appending keeps letters and adds a space');
  bold.text = 'b';
  check(prefixes(bold).join(',') == 'B bold', 'a new text redraws: ' + prefixes(bold));
  // The default style picks lowercase and capital frames, tolerating the engine's "captial" spelling.
  var plain = new AtlasText(0, 0, 'aJ', 'default');
  check(prefixes(plain).join(',') == 'a lowercase,J captial', 'default letters: ' + prefixes(plain));
  // An imported menu's own font comes from its session owner.
  HxcStateFactory.root = 'imported/menu-pack';
  var owned = new AtlasText(0, 0, 'hi.', 'menu');
  check(!owned.font.engineAlphabetStyle && owned.caseAllowed == 'Upper', 'owner font detected as upper case only');
  check(prefixes(owned).join(',') == 'H,I,-period-', 'V-Slice frame names for an owner font: ' + prefixes(owned));
  check(HxcStateAssetScope.asked.indexOf('imported/menu-pack:fonts/menu') >= 0, 'the session owner was asked for the font');
  var again = new AtlasText(0, 0, 'h', 'menu');
  check(again.font == owned.font, 'owner fonts are cached per owner');
  // A proxy passed by the script wins over the session.
  var explicit = new AtlasText(0, 0, 'h', 'menu', {getSparrowAtlas: function(key:String) return null});
  check(explicit.font.engineAlphabetStyle, 'an explicit proxy without the font falls back to the alphabet');
  check(bold.getWidth() == 50, 'getWidth measures letters');
 }
}
'''


class AtlasTextTest(unittest.TestCase):
    def test_fonts_and_layout(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            root = Path(folder)
            for relative, text in STUBS.items():
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                (root / relative).write_text(text, newline='\n')
            (root / 'AtlasText.hx').write_text((ROOT / 'source/AtlasText.hx').read_text(encoding='utf-8'), newline='\n')
            (root / 'Main.hx').write_text(MAIN, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'Main', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
