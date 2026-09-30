"""Live NMV conductor/window views without touching a desktop or native save."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / '.tools/haxe/haxe'

class NightmareVisionTimingWindowTest(unittest.TestCase):
    def test_live_tempo_map_window_and_camera_bindings(self):
        if not HAXE.exists():
            self.skipTest('portable Haxe unavailable')
        native = '''class Conductor {
 public static var bpm:Float=120;
 public static var crochet:Float=500;
 public static var stepCrochet:Float=125;
 public static var songPosition:Float=0;
 public static var lastSongPos:Float=0;
 public static var offset:Float=0;
 public static var safeZoneOffset:Float=150;
 public static var bpmChangeMap:Array<Dynamic>=[{stepTime:8,songTime:1000.,bpm:60.}];
 public static function changeBPM(v:Float) {bpm=v;crochet=60000/v;stepCrochet=crochet/4;}
}'''
        main = r'''class Main {
 static function eq(a:Dynamic,b:Dynamic,label:String) {if(a!=b) throw label+': '+a+' != '+b;}
 static function near(a:Float,b:Float) {if(Math.isNaN(a)||Math.abs(a-b)>.00001) throw 'timing '+a+' != '+b;}
 static function main() {
  var c = new NightmareVisionConductor();
  var sibling = new NightmareVisionConductor();
  var map = Conductor.bpmChangeMap;
  NightmareVisionConductor.initializeMap(120);
  eq(c.bpmChangeMap,map,'native map identity');
  eq(map.length,2,'initial tempo inserted once');
  NightmareVisionConductor.initializeMap(120);
  eq(map.length,2,'no duplicate initial tempo');
  near(c.getStep(1125),8.5); near(c.stepToSeconds(8.5),1125);
  near(c.getBeat(1000),2); near(c.beatToSeconds(2),1000);
  near(c.getStep(-250),-2); near(c.getCrotchetAtTime(1100),1000);
  eq(c.getBPMFromSeconds(1000),map[1],'inclusive tempo boundary');
  eq(c.getBPMFromStep(8),map[1],'inclusive step boundary');
  c.bpm=240; near(Conductor.bpm,240);near(sibling.crotchet,250);near(c.stepCrotchet,62.5);
  // The source's explicit initial map preserves earlier tempo after a BPM write.
  near(c.getStep(500),4);
  c.songPosition=321; near(Conductor.songPosition,321);
  Conductor.songPosition=654; near(sibling.songPosition,654);
  eq(c.beatToRow(1.5),72,'row conversion');near(c.noteRowToBeat(24),.5);
  c.mapBPMChanges({bpm:120.,notes:[{sectionBeats:2.,changeBPM:false,bpm:120.},
   {sectionBeats:3.,changeBPM:true,bpm:60.},{sectionBeats:null,changeBPM:true,bpm:180.}]});
  eq(c.bpmChangeMap,map,'map rebuild keeps shared array');
  near(map[1].songTime,1000); eq(map[1].stepTime,8,'variable length section');
  near(map[2].songTime,4000); eq(map[2].stepTime,20,'second variable section');
  for(fps in [60,240,480]) for(frame in 0...fps*5) {
   var t=frame*1000./fps; near(c.stepToSeconds(c.getStep(t)),t);
  }
  var cameras:Array<Dynamic>=[{id:1},{id:2}];
  var view=new NightmareVisionCameraUtil(function() return cameras);
  eq(view.lastCamera,cameras[1],'last camera');
  cameras=[{id:3}];eq(view.lastCamera,cameras[0],'camera list replacement is live');
  var diagnosed=false;
  try view.quickCreateCam() catch(e:Dynamic) diagnosed=Std.string(e).indexOf('blend renderer')>=0;
  eq(diagnosed,true,'unsupported source renderer diagnosed');
  var alerts=0;
  var w:Dynamic={x:10,y:20,width:800,height:600,title:'old',borderless:false,
   opacity:1.,minimized:false,maximized:false,display:{bounds:{width:1920,height:1080}},
   alert:function(a:String,b:String){alerts++;}};
  var win=new NightmareVisionWindowUtil(function()return w,function()return 'engine',function(x,y)return {x:x,y:y});
  win.setTitle('end',true);eq(w.title,'oldend','append');
  win.setTitle('start',true,true);eq(w.title,'startoldend','prepend wins');
  win.setTitle();eq(w.title,'engine','default title');
  win.centerWindow();eq(w.x,560,'center x');eq(w.y,240,'center y');
  win.centerWindowOnPoint({x:100,y:200});eq(w.x,-300,'point x');eq(w.y,-100,'point y');
  eq(win.isWindowOnScreen(),false,'outside');win.clampWindowToScreen();eq(win.isWindowOnScreen(),true,'clamped');
  win.borderless=true;win.opacity=.7;win.minimized=true;win.maximized=true;
  eq(w.borderless,true,'borderless native');near(w.opacity,.7);eq(w.minimized,true,'minimized native');
  win.flash();eq(alerts,1,'source alert forwarded');
  eq(win.getCenterWindowPoint().x,960,'center point');
  w.title='changed';win.resetTitle();eq(w.title,'engine','title reset');
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            work=Path(directory)
            (work/'Conductor.hx').write_text(native)
            (work/'lime/ui').mkdir(parents=True)
            (work/'lime/ui/Window.hx').write_text('package lime.ui; typedef Window = Dynamic;')
            (work/'Main.hx').write_text(main)
            result=subprocess.run([str(HAXE),'-cp',str(ROOT/'source'),'-cp',str(work),'-main','Main','--interp'],cwd=work,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__':unittest.main()
