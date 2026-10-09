"""Execute historical coordinate formulas beside pinned source methods."""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND
from test_nv_multifield_routes import method
ROOT=Path(__file__).resolve().parents[2]
REV='7f96eb3b5a60352413229bf134bd348b79ad5fe6'
class LegacyGeometryTest(unittest.TestCase):
 def test_donor_coordinates_reverse_and_native_adapter_boundaries(self):
  donor=ROOT.parent/'fnf_sources/NightmareVision'
  if not donor.is_dir():self.skipTest('pinned historical donor repository is unavailable')
  def read(path):return subprocess.check_output(['git','show',REV+':'+path],cwd=donor,text=True)
  base=method(read('source/modchart/ModManager.hx'),'public function getBaseX(')
  reverse=method(read('source/modchart/modifiers/ReverseModifier.hx'),'override function getPos(').replace('override function','public function',1)
  fixture=r'''
import nightmarevision.modchart.NightmareVisionModchartContext;
import nightmarevision.modchart.NightmareVisionModchartObject;
import nightmarevision.modchart.NightmareVisionModchartTransform;
import nightmarevision.modchart.NightmareVisionModchartRenderer;
import nightmarevision.modchart.NightmareVisionModifierRegistry;
import nightmarevision.modchart.NightmareVisionModchartVector as Vector3;
using StringTools;
class FlxG {public static var width:Float=1280;public static var height:Float=720;}
class FlxSprite {public function new(){}}
class Note extends FlxSprite {public static var swagWidth:Float=112;public var isSustainNote=false;public var multSpeed=1.;public var animation:{curAnim:{name:String}}={curAnim:{name:'Scroll'}};}
class PlayState {public static var SONG:Dynamic={bpm:120.};public static var instance:Dynamic={songSpeed:1.};}
class CoolUtil {public static function scale(v:Float,a:Float,b:Float,c:Float,d:Float):Float return (v-a)*(d-c)/(b-a)+c;}
class Donor {public function new(){} __BASE__ }
class Reverse {
 public var reverse=0.;public var centered=0.;public function new(){}
 function getReverseValue(d:Int,p:Int):Float return reverse;
 function getSubmodValue(n:String,p:Int):Float return centered;
 function lerp(a:Float,b:Float,c:Float):Float return a+(b-a)*c;
 __REVERSE__
}
class Main {
 static function near(a:Float,b:Float,m:String):Void if(!Math.isFinite(a)||Math.abs(a-b)>.00001)throw m+': '+a+' != '+b;
 static function check(v:Bool,m:String):Void if(!v)throw m;
 static function fake():Dynamic return {x:14.,y:27.,width:90.,height:80.,frameWidth:128.,frameHeight:114.,scale:{x:.7,y:.7},baseScale:{x:.7,y:.7},offset:{x:0.,y:0.},origin:{x:0.,y:0.},active:true,noteData:2,strumTime:500.,multSpeed:1.,isSustainNote:false,offsetX:11.,offsetY:17.,typeOffsetX:23.,typeOffsetY:29.,animation:{curAnim:{name:'Scroll'}},centerOrigin:function(){},centerOffsets:function(){},updateHitbox:function(){}};
 static function main(){
  var donor=new Donor();var reference=new Reverse();
  for(width in [960.,1280.,1920.])for(keys in [4,6])for(spacing in [80.,112.,160.]){
   FlxG.width=width;Note.swagWidth=spacing;
   var ctx=new NightmareVisionModchartContext(width,720,keys,spacing,0,0,1,500,false,false,true);
   for(player in 0...3)for(dir in 0...keys)near(NightmareVisionModchartTransform.baseX(ctx,dir,player),donor.getBaseX(dir,player),'pinned getBaseX');
  }
  FlxG.width=1280;Note.swagWidth=112;
  var reg=new NightmareVisionModifierRegistry(4), transform=new NightmareVisionModchartTransform(reg);
  var note=new Note();var obj=new NightmareVisionModchartObject();
  for(down in [false,true])for(percent in [0.,.25,1.])for(center in [0.,.7])for(bpm in [90.,180.])for(speed in [.8,2.])for(hold in [false,true])for(end in [false,true]){
   var ctx=new NightmareVisionModchartContext(1280,720,4,112,0,0,speed,500,down,false,true,bpm);
   reg.setValue('reverse',percent,0);reg.setSubmodValue('reverse','centered',center,0);
   reference.reverse=down?1-percent:percent;reference.centered=center;
   PlayState.SONG.bpm=bpm;PlayState.instance.songSpeed=speed;
   note.isSustainNote=hold;note.multSpeed=1.3;note.animation.curAnim.name=end?'holdend':'hold';
   obj.isSustain=hold;obj.isSustainEnd=end;obj.multSpeed=1.3;
   var expected=reference.getPos(0,157,0,0,new Vector3(),0,0,note);
   near(transform.getPosition(ctx,obj,157,0,0).y,expected.y,'pinned reverse/tail correction');
  }
  reg=new NightmareVisionModifierRegistry(4);transform=new NightmareVisionModchartTransform(reg);
  var legacy=new NightmareVisionModchartContext(1280,720,4,112,0,0,1,500,false,false,true);
  var modern=new NightmareVisionModchartContext(1280,720,4,112);
  var renderer=new NightmareVisionModchartRenderer(transform);
  var sprite=fake();var visual=renderer.updateNote(legacy,sprite,0,100,0,100,0,0);
  near(sprite.x,donor.getBaseX(2,0)+11,'legacy top-left plus source offset');near(sprite.y,167,'legacy Y plus source offset');
  near(visual.spriteOffsetX,23,'draw offset separate from position');near(visual.spriteOffsetY,29,'draw Y separate');
  renderer.updateNote(legacy,sprite,0,100,0,100,0,0);near(sprite.x,donor.getBaseX(2,0)+11,'offset does not accumulate');
  sprite.x=31;sprite.y=47;renderer.applyObject(legacy,sprite,'note',0,0,new Vector3(900,600));near(sprite.x,31,'source updateObject preserves x');near(sprite.y,47,'source updateObject preserves y');
  var receptor=fake();visual=renderer.updateReceptor(legacy,receptor,0);near(receptor.x,donor.getBaseX(2,0),'receptor top-left');near(receptor.y,50,'receptor top Y');
  sprite=fake();visual=renderer.updateNote(modern,sprite,0,100,0,100,0,0);near(sprite.x,NightmareVisionModchartTransform.baseX(modern,2,0)-45,'modern centered X');near(sprite.y,166,'modern centered Y');near(visual.spriteOffsetX,11,'modern offset remains draw offset');
  var liveX=7.;var liveY=9.;
  renderer.positionOffsets=function(kind,dir,hold)return new Vector3(kind=='receptor'?3:liveX,hold?liveY+20:liveY);
  sprite=fake();renderer.updateNote(legacy,sprite,0,100,0,100,0,0);near(sprite.x,donor.getBaseX(2,0)+18,'live note position offset');near(sprite.y,176,'live note Y');
  liveX=13;renderer.updateNote(legacy,sprite,0,100,0,100,0,0);near(sprite.x,donor.getBaseX(2,0)+24,'live replacement without accumulation');
  sprite.isSustainNote=true;renderer.updateNote(legacy,sprite,0,100,0,100,0,0);near(sprite.x,donor.getBaseX(2,0)+24,'hold note offset');
  receptor=fake();renderer.updateReceptor(legacy,receptor,0);near(receptor.x,donor.getBaseX(2,0)+3,'independent strum offsets');near(receptor.y,59,'strum Y');
  sprite=fake();renderer.updateNote(modern,sprite,0,100,0,100,0,0);near(sprite.x,NightmareVisionModchartTransform.baseX(modern,2,0)-45,'modern ignores legacy arrays');
  sprite.x=31;sprite.y=47;renderer.applyObject(legacy,sprite,'note',0,0,new Vector3(900,600));near(sprite.x,31,'public updateObject ignores gameplay offsets');
  renderer.destroy();check(renderer.positionOffsets==null,'release offset reader');
  near(NightmareVisionPlayfieldLayout.legacyEntranceX(960,0,112,false),734,'initial source X');
  near(NightmareVisionPlayfieldLayout.legacyEntranceX(640,0,112,true),78,'middle left split');
  near(NightmareVisionPlayfieldLayout.legacyEntranceX(640,3,112,true),1086,'middle right split');
 }
}
'''.replace('__BASE__',base).replace('__REVERSE__',reverse)
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as d:
   Path(d,'Main.hx').write_text(fixture)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/flixel/6,1,2'),'-cp',d,'--main','Main','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=45)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
