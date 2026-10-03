"""Run the Codename import enum facade without the native game target."""
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


class CodenameImportBindingsTest(unittest.TestCase):
    def test_codename_point_bindings_execute_imported_and_implicit_points(self):
        source = (ROOT / "source/CodenameImportBindings.hx").read_text()
        self.assertIn("bindings.set('flixel.math.FlxBasePoint', FlxBasePoint);", source)
        self.assertIn("bindings.set('flixel.math.FlxPoint', pointConstants());", source)
        self.assertIn("interp.variables.set('FlxPoint', CodenameImportBindings.pointConstants());",
                      (ROOT / "source/PlayState.hx").read_text())
        method = extract_method(source, "public static function pointConstants")
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            stub = base / "flixel/math/FlxPoint.hx"
            stub.parent.mkdir(parents=True)
            stub.write_text('''package flixel.math;
class FlxPoint {
 public static function get(x:Float=0,y:Float=0):FlxBasePoint return new FlxBasePoint(x,y);
 public static function weak(x:Float=0,y:Float=0):FlxBasePoint return new FlxBasePoint(x,y);
}
class FlxBasePoint {
 public var x:Float; public var y:Float;
 public function new(x:Float=0,y:Float=0) { this.x=x; this.y=y; }
 public function set(x:Float,y:Float):FlxBasePoint { this.x=x; this.y=y; return this; }
}
''', newline='\n')
            (base / "Main.hx").write_text(f'''import hscript.Interp;
import flixel.math.FlxPoint;
import flixel.math.FlxPoint.FlxBasePoint;
class Facade {{ {method} }}
class Main {{
 static function main():Void {{
  var allowed:Map<String,Dynamic>=new Map();
  allowed.set("flixel.math.FlxBasePoint",FlxBasePoint);
  allowed.set("flixel.math.FlxPoint",Facade.pointConstants());
  var parsed=CodenameScriptParser.prepare(
   'import flixel.math.FlxBasePoint; var movement = new FlxBasePoint(); var rating = FlxPoint.get(-450, 300); movement.set(23, 0); function values() return [movement.x, movement.y, rating.x, rating.y];',allowed);
  if(parsed.program==null || parsed.diagnostics.length!=0)
   throw parsed.diagnostics.length==0 ? "no program" : parsed.diagnostics[0].message;
  var interp=new Interp();
  interp.variables.set("FlxBasePoint",FlxBasePoint);
  interp.variables.set("FlxPoint",Facade.pointConstants());
  interp.execute(parsed.program);
  var observed:Array<Dynamic>=interp.variables.get("values")();
  if(observed[0]!=23 || observed[1]!=0 || observed[2]!=-450 || observed[3]!=300)
   throw "Codename point values changed: " + observed;
 }}
}}
''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(base), "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_stringtools_import_uses_a_reflectable_static_facade(self):
        source = (ROOT / "source/CodenameImportBindings.hx").read_text()
        self.assertIn("bindings.set('StringTools', stringToolsConstants());", source)
        method = extract_method(source, "public static function stringToolsConstants")
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "Main.hx").write_text(f'''import hscript.Interp;
class CodenameImportBindings {{
 {method}
}}
class Main {{
 static function main():Void {{
  var facade = CodenameImportBindings.stringToolsConstants();
  var allowed:Map<String, Dynamic> = new Map();
  allowed.set("StringTools", facade);
  var parsed = CodenameScriptParser.prepare('import StringTools; var result = StringTools.replace("a>b<c", ">", ""); function getResult() return result;', allowed);
  if (parsed.program == null || parsed.diagnostics.length != 0)
   throw "StringTools import was not accepted by the Codename parser";
  var interp = new Interp();
  interp.variables.set("StringTools", facade);
  interp.execute(parsed.program);
  var getResult:Dynamic = interp.variables.get("getResult");
  var observed:String = cast getResult();
  if (observed != "ab<c")
   throw "StringTools replacement facade changed source semantics: " + observed;
 }}
}}''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(base),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), "--run", "Main"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_flx_string_util_import_delegates_to_flixel_format_money(self):
        bindings_source = (ROOT / "source/CodenameImportBindings.hx").read_text()
        self.assertIn("bindings.set('flixel.util.FlxStringUtil', flxStringUtilConstants());",
                      bindings_source)
        self.assertIn("bindings.set('CodenameKeyValueIterator', CodenameKeyValueIterator.facade());",
                      bindings_source)
        facade_method = extract_method(bindings_source, "public static function flxStringUtilConstants")
        flixel_source = (ROOT / ".haxelib/flixel/6,1,2/flixel/util/FlxStringUtil.hx").read_text()
        format_money_method = extract_method(flixel_source, "public static function formatMoney")

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            flx_string_util = base / "flixel/util/FlxStringUtil.hx"
            flx_string_util.parent.mkdir(parents=True)
            flx_string_util.write_text(
                "package flixel.util;\nclass FlxStringUtil {\n"
                + format_money_method
                + "\n}"
            , newline='\n')
            (base / "Main.hx").write_text(f'''import hscript.Interp;
import flixel.util.FlxStringUtil;
class CodenameImportBindings {{
 {facade_method}
}}
class Main {{
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {{
  var facade = CodenameImportBindings.flxStringUtilConstants();
  var allowed:Map<String, Dynamic> = new Map();
  allowed.set("flixel.util.FlxStringUtil", facade);
  var parsed = CodenameScriptParser.prepare(
   'import flixel.util.FlxStringUtil; '
   + 'function scoreText(score) return "Score: " + FlxStringUtil.formatMoney(score, false, true); '
   + 'function negativeScore() return FlxStringUtil.formatMoney(-1234567.89, false, true); '
   + 'function defaultMoney() return FlxStringUtil.formatMoney(1234.5); '
   + 'function europeanMoney() return FlxStringUtil.formatMoney(1234567.89, true, false);', allowed);
  check(parsed.program != null && parsed.diagnostics.length == 0,
   parsed.diagnostics.length == 0 ? "imports produced no program" : parsed.diagnostics[0].message);
  var interp = new Interp();
  interp.variables.set("FlxStringUtil", facade);
  interp.execute(parsed.program);
  var scoreText:Dynamic = interp.variables.get("scoreText");
  var negativeScore:Dynamic = interp.variables.get("negativeScore");
  var defaultMoney:Dynamic = interp.variables.get("defaultMoney");
  var europeanMoney:Dynamic = interp.variables.get("europeanMoney");
  check(scoreText(1234567.89) == "Score: 1,234,567",
   "FlxStringUtil.formatMoney lost the donor's integer English score format");
  check(negativeScore() == "-1,234,567", "negative score formatting changed");
  check(defaultMoney() == "1,234.50", "Flixel's default decimal arguments changed");
  check(europeanMoney() == "1.234.567,88", "Flixel's localized decimal/comma rules changed");
 }}
}}''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(base), "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), "--run", "Main"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_top_level_fltweentype_import_is_explicitly_bound(self):
        source = (ROOT / "source/CodenameImportBindings.hx").read_text()
        method = extract_method(source, "public static function tweenTypeConstants")
        self.assertIn("bindings.set('flixel.tweens.FlxTweenType', tweenTypeConstants());", source)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            tween = base / "flixel/tweens/FlxTween.hx"
            tween.parent.mkdir(parents=True)
            tween.write_text("""package flixel.tweens;
enum abstract FlxTweenType(Int) from Int to Int {
 var PERSIST=1; var LOOPING=2; var PINGPONG=4; var ONESHOT=8; var BACKWARD=16;
}
""", newline='\n')
            (base / "Main.hx").write_text(f'''import hscript.Interp;
import flixel.tweens.FlxTween.FlxTweenType;
class Facade {{
 {method}
}}
class Main {{
 static function main():Void {{
  var values=Facade.tweenTypeConstants();
  var allowed:Map<String,Dynamic>=new Map();
  allowed.set("flixel.tweens.FlxTweenType",values);
  var parsed=CodenameScriptParser.prepare(
    'import flixel.tweens.FlxTweenType; function getFlag() return FlxTweenType.PERSIST;',allowed);
  if(parsed.program==null || parsed.diagnostics.length!=0)
    throw parsed.diagnostics.length==0 ? "no parsed program" : parsed.diagnostics[0].message;
  var interp=new Interp(); interp.variables.set("FlxTweenType",values);
  interp.execute(parsed.program);
  var getFlag:Dynamic=interp.variables.get("getFlag");
  if(getFlag==null || getFlag()!=1) throw "top-level FlxTweenType import lost its enum constant";
 }}
}}
''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(base), "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_tween_enum_abstract_is_exposed_as_runtime_constants(self):
        source = (ROOT / "source/CodenameImportBindings.hx").read_text()
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "public static function tweenTypeConstants",
                "public static function blendModeConstants",
                "public static function barFillDirectionConstants",
                "public static function textBorderStyleConstants",
            )
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            tween = base / "flixel/tweens/FlxTween.hx"
            tween.parent.mkdir(parents=True)
            tween.write_text("""package flixel.tweens;
enum abstract FlxTweenType(Int) from Int to Int {
 var PERSIST=1; var LOOPING=2; var PINGPONG=4; var ONESHOT=8; var BACKWARD=16;
}
""", newline='\n')
            (base / "openfl/display/BlendMode.hx").parent.mkdir(parents=True)
            (base / "openfl/display/BlendMode.hx").write_text("""package openfl.display;
enum abstract BlendMode(Int) from Int to Int {
 var ADD=0; var ALPHA=1; var DARKEN=2; var DIFFERENCE=3; var ERASE=4;
 var HARDLIGHT=5; var INVERT=6; var LAYER=7; var LIGHTEN=8; var MULTIPLY=9;
 var NORMAL=10; var OVERLAY=11; var SCREEN=12; var SHADER=13; var SUBTRACT=14;
}
""", newline='\n')
            (base / "flixel/ui/FlxBar.hx").parent.mkdir(parents=True)
            (base / "flixel/ui/FlxBar.hx").write_text("""package flixel.ui;
class FlxBar {}
enum FlxBarFillDirection { LEFT_TO_RIGHT; RIGHT_TO_LEFT; TOP_TO_BOTTOM; BOTTOM_TO_TOP;
 HORIZONTAL_INSIDE_OUT; HORIZONTAL_OUTSIDE_IN; VERTICAL_INSIDE_OUT; VERTICAL_OUTSIDE_IN; }
""", newline='\n')
            (base / "flixel/text/FlxText.hx").parent.mkdir(parents=True)
            (base / "flixel/text/FlxText.hx").write_text("""package flixel.text;
class FlxText {}
enum FlxTextBorderStyle { NONE; SHADOW; SHADOW_XY(offsetX:Float,offsetY:Float); OUTLINE; OUTLINE_FAST; }
""", newline='\n')
            (base / "Main.hx").write_text(f"""import flixel.tweens.FlxTween.FlxTweenType;
import openfl.display.BlendMode;
import flixel.ui.FlxBar.FlxBarFillDirection;
import flixel.text.FlxText.FlxTextBorderStyle;
class Main {{
 {methods}
 static function main():Void {{
  var values=tweenTypeConstants();
  if (values.PERSIST!=1 || values.LOOPING!=2 || values.PINGPONG!=4
   || values.ONESHOT!=8 || values.BACKWARD!=16)
   throw 'Codename tween flags changed';
  var blend=blendModeConstants();
  if (blend.ADD!=0 || blend.MULTIPLY!=9 || blend.SCREEN!=12 || blend.SUBTRACT!=14)
   throw 'Codename blend modes changed';
  var direction=barFillDirectionConstants();
  if (Type.enumConstructor(direction.LEFT_TO_RIGHT)!='LEFT_TO_RIGHT'
   || Type.enumConstructor(direction.VERTICAL_OUTSIDE_IN)!='VERTICAL_OUTSIDE_IN')
   throw 'Codename bar fill directions changed';
  var border=textBorderStyleConstants();
  if (Type.enumConstructor(border.NONE)!='NONE' || Type.enumConstructor(border.OUTLINE_FAST)!='OUTLINE_FAST'
   || Type.enumConstructor(border.SHADOW_XY(3,4))!='SHADOW_XY')
   throw 'Codename text border styles changed';
 }}
}}
""", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", directory, "--run", "Main"],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
