"""Elapsed-time Freeplay hold repeat and centered selection behavior."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import HAXE_COMMAND
ROOT = Path(__file__).resolve().parents[2]
class FreeplayScrollMotionTest(unittest.TestCase):
 def test_scaled_title_keeps_left_anchor_after_text_refresh(self):
  from test_freeplay_random_difficulty import extract_method
  source=(ROOT/'source/FreeplayBrowserRow.hx').read_text(encoding='utf-8')
  draw=extract_method(source,'function drawPresentation(')
  self.assertLess(draw.index('title.text ='),draw.index('title.origin.set(0, 0)'))
  self.assertLess(draw.index('title.text ='),draw.index('title.updateHitbox();'))
  self.assertLess(draw.index('title.updateHitbox();'),draw.index('title.offset.set(0, 0)'))
  self.assertLess(draw.index('title.offset.set(0, 0)'),draw.index('title.origin.set(0, 0)'))
  self.assertIn('if (titleAppearanceChanged) title.updateHitbox();',draw)
  self.assertIn('titleChanged || title.color != titleColor',draw)
  self.assertLess(draw.index('title.color = titleColor;'),draw.index('title.updateHitbox();'))
  self.assertLess(draw.index('title.scale.set('),draw.index('title.updateHitbox();'))
  self.assertEqual(draw.count('title.updateHitbox();'),1)
  self.assertLess(draw.index('title.origin.set(0, 0)'),draw.index('title.setPosition('))
  self.assertIn('title.setPosition(x + 82,',draw)
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
  for(fps in [30,60,144,480,1000]) {
   var motion=new FreeplayCardMotion(); motion.target(24,402,42,false,true);
   motion.target(32,319,82,true);
   check(motion.y==402 && motion.height==42,'target change snapped geometry');
   motion.advance(0.05);
   check(motion.y<402 && motion.y>319 && motion.height>42 && motion.height<82,'missing intermediate transition');
   motion.target(24,360,42,false);
   var from=motion.y;
   motion.advance(0.01);check(motion.y<360 && motion.y>from,'retarget jumped or reversed');
   for(i in 0...fps)motion.advance(1/fps);
   check(motion.y==360 && motion.height==42 && motion.focus==0,'motion did not settle exactly');
  }
  var low=new FreeplayCardMotion();var high=new FreeplayCardMotion();
  low.target(0,0,42,false,true);high.target(0,0,42,false,true);
  low.target(32,319,82,true);high.target(32,319,82,true);
  low.advance(0.1);for(i in 0...48)high.advance(1/480);
  check(Math.abs(low.y-high.y)<0.001 && Math.abs(low.height-high.height)<0.001,'geometry FPS drift');
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
  self.assertNotIn('scrollMotion.offset',freeplay)
  self.assertIn('animateBrowserRows(elapsed)',freeplay)
  self.assertIn('LibraryCollectionsSubState', (ROOT/'source/LibraryActionsSubState.hx').read_text())
