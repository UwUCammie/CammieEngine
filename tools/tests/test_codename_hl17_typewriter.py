"""Run the HL17 shared typewriter adapter against deterministic Flixel stubs."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


STUBS = {
    "flixel/FlxSprite.hx": '''package flixel;
class Point { public var x:Float = 0; public var y:Float = 0; public function new() {} }
class FlxSprite {
 public var x:Float; public var y:Float; public var width:Float = 0;
 public var alpha:Float = 1; public var color:flixel.util.FlxColor = 0xFFFFFFFF;
 public var borderColor:flixel.util.FlxColor = 0; public var borderSize:Float = 0;
 public var borderStyle:flixel.text.FlxText.FlxTextBorderStyle;
 public var ID:Int = 0; public var font:String = ""; public var offset:Point = new Point();
 public function new(x:Float=0, y:Float=0) { this.x=x; this.y=y; }
 public function destroy():Void {}
}
''',
    "flixel/group/FlxSpriteGroup.hx": '''package flixel.group;
import flixel.FlxSprite;
class FlxTypedSpriteGroup<T:FlxSprite> extends FlxSprite {
 public var members:Array<T> = [];
 public function new() super();
 public function add(item:T):T { members.push(item); return item; }
 public function screenCenter(?axis:Int):Void {}
}
''',
    "flixel/text/FlxText.hx": '''package flixel.text;
import flixel.FlxSprite;
class FlxText extends FlxSprite {
 public var text:String;
 public var size:Int;
 public function new(x:Float=0, y:Float=0, fieldWidth:Float=0, text:String="", size:Int=8) {
  super(x,y); this.text=text; this.size=size;
  this.width = text == "i" || text == "l" || text == "1" || text == ":" ? 3 : text.length * 10;
 }
}
enum abstract FlxTextBorderStyle(Int) from Int to Int { var OUTLINE=1; }
''',
    "flixel/tweens/FlxTween.hx": '''package flixel.tweens;
import flixel.FlxSprite;
class FlxTween {
 public static var created:Array<FlxTween> = [];
 public var target:Dynamic; public var kind:String; public var duration:Float;
 public var onComplete:FlxTween->Void; public var cancelled:Bool = false; public var destroyed:Bool = false;
 public function new(target:Dynamic, kind:String, duration:Float) { this.target=target; this.kind=kind; this.duration=duration; created.push(this); }
 public static function color(sprite:FlxSprite, duration:Float, from:Int, to:Int):FlxTween return new FlxTween(sprite,"color",duration);
 public static function tween(object:Dynamic, values:Dynamic, duration:Float):FlxTween return new FlxTween(object,"tween",duration);
 public function complete():Void { if (onComplete != null) onComplete(this); }
 public function cancel():Void cancelled=true;
 public function destroy():Void destroyed=true;
}
''',
    "flixel/util/FlxColor.hx": "package flixel.util; typedef FlxColor = Int;\n",
    "flixel/util/FlxTimer.hx": '''package flixel.util;
class FlxTimer {
 public static var created:Array<FlxTimer> = [];
 public var time:Float = 0; public var callback:FlxTimer->Void;
 public var cancelled:Bool = false; public var destroyed:Bool = false;
 public function new() created.push(this);
 public function start(time:Float, callback:FlxTimer->Void):FlxTimer { this.time=time; this.callback=callback; return this; }
 public function complete():Void { if (!cancelled && callback != null) callback(this); }
 public function cancel():Void cancelled=true;
 public function destroy():Void destroyed=true;
}
''',
    "CodenamePaths.hx": '''class CodenamePaths {
 public var root:String; public var lastFont:String;
 public function new(root:String) this.root=root;
 public function font(key:String):String { lastFont=root+"/fonts/"+key; return lastFont; }
}
''',
}


class CodenameHl17TypewriterTest(unittest.TestCase):
    def test_source_import_binding_and_constructor_are_shared(self):
        bindings = (ROOT / "source/CodenameImportBindings.hx").read_text()
        interp = (ROOT / "source/CodenameScriptInterp.hx").read_text()
        self.assertIn("bindings.set('HLTypeText', CodenameHLTypeTextCompat);", bindings)
        self.assertIn("if (name == 'HLTypeText')", interp)
        self.assertIn("CodenameHLTypeTextCompat.fromArgs(args, paths)", interp)

    def test_glyph_layout_timing_callbacks_and_cleanup(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            for relative, content in STUBS.items():
                target = base / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
            (base / "Main.hx").write_text('''import flixel.FlxSprite;
import flixel.text.FlxText;
import flixel.tweens.FlxTween;
import flixel.util.FlxTimer;
class Main {
 static function fail(message:String):Void throw message;
 static function main():Void {
  var paths = new CodenamePaths("owner-a");
  var completeCount = 0;
  var label = CodenameHLTypeTextCompat.fromArgs([12, 34, "Wi", 0xFF123456, true], paths);
  label.onComplete = function() completeCount++;
  if (label.x != 12 || label.y != 34 || label.lettersGroup.members.length != 2)
   fail("constructor/lettersGroup shape");
  if (paths.lastFont != "owner-a/fonts/trebuc.ttf") fail("font did not resolve in selected owner");
  var first:FlxText = cast label.lettersGroup.members[0];
  var second:FlxText = cast label.lettersGroup.members[1];
  if (first.text != "W" || first.font != paths.lastFont || first.size != 32
    || first.alpha != 0.001 || first.color != 0xFF123456 || first.ID != 0)
   fail("first glyph styling");
  if (second.text != "i" || second.ID != 1 || second.x != 19)
   fail("source character spacing");
  if (FlxTimer.created.length != 3 || FlxTimer.created[0].time != 0
    || FlxTimer.created[1].time != 0.07 || FlxTimer.created[2].time != 0.14)
   fail("per-character and completion timers");

  FlxTimer.created[0].complete();
  if (FlxTween.created.length != 2 || FlxTween.created[0].target != first
    || FlxTween.created[0].kind != "color" || FlxTween.created[1].kind != "tween")
   fail("glyph reveal tweens");
  FlxTimer.created[2].complete();
  if (completeCount != 1 || FlxTimer.created.length != 4 || FlxTimer.created[3].time != 2.8)
   fail("completion callback/fade delay");
  FlxTimer.created[3].complete();
  if (FlxTween.created.length != 4) fail("fade should tween both glyphs");
  label.destroy();
  if (label.onComplete != null || !FlxTween.created[0].cancelled
    || !FlxTween.created[0].destroyed || !FlxTween.created[1].cancelled
    || !FlxTween.created[1].destroyed)
   fail("widget tweens/callback escaped destroy");

  var offsets = CodenameHLTypeTextCompat.fromArgs([], paths);
  offsets.playText(0, 0, "IM", 0xFFFFAA00);
  var i:FlxText = cast offsets.lettersGroup.members[0];
  var m:FlxText = cast offsets.lettersGroup.members[1];
  if (i.offset.x != 0 || m.offset.x != 5) fail("source I/M glyph offsets");
  offsets.destroy();
  if (offsets.onComplete != null || offsets.lettersGroup != null)
   fail("widget references retained after destroy");
  if (!FlxTimer.created[4].cancelled || !FlxTimer.created[4].destroyed
    || !FlxTimer.created[5].cancelled || !FlxTimer.created[5].destroyed
    || !FlxTimer.created[6].cancelled || !FlxTimer.created[6].destroyed)
   fail("widget timers escaped destroy");
  var rejected = false;
  try CodenameHLTypeTextCompat.fromArgs(["not-a-number"], paths) catch (error:Dynamic)
   rejected = Std.string(error).indexOf("argument 0 must be numeric") >= 0;
  if (!rejected) fail("dynamic constructor argument validation");
 }
}''')
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base), "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
