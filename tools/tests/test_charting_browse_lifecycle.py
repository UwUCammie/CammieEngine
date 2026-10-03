"""Regression coverage for the chart editor's character picker and file dialog.

The observed crash came from the registry entry `17bucksyuri`, which has no
health-strip image. Fixtures inject a generic missing entry so the test does
not depend on which imported character sorts first.
"""
from haxe_test_support import HAXE_COMMAND

import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


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


class ChartingBrowseLifecycleTest(unittest.TestCase):
    def test_missing_registry_icon_uses_safe_fallback(self):
        source = (ROOT / "source/HealthIcon.hx").read_text(encoding="utf-8")
        load_icon = extract_method(source, "public function loadIcon(")
        missing_character = "picker-entry-without-icons"
        fixture = f'''import lime.app.Future;
typedef IconData = {{ var json:Dynamic; var path:String; var assetRoot:String; }};
class HealthIcon {{
  public static var fallbackCount:Int = 0;
  public static var lastFallback:String = "";
  public var iconOwnerRoot:Null<String> = null;
  public var frames:Dynamic;
  public var animation:Dynamic = {{}};
  public var loadCount:Int = 0;
  public function new() {{}}
  static function getIconFromJsons(_name:String, _owner:Null<String>):IconData
    return {{json: {{icons: [0]}}, path: "{missing_character}", assetRoot: "assets/images/custom_chars/"}};
  public function switchAnim(name:String):Dynamic {{
    fallbackCount++;
    lastFallback = name;
    return this;
  }}
  public function loadGraphic(_image:Dynamic, _animated:Bool, _width:Int, _height:Int):Void {{}}
{load_icon}
  static function main() {{
    var icon = new HealthIcon();
    var result = icon.loadIcon("{missing_character}");
    if (FNFAssets.loadCount != 0) throw "missing registry icon reached asynchronous file load";
    if (fallbackCount != 1 || lastFallback != "{missing_character}")
      throw "missing registry icon did not use the established fallback";
    if (result.value != icon) throw "loadIcon did not complete with its receiver";
    trace("OK");
  }}
}}
class FNFAssets {{
  public static var loadCount:Int = 0;
  public static function exists(_path:String):Bool return false;
  public static function loadBitmapData(path:String):Future<Dynamic> {{
    loadCount++;
    throw "unguarded missing icon load: " + path;
  }}
}}
'''
        self._run_haxe_fixture({
            "HealthIcon.hx": fixture,
            "DynamicSprite.hx": '''class DynamicSprite {}
class DynamicAtlasFrames {
  public static function fromSparrow(_png:String, _xml:String):Dynamic return null;
}
''',
            "lime/app/Future.hx": '''package lime.app;
class Future<T> {
  public var value:T;
  public function new(value:T) this.value = value;
  public static function withValue<T>(value:T):Future<T> return new Future<T>(value);
  public function then(_callback:Dynamic->Dynamic):Dynamic return this;
  public function onComplete(_callback:Dynamic->Dynamic):Dynamic return this;
}
''',
        }, "HealthIcon")

    def test_picker_async_icons_are_per_request_and_safe_across_destroy(self):
        source = (ROOT / "source/ChartCharDropdown.hx").read_text(encoding="utf-8")
        icon_loop = source[source.index("for (char in allChars)"):
                           source.index("for (stage in allStages)")]
        self.assertIn("loadCharacterIcon(char, charButton);", icon_loop)
        load_icon = extract_method(source, "function loadCharacterIcon(")
        destroy = extract_method(source, "override function destroy():Void")
        fixture = f'''class Main {{
  static function main() {{
    var picker = new ChartCharDropdown();
    var earlyA = new FlxUIButton("early-a");
    var earlyB = new FlxUIButton("early-b");
    picker.attach(earlyA);
    picker.attach(earlyB);
    picker.requestIcon("character-a", earlyA);
    picker.requestIcon("character-b", earlyB);
    if (HealthIcon.requests.length != 2) throw "each button did not get an icon request";
    if (HealthIcon.requests[0].icon == HealthIcon.requests[1].icon)
      throw "two buttons shared one async HealthIcon receiver";
    if (earlyA.image == earlyB.image) throw "picker buttons shared their base image";
    HealthIcon.requests[1].future.resolve(HealthIcon.requests[1].icon);
    HealthIcon.requests[0].future.resolve(HealthIcon.requests[0].icon);
    if (earlyA.writes != 1 || earlyB.writes != 1)
      throw "completed icon was not stamped onto its own button";
    if (HealthIcon.requests[0].icon.destroyCount != 1
      || HealthIcon.requests[1].icon.destroyCount != 1)
      throw "completed loader icon was not destroyed exactly once";
    if (earlyA.lastIcon != HealthIcon.requests[0].icon.id
      || earlyB.lastIcon != HealthIcon.requests[1].icon.id)
      throw "out-of-order icon completion crossed button ownership";

    var latePicker = new ChartCharDropdown();
    var lateButton = new FlxUIButton("late");
    latePicker.attach(lateButton);
    latePicker.requestIcon("late-character", lateButton);
    var lateIcon = HealthIcon.requests[2].icon;
    latePicker.destroy();
    latePicker.destroy();
    if (!lateButton.destroyed) throw "picker teardown did not dispose its button";
    HealthIcon.requests[2].future.resolve(lateIcon);
    if (lateButton.writes != 0) throw "late callback wrote into a disposed button";
    if (lateIcon.destroyCount != 1) throw "late loader icon was not destroyed exactly once";
    if (latePicker.destroyCount != 1) throw "picker teardown ran more than once";

    var failedPicker = new ChartCharDropdown();
    var failedButton = new FlxUIButton("failed");
    failedPicker.attach(failedButton);
    failedPicker.requestIcon("failed-character", failedButton);
    var failedIcon = HealthIcon.requests[3].icon;
    HealthIcon.requests[3].future.reject("decode failed");
    if (failedButton.writes != 0 || failedIcon.destroyCount != 1)
      throw "failed async load did not clean up without touching the button";
    trace("OK");
  }}
}}
class Future<T> {{
  public var completeCallback:T->Void;
  public var errorCallback:Dynamic->Void;
  public var isComplete:Bool = false;
  public var isError:Bool = false;
  public var value:T;
  public var error:Dynamic;
  public function new() {{}}
  public function onComplete(callback:T->Void):Future<T> {{
    completeCallback = callback;
    if (isComplete) callback(value);
    return this;
  }}
  public function onError(callback:Dynamic->Void):Future<T> {{
    errorCallback = callback;
    if (isError) callback(error);
    return this;
  }}
  public function resolve(result:T):Void {{
    value = result;
    isComplete = true;
    if (completeCallback != null) completeCallback(result);
  }}
  public function reject(result:Dynamic):Void {{
    error = result;
    isError = true;
    if (errorCallback != null) errorCallback(result);
  }}
}}
class HealthIcon {{
  public static var requests:Array<{{icon:HealthIcon, future:Future<HealthIcon>}}> = [];
  public static var nextId:Int = 0;
  public var id:String;
  public var destroyCount:Int = 0;
  public function new(_initial:String) {{ id = "icon-" + nextId++; }}
  public function setGraphicSize(_width:Int, _height:Int):Void {{}}
  public function loadIcon(_name:String):Future<HealthIcon> {{
    var future = new Future<HealthIcon>();
    requests.push({{icon:this, future:future}});
    return future;
  }}
  public function destroy():Void destroyCount++;
}}
class FlxUIButton {{
  public var image:Dynamic;
  public var writes:Int = 0;
  public var destroyed:Bool = false;
  public var destroyCount:Int = 0;
  public var lastIcon:String = "";
  public function new(id:String) image = {{id:id}};
  public function addIcon(icon:HealthIcon):Void {{
    if (destroyed) throw "disposed-button-write";
    writes++;
    lastIcon = icon.id;
  }}
  public function destroy():Void {{
    if (!destroyed) {{ destroyed = true; destroyCount++; image = null; }}
  }}
}}
class Group {{
  public var members:Array<FlxUIButton> = [];
  public var destroyCount:Int = 0;
  public function new() {{}}
  public function attach(button:FlxUIButton):Void members.push(button);
  public function destroy():Void {{
    destroyCount++;
    for (button in members) button.destroy();
  }}
}}
class ChartCharDropdown extends Group {{
  var pickerDestroyed:Bool = false;
  public function requestIcon(char:String, button:FlxUIButton):Void loadCharacterIcon(char, button);
{load_icon}
{destroy}
}}
'''
        self._run_haxe_fixture({"Main.hx": fixture}, "Main")

    def test_flx_ui_button_stamp_survives_icon_sprite_destroy(self):
        source = (ROOT / ".haxelib/flixel-ui/2,6,5/flixel/addons/ui/FlxUIButton.hx").read_text(
            encoding="utf-8"
        )
        add_icon = extract_method(source, "public function addIcon(")
        fixture = f'''class Main {{
  static function main() {{
    var buttonA = new FlxUIButton("base-a", 10);
    var buttonB = new FlxUIButton("base-b", 20);
    var originalA = buttonA.graphic.bitmap;
    var iconA = new FlxSprite("icon-a", 91);
    var iconBitmap = iconA.graphic.bitmap;
    buttonA.addIcon(iconA);
    buttonB.addIcon(new FlxSprite("icon-b", 92));
    var stampedBitmap = buttonA.graphic.bitmap;
    if (stampedBitmap == originalA || stampedBitmap == iconBitmap)
      throw "addIcon did not stamp into an owned button bitmap";
    if (stampedBitmap.pixels[0] != 91) throw "addIcon did not stamp icon pixels";
    if (buttonA.graphic.bitmap == buttonB.graphic.bitmap)
      throw "buttons shared their stamped bitmaps";
    iconA.destroy();
    if (buttonA.graphic.bitmap != stampedBitmap || stampedBitmap.pixels[0] != 91)
      throw "destroying the icon invalidated the button stamp";
    trace("OK");
  }}
}}
class BitmapData {{
  public var pixels:Array<Int>;
  public function new(pixels:Array<Int>) this.pixels = pixels.copy();
  public function clone():BitmapData return new BitmapData(pixels);
}}
class Graphic {{
  public var bitmap:BitmapData;
  public var key:String;
  public function new(bitmap:BitmapData, key:String) {{ this.bitmap = bitmap; this.key = key; }}
}}
class Offset {{
  public var x:Float; public var y:Float;
  public function new(x:Float, y:Float) {{ this.x = x; this.y = y; }}
}}
class FlxSprite {{
  public var graphic:Graphic;
  public var width:Float = 1;
  public var height:Float = 1;
  public var numFrames:Int = 1;
  public var labelOffsets:Array<Offset> = [new Offset(0, 0), new Offset(0, 0), new Offset(0, 0)];
  public function new(key:String, pixel:Int) graphic = new Graphic(new BitmapData([pixel]), key);
  public function loadGraphic(value:Graphic, _animated:Bool, _width:Int, _height:Int):Void graphic = value;
  public function stamp(icon:FlxSprite, _x:Int, _y:Int):Void
    graphic.bitmap.pixels[0] = icon.graphic.bitmap.pixels[0];
  public function destroy():Void graphic = null;
}}
class FlxUIButton extends FlxSprite {{
  var _noIconGraphicsBkup:BitmapData;
  public function new(key:String, pixel:Int) super(key, pixel);
{add_icon}
}}
class BitmapCache {{
  public function new() {{}}
  public function add(bitmap:BitmapData, _unique:Bool, key:String):Graphic
    return new Graphic(bitmap, key);
}}
class FlxG {{ public static var bitmap:BitmapCache = new BitmapCache(); }}
class FlxMath {{ public static function minInt(a:Int, b:Int):Int return a < b ? a : b; }}
'''
        self._run_haxe_fixture({"Main.hx": fixture}, "Main")

    def test_event_file_dialog_listener_precedes_native_browse_and_ignores_late_result(self):
        charting = (ROOT / "source/ChartingState.hx").read_text(encoding="utf-8")
        converter = extract_method(charting, "function psychEventsToHScript()")
        self.assertLess(converter.index("coolDialog.onSelect.add"),
                        converter.index("coolDialog.browse(FileDialogType.OPEN)"))
        callback = converter[converter.index("coolDialog.onSelect.add"):]
        self.assertLess(callback.index("if (editorDestroyed)"), callback.index("File.getContent(path)"))
        destroy = extract_method(charting, "override public function destroy()")
        self.assertLess(destroy.index("editorDestroyed = true"), destroy.index("super.destroy()"))

    def _run_haxe_fixture(self, files, main_class):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            folder = Path(folder)
            for relative, content in files.items():
                path = folder / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline='\n')
            env = os.environ.copy()
            env["TMPDIR"] = str(ROOT / "tmp")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(folder), "-main", main_class, "--interp"],
                cwd=folder,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
