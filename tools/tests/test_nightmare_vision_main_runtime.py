"""Focused source Main runtime, reflection, and teardown contracts."""
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]


FIXTURES = {
    "openfl/display/Sprite.hx": r'''package openfl.display;
class Sprite {
 public var __cacheBitmap:Dynamic;
 public var __cacheBitmapData:Dynamic;
 public var filters:Dynamic;
 public function new() {}
}''',
    "openfl/display/Stage.hx": r'''package openfl.display;
import openfl.events.Event;
class Stage {
 public var listeners:Array<{type:String, callback:Event->Void, capture:Bool, priority:Int}> = [];
 public function new() {}
 public function addEventListener(type:String, callback:Event->Void, capture:Bool=false,
  priority:Int=0, ?useWeakReference:Bool=false):Void
  listeners.push({type:type, callback:callback, capture:capture, priority:priority});
 public function removeEventListener(type:String, callback:Event->Void, capture:Bool=false):Void {
  for (index in 0...listeners.length) {
   var listener = listeners[index];
   if (listener.type == type && listener.callback == callback && listener.capture == capture) {
    listeners.splice(index, 1); return;
   }
  }
 }
 public function dispatch(event:Event):Void
  for (listener in listeners.copy()) if (listener.type == event.type) listener.callback(event);
}''',
    "openfl/events/Event.hx": r'''package openfl.events;
class Event {
 public final type:String;
 public function new(type:String) this.type=type;
}''',
    "openfl/events/KeyboardEvent.hx": r'''package openfl.events;
class KeyboardEvent extends Event {
 public static inline var KEY_DOWN:String='keyDown';
 public final keyCode:Int;
 public final altKey:Bool;
 public var stopCount:Int=0;
 public function new(type:String,keyCode:Int,altKey:Bool) {super(type);this.keyCode=keyCode;this.altKey=altKey;}
 public function stopImmediatePropagation():Void stopCount++;
}''',
    "flixel/input/keyboard/FlxKey.hx": r'''package flixel.input.keyboard;
class FlxKey { public static inline var ENTER:Int=13; }''',
    "flixel/math/FlxPoint.hx": r'''package flixel.math;
class FlxPoint { public var x:Float; public var y:Float; public function new(x=0.,y=0.) {this.x=x;this.y=y;}
 public function set(x:Float,y:Float):FlxPoint {this.x=x;this.y=y;return this;}
 public function copyFrom(point:FlxPoint):Void {x=point.x;y=point.y;}}
class FlxCallbackPoint extends FlxPoint { public function new(?callback:FlxPoint->Void) super(); }''',
    "flixel/FlxGame.hx": r'''package flixel;
import openfl.display.Sprite;
class FlxGame extends Sprite { public function new() super(); }''',
    "flixel/FlxCamera.hx": r'''package flixel;
import openfl.display.Sprite;
class FlxCamera {
 public var filters:Dynamic;
 public var flashSprite:Sprite;
 public function new(filters:Dynamic) {this.filters=filters;flashSprite=new Sprite();}
}''',
    "flixel/FlxG.hx": r'''package flixel;
import openfl.display.Stage;
class ResizeSignal {
 public var listeners:Array<Int->Int->Void>=[];
 public function new() {}
 public function add(callback:Int->Int->Void):Void listeners.push(callback);
 public function remove(callback:Int->Int->Void):Void listeners.remove(callback);
 public function dispatch(width:Int,height:Int):Void
  for (callback in listeners.copy()) callback(width,height);
}
class Signals { public var gameResized:ResizeSignal=new ResizeSignal(); public function new() {} }
class CameraFrontEnd { public var list:Array<FlxCamera>=[]; public function new() {} }
class FlxG {
 public static var stage:Stage;
 public static var signals:Signals=new Signals();
 public static var cameras:CameraFrontEnd=new CameraFrontEnd();
 public static var game:FlxGame;
 public static var width:Int=1280;
 public static var height:Int=720;
}''',
    "NightmareVisionScriptInterp.hx": r'''package;
class NightmareVisionScriptInterp {
 public var variables:Map<String,Dynamic>=new Map();
 public var imports:Map<String,Dynamic>=new Map();
 public var constructors:Array<{type:Dynamic,make:Array<Dynamic>->Dynamic}>=[];
 var scope:SourceNativeClassScope;
 public function new() {}
 public function sourceClassScope():SourceNativeClassScope {
  if (scope==null) {scope=new SourceNativeClassScope();scope.installReflectionBindings();}
  return scope;
 }
 public function bindImport(path:String,value:Dynamic):Void imports.set(path,value);
 public function bindConstructorFactory(type:Dynamic,make:Array<Dynamic>->Dynamic,owner:Dynamic):Void
  constructors.push({type:type,make:make});
 public function construct(type:Dynamic,args:Array<Dynamic>):Dynamic {
  for (binding in constructors) if (binding.type==type) return binding.make(args);
  throw 'missing constructor factory';
 }
}''',
}


