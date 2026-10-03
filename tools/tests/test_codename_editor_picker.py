"""Exercise HL17's key-7 EditorPicker handoff without launching the game."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
DONOR_MENU = (
    Path("/run/media/cammie/External Storage/FNF-Example-Mods")
    / "codename/hl17_v3/mods/HL17/data/states/HL17MainMenu.hx"
)


class CodenameEditorPickerTest(unittest.TestCase):
    def test_key7_opens_picker_and_native_routes_report_support(self):
        if DONOR_MENU.is_file():
            donor = DONOR_MENU.read_text(encoding="utf-8")
            self.assertIn("FlxG.keys.justPressed.SEVEN", donor)
            self.assertIn("openSubState(new EditorPicker())", donor)

        bindings = (ROOT / "source/CodenameModBindings.hx").read_text(encoding="utf-8")
        self.assertIn(
            "result.set('funkin.editors.EditorPicker', CodenameEditorPickerCompat);",
            bindings,
        )

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "flixel/FlxG.hx").parent.mkdir(parents=True, exist_ok=True)
            (base / "flixel/FlxG.hx").write_text("""package flixel;
class FlxG {
 public static var width:Int=1280; public static var height:Int=720;
 public static var keys:Dynamic={justPressed:{SEVEN:true,ESCAPE:false,BACKSPACE:false,
  UP:false,DOWN:false,ENTER:false,SPACE:false}};
 public static var lastOpenedURL:String='';
 public static function openURL(url:String):Void lastOpenedURL=url;
}
""", newline='\n')
            (base / "flixel/FlxSprite.hx").write_text("""package flixel;
class FlxSprite {
 public var x:Float; public var y:Float; public var width:Float=0; public var height:Float=0;
 public var alpha:Float=1;
 public function new(X:Float=0,Y:Float=0) {x=X;y=Y;}
 public function makeGraphic(Width:Int,Height:Int,color:Int):FlxSprite {
  width=Width;height=Height;return this;
 }
 public function setGraphicSize(Width:Int,Height:Int):Void {width=Width;height=Height;}
 public function updateHitbox():Void {}
}
""", newline='\n')
            (base / "flixel/FlxSubState.hx").write_text("""package flixel;
class FlxSubState {
 public var members:Array<Dynamic>=[]; public var closed:Bool=false;
 public function new() {}
 public function create():Void {}
 public function update(elapsed:Float):Void {}
 public function close():Void closed=true;
 public function add<T>(item:T):T {members.push(item);return item;}
}
""", newline='\n')
            (base / "flixel/text/FlxText.hx").parent.mkdir(parents=True, exist_ok=True)
            (base / "flixel/text/FlxText.hx").write_text("""package flixel.text;
import flixel.FlxSprite;
enum abstract FlxTextAlign(String) {var CENTER='center';}
class FlxText extends FlxSprite {
 public var text:String; public var alignment:FlxTextAlign; public var size:Int;
 public var fieldWidth:Float;
 public function new(X:Float,Y:Float,Width:Float,Text:String,Size:Int=8) {
  super(X,Y); text=Text;fieldWidth=Width;size=Size;height=Size+3;
 }
 public function setFormat(?font:String,Size:Int=8,color:Int=0xFFFFFF,
   ?Align:FlxTextAlign):FlxText {
  size=Size;if(Align!=null) alignment=Align;return this;
 }
 override public function updateHitbox():Void {
  width=fieldWidth;height=size+3;
 }
}
""", newline='\n')
            (base / "flixel/ui/FlxButton.hx").parent.mkdir(parents=True, exist_ok=True)
            (base / "flixel/ui/FlxButton.hx").write_text("""package flixel.ui;
import flixel.FlxSprite;
import flixel.text.FlxText;
class LabelOffset { public var x:Float; public var y:Float;
 public function new(X:Float=0,Y:Float=0) {x=X;y=Y;}
}
class FlxButton extends FlxSprite {
 public var text:String; public var label:FlxText;
 public var labelOffsets:Array<LabelOffset>=[new LabelOffset(),new LabelOffset(),
  new LabelOffset(),new LabelOffset()];
 var callback:Void->Void;
 public function new(X:Float,Y:Float,Text:String,OnClick:Void->Void) {
  super(X,Y); text=Text; callback=OnClick;label=new FlxText(X,Y,80,Text);
 }
 public function click():Void if(callback!=null) callback();
}
""", newline='\n')
            (base / "ChartingState.hx").write_text("""class ChartingState { public function new(){} }
