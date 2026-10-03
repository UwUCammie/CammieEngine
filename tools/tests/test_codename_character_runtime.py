"""Exercise one Codename character script scope per actor instance."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameCharacterRuntimeTest(unittest.TestCase):
    def test_playstate_binds_live_camera_global_for_both_script_scopes(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        self.assertGreaterEqual(source.count("bindLiveGlobal('camFollow'"), 2)

    def test_character_public_imports_follow_the_actor_scope_lifetime(self):
        playstate = (ROOT / 'source/PlayState.hx').read_text()
        runtime = (ROOT / 'source/CodenameCharacterRuntime.hx').read_text()
        self.assertIn("bindCodenameImportScript(interpreter, root, bindings, publicScopeKey);", playstate)
        self.assertIn("codenamePublicScriptGlobals.releaseScope(publicScopeKey);", playstate)
        self.assertIn("codenamePublicScriptGlobals.detach(interpreter);", playstate)
        self.assertIn("onPublicVariables:Array<String>->Void", runtime)
        self.assertIn("onPublicVariables(parsed.publicVariables)", runtime)

    def test_actor_scopes_events_failure_and_cleanup(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            base = Path(directory)
            stubs = {
                'flixel/FlxBasic.hx': '''package flixel;
class FlxBasic { public function new() {} public function destroy():Void {} }''',
                'flixel/FlxState.hx': '''package flixel;
class FlxState extends FlxBasic { public function new() { super(); } }''',
                'flixel/FlxG.hx': '''package flixel;
class TestStateSwitchSignal {
 public function new() {}
 public function addOnce(_listener:Void->Void):Void {}
 public function remove(_listener:Void->Void):Void {}
}
class TestSignals {
 public var postStateSwitch:TestStateSwitchSignal;
 public function new() postStateSwitch = new TestStateSwitchSignal();
}
class FlxG {
 public static var game:Dynamic;
 public static var state:FlxState;
 public static var signals:TestSignals = new TestSignals();
}''',
                'flixel/util/FlxSignal.hx': '''package flixel.util;
class FlxSignal {}
class FlxTypedSignal<T> { public function new() {} public function removeAll():Void {} }''',
                'CodenameGraphicCache.hx': '''class CodenameGraphicCache {
 public function new(_paths:CodenamePaths) {}
 public function release():Void {}
}''',
                'CodenameHL17UICompat.hx': '''import flixel.FlxBasic;
class CodenameHL17UICompat {
 public static function bindValue(_value:Dynamic,_paths:CodenamePaths,
  _claim:FlxBasic->Void):Void {}
}''',
                'flixel/group/FlxGroup.hx': '''package flixel.group;
import flixel.FlxBasic;
class FlxTypedGroup<T:FlxBasic> extends FlxBasic {
 public var members:Array<T>=[];
 public function new() { super(); }
 public function add(member:T):T { members.push(member); return member; }
 public function remove(member:T,splice:Bool=false):T { members.remove(member); return member; }
}
class FlxGroup extends FlxTypedGroup<FlxBasic> {
 public function new() { super(); }
}''',
                'CodenameFlxGFacade.hx': '''class CodenameFlxGFacade {
 public var cameras:Dynamic; public var save:Dynamic=null; public var releases:Int=0;
 public var onStateSwitchAccepted:Dynamic;
 public function new() cameras={adoptCreated:function(camera:Dynamic):Dynamic return camera};
 public function release():Void releases++;
}''',
                'CodenameOwnerSaveData.hx': '''class CodenameOwnerSaveData {
 public function new() {}
 public function getField(_field:String):Dynamic return null;
 public function setField(_field:String,value:Dynamic):Dynamic return value;
}''',
                'flixel/FlxCamera.hx': '''package flixel;
import openfl.filters.BitmapFilter;
class FlxCamera { public var filters:Array<BitmapFilter>; public var lastFocus:Dynamic;
 public var alpha(default,set):Float=1;
 public function new() {}
 function set_alpha(value:Float):Float return alpha=value;
 public function focusOn(point:Dynamic):Void {
  if (Std.isOfType(point,FlxObject)) throw 'focusOn received FlxObject rather than point';
  lastFocus=point;
 }
}''',
                'flixel/FlxObject.hx': '''package flixel;
class FlxObject { public var x:Float; public var y:Float;
 public function new(x:Float,y:Float) { this.x=x; this.y=y; }
 public function getPosition():Dynamic return {x:x,y:y};
}''',
                'Character.hx': '''class Character { public function new() {} }''',
                'flx3d/CodenameFlx3DView.hx': '''package flx3d;
class CodenameFlx3DView extends flixel.FlxSprite {
 public function new() super();
}''',
                'flx3d/CodenameFlx3DCamera.hx': '''package flx3d;
class CodenameFlx3DCamera extends flixel.FlxCamera {
 public function new() super();
}''',
                'flixel/FlxSprite.hx': '''package flixel;
class FlxSprite extends FlxBasic {
 public var x:Float=0; public var y:Float=0; public var width:Float=0; public var alpha:Float=1;
 public var ID:Int=0; public var offset:Dynamic={x:0.0,y:0.0};
 public function new() super();
 public function makeGraphic(width:Int,height:Int,color:Int=0xFFFFFFFF):FlxSprite return this;
}''',
                'flixel/group/FlxSpriteGroup.hx': '''package flixel.group;
import flixel.FlxSprite;
import flixel.group.FlxGroup.FlxTypedGroup;
typedef FlxSpriteGroup=FlxTypedSpriteGroup<FlxSprite>;
class FlxTypedSpriteGroup<T:FlxSprite> extends FlxTypedGroup<T> {
 public var x:Float=0; public var y:Float=0;
 public function new() super();
 public function update(elapsed:Float):Void {}
}''',
                'flixel/text/FlxText.hx': '''package flixel.text;
import flixel.FlxSprite;
import flixel.util.FlxColor;
enum abstract FlxTextBorderStyle(Int) { var OUTLINE=1; }
class FlxText extends FlxSprite {
 public var text:String=''; public var font:String=''; public var color:FlxColor;
 public var borderColor:Int=0; public var borderSize:Float=0;
 public var borderStyle:FlxTextBorderStyle=FlxTextBorderStyle.OUTLINE;
 public function new(x:Float=0,y:Float=0,width:Float=0,text:String='',size:Int=8) {
  super();this.x=x;this.y=y;this.width=width;this.text=text;
 }
}''',
                'flixel/util/FlxColor.hx': '''package flixel.util;
class FlxColor { public static inline var WHITE:Int=0xFFFFFFFF; }''',
                'flixel/addons/display/FlxRuntimeShader.hx': '''package flixel.addons.display;
class FlxRuntimeShader {
 public var data:Dynamic={}; public function new() {}
 public function setBool(name:String,value:Bool):Void {}
 public function setInt(name:String,value:Int):Void {}
 public function setFloat(name:String,value:Float):Void {}
 public function setBoolArray(name:String,value:Array<Bool>):Void {}
 public function setIntArray(name:String,value:Array<Int>):Void {}
 public function setFloatArray(name:String,value:Array<Float>):Void {}
}''',
                'openfl/filters/BitmapFilter.hx': '''package openfl.filters;
class BitmapFilter { public function new() {} }''',
                'openfl/display/DisplayObject.hx': '''package openfl.display;
class DisplayObject {
 public var parent:DisplayObject;
 public function new() {}
 public function removeChild(child:DisplayObject):DisplayObject { child.parent=null; return child; }
}''',
                'openfl/events/EventDispatcher.hx': '''package openfl.events;
class EventDispatcher {
 public function new() {}
 public function addEventListener(type:String, listener:Dynamic, useCapture:Bool=false):Void {}
 public function removeEventListener(type:String, listener:Dynamic, useCapture:Bool=false):Void {}
}''',
                'openfl/filters/ShaderFilter.hx': '''package openfl.filters;
class ShaderFilter extends BitmapFilter {
 public var shader:Dynamic; public function new(shader:Dynamic) { super(); this.shader=shader; }
}''',
                'openfl/display/ShaderParameterType.hx': '''package openfl.display;
enum abstract ShaderParameterType(Int) {
 var BOOL=0; var BOOL2=1; var BOOL3=2; var BOOL4=3;
 var FLOAT=4; var FLOAT2=5; var FLOAT3=6; var FLOAT4=7;
 var INT=8; var INT2=9; var INT3=10; var INT4=11;
 var MATRIX2X2=12; var MATRIX2X3=13; var MATRIX2X4=14; var MATRIX3X2=15;
 var MATRIX3X3=16; var MATRIX3X4=17; var MATRIX4X2=18; var MATRIX4X3=19; var MATRIX4X4=20;
}''',
                'CodenamePaths.hx': 'class CodenamePaths { public var root:String; public function new(root:String) this.root=root; public function font(path:String):String return path; public function getFontName(path:String):String return path; }',
                'Controls.hx': 'class Controls { public var SWITCHMOD:Bool=false; public function new() {} }',
                'CodenameFunkinSprite.hx': '''class CodenameFunkinSprite {
 public function new(x:Float=0,y:Float=0,?graphic:Dynamic,?resolver:Dynamic) {}
}''',
                'CodenameFunkinText.hx': '''class CodenameFunkinText {
 public function new() {}
 public static function fromArgs(_args:Array<Dynamic>,_paths:CodenamePaths):CodenameFunkinText
  return new CodenameFunkinText();
}''',
                'flixel/util/FlxTimer.hx': '''package flixel.util;
class FlxTimer { public var active:Bool=true; public var finished:Bool=false;
 public var time:Float=0; public var elapsedLoops:Int=0;
 public var cancelled=false; public function new() {}
 public function start(duration:Float, callback:FlxTimer->Void):FlxTimer return this;
 public function cancel():Void { cancelled=true; finished=true; active=false; }
 public function destroy():Void {}
}''',
                'flixel/tweens/FlxTween.hx': '''package flixel.tweens;
enum abstract FlxTweenType(Int) { var ONESHOT=8; var PERSIST=1; var LOOPING=2;
 var PINGPONG=4; var BACKWARD=16; }
class FlxTween { public var active:Bool=true; public var finished:Bool=false;
 public var onComplete:FlxTween->Void;
 public function new() {}
 public static function tween(object:Dynamic, properties:Dynamic, duration:Float=1,
  ?options:Dynamic):FlxTween return new FlxTween();
 public static function num(from:Float,to:Float,duration:Float=1,?options:Dynamic,?onValue:Float->Void):FlxTween return new FlxTween();
 public static function angle(sprite:Dynamic,from:Float,to:Float,duration:Float=1,?options:Dynamic):FlxTween return new FlxTween();
 public static function color(sprite:Dynamic,duration:Float,from:Dynamic,to:Dynamic,?options:Dynamic):FlxTween return new FlxTween();
 public static function cancelTweensOf(object:Dynamic):Void {}
 public static function completeTweensOf(object:Dynamic):Void {}
 public function cancel():Void { finished=true; active=false; }
 public function destroy():Void {}
}''',
            }
            for name, content in stubs.items():
                path = base / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, newline='\n')
            (base / 'Main.hx').write_text('''class Actor {
 public var x:Int=0;
 public var calls:Int=0;
 public function new() {}
}
class Main {
 static function check(value:Bool, message:String):Void { if (!value) throw message; }
 static function main() {
  var log:Array<String>=[];
  var releasedA=0; var releasedB=0;
  var source="import sample.Helper; " +
   "function create() { log.push(tag + ':create'); x++; } " +
   "function postCreate() { log.push(tag + ':postCreate'); } " +
   "function onXML(e) { e.cancelled=true; e.node='changed'; calls++; " +
   "if (!e.xml.has.texture || e.xml.att.texture != 'old') throw 'xml access'; " +
   "e.xml.att.texture='new'; e.xml.node.anim.att.name='edited'; " +
   "return {cancelled:false}; } " +
   "function bad() { throw 'broken'; } " +
   "function destroy() { log.push(tag + ':destroy'); } " +
   "function focusCamera() { probeCamera.focusOn(probeTarget); } " +
   "function moveCamera(dx,dy) { camFollow.x += dx; camFollow.y += dy; } " +
   "function readCameraX() { return camFollow.x; } " +
   "function replaceCamera(next) { camFollow = next; }";
  var bindings:Map<String,Dynamic>=new Map(); bindings.set('sample.Helper', 'helper');
  var actorA=new Actor(); var actorB=new Actor();
  var interpA=new CodenameScriptInterp(new CodenamePaths('a'),new CodenameFlxGFacade());
  var interpB=new CodenameScriptInterp(new CodenamePaths('b'),new CodenameFlxGFacade());
  interpA.bindScriptObject(actorA); interpB.bindScriptObject(actorB);
  interpA.variables.set('log',log); interpA.variables.set('tag','a');
  interpB.variables.set('log',log); interpB.variables.set('tag','b');
  var cameraA:Dynamic={x:10.0,y:20.0};
  var cameraB:Dynamic={x:30.0,y:40.0};
  var activeCameraA:Dynamic=cameraA;
  var activeCameraB:Dynamic=cameraB;
  interpA.bindLiveGlobal('camFollow',function():Dynamic return activeCameraA,
   function(value:Dynamic):Void activeCameraA=value);
  interpB.bindLiveGlobal('camFollow',function():Dynamic return activeCameraB,
   function(value:Dynamic):Void activeCameraB=value);
  var liveDad:Dynamic=actorA;
  interpA.bindLiveGlobal('dad',function():Dynamic return liveDad,
   function(value:Dynamic):Void liveDad=value);
  var nativeStageCharacter=new Character();
  check(!interpA.isStageActorAlias('dad',actorA),
   'non-native actor was classified as a stage-character alias');
  check(interpA.isStageActorAlias('dad',nativeStageCharacter)
   && !interpA.isStageActorAlias('gf',nativeStageCharacter),
   'stage-character alias requires both native Character type and a live binding');
  var a=new CodenameCharacterRuntime(interpA,source,'a.hx',bindings,function() releasedA++);
  var b=new CodenameCharacterRuntime(interpB,source,'b.hx',bindings,function() releasedB++);
  check(a.ready && b.ready && !a.destroyed && !b.destroyed,'initial state');
  var probeCamera=new flixel.FlxCamera();
  interpA.variables.set('probeCamera',probeCamera);
  interpA.variables.set('probeTarget',new flixel.FlxObject(42,64));
  check(a.call('focusCamera',[]) && probeCamera.lastFocus.x==42
   && probeCamera.lastFocus.y==64,'camera focus target was not adapted to a point');
  check(a.call('moveCamera',[3.0,5.0]) && cameraA.x==13 && cameraA.y==25,
   'camera alias writes live follow target');
  var readCameraX:Dynamic=interpA.variables.get('readCameraX');
  var replacementCamera:Dynamic={x:100.0,y:200.0};
  activeCameraA=replacementCamera;
  check(a.call('readCameraX',[]) && readCameraX()==100,
   'camera alias reads replacement target');
  check(a.call('moveCamera',[2.0,-3.0]) && replacementCamera.x==102 && replacementCamera.y==197,
   'camera alias remains live as follow target moves');
  var assignedCamera:Dynamic={x:-5.0,y:9.0};
  check(a.call('replaceCamera',[assignedCamera]) && activeCameraA==assignedCamera,
   'camera alias assignment updates owning state');
  check(log.length==0 && actorA.x==0 && actorB.x==0,'create called by constructor');
  check(a.call('create',[]) && b.call('create',[]),'create');
  check(actorA.x==1 && actorB.x==1 && log.join(',')=='a:create,b:create','instance binding');
  check(b.call('postCreate',[]) && a.call('postCreate',[]),'postCreate');
  check(log.join(',')=='a:create,b:create,b:postCreate,a:postCreate','caller lifecycle order');
  var xml=Xml.parse('<char texture="old"><anim name="idle"/></char>').firstElement();
  var event:Dynamic={cancelled:false,node:'original',xml:new CodenameXmlAccess(xml)};
  check(a.event('onXML',event)==event && event.cancelled && event.node=='changed','event mutation');
  check(xml.get('texture')=='new' && xml.firstElement().get('name')=='edited','XML mutation');
  var view:CodenameXmlAccess=event.xml;
  check(view.hasNode.getField('anim') && (cast view.nodes.getField('anim'):Array<Dynamic>).length==1 &&
   (cast view.node.getField('anim'):CodenameXmlAccess).att.getField('name')=='edited','XML access views');
  check(actorA.calls==1 && actorB.calls==0,'event isolation');
  var replacement:Dynamic={cancelled:false};
  check(a.event('missing',replacement)==replacement && !replacement.cancelled,'absent event');
  check(a.call('missing',[]),'absent callback');
  check(!a.call('bad',[]) && !a.call('bad',[]),'failed callback');
  check(a.diagnostics.length==1 && a.diagnostics[0].indexOf('callback:bad:')==0,'failure once');
  check(a.call('postCreate',[]) && b.call('postCreate',[]),'failure isolation');
  var timer=new flixel.util.FlxTimer();
  // Actor-owned interpreter resources obey the runtime pause.
  var timed=new CodenameCharacterRuntime(new CodenameScriptInterp(new CodenamePaths('timer')),
   'timer = new FlxTimer();', 'timer.hx', new Map());
  check(timed.ready,'timer parse');
  timed.setPaused(true);
  check(!timed.interp.variables.get('timer').active,'pause');
  timed.setPaused(false);
  check(timed.interp.variables.get('timer').active,'resume');
  timed.destroy(); timed.destroy();
  check(timed.interp.variables.get('timer').cancelled,'resource cleanup');
  a.destroy(); a.destroy();
  check(a.destroyed && !a.ready && releasedA==1 && interpA.flxG.releases==1,'release once');
  check(log.indexOf('a:destroy')>=0 && log.indexOf('b:destroy')<0,'independent destroy');
  check(!a.call('postCreate',[]) && b.call('postCreate',[]),'destroy isolation');
  b.destroy(); b.destroy();
  check(releasedB==1 && interpB.flxG.releases==1 && log.indexOf('b:destroy')>=0,'second release');
  var emptyReleases=0;
  var empty=new CodenameCharacterRuntime(new CodenameScriptInterp(new CodenamePaths('empty')),
   null,'empty.hx',new Map(),function() emptyReleases++);
  check(empty.ready && empty.call('create',[]) && empty.diagnostics.length==0,'optional script');
  empty.destroy(); empty.destroy(); check(emptyReleases==1,'optional release');
  var recursive:CodenameCharacterRuntime=null;
  var recursiveInterp=new CodenameScriptInterp(new CodenamePaths('recursive'));
  var destroyCalls=0; var recursiveReleases=0;
  recursive=new CodenameCharacterRuntime(recursiveInterp,null,'recursive.hx',new Map(),
   function() recursiveReleases++);
  recursiveInterp.variables.set('destroy',function() {
   destroyCalls++; recursive.destroy();
  });
  recursive.destroy(); recursive.destroy();
  check(destroyCalls==1 && recursiveReleases==1 && recursive.destroyed,
   'recursive destroy callback reentered cleanup');
  var parseReleases=0;
  var broken=new CodenameCharacterRuntime(new CodenameScriptInterp(new CodenamePaths('parse')),
   'function nope( {','parse.hx',new Map(),function() parseReleases++);
  check(!broken.ready && broken.diagnostics.length>0 && parseReleases==1,'parse cleanup');
  broken.destroy(); check(parseReleases==1,'failed parse idempotence');
  var bodyReleases=0;
  var body=new CodenameCharacterRuntime(new CodenameScriptInterp(new CodenamePaths('body')),
   "throw 'body error';",'body.hx',new Map(),function() bodyReleases++);
  check(!body.ready && body.diagnostics.length==1 && bodyReleases==1,'body cleanup');
  body.destroy(); check(bodyReleases==1,'failed body idempotence');
 }
}''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                 '-cp', str(ROOT / '.haxelib/hscript/2,5,0'),
                 '-cp', str(ROOT / '.haxelib/hscript-ex/git/src'), '-cp', str(base),
                 '--run', 'Main'], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
