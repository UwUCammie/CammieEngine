"""Pinned historical pixel sheet/reload contracts over the shared Psych loader."""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND
from tools.haxe_flixel_math_stubs import write_flixel_point_stub
from test_nv_multifield_routes import method
ROOT=Path(__file__).resolve().parents[2]
REV='7f96eb3b5a60352413229bf134bd348b79ad5fe6'
class LegacyPixelSkinTest(unittest.TestCase):
 def test_pinned_note_and_receptor_reload(self):
  donor=ROOT.parent/'fnf_sources/NightmareVision'
  if not donor.is_dir():self.skipTest('pinned historical source unavailable')
  def source(path):return subprocess.check_output(['git','show',REV+':'+path],cwd=donor,text=True)
  note=source('source/gameObjects/Note.hx')
  pixel=method(note[note.index('public function reloadNote'):], 'if(PlayState.isPixelStage)')
  anim=method(note,'function _loadPixelNoteAnims()').replace('function _loadPixelNoteAnims()','public function loadPixelNoteAnims()')
  strum=source('source/gameObjects/StrumNote.hx')
  receptor=method(strum,'if(PlayState.isPixelStage)')
  files={
   'Note.hx':r"""import flixel.math.FlxPoint;
class Note extends FakeSprite {
 public var noteData=0;public var isSustainNote=false;public var isQuant=false;public var canQuant=true;
 public var originalHeightForCalcs=6.;public var offsetX=0.;public var lastNoteOffsetXForPixelAutoAdjusting=0.;
 public var nightmareVisionSustainInitialized=false;public var nightmareVisionSustainInitialWidth=0.;
 public var baseScaleX=1.;public var baseScaleY=1.;public var baseScale=new FlxPoint();public var defScale(get,never):FlxPoint;function get_defScale():FlxPoint return baseScale;
 public var normalSize=1.;public var nightmareVisionRGB:NightmareVisionRGBGraphics;
 public function resetPsychVisualOffset():Void {}
 public function new(){super();}
}
""",
   'FakeSprite.hx':r"""import flixel.math.FlxPoint;
class FakeSprite {
 public var scale=new FlxPoint(1,1);public var width=100.;public var height=100.;public var frameWidth=100.;public var frameHeight=100.;public var antialiasing=true;public var animation=new Anim();
 public function new(){}
 public function loadGraphic(g:Dynamic,a:Bool=false,w:Int=0,h:Int=0):Void {frameWidth=a?w:g.width;frameHeight=a?h:g.height;width=frameWidth;height=frameHeight;}
 public function setGraphicSize(w:Int):Void {scale.set(w/width,w/width);}
 public function updateHitbox():Void {width=frameWidth*Math.abs(scale.x);height=frameHeight*Math.abs(scale.y);}
 public function playAnim(n:String,f:Bool=false):Void animation.play(n,f);
}
class Anim {
 public var rows:Map<String,Dynamic>=new Map();public var curAnim:Dynamic;
 public function new(){}
 public function add(n:String,ids:Array<Int>,fps:Float=30,loop:Bool=true):Void rows.set(n,{ids:ids,fps:fps,loop:loop});
 public function exists(n:String):Bool return rows.exists(n);
 public function play(n:String,f:Bool=false):Void curAnim={name:n};
}
""",
   'Strumline.hx':r"""class Strumline {}
class StrumNote extends Note {
 public var ID=0;public var isPixel=false;public var nightmareVisionOffsets:Map<String,Array<Float>>;
 public var useRGBShader=true;public var nightmareVisionPalette:Dynamic;
 public function new(){super();}
}
""",
   'NightmareVisionNoteSkin.hx':r"""class NightmareVisionNoteSkin {public var inEngineColoring=true;public function new(){}public function palette(l:Int):Dynamic return [l];}""",
   'NightmareVisionRGBGraphics.hx':r"""class NightmareVisionRGBGraphics {public var enabled=true;public function new(?p:Dynamic){}public function apply(n:Dynamic):Void {}}""",
   'Main.hx':r"""import flixel.math.FlxPoint;
class PlayState {public static var isPixelStage=true;public static var daPixelZoom=6.;}
class ClientPrefs {public static var noteSkin='Vanilla';}
class Assets {public static function exists(p:String):Bool return false;}
class FileSystem {public static function exists(p:String):Bool return false;}
class Paths {
 public static function image(p:String):Dynamic return Main.graphic;
 public static function getPath(p:String,t:String):String return p;
 public static function modsImages(p:String):String return p;
}
class Reference extends Note {
 static inline var IMAGE='image';static inline var PURP_NOTE=0;static inline var BLUE_NOTE=1;static inline var GREEN_NOTE=2;static inline var RED_NOTE=3;
 public function new(){super();}
 __ANIM__
 public function reload():Void {
  var blahblah='test';var lastScaleY=scale.y;__PIXEL__
  if(isSustainNote)scale.y=lastScaleY;
  updateHitbox();baseScaleX=scale.x;baseScaleY=scale.y;
 }
}
class ReferenceStrum extends Strumline.StrumNote {
 static inline var IMAGE='image';public var texture='test';
 public function new(){super();}
 public function reload():Void {var br=texture;__RECEPTOR__ updateHitbox();}
}
class Main {
 public static var graphic:Dynamic;
 static function near(a:Float,b:Float,m:String):Void if(Math.abs(a-b)>.000001)throw m+': '+a+' != '+b;
 static function main(){
  for(sustain in [false,true])for(lane in 0...4)for(width in [28,40,45])for(zoom in [3.,6.]){
   graphic={width:width,height:sustain?12:100};PlayState.daPixelZoom=zoom;
   var expected=new Reference(),actual=new Note();expected.isSustainNote=actual.isSustainNote=sustain;
   expected.scale.y=actual.scale.y=2.5;expected.offsetX=actual.offsetX=11;
   for(reload in 0...2){
    expected.reload();if(!NightmareVisionLegacyPixelSkin.applyNote(actual,graphic,lane,zoom))throw 'pixel load failed';
    near(actual.frameWidth,expected.frameWidth,'cell width');near(actual.frameHeight,expected.frameHeight,'cell height');
    near(actual.scale.x,expected.scale.x,'pixel zoom');near(actual.scale.y,expected.scale.y,'hold scale preserved');
    near(actual.baseScaleY,expected.baseScaleY,'raw scale');near(actual.width,expected.width,'hitbox width');
    near(actual.offsetX,expected.offsetX,'repeated pixel offset replacement');near(actual.originalHeightForCalcs,expected.originalHeightForCalcs,'unrounded tail height');
    for(name in expected.animation.rows.keys()){
     var a=actual.animation.rows.get(name),b=expected.animation.rows.get(name);
     if(a==null||a.ids.join(',')!=b.ids.join(',')||a.fps!=b.fps||a.loop!=b.loop)throw 'source note frame mapping '+name;
    }
    actual.nightmareVisionSustainInitialized=true;
   }
  }
  for(lane in 0...4){
   graphic={width:40,height:100};PlayState.daPixelZoom=6;
   var expected=new ReferenceStrum(),actual=new Strumline.StrumNote();expected.noteData=lane;actual.ID=lane;
   expected.reload();NightmareVisionLegacyPixelSkin.applyReceptor(actual,new NightmareVisionNoteSkin(),graphic,lane,6);
   near(actual.scale.x,expected.scale.x,'receptor scale');if(actual.antialiasing||!actual.isPixel)throw 'pixel render flags';
   for(name in expected.animation.rows.keys()){
    var a=actual.animation.rows.get(name),b=expected.animation.rows.get(name);
    if(a==null||a.ids.join(',')!=b.ids.join(',')||a.fps!=b.fps||a.loop!=b.loop)throw 'source receptor frame mapping '+name;
   }
  }
  var untouched=new Note();if(NightmareVisionLegacyPixelSkin.applyNote(untouched,{width:2,height:1},0,6))throw 'invalid sheet admitted';
  near(untouched.width,100,'invalid sheet changed live note');
 }
}
""".replace('__ANIM__',anim).replace('__PIXEL__',pixel).replace('__RECEPTOR__',receptor)
  }
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=Path(folder);write_flixel_point_stub(work)
   for name,text in files.items():(work/name).write_text(text)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',folder,'--run','Main'],capture_output=True,text=True,timeout=40)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
