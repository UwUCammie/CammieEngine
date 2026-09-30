"""Exercise the Codename group/text constructors through small source fixtures."""
from pathlib import Path
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


class CodenameTextGroupBindingsTest(unittest.TestCase):
    def test_shared_import_names_and_context_constructors(self):
        bindings = (ROOT / "source/CodenameImportBindings.hx").read_text()
        interp_source = (ROOT / "source/CodenameScriptInterp.hx").read_text()
        for import_path in (
            "flixel.group.FlxSpriteGroup",
            "flixel.addons.text.FlxTypeText",
            "funkin.backend.FunkinText",
            "funkin.ui.FunkinText",
            "haxe.Json",
        ):
            self.assertIn(f"bindings.set('{import_path}'", bindings)
        self.assertIn("bindings.set('flixel.group.FlxSpriteGroup', FlxTypedSpriteGroup);", bindings)
        self.assertIn("bindings.set('flixel.group.FlxGroup', FlxTypedGroup);", bindings)
        self.assertIn("CodenameFunkinText.fromArgs(args, paths)", interp_source)
        self.assertIn("name.substr(name.lastIndexOf('.') + 1)",
                      (ROOT / "source/CodenameModBindings.hx").read_text())
        self.assertIn("interp.variables.set('FlxGroup', FlxTypedGroup);",
                      (ROOT / "source/CodenameModBindings.hx").read_text())

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            stubs = {
                "CodenamePaths.hx": '''class CodenamePaths {
 public var root:String; public var fontCalls:Array<String>=[]; public var missingFont:Bool=false;
 public function new(root:String) this.root=root;
 public function font(key:String):String { fontCalls.push(key); if(missingFont) throw "missing owner font"; return root + "/fonts/" + key; }
}''',
                "FNFAssets.hx": '''class FNFAssets {
 public static var defaultFontExists:Bool=false;
 public static function exists(path:String):Bool return defaultFontExists && path=="assets/fonts/vcr.ttf";
}''',
                "flixel/FlxSprite.hx": '''package flixel;
class FlxSprite { public var x:Float=0; public var y:Float=0; public function new(x:Float=0,y:Float=0) { this.x=x;this.y=y; } }''',
                "flixel/util/FlxColor.hx": '''package flixel.util;
enum abstract FlxColor(Int) from Int to Int { var WHITE=0xFFFFFFFF; var BLACK=0xFF000000; var TRANSPARENT=0; }''',
                "flixel/text/FlxText.hx": '''package flixel.text;
import flixel.FlxSprite;
import flixel.util.FlxColor;
enum abstract FlxTextBorderStyle(Int) from Int to Int { var NONE=0; var OUTLINE=1; }
class FlxText extends FlxSprite {
 public var text:String=""; public var width:Float=0; public var size:Int=8;
 public var font:String=""; public var color:FlxColor=FlxColor.WHITE;
 public var borderStyle:FlxTextBorderStyle=FlxTextBorderStyle.NONE;
 public var borderSize:Float=1; public var borderColor:FlxColor=FlxColor.TRANSPARENT;
 public function new(X:Float=0,Y:Float=0,FieldWidth:Float=0,?Text:String,Size:Int=8,EmbeddedFont:Bool=true) {
  super(X,Y); width=FieldWidth;text=Text==null?"":Text;size=Size;
 }
 public function setFormat(?Font:String,Size:Int=8,Color:FlxColor=FlxColor.WHITE,?Alignment:Dynamic,
  ?BorderStyle:FlxTextBorderStyle,BorderColor:FlxColor=FlxColor.TRANSPARENT,EmbeddedFont:Bool=true):FlxText {
  if(Font!=null) font=Font; size=Size;color=Color;
  borderStyle=BorderStyle==null?FlxTextBorderStyle.NONE:BorderStyle;borderColor=BorderColor;return this;
 }
}''',
                "flixel/addons/text/FlxTypeText.hx": '''package flixel.addons.text;
import flixel.text.FlxText;
class FlxTypeText extends FlxText {
 public var delay:Float=0.05; public var started:Bool=false; public var resets:Int=0;
 public function new(x:Float=0,y:Float=0,width:Int=0,text:String="",size:Int=8,embeddedFont:Bool=true)
  super(x,y,width,text,size,embeddedFont);
 public function resetText(value:String):Void { text=value;resets++; }
 public function start(?delay:Float):Void { if(delay!=null) this.delay=delay; started=true; }
}''',
                "flixel/group/FlxSpriteGroup.hx": '''package flixel.group;
import flixel.FlxSprite;
typedef FlxSpriteGroup=FlxTypedSpriteGroup<FlxSprite>;
class FlxTypedSpriteGroup<T:FlxSprite> extends FlxSprite {
 public var members:Array<T>=[];
 public function new(x:Float=0,y:Float=0,maxSize:Int=0) super(x,y);
 public function add(value:T):T { members.push(value);return value; }
}''',
            }
            for name, content in stubs.items():
                path = base / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)

            json_method = extract_method(bindings, "public static function jsonConstants")
            (base / "CodenameImportBindings.hx").write_text(
                "class CodenameImportBindings {\n" + json_method + "\n}"
            )
            (base / "Main.hx").write_text('''import hscript.Interp;
import hscript.Parser;
import flixel.group.FlxSpriteGroup.FlxTypedSpriteGroup;
import flixel.addons.text.FlxTypeText;
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main():Void {
  var parser=new Parser(); var interp=new Interp();
  interp.variables.set("FlxSpriteGroup",FlxTypedSpriteGroup);
  interp.variables.set("FlxTypeText",FlxTypeText);
  interp.execute(parser.parseString('group = new FlxSpriteGroup(3, 4); '
   +'typed = new FlxTypeText(5, 6, 200, "hello", 18); group.add(typed); '
   +'typed.resetText("ready"); typed.start(0.02);'));
  var group:FlxTypedSpriteGroup<flixel.FlxSprite>=interp.variables.get("group");
  var typed:FlxTypeText=interp.variables.get("typed");
  check(group.x==3 && group.y==4 && group.members.length==1 && group.members[0]==typed,
   "FlxSpriteGroup alias and add behavior");
  check(typed.text=="ready" && typed.started && typed.delay==0.02 && typed.resets==1,
   "FlxTypeText reset/start behavior");

  var paths=new CodenamePaths("selected-owner");
  var text=CodenameFunkinText.fromArgs([10,20,300,"lyrics",32],paths);
  check(text.x==10 && text.y==20 && text.width==300 && text.text=="lyrics" && text.size==32,
   "FunkinText supplied constructor args");
  check(text.font=="selected-owner/fonts/vcr.ttf" && paths.fontCalls.join(",")=="vcr.ttf",
   "FunkinText resolves default font from selected owner");
  check(text.borderStyle==flixel.text.FlxText.FlxTextBorderStyle.OUTLINE && text.borderSize==1
   && text.borderColor==flixel.util.FlxColor.BLACK && text.zoomFactor==1
   && text.zoomFactorEnabled && text.angleFactor==1 && text.angleFactorEnabled,
   "FunkinText Codename defaults");
  var noBorder=CodenameFunkinText.fromArgs([0,0,0,"plain",null,false],paths);
  check(noBorder.size==16 && noBorder.borderStyle==flixel.text.FlxText.FlxTextBorderStyle.NONE,
   "FunkinText default size and no-border variant");
  FNFAssets.defaultFontExists=true;
  var fallbackPaths=new CodenamePaths("owner-without-vcr"); fallbackPaths.missingFont=true;
  var fallback=CodenameFunkinText.fromArgs([],fallbackPaths);
  check(fallback.font=="assets/fonts/vcr.ttf", "shared engine default font fallback");

  var json=CodenameImportBindings.jsonConstants();
  interp.variables.set("Json",json);
  interp.execute(parser.parseString("decoded = Json.parse('{\\\"lyrics\\\":[1,2]}'); "
   +"encoded = Json.stringify(decoded);"));
  var decoded:Dynamic=interp.variables.get("decoded");
  check(decoded.lyrics.length==2 && decoded.lyrics[1]==2
   && haxe.Json.parse(interp.variables.get("encoded")).lyrics[0]==1,
   "haxe.Json facade parse/stringify behavior");
 }
}''')
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"), "-cp", str(base),
                 "--run", "Main"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