class NightmareVisionMainRuntimeTest(unittest.TestCase):
    def test_listeners_cache_reset_source_reflection_and_teardown(self):
        main = r'''package;
import flixel.FlxCamera;
import flixel.FlxG;
import flixel.FlxGame;
import NightmareVisionScriptInterp;
import openfl.display.Stage;
import openfl.events.KeyboardEvent;
class Main {
 static function check(ok:Bool,message:String):Void if (!ok) throw message;
 static function call(fn:Dynamic,args:Array<Dynamic>):Dynamic return Reflect.callMethod(null,fn,args);
 static function expectThrow(fn:Void->Void,fragment:String):Void {
  var caught=false;try fn() catch (error:Dynamic) caught=Std.string(error).indexOf(fragment)>=0;
  check(caught,'expected error with ' + fragment);
 }
 static function main():Void {
  var stageA=new Stage(); var signalA=new flixel.FlxG.ResizeSignal();
  var stageB=new Stage(); var signalB=new flixel.FlxG.ResizeSignal();
  var runtime=new NightmareVisionMainRuntime('assets/imported_mods/family',stageA,signalA);
  runtime.install();
  check(stageA.listeners.length==1 && stageA.listeners[0].type==KeyboardEvent.KEY_DOWN
   && !stageA.listeners[0].capture && stageA.listeners[0].priority==100,
   'source Main registers Alt+Enter at KEY_DOWN priority 100');
  check(signalA.listeners.length==1,'source Main captures one gameResized callback');
  var enter=new KeyboardEvent(KeyboardEvent.KEY_DOWN,13,true);
  stageA.dispatch(enter);
  check(enter.stopCount==1,'Alt+Enter stops immediate propagation');
  var ordinary=new KeyboardEvent(KeyboardEvent.KEY_DOWN,13,false);
  stageA.dispatch(ordinary);
  check(ordinary.stopCount==0,'Enter without Alt is left untouched');

  var noFilter=new FlxCamera(null); var filtered=new FlxCamera({blur:true});
  noFilter.flashSprite.__cacheBitmap='keep'; noFilter.flashSprite.__cacheBitmapData='keep-data';
  filtered.flashSprite.__cacheBitmap='old'; filtered.flashSprite.__cacheBitmapData='old-data';
  FlxG.cameras.list=[noFilter,filtered];
  var game=new FlxGame(); game.__cacheBitmap='game-old'; game.__cacheBitmapData='game-data'; FlxG.game=game;
  signalA.dispatch(900,600);
  check(filtered.flashSprite.__cacheBitmap==null && filtered.flashSprite.__cacheBitmapData==null,
   'resize invalidates filtered camera flashSprite caches');
  check(noFilter.flashSprite.__cacheBitmap=='keep' && noFilter.flashSprite.__cacheBitmapData=='keep-data',
   'resize leaves cameras without filters untouched');
  check(game.__cacheBitmap==null && game.__cacheBitmapData==null,
   'resize invalidates the FlxGame cache');

  var interp=new NightmareVisionScriptInterp();
  var startMeta={width:1280,height:720,fps:60,skipSplash:true,startFullScreen:false,initialState:Main};
  NightmareVisionMainBindings.install(interp,startMeta,runtime);
  var mainType:Dynamic=interp.variables.get('Main');
  check(mainType==NightmareVisionMainMetadata && interp.imports.get('Main')==mainType,
   'Main resolves to the owner metadata identity, never the native host class');
  var scope=interp.sourceClassScope();
  check(scope.read(mainType,'startMeta')==startMeta
   && scope.read(mainType,'PSYCH_VERSION')=='0.5.2h'
   && scope.read(mainType,'NMV_VERSION')=='1.0'
   && scope.read(mainType,'FUNKIN_VERSION')=='0.2.7',
   'source Main metadata and pinned version fields are exposed');
  var fieldsFn:Dynamic=scope.read(Reflect,'fields');
  var reflectedFields:Array<String>=cast call(fieldsFn,[mainType]);
  check(reflectedFields.indexOf('onResize')>=0 && reflectedFields.indexOf('resetSpriteCache')>=0,
   'Reflect.fields exposes donor private onResize and public resetSpriteCache');
  var hasFieldFn:Dynamic=scope.read(Reflect,'hasField');
  check(call(hasFieldFn,[mainType,'onResize'])==true,
   'Reflect.hasField recognizes donor private onResize');
  var getClassFieldsFn:Dynamic=scope.read(Type,'getClassFields');
  var typeFields:Array<String>=cast call(getClassFieldsFn,[mainType]);
  check(typeFields.indexOf('onResize')>=0,
   'Type.getClassFields exposes donor private onResize');

  filtered.flashSprite.__cacheBitmap='reflect-old'; filtered.flashSprite.__cacheBitmapData='reflect-data';
  var resizeFn:Dynamic=scope.read(mainType,'onResize',false);
  call(resizeFn,[800,600]);
  check(filtered.flashSprite.__cacheBitmap==null && filtered.flashSprite.__cacheBitmapData==null,
   'Reflect-field onResize routes to this owner runtime');
  filtered.flashSprite.__cacheBitmap='static-old'; filtered.flashSprite.__cacheBitmapData='static-data';
  var resetFn:Dynamic=scope.read(mainType,'resetSpriteCache',false);
  call(resetFn,[filtered.flashSprite]);
  check(filtered.flashSprite.__cacheBitmap==null && filtered.flashSprite.__cacheBitmapData==null,
   'Main.resetSpriteCache is callable through the owner class scope');
  expectThrow(function() call(scope.read(mainType,'main'),[]),
   'cannot create a second OpenFL application');
  expectThrow(function() interp.construct(mainType,[]),
   'original app host');
  expectThrow(function() call(scope.read(mainType,'new'),[]),
   'original app host');

  // A later host replacement must not redirect removal away from captured objects.
  FlxG.stage=stageB; FlxG.signals.gameResized=cast {gameResized:signalB};
  runtime.release();
  check(stageA.listeners.length==0 && signalA.listeners.length==0,
   'release removes the exact listeners from the captured stage and signal');
  check(stageB.listeners.length==0 && signalB.listeners.length==0,
   'release does not modify a replacement stage or signal');
  var afterRelease=new KeyboardEvent(KeyboardEvent.KEY_DOWN,13,true);
  stageA.dispatch(afterRelease);
  check(afterRelease.stopCount==0,'released key listener no longer handles events');
  expectThrow(function() call(resizeFn,[800,600]),'runtime has been released');
  expectThrow(function() call(resetFn,[filtered.flashSprite]),'runtime has been released');
  expectThrow(function() runtime.install(),'runtime has been released');
 }
}'''
        with tempfile.TemporaryDirectory(prefix="nv-main-runtime-", dir=ROOT / "tmp") as directory:
            work = Path(directory)
            for relative, content in FIXTURES.items():
                path = work / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
            (work / "Main.hx").write_text(main, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_real_source_interpreter_resolves_main_through_reflect_and_type(self):
        script = r'''package;
import flixel.FlxG;
import openfl.display.Stage;
import openfl.display.Sprite;
import openfl.events.KeyboardEvent;
import NightmareVisionScriptInterp;
import crowplexus.hscript.Parser;
class Main {
 static function check(ok:Bool,message:String):Void if (!ok) throw message;
 static function main():Void {
  var runtime=new NightmareVisionMainRuntime('assets/imported_mods/family',new Stage(),new flixel.FlxG.ResizeSignal());
  runtime.install();
  var interp=new NightmareVisionScriptInterp();
  interp.variables.set('Reflect',Reflect);
  interp.variables.set('Type',Type);
  interp.variables.set('Std',Std);
  NightmareVisionMainBindings.install(interp,
   {width:1280,height:720,fps:60,skipSplash:true,startFullScreen:false,initialState:Main},runtime);
  interp.variables.set('testSprite',new Sprite());
  interp.variables.set('verify',function(ok:Bool,message:String):Void if (!ok) throw message);
  var parser=new Parser(); parser.allowTypes=true;
  var program=parser.parseString('
   var mainClass = Type.resolveClass("Main");
   verify(mainClass == Main, "Type.resolveClass must return this source Main identity");
   verify(Reflect.fields(Main).indexOf("onResize") >= 0, "bare Reflect.fields must expose onResize");
   verify(Reflect.hasField(Main, "onResize"), "bare Reflect.hasField must expose onResize");
   verify(Type.getClassFields(mainClass).indexOf("onResize") >= 0,
    "bare Type.getClassFields must expose onResize");
   var byReflect = Reflect.field(Main, "onResize");
   var byType = Reflect.field(mainClass, "onResize");
   verify(Reflect.isFunction(byReflect) && Reflect.isFunction(byType),
    "Reflect.field must return owner-bound private callback from both class routes");
   byReflect(800, 600);
   byType(700, 500);
   var failed = false;
   try Main.main() catch (error:Dynamic) failed = Std.string(error).indexOf("second OpenFL application") >= 0;
   verify(failed, "Main.main must report unsupported app creation");
   failed = false;
   try new Main() catch (error:Dynamic) failed = Std.string(error).indexOf("original app host") >= 0;
   verify(failed, "new Main must report unsupported app creation");
   var sprite = testSprite;
   sprite.__cacheBitmap = "old";
   sprite.__cacheBitmapData = "old-data";
   Main.resetSpriteCache(sprite);
   verify(sprite.__cacheBitmap == null && sprite.__cacheBitmapData == null,
    "source Main.resetSpriteCache must dispatch to the captured runtime API");
  ');
  interp.execute(program);
  var retired = parser.parseString('var failed = false; try Main.resetSpriteCache(testSprite)
   catch (error:Dynamic) failed = Std.string(error).indexOf("runtime has been released") >= 0;
   verify(failed, "captured callbacks must reject use after owner release");');
  runtime.release();
  interp.execute(retired);
 }
}'''
        with tempfile.TemporaryDirectory(prefix="nv-main-real-interp-", dir=ROOT / "tmp") as directory:
            work = Path(directory)
            for relative, content in FIXTURES.items():
                if relative == "NightmareVisionScriptInterp.hx":
                    continue
                path = work / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
            (work / "Main.hx").write_text(script, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript-iris/1,1,3"), "-cp", str(work),
                 "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_reset_uses_real_openfl_sprite_cache_fields(self):
        probe = r'''import openfl.display.Bitmap;
import openfl.display.BitmapData;
import openfl.display.Sprite;
class CacheProbe {
 static function check(ok:Bool,message:String):Void if (!ok) throw message;
 static function main():Void {
  var sprite=new Sprite();
  var data=new BitmapData(1,1,true,0xFFFFFFFF);
  @:privateAccess sprite.__cacheBitmap=new Bitmap(data);
  @:privateAccess sprite.__cacheBitmapData=data;
  NightmareVisionMainRuntime.resetSpriteCache(sprite);
  check((@:privateAccess sprite.__cacheBitmap)==null && (@:privateAccess sprite.__cacheBitmapData)==null,
   'source cache reset clears real OpenFL Sprite fields');
  NightmareVisionMainRuntime.resetSpriteCache(null);
 }
}'''
        with tempfile.TemporaryDirectory(prefix="nv-main-openfl-", dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "CacheProbe.hx").write_text(probe, encoding="utf-8", newline="\n")
            import os
            env = os.environ.copy()
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["HAXEPATH"] = str(ROOT / ".tools/haxe")
            env["NEKOPATH"] = str(ROOT / ".tools/neko")
            env["PATH"] = os.pathsep.join((env["HAXEPATH"], env["NEKOPATH"], env.get("PATH", "")))
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                 "-lib", "flixel", "-lib", "openfl", "-lib", "lime",
                 "--macro", "flixel.system.macros.FlxDefines.run()", "--main", "CacheProbe", "--interp"],
                cwd=work, env=env, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
