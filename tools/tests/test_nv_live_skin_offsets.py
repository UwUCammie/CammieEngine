"""Execute mutable source NoteSkin vectors through the production offset bridge."""
import shutil
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from tools.haxe_flixel_math_stubs import write_flixel_point_stub

ROOT = Path(__file__).resolve().parents[2]


class NvLiveSkinOffsetsTest(unittest.TestCase):
    def test_vector_mutation_replacement_and_field_isolation(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            write_flixel_point_stub(work)
            shutil.copy2(ROOT / 'source/NightmareVisionSkinOffsetBridge.hx', work)
            package = work / 'nightmarevision/modchart'
            package.mkdir(parents=True)
            for name in ['NightmareVisionModchartSkinOffsets', 'NightmareVisionModchartObject',
                         'NightmareVisionModchartVector']:
                shutil.copy2(ROOT / ('source/nightmarevision/modchart/' + name + '.hx'), package)
            (work / 'NightmareVisionNoteSkin.hx').write_text('''
import haxe.ds.Vector;
import flixel.math.FlxPoint;
class NightmareVisionNoteSkin {
 public var noteOffsets:Vector<FlxPoint>;
 public var receptorOffsets:Vector<FlxPoint>;
 public var sustainOffsets:Vector<FlxPoint>;
 public var susEndOffsets:Vector<FlxPoint>;
 public var splashOffsets:Vector<FlxPoint>;
 public var sustainSplashOffsets:Vector<FlxPoint>;
 public function new() {
  noteOffsets=points();receptorOffsets=points();sustainOffsets=points();
  susEndOffsets=points();splashOffsets=points();sustainSplashOffsets=points();
 }
 static function points():Vector<FlxPoint> {
  var result=new Vector<FlxPoint>(4);
  for(i in 0...4)result[i]=new FlxPoint();
  return result;
 }
}
''', newline='\n')
            (work / 'Main.hx').write_text('''
import haxe.ds.Vector;
import flixel.math.FlxPoint;
import nightmarevision.modchart.NightmareVisionModchartSkinOffsets;
class Main {
 static function check(ok:Bool,label:String):Void if(!ok)throw label;
 static function main() {
  var a=new NightmareVisionNoteSkin(), b=new NightmareVisionNoteSkin();
  var current=a;
  var offsets=new NightmareVisionModchartSkinOffsets(4);
  offsets.readLive=function(kind,lane,hold)return NightmareVisionSkinOffsetBridge.read(current,kind,lane,hold);
  a.noteOffsets[1].set(5,6);a.sustainOffsets[1].set(2,3);
  var tap=offsets.get('note',1), hold=offsets.get('note',1,true);
  check(tap.x==5&&tap.y==6&&hold.x==7&&hold.y==9,'hold sums live note/sustain vectors');
  tap.x=999;
  check(a.noteOffsets[1].x==5,'results do not modify source vectors');
  a.noteOffsets[1].x=10;
  check(offsets.get('note',1).x==10,'live point mutation');
  a.receptorOffsets[3]=new FlxPoint(11,12);
  check(offsets.get('receptor',-1).x==11,'replacement points and wrapped lanes');
  a.susEndOffsets[0].set(13,14);
  check(offsets.getSustainEnd(0).y==14,'live sustain-end vector');
  a.splashOffsets[0].x=15;a.sustainSplashOffsets[0].y=16;
  check(offsets.get('noteSplash',0).x==15&&offsets.get('sustainSplash',0).y==16,'live effect vectors');
  b.noteOffsets[1].x=20;current=b;
  check(offsets.get('note',1).x==20&&a.noteOffsets[1].x==10,'replacement skin and field isolation');
  b.noteOffsets=new Vector<FlxPoint>(0);
  check(offsets.get('note',1).x==0,'empty vectors');
  current=null;
  check(offsets.get('note',0).x==0,'detached skin');
  offsets.readLive=null;offsets.note[0].x=21;
  check(offsets.get('note',0).x==21,'snapshot fixtures retain prior behavior');
 }
}
''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '-main', 'Main', '--interp'],
                                    capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
