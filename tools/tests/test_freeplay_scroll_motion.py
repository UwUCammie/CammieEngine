"""Elapsed-time Freeplay hold repeat and centered selection behavior."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import HAXE_COMMAND
ROOT = Path(__file__).resolve().parents[2]
class FreeplayScrollMotionTest(unittest.TestCase):
 def test_repeat_and_motion_across_frame_rates(self):
  fixture = r'''class Main {
 static function check(ok:Bool, message:String) { if (!ok) throw message; }
 static function run(fps:Int, fast:Bool):Int {
  var motion = new FreeplayScrollMotion(); var steps=motion.advance(0,false,true,fast);
  for(i in 0...fps*2) steps+=motion.advance(1/fps,false,true,fast);
  return steps;
 }
 static function main() {
  for(fps in [30,60,144,480,1000]) {
   check(run(fps,false)==18,'normal FPS drift '+fps);
   check(run(fps,true)==52,'fast FPS drift '+fps);
  }
  var motion=new FreeplayScrollMotion();
  check(motion.advance(0,true,false,false)==-1,'initial single step');
  for(i in 0...3)check(motion.advance(0.09,true,false,false)==0,'initial delay');
  check(motion.advance(0.02,true,false,false)==0,'delay remainder');
  check(motion.advance(0.03,true,false,true)==-1,'shift during hold');
  check(motion.advance(0,false,true,false)==1,'direction change must be immediate');
  check(motion.advance(1,true,true,true)==0,'opposed keys');
  check(motion.advance(0,true,false,false)==-1,'release reset');
  motion.advance(0,false,false,false);
  check(motion.advance(0,false,true,false)==1,'typing or substate reset must rearm initial step');
  for(i in 0...4)motion.advance(0.1,false,true,false);
  check(motion.advance(10,false,true,true)<=3,'hitch backlog must be discarded');
  var low=new FreeplayScrollMotion(); var high=new FreeplayScrollMotion();
  low.moved(-1);high.moved(-1);
  check(low.offset>0,'up should start below center');
  for(i in 0...30)low.settle(1/30);
  for(i in 0...480)high.settle(1/480);
  check(Math.abs(low.offset-high.offset)<0.001 && low.offset==0,'settle FPS drift');
  high.moved(1);check(high.offset<0,'down should start above center');
  var entries=[for(i in 0...1300)i];
  for(height in [480,720,1080])for(selected in [0,1,650,1299]) {
   var page=FreeplayBrowserLayout.centeredPage(entries,selected,height);
   var pos=page.indexOf(selected);
   check(pos>=0,'selected absent');
   var y=FreeplayBrowserLayout.centeredRowY(pos,pos,height);
   check(y+FreeplayBrowserLayout.SELECTED_HEIGHT/2==height/2,'selection not centered');
   check(FreeplayBrowserLayout.centeredRowY(0,pos,height)>=FreeplayBrowserLayout.TOP+18,'header overlap');
   check(FreeplayBrowserLayout.centeredRowY(page.length-1,pos,height)+(page.length-1==pos?82:42)<=height-84-18,'footer overlap');
  }
 }
}'''
  with tempfile.TemporaryDirectory() as folder:
   Path(folder,'Main.hx').write_text(fixture)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',folder,'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=30)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr)
 def test_host_routes_and_embedded_collections(self):
  menu=(ROOT/'source/MainMenuState.hx').read_text()
  self.assertEqual(menu.count('FreeplayState.openHostLibrary();'),2)
  self.assertNotIn('new CategoryState()',menu)
  freeplay=(ROOT/'source/FreeplayState.hx').read_text()
  self.assertIn('controls.UP_MENU_H || upP',freeplay)
  self.assertIn('controls.DOWN_MENU_H || downP',freeplay)
  self.assertIn('typedChar.length == 0 && anyVisible() && subState == null',freeplay)
  self.assertIn('scrollMotion.reset();',freeplay)
  self.assertIn('FreeplayBrowserLayout.centeredPage',freeplay)
  self.assertIn('LibraryCollectionsSubState', (ROOT/'source/LibraryActionsSubState.hx').read_text())
