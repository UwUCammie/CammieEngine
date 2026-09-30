"""Run scoped Codename camera mutations against a pinned-shape Flixel stub."""

from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameCameraFacadeTest(unittest.TestCase):
    def test_scope_journals_host_changes_and_keeps_other_scope_cameras(self):
        stubs = {
            "flixel/FlxBasic.hx": '''package flixel;
class FlxBasic { public function new() {} }''',
            "flixel/math/FlxRect.hx": '''package flixel.math;
class FlxRect {
 public var x:Float; public var y:Float; public var width:Float; public var height:Float;
 public function new(x:Float=0,y:Float=0,width:Float=0,height:Float=0) set(x,y,width,height);
 public static function get(x:Float=0,y:Float=0,width:Float=0,height:Float=0):FlxRect return new FlxRect(x,y,width,height);
 public function set(x:Float,y:Float,width:Float,height:Float):FlxRect {
   this.x=x;this.y=y;this.width=width;this.height=height;return this;
 }
 public function put():Void {}
}''',
            "flixel/FlxState.hx": '''package flixel;
class FlxState { public function new() {} }''',
            "flixel/FlxCamera.hx": '''package flixel;
class FlxCamera {
 public var name:String; public var ID:Int=0; public var destroyed=false;
 public var flashSprite:Dynamic={}; public var destroyCalls=0;
 public function new(?name:String="new") this.name=name;
 public function destroy():Void { destroyed=true; flashSprite=null; destroyCalls++; }
}''',
            "flixel/system/frontEnds/CameraFrontEnd.hx": '''package flixel.system.frontEnds;
import flixel.FlxCamera;
import flixel.FlxG;
class CameraFrontEnd {
 public var list(default,null):Array<FlxCamera>=[];
 var defaults:Array<FlxCamera>=[];
 public function new() {}
 public function add<T:FlxCamera>(camera:T, defaultDrawTarget:Bool=true):T {
   if(camera.flashSprite==null) throw "cannot add destroyed camera";
   list.push(camera); if(defaultDrawTarget) defaults.push(camera); camera.ID=list.length-1; return camera;
 }
 public function insert<T:FlxCamera>(camera:T, position:Int, defaultDrawTarget:Bool=true):T {
   if(camera.flashSprite==null) throw "cannot insert destroyed camera";
   if(position>=list.length) return add(camera,defaultDrawTarget);
   if(position<0) position=list.length+position;
   list.insert(position,camera); if(defaultDrawTarget) defaults.push(camera); return camera;
 }
 public function remove(camera:FlxCamera, destroy:Bool=true):Void {
   if(list.remove(camera)) {
     defaults.remove(camera);
     if(FlxG.camera==camera) FlxG.camera=list.length>0 ? list[0] : null;
     if(destroy) camera.destroy();
   }
 }
 public function setDefaultDrawTarget(camera:FlxCamera,value:Bool):Void {
   if(list.indexOf(camera)<0) return;
   if(value && defaults.indexOf(camera)<0) defaults.push(camera);
   if(!value) defaults.remove(camera);
 }
 public function isDefault(camera:FlxCamera):Bool return defaults.indexOf(camera)>=0;
}''',
            "flixel/FlxG.hx": '''package flixel;
import flixel.system.frontEnds.CameraFrontEnd;
import flixel.FlxBasic;
import flixel.math.FlxRect;
class FlxG {
 public static var cameras:CameraFrontEnd=new CameraFrontEnd();
 public static var camera:FlxCamera;
 public static var width:Int=1280; public static var height:Int=720;
 public static var elapsed:Float=0.016; public static var keys:Dynamic={};
 public static var timeScale:Float=1.0;
 public static var autoPause:Bool=true;
 public static var lastOpenedUrl:String='';
 public static var lastOpenedTarget:String='';
 public static var save:Dynamic;
 static var storedFullscreen:Bool=false;
 public static var fullscreen(get,set):Bool;
 static function get_fullscreen():Bool return storedFullscreen;
 static function set_fullscreen(value:Bool):Bool return storedFullscreen=value;
 public static var random:Dynamic={}; public static var mouse:Dynamic={};
 public static var sound:Dynamic={}; public static var state:Dynamic={}; public static var game:Dynamic={};
 public static var worldBounds:FlxRect=FlxRect.get(0,0,100,100);
 public static var collisionBoundsX:Float=-1;
 public static function collide(?a:FlxBasic,?b:FlxBasic,?callback:Dynamic->Dynamic->Void):Bool {
   collisionBoundsX=worldBounds.x; if(callback!=null) callback(a,b);return true;
 }
 public static function overlap(?a:FlxBasic,?b:FlxBasic,?callback:Dynamic->Dynamic->Void,
    ?process:Dynamic->Dynamic->Bool):Bool {
   collisionBoundsX=worldBounds.x;if(b==null) b=a;
   if(process==null || process(a,b)) { if(callback!=null) callback(a,b);return true; }
   return false;
 }
 public static function switchState(state:FlxState):Void {}
 public static function resetState():Void {}
 public static function openURL(url:String,target:String='_blank'):Void { lastOpenedUrl=url;lastOpenedTarget=target; }
}''',
        }
        fixture = '''import flixel.FlxCamera;
import flixel.FlxG;
class Main {
 static function check(condition:Bool, label:String):Void if(!condition) throw label;
 static function rejects(fn:Void->Void, label:String):Void {
   var rejected=false; try fn() catch (_:Dynamic) rejected=true;
   if(!rejected) throw label;
 }
 static function main():Void {
   var game=new FlxCamera("game"); var hud=new FlxCamera("hud"); var other=new FlxCamera("other");
   FlxG.cameras.add(game,true); FlxG.cameras.add(hud,false); FlxG.cameras.add(other,false);
   FlxG.camera=game;
   var hosts=[game,hud,other];
   var urlScope=new CodenameFlxGFacade(hosts);
   check(urlScope.openURL('https://example.com/path?q=1'),"safe URL was rejected");
   check(FlxG.lastOpenedUrl=='https://example.com/path?q=1',"safe URL was not dispatched to the host bridge");
   check(FlxG.lastOpenedTarget=='_blank',"default browser target changed");
   check(urlScope.openURL('https://example.com/path','_self') && FlxG.lastOpenedTarget=='_self',
     "explicit browser target was not preserved");
   check(!urlScope.openURL('file:///etc/passwd'),"unsafe URL was accepted");
   check(FlxG.lastOpenedUrl=='https://example.com/path' && FlxG.lastOpenedTarget=='_self',
     "unsafe URL reached the host bridge");
   urlScope.release();
   var a=new CodenameFlxGFacade(hosts); var b=new CodenameFlxGFacade(hosts);
   a.timeScale=1.25;
   check(FlxG.timeScale==1.25 && b.timeScale==1.25,"Codename shared time scale");
   var aCam=new FlxCamera("a"); var bCam=new FlxCamera("b");
   a.cameras.add(aCam,false); b.cameras.add(bCam,false);
   var snapshot=a.cameras.list; snapshot.pop();
   check(FlxG.cameras.list.length==5,"list escaped");
   var defaultSnapshot=a.cameras.defaults; defaultSnapshot.pop();
   check(a.cameras.defaults.contains(game) && !a.cameras.defaults.contains(hud),
     "default draw target snapshot escaped");
   a.cameras.remove(hud,true);
   check(!hud.destroyed && FlxG.cameras.list.indexOf(hud)<0,"host removal");
   rejects(function() b.cameras.add(hud,false),"overlapping host lease");
   rejects(function() a.cameras.remove(bCam),"foreign scope camera");
   a.cameras.add(hud,false);
   check(FlxG.cameras.list.indexOf(hud)>=0,"host reorder");
   a.release(); a.release();
   check(aCam.destroyed && !bCam.destroyed && FlxG.cameras.list.indexOf(bCam)>=0,"other scope overwritten");
   check(!game.destroyed && !hud.destroyed && !other.destroyed,"host destroyed");
   check(FlxG.cameras.list.indexOf(game)<FlxG.cameras.list.indexOf(hud),"host order");
   var c=new CodenameFlxGFacade(hosts);
   rejects(function() c.cameras.reset(),"reset swallowed another scope camera");
   c.release();
   var replacement=new FlxCamera("replacement");
   b.cameras.reset(replacement);
   check(FlxG.cameras.list.length==1 && FlxG.camera==replacement,"scoped reset");
   b.release();
   check(FlxG.camera==game && FlxG.cameras.list.length==3,"reset rollback");
   check(bCam.destroyed && replacement.destroyed,"owned camera leak");
   check(!game.destroyed && !hud.destroyed && !other.destroyed,"host reset destruction");
   var selectionScope=new CodenameFlxGFacade(hosts);
   var selection=new FlxCamera("selection");
   selectionScope.cameras.add(selection,false);
   selectionScope.cameras.selectMain(selection);
   FlxG.camera=hud; // another owner selected a different registered camera
   selectionScope.release();
   check(FlxG.camera==hud,"external main selection overwritten");
   FlxG.camera=game;
   var d=new CodenameFlxGFacade(hosts);
   var extra=new FlxCamera("extra");
   rejects(function() d.cameras.remove(extra),"unowned removal accepted");
   d.cameras.insert(extra,99,false);
   check(!FlxG.cameras.isDefault(extra),"insert-at-end default changed");
   d.release();
   check(extra.destroyed && FlxG.cameras.list.length==3,"insert cleanup");
   var e=new CodenameFlxGFacade(hosts);
   var neverAdded=e.cameras.adoptCreated(new FlxCamera("never-added"));
   e.release();
   check(neverAdded.destroyed && FlxG.cameras.list.length==3,"constructor cleanup");
   var scriptScope=new CodenameFlxGFacade(hosts);
   var scriptCam=new FlxCamera("script");
   var interp=new hscript.Interp();
   interp.variables.set("FlxG",scriptScope);
   interp.variables.set("scriptCam",scriptCam);
   var parser=new hscript.Parser();
   interp.execute(parser.parseString("if (!FlxG.cameras.defaults.contains(FlxG.camera)) throw 'default target missing'; FlxG.cameras.add(scriptCam, false); FlxG.cameras.list.pop();"));
   check(FlxG.cameras.list.indexOf(scriptCam)>=0,"HScript getter/list snapshot");
   scriptScope.release();
   check(scriptCam.destroyed && FlxG.cameras.list.length==3,"HScript scope cleanup");
   FlxG.fullscreen=false;
   var fullscreenScope=new CodenameFlxGFacade(hosts,"assets/imported_mods/fullscreen-owner");
   var fullscreenInterp=new hscript.Interp();
   fullscreenInterp.variables.set("FlxG",fullscreenScope);
   fullscreenInterp.execute(parser.parseString("FlxG.fullscreen=true;"));
   check(FlxG.fullscreen,"Codename FlxG fullscreen property");
   fullscreenScope.release();
   var stageScope=new CodenameFlxGFacade(hosts,"same-owner");
   var stageCam=new FlxCamera("stage-camera");
   stageScope.cameras.remove(hud,false);
   stageScope.cameras.add(stageCam,false);
   stageScope.cameras.add(hud,false);
   var ratingScope=new CodenameFlxGFacade(hosts,"same-owner");
   var ratingCam=new FlxCamera("rating-camera");
   ratingScope.cameras.add(ratingCam,false);
   ratingScope.cameras.remove(hud,false);
   ratingScope.cameras.add(hud,false);
   var foreignScope=new CodenameFlxGFacade(hosts,"other-owner");
   rejects(function() foreignScope.cameras.remove(hud,false),"different owner camera reorder");
   foreignScope.release();
   stageScope.release(); // stages can be unloaded before the song script
   check(stageCam.destroyed && FlxG.cameras.list[FlxG.cameras.list.length-1]==hud,
     "later same-owner HUD placement lost on stage release");
   ratingScope.release();
   check(ratingCam.destroyed && FlxG.cameras.list.length==3
     && FlxG.cameras.list[0]==game && FlxG.cameras.list[1]==hud
     && FlxG.cameras.list[2]==other,"overlapping same-owner rollback");
   var collisionScope=new CodenameFlxGFacade(hosts);
   var object=new flixel.FlxBasic();
   collisionScope.worldBounds.set(20,30,40,50);
   check(collisionScope.collide(object,object) && FlxG.collisionBoundsX==20,"scoped collide bounds");
   check(FlxG.worldBounds.x==0 && FlxG.worldBounds.width==100,"collide global restore");
   var hits=0;
   var scriptInterp=new hscript.Interp();
   scriptInterp.variables.set("scope",collisionScope);
   scriptInterp.variables.set("object",object);
   scriptInterp.variables.set("hits",hits);
   scriptInterp.execute(parser.parseString("function onHit() { hits++; } scope.overlap(object, null, onHit);"));
   check(scriptInterp.variables.get("hits")==1,"zero-arity HScript overlap callback");
   check(FlxG.collisionBoundsX==20 && FlxG.worldBounds.x==0,"self overlap bounds/restore");
   var threw=false;
   try collisionScope.overlap(object,object,function(a,b):Void throw "callback error")
   catch (_:Dynamic) threw=true;
   check(threw && FlxG.worldBounds.x==0,"throwing callback restores bounds");
   collisionScope.release(); collisionScope.release();
   var switchingScope=new CodenameFlxGFacade(hosts);
   var switchingCamera=new FlxCamera("switching");
   switchingScope.cameras.add(switchingCamera,false);
   switchingScope.cameras.remove(hud,false);
   // FlxGame.switchState calls cameras.reset before destroying the old state.
   for(camera in FlxG.cameras.list.copy()) FlxG.cameras.remove(camera,true);
   var nextStateCamera=new FlxCamera("next-state");
   FlxG.cameras.add(nextStateCamera,true);
   FlxG.camera=nextStateCamera;
   switchingScope.release();
   check(FlxG.cameras.list.length==1 && FlxG.cameras.list[0]==nextStateCamera
     && FlxG.camera==nextStateCamera,"state reset camera was overwritten");
   check(switchingCamera.destroyCalls==1 && hud.destroyCalls==0
     && FlxG.cameras.list.indexOf(hud)<0,
     "old state camera was destroyed twice or reattached after reset");
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            for name, content in stubs.items():
                path = base / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            (base / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"), "-cp", work,
                 "--run", "Main"], cwd=ROOT, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