""", newline='\n')
            (base / "LoadingState.hx").write_text("""class LoadingState {
 public static var lastState:Dynamic;
 public static function loadAndSwitchState(state:Dynamic):Void lastState=state;
}
""", newline='\n')
            (base / "Main.hx").write_text(r'''import hscript.Interp;
import flixel.ui.FlxButton;
import flixel.text.FlxText.FlxTextAlign;
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function checkButton(button:FlxButton):Void {
  check(button.width==348 && button.height==44,"picker button hitbox was not sized");
  check(button.label.fieldWidth==button.width,"button label field did not match the hitbox width");
  check(button.label.size==16 && button.label.alignment==FlxTextAlign.CENTER,
   "button label was not enlarged and centered");
  check(Math.abs(button.label.y-(button.y+(button.height-button.label.height)*0.5))<0.01,
   "button label was not vertically centered");
  for(offset in button.labelOffsets)
   check(offset.x==0 && Math.abs(offset.y-(button.height-button.label.height)*0.5)<0.01,
    "button state offset would move the centered label");
 }
 static function main():Void {
  var imports:Map<String,Dynamic>=new Map();
  imports.set("funkin.editors.EditorPicker",CodenameEditorPickerCompat);
  var parsed=CodenameScriptParser.prepare(
   'import funkin.editors.EditorPicker; '
   + 'if (FlxG.keys.justPressed.SEVEN) { persistentUpdate=false; persistentDraw=true; '
   + 'openSubState(new EditorPicker()); }', imports, "data/states/HL17MainMenu.hx");
  if(parsed.program==null || parsed.diagnostics.length!=0)
   throw "HL17 key-7 script did not bind the shared EditorPicker: "+parsed.diagnostics;
  var interp=new Interp(); var opened:Dynamic=null;
  interp.variables.set("FlxG",flixel.FlxG);
  interp.variables.set("EditorPicker",CodenameEditorPickerCompat);
  interp.variables.set("persistentUpdate",true); interp.variables.set("persistentDraw",false);
  interp.variables.set("openSubState",function(value:Dynamic):Void opened=value);
  interp.execute(parsed.program);
  check(opened!=null && Std.isOfType(opened,CodenameEditorPickerCompat),
   "SEVEN did not construct and open the compatibility picker");
  check(interp.variables.get("persistentUpdate")==false
   && interp.variables.get("persistentDraw")==true,"key-7 persistence flags were lost");
  var picker:CodenameEditorPickerCompat=cast opened; picker.create();
  check(picker.options.length>=5 && picker.choiceButtons.length==picker.options.length,
   "source EditorPicker choices were not preserved in the shared adapter");
  check(Reflect.field(picker.options[0],"name")=="Chart Editor"
   && Reflect.field(picker.options[1],"name")=="Character Editor"
   && Reflect.field(picker.options[2],"name")=="Stage Editor"
   && Reflect.field(picker.options[3],"name")=="Alphabet Editor"
   && Reflect.field(picker.options[picker.options.length-1],"name")=="Wiki",
   "EditorPicker source choice order or Wiki entry changed");
  for(button in picker.choiceButtons) checkButton(button);
  checkButton(picker.backButton);
  picker.choiceButtons[0].click();
  check(Std.isOfType(LoadingState.lastState,ChartingState),
   "Chart Editor choice did not route to the native chart editor");
  picker.choose(1);
  check(flixel.FlxG.lastOpenedURL=="","unsupported Character Editor unexpectedly opened a link");
  picker.choiceButtons[picker.choiceButtons.length-1].click();
  check(flixel.FlxG.lastOpenedURL=="https://codename-engine.com/",
   "Wiki choice did not use the Codename destination");
  var back:CodenameEditorPickerCompat=new CodenameEditorPickerCompat(); back.create();
  back.backButton.click(); check(back.closed,"Back button did not close the picker");
  var escape:CodenameEditorPickerCompat=new CodenameEditorPickerCompat(); escape.create();
  flixel.FlxG.keys.justPressed.ESCAPE=true; escape.update(0);
  check(escape.closed,"Escape did not close the picker");
 }
}''', newline='\n')
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
        self.assertIn("[codename-editor-picker-partial] Chart Editor", result.stdout + result.stderr)
        self.assertIn("[codename-editor-picker-unsupported] Character Editor", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
