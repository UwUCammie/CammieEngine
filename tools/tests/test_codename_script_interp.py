"""Execute real HScript against per-interpreter constructors and cleanup."""
from pathlib import Path
import shutil
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
DONOR_UI = (
    Path("/run/media/cammie/External Storage/FNF-Example-Mods")
    / "codename/D-Sides REDUX Codename Engine (Cancelled)/mods/D-Sides REDUX/songs/UI.hx"
)
DONOR_HL17 = (
    Path("/run/media/cammie/External Storage/FNF-Example-Mods")
    / "codename/hl17_v3/mods/HL17"
)


def mounted_try_harder_owner():
    for assets_root in (
        ROOT / 'tmp/dsides-current-chart-refresh/runtime-overlay/assets',
        ROOT / 'tmp/vslice-native-preview/runtime/assets',
    ):
        imported_mods = assets_root / 'imported_mods'
        for owner in sorted(imported_mods.glob('codename-engine-d-sides-redux-*')):
            if ((owner / 'songs/try-harder/scripts/events.hx').is_file()
                    and (owner / 'data/scripts/Lyrics.hx').is_file()):
                return owner
    return None


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


class CodenameScriptInterpTest(unittest.TestCase):
    def test_mounted_try_harder_color_alias_regression_sources(self):
        owner = mounted_try_harder_owner()
        if owner is None:
            self.skipTest('mounted Codename D-Sides Try Harder scripts are unavailable')

        events = (owner / 'songs/try-harder/scripts/events.hx').read_text()
        lyrics = (owner / 'data/scripts/Lyrics.hx').read_text()
        assignments = re.findall(r'\bFlxColor\s*=\s*0x[0-9A-Fa-f]+', events)
        self.assertGreaterEqual(len(assignments), 2)
        self.assertIn('importScript("data/scripts/Lyrics");', events)
        self.assertIn('FlxColor.fromString(j.color)', lyrics)

        playstate = (ROOT / 'source/PlayState.hx').read_text()
        self.assertIn('interp.protectImportAliases(bindings);', playstate)

    def test_camera_alpha_accessor_uses_typed_flixel_route(self):
        source = (ROOT / 'source/CodenameScriptInterp.hx').read_text()
        get_method = extract_method(source, 'override function get(')
        set_method = extract_method(source, 'override function set(')
        self.assertIn("Std.isOfType(object, FlxCamera) && field == 'alpha'", get_method)
        self.assertIn("return (cast object:FlxCamera).alpha;", get_method)
        self.assertIn("Std.isOfType(object, FlxCamera) && field == 'alpha'", set_method)
        self.assertIn("(cast object:FlxCamera).alpha = value;", set_method)

    def test_codename_state_switch_transfers_only_accepted_target(self):
        facade = (ROOT / 'source/CodenameFlxGFacade.hx').read_text()
        switch_method = extract_method(facade, 'public function switchState(target:Dynamic):Bool')
        self.assertIn('if (accepted && onStateSwitchAccepted != null)', switch_method)
        native_switch_path = switch_method[switch_method.index('if (!Std.isOfType(target, FlxState))'):]
        self.assertLess(native_switch_path.index('FlxG.switchState(cast target);'),
                        native_switch_path.index('onStateSwitchAccepted(target);'))
        self.assertIn('onStateSwitchAccepted = null;', extract_method(facade, 'public function release():Void'))

        source = (ROOT / 'source/CodenameScriptInterp.hx').read_text()
        transfer = extract_method(source, 'public function transferStateTarget(value:Dynamic):Void')
        self.assertIn('Std.isOfType(basic, FlxState)', transfer)
        self.assertIn('unclaimedBasics.remove(basic)', transfer)

    def test_codename_line_characters_use_typed_script_access(self):
        source = (ROOT / 'source/CodenameScriptInterp.hx').read_text()
        get_method = extract_method(source, 'override function get(')
        set_method = extract_method(source, 'override function set(')
        self.assertIn("field == 'cpu' && Std.isOfType(object, CodenameInputLine)", get_method)
        self.assertIn('CodenameInputLineScriptAccess.getEffectiveCpu(cast object)', get_method)
        self.assertIn('CodenameInputLineScriptAccess.getCharacters(cast object)', get_method)
        self.assertIn('CodenameInputLineScriptAccess.setCharacters(cast object, cast value)', set_method)
        playstate = (ROOT / 'source/PlayState.hx').read_text()
        self.assertIn("interp.bindLiveGlobal('player', function():Dynamic return getCodenameInputLine(1),", playstate)
        self.assertIn('opponentPlayer, duoMode, demoMode,', playstate)

        fixture = r'''import hscript.Interp;
import hscript.Parser;
class Actor {
 public var visible:Bool=true;
 public var animations:Array<String>=[];
 public function new() {}
 public function hasAnim(name:String):Bool return name=='combo50' || name=='idle';
 public function playAnim(name:String,force:Bool=false):Void animations.push(name+':'+force);
}
class LineInterp extends Interp {
 override function get(object:Dynamic,field:String):Dynamic {
  if(field=='cpu' && Std.isOfType(object,CodenameInputLine))
   return CodenameInputLineScriptAccess.getEffectiveCpu(object);
  if(field=='characters' && Std.isOfType(object,CodenameInputLine))
   return CodenameInputLineScriptAccess.getCharacters(object);
  return super.get(object,field);
 }
 override function set(object:Dynamic,field:String,value:Dynamic):Dynamic {
  if(field=='characters' && Std.isOfType(object,CodenameInputLine)) {
   CodenameInputLineScriptAccess.setCharacters(object,value);
   return value;
  }
  return super.set(object,field,value);
 }
}
class Main {
 static function check(ok:Bool,why:String):Void if(!ok) throw why;
 static function main():Void {
  var first=new Actor(); var second=new Actor(); var third=new Actor();
  var line=new CodenameInputLine<Actor>([null,first,second]);
  var strumLines={members:[null,line]};
  var seen:Array<Dynamic>=[];
  check(line.characters.length==2,'fixture line did not expose its live actors');
  check(CodenameInputLineScriptAccess.getCharacters(line).length==2,
   'typed helper did not invoke the computed getter');
  var interp=new LineInterp();
  interp.variables.set('strumLines',strumLines);
  interp.variables.set('player',line);
  interp.variables.set('seen',seen);
  var script="for (chars in strumLines.members[1].characters) {\n"
   + " if (chars == null) throw 'null actor reached iteration';\n"
   + " seen.push(chars.hasAnim('combo50'));\n}\n"
   + "strumLines.members[1].characters[0].visible = false;\n"
   + "strumLines.members[1].characters[1].playAnim('idle', true);\n"
   + "strumLines.members[1].characters = [null, third];\n";
  interp.variables.set('third',third);
  interp.execute(new Parser().parseString(script));
  line.cpu=false;line.botplay=true;
  interp.execute(new Parser().parseString("if(player.cpu!=true) throw 'bare player.cpu missed initial demo botplay'; player.cpu=false; if(player.cpu!=true) throw 'script ownership write hid active botplay';"));
  check(!line.cpu && line.botplay,'bare player.cpu read or write changed authored ownership during botplay');
  line.botplay=false;
  interp.execute(new Parser().parseString("if(player.cpu!=false) throw 'bare player.cpu stayed true after botplay';"));
  line.cpu=true;
  interp.execute(new Parser().parseString("if(player.cpu!=true) throw 'bare player.cpu missed authored CPU ownership';"));
  check(seen.length==2 && seen[0]==true && seen[1]==true,
   'typed line getter exposed an unresolved source slot during iteration');
  check(!first.visible && second.animations.join(',')=='idle:true',
   'indexed script reads no longer reach the live actor instances');
  check(line.characters.length==1 && line.characters[0]==third,
   'typed script setter did not retain only materialized actors');
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            folder = Path(directory)
            (folder / 'Main.hx').write_text(fixture)
            (folder / 'CodenameInputLine.hx').write_text(r'''class CodenameInputLine<T> {
 var live:Array<T>=[];
 public var cpu:Bool=false;
 public var botplay:Bool=false;
 public var characters(get,set):Array<T>;
 public var notes(get,never):CodenameStrumlineNoteCollection;
 function get_characters():Array<T> {
  var i=0;
  while(i<live.length) if(live[i]==null) live.splice(i,1); else i++;
  return live;
 }
 function set_characters(value:Array<T>):Array<T> {
  live=[];
  if(value!=null) for(actor in value) if(actor!=null) live.push(actor);
  return live;
 }
 function get_notes():CodenameStrumlineNoteCollection return null;
 public function new(value:Array<Null<T>>) {
  for(actor in value) if(actor!=null) live.push(actor);
 }
}''')
            shutil.copy2(ROOT / 'source/CodenameInputLineScriptAccess.hx', folder)
            shutil.copy2(ROOT / 'source/CodenameStrumlineNoteCollection.hx', folder)
            shutil.copy2(ROOT / 'source/CodenameLineNoteQuery.hx', folder)
            shutil.copy2(ROOT / 'source/CodenameLineNoteIndex.hx', folder)
            result = subprocess.run(
                [str(ROOT / '.tools/haxe/haxe'), '-cp', str(ROOT / '.haxelib/hscript/2,5,0'),
                 '-cp', str(folder), '--run', 'Main'], cwd=ROOT,
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_gameplay_state_companion_uses_normal_script_scope_lifecycle(self):
        playstate = (ROOT / 'source/PlayState.hx').read_text()
        self.assertIn("interp.bindLiveGlobal('health', function():Dynamic return health,", playstate)
        self.assertIn("interp.variables.set('scripts', codenamePublicScriptGlobals.scriptFacade(file.relative, file.relative));",
                      playstate)
        self.assertIn("var relative = 'data/states/PlayState.hx';", playstate)
        self.assertIn("loadCodenameScript({path:path, relative:resolution.relative, family:'state'}, root);",
                      playstate)
        self.assertLess(playstate.index('\t\tloadCodenameStateCompat();'),
                        playstate.index('\t\tloadCodenameStageCompat();'),
                        'gameplay state exports must exist before stage scopes load')

    def test_constructor_context_and_async_cleanup_are_scope_local(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            base = Path(directory)
            hscript_ex = base / 'hscript-ex'
            upstream = ROOT / '.haxelib/hscript-ex/git'
            shutil.copytree(upstream / 'src/hscript', hscript_ex / 'hscript')
            # Exercise the tracked patcher from pristine upstream files even
            # after run.sh has patched the local haxelib checkout.
            for filename in ('InterpEx.hx', 'ScriptClass.hx', 'AbstractScriptClass.hx'):
                original = subprocess.run(
                    ['git', '-C', str(upstream), 'show', f'HEAD:src/hscript/{filename}'],
                    cwd=ROOT, check=True, capture_output=True, text=True,
                ).stdout
                (hscript_ex / 'hscript' / filename).write_text(original, encoding='utf-8')
            for _ in range(2):
                subprocess.run(['python3', str(ROOT / 'tools/patch_hscript_ex_owner_scope.py'),
                                 str(hscript_ex / 'hscript')], cwd=ROOT, check=True,
                               text=True, capture_output=True)
            stubs = {
                'flixel/FlxBasic.hx': '''package flixel;
class FlxBasic { public var destroyCount:Int=0; public var exists:Bool=true; public var active:Bool=true;
 public var visible:Bool=true; public function new() {} public function update(elapsed:Float):Void {}
 public function destroy():Void {destroyCount++;exists=false;} }''',
                'flixel/FlxG.hx': '''package flixel;
class TestStateSwitchSignal { public function new() {} public function addOnce(listener:Void->Void):Void {}
 public function remove(listener:Void->Void):Void {} }
class TestStateSwitchSignals { public var postStateSwitch:TestStateSwitchSignal; public function new() postStateSwitch=new TestStateSwitchSignal(); }
class FlxG { public static var signals:Dynamic=new TestStateSwitchSignals();
 public static var save:Dynamic; public static var width:Int=1280; public static var height:Int=720;
 public static var state:Dynamic; public static var camera:FlxCamera;
 public static var game:FlxGame=new FlxGame();
 public static var mouse:flixel.input.FlxMouse=new flixel.input.FlxMouse();
 public static var keys:flixel.input.FlxKeys=new flixel.input.FlxKeys(); }''',
                'flixel/FlxGame.hx': '''package flixel;
class FlxGame { public var _nextState:Dynamic; public var ticks:Int=7;
 public function new() {}
 public function bump(value:Int):Int return ticks+=value; }''',
                'flixel/group/FlxGroup.hx': '''package flixel.group;
import flixel.FlxBasic;
typedef FlxGroup=FlxTypedGroup<FlxBasic>;
class FlxTypedGroup<T:FlxBasic> extends FlxBasic {
 public var members:Array<T>=[];
 public function new() super();
 public function add(member:T):T {members.push(member);return member;}
 public function remove(member:T,splice:Bool=false):T {
  if(splice) members.remove(member);else {var index=members.indexOf(member);if(index>=0) members[index]=null;}
  return member;
 }
 override public function destroy():Void {super.destroy();for(member in members) if(member!=null) member.destroy();members=null;}
}''',
                'CodenameFlxGFacade.hx': '''class CodenameFlxGFacade {
 public var cameras:Dynamic; public var save:Dynamic; public var adopted:Array<Dynamic>=[]; public var released=false;
 public var onStateSwitchAccepted:Null<Dynamic->Void>;
 public var stateSwitch:Null<Dynamic->Bool>;
 public var game(get,never):Dynamic; function get_game():Dynamic return flixel.FlxG.game;
 public function new() { cameras={adoptCreated:function(camera:Dynamic):Dynamic { adopted.push(camera); return camera; }}; }
 public function switchState(target:Dynamic):Bool {
  var accepted=stateSwitch==null ? true : stateSwitch(target);
  if(accepted && onStateSwitchAccepted!=null) onStateSwitchAccepted(target);
  return accepted;
 }
 public function release():Void {released=true;onStateSwitchAccepted=null;}
}''',
                'flixel/FlxCamera.hx': '''package flixel;
