"""Compare shared field scaling with the pinned historical source setter."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND
from test_nv_multifield_routes import method
ROOT=Path(__file__).resolve().parents[2]
class LegacyFieldScaleTest(unittest.TestCase):
 def test_source_scale_mutations_membership_and_restoration(self):
  donor=subprocess.check_output(['git','show','7f96eb3b5a60352413229bf134bd348b79ad5fe6:source/gameObjects/PlayField.hx'],cwd=ROOT.parent/'fnf_sources/NightmareVision',text=True)
  setter=method(donor,'public function set_scale(')
  main=r'''
class Point {public var x:Float;public var y:Float;public function new(x=1.,y=1.)set(x,y);public function set(x:Float,y:Float){this.x=x;this.y=y;}public function copyFrom(p:Point)set(p.x,p.y);}
class Sprite {
 public var frameWidth(get,never):Int;function get_frameWidth():Int return 160;public var scale=new Point();var baseline=new Point();public var defScale(get,never):Point;function get_defScale():Point return baseline;public var baseScaleX=2.;public var baseScaleY=3.;public var isSustainNote=false;public var updates=0;
 public var animation:Dynamic={curAnim:{name:'confirm'}};public var calls:Array<String>=[];
 public function new(sustain=false){isSustainNote=sustain;if(sustain)baseScaleY=9;}
 public function setGraphicSize(w:Int):Void scale.set(w/frameWidth,w/frameWidth);
 public function updateHitbox():Void updates++;
 public function playAnim(n:String,force:Bool):Void{calls.push(n);animation.curAnim={name:n};}
}
class Donor {public var members:Array<Sprite>;public var notes:Array<Sprite>;public var scale=1.;public function new(){members=[new Sprite(),new Sprite()];members[1].animation.curAnim=null;notes=[new Sprite(),new Sprite(true)];}__SETTER__}
class Main {
 static function snapshot(s:Sprite):String return [s.scale.x,s.scale.y,s.defScale.x,s.defScale.y,s.baseScaleX,s.baseScaleY,s.updates].join(',')+':'+s.calls.join(',');
 static function check(v:Bool,m:String):Void if(!v)throw m;
 static function main(){
  var expected=new Donor(),actual=new Donor();
  for(value in [.5,2.,0.,-1.,1.]){
   expected.set_scale(value);NightmareVisionLegacyFieldScale.apply(cast actual.members,cast actual.notes,value);
   for(i in 0...2){check(snapshot(expected.members[i])==snapshot(actual.members[i]),'source receptor scale/animation');check(snapshot(expected.notes[i])==snapshot(actual.notes[i]),'source note scale');}
   check(actual.notes[1].scale.y==9,'sustain timing height unchanged');
   check(actual.notes[0].baseScaleX==2&&actual.notes[0].baseScaleY==3,'unscaled source baseline retained');
  }
  var added=new Sprite();added.scale.set(.75,.8);NightmareVisionLegacyFieldScale.captureNote(added);
  NightmareVisionLegacyFieldScale.note(added,2);check(added.scale.x==1.5&&added.scale.y==1.6,'new note adopts field scalar');
  NightmareVisionLegacyFieldScale.note(added,.5);check(added.scale.x==.375&&added.scale.y==.4,'field changes do not compound');
  NightmareVisionLegacyFieldScale.remove(added);check(added.scale.x==.75&&added.scale.y==.8&&added.defScale.x==.75,'removal restores raw baseline');
 }
}
'''.replace('__SETTER__',setter)
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as d:
   Path(d,'Main.hx').write_text(main)
   Path(d,'flixel/math').mkdir(parents=True)
   Path(d,'flixel/math/FlxPoint.hx').write_text('package flixel.math; typedef FlxPoint = Main.Point;')
   r=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',d,'--main','Main','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=30)
   self.assertEqual(r.returncode,0,r.stdout+r.stderr)
if __name__=='__main__':unittest.main()
