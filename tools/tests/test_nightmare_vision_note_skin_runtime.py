"""Run the real NMV NoteSkin adapter and factory with small rendering stubs."""

import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]


STUBS = {
    "flixel/graphics/frames/FlxAtlasFrames.hx": r'''package flixel.graphics.frames;
class FlxAtlasFrames {
 public var frames:Array<FlxFrame>;
 public function new(names:Array<String>) frames=[for(name in names)new FlxFrame(name)];
}
class FlxFrame { public var name:String; public function new(name:String) this.name=name; }
''',
    "flixel/math/FlxPoint.hx": r'''package flixel.math;
class FlxPoint {
 public var x:Float; public var y:Float;
 public function new(x:Float=0,y:Float=0) {this.x=x;this.y=y;}
 public function set(x:Float=0,y:Float=0):FlxPoint {this.x=x;this.y=y;return this;}
}
class FlxCallbackPoint extends FlxPoint {
 public var callback:Dynamic;
 public function new(?x:Float=0,?y:Float=0,?callback:Dynamic) {super(x,y);this.callback=callback;}
}
''',
    "Strumline.hx": r'''import flixel.graphics.frames.FlxAtlasFrames;
class Strumline {}
class StrumNote {
 public var frames:FlxAtlasFrames;
 public var animation:FakeAnimation = new FakeAnimation();
 public var scale:FakeScale = new FakeScale();
 public var antialiasing:Bool=true; public var isPixel:Bool=false;
 public var baseScale:flixel.math.FlxPoint=new flixel.math.FlxPoint(1,1);
 public var normalSize:Float=1; public var resetAnim:Float=0;
 public var nightmareVisionOffsets:Map<String,Array<Float>>;
 public var nightmareVisionPalette:PsychRGBPalette;
 public var useRGBShader:Bool=false;
 public var nightmareVisionRGB:NightmareVisionRGBGraphics; public var shader:Dynamic;
 public function new() {}
 public function updateHitbox():Void {}
 public function playAnim(name:String,force:Bool=false):Void animation.play(name,force);
}
class FakeScale { public var x:Float=1; public var y:Float=1; public function new() {}
 public function set(x:Float,y:Float):Void {this.x=x;this.y=y;} }
class FakeAnim { public var name:String; public function new(name:String) this.name=name; }
class FakeAnimation {
 public var curAnim:FakeAnim;
 var names:Map<String,String>=new Map();
 public function new() {}
 public function addByPrefix(name:String,prefix:String,fps:Int,looping:Bool):Void names.set(name,prefix);
 public function exists(name:String):Bool return names.exists(name);
 public function play(name:String,force:Bool=false):Void curAnim=new FakeAnim(name);
}
''',
    "Note.hx": r'''import flixel.graphics.frames.FlxAtlasFrames;
import flixel.math.FlxPoint;
import Strumline.FakeAnimation;
import Strumline.FakeScale;
class Note {
 public var nightmareVisionLegacyGeometry=false; public var nightmareVisionSustainInitialized=false; public var nightmareVisionSustainInitialWidth=0.; public var width=100.;
 public var isSustainNote:Bool=false; public var animation:FakeAnimation=new FakeAnimation();
 public var scale:FakeScale=new FakeScale(); public var baseScale:FlxPoint=new FlxPoint(1,1);
 public var frames:FlxAtlasFrames; public var antialiasing:Bool=true; public var normalSize:Float=1;
 public var nightmareVisionRGB:NightmareVisionRGBGraphics; public var shader:Dynamic;
 public function new(sustain:Bool=false) {isSustainNote=sustain;animation.play("PsychDefault");}
 public function resetPsychVisualOffset():Void {}
 public function updateHitbox():Void {}
 public function centerOffsets():Void {}
 public function centerOrigin():Void {}
}
''',
    "NoteSplash.hx": r'''import flixel.graphics.frames.FlxAtlasFrames;
import Strumline.FakeAnimation;
import Strumline.FakeScale;
class NoteSplash {
 public var frames:FlxAtlasFrames; public var animation:FakeAnimation=new FakeAnimation();
 public var variants:Int=0; public var nightmareVisionSplashOffset:Array<Float>;
 public var scale:FakeScale=new FakeScale(); public var antialiasing:Bool=true;
 public var baseScale:flixel.math.FlxPoint=new flixel.math.FlxPoint(1,1);
 public var nightmareVisionRGB:NightmareVisionRGBGraphics; public var shader:Dynamic;
 public var alpha:Float=0.42;
 public function new() {}
}
''',
    "PsychRGBPalette.hx": r'''class PsychRGBPalette {
 public var r:Int; public var g:Int; public var b:Int; public var mult:Float=1;
 public var shader:Dynamic;
 public function new(r:Int=0,g:Int=0,b:Int=0) {this.r=r;this.g=g;this.b=b;shader={};}
 public static function defaultFor(lane:Int,pixel:Bool):PsychRGBPalette
  return new PsychRGBPalette(0xFFC24B99,0xFFFFFFFF,0xFF3C1F56);
 public function copy():PsychRGBPalette return new PsychRGBPalette(r,g,b);
 public function copyValues(other:PsychRGBPalette):Void {r=other.r;g=other.g;b=other.b;mult=other.mult;}
}
''',
    "NightmareVisionRGBGraphics.hx": r'''class NightmareVisionRGBGraphics {
 public var palette:PsychRGBPalette; public var enabled:Bool=true; public var alpha:Float=1; public var flash:Float=0;
 public function new(?palette:PsychRGBPalette) this.palette=palette==null?new PsychRGBPalette():palette.copy();
 public function apply(note:Dynamic):Void {note.shader=palette.shader;}
}
''',
    "NightmareVisionPaths.hx": r'''import flixel.graphics.frames.FlxAtlasFrames;
class NightmareVisionPaths {
 public var root:String; public var atlas:FlxAtlasFrames; public var hasJson:Bool=false;
 public var hudProfile:Dynamic={name:"split"};
 public var coreFiles:Map<String,Bool>=[];
 public var atlasRequests:Array<String>=[];
 public function new(root:String,atlas:FlxAtlasFrames) {this.root=root;this.atlas=atlas;}
 public function noteskin(name:String):String return root+"/noteskins/"+name+".json";
 public function scopeAssetPath(path:String):Null<String> return path;
 public function getPath(path:String,?library:String,?allowNullSafety:Bool=false):String return path;
 public function getCorePath(path:String):String return root+"/__core/"+path;
 public function exists(path:String):Bool return path.indexOf("/__core/")>=0?coreFiles.exists(path):hasJson;
 public function getSparrowAtlas(path:String):FlxAtlasFrames {atlasRequests.push(path);return atlas;}
}
''',
    "FNFAssets.hx": r'''class FNFAssets { public static var content:String=""; public static function getText(path:String):String return content; }
''',
    "CoolUtil.hx": r'''class CoolUtil { public static function parseJson(content:String):Dynamic return haxe.Json.parse(content); }
''',
}


