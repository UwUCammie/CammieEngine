"""Source camera locks and HUD fades survive the shared event boundary."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath

ROOT = Path(__file__).resolve().parents[2]


def method(text, name):
    start = text.index('\tfunction ' + name + '(')
    opening = text.index('{', start)
    cursor = opening + 1
    depth = 1
    while depth:
        depth += (text[cursor] == '{') - (text[cursor] == '}')
        cursor += 1
    return text[start:cursor]


class SourceCameraHudEventsTest(unittest.TestCase):
    def test_source_lock_release_and_replacing_hud_fades(self):
        text = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        self.assertIn('sourceCameraFollowPosition(e.v1, e.v2);', text)
        self.assertIn("case 'HUD Fade':\n\t\t\t\tsourceHudFade(e.v1, e.v2);", text)
        code = method(text, 'sourceCameraFollowPosition') + method(text, 'sourceHudFade')
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='source-camera-events-', dir=TEST_TMP) as directory:
            work = FixturePath(directory)
            (work / 'Bridge.hx').write_text('''class Bridge {
 public var camFollow:Dynamic={x:0.0,y:0.0};public var isCameraOnForcedPos:Bool=false;
 public var camHUD:Dynamic={alpha:0.4}; public function new(){}
''' + code + '}', encoding='utf-8')
            (work / 'FlxTween.hx').write_text('''class FlxTween {
 public static var cancelled:Int=0;public static var started:Int=0;
 public static var target:Dynamic;public static var values:Dynamic;public static var duration:Float;
 public static function cancelTweensOf(object:Dynamic,fields:Array<String>):Void {
  if(fields.length!=1 || fields[0]!='alpha') throw 'only replace HUD alpha tween';
  cancelled++;target=object;
 }
 public static function tween(object:Dynamic,props:Dynamic,time:Float):Void {
  started++;target=object;values=props;duration=time;
 }
}''', encoding='utf-8')
            (work / 'Main.hx').write_text('''@:access(Bridge)
class Main {
 static function check(value:Bool,message:String):Void if(!value) throw message;
 static function main():Void {
  var b=new Bridge();b.sourceCameraFollowPosition('450','490');
  check(b.isCameraOnForcedPos && b.camFollow.x==450 && b.camFollow.y==490,'coordinates lock source follow');
  b.sourceCameraFollowPosition('','');check(!b.isCameraOnForcedPos,'empty values release source follow');
  b.sourceCameraFollowPosition('oops','12');
  check(b.isCameraOnForcedPos && b.camFollow.x==0 && b.camFollow.y==12,'one numeric coordinate still locks');
  b.sourceCameraFollowPosition('oops','bad');check(!b.isCameraOnForcedPos,'non-numeric values release');
  b.sourceHudFade('1','1.3');
  check(FlxTween.cancelled==1 && FlxTween.started==1 && FlxTween.target==b.camHUD
   && FlxTween.values.alpha==1 && FlxTween.duration==1.3,'restore replaces unfinished alpha fade');
  b.sourceHudFade('0','0');check(b.camHUD.alpha==0 && FlxTween.started==1,'zero duration hides immediately');
  b.sourceHudFade('1','-1');check(b.camHUD.alpha==1 && FlxTween.started==1,'negative duration assigns directly');
  b.sourceHudFade('bad','');
  check(FlxTween.cancelled==4 && FlxTween.started==2 && FlxTween.values.alpha==1
   && FlxTween.duration==1,'source defaults are one alpha and one second');
 }
}''', encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '--run', 'Main'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
