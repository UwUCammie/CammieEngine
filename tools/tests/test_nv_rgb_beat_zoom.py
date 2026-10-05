"""Pin reflective NV RGB methods and the donor beat-camera contract."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_nv_multifield_routes import method

ROOT = Path(__file__).resolve().parents[2]


class NvRgbBeatZoomTest(unittest.TestCase):
    def test_reflective_rgb_and_extracted_source_beat_zoom(self):
        play = (ROOT / 'source/PlayState.hx').read_text()
        start = play.index('@:keep public var beatsPerZoom(get, set):Int;')
        end = play.index('\n\tpublic var cameraZoomRate', start)
        helper = method(play, 'function applyNightmareVisionBeatZoom():Void')
        self.assertLess(play.index('applyNightmareVisionBeatZoom();'), play.index("callNightmareVision('onBeatHit', []);"))
        self.assertIn('if (nightmareVisionScripts == null && !codenameCameraModuloActive', play)
        fixture = r'''
class FlxG {public static var camera:Dynamic;}
class FlxTween {
 public static var game:Dynamic;
 public static var hud:Dynamic;
 public static var gameTween:Bool=false;
 public static var hudTween:Bool=false;
 public static var globalManager={containsTweensOf:function(object:Dynamic, fields:Array<String>):Bool {
  return object==game ? gameTween : hudTween;
 }};
}
class Main {
 public var camZoomRate:Int=4;
 __ALIAS__
 var nightmareVisionScripts:Dynamic={};
 var camZooming:Bool=true;
 var enabled:Bool=true;
 var curBeat:Int=0;
 var camZoomIntensity:Float=2;
 var camGame:Dynamic={zoom:2.0};
 var camHUD:Dynamic={zoom:1.0};
 function sourceLivePreference(name:String, fallback:Bool):Bool return enabled;
 function setGameCameraZoom(value:Float):Void camGame.zoom=value;
 __HELPER__
 public function new() {FlxTween.game=camGame;FlxTween.hud=camHUD;FlxG.camera=camGame;}
 static function near(actual:Float, expected:Float, label:String) { if(Math.abs(actual-expected)>0.00001) throw label; }
 static function check(ok:Bool, label:String) {if(!ok)throw label;}
 static function main() {
  // No typed setColors/getColors call: the production script finds both reflectively.
  var rgb:Dynamic=new NightmareVisionRGBGraphics();
  var set=Reflect.field(rgb,'setColors');
  check(set!=null,'setColors retained for native reflective scripts');
  Reflect.callMethod(rgb,set,[[0x112233,0x445566,0x778899]]);
  var colors:Array<Int>=Reflect.callMethod(rgb,Reflect.field(rgb,'getColors'),[]);
  check(colors.join(',')==[0x112233,0x445566,0x778899].join(','),'reflective colors update live palette');
  var h=new Main();
  h.beatsPerZoom=3; check(h.camZoomRate==3,'source alias updates live native interval');
  h.curBeat=2;h.applyNightmareVisionBeatZoom();near(h.camGame.zoom,2,'no off-beat zoom');
  h.curBeat=3;h.applyNightmareVisionBeatZoom();near(h.camGame.zoom,2.03,'source zoom above legacy cap');near(h.camHUD.zoom,1.06,'source HUD zoom');
  h.enabled=false;h.curBeat=6;h.applyNightmareVisionBeatZoom();near(h.camGame.zoom,2.03,'source camZooms preference');
  h.enabled=true;FlxTween.gameTween=true;h.applyNightmareVisionBeatZoom();near(h.camGame.zoom,2.03,'game tween suppresses game bop');near(h.camHUD.zoom,1.12,'independent HUD bop');
  FlxTween.gameTween=false;FlxTween.hudTween=true;h.applyNightmareVisionBeatZoom();near(h.camGame.zoom,2.06,'independent game bop');near(h.camHUD.zoom,1.12,'HUD tween suppresses HUD bop');
  h.beatsPerZoom=0;h.curBeat=7;h.applyNightmareVisionBeatZoom();check(h.beatsPerZoom==4,'source zero interval resets');near(h.camGame.zoom,2.06,'reset interval gates current beat');
  h.curBeat=8;var replaced:Dynamic={zoom:1.5};FlxG.camera=replaced;FlxTween.game=replaced;
  h.applyNightmareVisionBeatZoom();near(replaced.zoom,1.53,'source uses replaced live camera');near(h.camGame.zoom,2.06,'replacement leaves native camera alone');
  FlxTween.gameTween=true;h.applyNightmareVisionBeatZoom();near(replaced.zoom,1.53,'replacement tween guards live camera');
  h.nightmareVisionScripts=null;h.applyNightmareVisionBeatZoom();near(replaced.zoom,1.53,'non NV source helper inert');
 }
}
'''.replace('__ALIAS__', play[start:end]).replace('__HELPER__', helper)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = FixturePath(directory)
            (work / 'Main.hx').write_text(fixture, newline='\n')
            (work / 'NightmareVisionRGBGraphics.hx').write_text((ROOT / 'source/NightmareVisionRGBGraphics.hx').read_text(), newline='\n')
            (work / 'PsychRGBPalette.hx').write_text('''class PsychRGBPalette {
 public var r:Int=0;public var g:Int=0;public var b:Int=0;public var mult:Float=1;
 public var shader:Dynamic={mult:{value:[]},u_alpha:{value:[]},u_flash:{value:[]}};
 public function new() {}
 public function copy():PsychRGBPalette return new PsychRGBPalette();
}''', newline='\n')
            (work / 'flixel').mkdir()
            (work / 'flixel/FlxSprite.hx').write_text('package flixel; class FlxSprite {public var shader:Dynamic;}', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', directory,
                                     '-main', 'Main', '-dce', 'full', '--interp'], capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
