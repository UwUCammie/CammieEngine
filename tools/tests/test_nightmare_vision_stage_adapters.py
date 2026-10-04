"""Owner-scoped NMV sprite and Bopper constructors used by imported stages."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
from tools.haxe_flixel_math_stubs import write_flixel_point_stub


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
IRIS = ROOT / ".haxelib/hscript-iris/1,1,3"


class NightmareVisionStageAdaptersTest(unittest.TestCase):
    def test_script_imports_create_owner_bound_sprites_and_boppers(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        stubs = {
            "flixel/graphics/frames/FlxAtlasFrames.hx": r'''package flixel.graphics.frames;
class FlxAtlasFrames {
 public var path:String;
 public var kind:String;
 public function new(path:String, ?kind:String='flixel'){this.path=path;this.kind=kind;}
}''',
            "flixel/animation/FlxAnimationController.hx": r'''package flixel.animation;
class FakeAnimation {
 public var name:String;
 public var numFrames:Int;
 public function new(name:String,numFrames:Int){this.name=name;this.numFrames=numFrames;}
}
class FakeNameSignal {
 public var callbacks:Array<String->Void> = [];
 public function new(){}
 public function add(callback:String->Void):Void callbacks.push(callback);
 public function dispatch(name:String):Void for(callback in callbacks) callback(name);
}
class FakeFrameSignal {
 public var callbacks:Array<String->Int->Int->Void> = [];
 public function new(){}
 public function add(callback:String->Int->Int->Void):Void callbacks.push(callback);
 public function dispatch(name:String,number:Int,index:Int):Void
  for(callback in callbacks) callback(name,number,index);
}
class FlxAnimationController {
 var names:Map<String,Bool> = [];
 public var curAnim:FakeAnimation;
 public var onFinish:FakeNameSignal = new FakeNameSignal();
 public var onFrameChange:FakeFrameSignal = new FakeFrameSignal();
 public var onLoop:FakeNameSignal = new FakeNameSignal();
 public var pauseCalls:Int=0;
 public var resumeCalls:Int=0;
 public function new(){}
 public function addByPrefix(name:String,prefix:String,?fps:Float=24,?looped:Bool=true,?flipX:Bool=false,?flipY:Bool=false):Void names.set(name,true);
 public function play(name:String,?force:Bool=false,?reversed:Bool=false,?frame:Int=0):Void if(exists(name)) curAnim=new FakeAnimation(name,2);
 public function exists(name:String):Bool return names.exists(name);
 public function pause():Void pauseCalls++;
 public function resume():Void resumeCalls++;
}''',
            "flixel/system/FlxAssets.hx": r'''package flixel.system;
typedef FlxGraphicAsset = Dynamic;''',
            "flixel/util/FlxTimer.hx": r'''package flixel.util;
class FlxTimer {
 public function new() {}
 public function start(time:Float=1, ?onComplete:(FlxTimer)->Void, loops:Int=1):FlxTimer return this;
 public function cancel():Void {}
 public function destroy():Void {}
}''',
            "flixel/FlxSprite.hx": r'''package flixel;
import flixel.graphics.frames.FlxAtlasFrames;
import flixel.animation.FlxAnimationController;
import flixel.system.FlxAssets.FlxGraphicAsset;
class Scale {public var x:Float=1;public var y:Float=1;public function new(){} public function set(x:Float=1,y:Float=1):Void{this.x=x;this.y=y;}}
class FlxSprite {
 public var x:Float; public var y:Float; public var active:Bool=true; public var exists:Bool=true;
 public var camera:Dynamic; public var cameras:Array<Dynamic>;
 public var scale:Scale=new Scale(); public var graphic:Dynamic; public var hitboxUpdates:Int=0;
 public var animation:FlxAnimationController = new FlxAnimationController();
 public var frames(default,set):FlxAtlasFrames;
 public function new(?x:Float=0,?y:Float=0){this.x=x;this.y=y;}
 function set_frames(value:FlxAtlasFrames):FlxAtlasFrames {frames=value;return value;}
 public function loadGraphic(graphic:FlxGraphicAsset,animated:Bool=false,frameWidth:Int=0,frameHeight:Int=0,unique:Bool=false,?key:String):FlxSprite{this.graphic=graphic;return this;}
 public function makeGraphic(width:Int,height:Int,color:Dynamic,?unique:Bool=false,?key:String):FlxSprite{graphic='generated';return this;}
 public function updateHitbox():Void hitboxUpdates++;
 public function destroy():Void{frames=null;graphic=null;}
}''',
            "animate/FlxAnimateController.hx": r'''package animate;
class FlxAnimateController extends flixel.animation.FlxAnimationController {
 public function new(){super();}
 public function findFrameLabelIndices(name:String):Array<Int> return [];
 public function addByFrameLabel(name:String,label:String,?fps:Float=24,?looped:Bool=true,?flipX:Bool=false,?flipY:Bool=false):Void addByPrefix(name,label,fps,looped,flipX,flipY);
 public function addBySymbol(name:String,symbol:String,?fps:Float=24,?looped:Bool=true,?flipX:Bool=false,?flipY:Bool=false):Void addByPrefix(name,symbol,fps,looped,flipX,flipY);
}''',
            "animate/FlxAnimateFrames.hx": r'''package animate;
import flixel.graphics.frames.FlxAtlasFrames;
class FlxAnimateFrames extends FlxAtlasFrames {
 public var addedCollections:Array<FlxAnimateFrames>=[];
 public var dictionary:Map<String,Dynamic> = ['uberkid'=>true];
 public function new(path:String){super(path,'animate');}
 public function existsSymbol(name:String):Bool return dictionary.exists(name);
 public static function fromAnimate(path:String):FlxAnimateFrames return new FlxAnimateFrames(path);
 public static function combineAtlas(items:Array<FlxAtlasFrames>):FlxAtlasFrames return new FlxAtlasFrames(items.map(function(i)return i.path).join(','),'combined');
}''',
            "animate/FlxAnimate.hx": r'''package animate;
class FlxAnimate extends flixel.FlxSprite {
 public var anim:FlxAnimateController=new FlxAnimateController();
 public var library:FlxAnimateFrames;
 public var useRenderTexture:Bool=false;
 public function new(?x:Float=0,?y:Float=0,?simpleGraphic:flixel.system.FlxAssets.FlxGraphicAsset){super(x,y);animation=anim;}
 override function set_frames(value:flixel.graphics.frames.FlxAtlasFrames):flixel.graphics.frames.FlxAtlasFrames {
  super.set_frames(value); library=Std.isOfType(value,FlxAnimateFrames)?cast value:null; return value;
 }
}''',
            "NightmareVisionPaths.hx": r'''class NightmareVisionPaths {
 public var root(default,null):String;
 public function new(root:String)this.root=root;
 public function getAtlasFrames(path:String,?parentFolder:String,allowGPU:Bool=true,checkMods:Bool=true):flixel.graphics.frames.FlxAtlasFrames
  return new flixel.graphics.frames.FlxAtlasFrames(root+'/images/'+path,'flixel');
 public function getTextureAtlas(path:String,?parentFolder:String,allowGPU:Bool=true,checkMods:Bool=true):flixel.graphics.frames.FlxAtlasFrames
  return animate.FlxAnimateFrames.fromAnimate(root+'/images/'+path);
 public function image(key:String,?parentFolder:String,allowGPU:Bool=true,checkMods:Bool=true):Dynamic
  return root+'/images/'+key+'.png';
 public function video(key:String):String return root+'/videos/'+key+'.mp4';
}''',
            "NightmareVisionSaveFacade.hx": r'''class NightmareVisionSaveFacade {public function new(ownerRoot:String,storage:Dynamic){} public function release():Void{}}''',
            "NightmareVisionFlxGView.hx": r'''class NightmareVisionFlxGView {public function new(){} public function getField(field:String):Dynamic return null; public function setField(field:String,value:Dynamic):Dynamic return value;}''',
            "NightmareVisionSaveData.hx": r'''class NightmareVisionSaveData {public function new(){} public function getField(field:String):Dynamic return null; public function setField(field:String,value:Dynamic):Dynamic return value;}''',
            "HxcCompatRuntime.hx": r'''class HxcCompatRuntime {public static function getZIndex(target:Dynamic):Dynamic return 0; public static function setZIndex(target:Dynamic,value:Dynamic):Dynamic return value;}''',
        }

        fixture = r'''import crowplexus.hscript.Parser;
class TestMain {
 static function check(value:Bool,message:String):Void if(!value)throw message;
 static function main():Void {
  var pathsA=new NightmareVisionPaths('assets/imported_mods/owner-a');
  var pathsB=new NightmareVisionPaths('assets/imported_mods/owner-b');
  var interp=new NightmareVisionScriptInterp();
  interp.bindOwnerPaths(pathsA);
  interp.bindImport('flixel.FlxSprite',NightmareVisionFlxSprite);
  interp.bindImport('funkin.objects.Bopper',NightmareVisionBopper);
  var parser=new Parser(); parser.allowTypes=true;
  interp.execute(parser.parseString(
   'import flixel.FlxSprite; import funkin.objects.Bopper; '
   + 'sheet=new FlxSprite(2,3).loadFromSheet("backgrounds/dusk/dusk","skysky"); '
   + 'sheet.loadGraphic("backgrounds/dusk/cream"); sheet.setScale(1.1,1.1); '
   + 'uber=new Bopper(1200,196); uber.loadAtlas("backgrounds/dusk/uberkid"); '
   + 'uber.addAnimByPrefix("idle","uberkid",24,false); uber.danceEveryNumBeats=1; uber.dance(); '
   + 'uber.animateAtlas.useRenderTexture=true; '
   + 'stageAdds=[sheet,uber];'));
  var sheet:NightmareVisionFlxSprite=cast interp.variables.get('sheet');
  var uber:NightmareVisionBopper=cast interp.variables.get('uber');
  check(sheet!=null && sheet.ownerPaths==pathsA && sheet.x==2 && sheet.y==3,'FlxSprite import did not use the selected owner factory');
  check(sheet.frames.path=='assets/imported_mods/owner-a/images/backgrounds/dusk/dusk' && sheet.animation.curAnim.name=='skysky','loadFromSheet did not resolve owner atlas/animation');
  check(sheet.graphic=='assets/imported_mods/owner-a/images/backgrounds/dusk/cream.png','string loadGraphic escaped owner image lookup');
  check(sheet.scale.x==1.1 && sheet.scale.y==1.1 && sheet.hitboxUpdates==1,'source setScale macro behavior was not exposed');
  check(uber!=null && uber.ownerPaths==pathsA && uber.x==1200 && uber.y==196,'Bopper import did not use the selected owner factory');
  check(uber.frames.path=='assets/imported_mods/owner-a/images/backgrounds/dusk/uberkid' && uber.animation.curAnim.name=='idle','Bopper atlas, prefix helper, or dance failed');
  check(uber.animateAtlas==uber && uber.useRenderTexture,'Bopper animateAtlas self-alias did not expose FlxAnimate properties');
  var finished=''; var looped=''; var frameName=''; var frameNumber=-1; var frameIndex=-1;
  uber.onAnimationFinish.add(function(name:String) finished=name);
  uber.onAnimationFrameChange.add(function(name:String,number:Int,index:Int) {
   frameName=name; frameNumber=number; frameIndex=index;
  });
  uber.onAnimationLoop.add(function(name:String) looped=name);
  check(uber.onAnimationFinish==uber.animation.onFinish
   && uber.onAnimationFrameChange==uber.animation.onFrameChange
   && uber.onAnimationLoop==uber.animation.onLoop,'Bopper exposes the live animation signals');
  uber.animation.onFinish.dispatch('idle');
  uber.animation.onFrameChange.dispatch('idle',1,7);
  uber.animation.onLoop.dispatch('idle');
  check(finished=='idle' && frameName=='idle' && frameNumber==1 && frameIndex==7 && looped=='idle',
   'Bopper animation callbacks forward the actual finish/frame/loop signal payloads');
  uber.pauseAnim(); uber.resumeAnim();
  check(uber.animation.pauseCalls==1 && uber.animation.resumeCalls==1,
   'Bopper pauseAnim/resumeAnim forward to the live animation controller');
  check(uber.danceEveryNumBeats==1 && cast(interp.variables.get('stageAdds'),Array<Dynamic>).length==2,'source stage members were not retained for add/layer forwarding');
  check(interp.importBindings.get('flixel.FlxSprite')==NightmareVisionFlxSprite && interp.importBindings.get('funkin.objects.Bopper')==NightmareVisionBopper,'qualified source imports are not owner adapters');
  interp.release();
  check(interp.ownerPaths==null && interp.importBindings.keys().hasNext()==false,'script release retained selected owner paths/import bindings');
  sheet.destroy(); uber.destroy();
  check(sheet.ownerPaths==null && uber.ownerPaths==null,'sprite destruction retained the selected owner');
  var next=new NightmareVisionScriptInterp(); next.bindOwnerPaths(pathsB);
  next.bindImport('flixel.FlxSprite',NightmareVisionFlxSprite);
  next.bindImport('funkin.objects.Bopper',NightmareVisionBopper);
  next.execute(parser.parseString('import flixel.FlxSprite; import funkin.objects.Bopper; '
   + 'sheet=new FlxSprite().loadFromSheet("backgrounds/dusk/dusk","skysky"); uber=new Bopper(); uber.loadAtlas("backgrounds/dusk/uberkid");'));
  check((cast next.variables.get('sheet'):NightmareVisionFlxSprite).frames.path.indexOf('owner-b')>=0
   && (cast next.variables.get('uber'):NightmareVisionBopper).frames.path.indexOf('owner-b')>=0,
   'a later script used asset paths captured from the previous owner');
  next.release();

  var videoInterp=new NightmareVisionScriptInterp();
  videoInterp.bindOwnerPaths(pathsA);
  var camera={visible:false};
  var endState={count:0};
  videoInterp.variables.set('camera',camera);
  videoInterp.variables.set('Paths',pathsA);
  videoInterp.variables.set('endState',endState);
  videoInterp.execute(parser.parseString('video=new FunkinVideoSprite(12,34,false); '
   + 'video.onEnd(function(){camera.visible=true; endState.count++;}); '
   + 'loaded=video.load(Paths.video("RETROSLALA")); if(loaded) video.delayAndStart();'));
  var video:NightmareVisionVideoSprite=cast videoInterp.variables.get('video');
  check(video!=null && video.ownerRoot==pathsA.root
   && video.x==12 && video.y==34,'FunkinVideoSprite did not use the selected owner constructor');
  check(videoInterp.variables.get('loaded')==false,'unsupported video load did not preserve its failure Bool');
  check(camera.visible && endState.count==1,'video load failure did not dispatch onEnd to restore camera visibility');
  check(video.exists,'oneTimeUse=false destroyed the scripted video sprite after completion');
  videoInterp.release(); video.destroy();
 }
}'''

        with tempfile.TemporaryDirectory(prefix="nmv-stage-adapters-", dir=ROOT / "tmp") as directory:
            scratch = Path(directory)
            write_flixel_point_stub(scratch)
            for name, content in stubs.items():
                path = scratch / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, newline='\n')
            (scratch / "TestMain.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(IRIS),
                 "-cp", str(scratch), "--run", "TestMain"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
