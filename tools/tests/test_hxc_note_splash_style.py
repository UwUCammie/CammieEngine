"""The imported note splash path keeps one selected style and a playable adapter."""
from haxe_test_support import HAXE_COMMAND

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]


class HxcNoteSplashStyleTest(unittest.TestCase):
    def test_literal_style_lookup_and_splash_constructor_survive_translation(self):
        source = '''class FlameNote extends NoteKind {
  var splashData = NoteStyleRegistry.instance.fetchEntry("fire-style");
  function onNoteHit(event) {
    var splash:NoteSplash = new NoteSplash(splashData);
    PlayState.instance.playerStrumline.add(splash);
    splash.play(event.note.noteData.getDirection());
    splash.x += splashData.getSplashOffsets()[0] * splash.scale.x;
  }
}'''
        dynamic = '''class OtherNote extends NoteKind {
  var splashData = NoteStyleRegistry.instance.fetchEntry(styleName);
}'''
        fixture = f'''import hscript.Parser;
class Main {{
  static function main() {{
    var result = HxcCompat.analyze({json.dumps(source)}, "scripts/notekinds/flame.hxc");
    var script = result.generatedHscript;
    if (script.indexOf('var splashData = HxcNoteStyleCompat.fetchEntry(hxcAssetRoot, "fire-style");') < 0)
      throw 'style field dropped: ' + script;
    if (script.indexOf('new HxcNoteSplashCompat(splashData)') < 0)
      throw 'splash constructor not adapted: ' + script;
    if (script.indexOf('PlayState.instance.playerStrumline.addScriptSprite(splash)') < 0)
      throw 'typed strumline add boundary not adapted: ' + script;
    new Parser().parseString(script);
    var blocked = HxcCompat.analyze({json.dumps(dynamic)}, "scripts/notekinds/other.hxc");
    if (blocked.generatedHscript.indexOf('HxcNoteStyleCompat.fetchEntry(hxcAssetRoot') >= 0)
      throw 'dynamic style expression escaped literal gate';
  }}
}}'''
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run([
                *HAXE_COMMAND, "-cp", str(ROOT / "source"),
                "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                "-cp", tmp, "-main", "Main", "--interp",
            ], cwd=ROOT, text=True, capture_output=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_style_media_resolution_stays_inside_selected_import(self):
        source = (ROOT / "source/HxcNoteStyleCompat.hx").read_text()
        self.assertIn("scopedAssetPath(root, 'data/notestyles/' + id + '.json')", source)
        self.assertIn("eventAtlas(style.root, style.splashAsset, 'sparrow'", source)
        self.assertIn("function getSplashOffsets()", source)

    def test_native_script_entry_accepts_sprite_before_receptor_cast(self):
        source = (ROOT / "source/Strumline.hx").read_text()
        entry = source[source.index("public function addScriptSprite("):
                       source.index("override public function insert(")]
        self.assertIn("sprite:FlxSprite", entry)
        self.assertIn("if (Std.isOfType(sprite, StrumNote))", entry)
        self.assertIn("attachEffect(sprite);", entry)

    def test_script_sprite_readd_keeps_one_attachment_and_transform(self):
        source = (ROOT / "source/Strumline.hx").read_text()
        entry = source[source.index("\tpublic function addScriptSprite("):
                       source.index("\n\toverride public function insert(")]
        attach = source[source.index("\tfunction attachEffect("):
                        source.index("\n\tpublic function forEachReceptor(")]
        fixture = '''class FakePoint {
  public var x:Float = 0;
  public var y:Float = 0;
  public function new() {}
  public function copyFrom(other:FakePoint):Void { x = other.x; y = other.y; }
}
class FlxSprite {
  public var x:Float = 1;
  public var y:Float = 2;
  public var alpha:Float = 0.8;
  public var scrollFactor:FakePoint = new FakePoint();
  public var cameras:Array<Int> = [];
  public function new() {}
}
class StrumNote extends FlxSprite { public function new() super(); }
class FlxTypedGroup<T> {
  public var members:Array<T> = [];
  public function new() {}
  public function add(sprite:T):Void members.push(sprite);
}
class Line {
  public var x:Float = 10;
  public var y:Float = 20;
  public var alpha:Float = 0.5;
  public var scrollFactor:FakePoint = new FakePoint();
  public var cameras:Array<Int> = [1];
  public var attachedEffects:FlxTypedGroup<FlxSprite>;
  public function new() {}
  public function add(sprite:StrumNote):StrumNote return sprite;
''' + entry + attach + '''
}
class Main {
  static function main() {
    var line = new Line();
    var sprite = new FlxSprite();
    line.addScriptSprite(sprite);
    line.addScriptSprite(sprite);
    if (line.attachedEffects.members.length != 1
      || sprite.x != 11 || sprite.y != 22 || sprite.alpha != 0.4)
      throw 'readding effect changed its transform or duplicated group member';
    if (sprite.cameras != line.cameras) throw 'strumline camera lost';
  }
}'''
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run([
                *HAXE_COMMAND, "-cp", tmp,
                "-main", "Main", "--interp",
            ], cwd=ROOT, text=True, capture_output=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_scoped_metadata_and_splash_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            (work / "flixel").mkdir()
            (work / "flixel/FlxSprite.hx").write_text('''package flixel;
class FlxSprite {
  public var frames:Dynamic;
  public var scale:FakeScale = new FakeScale();
  public var animation:FakeAnimation = new FakeAnimation();
  public var visible:Bool = true;
  public var alpha:Float = 1;
  public var alive:Bool = true;
  public function new() {}
  public function update(elapsed:Float):Void {}
  public function updateHitbox():Void {}
  public function kill():Void { alive = false; }
  public function revive():Void { alive = true; }
}
class FakeScale {
  public var x:Float = 1;
  public var y:Float = 1;
  public function new() {}
  public function set(x:Float, y:Float):Void { this.x = x; this.y = y; }
}
class FakeAnimation {
  public var curAnim:FakeCurAnim;
  public var available:Map<String, String> = [];
  public function new() {}
  public function addByPrefix(name:String, prefix:String, fps:Int, loop:Bool):Void {
    available.set(name, prefix);
  }
  public function play(name:String, force:Bool):Void {
    if (available.exists(name)) curAnim = new FakeCurAnim(name);
  }
}
class FakeCurAnim {
  public var name:String;
  public var finished:Bool = false;
  public function new(name:String) this.name = name;
}
''', newline='\n')
            (work / "flixel/FlxG.hx").write_text('''package flixel;
class FlxG { public static var random = new FakeRandom(); }
class FakeRandom { public function new() {} public function int(a:Int,b:Int):Int return a; }
''', newline='\n')
            (work / "HxcNoteStyleCompat.hx").write_text(
                (ROOT / "source/HxcNoteStyleCompat.hx").read_text(), newline='\n')
            (work / "HxcStateAssetScope.hx").write_text('''class HxcStateAssetScope {
  public static function scopedAssetPath(root:String, relative:String):String {
    var path = root + '/' + relative;
    return sys.FileSystem.exists(path) ? path : null;
  }
  public static function eventAtlas(root:String, key:String, kind:String, context:String):Dynamic {
    var image = scopedAssetPath(root, 'images/' + key + '.png');
    var xml = scopedAssetPath(root, 'images/' + key + '.xml');
    return image != null && xml != null ? {image:image, xml:xml} : null;
  }
}''', newline='\n')
            (work / "CoolUtil.hx").write_text(
                "class CoolUtil { public static function parseJson(s:String):Dynamic return haxe.Json.parse(s); }", newline='\n')
            (work / "FNFAssets.hx").write_text(
                "class FNFAssets { public static function getText(p:String):String return sys.io.File.getContent(p); }", newline='\n')
            for root_name, scale, alpha, offsets in [
                ("one", 0.6, 1.0, [-27.5, -75]),
                ("two", 1.25, 0.3, [12, 34]),
            ]:
                data = work / root_name / "data/notestyles"
                data.mkdir(parents=True)
                (data / "same.json").write_text(json.dumps({"assets": {"noteSplash": {
                    "assetPath": "shared:notes/SmokeSplash", "scale": scale,
                    "alpha": alpha, "offsets": offsets,
                    "data": {"enabled": True, "leftSplashes": [{"prefix": "smoke"}]},
                }}}), newline='\n')
            atlas = work / "one/images/notes"
            atlas.mkdir(parents=True)
            (atlas / "SmokeSplash.png").write_text("pixels", newline='\n')
            (atlas / "SmokeSplash.xml").write_text("atlas", newline='\n')
            main = '''import HxcNoteStyleCompat.HxcNoteSplashCompat;
class Main {
  static function main() {
    var one = HxcNoteStyleCompat.fetchEntry(Sys.getEnv('HXC_TEST_ROOT_ONE'), 'same');
    var two = HxcNoteStyleCompat.fetchEntry(Sys.getEnv('HXC_TEST_ROOT_TWO'), 'same');
    var absent = HxcNoteStyleCompat.fetchEntry(Sys.getEnv('HXC_TEST_ROOT_ONE'), 'missing');
    if (one == null || two == null || absent == null) throw 'missing descriptor';
    if (one.getSplashOffsets()[0] != -27.5 || two.getSplashOffsets()[0] != 12)
      throw 'root scope crossed';
    if (one.splashScale != 0.6 || two.splashScale != 1.25
      || one.splashAlpha != 1 || two.splashAlpha != 0.3)
      throw 'style parameters lost';
    if (one.getSplashPrefixes(0)[0] != 'smoke') throw 'prefix lost';
    if (absent.splashAsset != '' || absent.getSplashOffsets()[0] != 0)
      throw 'missing style invented media';
    var sprite = new HxcNoteSplashCompat(one);
    if (sprite.visible || sprite.scale.x != 0.6 || sprite.alpha != 1)
      throw 'splash constructor state';
    sprite.play(0);
    if (!sprite.visible || sprite.animation.curAnim.name != 'note0-0')
      throw 'splash did not play';
    sprite.animation.curAnim.finished = true;
    sprite.update(0.016);
    if (sprite.alive) throw 'finished splash not killed';
    sprite.play(0);
    if (!sprite.alive || !sprite.visible) throw 'splash did not revive';
    var missingAtlas = new HxcNoteSplashCompat(two);
    missingAtlas.play(0);
    if (missingAtlas.visible || missingAtlas.frames != null)
      throw 'missing scoped atlas made visible splash';
  }
}'''
            (work / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run([
                *HAXE_COMMAND, "-cp", tmp,
                "-main", "Main", "--interp",
            ], cwd=ROOT, text=True, capture_output=True, timeout=120,
                env={**os.environ, "HXC_TEST_ROOT_ONE": str(work / "one"),
                     "HXC_TEST_ROOT_TWO": str(work / "two")})
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
