"""Historical splash constructor/setup and noteskin selection against pinned source."""
from pathlib import Path
import re,subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from nv_splash_fixture_support import splash_fixture_files
from test_nv_multifield_routes import method
ROOT=Path(__file__).resolve().parents[2]
REV='7f96eb3b5a60352413229bf134bd348b79ad5fe6'
class LegacySplashTest(unittest.TestCase):
 def test_complete_donor_sprite_and_scripted_selection(self):
  donor=ROOT.parent/'fnf_sources/NightmareVision'
  if not donor.is_dir():self.skipTest('pinned source unavailable')
  source=subprocess.check_output(['git','show',REV+':source/gameObjects/NoteSplash.hx'],cwd=donor,text=True)
  source=re.sub(r'^(package|import)[^\n]*\n','',source,flags=re.M)
  source=source.replace('class NoteSplash extends FlxSprite','class DonorLegacySplash extends FlxSprite').replace('override function update','override public function update').replace('private var textureLoaded','public var textureLoaded')
  files=splash_fixture_files('', '')
  files.pop('DonorSplash.hx');files.pop('Main.hx')
  files['flixel/math/FlxPoint.hx']+='class FlxCallbackPoint extends FlxPoint {public function new(a:FlxPoint->Void,?b:FlxPoint->Void,?c:FlxPoint->Void){super();}}'
  files['DonorLegacySplash.hx']='import flixel.FlxSprite;import flixel.FlxG;typedef HSLColorSwap=NightmareVisionHSLColorSwap;typedef PlayField=NightmareVisionPlayFieldView;\n'+source
  files['NightmareVisionPlayFieldView.hx']=files['NightmareVisionPlayFieldView.hx'].replace('public var player=1;','public var player=1;public var trackNoteSplashes=true;')
  files['NightmareVisionNoteSkin.hx']=files['NightmareVisionNoteSkin.hx'].replace('public var sustainSplashTexture=', 'public var keys=4;public var splashTexture="modern";public var splashScale=1.5;public var splashOffsets:Array<flixel.math.FlxPoint>=[];public var splashAnims:Array<Dynamic>=[];public var sustainSplashTexture=').replace('public function loadSustainSplashFrames()', 'public static function resolveData(d:Dynamic){d.noteSplashAnimations=[];}public function loadNoteSplashFrames(t:String):Dynamic return Paths.getAtlasFrames(t);public function loadSustainSplashFrames()')
  files['Paths.hx']=files['Paths.hx'].replace('public static var loads:', 'public static function getSparrowAtlas(t:String):Dynamic return getAtlasFrames(t);public static var loads:')
  files['ClientPrefs.hx']='class ClientPrefs {public static var globalAntialiasing=false;}'
  files['PlayState.hx']='class PlayState {public static var SONG:Dynamic={splashSkin:"authored"};}'
  files['FakeAnimation.hx']=files['FakeAnimation.hx'].replace('curAnim={name:n}', 'curAnim={name:n,finished:false}').replace('public var pending:String;', 'public var pending:String;public var markFinished=false;')
  files['flixel/FlxSprite.hx']=files['flixel/FlxSprite.hx'].replace('public function update(e:Float){','public function update(e:Float){if(animation.markFinished){animation.markFinished=false;animation.curAnim.finished=true;}')
  files['NightmareVisionRGBGraphics.hx']=files['NightmareVisionRGBGraphics.hx'].replace('s.shader=this;','s.shader=legacyHSL==null?this:legacyHSL.shader;')
  play=subprocess.check_output(['git','show',REV+':source/meta/states/PlayState.hx'],cwd=donor,text=True)
  selection=play[play.index("\t\tvar quant:Bool =",play.index('public function spawnNoteSplash(')):play.index('\n\t\tif (lazerSplash)',play.index('public function spawnNoteSplash('))]
  selection=re.sub(r'^.*var lazerSplash:Bool.*\n','',selection,flags=re.M)
  files['SourceSelection.hx']='import flixel.math.FlxPoint;class SourceSelection {public var SONG:Dynamic={keys:7};public var ClientPrefs:Dynamic;public var noteskinScript:Dynamic;public function new(p:Dynamic,s:NightmareVisionScriptModule){ClientPrefs=p;noteskinScript={call:function(n:String,a:Array<Dynamic>):Dynamic return s==null?null:s.callValue(n,a)};}public function run(data:Int,note:Note):Dynamic {'+selection+'return {texture:skin,offsets:offsets,hue:hue,saturation:sat,brightness:brt};}}'
  files['Main.hx']=r"""class Main {
 static function check(v:Bool,m:String):Void if(!v)throw m;
 static function snap(s:Dynamic):String {
  var a:Dynamic=s.animation.curAnim;
  var colors:NightmareVisionHSLColorSwap=s.colorSwap;
  var values:Array<Dynamic>=[s.x,s.y,s.scale.x,s.scale.y,s.alpha,s.antialiasing,s.visible,s.alive,s.offset.x,s.offset.y,s.textureLoaded,a==null?'':a.name,a==null?0:a.frameRate,colors.hue,colors.saturation,colors.lightness,s.shader==colors.shader,s.kills,Paths.loads.join(',')];return values.join('|');
 }
 static function run(host:Bool,index:Int):String {
  Paths.loads=[];PlayState.SONG.splashSkin=index==1?'':index==2?null:'authored';
  var s:Dynamic=host?new NightmareVisionLegacyNoteSplash(9,13,1,{skinForID:NoteUtil.getSkinFromID,noteSplashType:function()return 'Both',legacySplashTexture:function()return PlayState.SONG.splashSkin,legacyAntialiasing:function()return ClientPrefs.globalAntialiasing}):new DonorLegacySplash(9,13,1);
  var states=[snap(s)];var field=new NightmareVisionPlayFieldView();field.scale=2;field.members[1].swagWidth=173;
  s.scale.set(3,4);s.visible=false;s.alpha=.1;
  s.setupNoteSplash(200,300,1,'same',.25,-.2,.4,field);states.push(snap(s));
  s.setupNoteSplash(200,300,1,'same',0.,0.,0.,field);states.push(snap(s));
  check(Paths.loads.length==4,'source reloads same texture on each setup');
  field.scale=.5;s.setupNoteSplash(10,20,0,null,0.,0.,0.,null);states.push(snap(s));
  s.animation.markFinished=true;s.update(.1);states.push(snap(s));s.update(.1);states.push(snap(s));
  s.loadAnims('manual');states.push(snap(s));
  s.revive();s.animation.curAnim=null;s.update(.1);states.push(snap(s));
  for(lane in 0...7) {s.setupNoteSplash(50,70,lane,'all',.1,.2,.3,field);states.push(snap(s));}
  s.destroy();return states.join('\n');
 }
 static function main(){
  for(i in 0...3){var expected=run(false,i),actual=run(true,i);check(actual==expected,'sprite source comparison '+i+'\n'+actual+'\nEXPECTED\n'+expected);}
  var prefs:Dynamic={noteSkin:'Quants',arrowHSV:[[90.,20.,-30.],[0.,0.,0.],[0.,0.,0.],[0.,0.,0.]]};
  var events:Array<String>=[];var module=NightmareVisionScriptModule.fromSource('skin',"function noteSplash(o){record('splash');o[0].set(11,13);return 'custom';}function quants(){record('quants');return true;}",null,null,function(i)i.variables.set('record',function(s:String)events.push(s)),function(n,p,e)throw e);
  for(mode in ['Vanilla','Quants','QuantStep'])for(withNote in [false,true]) {
   prefs.noteSkin=mode;var note=withNote?new Note():null;if(note!=null){note.noteSplashHue=.7;note.noteSplashSat=.8;note.noteSplashBrt=.9;}
   events=[];var expected=new SourceSelection(prefs,module).run(0,note);check(events.join(',')=='splash,quants','donor callback order');
   events=[];var actual=NightmareVisionLegacyNoteSkin.splash(module,7,prefs,0,note);check(events.join(',')=='splash,quants','host callback order');
   check(actual.texture==expected.texture&&actual.hue==expected.hue&&actual.saturation==expected.saturation&&actual.brightness==expected.brightness,'selection and source colors');
   check(actual.offsets.length==7&&actual.offsets[0].x==11&&actual.offsets[0].y==13&&actual.offsets!=expected.offsets,'fresh source offsets');
  }
  var absent=NightmareVisionLegacyNoteSkin.splash(null,4,prefs,0,null);check(absent.texture=='noteSplashes','no scripted quant consent');module.destroy();
 }
}
"""
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as d:
   work=FixturePath(d)
   for name,content in files.items():
    path=work/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content)
   (work/'flixel/util').mkdir(parents=True,exist_ok=True)
   (work/'flixel/util/FlxSignal.hx').write_text((ROOT/'.haxelib/flixel/6,1,2/flixel/util/FlxSignal.hx').read_text())
   (work/'flixel/util/FlxDestroyUtil.hx').write_text('package flixel.util;interface IFlxDestroyable{public function destroy():Void;}class FlxDestroyUtil{public static function destroyArray<T:IFlxDestroyable>(a:Array<T>):Array<T>{if(a!=null)for(v in a)if(v!=null)v.destroy();return null;}}')
   r=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',str(work),'--main','Main','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=45)
   self.assertEqual(r.returncode,0,r.stdout+r.stderr)
if __name__=='__main__':unittest.main()