MAIN = r'''import crowplexus.hscript.Parser;
import flixel.graphics.frames.FlxAtlasFrames;
import Strumline.StrumNote;

class Main {
 static function check(ok:Bool,message:String):Void if(!ok)throw message;
 static function frames():FlxAtlasFrames return new FlxAtlasFrames([
  "purple0000","purple hold piece0000","pruple end hold0000",
  "blue0000","blue hold piece0000","blue hold end0000",
  "green0000","green hold piece0000","green hold end0000",
  "red0000","red hold piece0000","red hold end0000",
  "arrowLEFT","left press","left confirm","arrowDOWN","down press","down confirm",
  "arrowUP","up press","up confirm","arrowRIGHT","right press","right confirm",
  "note splash purple","note splash blue","note splash green","note splash red"
 ]);
 static function main():Void {
  var firstPaths=new NightmareVisionPaths("skin-owner-a",frames());
  for(layout in 0...3){
   var owner=new NightmareVisionPaths("layout-owner"+layout,frames());
   for(d in 0...10)if(layout!=2||d<9)owner.coreFiles.set(owner.getCorePath("images/num"+d+".png"),true);
   if(layout==1)for(d in 0...10)owner.coreFiles.set(owner.getCorePath("images/UI/combo/num"+d+".png"),true);
   owner.hudProfile=NightmareVisionHUDProfile.detect(owner);
   var selected=new NightmareVisionNoteSkin(owner,"",4,0);
   check(selected.sustainSplashTexture==(layout==0?"sustainHold":"UI/notes/sustainHold"),
    "actual core layout detection, modern priority and partial-core default");
   owner.atlasRequests=[];
   check(selected.loadSustainSplashFrames()==owner.atlas&&owner.atlasRequests[0]==selected.sustainSplashTexture,
    "selected default must load through its own exact atlas path");
   owner.hasJson=true;FNFAssets.content='{"sustainSplashTexture":"custom/hold"}';
   var authored=new NightmareVisionNoteSkin(owner,"authored",4,0);
   check(authored.sustainSplashTexture=="custom/hold","explicit authored path overrides every layout");
  }
  FNFAssets.content="";
  var legacy=NightmareVisionNoteSkin.fromLegacyTexture(firstPaths,"notes/source-texture",4,7);
  check(legacy.noteTexture=="notes/source-texture" && legacy.name=="notes/source-texture" && legacy.ID==7 && legacy.paths==firstPaths,"legacy callback returns owner-local texture, not JSON skin name");
  var fallback=NightmareVisionNoteSkin.fromLegacyTexture(firstPaths,"",4,0);
  check(fallback.noteTexture=="NOTE_assets","legacy empty texture fallback");
  var skin=new NightmareVisionNoteSkin(firstPaths,"",4,9);
  skin.sustainSplashTexture="private-cover";
  firstPaths.atlasRequests=[];
  check(skin.loadSustainSplashFrames()==firstPaths.atlas && skin.loadSustainSplashFrames()==firstPaths.atlas
   && firstPaths.atlasRequests.join(",")=="private-cover,private-cover",
   "sustain setup atlas helper must use its owner paths and reload on every call");
  firstPaths.atlasRequests=[];
  skin.splashTexture="skin-tap";
  check(skin.loadNoteSplashFrames("explicit/tap")==firstPaths.atlas
   && skin.loadNoteSplashFrames("")==firstPaths.atlas
   && firstPaths.atlasRequests.join(",")=="explicit/tap,",
   "tap atlas helper must preserve explicit texture and blank paths through selected owner");
  var separate=new NightmareVisionNoteSkin(firstPaths,"second",4,9);
  check(skin.name=="" && skin.keys==4 && skin.ID==9,
   "native constructor must retain authored name, key count, and ID");
  check(skin.noteOffsets.length==4 && skin.noteOffsets[0]!=skin.noteOffsets[1]
   && skin.noteOffsets[0]!=separate.noteOffsets[0],
   "each skin must receive independent per-lane mutable offset points");
  check(skin.data.noteTexture=="UI/notes/NOTE_assets" && skin.noteScale==0.7
   && skin.receptorScale==0.7 && skin.receptorAlpha==1 && skin.splashAlpha==1,
   "missing JSON must load donor defaults without applying unused alpha JSON");

  var head=new Note(false);
  skin.noteScale=0.5;
  check(skin.applyNote(head,0) && head.scale.x==0.5 && head.baseScale.x==0.5
   && head.normalSize==0.5,"note renderer helper did not consume mutable noteScale");
  skin.noteScale=0.8;
  check(skin.applyNote(head,0) && head.scale.x==0.8 && head.baseScale.x==0.8,
   "note skin changes must set a stable scale instead of compounding");
  skin.colors[0].r=0xFF010203;
  check(skin.palette(0).r==0xFF010203 && separate.palette(0).r==0xFFC24B99,
   "runtime color mutation or per-skin palette isolation failed");
  var oldRGB=new NightmareVisionRGBGraphics(); oldRGB.alpha=0.35; oldRGB.flash=0.6;
  head.nightmareVisionRGB=oldRGB;
  check(skin.applyNote(head,0) && head.nightmareVisionRGB==oldRGB
   && oldRGB.alpha==0.35 && oldRGB.flash==0.6 && oldRGB.palette.r==0xFF010203,
   "note palette refresh must preserve the per-object RGB state");

  var receptor=new StrumNote();
  var receptorRGB=new NightmareVisionRGBGraphics(); receptorRGB.alpha=0.25; receptorRGB.flash=0.75;
  receptor.nightmareVisionRGB=receptorRGB;
  skin.receptorScale=0.6;
  check(skin.applyReceptor(receptor,0) && receptor.scale.x==0.6
   && receptor.baseScale.x==0.6 && receptor.nightmareVisionRGB==receptorRGB && receptorRGB.alpha==0.25
   && receptorRGB.flash==0.75 && receptorRGB.palette.r==0xFF010203 && receptor.useRGBShader,
   "receptor helper must consume mutable scale/palette, enable source RGB, and retain draw state");
  skin.inEngineColoring=false;
  check(skin.applyReceptor(receptor,0) && !receptor.useRGBShader && !receptorRGB.enabled,
   "receptor skin changes must disable both the source RGB flag and graphics view");
  skin.inEngineColoring=true;
  check(skin.applyReceptor(receptor,0) && receptor.useRGBShader && receptorRGB.enabled,
   "receptor skin changes must restore both the source RGB flag and graphics view");
  skin.receptorScale=0.9;
  check(skin.applyReceptor(receptor,0) && receptor.scale.x==0.9 && receptor.baseScale.x==0.9,
   "receptor scale changes must be direct and stable");
  var splash=new NoteSplash();
  check(skin.applySplash(splash,0) && splash.scale.x==1 && splash.alpha==0.42,
   "splash helper must keep source's unused alpha property inert");

  var splashRGB=splash.nightmareVisionRGB; splashRGB.alpha=0.23; splashRGB.flash=0.4;
  skin.splashScale=0.8;skin.inEngineColoring=false;
  check(skin.applySplash(splash,0)&&splash.baseScale.x==0.8&&splash.nightmareVisionRGB==splashRGB
   &&splashRGB.alpha==0.23&&splashRGB.flash==0.4&&!splashRGB.enabled&&splash.alpha==0.42,
   "splash reload must refresh baseline and retain RGB identity/alpha/coloring flags");
  skin.inEngineColoring=true;
  firstPaths.hasJson=true;
  FNFAssets.content="null";
  var parsedNull=skin.loadFromPath("null-data");
  check(parsedNull.noteTexture=="UI/notes/NOTE_assets",
   "loadFromPath JSON null must use the default empty object");
  var directError="";
  try NightmareVisionNoteSkin.resolveData(null) catch(error:Dynamic) directError=Std.string(error);
  check(directError.indexOf("resolveData requires an object")>=0,
   "direct static resolveData(null) must retain the source's invalid-input failure");

  var currentPaths=firstPaths;
  var interp=new NightmareVisionScriptInterp();
  NightmareVisionNoteSkinBindings.install(interp,"owner-a",
   function(owner:String):NightmareVisionPaths return owner=="owner-a"?currentPaths:null);
  var identity:Dynamic=interp.variables.get("NoteSkin");
  check(identity==interp.importBindings.get("funkin.data.NoteSkin"),
   "bare and qualified aliases must use the same runtime class identity");
  var parser=new Parser();
  interp.execute(parser.parseString(
   'bare = new NoteSkin("factory", 2, 31); qualified = new funkin.data.NoteSkin("qualified", 1, 32);'));
  var bare:NightmareVisionNoteSkin=cast interp.variables.get("bare");
  var qualified:NightmareVisionNoteSkin=cast interp.variables.get("qualified");
  check(bare.paths==firstPaths && bare.keys==2 && bare.ID==31
   && qualified.paths==firstPaths && qualified.keys==1 && qualified.ID==32
   && Std.isOfType(bare,NightmareVisionNoteSkin),
   "real Iris source constructor or Std.isOfType identity failed");
  var localType:Dynamic={};
  interp.bindConstructorFactory(localType,function(_args:Array<Dynamic>):Dynamic return {name:"local"},null);
  interp.variables.set("localType",localType);
  interp.execute(parser.parseString(
   '{ var NoteSkin = localType; local = new NoteSkin("shadow"); } afterLocal = new NoteSkin("again", 0, 33);'));
  check(interp.variables.get("local").name=="local"
   && Std.isOfType(interp.variables.get("afterLocal"),NightmareVisionNoteSkin),
   "script-local class shadowing must survive owner factory interception");
  var replacementPaths=new NightmareVisionPaths("skin-owner-replacement",frames());
  currentPaths=replacementPaths;
  interp.execute(parser.parseString('replacement = new NoteSkin("replacement", 0, 34);'));
  check((cast interp.variables.get("replacement"):NightmareVisionNoteSkin).paths==replacementPaths,
   "owner paths must be re-resolved when the factory constructs a later skin");
  var constructorError="";
  try interp.execute(parser.parseString('negative = new NoteSkin("default");'))
  catch(error:Dynamic) constructorError=Std.string(error);
  check(constructorError.indexOf("Vector size must be >= 0")>=0,
   "source omitted key count must preserve the donor's negative-vector failure");
  interp.release();
  trace("NV_NOTE_SKIN_RUNTIME_OK");
 }
}'''


class NightmareVisionNoteSkinRuntimeTest(unittest.TestCase):
    def test_real_adapter_mutable_rendering_and_owner_factory(self):
        if not (ROOT / ".tools/haxe/haxe").is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            for name, content in STUBS.items():
                path = work / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, newline="\n")
            (work / "Main.hx").write_text(MAIN, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND,
                 "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript-iris/1,1,3"),
                 "-cp", str(work),
                 "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=90,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("NV_NOTE_SKIN_RUNTIME_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