import openfl.filters.BitmapFilter;
class FlxCamera { public var filters:Null<Array<BitmapFilter>>; public var filtersEnabled:Bool=true;
 public var bgColor:Dynamic; public var zoom:Float=1; public var alpha(get,set):Float;
 var storedAlpha:Float=1; public var alphaWrites:Int=0;
 function get_alpha():Float return storedAlpha;
 function set_alpha(value:Float):Float { alphaWrites++; storedAlpha=value; return value; }
 public function new() {}
 public function focusOn(point:Dynamic):Void {}
}''',
                'flixel/FlxObject.hx': '''package flixel;
class FlxObject { public var x:Float; public var y:Float;
 public function new(x:Float=0,y:Float=0) { this.x=x; this.y=y; }
 public function getPosition():Dynamic return {x:x,y:y};
}''',
                'flx3d/CodenameFlx3DView.hx': '''package flx3d;
class CodenameFlx3DView extends flixel.FlxSprite {
 public function new() super();
}''',
                'flx3d/CodenameFlx3DCamera.hx': '''package flx3d;
class CodenameFlx3DCamera extends flixel.FlxCamera {
 public function new() super();
}''',
                'flixel/FlxState.hx': '''package flixel;
class FlxState extends FlxBasic {
 public var members:Array<FlxBasic>=[]; public function new() super();
 public function add<T:FlxBasic>(basic:T):T { if(members.indexOf(basic)<0)members.push(basic);return basic; }
 public function insert<T:FlxBasic>(index:Int,basic:T):T { members.insert(index,basic);return basic; }
 public function remove<T:FlxBasic>(basic:T,splice:Bool=false):T { members.remove(basic);return basic; }
 override public function destroy():Void {members=null;super.destroy();}
}''',
                'flixel/graphics/FlxGraphic.hx': '''package flixel.graphics;
class FlxGraphic { public var assetsKey:Null<String>;public var destroyOnNoUse:Bool=true;public var useCount:Int=0;
 public function new(?assetsKey:String)this.assetsKey=assetsKey;
 public function incrementUseCount():Void useCount++;
 public function decrementUseCount():Void useCount--; }''',
                'flixel/math/FlxPoint.hx': '''package flixel.math;
class FlxPoint { public var x:Float;public var y:Float;
 public function new(x:Float=0,y:Float=0){this.x=x;this.y=y;}
 public static function get(x:Float=0,y:Float=0):FlxPoint return new FlxPoint(x,y);
 public function set(x:Float=0,y:Float=0):FlxPoint {this.x=x;this.y=y;return this;}
 public function put():Void {} }''',
                'flixel/input/FlxMouse.hx': '''package flixel.input;
class FlxMouse { public var x:Float=0;public var y:Float=0;public var justPressed:Bool=false;
 public var justReleased:Bool=false;public function new() {}
 public function overlaps(sprite:flixel.FlxSprite):Bool return sprite!=null && x>=sprite.x && y>=sprite.y && x<=sprite.x+sprite.width && y<=sprite.y+sprite.height; }''',
                'flixel/input/FlxKeys.hx': '''package flixel.input;
class FlxKeyStatus { public var LEFT:Bool=false;public var RIGHT:Bool=false;public function new(){} }
class FlxKeys { public var justPressed:FlxKeyStatus=new FlxKeyStatus();public function new(){} }''',
                'flixel/FlxSprite.hx': '''package flixel;
import flixel.util.FlxColor;
import flixel.math.FlxPoint;
class FlxSprite extends FlxBasic {
 public var x:Float=0; public var y:Float=0; public var width:Float=0; public var height:Float=0; public var alpha:Float=1;
 public var antialiasing:Bool=true; public var scale:FlxPoint=new FlxPoint(1,1); public var blend:Int=0;
 public var cameras:Array<Dynamic>=[];
 public var ID:Int=0; public var offset:Dynamic={x:0.0,y:0.0};
 public var frames:Dynamic; public var animation:Dynamic; public var animationCalls:Array<Dynamic>=[];
 public var graphic:flixel.graphics.FlxGraphic;
 public var solidWidth:Int=0; public var solidHeight:Int=0; public var solidColor:FlxColor=FlxColor.WHITE;
 public function new(x:Float=0,y:Float=0) {super();this.x=x;this.y=y;
  animation={addByPrefix:function(name:String,prefix:String,rate:Float,looped:Bool):Void
   animationCalls.push([name,prefix,rate,looped])}; }
 public function setSize(width:Float,height:Float):Void {this.width=width;this.height=height;}
 public function updateHitbox():Void {}
 public function draw():Void {}
 public function drawComplex(camera:FlxCamera):Void {}
 public function makeGraphic(width:Int,height:Int,color:FlxColor=FlxColor.WHITE,unique:Bool=false,?key:String):FlxSprite {
  solidWidth=width;solidHeight=height;solidColor=color;this.width=width;this.height=height;return this;
 }
 public function loadGraphic(graphic:flixel.system.FlxAssets.FlxGraphicAsset,animated:Bool=false,
  frameWidth:Int=0,frameHeight:Int=0,unique:Bool=false,?key:String):FlxSprite {
  if(Std.isOfType(graphic,flixel.graphics.FlxGraphic)) this.graphic=cast graphic;
  width=200;height=100;return this;
 }
}''',
                'flixel/system/FlxAssets.hx': 'package flixel.system; typedef FlxGraphicAsset=Dynamic;',
                'flixel/group/FlxSpriteGroup.hx': '''package flixel.group;
import flixel.FlxSprite;
import flixel.group.FlxGroup.FlxTypedGroup;
typedef FlxSpriteGroup=FlxTypedSpriteGroup<FlxSprite>;
class FlxTypedSpriteGroup<T:FlxSprite> extends FlxTypedGroup<T> {
 public var x:Float=0; public var y:Float=0;
 public function new() super();
 override public function update(elapsed:Float):Void super.update(elapsed);
}''',
                'flixel/text/FlxText.hx': '''package flixel.text;
import flixel.FlxSprite;
import flixel.util.FlxColor;
enum abstract FlxTextBorderStyle(Int) { var OUTLINE=1; }
class FlxText extends FlxSprite {
 public var text(get,set):String; public var size(get,set):Int; public var font:String=''; public var color:FlxColor=FlxColor.WHITE;
 public var borderColor:FlxColor=FlxColor.WHITE; public var borderSize:Float=0;
 public var borderStyle:FlxTextBorderStyle=FlxTextBorderStyle.OUTLINE;
 var textValue:String=''; var sizeValue:Int=8;
 public function new(x:Float=0,y:Float=0,width:Float=0,text:String='',size:Int=8) {
  super(x,y);this.width=width;textValue=text;sizeValue=size;measure();
 }
 function get_text():String return textValue;
 function set_text(value:String):String {textValue=value;measure();return value;}
 function get_size():Int return sizeValue;
 function set_size(value:Int):Int {sizeValue=value;measure();return value;}
 public function setFormat(?fontName:String, size:Int=8, ?colorValue:Dynamic,
   ?alignment:Dynamic, ?border:Dynamic, ?borderColorValue:Dynamic):FlxText {
  if(fontName!=null) font=fontName; if(size!=null) sizeValue=size; measure(); return this;
 }
 function measure():Void {width=textValue.length*sizeValue*0.5;height=sizeValue+4;}
}''',
                'flixel/util/FlxColor.hx': '''package flixel.util;
enum abstract FlxColor(Int) from Int to Int { var WHITE=0xFFFFFFFF; var TRANSPARENT=0x00000000; }''',
                'flixel/util/FlxSignal.hx': '''package flixel.util;
class FlxSignal {}
class FlxTypedSignal<T> { public function new() {} public function removeAll():Void {} }''',
                'flixel/util/FlxDestroyUtil.hx': '''package flixel.util;
class FlxDestroyUtil { public static function put<T>(value:T):T return null; }''',
                'openfl/display/Shader.hx': '''package openfl.display; class Shader { public function new() {} }''',
                'openfl/display/ShaderParameterType.hx': '''package openfl.display;
enum abstract ShaderParameterType(Int) {
 var BOOL=0; var BOOL2=1; var BOOL3=2; var BOOL4=3;
 var FLOAT=4; var FLOAT2=5; var FLOAT3=6; var FLOAT4=7;
 var INT=8; var INT2=9; var INT3=10; var INT4=11;
 var MATRIX2X2=12; var MATRIX2X3=13; var MATRIX2X4=14; var MATRIX3X2=15;
 var MATRIX3X3=16; var MATRIX3X4=17; var MATRIX4X2=18; var MATRIX4X3=19; var MATRIX4X4=20;
}''',
                'openfl/events/EventDispatcher.hx': '''package openfl.events;
class EventDispatcher {
 public var listeners:Array<Dynamic>=[];
 public function new() {}
 public function addEventListener(type:String,listener:Dynamic,useCapture:Bool=false,priority:Int=0,weak:Bool=false):Void
  listeners.push({type:type,listener:listener,useCapture:useCapture});
 public function removeEventListener(type:String,listener:Dynamic,useCapture:Bool=false):Void {
  listeners=[for (entry in listeners) if(entry.type!=type || entry.listener!=listener || entry.useCapture!=useCapture) entry];
 }
}''',
                'openfl/display/DisplayObject.hx': '''package openfl.display;
import openfl.events.EventDispatcher;
class DisplayObject extends EventDispatcher { public var parent:DisplayObjectContainer; public function new() super(); }''',
                'openfl/display/DisplayObjectContainer.hx': '''package openfl.display;
class DisplayObjectContainer extends DisplayObject {
 public var children:Array<DisplayObject>=[];
 public var numChildren(get,never):Int; function get_numChildren():Int return children.length;
 public function new() super();
 public function addChild(child:DisplayObject):DisplayObject {
  if(child.parent!=null) child.parent.removeChild(child); children.push(child); child.parent=this; return child;
 }
 public function removeChild(child:DisplayObject):DisplayObject {
  if(child==null) throw 'Parameter child must be non-null';
  if(!children.remove(child)) throw 'Display object is not a child'; child.parent=null; return child;
 }
}''',
                'openfl/display/Sprite.hx': '''package openfl.display;
class Sprite extends DisplayObjectContainer { public function new() super(); }''',
                'openfl/filters/BitmapFilter.hx': '''package openfl.filters; class BitmapFilter { public function new() {} }''',
                'openfl/filters/ShaderFilter.hx': '''package openfl.filters;
import openfl.display.Shader;
class ShaderFilter extends BitmapFilter { public var shader:Shader; public function new(shader:Shader) { super();this.shader=shader; } }''',
                'CodenamePaths.hx': '''import flixel.graphics.FlxGraphic;
class CodenamePaths { public var root:String; public var fontLookups:Array<String>=[];
 public function new(root:String) this.root=root;
 public function font(path:String):String return root+'/fonts/'+path;
 public function getFontName(path:String):String { fontLookups.push(path); return 'Test Owner Font'; }
 public function getPath(path:String):String return path;
 public function graphic(path:String):FlxGraphic return null; }''',
                'TestWindow.hx': '''class TestWindow {
 public var x:Float=0; public var y:Float=0; public var width:Float=0; public var height:Float=0;
 public function new(x:Float=0,y:Float=0,width:Float=0,height:Float=0) {
  this.x=x;this.y=y;this.width=width;this.height=height;
 }
}''',
                'CodenameFunkinSprite.hx': '''class CodenameFunkinSprite {
 public var resolver:Dynamic; public var x:Float; public var y:Float;
 public function new(x:Float=0,y:Float=0,?graphic:Dynamic,?resolver:Dynamic) {
  this.x=x; this.y=y; this.resolver=resolver;
 }
}''',
                'CodenameFunkinText.hx': '''class CodenameFunkinText {
 public static function fromArgs(args:Array<Dynamic>, paths:CodenamePaths):Dynamic
  return {args:args, paths:paths};
}''',
                'flixel/addons/display/FlxRuntimeShader.hx': '''package flixel.addons.display;
class FlxRuntimeShader extends openfl.display.Shader {
 var storedData:Dynamic; public var data(get, never):Dynamic; public var writes:Array<Dynamic>=[];
 function get_data():Dynamic return storedData;
 public function new(data:Dynamic) { super();storedData=data; }
 public function setFloat(name:String,value:Float):Void { writes.push([name,value]); Reflect.field(this.data,name).value=[value]; }
 public function setFloatArray(name:String,value:Array<Float>):Void { writes.push([name,value]); Reflect.field(this.data,name).value=value; }
 public function setInt(name:String,value:Int):Void { writes.push([name,value]); Reflect.field(this.data,name).value=[value]; }
 public function setIntArray(name:String,value:Array<Int>):Void { writes.push([name,value]); Reflect.field(this.data,name).value=value; }
 public function setBool(name:String,value:Bool):Void { writes.push([name,value]); Reflect.field(this.data,name).value=[value]; }
 public function setBoolArray(name:String,value:Array<Bool>):Void { writes.push([name,value]); Reflect.field(this.data,name).value=value; }
}''',
                'Character.hx': '''class Character {
 public var x:Dynamic; public var y:Dynamic; public var character:String; public var isPlayer:Bool;
 public function new(x:Dynamic,y:Dynamic,character:String,isPlayer:Bool) {
  this.x=x;this.y=y;this.character=character;this.isPlayer=isPlayer;
 }
}''',
                'Controls.hx': '''class Controls {
 public var SWITCHMOD:Bool=false;
 public function new() {}
}''',
                'flixel/util/FlxTimer.hx': '''package flixel.util;
