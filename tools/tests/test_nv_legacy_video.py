"""Historical NV video behavior using production adapters and a deterministic decoder."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]


class LegacyVideoTest(unittest.TestCase):
    def test_callbacks_restart_failure_focus_and_owner_teardown(self):
        files = {
            'Event.hx': """class Event {
 public var handlers:Array<Dynamic>=[]; public function new(){}
 public function has(f:Dynamic):Bool {for(h in handlers)if(Reflect.compareMethods(h,f))return true;return false;}
 public function add(f:Dynamic):Void {if(!has(f))handlers.push(f);}
 public function remove(f:Dynamic):Void {handlers=handlers.filter(function(h)return !Reflect.compareMethods(h,f));}
 public function dispatch():Void {for(f in handlers.copy())Reflect.callMethod(null,f,[]);}
}""",
            'flixel/FlxG.hx': """package flixel; class FlxG {
 public static var autoPause=true;
 public static var signals={focusGained:new Event(),focusLost:new Event()};
}""",
            'flixel/util/FlxTimer.hx': """package flixel.util; class FlxTimer {
 public function new(){} public function start(t:Float,f:FlxTimer->Void):FlxTimer return this;
 public function cancel():Void {}
}""",
            'hxvlc/openfl/Location.hx': 'package hxvlc.openfl; typedef Location=Dynamic;',
            'hxvlc/flixel/FlxInternalVideo.hx': """package hxvlc.flixel; import flixel.FlxG;
 class FlxInternalVideo {
 public var onEndReached=new Event();public var onOpening=new Event();public var onFormatSetup=new Event();
 public var onEncounteredError:Dynamic=new Event();public var isPlaying=false;public var disposed=false;
 public var loadOK=true;public var path:String;public var options:Array<String>;public var pauseCalls=0;public var resumeCalls=0;
 var resumeOnFocus=false;
 public function new(){}
 public function load(p:String,o:Array<String>):Bool {if(!loadOK)return false;path=p;options=o;
 FlxG.signals.focusGained.add(onFocusGained);FlxG.signals.focusLost.add(onFocusLost);return true;}
 public function play():Bool {isPlaying=true;onOpening.dispatch();return true;}
 public function pause():Void {pauseCalls++;isPlaying=false;}public function resume():Void {resumeCalls++;isPlaying=true;}
 public function stop():Void isPlaying=false;
 public function onFocusLost():Void {resumeOnFocus=isPlaying;pause();}
 public function onFocusGained():Void {if(resumeOnFocus){resumeOnFocus=false;resume();}}
 public function dispose():Void {disposed=true;FlxG.signals.focusGained.remove(onFocusGained);FlxG.signals.focusLost.remove(onFocusLost);}
 }
""",
            'hxvlc/flixel/FlxVideoSprite.hx': """package hxvlc.flixel; import hxvlc.openfl.Location;
 class FlxVideoSprite {
 public var bitmap:FlxInternalVideo;public var x:Float;public var y:Float;public var exists=true;
 public function new(?instance:Dynamic,x:Float=0,y:Float=0){this.x=x;this.y=y;bitmap=new FlxInternalVideo();}
 public function load(path:Location,?options:Array<String>):Bool return bitmap.load(path,options);
 public function play():Bool return bitmap!=null&&bitmap.play();
 public function pause():Void {if(bitmap!=null)bitmap.pause();}public function resume():Void {if(bitmap!=null)bitmap.resume();}
 public function destroy():Void {exists=false;if(bitmap!=null){bitmap.dispose();bitmap=null;}}
 }
""",
            'NightmareVisionSpriteMethods.hx': 'class NightmareVisionSpriteMethods {public static function bind(a:Dynamic,b:Dynamic):Void{}}',
            'NightmareVisionSpriteRegistry.hx': 'class NightmareVisionSpriteRegistry {public static function peek(a:Dynamic):Dynamic return null;}',
        }
        for name in ['NightmareVisionVideoSprite','NightmareVisionLegacyVideoSprite']:
            source=(ROOT/'source'/f'{name}.hx').read_text().replace('#if cpp','#if true')
            source=source.replace('@:build(NightmareVisionSpriteMacro.build())','')
            files[f'{name}.hx']=source
        files['Main.hx']=r"""import flixel.FlxG;
