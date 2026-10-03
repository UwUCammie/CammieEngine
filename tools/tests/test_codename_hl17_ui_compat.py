"""Exercise the owner-scoped HL17 UI subset with deterministic Flixel stubs."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
import os


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


STUBS = {
    "flixel/FlxBasic.hx": '''package flixel;
class FlxBasic {
 public var exists:Bool=true; public var active:Bool=true; public var visible:Bool=true;
 public function new() {} public function update(elapsed:Float):Void {}
 public function destroy():Void { exists=false; }
}
''',
    "flixel/math/FlxPoint.hx": '''package flixel.math;
class FlxPoint {
 public var x:Float; public var y:Float;
 public function new(x:Float=0,y:Float=0) { this.x=x; this.y=y; }
 public static function get(x:Float=0,y:Float=0):FlxPoint return new FlxPoint(x,y);
 public function set(x:Float=0,y:Float=0):FlxPoint { this.x=x;this.y=y;return this; }
 public function put():Void {}
}
''',
    "flixel/util/FlxColor.hx": '''package flixel.util;
abstract FlxColor(Int) from Int to Int {
 public static inline var WHITE:FlxColor=0xFFFFFFFF;
 public static inline var TRANSPARENT:FlxColor=0x00000000;
}
''',
    "flixel/util/FlxDestroyUtil.hx": '''package flixel.util;
class FlxDestroyUtil { public static function put<T>(value:T):T return null; }
''',
    "flixel/FlxSprite.hx": '''package flixel;
import flixel.math.FlxPoint;
import flixel.util.FlxColor;
class FlxSprite extends FlxBasic {
 public var x:Float=0; public var y:Float=0; public var width:Float=0; public var height:Float=0;
 public var alpha:Float=1; public var antialiasing:Bool=true; public var scale:FlxPoint=new FlxPoint(1,1);
 public var offset:FlxPoint=new FlxPoint(); public var blend:Int=0; public var graphic:Dynamic; public var drawCalls:Int=0;
 public function new(x:Float=0,y:Float=0) { super();this.x=x;this.y=y; }
 public function setSize(width:Float,height:Float):Void { this.width=width;this.height=height; }
 public function makeGraphic(width:Int,height:Int,color:FlxColor=FlxColor.WHITE,unique:Bool=false,?key:String):FlxSprite { this.width=width;this.height=height;graphic={key:key==null?'generated':key};return this; }
 public function loadGraphic(graphic:flixel.system.FlxAssets.FlxGraphicAsset,animated:Bool=false,frameWidth:Int=0,frameHeight:Int=0,unique:Bool=false,?key:String):FlxSprite { width=200;height=100;this.graphic={key:'loaded'};return this; }
 public function draw():Void { drawCalls++; if(graphic==null)graphic={key:'flixel/images/logo/default.png'}; }
 public function updateHitbox():Void {}
}
''',
    "flixel/system/FlxAssets.hx": '''package flixel.system;
typedef FlxGraphicAsset = Dynamic;
''',
    "flixel/FlxState.hx": '''package flixel;
class FlxState {
 public var members:Array<FlxBasic>=[];
 public function new() {}
 public function add<T:FlxBasic>(basic:T):T { if(members.indexOf(basic)<0)members.push(basic);return basic; }
 public function remove<T:FlxBasic>(basic:T,splice:Bool=false):T { members.remove(basic);return basic; }
}
''',
    "flixel/input/FlxMouse.hx": '''package flixel.input;
class FlxMouse {
 public var x:Float=0;public var y:Float=0;public var justPressed:Bool=false;public var justReleased:Bool=false;
 public function new() {}
 public function overlaps(sprite:flixel.FlxSprite):Bool return sprite != null && x>=sprite.x && y>=sprite.y && x<=sprite.x+sprite.width && y<=sprite.y+sprite.height;
}
''',
    "flixel/input/FlxKeys.hx": '''package flixel.input;
class FlxKeyStatus { public var LEFT:Bool=false;public var RIGHT:Bool=false;public function new(){} }
class FlxKeys { public var justPressed:FlxKeyStatus=new FlxKeyStatus();public function new(){} }
''',
    "flixel/FlxG.hx": '''package flixel;
class FlxG {
 public static var width:Int=1280; public static var height:Int=720;
 public static var mouse:flixel.input.FlxMouse=new flixel.input.FlxMouse();
 public static var keys:flixel.input.FlxKeys=new flixel.input.FlxKeys();
}
''',
    "flixel/text/FlxText.hx": '''package flixel.text;
import flixel.FlxSprite;
import flixel.math.FlxPoint;
class FlxText extends FlxSprite {
 public var text(get,set):String;public var size(get,set):Int;public var color(get,set):flixel.util.FlxColor;public var font(get,set):String;
 public var fieldWidth:Float;
 public var textWriteCount:Int=0;public var sizeWriteCount:Int=0;public var colorWriteCount:Int=0;public var fontWriteCount:Int=0;
 var textValue:String='';var sizeValue:Int=16;var colorValue:flixel.util.FlxColor=0xFFFFFFFF;var fontValue:String='';
 static var nextGraphicKey:Int=0;
 public function new(x:Float=0,y:Float=0,fieldWidth:Float=0,text:String='',size:Int=8) { super(x,y);this.fieldWidth=fieldWidth;textValue=text;sizeValue=size;measure(); }
 function get_text():String return textValue;function set_text(value:String):String { textWriteCount++;textValue=value;measure();return value; }
 function get_size():Int return sizeValue;function set_size(value:Int):Int { sizeWriteCount++;sizeValue=value;measure();return value; }
 function get_color():flixel.util.FlxColor return colorValue;function set_color(value:flixel.util.FlxColor):flixel.util.FlxColor { colorWriteCount++;colorValue=value;measure();return value; }
 function get_font():String return fontValue;function set_font(value:String):String { fontWriteCount++;fontValue=value;measure();return value; }
 function measure():Void { width=fieldWidth<=0?textValue.length*sizeValue*0.5:fieldWidth;height=sizeValue+4;graphic={key:'text'+nextGraphicKey++,width:Std.int(width),height:Std.int(height)}; }
}
''',
    "CodenamePaths.hx": '''class CodenamePaths { public var root:String;public var fontNameCalls:Int=0;
 public function new(root:String)this.root=root;
 public function font(key:String):String return root+'/fonts/'+key;
 public function getFontName(path:String):String { fontNameCalls++; if(path!=root+'/fonts/verdana.ttf') throw 'wrong font path '+path; return 'Owner Family'; }
 }
''',
    "CodenameModRuntime.hx": '''class CodenameModRuntime {
 public static var exited:Bool=false;public static var activeRoot:String='owner-a';
 public static function isActiveOwner(root:String):Bool return root==activeRoot;
 public static function exitToNativeMenu():Void exited=true;
 }
''',
}


class CodenameHl17UiCompatTest(unittest.TestCase):
    def test_import_surface_widgets_lifecycle_and_safe_exit(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            for relative, content in STUBS.items():
                target = base / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, newline='\n')
            (base / "HL17UiTestMain.hx").write_text('''
import flixel.FlxState;
class HL17UiTestMain {
 static function check(ok:Bool,message:String):Void if(!ok)throw message;
 static function main():Void {
  var bindings:Map<String,Dynamic>=new Map();
  CodenameHL17UICompat.addBindings(bindings);
  for (name in ['HLUIComponent','HLUILabel','HLUIBox','HLUIButton','HLUITable',
    'HLUITab','HLUITabBox','HLUICheckbox','HLUINumberStepper','HLUIWindow',
    'funkin.hl.ui.HLUIWindow','Layout','funkin.hl.ui.Layout'])
   check(bindings.exists(name) && bindings.get(name)!=null,'missing import '+name);
  var parsed=CodenameScriptParser.prepare(
   'import HLUIBox; import HLUIButton; import Layout; '
   + 'var box=new HLUIBox(Layout.HORIZONTAL); var button=new HLUIButton("Go"); '
   + 'box.addComponent(button);',bindings,'hl17-test');
  check(parsed.program!=null && parsed.diagnostics.length==0,'HScript import preparation failed');
  var box=new HLUIBox(CodenameHL17UICompat.HORIZONTAL);
  var button=new HLUIButton('Go');box.addComponent(button);
  check(box._components.length==1 && box._components[0]==button,'box child ownership');
  var emptyWidget=new HLUIComponent();emptyWidget.draw();
  check(emptyWidget.drawCalls==0 && emptyWidget.graphic==null,
    'empty UI wrappers must bypass FlxSprite fallback-logo drawing');
  var graphicWidget=new HLUIComponent();graphicWidget.makeGraphic(20,10,0xFF333333);graphicWidget.draw();
  check(graphicWidget.drawCalls==1 && graphicWidget.graphic!=null,
    'explicit makeGraphic content must still draw');
  var loadedWidget=new HLUIComponent();loadedWidget.loadGraphic('owner-image');loadedWidget.draw();
  check(loadedWidget.drawCalls==1 && loadedWidget.graphic!=null,
    'explicitly loaded content must still draw');
  var window=new HLUIWindow(100,200,466,515);
  var windowBody=new HLUIComponent();windowBody.componentWidth=450;windowBody.componentHeight=120;
  windowBody.componentOffset.set(4,6);window.addComponent(windowBody);
  check(window._titlebar.y==window.y
    && windowBody.x==window.x+4 && windowBody.y==window.y+35+6,
    'window children must flow below the titlebar while retaining explicit offsets');
  var clicked=0;button.onClickCallback=function() clicked++;
  button.onClickCallback();
  check(clicked==1,'button callback');

  var paths=new CodenamePaths('owner-a');var claimed=0;
  box.bindOwner(paths,function(_) claimed++);
  check(button.ownerPaths.root=='owner-a','owner path was not inherited');
  var label=new HLUILabel('Ready');box.addComponent(label);
  var state=new FlxState();box.addThisAndChildComponentsToState(state);box.addThisAndChildComponentsToState(state);
  check(state.members.length==6 && claimed==6,'state mounting must be idempotent and claim each component');
  check(label.labelSprite.font=='Owner Family' && label.labelSprite.fieldWidth==0
    && label.labelSprite.width>1 && paths.fontNameCalls==2,
    'owner UI text must use the resolved font family, not the file path (font='
    +label.labelSprite.font+', calls='+paths.fontNameCalls+', owner='+label.ownerPaths.root+')');
  label.size=18;
  var stableFrameKey=label.labelSprite.graphic.key;
  var stableTextWrites=label.labelSprite.textWriteCount;
  var stableSizeWrites=label.labelSprite.sizeWriteCount;
  var stableColorWrites=label.labelSprite.colorWriteCount;
  var stableFontWrites=label.labelSprite.fontWriteCount;
  label.drawText();label.syncPosition();label.buildUI();
  check(label.labelSprite.graphic.key==stableFrameKey
    && label.labelSprite.textWriteCount==stableTextWrites
    && label.labelSprite.sizeWriteCount==stableSizeWrites
    && label.labelSprite.colorWriteCount==stableColorWrites
    && label.labelSprite.fontWriteCount==stableFontWrites,
    'unchanged HLUILabel styling must not regenerate its FlxText frame');
  label.text='Still ready';
  check(paths.fontNameCalls==2,'owner font family should be resolved once per label');
  box.removeThisAndChildComponentsFromState(state);
  check(state.members.length==0 && claimed==12,'state detach/claim callbacks');

  var table=new HLUITable([{columns:['A','B'],rows:[['one','two'],['three','four']]}],[80,90]);
  check(table._rows.length==3 && table._rows[1].labels[0].text=='one'
    && table._rows[2].index==1 && table._rows[1].y==table.y+30
    && table._rows[2].y==table.y+60
    && table._rows[1].labels[1].x>table._rows[1].labels[0].x,
    'table rows need ordered vertical layout and horizontal cells');
  table.selectRow(table._rows[2]);check(table.selectedRow==table._rows[2],'table selection');
  var tab=new HLUITab('Data',table);var tabbox=new HLUITabBox([tab],300,200);
  tabbox.tabContent=table;check(tabbox.tabContent==table && tab.selected,'tab content selection');
  var window=new HLUIWindow();
  check(window.x==380 && window.y==180 && window._titlebarLabel!=null
    && window._titlebarClose!=null && window.alpha==1,
    'window background remains visible');
  var blank=new HLUIComponent();blank.buildUI();
  blank.buildUI({background:true});
  check(blank.width>0 && blank.height>0,'building a UI fill must allocate the requested bounds');

  var sys=CodenameSysCompat.facade();
  check(Reflect.fields(sys).length==1 && Reflect.field(sys,'exit')!=null
    && Reflect.field(sys,'command')==null,'Sys facade exposed more than safe exit');
  Reflect.callMethod(sys,Reflect.field(sys,'exit'),[0]);
  check(CodenameModRuntime.exited,'safe exit did not route to native host callback');
  CodenameModRuntime.exited=false;var requestedExit=-1;
  var importedStateSys=CodenameSysCompat.importedStateFacade('owner-a',
    function(code:Int):Void requestedExit=code);
  Reflect.callMethod(importedStateSys,Reflect.field(importedStateSys,'exit'),[0]);
  check(requestedExit==0 && !CodenameModRuntime.exited,
    'active imported-state quit did not request source exit through the injectable callback');
  CodenameModRuntime.exited=false;requestedExit=-1;
  var staleSys=CodenameSysCompat.importedStateFacade('owner-a',
    function(code:Int):Void requestedExit=42);
  CodenameModRuntime.activeRoot='owner-b';
  Reflect.callMethod(staleSys,Reflect.field(staleSys,'exit'),[0]);
  check(CodenameModRuntime.exited && requestedExit==-1,
    'stale imported-state facade did not recheck owner activity before process exit');
 }
}
''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"),
                 "-main", "HL17UiTestMain", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipIf(not Path('/run/media/cammie/External Storage/FNF-Example-Mods/codename/hl17_v3/mods/HL17/data/states/HL17MainMenu.hx').is_file(), 'mounted HL17 donor fixture is unavailable')
    def test_menu_exit_never_binds_native_sys_and_window_modules_remain_diagnosed(self):
        bindings = (ROOT / "source/CodenameImportBindings.hx").read_text()
        self.assertIn("bindings.set('Sys', CodenameSysCompat.facade());", bindings)
        self.assertNotIn("bindings.set('Sys', Sys);", bindings)
        mod_bindings = (ROOT / "source/CodenameModBindings.hx").read_text()
        self.assertIn("Std.isOfType(host, CodenameImportedState)", mod_bindings)
        self.assertIn("CodenameSysCompat.importedStateFacade(root)", mod_bindings)
        menu = Path("/run/media/cammie/External Storage/FNF-Example-Mods/codename/hl17_v3/mods/HL17/data/states/HL17MainMenu.hx").read_text()
        self.assertIn("Sys.exit(0)", menu)
        parser = (ROOT / "source/CodenameScriptParser.hx").read_text()
        self.assertIn("cannot execute in the classless script runtime", parser)
        for class_name in ("HLCreditsWindow", "HLOptionsWindow", "HLSelectWindow"):
            self.assertIn(f"class {class_name} extends HLUIWindow", Path(
                "/run/media/cammie/External Storage/FNF-Example-Mods/codename/hl17_v3/mods/HL17/source/"
                + class_name + ".hx").read_text())


if __name__ == "__main__":
    unittest.main()