class FlxTimer { public var active:Bool=true; public var finished:Bool=false; public var cancelled:Bool=false;
 public var time:Float=0; public var elapsedLoops:Int=0; public function new() {}
 public function start(duration:Float, callback:FlxTimer->Void):FlxTimer return this;
 public function cancel():Void { cancelled=true; finished=true; active=false; }
 public function destroy():Void {} }''',
                'flixel/tweens/FlxTween.hx': '''package flixel.tweens;
enum abstract FlxTweenType(Int) { var ONESHOT=8; var PERSIST=1; var LOOPING=2; var PINGPONG=4; var BACKWARD=16; }
class FlxTween { public var active:Bool=true; public var finished:Bool=false; public var cancelled:Bool=false; public var onComplete:FlxTween->Void;
 public static var lastTweenObject:Dynamic; public function new() {}
 public static function tween(object:Dynamic, properties:Dynamic, duration:Float=1, ?options:Dynamic):FlxTween {
  lastTweenObject=object;
  if(properties!=null && Reflect.hasField(properties,'alpha'))
   Reflect.setProperty(object,'alpha',Reflect.field(properties,'alpha'));
  return new FlxTween(); }
 public static function num(from:Float,to:Float,duration:Float=1,?options:Dynamic,?onValue:Float->Void):FlxTween { if(onValue!=null) onValue(to); return new FlxTween(); }
 public static function angle(sprite:Dynamic,from:Float,to:Float,duration:Float=1,?options:Dynamic):FlxTween return new FlxTween();
 public static function color(sprite:Dynamic,duration:Float,from:Dynamic,to:Dynamic,?options:Dynamic):FlxTween return new FlxTween();
 public static function cancelTweensOf(object:Dynamic):Void {}
 public static function completeTweensOf(object:Dynamic):Void {}
 public function cancel():Void { cancelled=true; finished=true; active=false; }
 public function destroy():Void {}
}''',
            }
            for name, content in stubs.items():
                path = base / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            synthetic_owner = base / 'synthetic-owner'
            (synthetic_owner / 'source').mkdir(parents=True)
            bopper_source = DONOR_HL17 / 'source/Bopper.hx'
            self.assertTrue(bopper_source.is_file(), f'mounted HL17 Bopper source is missing: {bopper_source}')
            (synthetic_owner / 'source/Bopper.hx').write_bytes(bopper_source.read_bytes())
            (synthetic_owner / 'source/UnsupportedInlineMethod.hx').write_text(
                'class UnsupportedInlineMethod { public function read():Int return 1; }\n',
                encoding='utf-8',
            )
            foreign_owner = base / 'foreign-owner'
            (foreign_owner / 'source').mkdir(parents=True)
            (foreign_owner / 'source/Bopper.hx').write_bytes(bopper_source.read_bytes())
            (foreign_owner / 'source/Plain.hx').write_text(
                'class Plain { public var value:Int=1; public function new() {} }\n',
                encoding='utf-8',
            )
            empty_owner = base / 'empty-owner'
            (empty_owner / 'source').mkdir(parents=True)
            (synthetic_owner / 'source/MissingTerminator.hx').write_text(
                'class MissingTerminator {\n'
                ' public var values:Array<Int> = [\n'
                '  1, 2\n'
                ' ]\n'
                ' public var answer:Int = 42;\n'
                '}\n'
            )
            (synthetic_owner / 'source/MiniOptionsWindow.hx').write_text('''class MiniOptionsWindow extends ProbeNativeWindowBase {
 public var output:Dynamic;
 public function new() { super(); }
 public function initializeAndAddToState(state:Dynamic):Void {
  var controls = new HLUIBox(Layout.VERTICAL);
  var gameplay = new HLUIBox(Layout.VERTICAL);
  gameplay.componentOffset.set(8, 8);
  var configured = addOptionsToTab(gameplay, []);
  var appearance = new HLUIBox(Layout.VERTICAL);
  var tabs = new HLUITabBox([
   new HLUITab("Keyboard", controls),
   new HLUITab("Gameplay", gameplay),
   new HLUITab("Appearance", appearance)
  ], 458, 438, state);
  output = {gameplay:gameplay, configured:configured, tabContent:tabs._tabs[1].content};
 }
 public function addOptionsToTab(tab:Dynamic, options:Array<Dynamic>):Int {
  return options.length + 1;
 }
 public function failNested():Void { throw "expected nested test error"; }
 public function verifyLocalAssignmentPriority():Bool {
  this.visible=true;
  var visible:Bool=true;
  visible=false;
  var spriteProperties:Array<Dynamic>=null;
  if(spriteProperties==null) spriteProperties=["idle",24,false];
  return !visible && this.visible && spriteProperties[0]=="idle"
   && spriteProperties[1]==24 && spriteProperties[2]==false;
 }
 public function verifyParameterAssignmentPriority(visible:Bool):Bool {
  visible=false;
  return !visible;
 }
 public function verifyInheritedProperties():Bool {
  var wasVisible:Bool=visible;
  var nullableWasNull:Bool=nullableNative==null;
  visible=false;
  this.nullableNative="written";
  return wasVisible && !visible && nullableWasNull && nullableNative=="written";
 }
 public function writeMissingNativeField():Void { this.noSuchNativeField=3; }
 public function getOutput():Dynamic { return output; }
}
''')
            (synthetic_owner / 'source/CameraAlphaWriter.hx').write_text('''class CameraAlphaWriter {
 public function new() {}
 public function writeAlpha(camera:Dynamic,value:Float):Void { camera.alpha=value; }
 public function readAlpha(camera:Dynamic):Float { return camera.alpha; }
}
''')
            (base / 'Main.hx').write_text('''class Actor {
 public var x:Float=10;
 public var nullable:Dynamic=null;
 public var visible:Bool=true;
 public var value(get,set):Float;
 var stored:Float=2;
 public var writes:Int=0;
 public function new() {}
 function get_value():Float return stored;
 function set_value(v:Float):Float { writes++; return stored=v; }
 public function move(v:Float):Void x+=v;
}
class SourceActor implements CodenameCharacterAccess {
 public var codenameSourceId:String;
 public var curCharacter:String='native-key';
 public var calls:Array<Dynamic>=[];
 public var dances:Int=0;
 public function new(id:String) codenameSourceId=id;
 public function playAnim(name:String,force:Bool=false,reverse:Bool=false,frame:Int=0):Void
  calls.push(['native',name,force,reverse,frame]);
 public function codenamePlayAnim(name:String,?force:Null<Bool>,context:Dynamic=null,reverse:Bool=false,frame:Int=0):Void
  calls.push(['source',name,force,context,reverse,frame]);
 public function codenameTryDance():Void dances++;
 public var codenameSingAnims:Array<String> = ['left','down','up','right'];
 public function codenameGetSingAnim(direction:Int,suffix:String=''):String return codenameSingAnims[direction%codenameSingAnims.length]+suffix;
 public var directional:Array<Dynamic>=[];
 public function codenamePlaySingAnim(direction:Int,suffix:String='',context:Dynamic='SING',?force:Null<Bool>,reversed:Bool=false,frame:Int=0):Void
  directional=[direction,suffix,context,force,reversed,frame];
 public function codenamePlaySingAnimUnsafe(direction:Int,suffix:String='',context:Dynamic='SING',force:Bool=true,reversed:Bool=false,frame:Int=0):Void
  directional=['unsafe',direction,suffix,context,force,reversed,frame];
}
class Game implements CodenameGameplayAccess {
 public static var misses:Int=0;
 public var codenameMisses(get,set):Int;
 public var accuracy:Float=100;
 public var codenameAccuracy(get,set):Float;
 function get_codenameAccuracy():Float return accuracy/100;
 function set_codenameAccuracy(v:Float):Float {accuracy=v*100;return v;}
 public function new(){}
 function get_codenameMisses():Int return misses;
 function set_codenameMisses(v:Int):Int return misses=v;
}
class MainMenuState extends flixel.FlxState { public function new() super(); }
class FnasMainState extends flixel.FlxState { public function new() super(); }
class AlphaHolder { public var alpha:Float=1; public function new() {} }
class ProbeNativeWindowBase {
 var visibleValue:Bool=true;
 public var visible(get,set):Bool;
 var nullableValue:Dynamic=null;
 public var nullableNative(get,set):Dynamic;
 public function new() {}
 function get_visible():Bool return visibleValue;
 function set_visible(value:Bool):Bool return visibleValue=value;
 function get_nullableNative():Dynamic return nullableValue;
 function set_nullableNative(value:Dynamic):Dynamic return nullableValue=value;
}
class Main {
 static function isHuggyStepIdentifier(expression:Dynamic):Bool {
  return switch (hscript.Tools.expr(expression)) {
   case hscript.Expr.EIdent('step'): true;
   case hscript.Expr.EParent(inner): isHuggyStepIdentifier(inner);
   default: false;
  };
 }
 static function isHuggyAlphaAssignment(expression:Dynamic):Bool {
  switch (hscript.Tools.expr(expression)) {
   case hscript.Expr.EBinop('=', hscript.Expr.EField(hscript.Expr.EIdent('camGame'),'alpha'),
    hscript.Expr.EConst(hscript.Expr.Const.CInt(0))): return true;
   case hscript.Expr.EBlock(expressions):
    for (entry in expressions) if (isHuggyAlphaAssignment(entry)) return true;
   case hscript.Expr.EParent(inner): return isHuggyAlphaAssignment(inner);
   default:
  }
  return false;
 }
 static function hasHuggyAlphaCase(expression:Dynamic):Bool {
  switch (hscript.Tools.expr(expression)) {
   case hscript.Expr.EBlock(expressions):
    for (entry in expressions) if (hasHuggyAlphaCase(entry)) return true;
   case hscript.Expr.EFunction(arguments, body, name, _) if (name=='stepHit'
    && arguments.length==1 && arguments[0].name=='step'):
    return hasHuggyAlphaCase(body);
   case hscript.Expr.ESwitch(subject, cases, _):
    if(isHuggyStepIdentifier(subject)) {
      for (entry in cases) {
       var isTargetStep=false;
       for (value in entry.values) switch(hscript.Tools.expr(value)) {
        case hscript.Expr.EConst(hscript.Expr.Const.CInt(1268)): isTargetStep=true;
        default:
       }
       if (isTargetStep && isHuggyAlphaAssignment(entry.expr)) return true;
      }
    }
   case hscript.Expr.EParent(inner): return hasHuggyAlphaCase(inner);
   default:
  }
  return false;
 }
 static function scope(root:String):CodenameScriptInterp {
  var interp = new CodenameScriptInterp(new CodenamePaths(root), new CodenameFlxGFacade());
  interp.variables.set('FlxTween', interp.tweenFacade());
  var parser = new hscript.Parser();
  interp.execute(parser.parseString("camera = new FlxCamera(); card = new FunkinSprite(2, 3); timer = new FlxTimer(); tween = FlxTween.tween(card, {x:8}, 2);"));
  return interp;
 }
 static function main() {
  var stringInterp=new CodenameScriptInterp(new CodenamePaths('string-extension'),new CodenameFlxGFacade());
  stringInterp.execute(new hscript.Parser().parseString(
   'sourceText = "  BF  ".toLowerCase().trim(); sourceContains = sourceText.contains("bf"); sourceReplaced = sourceText.replace("bf", "gf");'));
  if(stringInterp.variables.get('sourceText')!='bf'
   || stringInterp.variables.get('sourceContains')!=true
   || stringInterp.variables.get('sourceReplaced')!='gf')
   throw 'StringTools source extensions did not execute in HScript';
  var ownerFontPaths=new CodenamePaths('font-owner');
  var ownerFontInterp=new CodenameScriptInterp(ownerFontPaths,new CodenameFlxGFacade());
  ownerFontInterp.variables.set('FlxText',flixel.text.FlxText);
  ownerFontInterp.variables.set('Paths',ownerFontPaths);
  ownerFontInterp.execute(new hscript.Parser().parseString(
   "menuText=new FlxText(); menuText.setFormat('fonts/Technology.ttf',70); "
   +"menuText.font=Paths.font('851MkPOP.ttf'); nativeText=new FlxText(); "
   +"nativeText.setFormat('assets/fonts/vcr.ttf',16);"));
  var ownerFontText:flixel.text.FlxText=ownerFontInterp.variables.get('menuText');
  var nativeFontText:flixel.text.FlxText=ownerFontInterp.variables.get('nativeText');
  if(ownerFontText.font!='Test Owner Font' || nativeFontText.font!='assets/fonts/vcr.ttf'
   || ownerFontPaths.fontLookups.join(',')!='font-owner/fonts/Technology.ttf,font-owner/fonts/851MkPOP.ttf')
   throw 'owner-local FlxText font paths were not registered and normalized';
  var cameraInterp=new CodenameScriptInterp(new CodenamePaths('camera-alpha'),new CodenameFlxGFacade());
  var scriptCamera=new flixel.FlxCamera();
  cameraInterp.variables.set('scriptCamera',scriptCamera);
  cameraInterp.execute(new hscript.Parser().parseString(
   'scriptCamera.alpha=0; observedCameraAlpha=scriptCamera.alpha;'));
  if(scriptCamera.alpha!=0 || scriptCamera.alphaWrites!=1
   || cameraInterp.variables.get('observedCameraAlpha')!=0)
   throw 'HScript setter-backed camera alpha read/write did not reach the native property';
  var huggyCamera=new flixel.FlxCamera();
  var huggyInterp=new CodenameScriptInterp(new CodenamePaths('huggy-alpha-branch'),new CodenameFlxGFacade());
  huggyInterp.variables.set('camGame',huggyCamera);
  huggyInterp.variables.set('game',{camGame:huggyCamera});
  var huggyAlphaSource='function stepHit(step) { switch(step) { case 1268: camGame.alpha = 0; } } '
   +'function alphaRouteSnapshot() return [camGame, game.camGame];';
  var huggyAlphaProgram=CodenameScriptParser.prepare(huggyAlphaSource,new Map());
  if(huggyAlphaProgram.program==null || CodenameScriptParser.hasFatalDiagnostics(huggyAlphaProgram)
   || !hasHuggyAlphaCase(huggyAlphaProgram.program))
   throw 'Huggyteen stepHit AST no longer contains the step 1268 camGame.alpha assignment: '
    +hscript.Printer.toString(huggyAlphaProgram.program);
  huggyInterp.execute(huggyAlphaProgram.program);
  var alphaRoute:Array<Dynamic>=cast Reflect.callMethod(null,huggyInterp.variables.get('alphaRouteSnapshot'),[]);
  if(alphaRoute==null || alphaRoute.length!=2 || alphaRoute[0]!=huggyCamera || alphaRoute[1]!=huggyCamera)
   throw 'Huggyteen callback globals did not resolve the seeded camGame and game.camGame identity';
  Reflect.callMethod(null,huggyInterp.variables.get('stepHit'),[1268]);
  if(huggyCamera.alpha!=0 || huggyCamera.alphaWrites!=1
   || huggyInterp.variables.get('camGame')!=huggyCamera
   || Reflect.field(huggyInterp.variables.get('game'),'camGame')!=huggyCamera)
   throw 'Huggyteen step 1268 alpha callback did not write the seeded native camera';
  huggyInterp.release();
  var alphaHolder=new AlphaHolder();
  cameraInterp.variables.set('alphaHolder',alphaHolder);
  cameraInterp.execute(new hscript.Parser().parseString('alphaHolder.alpha=0.5;'));
  if(alphaHolder.alpha!=0.5) throw 'HScript generic alpha property write did not reach the native property';
  cameraInterp.release();

  var tweenClassScope=new hscript.ScriptClassScope();
  tweenClassScope.seed('flixel.FlxSprite',flixel.FlxSprite);
  tweenClassScope.registerModule(new hscript.ParserEx().parseModule(
   'class TweenSpriteProxy extends flixel.FlxSprite { public function new(){super();} }'));
  var tweenInterp=new CodenameScriptInterp(new CodenamePaths('tween-proxy'),new CodenameFlxGFacade());
  tweenInterp.bindScriptClassScope(tweenClassScope);
  tweenInterp.variables.set('FlxTween',tweenInterp.tweenFacade());
  var tweenProgram=CodenameScriptParser.prepare('spriteProxy=new TweenSpriteProxy();',new Map());
  if(tweenProgram.program==null || CodenameScriptParser.hasFatalDiagnostics(tweenProgram))
   throw 'native FlxSprite proxy setup did not parse';
  tweenInterp.execute(tweenProgram.program);
  var tweenProxy=tweenInterp.variables.get('spriteProxy');
  var nativeTweenSprite=tweenInterp.nativeFlxBasic(tweenProxy);
  if(nativeTweenSprite==null || nativeTweenSprite==tweenProxy)
   throw 'owner-scoped HScript-ex sprite did not resolve to its native FlxBasic';
  tweenInterp.execute(new hscript.Parser().parseString('FlxTween.tween(spriteProxy,{alpha:0.25},1);'));
  if(flixel.tweens.FlxTween.lastTweenObject!=nativeTweenSprite
   || (cast nativeTweenSprite:flixel.FlxSprite).alpha!=0.25)
   throw 'FlxTween facade did not unwrap the owned script-class proxy to its native FlxSprite';
  var plainTweenTarget:Dynamic={x:1};
  tweenInterp.variables.set('plainTweenTarget',plainTweenTarget);
  tweenInterp.execute(new hscript.Parser().parseString('FlxTween.tween(plainTweenTarget,{x:2},1);'));
  if(flixel.tweens.FlxTween.lastTweenObject!=plainTweenTarget)
   throw 'FlxTween facade replaced a non-native target';
  tweenInterp.release();

  var redirectScope=new CodenameScriptInterp(new CodenamePaths('owner/fnas'),new CodenameFlxGFacade());
  redirectScope.variables.set('FlxG',redirectScope.flxG);
  redirectScope.variables.set('Std',Std);
  redirectScope.variables.set('MainMenuState',MainMenuState);
  redirectScope.variables.set('FnasMainState',FnasMainState);
  flixel.FlxG.game._nextState=new MainMenuState();
  var redirectProgram=CodenameScriptParser.prepare(
   'function preStateSwitch(){if(Std.isOfType(FlxG.game._requestedState,MainMenuState)) FlxG.game._requestedState=new FnasMainState();}',
   new Map());
  if(redirectProgram.program==null) throw 'legacy requested-state redirect did not parse';
  redirectScope.execute(redirectProgram.program);
  Reflect.callMethod(null,redirectScope.variables.get('preStateSwitch'),[]);
  if(!Std.isOfType(flixel.FlxG.game._nextState,FnasMainState))
   throw 'legacy requested-state alias did not replace the pending state';
  redirectScope.execute(new hscript.Parser().parseString('FlxG.game.bump(3);'));
  if(flixel.FlxG.game.ticks!=10) throw 'legacy alias hid native FlxG.game methods or fields';
  redirectScope.release();

  var mountedUi=CodenameScriptParser.prepare(sys.io.File.getContent(Sys.args()[0]),new Map());
  if(mountedUi.publicVariables.indexOf('newHealthBar')<0
   || mountedUi.publicVariables.indexOf('statsTxt')<0)
   throw 'mounted D-Sides UI public fields were not extracted';

  var colorFacadeCalls=0;
  var colorFacade:Dynamic={fromString:function(value:String):Int {colorFacadeCalls++;return 0xFF123456;}};
  var colorBindings:Map<String,Dynamic>=new Map(); colorBindings.set('flixel.util.FlxColor',colorFacade);
  var colorInterp=new CodenameScriptInterp(new CodenamePaths('mounted-try-harder'),new CodenameFlxGFacade());
  colorInterp.variables.set('FlxColor',colorFacade); colorInterp.protectImportAliases(colorBindings);
  var mountedColorProgram=CodenameScriptParser.prepare(sys.io.File.getContent(Sys.args()[6]),
   colorBindings,'songs/try-harder/scripts/events.hx');
  if(mountedColorProgram.program==null || CodenameScriptParser.hasFatalDiagnostics(mountedColorProgram))
   throw 'mounted Try Harder color expression fixture did not parse';
  colorInterp.execute(mountedColorProgram.program);
  if(colorInterp.variables.get('FlxColor')!=colorFacade || colorFacadeCalls!=1
   || colorInterp.variables.get('lyricColor')!=0xFF123456)
   throw 'mounted Try Harder color assignments replaced the FlxColor facade or hid Lyrics.fromString';
  var donorColorCount:Int=cast colorInterp.variables.get('donorColorCount');
  for (index in 0...donorColorCount) if(colorInterp.variables.get('donorColor'+index)==null)
   throw 'mounted Try Harder color assignment lost its RHS value at '+index;
  colorInterp.release();

  var syntheticColorFacadeCalls=0;
  var syntheticColorFacade:Dynamic={fromString:function(value:String):Int {
   syntheticColorFacadeCalls++;return value=='#AABBCC' ? 0xFFAABBCC : 0;
  }};
  var syntheticColorBindings:Map<String,Dynamic>=new Map();
  syntheticColorBindings.set('flixel.util.FlxColor',syntheticColorFacade);
  var syntheticColorInterp=new CodenameScriptInterp(new CodenamePaths('synthetic-color'),new CodenameFlxGFacade());
  syntheticColorInterp.variables.set('FlxColor',syntheticColorFacade);
  syntheticColorInterp.protectImportAliases(syntheticColorBindings);
  var syntheticColorProgram=CodenameScriptParser.prepare(
   'import flixel.util.FlxColor; assignedColor = FlxColor = 0xFF0A274F; parsedColor = FlxColor.fromString("#AABBCC");',
   syntheticColorBindings,'synthetic-color.hx');
  if(syntheticColorProgram.program==null || CodenameScriptParser.hasFatalDiagnostics(syntheticColorProgram))
   throw 'synthetic imported-color assignment fixture did not parse';
  syntheticColorInterp.execute(syntheticColorProgram.program);
  if(syntheticColorInterp.variables.get('FlxColor')!=syntheticColorFacade
   || syntheticColorInterp.variables.get('assignedColor')!=0xFF0A274F
   || syntheticColorInterp.variables.get('parsedColor')!=0xFFAABBCC
   || syntheticColorFacadeCalls!=1)
   throw 'bare assignment to an imported alias did not preserve its facade and RHS value';
  syntheticColorInterp.release();

  var a = scope('first'); var b = scope('second');
  var classSource='class SharedWindow extends TestWindow { public var ownerStamp:String=ownerName; public var label:String="initial"; '
   +'public function new(value:Float){x=value;center();super(x,0,100,40);} public function center():Void{x+=7;} }';
  var classA=new hscript.ScriptClassScope(); classA.seed('ownerName','owner-a'); classA.seed('TestWindow',TestWindow);
  var classB=new hscript.ScriptClassScope(); classB.seed('ownerName','owner-b'); classB.seed('TestWindow',TestWindow);
  classA.registerModule(new hscript.ParserEx().parseModule(classSource));
  classB.registerModule(new hscript.ParserEx().parseModule(classSource));
  var classInterpA=new CodenameScriptInterp(new CodenamePaths('class-owner-a'),new CodenameFlxGFacade());
  var classInterpB=new CodenameScriptInterp(new CodenamePaths('class-owner-b'),new CodenameFlxGFacade());
  classInterpA.bindScriptClassScope(classA); classInterpB.bindScriptClassScope(classB);
  classInterpA.variables.set('TestWindow',TestWindow); classInterpB.variables.set('TestWindow',TestWindow);
  var classProgram=CodenameScriptParser.prepare('window=new SharedWindow(5); stamp=window.ownerStamp; '
   +'window.label="owner-write"; labelRoundTrip=window.label; window.center(); xAfter=window.x;',new Map());
  if(classProgram.program==null || CodenameScriptParser.hasFatalDiagnostics(classProgram)) throw 'owner class script parse';
  classInterpA.execute(classProgram.program);
  var classProgramB=CodenameScriptParser.prepare('window=new SharedWindow(9); stamp=window.ownerStamp; xAfter=window.x;',new Map());
  classInterpB.execute(classProgramB.program);
  if(classInterpA.variables.get('stamp')!='owner-a' || classInterpB.variables.get('stamp')!='owner-b'
   || classInterpA.variables.get('labelRoundTrip')!='owner-write'
   || classInterpA.variables.get('xAfter')!=19 || classInterpB.variables.get('xAfter')!=16)
   throw 'owner class field initialization, native field dispatch, pre-super assignments, or center';
  classInterpA.release();
  var releasedClass=false;
  try classInterpA.execute(new hscript.Parser().parseString('window.center();')) catch (_:Dynamic) releasedClass=true;
  if(!releasedClass || classInterpB.variables.get('xAfter')!=16)
   throw 'owner class scope release leaked into second owner';
  classInterpB.release();
  var hl17Root=Sys.args()[1];
  var hl17Menu=sys.io.File.getContent(hl17Root+'/data/states/HL17MainMenu.hx');
  var hl17Imports=CodenameScriptParser.importPaths(hl17Menu);
  var menuBindings:Map<String,Dynamic>=new Map();
  menuBindings.set('flixel.FlxG',{}); menuBindings.set('flixel.FlxState',{});
  for (name in hl17Imports) if(name!='HLCreditsWindow' && name!='HLOptionsWindow' && name!='HLSelectWindow')
   menuBindings.set(name,{});
  var classLoad=CodenameScriptClassLoader.load(hl17Root,hl17Imports,menuBindings,new Map());
  if(classLoad.scope.findDescriptor('HLCreditsWindow')==null
   || classLoad.scope.findDescriptor('HLSelectWindow')==null
   || !classLoad.imports.exists('HLOptionsWindow')) throw 'HL17 imported source class registration';
  for (name in classLoad.imports.keys()) menuBindings.set(name,classLoad.imports.get(name));
  var hl17Program=CodenameScriptParser.prepare(hl17Menu,menuBindings,'data/states/HL17MainMenu.hx');
  if(CodenameScriptParser.hasFatalDiagnostics(hl17Program)) throw 'HL17 menu import parse: '+hl17Program.diagnostics;
  if(classLoad.scope.findDescriptor('HLOptionsWindow')==null || classLoad.diagnostics.length!=0)
   throw 'HL17 options-window class did not load after field terminator repair: '+classLoad.diagnostics;
  classLoad.scope.release();
  var syntheticLoad=CodenameScriptClassLoader.load(Sys.args()[2],['MissingTerminator'],new Map(),new Map());
  if(syntheticLoad.scope.findDescriptor('MissingTerminator')==null || syntheticLoad.diagnostics.length!=0)
   throw 'generic missing array-field terminator was not repaired: '+syntheticLoad.diagnostics;
  syntheticLoad.scope.release();
  var unsupportedInline=CodenameScriptClassLoader.load(Sys.args()[2],['UnsupportedInlineMethod'],new Map(),new Map());
  if(unsupportedInline.diagnostics.length!=0
   || unsupportedInline.scope.findDescriptor('UnsupportedInlineMethod')==null)
   throw 'expression-bodied source method did not load: '+unsupportedInline.diagnostics;
  var inlineObject=unsupportedInline.scope.createInstance('UnsupportedInlineMethod',[]);
  var inlineValue:Dynamic=inlineObject==null ? null : inlineObject.callFunction('read',[]);
  if(inlineObject==null || inlineValue!=1)
   throw 'expression-bodied source method did not retain its return value';
  unsupportedInline.scope.release();
  var methodBindings:Map<String,Dynamic>=new Map();
  methodBindings.set('ProbeNativeWindowBase',ProbeNativeWindowBase);
  methodBindings.set('Layout',{VERTICAL:'vertical',HORIZONTAL:'horizontal'});
  var methodLoad=CodenameScriptClassLoader.load(Sys.args()[2],['MiniOptionsWindow'],methodBindings,new Map());
  if(methodLoad.diagnostics.length!=0 || methodLoad.scope.findDescriptor('MiniOptionsWindow')==null)
   throw 'nested class-method regression module failed to load: '+methodLoad.diagnostics;
  var miniWindow=methodLoad.scope.createInstance('MiniOptionsWindow',[]);
  miniWindow.callFunction('initializeAndAddToState',[null]);
  var inheritedProperties:Bool=miniWindow.callFunction('verifyInheritedProperties',[]);
  var unknownNativeFieldRejected=false;
  try miniWindow.callFunction('writeMissingNativeField',[]) catch (error:Dynamic)
   unknownNativeFieldRejected=Std.string(error).indexOf('noSuchNativeField')>=0;
  var externalErrorCaught=false;
  try miniWindow.callFunction('failNested',[]) catch (error:Dynamic) externalErrorCaught=true;
  var localAssignments:Bool=miniWindow.callFunction('verifyLocalAssignmentPriority',[]);
  Reflect.setProperty(miniWindow.superClass,'visible',true);
  var parameterAssignment:Bool=miniWindow.callFunction('verifyParameterAssignmentPriority',[true]);
  var parameterPreservedSuper:Bool=Reflect.getProperty(miniWindow.superClass,'visible');
  var miniOutput:Dynamic=miniWindow.callFunction('getOutput',[]);
  if(miniOutput==null) throw 'nested class method did not preserve output field assignment';
  if(Reflect.field(miniOutput,'configured')!=1
   || Reflect.field(miniOutput,'tabContent')!=Reflect.field(miniOutput,'gameplay')
   || !externalErrorCaught || !inheritedProperties || !unknownNativeFieldRejected
   || !localAssignments || !parameterAssignment || !parameterPreservedSuper)
   throw 'nested class methods result: configured='+Std.string(Reflect.field(miniOutput,'configured'))
    +' tab-preserved='+Std.string(Reflect.field(miniOutput,'tabContent')==Reflect.field(miniOutput,'gameplay'))
    +' external-error-caught='+Std.string(externalErrorCaught)
    +' inherited-properties='+Std.string(inheritedProperties)
    +' unknown-field-rejected='+Std.string(unknownNativeFieldRejected)
    +' local-assignment-priority='+Std.string(localAssignments)
    +' parameter-assignment-priority='+Std.string(parameterAssignment)
    +' parameter-preserved-super='+Std.string(parameterPreservedSuper);
  methodLoad.scope.release();

  var alphaLoad=CodenameScriptClassLoader.load(Sys.args()[2],['CameraAlphaWriter'],new Map(),new Map());
  if(alphaLoad.diagnostics.length!=0 || alphaLoad.scope.findDescriptor('CameraAlphaWriter')==null)
   throw 'camera alpha class fixture failed to load: '+alphaLoad.diagnostics;
  var classCamera=new flixel.FlxCamera();
  var alphaWriter=alphaLoad.scope.createInstance('CameraAlphaWriter',[]);
  alphaWriter.callFunction('writeAlpha',[classCamera,0.75]);
  var readAlpha:Dynamic=alphaWriter.callFunction('readAlpha',[classCamera]);
  var readAlphaNumber=Std.parseFloat(Std.string(readAlpha));
  if(classCamera.alpha!=0.75 || readAlphaNumber!=0.75)
   throw 'HScript-ex class method camera alpha access did not reach the native property';
  alphaLoad.scope.release();

  // Exercise the selected-owner loader with the mounted HL17 Bopper source,
  // while all asset access and scene placement remain host supplied.
  var ownerRoot=Sys.args()[2];
  var atlasCalls:Array<String>=[];
  var ownerPaths:Dynamic={getSparrowAtlas:function(char:String):Dynamic {
   atlasCalls.push(char); return 'owner-atlas:'+char;
  }};
  var ownerBindings:Map<String,Dynamic>=new Map();
  ownerBindings.set('FlxSprite',flixel.FlxSprite);
  ownerBindings.set('flixel.FlxSprite',flixel.FlxSprite);
  ownerBindings.set('Paths',ownerPaths);
  var ownerInterp=new CodenameScriptInterp(new CodenamePaths(ownerRoot),new CodenameFlxGFacade());
  var ownerSource='import Bopper;\nplaced=new Bopper(12,34).setCharacter("characters/huggy");\n'
   +'placed.x=91; placed.alpha=0.25; unplaced=new Bopper(5,6);';
  var ownerPrepared=CodenameScriptClassLoader.prepareOwnerScript(ownerRoot,ownerSource,
   ownerBindings,ownerInterp.variables,ownerInterp,'songs/owner-fixture.hx');
  if(ownerPrepared.classLoad.diagnostics.length!=0 || ownerPrepared.classLoad.sourceUseDiagnostics.length!=0
   || !ownerPrepared.classLoad.imports.exists('Bopper')
   || ownerPrepared.classLoad.scope.findDescriptor('Bopper')==null
   || ownerPrepared.parsed.program==null || CodenameScriptParser.hasFatalDiagnostics(ownerPrepared.parsed))
   throw 'selected-owner Bopper did not load/parse: '+ownerPrepared.classLoad.diagnostics+' '+ownerPrepared.parsed.diagnostics;
  ownerInterp.execute(ownerPrepared.parsed.program);
  var ownerProxy:Dynamic=ownerInterp.variables.get('placed');
  var ownerNative=ownerInterp.nativeFlxBasic(ownerProxy);
  var unplacedNative=ownerInterp.nativeFlxBasic(ownerInterp.variables.get('unplaced'));
  var manuallyCreatedProxy:Dynamic=ownerPrepared.classLoad.scope.createInstance('Bopper',[7,8]);
  var manuallyCreatedNative:flixel.FlxBasic=cast (cast manuallyCreatedProxy:hscript.ScriptClass).superClass;
  if(ownerNative==null || unplacedNative==null || atlasCalls.length!=1
   || atlasCalls[0]!='characters/huggy' || Reflect.field(ownerNative,'x')!=91
   || Reflect.field(ownerNative,'alpha')!=0.25
   || Reflect.field(ownerNative,'frames')!='owner-atlas:characters/huggy'
   || Reflect.field(ownerNative,'animationCalls').length!=1
   || Reflect.field(ownerNative,'animationCalls')[0][0]!='idle'
   || Reflect.field(ownerNative,'animationCalls')[0][1]!='idle'
   || Reflect.field(ownerNative,'animationCalls')[0][2]!=24
   || Reflect.field(ownerNative,'animationCalls')[0][3]!=false
   || ownerInterp.nativeFlxBasic(manuallyCreatedProxy)!=null)
   throw 'Bopper native superclass, owner Paths, or proxy mutation bridge failed';
  var ownerScene=new flixel.FlxState();
  ownerScene.add(ownerNative);
  ownerInterp.claimSceneObject(ownerProxy);
  ownerInterp.claimSceneObject(ownerProxy);

  var missingBindings:Map<String,Dynamic>=new Map();
  missingBindings.set('FlxSprite',flixel.FlxSprite);
  missingBindings.set('Paths',ownerPaths);
  var missingPrepared=CodenameScriptClassLoader.prepareOwnerScript(Sys.args()[4],
   'import Bopper; actor=new Bopper(0,0);',missingBindings,new Map(),null,'songs/foreign-only.hx');
  var missingWasOwnerLocal=false;
  for (diagnostic in missingPrepared.classLoad.diagnostics)
   if(diagnostic.indexOf('no explicit owner binding or source module for import Bopper')>=0)
    missingWasOwnerLocal=true;
  if(!missingWasOwnerLocal || !CodenameScriptParser.hasFatalDiagnostics(missingPrepared.parsed))
   throw 'sibling-owner class source was imported or lacked an explicit diagnostic: '+missingPrepared.classLoad.diagnostics;
  missingPrepared.classLoad.scope.release();

  var unsafe=CodenameScriptClassLoader.load(ownerRoot,['../Bopper'],new Map(),new Map());
  if(unsafe.diagnostics.length!=1 || unsafe.diagnostics[0].indexOf('unsafe class import: ../Bopper')<0)
   throw 'unsafe class path did not produce an explicit rejection: '+unsafe.diagnostics;
  unsafe.scope.release();

  var foreignBindings:Map<String,Dynamic>=new Map();
  foreignBindings.set('FlxSprite',flixel.FlxSprite);
  foreignBindings.set('Paths',ownerPaths);
  var foreignLoad=CodenameScriptClassLoader.load(Sys.args()[3],['Bopper','Plain'],foreignBindings,new Map());
  if(foreignLoad.diagnostics.length!=0) throw 'foreign fixture class load: '+foreignLoad.diagnostics;
  var foreignInterp=new CodenameScriptInterp(new CodenamePaths(Sys.args()[3]),new CodenameFlxGFacade());
  foreignInterp.bindScriptClassScope(foreignLoad.scope);
  foreignInterp.execute(new hscript.Parser().parseString('foreign=new Bopper(1,2); plain=new Plain();'));
  var foreignProxy:Dynamic=foreignInterp.variables.get('foreign');
  var plainProxy:Dynamic=foreignInterp.variables.get('plain');
  var foreignNative=foreignInterp.nativeFlxBasic(foreignProxy);
  if(foreignNative==null || ownerInterp.nativeFlxBasic(foreignProxy)!=null
   || ownerInterp.nativeFlxBasic(plainProxy)!=null)
   throw 'foreign or non-FlxBasic class proxies crossed the owner scene bridge';
  foreignInterp.release();
  if(ownerInterp.nativeFlxBasic(foreignProxy)!=null)
   throw 'released owner class proxy was accepted by another interpreter';

  ownerInterp.release();
  if(ownerNative.destroyCount!=0 || unplacedNative.destroyCount!=1
   || manuallyCreatedNative.destroyCount!=0)
   throw 'placed class proxy cleanup was duplicated or unplaced proxy leaked';
  ownerScene.remove(ownerNative,true);
  ownerNative.destroy();
  if(ownerNative.destroyCount!=1 || ownerScene.members.indexOf(ownerNative)>=0)
   throw 'scene owner did not detach and destroy its class proxy exactly once';
  manuallyCreatedNative.destroy();
  if(manuallyCreatedNative.destroyCount!=1) throw 'external same-owner proxy cleanup';

  var optional = new CodenameScriptInterp(new CodenamePaths('optional'), new CodenameFlxGFacade());
  optional.variables.set('disableScript', optional.disableScript);
  optional.execute(new hscript.Parser().parseString('disableScript();'));
  if (!optional.scriptDisabled || a.scriptDisabled || b.scriptDisabled)
   throw 'disableScript must affect only its interpreter';
  optional.release();
  a.execute(new hscript.Parser().parseString("customLabel = new FunkinText(1, 2, 30, 'title', 24);"));
  var customLabel:Dynamic=a.variables.get('customLabel');
  if(customLabel.paths!=a.paths || customLabel.args.join(',')!='1,2,30,title,24')
   throw 'FunkinText constructor receives selected owner context';
  a.execute(new hscript.Parser().parseString("if(lerp(2,10,0.25)!=4 || lerp(2,10,1.5)!=14) throw 'Codename lerp';"));
  var stateScript = new CodenameScriptInterp(new CodenamePaths('state-owner'), new CodenameFlxGFacade());
  stateScript.bindScriptObject({});
  var nativeHealth:Float = 1.75;
  stateScript.bindLiveGlobal('health', function():Dynamic return nativeHealth,
   function(value:Dynamic):Void nativeHealth = value);
  var healthProgram=CodenameScriptParser.prepare(
   'var lastHealth = health; function readInitialHealth(){return lastHealth;} '
   +'function readHealth(){return health;} function writeHealth(value){health=value;}', new Map());
  if(healthProgram.program==null || healthProgram.diagnostics.length!=0)
   throw 'gameplay health global program did not prepare';
  stateScript.execute(healthProgram.program);
  var readInitialHealth:Dynamic=stateScript.variables.get('readInitialHealth');
  if(Reflect.callMethod(null,readInitialHealth,[])!=1.75)
   throw 'top-level gameplay initializer did not read native health';
  var readHealth:Dynamic=stateScript.variables.get('readHealth');
  var writeHealth:Dynamic=stateScript.variables.get('writeHealth');
  nativeHealth=0.25;
  if(Reflect.callMethod(null,readHealth,[])!=0.25)
   throw 'gameplay callback read a stale health value';
  Reflect.callMethod(null,writeHealth,[0.5]);
  if(nativeHealth!=0.5) throw 'gameplay health assignment did not reach PlayState';
  var stateProgram = CodenameScriptParser.prepare(
   "var iTime:Float=0; function create(){so={animation:'idle'};} "
   +"function update(elapsed:Float){iTime+=elapsed;} "
   +"function stepHit(){so.animation='jump';} "
   +"function snapshot(){return {iTime:iTime,animation:so.animation};}", new Map());
  if(stateProgram.program==null || stateProgram.diagnostics.length!=0)
   throw 'state callback fields did not prepare';
  stateScript.execute(stateProgram.program);
  var stateCreate:Dynamic=stateScript.variables.get('create');
  var stateUpdate:Dynamic=stateScript.variables.get('update');
  var stateStep:Dynamic=stateScript.variables.get('stepHit');
  var stateSnapshot:Dynamic=stateScript.variables.get('snapshot');
  stateCreate(); stateUpdate(0.25); stateStep();
  var snapshot:Dynamic=stateSnapshot();
  if(snapshot.iTime!=0.25 || snapshot.animation!='jump')
   throw 'Codename state field lifetime across callbacks: '+snapshot.iTime+'/'+snapshot.animation;
  stateScript.release();


  var publicSource="public var newHealthBar:Dynamic;\\npublic var statsTxt:Dynamic;\\npublic var canPlayGFAnims:Bool=true;\\n"
   +"function createHud(){newHealthBar={id:'bar'}; statsTxt={text:'created'};} "
   +"function readHud(){return [newHealthBar.id,statsTxt.text,canPlayGFAnims];}";
  var stageSource="function stepHit(){newHealthBar.id='stage'; statsTxt.text='stage'; canPlayGFAnims=false; "
   +"return [newHealthBar.id,statsTxt.text,canPlayGFAnims];}";
  var publicProgram=CodenameScriptParser.prepare(publicSource,new Map());
  var stageProgram=CodenameScriptParser.prepare(stageSource,new Map());
  if(publicProgram.program==null || stageProgram.program==null
   || publicProgram.publicVariables.join(',')!='newHealthBar,statsTxt,canPlayGFAnims')
   throw 'top-level public field extraction failed: '+publicProgram.publicVariables.join(',')
    +' ui='+[for(d in publicProgram.diagnostics) d.message].join(';')
    +' stage='+[for(d in stageProgram.diagnostics) d.message].join(';');
  var publicGlobals=new CodenamePublicScriptGlobals();
  var uiScope=new CodenameScriptInterp(new CodenamePaths('owner/song'),new CodenameFlxGFacade());
  var stageScope=new CodenameScriptInterp(new CodenamePaths('owner/stage'),new CodenameFlxGFacade());
  publicGlobals.attach(stageScope); // Stage may load before the song's public module.
  publicGlobals.declare(uiScope,publicProgram.publicVariables,'songs/UI.hx','songs/UI.hx');
  uiScope.execute(publicProgram.program);
  stageScope.execute(stageProgram.program);
  Reflect.callMethod(null,uiScope.variables.get('createHud'),[]);
  var stageStep:Dynamic=stageScope.variables.get('stepHit');
  var uiRead:Dynamic=uiScope.variables.get('readHud');
  var stageValues:Array<Dynamic>=cast stageStep();
  var uiValues:Array<Dynamic>=cast uiRead();
  if(stageValues[0]!='stage' || stageValues[1]!='stage' || stageValues[2]!=false
   || uiValues[0]!='stage' || uiValues[1]!='stage' || uiValues[2]!=false)
   throw 'public module fields did not share live object/value writes across song and stage scopes';

  var foreignGlobals=new CodenamePublicScriptGlobals();
  var foreignScope=new CodenameScriptInterp(new CodenamePaths('foreign/song'),new CodenameFlxGFacade());
  var foreignProgram=CodenameScriptParser.prepare(
   "public var newHealthBar:Dynamic='foreign'; function getForeign(){return newHealthBar;}",new Map());
  foreignGlobals.declare(foreignScope,foreignProgram.publicVariables,'songs/UI.hx','songs/UI.hx');
  foreignScope.execute(foreignProgram.program);
  if(Reflect.callMethod(null,foreignScope.variables.get('getForeign'),[])!='foreign'
   || publicGlobals.getField('newHealthBar').id!='stage')
   throw 'public module fields crossed selected-owner PlayState storage';
  publicGlobals.releaseScope('songs/UI.hx');
  if(publicGlobals.hasField('newHealthBar') || publicGlobals.hasField('statsTxt'))
   throw 'song teardown retained its public module values';
  var tornDown=false;
  try stageStep() catch (_:Dynamic) tornDown=true;
  if(!tornDown) throw 'stage callback retained released song public fields';
  publicGlobals.detach(uiScope); publicGlobals.detach(stageScope); publicGlobals.clear();
  foreignGlobals.releaseScope('songs/UI.hx'); foreignGlobals.detach(foreignScope); foreignGlobals.clear();
  uiScope.release(); stageScope.release(); foreignScope.release();

  var exportedGlobals=new CodenamePublicScriptGlobals();
  var stateScope=new CodenameScriptInterp(new CodenamePaths('owner/state'),new CodenameFlxGFacade());
  var songScope=new CodenameScriptInterp(new CodenamePaths('owner/song'),new CodenameFlxGFacade());
  exportedGlobals.attach(stateScope);
  stateScope.variables.set('scripts',exportedGlobals.scriptFacade('data/states/PlayState.hx',
   'data/states/PlayState.hx'));
  var stateExportProgram=CodenameScriptParser.prepare(
   "static var camHuggy:Dynamic; function create(){camHuggy={zoom:0.75};scripts.set('camHuggy',camHuggy);}",
   new Map());
  if(stateExportProgram.program==null || stateExportProgram.diagnostics.length!=0)
   throw 'state export program did not prepare';
  stateScope.execute(stateExportProgram.program);
  Reflect.callMethod(null,stateScope.variables.get('create'),[]);
  exportedGlobals.attach(songScope); // Late song scopes inherit existing state exports.
  var songReadProgram=CodenameScriptParser.prepare(
   'function readStateCamera(){return camHuggy.zoom;}',new Map());
  if(songReadProgram.program==null || songReadProgram.diagnostics.length!=0)
   throw 'song reader did not prepare';
  songScope.execute(songReadProgram.program);
  if(Reflect.callMethod(null,songScope.variables.get('readStateCamera'),[])!=0.75)
   throw 'state scripts.set export was not visible to the later song scope';
  exportedGlobals.releaseScope('data/states/PlayState.hx');
  var releasedExportRejected=false;
  try Reflect.callMethod(null,songScope.variables.get('readStateCamera'),[])
  catch (_:Dynamic) releasedExportRejected=true;
  if(!releasedExportRejected) throw 'state export survived its owning state script';
  exportedGlobals.detach(stateScope); exportedGlobals.detach(songScope); exportedGlobals.clear();
  stateScope.release(); songScope.release();

  // Exercise the mounted HL17 gameplay module itself: its top-level health
  // snapshot must initialize before create(), which publishes camHuggy for the
  // later song postCreate scope.
  var hl17StateSource=sys.io.File.getContent(hl17Root+'/data/states/PlayState.hx');
  var hl17StateBindings:Map<String,Dynamic>=new Map();
  for(importName in CodenameScriptParser.importPaths(hl17StateSource))
   hl17StateBindings.set(importName, {});
  var hl17StateProgram=CodenameScriptParser.prepare(hl17StateSource
   +'\\nfunction testTopLevelSnapshots() return [lastHealth,lastAccuracy];',
   hl17StateBindings,'data/states/PlayState.hx');
  if(hl17StateProgram.program==null || CodenameScriptParser.hasFatalDiagnostics(hl17StateProgram))
   throw 'HL17 PlayState did not prepare: '+[for(d in hl17StateProgram.diagnostics)d.message].join(';');
  var hl17Globals=new CodenamePublicScriptGlobals();
  var hl17State=new CodenameScriptInterp(new CodenamePaths('hl17-state'),new CodenameFlxGFacade());
  hl17Globals.attach(hl17State);
  hl17State.variables.set('scripts',hl17Globals.scriptFacade('data/states/PlayState.hx','data/states/PlayState.hx'));
  var hl17Health:Float=1.6; var hl17Accuracy:Float=0.72;
  hl17State.bindLiveGlobal('health',function():Dynamic return hl17Health,
   function(value:Dynamic):Void hl17Health=value);
  hl17State.bindLiveGlobal('accuracy',function():Dynamic return hl17Accuracy,
   function(value:Dynamic):Void hl17Accuracy=value);
  hl17State.variables.set('FlxCamera',flixel.FlxCamera);
  var cameraRegistry:Dynamic={
   remove:function(_camera:Dynamic,_splice:Bool):Void {},
   add:function(_camera:Dynamic,_defaultCamera:Bool):Void {}
  };
  hl17State.variables.set('FlxG',{cameras:cameraRegistry});
  hl17State.variables.set('camGame',new flixel.FlxCamera());
  hl17State.variables.set('camHUD',new flixel.FlxCamera());
  hl17State.variables.set('PauseSubState',{script:''});
  hl17State.variables.set('GameOverSubstate',{script:'',gameOverCharacter:null});
  hl17State.execute(hl17StateProgram.program);
  var snapshot:Dynamic=Reflect.callMethod(null,hl17State.variables.get('testTopLevelSnapshots'),[]);
  if(snapshot[0]!=1.6 || snapshot[1]!=0.72)
   throw 'HL17 top-level health/accuracy snapshot was not initialized';
  Reflect.callMethod(null,hl17State.variables.get('create'),[]);
  var exportedCamera=hl17Globals.getField('camHuggy');
  if(exportedCamera==null || hl17Globals.getField('camOther')==null || hl17Globals.getField('camBars')==null)
   throw 'HL17 create did not publish its gameplay cameras';
  var hl17SongSource=sys.io.File.getContent(hl17Root+'/songs/huggyteen-dollars/scripts/script.hx');
  if(hl17SongSource.indexOf('awesome.cameras = [camHuggy]')<0)
   throw 'mounted Huggy postCreate camera consumer changed';
  var hl17Song=new CodenameScriptInterp(new CodenamePaths('hl17-song'),new CodenameFlxGFacade());
  hl17Globals.attach(hl17Song);
  hl17Song.variables.set('FlxSprite',flixel.FlxSprite);
  var laterPostCreate=CodenameScriptParser.prepare(
   'function postCreate(){var awesome=new FlxSprite(); awesome.cameras=[camHuggy]; '
   +'cameraSeen=awesome.cameras[0]; return cameraSeen;}',new Map());
  hl17Song.execute(laterPostCreate.program);
  var postCreateResult=Reflect.callMethod(null,hl17Song.variables.get('postCreate'),[]);
  if(postCreateResult!=exportedCamera || hl17Song.variables.get('cameraSeen')!=exportedCamera)
   throw 'later song postCreate could not resolve the HL17 camHuggy export';
  hl17Globals.releaseScope('data/states/PlayState.hx');
  hl17Globals.detach(hl17State);hl17Globals.detach(hl17Song);hl17Globals.clear();
  hl17State.release();hl17Song.release();

  var staticSource="static var lastStickers:Array<Int> = []; "
   +"function create() { lastStickers.push(7); } "
   +"function snapshot() return lastStickers.join(',');";
  var staticProgram=CodenameScriptParser.prepare(staticSource,new Map());
  if(staticProgram.program==null || staticProgram.diagnostics.length!=0)
   throw 'static transition field did not prepare';
  var outgoing=new CodenameScriptInterp(new CodenamePaths('static-owner'),new CodenameFlxGFacade());
  outgoing.retainModuleGlobals(['lastStickers']);
  outgoing.execute(staticProgram.program);
  Reflect.callMethod(null,outgoing.variables.get('create'),[]);
  var retained:Array<Int>=cast outgoing.variables.get('lastStickers');
  if(retained==null || retained.join(',')!='7') throw 'static field was closure-local';
  var incoming=new CodenameScriptInterp(new CodenamePaths('static-owner'),new CodenameFlxGFacade());
  incoming.retainModuleGlobals(['lastStickers']);
  incoming.execute(staticProgram.program);
  incoming.variables.set('lastStickers',retained);
  if(Reflect.callMethod(null,incoming.variables.get('snapshot'),[])!='7')
   throw 'incoming callback did not see retained static field';
  incoming.release();outgoing.release();
  a.customShaderFactory=function(name:String):Dynamic return {name:name,owner:a.paths.root};
  b.customShaderFactory=function(name:String):Dynamic return {name:name,owner:b.paths.root};
  a.execute(new hscript.Parser().parseString("firstShader = new CustomShader('greenscren');"));
  b.execute(new hscript.Parser().parseString("secondShader = new CustomShader('greenscren');"));
  if(a.variables.get('firstShader').owner!='first' || b.variables.get('secondShader').owner!='second')
   throw 'shader owner escaped';
  var invalidShader=false;
  try a.execute(new hscript.Parser().parseString("new CustomShader(42);")) catch (_:Dynamic) invalidShader=true;
  if(!invalidShader) throw 'invalid shader constructor accepted';
  var characterCalls=0;
  a.variables.set('Character',Character);
  a.characterFactory=function(args:Array<Dynamic>):Dynamic {
   characterCalls++;
   return new Character(args[0],args[1],args[2],args[3]);
  };
  a.execute(new hscript.Parser().parseString("authoredCharacter = new Character(7, 9, 'darnell-tunnel', true);"));
  var authoredCharacter:Character=a.variables.get('authoredCharacter');
  if(characterCalls!=1 || authoredCharacter.character!='darnell-tunnel'
   || authoredCharacter.x!=7 || authoredCharacter.y!=9 || !authoredCharacter.isPlayer)
   throw 'owner-aware Character constructor';
  a.modStateFactory=function(name:String):Dynamic return {stateName:name};
  a.execute(new hscript.Parser().parseString("importedState = new ModState('CreditsVideo');"));
  if(a.variables.get('importedState').stateName!='CreditsVideo') throw 'ModState owner route';
  a.customShaderFactory=function(name:String):Dynamic return new flixel.addons.display.FlxRuntimeShader({
   uRainColor:{type:openfl.display.ShaderParameterType.FLOAT3,value:[0.0,0.0,0.0]},
   uIntensity:{type:openfl.display.ShaderParameterType.FLOAT,value:[0.0]},
   uContrast:{type:openfl.display.ShaderParameterType.FLOAT,value:[0.0]},
   uFloatVector:{type:openfl.display.ShaderParameterType.FLOAT3,value:[0.0,0.0,0.0]},
   enabled:{type:openfl.display.ShaderParameterType.BOOL,value:[false]},
   boolVector:{type:openfl.display.ShaderParameterType.BOOL2,value:[false,false]},
   iTime:{type:openfl.display.ShaderParameterType.FLOAT,value:[0.0]},
   iMode:{type:openfl.display.ShaderParameterType.INT,value:[0]},
   intVector:{type:openfl.display.ShaderParameterType.INT3,value:[0,0,0]},
   uMult:{type:openfl.display.ShaderParameterType.FLOAT,value:[0.0]},
   uCameraBounds:{type:openfl.display.ShaderParameterType.FLOAT4,value:[0.0,0.0,0.0,0.0]}
  });
  a.execute(new hscript.Parser().parseString("shader = new CustomShader('rain'); shader.uRainColor = [0.25, 0.5, 0.75]; shader.uIntensity = 0.125; shader.enabled = true; shader.iTime = 2.5; shader.mult = 0.625; shader.cameraBounds = [1.0,2.0,3.0,4.0]; shader.rainColor = [0.75,0.5,0.25]; if(shader.uIntensity != 0.125 || shader.enabled != true || shader.iTime != 2.5 || shader.mult != 0.625 || shader.cameraBounds[3] != 4.0 || shader.rainColor[0] != 0.75) throw 'shader uniform read or Codename u-prefixed alias';"));
  var numericUniformProgram=CodenameScriptParser.prepare(
   'shader.uContrast = 1.0; shader.uFloatVector = [1, 2, 3]; shader.iMode = 2.9; '
   +'shader.intVector = [1.8, 2, 3.7]; shader.boolVector = [true, false];',new Map());
  if(numericUniformProgram.program==null || CodenameScriptParser.hasFatalDiagnostics(numericUniformProgram))
   throw 'stage-shaped numeric shader assignments did not prepare';
  a.execute(numericUniformProgram.program);
  var shader:flixel.addons.display.FlxRuntimeShader=a.variables.get('shader');
  if(shader.data.uIntensity.value[0]!=0.125 || shader.data.enabled.value[0]!=true
   || shader.data.iTime.value[0]!=2.5 || shader.data.uMult.value[0]!=0.625
   || shader.data.uCameraBounds.value.join(',')!='1,2,3,4'
   || shader.data.uRainColor.value.join(',')!='0.75,0.5,0.25'
   || shader.data.uContrast.value[0]!=1.0 || shader.data.uFloatVector.value.join(',')!='1,2,3'
   || shader.data.iMode.value[0]!=2 || shader.data.intVector.value.join(',')!='1,2,3'
   || shader.data.boolVector.value.join(',')!='true,false' || shader.writes.length!=12)
   throw 'declared shader uniform bridge through computed Shader.data';
  var unknownShaderUniform=false;
  try a.execute(new hscript.Parser().parseString("shader.unknownUniform = 1;")) catch (_:Dynamic) unknownShaderUniform=true;
  if(!unknownShaderUniform || Reflect.hasField(shader.data,'unknownUniform')) throw 'unknown shader field was accepted';
  var nullShaderValue='';
  try a.execute(new hscript.Parser().parseString("shader.uIntensity = null;")) catch (e:Dynamic) nullShaderValue=Std.string(e);
  if(nullShaderValue.indexOf('Unsupported value for shader uniform uIntensity: null')<0)
   throw 'declared shader uniform null value was misreported as unknown';
  var filterCamera=new flixel.FlxCamera();
  var originalFilter=new openfl.filters.BitmapFilter();
  filterCamera.filters=[originalFilter];
  var cameraShader=new flixel.addons.display.FlxRuntimeShader({});
  a.variables.set('FlxSprite',flixel.FlxSprite);
  a.variables.set('filterCamera',filterCamera); a.variables.set('cameraShader',cameraShader);
  a.variables.set('originalFilter',originalFilter);
  a.execute(new hscript.Parser().parseString("filterCamera.addShader(cameraShader); filterCamera.addShader(cameraShader);"));
  var addedFilter:openfl.filters.ShaderFilter=cast filterCamera.filters[1];
  if(filterCamera.filters.length!=2 || filterCamera.filters[0]!=originalFilter
   || addedFilter.shader!=cameraShader) throw 'camera shader filter add or idempotency';
  a.execute(new hscript.Parser().parseString("filterCamera.removeShader(cameraShader);"));
  if(filterCamera.filters.length!=1 || filterCamera.filters[0]!=originalFilter)
   throw 'camera shader filter remove changed unrelated filters';
  a.execute(new hscript.Parser().parseString("filterCamera.setFilters([originalFilter]);"));
  if(filterCamera.filters.length!=1 || filterCamera.filters[0]!=originalFilter)
   throw 'Codename camera setFilters adapter';
  a.execute(new hscript.Parser().parseString("filterCamera.setFilters([]);"));
  if(filterCamera.filters==null || filterCamera.filters.length!=0)
   throw 'Codename camera setFilters empty list';
  a.execute(new hscript.Parser().parseString("filterCamera.setFilters([originalFilter]);"));
  a.execute(new hscript.Parser().parseString("solidSprite = new FlxSprite(); solidResult = solidSprite.makeSolid(12, 7, 0xFF112233);"));
  var solidSprite:flixel.FlxSprite=a.variables.get('solidSprite');
  if(a.variables.get('solidResult')!=solidSprite || solidSprite.solidWidth!=12
   || solidSprite.solidHeight!=7 || solidSprite.solidColor!=0xFF112233)
   throw 'FlxSprite makeSolid compatibility adapter';
  a.execute(new hscript.Parser().parseString("sample = 0; numberTween = FlxTween.num(0, 8, 1, null, function(value) sample = value); angleTween = FlxTween.angle(card, 0, 90, 1); colorTween = FlxTween.color(card, 1, 0, 1);"));
  if(a.variables.get('sample')!=8) throw 'numeric tween callback';
  a.variables.set('game',new Game());
  a.execute(new hscript.Parser().parseString("if(game.misses==null || game.misses!=0) throw 'null instance misses'; game.misses=3; game.misses++;"));
  if(Game.misses!=4) throw 'miss accessor mutation';
  a.execute(new hscript.Parser().parseString("if(game.accuracy!=1) throw 'source ratio'; game.accuracy=0.75; if(game.accuracy!=0.75) throw 'source ratio setter';"));
  if(a.variables.get('game').accuracy!=75) throw 'native percent changed';
  var setting=2;
  a.bindLiveGlobal('setting',function():Dynamic return setting,function(value:Dynamic):Void setting=value);
  var liveParser=new hscript.Parser();
  a.execute(liveParser.parseString("setting += 3; function local(setting) { setting++; return setting; }"));
  if(setting!=5 || a.variables.exists('setting') || Reflect.callMethod(null,a.variables.get('local'),[10])!=11 || setting!=5) throw 'live global writes or local shadow';
  setting=8;a.execute(liveParser.parseString("if(setting!=8) throw 'stale global';"));
  var chart:Dynamic={song:'native-key',speed:1,notes:[[1,2,3]]};
  var meta:Dynamic={name:'authored-key',displayName:'Authored Title',custom:{value:7}};
  var view=new CodenameSongView(function() return chart,meta);
  a.variables.set('SONG',view); a.variables.set('PlayState',{SONG:view});
  b.variables.set('SONG',new CodenameSongView(function() return chart,{name:'other-owner'}));
  var parser=new hscript.Parser();
  a.variables.set('Std',Std);
  a.execute(parser.parseString("if(Std.parseInt(0)!=0 || Std.parseInt(2)!=2 || Std.parseFloat(1.5)!=1.5 || Std.parseInt('3')!=3) throw 'Codename numeric chart-event parameters';"));
  var nativeSave={data:{options:{antialiasing:false},personalSetting:'keep'},flushes:0};
  Reflect.setField(nativeSave,'flush',function():Void nativeSave.flushes++);
  flixel.FlxG.save=nativeSave;
  a.flxG.save=new CodenameOwnerSaveFacade('assets/imported_mods/owner-a');
  b.flxG.save=new CodenameOwnerSaveFacade('assets/imported_mods/owner-b');
  a.variables.set('FlxG',a.flxG); b.variables.set('FlxG',b.flxG);
  var saveProgram=CodenameScriptParser.prepare(
   'FlxG.save.data.mechanics ??= true; FlxG.save.data.modCharts ??= true;',new Map());
  if(saveProgram.program==null || saveProgram.diagnostics.length!=0) throw 'owner save fixture parse';
  a.execute(saveProgram.program);
  if(a.flxG.save.data.getField('mechanics')!=true || a.flxG.save.data.getField('modCharts')!=true
   || b.flxG.save.data.getField('mechanics')!=null) throw 'owner save defaults/isolation';
  b.execute(parser.parseString('FlxG.save.data.mechanics = false;'));
  if(a.flxG.save.data.getField('mechanics')!=true || b.flxG.save.data.getField('mechanics')!=false)
   throw 'owner save write isolation';
  if(nativeSave.data.options.antialiasing!=false || nativeSave.data.personalSetting!='keep'
   || Reflect.field(nativeSave.data,'codenameImportedModData')==null || nativeSave.flushes<3)
   throw 'owner save touched personal values or failed persistence';
  var first=new SourceActor('authored'); var second=new SourceActor('authored');
  var nativeActor=new SourceActor(null);
  a.variables.set('actors',[first,second]); a.variables.set('nativeActor',nativeActor);
  a.variables.set('unrelated',{curCharacter:'unchanged',playAnim:function(v:String) return v});
  // Song/stage scopes have no bound actor. The fifth argument and nullable force must survive.
  a.execute(parser.parseString("actors[0].playAnim('left',null,'SING',true,3); actors[1].playAnim('right',false,'MISS',false,8); actors[0].tryDance(); if (actors[0].curCharacter != 'authored') throw 'source identity'; nativeActor.playAnim('idle',true,true,2); if (nativeActor.curCharacter != 'native-key' || unrelated.curCharacter != 'unchanged' || unrelated.playAnim('ok') != 'ok') throw 'native API changed'; var saved=actors[1].playAnim; saved('held',true,'LOCK',true,6); actors[1].curCharacter='edited';"));
  if (haxe.Json.stringify(first.calls)!='[["source","left",null,"SING",true,3]]' || first.dances!=1)
   throw 'cross-scope nullable force/context';
  if (haxe.Json.stringify(second.calls)!='[["source","right",false,"MISS",false,8],["source","held",true,"LOCK",true,6]]'
   || second.codenameSourceId!='edited' || second.curCharacter!='native-key' || first.codenameSourceId!='authored')
   throw 'actor instance/method reference/write forwarding';
  if (haxe.Json.stringify(nativeActor.calls)!='[["native","idle",true,true,2]]') throw 'native signature';
  a.execute(parser.parseString("actors[0].singAnims=['custom']; if(actors[0].getSingAnim(0,'-alt')!='custom-alt') throw 'directional names'; actors[0].playSingAnim(2,'-alt','MISS',null,true,4); actors[1].playSingAnimUnsafe(1,'','SING',false,false,3);"));
  if(haxe.Json.stringify(first.directional)!='[2,"-alt","MISS",null,true,4]' || haxe.Json.stringify(second.directional)!='["unsafe",1,"","SING",false,false,3]') throw 'directional cross-scope aliases';
  b.bindScriptObject(first, ['curCharacter'=>'codenameSourceId','playAnim'=>'codenamePlayAnim','tryDance'=>'codenameTryDance']);
  b.variables.set('other',second);
  b.execute(parser.parseString("playAnim('self',null,'DANCE'); this.tryDance(); other.playAnim('other',true,'LOCK',false,4);"));
  if (first.calls[1][3]!='DANCE' || first.dances!=2 || second.calls[2][3]!='LOCK' || second.calls[2][5]!=4)
   throw 'character scope self/other routing';
  var actorA=new Actor(); var actorB=new Actor();
  a.bindScriptObject(actorA); b.bindScriptObject(actorB);
  a.execute(parser.parseString("x += 3; x++; ++x; move(2); this.visible=false; value += 4; if (nullable != null || this.x != 17) throw 'parent read'; privateCount=1; function advance() { privateCount++; x++; } function shadow(x) { x++; return x; }"));
  if (actorA.x!=17 || actorA.visible || actorA.value!=6 || actorA.writes!=1) throw 'parent mutation';
  if (a.variables.exists('x') || a.variables.exists('value')) throw 'parent state copied into globals';
  if (Reflect.callMethod(null,a.variables.get('shadow'),[40])!=41 || actorA.x!=17) throw 'local shadow';
  Reflect.callMethod(null,a.variables.get('advance'),[]);
  if (actorA.x!=18 || a.variables.get('privateCount')!=2) throw 'closure parent';
  b.execute(parser.parseString("if (x != 10 || !visible) throw 'actor isolation'; privateCount=8; x=22;"));
  if (actorB.x!=22 || actorA.x!=18 || a.variables.get('privateCount')!=2) throw 'instance isolation';
  a.variables.set('x',null);
  a.execute(parser.parseString("if (x != null) throw 'null global precedence'; x=80;"));
  if (actorA.x!=18 || a.variables.get('x')!=80) throw 'global shadow write';
  a.variables.remove('x');
  var replacement=new Actor(); a.bindScriptObject(replacement);
  Reflect.callMethod(null,a.variables.get('advance'),[]);
  if (replacement.x!=11 || actorA.x!=18) throw 'stale parent after rebind';
  var unknown=false;
  try a.execute(parser.parseString("missingActorProperty;")) catch (_:Dynamic) unknown=true;
  if (!unknown) throw 'unknown property hidden';
  a.execute(parser.parseString("if (SONG.meta.displayName != 'Authored Title' || PlayState.SONG.meta.custom.value != 7) throw 'meta'; SONG.speed += 2; SONG.meta.custom.value=9; SONG.notes[0][2]=11;"));
  if (chart.speed!=3 || chart.notes[0][2]!=11 || meta.custom.value!=9 || Reflect.hasField(chart,'meta'))
   throw 'live chart forwarding or native metadata pollution';
  b.execute(parser.parseString("if (SONG.meta.name != 'other-owner' || SONG.speed != 3) throw 'owner isolation';"));
  chart={song:'replacement',speed:5};
  a.execute(parser.parseString("if (SONG.speed != 5) throw 'chart replacement'; SONG.meta={name:'edited'}; if (PlayState.SONG.meta.name != 'edited') throw 'shared meta';"));
  if (a.flxG.adopted.length != 1 || a.flxG.adopted[0] != a.variables.get('camera')) throw 'camera adoption';
  var card:CodenameFunkinSprite = a.variables.get('card');
  if (card.x != 2 || card.y != 3 || card.resolver != a.paths) throw 'constructor context';
  if (b.variables.get('card').resolver != b.paths) throw 'second context';
  var life=new CodenameScriptInterp(new CodenamePaths('lifetime'),new CodenameFlxGFacade());
  life.variables.set('FlxGroup',flixel.group.FlxGroup.FlxTypedGroup);
  life.variables.set('FlxSprite',flixel.FlxSprite);
  life.execute(parser.parseString("group=new FlxGroup(); wall=new FlxSprite(); group.add(wall); stray=new FlxSprite(); hostGroup=new FlxGroup(); hostChild=new FlxSprite(); hostGroup.add(hostChild);"));
  var group:flixel.group.FlxGroup.FlxTypedGroup<flixel.FlxBasic>=life.variables.get('group');
  var wall:flixel.FlxSprite=life.variables.get('wall');
  var stray:flixel.FlxSprite=life.variables.get('stray');
  var hostGroup:flixel.group.FlxGroup.FlxTypedGroup<flixel.FlxBasic>=life.variables.get('hostGroup');
  var hostChild:flixel.FlxSprite=life.variables.get('hostChild');
  life.claimSceneObject(hostGroup);
  life.release();
  if(group.destroyCount!=1 || wall.destroyCount!=1 || stray.destroyCount!=1
   || hostGroup.destroyCount!=0 || hostChild.destroyCount!=0)
   throw 'unclaimed group/basic lifetime or scene ownership';
  hostGroup.destroy();
  if(hostGroup.destroyCount!=1 || hostChild.destroyCount!=1) throw 'claimed group teardown';
  var rejectedOwner=new CodenameScriptInterp(new CodenamePaths('rejected-state-target'),new CodenameFlxGFacade());
  rejectedOwner.variables.set('FlxState',flixel.FlxState);
  rejectedOwner.flxG.stateSwitch=function(_:Dynamic):Bool return false;
  rejectedOwner.execute(parser.parseString('pending = new FlxState();'));
  var rejectedTarget:flixel.FlxState=rejectedOwner.variables.get('pending');
  if(rejectedOwner.flxG.switchState(rejectedTarget)) throw 'rejected state switch unexpectedly accepted';
  rejectedOwner.release();
  if(rejectedTarget.destroyCount!=1 || rejectedTarget.members!=null)
   throw 'rejected/abandoned state target escaped its creating interpreter cleanup';
  var acceptedOwner=new CodenameScriptInterp(new CodenamePaths('accepted-state-target'),new CodenameFlxGFacade());
  acceptedOwner.variables.set('FlxState',flixel.FlxState);
  acceptedOwner.flxG.stateSwitch=function(_:Dynamic):Bool return true;
  acceptedOwner.execute(parser.parseString('pending = new FlxState();'));
  var acceptedTarget:flixel.FlxState=acceptedOwner.variables.get('pending');
  if(!acceptedOwner.flxG.switchState(acceptedTarget)) throw 'state switch was not accepted';
  acceptedOwner.release();
  if(acceptedTarget.destroyCount!=0 || acceptedTarget.members==null)
   throw 'accepted state target was destroyed with its outgoing interpreter';
  acceptedTarget.destroy();
  if(acceptedTarget.destroyCount!=1 || acceptedTarget.members!=null)
   throw 'accepted state target could not be torn down by its eventual owner';
  var overlayHost=new openfl.display.DisplayObjectContainer();
  var failedGlobal=new CodenameScriptInterp(new CodenamePaths('failed-global'),new CodenameFlxGFacade());
  failedGlobal.variables.set('Sprite',openfl.display.Sprite);
  failedGlobal.variables.set('host',overlayHost);
  var failedProgram=CodenameScriptParser.prepare(
   "function new(){overlay=new Sprite(); host.addChild(overlay); overlay.addEventListener('enterFrame',function(e){}); throw 'partial init';} "
   +"function destroy(){destroyCalls++;}",new Map());
  if(failedProgram.program==null || failedProgram.diagnostics.length!=0) throw 'failed global fixture parse';
  failedGlobal.variables.set('destroyCalls',0);
  var failedRuntime=new CodenameGlobalScriptRuntime(failedGlobal,'data/global.hx');
  if(failedRuntime.initialize(failedProgram.program) || overlayHost.numChildren!=0
   || failedGlobal.variables.get('destroyCalls')!=0 || failedGlobal.variables.get('overlay').listeners.length!=0)
   throw 'failed global new must skip destroy and release children/listeners';
  var reloadHost=new openfl.display.DisplayObjectContainer();
  var reloadCount=0;
  for (visit in 0...2) {
   var global=new CodenameScriptInterp(new CodenamePaths('repeat-owner'),new CodenameFlxGFacade());
   global.variables.set('Sprite',openfl.display.Sprite); global.variables.set('host',reloadHost);
   global.variables.set('created',0); global.variables.set('ticks',0.0); global.variables.set('destroyed',0);
   var source="function new(){created++; overlay=new Sprite(); host.addChild(overlay); overlay.addEventListener('enterFrame',function(e){});} "
    +"function update(elapsed){ticks+=elapsed;} function destroy(){destroyed++; host.removeChild(overlay);}";
   var parsed=CodenameScriptParser.prepare(source,new Map());
   var globalRuntime=new CodenameGlobalScriptRuntime(global,'data/global.hx');
   if(!globalRuntime.initialize(parsed.program) || reloadHost.numChildren!=1) throw 'repeat global init '+visit;
   globalRuntime.update(0.25);
   if(global.variables.get('ticks')!=0.25) throw 'global update callback';
   globalRuntime.destroy(); globalRuntime.destroy();
   if(global.variables.get('created')!=1 || global.variables.get('destroyed')!=1
    || reloadHost.numChildren!=0 || global.variables.get('overlay').listeners.length!=0)
    throw 'repeat global teardown '+visit;
   reloadCount++;
  }
  if(reloadCount!=2) throw 'same-owner global was not reinitialized';
  b.variables.get('timer').active = false;
  a.setPaused(true); a.setPaused(true); b.setPaused(true);
  if (a.variables.get('timer').active || a.variables.get('tween').active || a.variables.get('numberTween').active || a.variables.get('angleTween').active || a.variables.get('colorTween').active) throw 'pause';
  a.execute(new hscript.Parser().parseString("pausedTween = FlxTween.color(card, 1, 1, 2);"));
  if (a.variables.get('pausedTween').active) throw 'created during pause';
  a.setPaused(false); b.setPaused(false);
  if (!a.variables.get('timer').active || !a.variables.get('tween').active || !a.variables.get('numberTween').active || !a.variables.get('angleTween').active || !a.variables.get('colorTween').active || !a.variables.get('pausedTween').active) throw 'resume';
  if (b.variables.get('timer').active) throw 'inactive timer resumed';
  a.setPaused(true);
  a.execute(new hscript.Parser().parseString("filterCamera.addShader(cameraShader);"));
  if(filterCamera.filters.length!=2) throw 'camera shader re-add';
  a.release(); a.release(); a.setPaused(false);
  if(filterCamera.filters.length!=1 || filterCamera.filters[0]!=originalFilter)
   throw 'interpreter release retained camera shader filter';
  var detached=false;
  try a.execute(parser.parseString("this;")) catch (_:Dynamic) detached=true;
  if (!detached) throw 'released parent retained';
  if (!a.flxG.released || b.flxG.released) throw 'camera scope release';
  if (!a.variables.get('timer').cancelled || !a.variables.get('tween').cancelled || !a.variables.get('numberTween').cancelled || !a.variables.get('angleTween').cancelled || !a.variables.get('colorTween').cancelled || !a.variables.get('pausedTween').cancelled) throw 'cleanup';
  if (b.variables.get('timer').cancelled || b.variables.get('tween').cancelled) throw 'cross-scope cancellation';
  b.setPaused(true);
  b.variables.get('tween').cancel();
  b.setPaused(false);
  if (b.variables.get('tween').active) throw 'cancelled tween revived';
  b.release();
 }
}''')
            owner = mounted_try_harder_owner()
            if owner is None:
                mounted_assignments = ['FlxColor = 0xFF0A274F', 'FlxColor = 0xFF000000',
                                       'FlxColor = 0xFFFFE100']
                mounted_lyrics_call = 'poop.color = FlxColor.fromString(j.color);'
            else:
                events = (owner / 'songs/try-harder/scripts/events.hx').read_text()
                lyrics = (owner / 'data/scripts/Lyrics.hx').read_text()
                mounted_assignments = re.findall(r'\bFlxColor\s*=\s*0x[0-9A-Fa-f]+', events)
                lyric_call = re.search(r'poop\.color\s*=\s*FlxColor\.fromString\(j\.color\)\s*;', lyrics)
                if not mounted_assignments or lyric_call is None:
                    self.fail('mounted Try Harder source no longer contains its color assignment/call fixture')
                mounted_lyrics_call = lyric_call.group(0)
            mounted_color_lines = [
                'import flixel.util.FlxColor;',
                *[f'donorColor{index} = ({assignment});'
                  for index, assignment in enumerate(mounted_assignments)],
                f'donorColorCount = {len(mounted_assignments)};',
                'j = {color:"#ABCDEF"};', 'poop = {color:0};',
                mounted_lyrics_call, 'lyricColor = poop.color;',
            ]
            mounted_color_script = base / 'mounted-try-harder-color.hx'
            mounted_color_script.write_text('\n'.join(mounted_color_lines), encoding='utf-8')
            result = subprocess.run([str(ROOT / '.tools/haxe/haxe'), '-cp', str(ROOT / 'source'),
                                     '-cp', str(ROOT / '.haxelib/hscript/2,5,0'), '-cp', str(base),
                                     '-cp', str(hscript_ex),
                                     '--run', 'Main', str(DONOR_UI), str(DONOR_HL17), str(synthetic_owner),
                                     str(foreign_owner), str(empty_owner), '--smoke-song',
                                     str(mounted_color_script)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('[hscript-ex-alpha-access] op=write', result.stdout)
            self.assertIn('[hscript-ex-alpha-access] op=read', result.stdout)
            self.assertIn('owner=CameraAlphaWriter receiver=flixel.FlxCamera field=alpha', result.stdout)


if __name__ == '__main__':
    unittest.main()