class Main {
 static function check(v:Bool,s:String):Void {if(!v)throw s;}
 static function paths(root:String):Dynamic return {root:root,
 scopeAssetPath:function(p:String):Dynamic return StringTools.startsWith(p,root+'/')?p:null,
 exists:function(p:String):Bool return sys.FileSystem.exists(p),
 video:function(p:String):String return root+'/'+p+'.mp4'};
 static function main():Void {
  var state={members:[]};
  NightmareVisionLegacyVideoSprite.retainOwner(state,'owner-a');
  NightmareVisionLegacyVideoSprite.retainOwner(state,'owner-a');
  var emptyView=NightmareVisionLegacyVideoSprite.forOwner(state,'owner-a');
  NightmareVisionLegacyVideoSprite.releaseOwner(state,'owner-a');
  check(emptyView==NightmareVisionLegacyVideoSprite.forOwner(state,'owner-a'),'another interpreter retains the empty source registry');
  NightmareVisionLegacyVideoSprite.releaseOwner(state,'owner-a');
  check(emptyView!=NightmareVisionLegacyVideoSprite.forOwner(state,'owner-a'),'last interpreter releases an unused registry');
  NightmareVisionLegacyVideoSprite.releaseOwner(state,'owner-a');
  var a=paths('owner-a');var b=paths('owner-b');
  var v=new NightmareVisionLegacyVideoSprite(state,a,false);var foreign=new NightmareVisionLegacyVideoSprite(state,b,false);
  check(v.x==0&&v.y==0&&!v.destroyOnUse,'legacy boolean is not an X coordinate');
  var events:Array<String>=[];
  v.addCallback('onStart',function()events.push('start'));v.addCallback('onEnd',function()events.push('end'));
  v.addCallback('onFormat',function()events.push('format'));v.addCallback('unknown',function()throw 'unknown callback ran');
  check(v.load('clip',[NightmareVisionLegacyVideoSprite.muted]),'owner key resolves');
  check(v.bitmap.path=='owner-a/clip.mp4','captured owner path');
  v.play();v.bitmap.onFormatSetup.dispatch();v.bitmap.onEndReached.dispatch();
  check(events.join(',')=='start,format,end'&&v.exists,'decoder event order and reusable lifetime');
  v.addCallback('onEnd',function()events.push('late'));
  check(events.length==3,'legacy callback registration does not synthesize completion');
  v.restart(['loop']);check(v.bitmap.options[0]=='loop'&&v.bitmap.path=='owner-a/clip.mp4','restart retained path and supplied options');
  v.bitmap.onFormatSetup.dispatch();v.bitmap.onEndReached.dispatch();
  check(events.join(',')=='start,format,end,start,format,end,late','callbacks survive repeated loads');
  var before=events.length;
  check(!v.load('owner-b/clip.mp4')&&v.exists&&events.length==before,'foreign file rejected without synthetic end or destruction');
  v.restart();check(v.bitmap.path=='owner-a/clip.mp4','rejected load did not replace held source path');
  FlxG.signals.focusLost.dispatch();v.pause();var resumes=v.bitmap.resumeCalls;
  FlxG.signals.focusGained.dispatch();check(v.bitmap.resumeCalls==resumes,'focus regain cannot undo explicit pause');
  v.resume();FlxG.signals.focusLost.dispatch();FlxG.signals.focusGained.dispatch();
  check(v.bitmap.isPlaying,'focus lifecycle restored on explicit resume');
  var view=NightmareVisionLegacyVideoSprite.forOwner(state,'owner-a');
  check(view.length==1&&view==NightmareVisionLegacyVideoSprite.forOwner(state,'owner-a'),'stable owner registry isolation');
  var replacement=[v];NightmareVisionLegacyVideoSprite.replaceForOwner(state,'owner-a',replacement);
  check(replacement==NightmareVisionLegacyVideoSprite.forOwner(state,'owner-a'),'source registry replacement retains array identity');
  var refused=false;try NightmareVisionLegacyVideoSprite.replaceForOwner(state,'owner-a',[foreign]) catch(_:Dynamic)refused=true;
  check(refused,'registry assignment cannot borrow a foreign decoder');
  var once=new NightmareVisionLegacyVideoSprite(state,a);once.destroyOnUse=false;
  var onceBitmap=once.bitmap;onceBitmap.onEndReached.dispatch();
  check(!once.exists&&onceBitmap.disposed,'source constructor captures end destruction registration');
  var retainedBitmap=v.bitmap;NightmareVisionVideoSprite.destroyForState(state);
  check(retainedBitmap.disposed&&!v.exists&&!foreign.exists&&NightmareVisionLegacyVideoSprite.heldVideos.length==0,'shared teardown retires legacy instances');
  var modern=new NightmareVisionVideoSprite(state,a,12,34,false);var formats=0;
  modern.onFormat(function()formats++);modern.load('clip');modern.bitmap.onFormatSetup.dispatch();
  modern.load('clip');modern.bitmap.onFormatSetup.dispatch();check(formats==2,'shared reusable format lifecycle');modern.destroy();
 }
}"""
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as d:
            base=Path(d)
            for name,content in files.items():
                target=base/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(content)
            for owner in ['owner-a','owner-b']:
                (base/owner).mkdir();(base/owner/'clip.mp4').write_bytes(b'fixture')
            result=subprocess.run([*HAXE_COMMAND,'-cp',d,'--main','Main','--interp'],cwd=base,text=True,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_real_interpreter_import_reflection_and_owner_static_bindings(self):
        from test_nv_sprite_integration import sprite_integration_files, NVSpriteIntegrationTest
        files=sprite_integration_files()
        files['NightmareVisionGreenScreenShader.hx']='class NightmareVisionGreenScreenShader { public function new() {} }'
        files['NightmareVisionLegacyVideoSprite.hx']="""class NightmareVisionLegacyVideoSprite {
 public static var heldVideos:Array<NightmareVisionLegacyVideoSprite>=[];
 public var ownerState:Dynamic;public var ownerRoot:String;public var destroyOnUse:Bool;public var pauses=0;public var resumes=0;
 public function new(s:Dynamic,p:Dynamic,d=true){ownerState=s;ownerRoot=p.root;destroyOnUse=d;heldVideos.push(this);}
 public function pause(){pauses++;}public function resume(){resumes++;}
 public static var refs=0;public static function retainOwner(s:Dynamic,r:String):Void{refs++;}public static function releaseOwner(s:Dynamic,r:String):Void{refs--;}
 public static function forOwner(s:Dynamic,r:String)return heldVideos.filter(function(v)return v.ownerState==s&&v.ownerRoot==r);
 public static function replaceForOwner(s:Dynamic,r:String,v:Dynamic):Dynamic return v;
} """
        files['Main.hx']=r"""class Main {
 static function check(v:Bool,s:String){if(!v)throw s;}
 static function configure(state:Dynamic,root:String):Dynamic {
  var paths=new NightmareVisionPaths(root,root);
  var owner=new NightmareVisionSpriteOwner(function(p)return new flixel.graphics.frames.FlxAtlasFrames());
  var i=new NightmareVisionScriptInterp(state);i.bindOwnerPaths(paths);
  NightmareVisionLegacyVideoBindings.install(i,paths,owner);
  i.variables.set('Type',i.sourceClassScope().typeFacade());i.variables.set('Reflect',i.sourceClassScope().reflectFacade());
  return {i:i,owner:owner};
 }
 static function main(){
  var state={};var a=configure(state,'owner-a');var b=configure(state,'owner-b');
  NightmareVisionLegacyVideoBindings.install(a.i,new NightmareVisionPaths('owner-a','owner-a'),a.owner);
  check(NightmareVisionLegacyVideoSprite.refs==2,'reinstall releases old lease without retaining extra owner');
  var parser=new NightmareVisionScriptParser();
  a.i.execute(parser.parseString("import gameObjects.shader.GreenScreenShader; shader=new GreenScreenShader();shaderClass=Type.resolveClass('gameObjects.shader.GreenScreenShader'); import gameObjects.PsychVideoSprite; first=new PsychVideoSprite(false);cls=Type.resolveClass('gameObjects.PsychVideoSprite');second=Type.createInstance(cls,[]);held=Reflect.field(cls,'heldVideos');onStart=VidCallbacks.ONSTART;"));
  b.i.execute(parser.parseString("foreign=new PsychVideoSprite(false);"));
  var first:NightmareVisionLegacyVideoSprite=cast a.i.variables.get('first');
  var second:NightmareVisionLegacyVideoSprite=cast a.i.variables.get('second');
  var foreign:NightmareVisionLegacyVideoSprite=cast b.i.variables.get('foreign');
  check(first.ownerState==state&&first.ownerRoot=='owner-a'&&!first.destroyOnUse&&second.destroyOnUse,'import and Type constructor retain owner and bool default');
  check((cast a.i.variables.get('held'):Array<Dynamic>).length==2,'reflected registry is scoped');
  a.i.execute(parser.parseString("PsychVideoSprite.globalPause();Reflect.field(cls,'globalResume')();"));
  check(first.pauses==1&&second.pauses==1&&foreign.pauses==0&&first.resumes==1&&foreign.resumes==0,'global source methods cannot affect foreign owner in same state');
  check(a.i.variables.get('onStart')=='onStart','source enum abstract constants');
  check(Std.isOfType(a.i.variables.get('shader'),NightmareVisionGreenScreenShader)&&a.i.variables.get('shaderClass')==NightmareVisionGreenScreenShader,'shader import and reflective class identity');
  a.owner.release();var refused=false;
  try a.i.createSourceInstance(NightmareVisionLegacyVideoSprite,[]) catch(_:Dynamic)refused=true;
  check(refused,'released constructor cannot create another video');
  a.i.release();check(NightmareVisionLegacyVideoSprite.refs==1,'release retires current lease once');
  b.i.unbindConstructorFactory(NightmareVisionLegacyVideoSprite);
  check(NightmareVisionLegacyVideoSprite.refs==0,'unbind retires private lease');
  b.i.release();check(NightmareVisionLegacyVideoSprite.refs==0,'release after unbind does not retire twice');
 }
}"""
        NVSpriteIntegrationTest().run_haxe(files)


if __name__ == '__main__':
    unittest.main()
