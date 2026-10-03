"""Exercise the shared legacy imports used by selected-owner HL17 event classes."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HL17_DONOR = (
    Path("/run/media/cammie/External Storage/FNF-Example-Mods")
    / "codename/hl17_v3/mods/HL17/source/HLTextbox.hx"
)
ROBLOX_DONOR = HL17_DONOR.with_name("RobloxTextbox.hx")


def haxe_fixture_env():
    env = dict(os.environ)
    env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
    env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
    env["PATH"] = os.pathsep.join(
        [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
    )
    return env


class CodenameHL17EventImportTest(unittest.TestCase):
    def test_legacy_flixel_imports_and_selected_owner_hltextbox_execute(self):
        bindings_source = (ROOT / "source/CodenameImportBindings.hx").read_text(encoding="utf-8")
        self.assertIn("import flixel.math.FlxMath;", bindings_source)
        self.assertIn("bindings.set('flixel.math.FlxMath', FlxMath);", bindings_source)
        self.assertIn("bindings.set('flixel.FlxMath', FlxMath);", bindings_source)
        self.assertIn(
            "bindings.set('flixel.util.FlxSpriteUtil', CodenameFlxSpriteUtilCompat.facade());",
            bindings_source,
        )

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            # The fixture modules below are written relative to this root.
            owner = base
            modules = {
                "flixel/FlxSprite.hx": '''package flixel;
class FlxSprite {
 public var drawCalls:Int=0;
 public function new() {}
}''',
                "flixel/math/FlxMath.hx": '''package flixel.math;
class FlxMath {
 public static function lerp(a:Float,b:Float,ratio:Float):Float return a+(b-a)*ratio;
}''',
                "flixel/util/FlxSpriteUtil.hx": '''package flixel.util;
class FlxSpriteUtil {
 public static function drawRoundRect(sprite:flixel.FlxSprite,x:Float,y:Float,w:Float,h:Float,
  rx:Float,ry:Float,?color:Int):flixel.FlxSprite { sprite.drawCalls++; return sprite; }
 public static function drawTriangle(sprite:flixel.FlxSprite,x:Float,y:Float,height:Float,
  ?color:Int):flixel.FlxSprite { sprite.drawCalls++; return sprite; }
}''',
                "source/HLTextbox.hx": '''import flixel.FlxSprite;
import flixel.FlxMath;
import flixel.util.FlxSpriteUtil;
class HLTextbox extends FlxSprite {
 public function new() { super(); }
 public function drawBox():Int {
  FlxSpriteUtil.drawRoundRect(this,0,0,100,40,4,4);
  FlxSpriteUtil.drawTriangle(this,50,40,8);
  return this.drawCalls;
 }
 public function interpolate():Float { return FlxMath.lerp(10,20,0.5); }
}''',
            }
            for relative, content in modules.items():
                path = base / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline='\n')

            (base / "CodenameScriptInterp.hx").write_text('''class CodenameScriptInterp {
 public var variables:Map<String,Dynamic>=new Map();
 public function new() {}
 public function bindScriptClassScope(_scope:hscript.ScriptClassScope):Void {}
}''', encoding="utf-8", newline='\n')
            (base / "Main.hx").write_text(r'''import flixel.math.FlxMath;
import flixel.FlxSprite;
import flixel.util.FlxSpriteUtil;
@:access(hscript.ScriptClass)
class Main {
 public static var cwd:String;
 static function main():Void {
  var bindings:Map<String,Dynamic>=new Map();
  bindings.set("flixel.FlxSprite",FlxSprite);
  bindings.set("FlxSprite",FlxSprite);
  bindings.set("flixel.FlxMath",FlxMath);
  bindings.set("flixel.util.FlxSpriteUtil",CodenameFlxSpriteUtilCompat.facade());
  var loaded=CodenameScriptClassLoader.load(Sys.args()[0],
   ["flixel.FlxMath","HLTextbox"],bindings,new Map());
  if(loaded.diagnostics.length!=0)
   throw "selected-owner HLTextbox imports did not resolve: "+loaded.diagnostics;
  if(!loaded.imports.exists("HLTextbox"))
   throw "selected-owner HLTextbox descriptor was not registered";
  var textbox=loaded.scope.createInstance("HLTextbox",[]);
  if(textbox.callFunction("drawBox",[])!=2)
   throw "owner script sprite was not unwrapped for both native drawing calls";
  if(textbox.callFunction("interpolate",[])!=15)
   throw "legacy FlxMath import did not execute";
  loaded.scope.release();
 }
}''', encoding="utf-8", newline='\n')

            command = [
                *HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"),
                "--run", "Main", str(owner),
            ]
            result = subprocess.run(
                command, cwd=ROOT, env=haxe_fixture_env(), text=True,
                capture_output=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_selected_owner_textboxes_draw_and_run_delayed_callbacks(self):
        if not HL17_DONOR.is_file() or not ROBLOX_DONOR.is_file():
            self.skipTest("the selected HL17 owner source is not mounted")

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            owner = base / "owner"
            owner_source = owner / "source/HLTextbox.hx"
            owner_source.parent.mkdir(parents=True, exist_ok=True)
            owner_source.write_text(HL17_DONOR.read_text(encoding="utf-8"), encoding="utf-8", newline='\n')
            (owner_source.parent / "RobloxTextbox.hx").write_text(
                ROBLOX_DONOR.read_text(encoding="utf-8"), encoding="utf-8"
            , newline='\n')
            (owner / "source/PositionProbe.hx").write_text('''import fixture.NativePoint;
class PositionProbe extends NativePoint {
 public function new() { super(x,y); }
}''', encoding="utf-8", newline='\n')

            stubs = {
                "flixel/FlxSprite.hx": '''package flixel;
class FlxSprite {
 public var x:Float=0; public var y:Float=0; public var width:Float=0; public var height:Float=0;
 public var alpha:Float=1; public var drawCalls:Int=0; public var state:Dynamic;
 public var flipY:Bool=false;
 public var scale:Dynamic; public var origin:Dynamic;
 public function new(x:Float=0,y:Float=0) {
  this.x=x; this.y=y;
  var scaleValue:Dynamic; scaleValue={x:1.0,y:1.0,set:function(nx:Float,ny:Float):Dynamic {
   scaleValue.x=nx; scaleValue.y=ny; return scaleValue; }}; scale=scaleValue;
  var originValue:Dynamic; originValue={x:0.0,y:0.0,set:function(nx:Float,ny:Float):Dynamic {
   originValue.x=nx; originValue.y=ny; return originValue; }}; origin=originValue;
 }
 public function makeGraphic(width:Float,height:Float,color:Dynamic):FlxSprite {
  this.width=width; this.height=height; return this;
 }
 public function screenCenter(axis:Int):FlxSprite return this;
 public function updateHitbox():Void {}
 public function getGraphicMidpoint():Dynamic return {x:x+width/2,y:y+height/2};
 public function update(elapsed:Float):Void {}
 public function destroy():Void {}
}''',
                "fixture/NativePoint.hx": '''package fixture;
class NativePoint {
 public var x:Float=0; public var y:Float=0;
 public function new(x:Float=0,y:Float=0) { this.x=x; this.y=y; }
}''',
                "flixel/FlxG.hx": '''package flixel;
class FlxG { public static var width:Int=1280; }''',
                "flixel/text/FlxText.hx": '''package flixel.text;
import flixel.FlxSprite;
class FlxText extends FlxSprite {
 public var text:String; public var font:String=""; public var textField:Dynamic;
 public var alignment:String=""; public var color:Int=0;
 public function new(x:Float=0,y:Float=0,width:Float=0,text:String="",size:Int=8) {
  super(x,y); this.width=width; this.text=text; this.height=size+4; textField={numLines:1};
 }
}''',
                "flixel/util/FlxTimer.hx": '''package flixel.util;
class FlxTimer {
 public var active:Bool=false; public var callback:Dynamic;
 public function new() {}
 public function start(duration:Float,callback:Dynamic):FlxTimer {
  this.callback=callback; active=true; return this;
 }
 public function cancel():FlxTimer { active=false; callback=null; return this; }
 public function fire():Void {
  active=false; var current=callback; callback=null;
  if(current!=null) Reflect.callMethod(null,current,[]);
 }
}''',
                "flixel/util/FlxSpriteUtil.hx": '''package flixel.util;
import flixel.FlxSprite;
class FlxSpriteUtil {
 public static function drawRoundRect(sprite:FlxSprite,x:Float,y:Float,w:Float,h:Float,
  rx:Float,ry:Float,?color:Int):FlxSprite { sprite.drawCalls++; return sprite; }
 public static function drawTriangle(sprite:FlxSprite,x:Float,y:Float,height:Float,
  ?color:Int):FlxSprite { sprite.drawCalls++; return sprite; }
}''',
                "flixel/util/FlxColor.hx": '''package flixel.util;
class FlxColor { public static var TRANSPARENT:Int=0; }''',
                "flixel/group/FlxGroup.hx": '''package flixel.group;
class FlxGroup { public var members:Array<Dynamic>=[]; public function new() {} }''',
                "flixel/group/FlxSpriteGroup.hx": '''package flixel.group;
typedef FlxSpriteGroup=FlxTypedSpriteGroup<FlxSprite>;
class FlxTypedSpriteGroup<T:FlxSprite> extends FlxSprite {
 public var members:Array<T>=[]; public var cameras:Array<Dynamic>=[];
 public function new(x:Float=0,y:Float=0) super(x,y);
 public function add(member:T):T { members.push(member); member.state=state; return member; }
 override public function update(elapsed:Float):Void for(member in members) if(member!=null) member.update(elapsed);
 override public function destroy():Void { members=[]; super.destroy(); }
}''',
                "flixel/tweens/FlxTween.hx": '''package flixel.tweens;
class FlxTween {
 static var completions:Array<Dynamic>=[];
 public static function tween(target:Dynamic,properties:Dynamic,duration:Float,?options:Dynamic):Dynamic {
  if(options!=null) { var callback=Reflect.field(options,"onComplete"); if(callback!=null) completions.push(callback); }
  return null;
 }
 public static function cancelTweensOf(target:Dynamic):Void {}
 public static function completeTweensOf(target:Dynamic):Void {}
 public static function flushCompletions():Int {
  var pending=completions; completions=[];
  for(callback in pending) Reflect.callMethod(null,callback,[]);
  return pending.length;
 }
}''',
                "flixel/tweens/FlxEase.hx": '''package flixel.tweens;
class FlxEase { public static var expoOut:Dynamic=0; public static var backIn:Dynamic=0; }''',
                "Paths.hx": '''class Paths { public static function font(path:String):String return path; }''',
                "TestState.hx": '''class TestState {
 public var removals:Int=0;
 public function new() {}
 public function remove(member:Dynamic):Dynamic { removals++; member.state=null; return member; }
}''',
            }
            for relative, content in stubs.items():
                path = base / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline='\n')

            (base / "CodenameScriptInterp.hx").write_text('''class CodenameScriptInterp {
 public var variables:Map<String,Dynamic>=new Map();
 public function new() {}
 public function bindScriptClassScope(_scope:hscript.ScriptClassScope):Void {}
}''', encoding="utf-8", newline='\n')
            (base / "Main.hx").write_text(r'''import flixel.FlxG;
import flixel.FlxSprite;
import fixture.NativePoint;
import flixel.group.FlxGroup;
import flixel.group.FlxSpriteGroup;
import flixel.text.FlxText;
import flixel.tweens.FlxEase;
import flixel.tweens.FlxTween;
import flixel.util.FlxColor;
import flixel.util.FlxSpriteUtil;
import flixel.util.FlxTimer;
@:access(hscript.ScriptClass)
@:access(CodenameScriptClassLoader)
class Main {
 public static var cwd:String;
 static function main():Void {
  var bindings:Map<String,Dynamic>=new Map();
  bindings.set("flixel.FlxSprite",FlxSprite);
  bindings.set("flixel.FlxG",FlxG);
  bindings.set("flixel.text.FlxText",FlxText);
  bindings.set("flixel.util.FlxTimer",FlxTimer);
  var spriteUtil=CodenameFlxSpriteUtilCompat.facade();
  bindings.set("flixel.util.FlxSpriteUtil",spriteUtil);
  bindings.set("funkin.backend.MusicBeatGroup",CodenameMusicBeatGroupCompat);
  bindings.set("flixel.util.FlxColor",FlxColor);
  bindings.set("flixel.group.FlxGroup",FlxGroup);
  bindings.set("flixel.group.FlxSpriteGroup",FlxSpriteGroup);
  bindings.set("flixel.tweens.FlxTween",FlxTween);
  bindings.set("flixel.tweens.FlxEase",FlxEase);
  bindings.set("Paths",Paths);
  bindings.set("fixture.NativePoint",NativePoint);
  var normalized=CodenameScriptClassLoader.normalizeForRangeArithmetic(
   sys.io.File.getContent(Sys.args()[0]+"/source/HLTextbox.hx"));
  if(normalized.indexOf("0...(lines.length - 1)")<0)
   throw "native for-range precedence was not normalized";
  var loaded=CodenameScriptClassLoader.load(Sys.args()[0],["HLTextbox","RobloxTextbox","PositionProbe"],bindings,new Map());
  if(loaded.diagnostics.length!=0) throw "selected-owner HLTextbox did not load: "+loaded.diagnostics;
  var textbox=loaded.scope.createInstance("HLTextbox",["",false]);
  if(textbox==null) throw "selected-owner HLTextbox constructor did not run";
  var nativeSprite:Dynamic=Reflect.field(textbox,"superClass");
  if(Reflect.field(nativeSprite,"x")!=0 || Reflect.field(nativeSprite,"y")!=0)
   throw "inherited FlxSprite position defaults were not supplied to super(x,y)";
  var point=loaded.scope.createInstance("PositionProbe",[]);
  var nativePoint:Dynamic=Reflect.field(point,"superClass");
  if(Reflect.field(nativePoint,"x")!=0 || Reflect.field(nativePoint,"y")!=0)
   throw "position defaults were tied to a FlxSprite name instead of native field types";
  var nativeSprite:Dynamic=Reflect.field(textbox,"superClass");
  var scriptVariables=(cast textbox:hscript.ScriptClass)._interp.variables;
  var state=new TestState(); nativeSprite.state=state;
  var group:Dynamic=scriptVariables.get("linesGrp"); group.state=state;
  textbox.callFunction("addText",["a lyric line"]);
  var lines:Array<Dynamic>=cast scriptVariables.get("lines");
  if(lines.length!=1 || Reflect.field(nativeSprite,"drawCalls")!=0)
   throw "HLTextbox.addText did not register its line";
  textbox.callFunction("update",[0.016]);
  if(Reflect.field(nativeSprite,"drawCalls")!=1)
   throw "HLTextbox.update did not execute its imported FlxSpriteUtil drawing helper";
  var timer:FlxTimer=cast scriptVariables.get("lyricTimer");
  if(timer==null || !timer.active) throw "HLTextbox lyric cleanup timer did not start";
  timer.fire();
  if(FlxTween.flushCompletions()!=1) throw "HLTextbox line fade did not schedule one cleanup callback";
  if(state.removals!=1 || lines.length!=0)
   throw "delayed HLTextbox cleanup failed to call state.remove and remove the lyric";
  var roblox=loaded.scope.createInstance("RobloxTextbox",[12,34]);
  if(roblox==null) throw "selected-owner RobloxTextbox constructor did not run";
  var nativeGroup:CodenameMusicBeatGroupCompat=cast Reflect.field(roblox,"superClass");
  nativeGroup.bindOwnerScript(cast roblox);
  if(nativeGroup.x!=12 || nativeGroup.y!=34 || nativeGroup.members.length!=3)
   throw "RobloxTextbox did not create its source-positioned native child group";
  var robloxVariables=(cast roblox:hscript.ScriptClass)._interp.variables;
  var character=new FlxSprite(100,200).makeGraphic(50,70,0);
  roblox.callFunction("playText",["spoken line",character]);
  roblox.callFunction("update",[0.016]);
  var box:FlxSprite=cast robloxVariables.get("box");
  var triangle:FlxSprite=cast robloxVariables.get("triangle");
  if(box.drawCalls!=1 || triangle.drawCalls!=1)
   throw "RobloxTextbox failed to draw both source bubble sprites";
  var bubbleTimer:FlxTimer=cast robloxVariables.get("timer");
  if(bubbleTimer==null || !bubbleTimer.active)
   throw "RobloxTextbox delayed bubble fade did not start";
  bubbleTimer.fire();
  loaded.scope.release();
 }
}''', encoding="utf-8", newline='\n')

            command = [
                *HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"),
                "--run", "Main", str(owner),
            ]
            result = subprocess.run(
                command, cwd=ROOT, env=haxe_fixture_env(), text=True,
                capture_output=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
