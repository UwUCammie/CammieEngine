"""Pinned Paths atlas ordering/cache behavior and owner-key eviction."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND
from test_source_event_preparation import extract_method
ROOT=Path(__file__).resolve().parents[2]
class AtlasCacheTest(unittest.TestCase):
 def test_cache_selection_missing_metadata_and_native_owner_key_translation(self):
  actual=(ROOT/'source/NightmareVisionPaths.hx').read_text()
  donor=(ROOT.parent/'fnf_sources/NightmareVision/source/funkin/Paths.hx').read_text()
  methods='\n'.join(extract_method(actual,'public function '+n+'(') for n in ['getSparrowAtlas','getPackerAtlas','getAtlasFrames','forgetAtlasGraphic'])
  reference='\n'.join(extract_method(donor,'public static inline function '+n+'(').replace('public static inline function','public function') for n in ['getSparrowAtlas','getPackerAtlas','getAtlasFrames'])
  main=r'''
import haxe.io.Path;using StringTools;using haxe.io.Path;
class FlxGraphic {public var key:String;public function new(k:String)key=k;}
class FlxAtlasFrames {public var parent:FlxGraphic;public var kind:String;public function new(g:FlxGraphic,k:String){parent=g;kind=k;}
 public static function fromSparrow(g:FlxGraphic,t:String):FlxAtlasFrames return t==null?null:new FlxAtlasFrames(g,"xml");
 public static function fromAseprite(g:FlxGraphic,t:String):FlxAtlasFrames return t==null?null:new FlxAtlasFrames(g,"json");
 public static function fromSpriteSheetPacker(g:FlxGraphic,t:String):FlxAtlasFrames return t==null?null:new FlxAtlasFrames(g,"txt");}
class FNFAssets {public static var texts:Map<String,String>=[];public static function getText(p:String):String return texts.get(p);}
class FunkinAssets {public static function getContent(p:String):String return FNFAssets.getText(p);public static function exists(p:String):Bool return FNFAssets.texts.exists(p);}
class BasePaths {public var root="owner";public var calls:Array<String>=[];public var tempAtlasFramesCache:Map<String,FlxAtlasFrames>=[];public var tracked:Map<String,FlxGraphic>=[];
 public function new(){}public function getPath(p:String,?f:String,b:Bool=true):String {calls.push("path:"+p);return root+"/"+p;}
 public function exists(p:String):Bool return FNFAssets.texts.exists(p);
 public function image(k:String,?f:String,g:Bool=true,b:Bool=true):FlxGraphic {calls.push("image:"+k);var a=new FlxGraphic(root+"/images/"+k+".png");tracked.set(a.key,a);return a;}
 public function scopeAssetPath(p:String):String return p!=null&&p.startsWith(root+"/")?p:null;
 public function getOwnerAssetCache():Dynamic return {currentTrackedGraphics:tracked};}
class Actual extends BasePaths {public function new(){super();}
'''+methods+r'''
}
class Reference extends BasePaths {public function new(){super();}
'''+reference+r'''
}
class Main {
 static function ok(v:Bool,m:String):Void {if(!v)throw m;}
 static function run(p:Dynamic):String {
  FNFAssets.texts=["owner/images/sheet.xml"=>"xml","owner/images/sheet.json"=>"json","owner/images/sheet.txt"=>"txt","owner/images/json.json"=>"json"];
  var a=p.getAtlasFrames("sheet");ok(a.kind=="xml","Sparrow priority");var count=p.calls.length;
  ok(p.getPackerAtlas("sheet")==a&&p.getSparrowAtlas("sheet")==a&&p.calls.length==count+2,"cross-method cache checked before metadata/image");
  var b=p.getAtlasFrames("json");ok(b.kind=="json","Aseprite before missing Packer");
  ok(p.getPackerAtlas("plain")==null&&p.getSparrowAtlas("plain")==null&&p.getAtlasFrames("plain")==null,"missing metadata null without cache poisoning");
  FNFAssets.texts.set("owner/images/plain.txt","txt");ok(p.getAtlasFrames("plain").kind=="txt","later Packer metadata can load");
  return p.calls.join(",");
 }
 static function main(){ok(run(new Actual())==run(new Reference()),"pinned donor call ordering");
  var a=new Actual();a.getAtlasFrames("sheet");var frame=a.tempAtlasFramesCache.get("owner/images/sheet");
  a.tempAtlasFramesCache.set("authorAlias",frame);frame.parent.key="nightmare-vision:owner:owner/images/sheet.png";
  a.forgetAtlasGraphic(frame.parent);ok(!a.tempAtlasFramesCache.exists("owner/images/sheet")&&!a.tracked.exists("owner/images/sheet.png")&&a.tempAtlasFramesCache.exists("authorAlias"),"translated canonical eviction preserves alias rows");
  var foreign=new FlxGraphic("nightmare-vision:other:other/images/sheet.png");a.tracked.set("owner/keep.png",foreign);a.forgetAtlasGraphic(foreign);
  ok(a.tracked.exists("owner/keep.png"),"foreign native owner key cannot evict own row");
 }
}
'''
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
   (Path(tmp)/'Main.hx').write_text(main,encoding='utf-8')
   r=subprocess.run([*HAXE_COMMAND,'-cp',tmp,'-main','Main','--interp'],cwd=ROOT,capture_output=True,text=True)
   self.assertEqual(r.returncode,0,(r.stdout+r.stderr)[-4000:])
