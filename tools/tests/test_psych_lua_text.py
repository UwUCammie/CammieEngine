"""Psych Lua text uses HUD defaults and native FlxText property setters."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


def extract(source: str, name: str) -> str:
    match = re.search(r"\bfunction\s+" + name + r"\s*\(", source)
    if match is None:
        raise AssertionError(name)
    brace = source.index("{", match.end())
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[match.start():index + 1]
    raise AssertionError(f"unclosed {name}")


class PsychLuaTextTest(unittest.TestCase):
    def test_text_defaults_and_setters(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        source = (ROOT / "source/PlayState.hx").read_text()
        names = (
            "compatMakeLuaText", "compatRemoveLuaSprite", "compatAddLuaSprite", "compatAddLuaText",
            "compatSetTextString", "compatSetTextSize", "compatSetTextColor",
            "compatSetTextBorder", "compatSetTextFont", "compatSetTextAlignment",
            "compatGetTextFont", "compatRemoveLuaText", "compatFindText", "compatRemoveObject",
        )
        methods = "\n".join(extract(source, name) for name in names)
        self.assertIn("interp.variables.set('addLuaText', compatAddLuaText);", source)
        fixture = r'''class FixtureCamera { public function new() {} }
class Scroll { public var x:Float = 1; public var y:Float = 1;
 public function new() {} public function set(x:Float = 0,y:Float = 0):Void {this.x=x;this.y=y;} }
class FlxBasic {
 public var cameras(get,set):Array<FixtureCamera>;
 var assigned:Array<FixtureCamera>;
 public var cameraWrites:Int = 0;
 public function new() {}
 function get_cameras():Array<FixtureCamera> return assigned;
 function set_cameras(value:Array<FixtureCamera>):Array<FixtureCamera> {cameraWrites++; return assigned=value;}
}
class FlxSprite extends FlxBasic { public var destroyed:Bool=false; public function new() {super();} public function destroy():Void destroyed=true; }
class FlxText extends FlxSprite {
 public var scrollFactor = new Scroll();
 public var text(default,set):String = '';
 public var size(get,set):Int;
 public var font(get,set):String;
 public var color(default,set):Int = 0;
 public var borderSize(default,set):Float = 0;
 public var borderColor(default,set):Int = 0;
 public var alignment(get,set):String;
 var mySize:Int = 0; var myFont:String = ''; var myAlignment:String = '';
 public var setterWrites:Int = 0;
 public function new(x:Float,y:Float,width:Float,text:String,size:Int) {super();this.text=text;this.size=size;setterWrites=0;}
 function set_text(value:String):String {setterWrites++;return text=value;}
 function get_size():Int return mySize;
 function set_size(value:Int):Int {setterWrites++;return mySize=value;}
 function get_font():String return myFont;
 function set_font(value:String):String {setterWrites++;return myFont=value;}
 function set_color(value:Int):Int {setterWrites++;return color=value;}
 function set_borderSize(value:Float):Float {setterWrites++;return borderSize=value;}
 function set_borderColor(value:Int):Int {setterWrites++;return borderColor=value;}
 function get_alignment():String return myAlignment;
 function set_alignment(value:String):String {setterWrites++;return myAlignment=value;}
}
class CompatScriptManifest {
 public static function selectedRoot(data:Dynamic):String return data.selectedRoot;
}
class RuntimeSmokeHarness {
 public static function enabled():Bool return false;
 public static function markStep(_phase:String):Void {}
}
class PsychLuaTextFixture {
 var nightmareVisionLegacyFieldCameras=false;
 var modchartTexts:Map<String,FlxText>=[];
 var camHUD = new FixtureCamera();
 var haxeSprites:Map<String,FlxSprite> = [];
 var haxeSpriteAtlasNames:Map<String,Array<String>> = [];
 var psychGlobalProviderFirstSprite:FlxSprite = null;
 var members:Array<FlxSprite> = [];
 var BEHIND_NONE:Int = 0; var BEHIND_ALL:Int = 7;
 var addedAt:Int = -1;
 public function new() {}
 function remove(sprite:FlxSprite, splice:Bool):FlxSprite { if (splice) members.remove(sprite); return sprite; }
 function markPsychGlobalProviderSpritePhase(_sprite:Dynamic, _phase:String, ?_detail:String):Void {}
 function compatForgetSpriteAtlas(_sprite:Dynamic):Void {}
 function compatFindObject(name:Dynamic):Dynamic return haxeSprites.get(Std.string(name));
 function compatParseColor(value:Dynamic):Dynamic return Std.parseInt('0xFF' + Std.string(value));
 function getCompatScriptManifest():Dynamic return {selectedRoot:'assets/imported_mods/fixture'};
 function addHscriptSprite(sprite:FlxSprite,position:Int):Void {addedAt=position;members.push(sprite);}
 __METHODS__
 static function main() {
  var bridge = new PsychLuaTextFixture();
  var label = bridge.compatMakeLuaText('hpText','',0,0,22);
  if(label.cameras[0] != bridge.camHUD || label.cameraWrites != 1
   || label.scrollFactor.x != 0 || label.scrollFactor.y != 0)
   throw 'Lua text default camera/scroll differs from Psych';
  bridge.compatAddLuaText('hpText');
  if(bridge.addedAt != bridge.BEHIND_NONE) throw 'Lua text was not added at top';
  bridge.compatSetTextString('hpText','Health');
  bridge.compatSetTextSize('hpText',43);
  bridge.compatSetTextColor('hpText','FFFFFF');
  bridge.compatSetTextBorder('hpText',2,'000000');
  bridge.compatSetTextFont('hpText','PixelOld.ttf');
  bridge.compatSetTextAlignment('hpText','center');
  if(label.text != 'Health' || label.size != 43 || label.color != 0xFFFFFFFF
   || label.borderSize != 2 || label.borderColor != 0xFF000000
   || bridge.compatGetTextFont('hpText') != 'assets/imported_mods/fixture/fonts/PixelOld.ttf'
   || label.alignment != 'center' || label.setterWrites != 7)
   throw 'Lua text helper bypassed a native setter';
  bridge.compatSetTextFont('hpText','NativeOnly.ttf');
  if(bridge.compatGetTextFont('hpText') != 'assets/fonts/NativeOnly.ttf')
   throw 'Lua text font did not fall back to native Paths.font';
  bridge.nightmareVisionLegacyFieldCameras=true;
  var sprite=new FlxSprite();bridge.haxeSprites.set('shared',sprite);
  var first=bridge.compatMakeLuaText('shared','first');bridge.compatAddLuaText('shared');
  bridge.compatSetTextString('shared','changed');
  if(first.text!='changed'||sprite.destroyed||bridge.haxeSprites.get('shared')!=sprite)throw 'separate text namespace';
  bridge.compatRemoveLuaText('shared',false);if(first.destroyed||bridge.modchartTexts.get('shared')!=first)throw 'retained detached text';
  bridge.compatAddLuaText('shared');if(bridge.members.indexOf(first)<0)throw 'reattach text';
  var second=bridge.compatMakeLuaText('shared','second');if(!first.destroyed||bridge.members.indexOf(first)>=0||sprite.destroyed)throw 'text-only replacement';
  bridge.compatRemoveLuaSprite('shared');if(!sprite.destroyed||second.destroyed)throw 'sprite-only removal';
  bridge.compatRemoveObject('shared');if(!second.destroyed||bridge.modchartTexts.exists('shared'))throw 'text removal';
  Sys.println('OK');
 }
}'''.replace("__METHODS__", methods)
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "PsychLuaTextFixture.hx").write_text(fixture, newline='\n')
            (Path(folder) / "PsychFontPath.hx").write_text(
                (ROOT / "source/PsychFontPath.hx").read_text(), newline='\n')
            (Path(folder) / "FNFAssets.hx").write_text('''
class FNFAssets {
 public static function exists(path:String):Bool return sys.FileSystem.exists(path);
}
''', newline='\n')
            scoped = Path(folder) / 'assets/imported_mods/fixture/fonts'
            scoped.mkdir(parents=True)
            (scoped / 'PixelOld.ttf').write_bytes(b'scoped')
            native = Path(folder) / 'assets/fonts'
            native.mkdir(parents=True)
            (native / 'PixelOld.ttf').write_bytes(b'native')
            (native / 'NativeOnly.ttf').write_bytes(b'native')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "PsychLuaTextFixture"],
                cwd=folder, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
