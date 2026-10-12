"""Host browser density, filtered identity and safe label bounds."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]

class BrowserLayoutTest(unittest.TestCase):
    def test_dense_page_boundaries_and_filter_identity(self):
        fixture = r'''class Main {
 static function check(ok:Bool, message:String) {if(!ok) throw message;}
 static function main() {
  var entries=[for(i in 0...1300) i];
  for (height in [480,720,1080]) {
   var capacity=FreeplayBrowserLayout.capacity(height);
   for (selected in [0,1,650,1298,1299]) {
    var page=FreeplayBrowserLayout.page(entries,selected,height);
    check(page.length==capacity,"page must fill at both boundaries");
    check(page.indexOf(selected)>=0,"selected chart absent");
    check(FreeplayBrowserLayout.rowY(page.length,page.indexOf(selected))<=height-84,"footer overlap");
   }
  }
  check(FreeplayBrowserLayout.capacity(720)==11,"expected eleven rows with one expanded selection");
  check(FreeplayBrowserLayout.rowY(1,0)-FreeplayBrowserLayout.rowY(0,0)==FreeplayBrowserLayout.SELECTED_HEIGHT,"selected row not expanded");
  check(FreeplayBrowserLayout.rowY(2,0)-FreeplayBrowserLayout.rowY(1,0)==FreeplayBrowserLayout.ROW_HEIGHT,"unselected row not compact");
  var filtered=[3,33,503];
  check(FreeplayBrowserLayout.page(filtered,33,720).join(",")=="3,33,503","filtered indexes changed");
  check(FreeplayBrowserLayout.page(filtered,4,720).length==0,"hidden selection created rows");
  check(FreeplayBrowserLayout.page([],0,720).length==0,"empty view created rows");
  check(FreeplayBrowserLayout.label("Short",8)=="Short","short label changed");
  check(FreeplayBrowserLayout.label("A very long title",10)=="A very ...","long label unbounded");
  check(FreeplayBrowserLayout.label("line\nnext\rtitle",80)=="line next title","multiline row");
  Sys.println("browser-layout-ok");
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            Path(folder,'Main.hx').write_text(fixture)
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',folder,'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('browser-layout-ok',result.stdout)
