"""Pinned event-video setup and chroma key over the shared decoder boundary."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_source_event_preparation import extract_method

ROOT = Path(__file__).resolve().parents[2]
REV = '7f96eb3b5a60352413229bf134bd348b79ad5fe6'


class HistoricalEventVideoTest(unittest.TestCase):
    def source(self, path):
        donor = ROOT.parent / 'fnf_sources/NightmareVision'
        if not donor.is_dir():
            self.skipTest('pinned source unavailable')
        return subprocess.check_output(['git', 'show', REV + ':' + path], cwd=donor, text=True)

    def test_chroma_key_matches_pinned_shader(self):
        donor = self.source('source/gameObjects/shader/GreenScreenShader.hx')
        actual = (ROOT / 'source/NightmareVisionGreenScreenShader.hx').read_text()
        def shader(text):
            return re.sub(r'\s+', '', text.split("@:glFragmentSource('", 1)[1].split("')", 1)[0])
        self.assertEqual(shader(actual), shader(donor))

    def test_setup_format_end_and_visibility_match_source(self):
        method = extract_method(self.source('source/meta/states/PlayState.hx'), 'function playVideo(')
        files = {
            'Reference.hx': '''import flixel.FlxG;
class Reference extends flixel.FlxState {
 public var camHUD:flixel.FlxCamera;public function new(c){super();camHUD=c;}
 public __METHOD__
}
class PsychVideoSprite extends NightmareVisionLegacyVideoSprite {public function new(){super(null,null);}}
class GreenScreenShader extends NightmareVisionGreenScreenShader {public function new(){super();}}
class Paths {public static function video(n:String)return 'owner/videos/'+n+'.mp4';}
class VidCallbacks {public static var ONFORMAT='onFormat';public static var ONEND='onEnd';}
'''.replace('__METHOD__', method),
            'flixel/FlxState.hx': '''package flixel; class FlxState {
 public function new(){} public function add(v:Dynamic):Dynamic {NightmareVisionLegacyVideoSprite.log.push('add');return v;}
}''',
            'flixel/FlxCamera.hx': 'package flixel; class FlxCamera {public function new(){}}',
            'flixel/FlxG.hx': 'package flixel; class FlxG {public static var height=720;}',
            'NightmareVisionPaths.hx': "class NightmareVisionPaths {public function new(){} public function video(n:String)return 'owner/videos/'+n+'.mp4';}",
            'NightmareVisionGreenScreenShader.hx': 'class NightmareVisionGreenScreenShader {public function new(){}}',
            'NightmareVisionLegacyVideoSprite.hx': '''class NightmareVisionLegacyVideoSprite {
 public static var log:Array<String>=[];public static var latest:NightmareVisionLegacyVideoSprite;
 public var shader:Dynamic;public var cameras:Array<flixel.FlxCamera>;public var scrollFactor:Point=new Point();
 public var visible=true;public var callbacks:Map<String,Void->Void>=[];public var destroyed=false;
 public function new(s:Dynamic,p:Dynamic){latest=this;log.push('new');}
 public function addCallback(n:String,f:Void->Void){log.push('callback:'+n);callbacks.set(n,f);}
 public function load(p:String){log.push('load:'+p);}public function play(){log.push('play');}
 public function setGraphicSize(w:Int,h:Int){log.push('size:'+w+':'+h);}
 public function updateHitbox(){log.push('hitbox');}public function destroy(){destroyed=true;log.push('destroy');}
}
class Point {public var x=1.;public var y=1.;public function new(){}public function set(x=0.,y=0.){this.x=x;this.y=y;NightmareVisionLegacyVideoSprite.log.push('scroll');}}
''',
            'Main.hx': '''class Main {
 static function check(b:Bool,m:String){if(!b)throw m;}
 static function inspect(camera:flixel.FlxCamera,visible:Bool):String {
  var v=NightmareVisionLegacyVideoSprite.latest;
  check(v.visible&&v.cameras==null,'format must defer visibility and camera changes');
  v.callbacks.get('onFormat')();
  check(v.visible==visible&&v.cameras[0]==camera&&v.scrollFactor.x==0&&v.scrollFactor.y==0,'formatted state');
  check(Std.isOfType(v.shader,NightmareVisionGreenScreenShader),'source shader');
  v.callbacks.get('onEnd')();check(v.destroyed,'end destruction');
  return NightmareVisionLegacyVideoSprite.log.join('|');
 }
 static function main(){
  var camera=new flixel.FlxCamera();
  for(visible in [false,true]) {
   NightmareVisionLegacyVideoSprite.log=[];new Reference(camera).playVideo('clip',visible);
   var expected=inspect(camera,visible);
   NightmareVisionLegacyVideoSprite.log=[];
   if(visible)NightmareVisionLegacyEventVideo.play(new flixel.FlxState(),new NightmareVisionPaths(),camera,'clip');
   else NightmareVisionLegacyEventVideo.play(new flixel.FlxState(),new NightmareVisionPaths(),camera,'clip',false);
   check(inspect(camera,visible)==expected,'source call ordering');
  }
 }
}''',
            'NightmareVisionLegacyEventVideo.hx': (ROOT / 'source/NightmareVisionLegacyEventVideo.hx').read_text(),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = FixturePath(folder)
            for name, content in files.items():
                target = work / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '-main', 'Main', '--interp'],
                                    cwd=ROOT, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
