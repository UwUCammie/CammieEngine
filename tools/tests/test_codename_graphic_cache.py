"""Exercise Codename's owner-scoped FlxGraphic cache through HScript."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


STUBS = {
    "flixel/graphics/FlxGraphic.hx": '''package flixel.graphics;
class FlxGraphic {
 public var assetsKey:Null<String>; public var destroyOnNoUse:Bool=true; public var useCount:Int=0;
 public function new(?assetsKey:String) this.assetsKey=assetsKey;
 public function incrementUseCount():Void useCount++;
 public function decrementUseCount():Void useCount--;
}''',
    "flixel/FlxBasic.hx": '''package flixel;
class FlxBasic { public function new(){} public function destroy():Void{} }''',
    "flixel/FlxSprite.hx": '''package flixel;
import flixel.graphics.FlxGraphic;
class FlxSprite extends FlxBasic {
 public var alpha:Float=1; public var graphic:FlxGraphic; public var warmed:Int=0;
 public function new(){super();}
 public function loadGraphic(value:FlxGraphic):FlxSprite {graphic=value;return this;}
 public function draw():Void {}
 public function drawComplex(camera:Dynamic):Void warmed++;
 override public function destroy():Void {graphic=null;}
}''',
    "flixel/FlxState.hx": '''package flixel;
class FlxState {
 public var members:Array<FlxBasic>=[]; public function new(){}
 public function insert<T:FlxBasic>(index:Int,basic:T):T {members.insert(index,basic);return basic;}
 public function add<T:FlxBasic>(basic:T):T {members.push(basic);return basic;}
 public function remove<T:FlxBasic>(basic:T,splice:Bool=false):T {members.remove(basic);return basic;}
}''',
    "flixel/FlxG.hx": '''package flixel;
class FlxG { public static var state:Dynamic;public static var camera:Dynamic; }''',
    "CodenamePaths.hx": '''import flixel.graphics.FlxGraphic;
using StringTools;
class CodenamePaths {
 public var root:String;public var requests:Array<String>=[];var graphics:Map<String,FlxGraphic>=new Map();
 public function new(root:String)this.root=root;
 public function getPath(value:String):String {
  if(value==null || value.indexOf('..')>=0) throw '[codename-asset] Invalid asset key: '+value;
  if(haxe.io.Path.isAbsolute(value)) {
   if(!value.startsWith(root+'/')) throw '[codename-asset] Missing scoped asset: '+value;
   return value;
  }
  return root+'/'+value;
 }
 public function graphic(path:String):FlxGraphic {
  requests.push(path);
  if(!graphics.exists(path)) graphics.set(path,new FlxGraphic(path));
  return graphics.get(path);
 }
}''',
}


class CodenameGraphicCacheTest(unittest.TestCase):
    def test_owner_validation_video_noop_warmup_and_lifecycle(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            for relative, source in STUBS.items():
                target = base / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(source, newline='\n')
            (base / "GraphicCacheTestMain.hx").write_text('''
import flixel.FlxG;
import flixel.FlxState;
import flixel.graphics.FlxGraphic;
import hscript.Interp;
import hscript.Parser;
class GraphicCacheTestMain {
 static function check(ok:Bool,message:String):Void if(!ok)throw message;
 static function main():Void {
  var paths=new CodenamePaths(OWNER);
  var state=new FlxState();FlxG.state=state;FlxG.camera={id:'camera'};
  var cache=new CodenameGraphicCache(paths);
  var script=new Interp();var parser=new Parser();
  script.variables.set('graphicCache',cache);
  script.variables.set('Paths',{
   video:function(name:String):String return paths.root+'/videos/'+name+'.mp4',
   image:function(name:String):String return paths.root+'/images/'+name+'.png'
  });
  script.execute(parser.parseString("graphicCache.cache(Paths.video('Chester')); graphicCache.cache(Paths.image('warm')); graphicCache.cache(Paths.image('warm'));"));
  check(paths.requests.length==2 && paths.requests[0]==paths.root+'/images/warm.png'
   && paths.requests[1]==paths.root+'/images/warm.png','only validated raster paths are loaded');
  check(cache.cachedGraphics.length==2 && cache.nonRenderedCachedGraphics.length==2,
   'Codename cache holds each request and queues its draw warmup');
  var held:FlxGraphic=cache.cachedGraphics[0];
  check(held==cache.cachedGraphics[1] && held.useCount==2 && !held.destroyOnNoUse,
   'cached graphic use counts and shared path cache');
  check(state.members.length==1 && state.members[0]==cache,'cache draws before scene members');
  cache.draw();
  check(cache.nonRenderedCachedGraphics.length==0 && cache.warmed==2,
   'draw drains queued graphics through FlxSprite rendering');
  var outside='';
  try cache.cache('/foreign/images/unsafe.png') catch(error:Dynamic) outside=Std.string(error);
  check(outside.indexOf('Missing scoped asset')>=0,'foreign owner path rejection');
  var foreign=new FlxGraphic('/foreign/images/graphic.png');
  cache.cacheGraphic(foreign);
  check(foreign.useCount==0 && cache.cachedGraphics.length==2,'foreign keyed graphic rejection');
  cache.release();
  check(state.members.length==0 && held.useCount==0 && held.destroyOnNoUse,
   'state attachment and all owner cache holds are released');
 }
}
'''.replace("OWNER", repr((base / "owner").as_posix())), newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(base), "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-main", "GraphicCacheTestMain", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = result.stdout + result.stderr
        self.assertIn("[codename-graphic-cache-info]", output)
        self.assertNotIn("[codename-graphic-cache-error]", output)

    def test_interpreter_binding_and_cleanup_are_shared(self):
        bindings = (ROOT / "source/CodenameImportBindings.hx").read_text()
        interp = (ROOT / "source/CodenameScriptInterp.hx").read_text()
        self.assertIn("bindings.set('graphicCache', interp.graphicCache);", bindings)
        self.assertIn("variables.set('graphicCache', graphicCache);", interp)
        self.assertIn("graphicCache.release();", interp)


if __name__ == "__main__":
    unittest.main()
