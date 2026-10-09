"""Compare animated source ghost setup and reuse with the historical Character API."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from test_nv_hit_order import extract_method
ROOT=Path(__file__).resolve().parents[2]
REV='7f96eb3b5a60352413229bf134bd348b79ad5fe6'
class SourceCharacterGhostTest(unittest.TestCase):
 def test_pinned_setup_reuse_completion_and_owner_teardown(self):
  donor=ROOT.parent/'fnf_sources/NightmareVision'
  if not donor.is_dir():self.skipTest('pinned historical source unavailable')
  source=subprocess.check_output(['git','show',REV+':source/gameObjects/Character.hx'],cwd=donor,text=True)
  reference=extract_method(source,'public function playGhostAnim(')
  files={
  'Reference.hx': 'import flixel.FlxSprite;import flixel.tweens.FlxTween;import flixel.tweens.FlxEase;import flixel.util.FlxColor;class Reference extends Character { public function new(){super();}'+reference+'}',
  'Character.hx': r"""import flixel.FlxSprite;import flixel.tweens.FlxTween;
class Character extends FlxSprite {
 public var doubleGhosts:Array<FlxSprite>=SourceCharacterGhosts.create();public var ghostTweenGRP:Array<FlxTween>=[];
 public var healthColorArray=[20,70,180];public var animOffsets:Map<String,Array<Float>>=[];
 public function new(){super();}
}""",
  'flixel/FlxSprite.hx':r"""package flixel;
class Point {public var x=1.;public var y=1.;public function new(){}public function set(x:Float,y:Float){this.x=x;this.y=y;}public function copyFrom(p:Point){set(p.x,p.y);}}
class Anim {public var source:Dynamic;public var played='';public function new(){}public function copyFrom(a:Anim){source=a;}public function play(n:String,f:Bool,r:Bool,frame:Int){played=n+':'+f+':'+r+':'+frame;}}
class FlxSprite {public var x=0.;public var y=0.;public var alpha=1.;public var angle=0.;public var visible=true;public var antialiasing=true;public var flipX=false;public var flipY=false;public var color:Int=0;public var shader:Dynamic=null;public var frames:Dynamic;public var scale=new Point();public var offset=new Point();public var animation=new Anim();public var destroyed=false;public function new(){}public function setPosition(x:Float,y:Float){this.x=x;this.y=y;}public function destroy(){destroyed=true;} }
""",
  'flixel/tweens/FlxEase.hx':'package flixel.tweens;class FlxEase {public static function linear(t:Float):Float return t;}',
  'flixel/util/FlxColor.hx':'package flixel.util;class FlxColor {public static function fromRGB(r:Int,g:Int,b:Int):Int return (255<<24)|(r<<16)|(g<<8)|b;}',
  'flixel/tweens/FlxTween.hx':r"""package flixel.tweens;
class FlxTween {public var target:Dynamic;public var goal:Dynamic;public var duration:Float;public var options:Dynamic;public var cancelled=false;public var destroyed=false;public function new(){}
 public static function tween(t:Dynamic,g:Dynamic,d:Float,o:Dynamic):FlxTween{var x=new FlxTween();x.target=t;x.goal=g;x.duration=d;x.options=o;return x;}
 public function cancel(){cancelled=true;}public function destroy(){destroyed=true;}
 public function complete(){for(f in Reflect.fields(goal))Reflect.setProperty(target,f,Reflect.field(goal,f));options.onComplete(this);destroy();}
}
""",
  'SourceCharacterGhosts.hx':(ROOT/'source/SourceCharacterGhosts.hx').read_text(),
  'Main.hx':r"""
class Main {
 static function check(b:Bool,s:String){if(!b)throw s;}
 static function snapshot(s:flixel.FlxSprite):String return haxe.Json.stringify([s.x,s.y,s.alpha,s.angle,s.visible,s.antialiasing,s.flipX,s.flipY,s.color,s.scale.x,s.scale.y,s.offset.x,s.offset.y,s.animation.played]);
 static function main(){
  for(name in ['singLEFT','singDOWN','singUP','singRIGHT','singLEFT-alt','singDOWN-alt','singUP-alt','singRIGHT-alt'])for(id in 0...4)for(offset in [false,true])for(reversed in [false,true]){
   var a=new Character(),b=new Reference();var atlas={};
   for(c in [a,b]){c.x=230;c.y=-45;c.alpha=0.8;c.frames=atlas;c.scale.set(1.4,0.7);c.flipX=true;c.flipY=true;c.shader={};c.doubleGhosts[id].angle=13;if(offset)c.animOffsets.set(name,[17.,-29.]);}
   for(reuse in 0...2){
    var prior=a.ghostTweenGRP[id];
    SourceCharacterGhosts.play(a,id,name,true,reversed,2);b.playGhostAnim(id,name,true,reversed,2);
    check(snapshot(a.doubleGhosts[id])==snapshot(b.doubleGhosts[id]),'source ghost setup');
    check(a.doubleGhosts[id].frames==atlas&&a.doubleGhosts[id].animation.source==a.animation&&a.doubleGhosts[id].shader==null,'shared atlas, separate controller, source shader default');
    var at=a.ghostTweenGRP[id],bt=b.ghostTweenGRP[id];check(at.duration==bt.duration&&haxe.Json.stringify(at.goal)==haxe.Json.stringify(bt.goal),'source tween trajectory');
    if(prior!=null)check(prior.cancelled,'reused slot did not cancel prior tween');
   }
   a.ghostTweenGRP[id].complete();b.ghostTweenGRP[id].complete();
   check(snapshot(a.doubleGhosts[id])==snapshot(b.doubleGhosts[id])&&a.ghostTweenGRP[id]==null&&b.ghostTweenGRP[id]==null,'source completion');
   SourceCharacterGhosts.play(a,id,name,false,false,0);var live=a.ghostTweenGRP[id];var ghost=a.doubleGhosts[id];
   SourceCharacterGhosts.destroy(a.doubleGhosts,a.ghostTweenGRP);
   check(live.cancelled&&live.destroyed&&ghost.destroyed&&a.doubleGhosts.length==0&&a.ghostTweenGRP.length==0,'owned teardown');
  }
 }
}
"""}
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
   work=FixturePath(directory)
   for name,text in files.items():
    p=work/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
