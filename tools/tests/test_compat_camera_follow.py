"""Exercise the real camera adapter's automatic-follow and explicit-snap gates."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]

class CompatCameraFollowTest(unittest.TestCase):
    def test_default_follow_disabled_follow_and_explicit_snap(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as scratch:
            p=Path(scratch);(p/'flixel').mkdir()
            (p/'flixel/FlxCamera.hx').write_text('''package flixel;
class FlxCamera {
 public var target:Dynamic;
 public var follows=0;public var snaps=0;public var lerps=0;
 public var scroll=0.0;
 public function new() {}
 function updateFollow():Void follows++;
 // Pinned Flixel updates the target and interpolates scroll separately.
 function updateLerp(elapsed:Float):Void {lerps++;scroll+=(100-scroll)*0.25;}
 public function update(elapsed:Float):Void if(target!=null){updateFollow();updateLerp(elapsed);}
 public function snapToTarget():Void {updateFollow();snaps++;}
}
''')
            (p/'Main.hx').write_text('''class Main {
 static function check(ok:Bool,label:String):Void if(!ok)throw label;
 static function main():Void {
  var camera=new CompatCamera();var actor={x:1,y:2};camera.target=actor;
  camera.update(.016);check(camera.follows==1 && camera.lerps==1 && camera.scroll==25 && camera.followEnabled,"native default follow changed");
  camera.followEnabled=false;camera.update(.016);
  check(camera.follows==1 && camera.lerps==1 && camera.scroll==25 && camera.target==actor,"disabled follow still interpolated scroll or hid target");
  camera.scroll=60; // A script/tween owns scroll while following is suspended.
  for(i in 0...120)camera.update(.016);
  check(camera.scroll==60 && camera.lerps==1,"suspended camera drifted toward a stale follow point");
  camera.snapToTarget();
  check(camera.follows==2 && camera.snaps==1 && !camera.followEnabled && camera.target==actor,"explicit snap did not preserve disabled state");
  var other={x:3,y:4};camera.target=other;
  camera.followEnabled=true;camera.update(.016);
  check(camera.follows==3 && camera.lerps==2 && camera.scroll==70 && camera.target==other,"script retarget lost");
 }
}
''')
            result=subprocess.run([str(ROOT/'.tools/haxe/haxe'),'-cp',str(ROOT/'source'),'-cp',str(p),'--run','Main'],cwd=ROOT,text=True,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__':unittest.main()
