"""Nightmare Vision note splashes use the selected skin's single lane animation."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

from tools.tests.test_psych_character_scope import extract_method


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class NightmareVisionNoteSplashTest(unittest.TestCase):
    def test_setup_uses_authored_alias_offsets_and_no_native_jitter(self):
        source = (ROOT / "source/NoteSplash.hx").read_text()
        setup = extract_method(source, "public function setupNoteSplash(")
        fixture = '''
class Point {
 public var x:Float = 0; public var y:Float = 0;
 public function new() {}
 public function set(x:Float, y:Float):Void { this.x=x; this.y=y; }
}
class FakeAnim {
 public var names:Array<String> = [];
 public var curAnim:Dynamic = null;
 public function new() {}
 public function play(name:String, force:Bool):Void {
  names.push(name); curAnim={name:name,frameRate:24};
 }
}
class FakeRandom { public function new() {} public function int(min:Int,max:Int):Int return min; }
class FlxG { public static var random=new FakeRandom(); }
class TUI { public var splashAlpha:Null<Float>=null; public var splashOffsetX:Null<Float>=null; public var splashOffsetY:Null<Float>=null; public function new() {} }
class Judgement { public static var uiJson:Dynamic={normal:new TUI()}; }
class NightmareVisionNoteSkin {
 public var calls:Array<Int>=[];
 public function new() {}
 public function applySplash(splash:NoteSplash,lane:Int):Bool {
  calls.push(lane); splash.variants=1; splash.nightmareVisionSplashOffset=[3.,-2.]; return true;
 }
}
class NoteSplash {
 public var animation=new FakeAnim(); public var offset=new Point();
 public var alpha:Float=1; public var direction:Int=0; public var uiType="normal";
 public var variants:Int=2; public var frameRate:Int=24; public var isPixel:Bool=false;
 public var width:Float=100; public var height:Float=80;
 public var x:Float=0; public var y:Float=0;
 public var nightmareVisionSkin:NightmareVisionNoteSkin;
 public var nightmareVisionSplashOffset:Array<Float>=null;
 public var calls:Array<String>=[];
 public function new() {}
 public function setPosition(x:Float,y:Float):Void { this.x=x; this.y=y; }
 public function updateHitbox():Void calls.push("hitbox");
 public function centerOffsets():Void calls.push("centerOffsets");
 public function centerOrigin():Void calls.push("centerOrigin");
 static function curUiTypeFor(type:String):TUI return cast Reflect.field(Judgement.uiJson,type);
''' + setup + '''
 static function main():Void {
  var splash=new NoteSplash(); var skin=new NightmareVisionNoteSkin();
  splash.nightmareVisionSkin=skin;
  splash.setupNoteSplash(11,19,2);
  if (skin.calls.length!=1 || skin.calls[0]!=2) throw "lane was not forwarded";
  if (splash.animation.names.length!=1 || splash.animation.names[0]!="note2-0") throw "wrong alias";
  if (splash.x!=11 || splash.y!=19 || splash.direction!=2) throw "position/direction lost";
  if (splash.calls.join(",")!="hitbox,centerOffsets,centerOrigin") throw "authored offsets applied in the wrong order";
  if (splash.offset.x!=3 || splash.offset.y!=-2) throw "authored offsets lost";
  if (splash.animation.curAnim.frameRate!=24) throw "NMV animation fps was randomized";
 }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "NoteSplash.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "NoteSplash", "--interp"],
                capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_strumline_uses_playstate_owner_helper_before_recycled_setup(self):
        source = (ROOT / "source/Strumline.hx").read_text()
        splash = extract_method(source, "public function doSplash(")
        owner_lookup = splash.index("playState.nightmareVisionSkinForStrumline(this)")
        setup = splash.index("newsplash.setupNoteSplash(")
        self.assertLess(owner_lookup, setup)
        self.assertIn("newsplash.nightmareVisionSkin =", splash)
        self.assertIn("newsplash.sourceStrumline = this", splash)


if __name__ == "__main__":
    unittest.main()
