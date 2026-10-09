"""Historical note colors and shared shader selection execute against production code."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND
from test_nv_multifield_routes import method
ROOT=Path(__file__).resolve().parents[2]
class LegacyNoteColorsTest(unittest.TestCase):
 def test_hsv_state_lifecycle_and_rgb_non_regression(self):
  files={
   'flixel/system/FlxAssets.hx':'''package flixel.system;
class FlxAssets {} class Uniform<T>{public var value:Array<T>=[];public function new(){}}
class FlxShader {public var uTime=new Uniform<Float>();public var daAlpha=new Uniform<Float>();public var flash=new Uniform<Float>();public var awesomeOutline=new Uniform<Bool>();public var hue=new Uniform<Float>();public var saturation=new Uniform<Float>();public var lightness=new Uniform<Float>();public var mult=new Uniform<Float>();public var u_alpha=new Uniform<Float>();public var u_flash=new Uniform<Float>();public function new(){}}''',
   'flixel/FlxSprite.hx':'package flixel; class FlxSprite {public var shader:Dynamic;public function new(){}}',
   'PsychRGBPalette.hx':'''class PsychRGBPalette {public var r:Int=1;public var g:Int=2;public var b:Int=3;public var mult:Float=1;public var shader=new flixel.system.FlxAssets.FlxShader();public function new(){}public function copy():PsychRGBPalette return new PsychRGBPalette();public function copyValues(p:PsychRGBPalette):Void{r=p.r;g=p.g;b=p.b;}}''',
   'NightmareVisionScriptGroup.hx':'class NightmareVisionScriptGroup {public static var CONTINUE_FUNC=0;public static var STOP_FUNC=1;}',
   'NightmareVisionGameplayScripts.hx':'''class NightmareVisionGameplayScripts {public var calls=0;public function new(){}public function loadNoteTypes():Void{}public function callNoteType(type:String,callback:String,args:Array<Dynamic>,?receiver:Dynamic):Dynamic {if(callback=='setupNote'){calls++;var n:Note=cast args[0];if(type=='custom'){n.colorSwap.hue=0.75;n.noteSplashTexture='custom-splash';}}return 0;}}''',
   'Note.hx':'''class Note extends flixel.FlxSprite {
 public var noteSplashTexture='';public var noteType='';public var noteData=0;public var quant=8;public var isQuant=false;
 public var noteSplashHue:Float=0;public var noteSplashSat:Float=0;public var noteSplashBrt:Float=0;
 public var state:NightmareVisionLegacyNoteColors;public var colorSwap(get,never):NightmareVisionLegacyColorSwap;
 public var nightmareVisionRGB:NightmareVisionRGBGraphics;public var reloaded='';
 function get_colorSwap():NightmareVisionLegacyColorSwap return state.swap;
 public function reloadNote(prefix:String):Void reloaded=prefix;
 public function new(prefs:Dynamic){super();state=new NightmareVisionLegacyNoteColors(prefs);nightmareVisionRGB=new NightmareVisionRGBGraphics();nightmareVisionRGB.legacyHSV=state.swap;}}''',
   'Receptor.hx':'''class Receptor extends flixel.FlxSprite {
 public var ID=0;public var nightmareVisionQuantPrefs:Dynamic;public var nightmareVisionRGB=new NightmareVisionRGBGraphics();
 public var colorSwap:NightmareVisionLegacyColorSwap;public var animation:Dynamic={curAnim:{name:'confirm'}};
 public var nightmareVisionSource=true;public var useRGBShader=true;public var lastNote:Note;public var isQuant=false;public var nightmareVisionPalette:PsychRGBPalette;
 function getNightmareVisionRGB():NightmareVisionRGBGraphics return nightmareVisionRGB;
 public function new(){super();colorSwap=new NightmareVisionLegacyColorSwap();nightmareVisionRGB.legacyHSV=colorSwap;}
 __HANDLE__
}'''.replace('__HANDLE__',method((ROOT/'source/Strumline.hx').read_text(),'public function handleColors(')),
   'Main.hx':'''class Main {
 static function check(v:Bool,s:String):Void{if(!v)throw s;}
 static function near(a:Float,b:Float):Bool return Math.abs(a-b)<0.000001;
 static function main(){
  var prefs:Dynamic={noteSkin:'Vanilla',arrowHSV:[[90,20,-30],[0,0,0],[0,0,0],[0,0,0]],quantHSV:[[0,0,0],[180,-20,30]],quantStepmania:[[0,0,0],[-90,40,-10]]};
  var n=new Note(prefs);var scripts=new NightmareVisionGameplayScripts();var runtime=new NightmareVisionNoteTypeRuntime(scripts);
  runtime.prepareLegacyColors=function(v:Dynamic,force:Bool)return (cast v:Note).state.prepare(cast v,force);
  runtime.finishLegacyColors=function(v:Dynamic)(cast v:Note).state.finish(cast v);
  n.noteType='custom';runtime.setupNote(n);
  check(scripts.calls==1&&n.colorSwap.hue==0.75&&n.noteSplashHue==0.75,'script follows defaults; splash captures result');
  check(n.noteSplashTexture=='custom-splash','script-owned splash texture');
  n.colorSwap.hue=0.6;runtime.setupNote(n);check(scripts.calls==1&&n.colorSwap.hue==0.6,'spawn preserves source-assigned note');
  runtime.setupNote(n,true);check(scripts.calls==1&&n.colorSwap.hue==0.25&&n.noteSplashHue==0.25,'same setter resets HSV without script');
  n.noteType='Hurt Note';runtime.setupNote(n,true);check(n.reloaded=='HURT'&&n.colorSwap.hue==0&&n.colorSwap.saturation==0,'hurt reload and identity HSV');
  check(scripts.calls==1&&n.noteSplashTexture=='HURTnoteSplashes','built-in type bypasses custom setup');
  runtime.setupNote(n,true);check(n.colorSwap.hue==0.25&&n.noteSplashTexture=='noteSplashes','same hurt setter resets to source defaults');
  n.noteType='';n.isQuant=true;prefs.noteSkin='Quants';runtime.setupNote(n,true);check(n.colorSwap.hue==0.5&&near(n.colorSwap.saturation,-0.2),'quant HSV units');
  prefs.noteSkin='QuantStep';runtime.setupNote(n,true);check(n.colorSwap.hue==-0.25&&near(n.colorSwap.brightness,-0.1),'stepmania units');
  n.isQuant=false;runtime.setupNote(n,true);check(n.colorSwap.hue==0.25,'missing variant uses lane HSV');
  check(NightmareVisionLegacyNoteColors.selectTexture('folder/note',prefs,true,function(s)return s=='QUANTfolder/note')=='QUANTfolder/note','prefix whole path');
  check(NightmareVisionLegacyNoteColors.selectTexture('note',prefs,true,function(s)return false)=='note','missing variant fallback');
  check(NightmareVisionLegacyNoteColors.selectTexture('note',prefs,false,function(s)return true)=='note','canQuant gate');
  n.nightmareVisionRGB.alpha=0.4;n.nightmareVisionRGB.flash=0.2;n.nightmareVisionRGB.enabled=false;n.nightmareVisionRGB.apply(n);
  check(n.shader==n.colorSwap.shader&&n.colorSwap.daAlpha==0.4&&n.colorSwap.flash==0.2&&n.colorSwap.hue==0.25,'draw preserves HSV');
  var receptor=new Receptor();receptor.nightmareVisionQuantPrefs=prefs;n.colorSwap.hue=0.8;receptor.handleColors('confirm',n);
  check(receptor.colorSwap.hue==0.8,'explicit note colors');receptor.lastNote=n;receptor.handleColors('pressed');check(receptor.colorSwap.hue==0.25,'no historical lastNote fallback');
  receptor.animation.curAnim.name='static';receptor.handleColors('static');check(receptor.colorSwap.hue==0,'idle HSV');
  var other=new Note(prefs);check(other.colorSwap!=n.colorSwap&&other.colorSwap.hue==0,'per-note isolation');
  var sprite=new flixel.FlxSprite();var rgb=new NightmareVisionRGBGraphics();rgb.alpha=0.3;rgb.apply(sprite);check(sprite.shader==rgb.palette.shader&&rgb.palette.shader.u_alpha.value[0]==0.3,'modern RGB');
  rgb.legacyHSL=new NightmareVisionHSLColorSwap();rgb.legacyHSL.hue=0.25;rgb.legacyHSL.lightness=0.4;rgb.apply(sprite);check(sprite.shader==rgb.legacyHSL.shader&&rgb.legacyHSL.shader.lightness.value[0]==0.4,'splash HSL');
 }
}'''}
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as d:
   work=Path(d)
   for name,content in files.items():
    p=work/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
   r=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'--main','Main','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=45)
   self.assertEqual(r.returncode,0,r.stdout+r.stderr)
if __name__=='__main__':unittest.main()
