from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
class VerticalHealthIconsTest(unittest.TestCase):
    def test_icons_track_rotated_bar_and_respect_layout_override(self):
        s=(ROOT/'source/PlayState.hx').read_text();start=s.index('\t\tif (!iconOverride && iconsVertical)');end=s.index('\n\t\tplayer1Icon =',start)
        fixture='''class FlxMath {public static function remapToRange(v:Float,a:Float,b:Float,c:Float,d:Float)return c+(v-a)/(b-a)*(d-c);}
class Test {
 static function position(percent:Float,overrideLayout:Bool=false,p1OffsetX:Float=0,p1OffsetY:Float=0,p2OffsetX:Float=0,p2OffsetY:Float=0):Array<Float>{
 var healthBar={x:200.,y:100.,width:600.,height:20.,percent:percent};
 var iconP1={x:0.,y:0.,width:150.,height:150.};var iconP2={x:0.,y:0.,width:150.,height:150.};
 var iconOffset=26;var iconsVertical=true;var iconOverride=overrideLayout;
 var compatIconP1OffsetX=p1OffsetX;var compatIconP1OffsetY=p1OffsetY;
 var compatIconP2OffsetX=p2OffsetX;var compatIconP2OffsetY=p2OffsetY;
 var compatIconP1AppliedOffsetY=0.;var compatIconP2AppliedOffsetY=0.;
''' + s[start:end] + '''
 return [iconP1.x,iconP1.y,iconP2.x,iconP2.y];
 }
 static function main(){
  var half=position(50);if(half[0]!=425||half[2]!=425||half[1]!=84||half[3]!=-14)throw 'Incorrect centre';
  var full=position(100);var empty=position(0);
  if(empty[1]-full[1]!=600||empty[0]!=full[0])throw 'Icons must follow vertical fill';
  var shifted=position(50,false,10,20,-5,-30);
  if(shifted[0]!=435||shifted[1]!=104||shifted[2]!=420||shifted[3]!=-44)
   throw 'Compatibility icon offsets were not applied';
  for(v in position(50,true))if(v!=0)throw 'Layout override must win';
 }
}'''
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'Test.hx').write_text(fixture, newline='\n')
            p=subprocess.run([*HAXE_COMMAND,'-cp',d,'-main','Test','--interp'],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
