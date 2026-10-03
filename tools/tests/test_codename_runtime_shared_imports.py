"""Exercise the shared native imports used by Codename global scripts."""
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
                return source[start : index + 1]
    raise AssertionError(f"unterminated method: {marker}")


def run_haxe(folder: Path, main: str = "Main") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
         "-cp", str(folder), "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
         "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), "--run", main],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )


class CodenameRuntimeSharedImportsTest(unittest.TestCase):
    def test_shared_imports_use_native_or_behavioral_bindings(self):
        source = (ROOT / "source/CodenameImportBindings.hx").read_text()
        for mapping in (
            "bindings.set('Type', typeConstants());",
            "bindings.set('haxe.Timer', timerConstants());",
            "bindings.set('openfl.display.FPS', FPS);",
            "bindings.set('openfl.text.TextField', TextField);",
            "bindings.set('openfl.text.TextFormat', TextFormat);",
            "bindings.set('openfl.display.Sprite', Sprite);",
            "bindings.set('funkin.backend.utils.MemoryUtil', memoryUtilConstants());",
            "bindings.set('funkin.backend.system.Main', Main);",
            "bindings.set('funkin.backend.system.framerate.Framerate', CodenameFramerateCompat.facade());",
        ):
            with self.subTest(mapping=mapping):
                self.assertIn(mapping, source)
        self.assertNotIn("FramerateCounter'", source,
                         "the native engine has no source-equivalent FramerateCounter")

        main_source = (ROOT / "source/Main.hx").read_text()
        self.assertIn("public static var instance:Main;", main_source)
        self.assertIn("\t\tinstance = this;", main_source)
        self.assertLess(main_source.index("fpsCounter = new FPS("),
                        main_source.index("addChild(new FlxGame("),
                        "initial-state owner scripts need the counter before FlxGame creates the state")
        self.assertGreater(main_source.index("addChild(fpsCounter);"),
                           main_source.index("addChild(new FlxGame("),
                           "the native FPS counter must still render above the game")

    def test_type_timer_and_memory_facades_call_real_runtime_apis(self):
        source = (ROOT / "source/CodenameImportBindings.hx").read_text()
        type_method = extract_method(source, "public static function typeConstants")
        timer_method = extract_method(source, "public static function timerConstants")
        memory_method = extract_method(source, "public static function memoryUtilConstants")

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            system = base / "openfl/system/System.hx"
            system.parent.mkdir(parents=True)
            system.write_text("""package openfl.system;
class System { public static var totalMemoryNumber:Float = 0; }
""", newline='\n')
            (base / "Main.hx").write_text(f'''import hscript.Interp;
import haxe.Timer as HaxeTimer;
import openfl.system.System;
class CodenameImportBindings {{
 {type_method}
 {timer_method}
 {memory_method}
}}
class Sample {{ public function new() {{}} }}
class Main {{
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {{
  System.totalMemoryNumber = 987654.5;
  var typeFacade = CodenameImportBindings.typeConstants();
  var timerFacade = CodenameImportBindings.timerConstants();
  var memoryFacade = CodenameImportBindings.memoryUtilConstants();
  var allowed:Map<String,Dynamic> = new Map();
  allowed.set("Type", typeFacade);
  allowed.set("haxe.Timer", timerFacade);
  allowed.set("funkin.backend.utils.MemoryUtil", memoryFacade);
  var parsed = CodenameScriptParser.prepare(
   'import Type; import haxe.Timer; import funkin.backend.utils.MemoryUtil; '
   + 'function inspect(value) return [Type.getClassName(Type.getClass(value)), '
   + 'Timer.stamp(), MemoryUtil.currentMemUsage()];', allowed);
  check(parsed.program != null && parsed.diagnostics.length == 0,
   parsed.diagnostics.length == 0 ? "no program" : parsed.diagnostics[0].message);
  var interp = new Interp();
  interp.variables.set("Type", typeFacade);
  interp.variables.set("Timer", timerFacade);
  interp.variables.set("MemoryUtil", memoryFacade);
  interp.execute(parsed.program);
  var result:Array<Dynamic> = interp.variables.get("inspect")(new Sample());
  check(result[0] == "Sample", "Type reflection changed: " + result[0]);
  check(result[1] > 0, "Timer.stamp did not return its real monotonic clock");
  check(result[2] == 987654.5, "MemoryUtil did not read current process memory");
 }}
}}
''', newline='\n')
            result = run_haxe(base)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_openfl_constructors_and_native_main_framerate_adapter(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            sprite = base / "openfl/display/Sprite.hx"
            sprite.parent.mkdir(parents=True)
            sprite.write_text("""package openfl.display;
class Sprite {
 public var x:Float = 0; public var y:Float = 0; public var visible:Bool = true;
 public var children:Array<Dynamic> = [];
 public function new() {}
 public function addChild(child:Dynamic):Dynamic { children.push(child); return child; }
 public function removeChild(child:Dynamic):Dynamic { children.remove(child); return child; }
}
""", newline='\n')
            fps = base / "openfl/display/FPS.hx"
            fps.write_text("""package openfl.display;
class FPS extends Sprite {
 public var currentFPS:Int = 60;
 public var textWidth:Float = 20;
 public function new(x:Float=0, y:Float=0, color:Int=0) { super(); this.x=x; this.y=y; }
}
""", newline='\n')
            text_field = base / "openfl/text/TextField.hx"
            text_field.parent.mkdir(parents=True)
            text_field.write_text("""package openfl.text;
class TextField {
 public var text:String = ""; public var x:Float=0; public var y:Float=0;
 public var width:Float=0; public var height:Float=0; public var autoSize:Dynamic;
 public var defaultTextFormat:TextFormat; public var selectable:Bool=true;
 public function new() {}
}
""", newline='\n')
            (text_field.parent / "TextFormat.hx").write_text("""package openfl.text;
class TextFormat {
 public var leading:Float=0;
 public function new(font:String="_sans", size:Int=12, color:Int=0) {}
}
""", newline='\n')
            (base / "Main.hx").write_text('''import hscript.Interp;
import openfl.display.FPS;
import openfl.display.Sprite;
import openfl.text.TextField;
import openfl.text.TextFormat;
class Main extends Sprite {
 public static var instance:Main;
 public static var fpsCounter:FPS;
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  instance = new Main(); fpsCounter = new FPS(10, 3, 0xFFFFFF);
  var allowed:Map<String,Dynamic> = new Map();
  allowed.set("openfl.display.FPS", FPS);
  allowed.set("openfl.display.Sprite", Sprite);
  allowed.set("openfl.text.TextField", TextField);
  allowed.set("openfl.text.TextFormat", TextFormat);
  allowed.set("funkin.backend.system.Main", Main);
  allowed.set("funkin.backend.system.framerate.Framerate", CodenameFramerateCompat.facade());
  var parsed = CodenameScriptParser.prepare(
   'import openfl.display.FPS; import openfl.display.Sprite; '
   + 'import openfl.text.TextField; import openfl.text.TextFormat; '
   + 'import funkin.backend.system.Main; '
   + 'import funkin.backend.system.framerate.Framerate; '
   + 'var counter = new FPS(4, 7, 0xFFFFFFFF); var layer = new Sprite(); '
   + 'var label = new TextField(); var format = new TextFormat("_sans", 15, 0xFFFFFFFF); '
   + 'Framerate.debugMode = 2; Framerate.instance.visible = false; '
   + 'Framerate.instance.y = 12; Main.instance.addChild(layer); '
   + 'function inspect() return [counter.x, counter.y, label != null, format != null, '
   + 'Framerate.debugMode, Framerate.instance.visible, Framerate.instance.y, '
   + 'Main.instance.children.length];', allowed);
  check(parsed.program != null && parsed.diagnostics.length == 0,
   parsed.diagnostics.length == 0 ? "no program" : parsed.diagnostics[0].message);
  var interp = new Interp();
  interp.variables.set("FPS", FPS); interp.variables.set("Sprite", Sprite);
  interp.variables.set("TextField", TextField); interp.variables.set("TextFormat", TextFormat);
  interp.variables.set("Main", Main); interp.variables.set("Framerate", CodenameFramerateCompat.facade());
  interp.execute(parsed.program);
  var observed:Array<Dynamic> = interp.variables.get("inspect")();
  check(observed[0] == 4 && observed[1] == 7, "FPS constructor lost its coordinates");
  check(observed[2] && observed[3], "OpenFL text constructors did not run");
  check(observed[4] == 2 && observed[5] == false && observed[6] == 12,
   "Framerate did not control the live FPS counter");
  check(observed[7] == 1, "Main.instance was not the live display root");
 }
}
''', newline='\n')
            result = run_haxe(base)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
