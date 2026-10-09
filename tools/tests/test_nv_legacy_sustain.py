"""Pinned historical sustain construction, modifier order, and clipping contracts."""
from pathlib import Path
import re, subprocess, unittest
import test_nv_custom_modifier_registration as support
from test_nv_multifield_routes import method
ROOT=Path(__file__).resolve().parents[2]
REV='7f96eb3b5a60352413229bf134bd348b79ad5fe6'
class LegacySustainTest(unittest.TestCase):
 run_haxe=support.CustomModifierTest.run_haxe
 def donor(self,path):
  root=ROOT.parent/'fnf_sources/NightmareVision'
  if not root.is_dir():self.skipTest('pinned historical donor unavailable')
  return subprocess.check_output(['git','show',REV+':'+path],cwd=root,text=True)
 def test_pinned_construction_and_segment_clock(self):
  source=self.donor('source/gameObjects/Note.hx')
  block=method(source,'if (isSustainNote && prevNote != null)')
  block=block.replace('if (isSustainNote && prevNote != null)','public function donorFinish()',1)
  fixture=r"""
import flixel.math.FlxPoint;
using StringTools;
class Conductor {public static var stepCrotchet:Float=125;}
class PlayState {public static var instance:Dynamic={songSpeed:1.};public static var isPixelStage=false;public static var daPixelZoom:Float=6;}
class Anim {
 public var owner:Note;public var curAnim:Dynamic={name:'holdend'};
 public function new(n:Note){owner=n;}
 public function play(n:String):Void {curAnim={name:n.endsWith('end')?'holdend':'hold'};owner.frameWidth=n.endsWith('end')?30:20;owner.frameHeight=n.endsWith('end')?8:40;}
}
class Note {
 public var scale=new FlxPoint(.7,1);public var baseScale=new FlxPoint(.7,1);public var baseScaleX=1.;public var baseScaleY=1.;
 public var isSustainNote=true;public var prevNote:Note;public var noteData=0;public var frameWidth=160.;public var frameHeight=100.;
 public var width=112.;public var height=100.;public var offsetX=0.;public var x=0.;public var alpha=1.;public var multAlpha=1.;public var copyAngle=true;public var hitsoundDisabled=false;public var animation:Anim;
 public function new(){animation=new Anim(this);}
 public function updateHitbox():Void {width=frameWidth*Math.abs(scale.x);height=frameHeight*Math.abs(scale.y);}
 __DONOR__
}
class Main {
 static function near(a:Float,b:Float,m:String):Void if(Math.abs(a-b)>.000001)throw m+': '+a+' != '+b;
 static function main(){
  for(pixel in [false,true])for(step in [80.,125.,187.5])for(speed in [.73,1.,2.567]){
   PlayState.isPixelStage=pixel;PlayState.instance.songSpeed=speed;Conductor.stepCrotchet=step;
   var expectedPrevious=new Note(),actualPrevious=new Note();expectedPrevious.isSustainNote=actualPrevious.isSustainNote=false;
   for(index in 0...4){
    var expected=new Note(),actual=new Note();expected.prevNote=expectedPrevious;actual.prevNote=actualPrevious;
    expected.donorFinish();expected.x+=expected.offsetX;expected.baseScaleX=expected.scale.x;expected.baseScaleY=expected.scale.y;
    var initial=actual.width;actual.animation.play('holdend');NightmareVisionLegacySustain.finish(actual,initial,step,speed,pixel,6);
    near(actual.offsetX,expected.offsetX,'source cap width alignment');near(actual.scale.y,expected.scale.y,'source cap scale');near(actual.x,expected.x,'initial X');
    near(actualPrevious.scale.y,expectedPrevious.scale.y,'previous body scale');near(actualPrevious.baseScaleY,expectedPrevious.baseScaleY,'raw previous baseline');
    if(!actual.hitsoundDisabled||actual.copyAngle)throw 'source sustain flags';
    near(NightmareVisionSustainLayout.segmentTime(1000,index,step,true,speed),1000+step*index+step/(Math.fround(speed*100)/100),'historical generation timestamp');
    near(NightmareVisionSustainLayout.segmentTime(1000,index,step),1000+step*index,'modern timestamp isolation');
    expectedPrevious=expected;actualPrevious=actual;
   }
  }
 }
}
"""
  self.run_haxe(fixture.replace('__DONOR__',block))

 def test_pinned_reverse_clip_and_previous_frame_orientation(self):
  reverse=method(self.donor('source/modchart/modifiers/ReverseModifier.hx'),'override function updateNote(').replace('override function','public function',1)
  confusion=method(self.donor('source/modchart/modifiers/ConfusionModifier.hx'),'override function updateNote(').replace('override function','public function',1)
  perspective=method(self.donor('source/modchart/modifiers/PerspectiveModifier.hx'),'override function updateNote(').replace('override function','public function',1)
  play=self.donor('source/meta/states/PlayState.hx')
  orientation_start=play.rfind('if (daNote.isSustainNote)',0,play.index('var futureSongPos = Conductor.visualPosition'))
  orientation=method(play[orientation_start:],'if (daNote.isSustainNote)')
  fixture=r"""
import nightmarevision.modchart.NightmareVisionModchartContext;
import nightmarevision.modchart.NightmareVisionModchartRenderer;
import nightmarevision.modchart.NightmareVisionModchartTransform;
import nightmarevision.modchart.NightmareVisionModchartVector as Vector3;
class FlxRect {public var x:Float;public var y:Float;public var width:Float;public var height:Float;public function new(x:Float,y:Float,w:Float,h:Float){this.x=x;this.y=y;width=w;height=h;}}
class Note {
 public var vec3Cache=new Vector3();public var visualTime=1120.;public static var swagWidth=112.;public var x=0.;public var y=0.;public var width=64.;public var height=100.;public var frameWidth=64.;public var frameHeight=100.;public var angle=0.;public var mAngle=37.;
 public var lane=0;public var active=true;public var isSustainNote=true;public var isSustainEnd=false;public var noteData=0;public var mustPress=true;public var ignoreNote=false;public var wasGoodHit=false;public var canBeHit=true;public var prevNote:Note;
 public var offsetX=7.;public var offsetY=9.;public var offset:Dynamic={x:0.,y:3.};public var origin:Dynamic={x:0.,y:0.};public var scale:Dynamic={x:1.,y:2.};public var baseScale:Dynamic={x:1.,y:2.};public var clipRect:Dynamic={x:0.,y:11.,width:64.,height:89.};
 public var strumTime=500.;public var multSpeed(default,set):Float=1.;public var speedWrites=0;public var rawScaleY=2.;
 public function set_multSpeed(v:Float):Float {if(animation.curAnim.name=='hold'){scale.y*=v/multSpeed;rawScaleY=scale.y;}speedWrites++;return multSpeed=v;}public var alphaMod=1.;public var rgbGraphics:Dynamic={flash:0.,alpha:1.};public var animation:Dynamic={curAnim:{name:'hold'}};
 public function new(){prevNote=this;}
 public function centerOffsets():Void {offset.x=0;offset.y=0;}
 public function centerOrigin():Void {}
 public function updateHitbox():Void {}
}
class Reverse {public var rev=0.;public var modMgr:Dynamic;public function new(){}function getReverseValue(d:Int,p:Int):Float return rev;__REVERSE__}
class Confusion {public function new(){}function getValue(p:Int):Float return 0;function getSubmodValue(n:String,p:Int):Float return 0;__CONFUSION__}
class Conductor {public static var visualPosition=1000.;public static var stepCrotchet=125.;public static function getStep(t:Float):Float return t/125;}
class SourceFrame {
 public var modManager:NightmareVisionModManager;public var pN=0;public var songSpeed=1.;public var scriptedSustainOffsets=[new Vector3()];
 public function new(m:NightmareVisionModManager){modManager=m;}
 public function run(daNote:Note,pos:Vector3):Void {__ORIENTATION__}
}
class Witness extends NightmareVisionNoteModifier {
 public var seen=0.;public function new(m:NightmareVisionModManager){super(m);}
 override public function getName():String return 'witness';override public function getOrder():Int return -1;
 override public function updateNote(b:Float,n:Dynamic,p:Vector3,player:Int):Void {seen=n.clipRect.y;n.offsetY=500;}
}
class Perspective {public function new(){} __PERSPECTIVE__}
class Diagonal extends NightmareVisionNoteModifier {
 public function new(m:NightmareVisionModManager){super(m);}
 override public function getName():String return 'diagonal';
 override public function getPos(t:Float,d:Float,td:Float,b:Float,p:Vector3,k:Int,pl:Int,o:Dynamic):Vector3 return new Vector3(p.x+d,p.y,p.z);
}
class Main {
 static function near(a:Float,b:Float,m:String):Void if(Math.abs(a-b)>.000001)throw m+': '+a+' != '+b;
 static function main(){
  var ctx=new NightmareVisionModchartContext(1280,720,4,112,0,0,1,500,false,false,true);
  var manager=new NightmareVisionModManager();manager.renderContext=()->ctx;
  var renderer=new NightmareVisionModchartRenderer(new NightmareVisionModchartTransform(manager.registry));manager.sourceRenderer=renderer;
  var strum:Dynamic={y:100.,sustainReduce:true};manager.receptors=[[strum],[strum]];renderer.sourceReceptor=(p,d)->manager.receptors[p][d];
  var donor=new Reverse();donor.modMgr=manager;var reverse:NightmareVisionReverseModifier=cast manager.get('reverse');
  for(percent in [0.,.49,.5,1.])for(player in [false,true])for(ignore in [false,true])for(hit in [false,true])for(previousHit in [false,true])for(canHit in [false,true])for(y in [-100.,100.,160.,400.]){
   var a=new Note(),b=new Note();a.mustPress=b.mustPress=player;a.ignoreNote=b.ignoreNote=ignore;a.wasGoodHit=b.wasGoodHit=hit;a.canBeHit=b.canBeHit=canHit;
   a.prevNote=new Note();b.prevNote=new Note();a.prevNote.wasGoodHit=b.prevNote.wasGoodHit=previousHit;
   donor.rev=percent;reverse.setValue(percent,0);var pos=new Vector3(0,y);
   var beforeA=a.clipRect;var beforeB=b.clipRect;donor.updateNote(0,a,pos,0);reverse.updateNote(0,b,pos,0);
   if((a.clipRect==beforeA)!=(b.clipRect==beforeB))throw "source clip rectangle replacement identity";
   near(a.clipRect.y,b.clipRect.y,'source clipping Y/admission');near(a.clipRect.height,b.clipRect.height,'source clip height');
  }
  reverse.setValue(0,0);
  var witnessed=new Note();witnessed.wasGoodHit=true;var expectedClip=new Note();expectedClip.wasGoodHit=true;donor.rev=0;donor.updateNote(0,expectedClip,new Vector3(0,0),0);
  var witness=new Witness(manager);manager.quickRegister(witness);manager.setValue('witness',1,0);
  renderer.positionOffsets=(kind,dir,hold)->new Vector3(100,200);
  renderer.updateNote(ctx,witnessed,0,-50,400,-50.125,399.875,.25,strum,125,false);
  near(witness.seen,expectedClip.clipRect.y,'clip must precede later custom callback and scripted position offsets');
  near(witnessed.clipRect.y,expectedClip.clipRect.y,'no second radial clip after custom mutation');
  manager.setValue('witness',0,0);renderer.positionOffsets=null;
  reverse.setValue(0,0);strum.sustainReduce=false;
  var note=new Note();var reference=new Note();new Confusion().updateNote(0,reference,new Vector3(),0);
  renderer.updateNote(ctx,note,0,120,400,119.875,399.875,.25,strum,125,false);
  near(note.angle,reference.angle,'consume previous mAngle');near(note.mAngle,0,'source scratch alias gives zero delta');near(note.scale.y,2,'historical body must not stretch to modern endpoint');
  note.isSustainEnd=true;manager.setValue('mini',.5,0);renderer.updateNote(ctx,note,0,120,400,119.875,399.875,.25,strum,125,true);
  near(note.scale.y,2,'historical cap retains source vertical baseline');
  manager.setValue('mini',0,0);manager.quickRegister(new Diagonal(manager));manager.setValue('diagonal',1,0);note.mAngle=41;
  renderer.updateNote(ctx,note,0,120,400,119.875,399.875,.25,strum,125,true);
  near(note.angle,41,'future sample must not replace current-frame angle');near(note.mAngle,-45,'replacement vector future orientation');
  for(diagonal in [0.,1.]){
   manager.setValue('diagonal',diagonal,0);var expected=new Note(),actual=new Note();
   var pos=manager.getPos(expected.strumTime,120,400,0,0,0,expected,[],expected.vec3Cache);pos.x+=expected.offsetX;pos.y+=expected.offsetY;expected.x=pos.x;expected.y=pos.y;
   new SourceFrame(manager).run(expected,pos);
   renderer.updateNote(ctx,actual,0,120,400,119.875,399.875,Conductor.getStep(1000.125)/4,strum,125,false);
   near(actual.mAngle,expected.mAngle,'pinned future-clock block with shared/replaced scratch');
  }

  manager.setValue('diagonal',0,0);manager.setValue('transformZ',.25,0);
  var projected=new Note();var projectedState=renderer.updateNote(ctx,projected,0,120,400,119.875,399.875,.25,strum,125,false);
  // Execute the pinned donor projection on a typed Flixel point.
  var referenceProjection:Dynamic={scale:new flixel.math.FlxPoint(1,2)};
  new Perspective().updateNote(0,referenceProjection,projectedState.position,0);
  near(projected.scale.y,referenceProjection.scale.y,'projected historical hold keeps source baseline divided by depth');
  near(projectedState.position.z,.75,'fixture exercises non-unit projection');
  if(projected.speedWrites!=1)throw 'historical speed setter must run once at XModifier, not at each snapshot flush';
  near(projected.rawScaleY,2,'snapshot flush after perspective must not overwrite raw body scale');
  manager.setValue('transformZ',0,0);

  var modern=new NightmareVisionModchartContext(1280,720,4,112);var old=new Note();old.mAngle=77;renderer.updateNote(modern,old,0,100,400,150,525,1,strum,125,false);
  if(old.scale.y==2)throw 'modern endpoint stretch was lost';
  ctx=modern;var rect=old.clipRect;reverse.updateNote(0,old,new Vector3(0,-100),0);if(old.clipRect!=rect)throw 'historical direct clip leaked to modern';
 }
}
"""
  self.run_haxe(fixture.replace('__REVERSE__',reverse).replace('__CONFUSION__',confusion).replace('__ORIENTATION__',orientation).replace('__PERSPECTIVE__',perspective.replace('note:Note','note:Dynamic').replace('note.scale.scale(1/pos.z);','note.scale.x *= 1/pos.z; note.scale.y *= 1/pos.z;')))
