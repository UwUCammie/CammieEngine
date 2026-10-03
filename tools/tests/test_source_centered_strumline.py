"""Centered source receptors retain geometry through resize and reset."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def method(source, marker):
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for end in range(brace, len(source)):
        if source[end] == "{":
            depth += 1
        elif source[end] == "}":
            depth -= 1
            if depth == 0:
                return source[start:end + 1]
    raise AssertionError(marker)


class SourceCenteredStrumlineTest(unittest.TestCase):
    def test_native_reset_centers_each_frame_without_legacy_mania_shift(self):
        source = (ROOT / "source/Strumline.hx").read_text()
        fixture = '''class Note {
 public static var swagWidth:Float=112;
 public static var NOTE_AMOUNT:Int=6;
}
class StrumNote {
 public var ID:Int; public var x:Float=0; public var y:Float=0;
 public var width:Float; public var height:Float; public var pendingWidth:Float;
 public function new(id:Int,w:Float,h:Float) {
  ID=id; width=w; pendingWidth=w; height=h;
 }
 public function resetStrumSize():Void width=pendingWidth;
}
class Line {
 public var x:Float=0; public var y:Float=0; public var ID:Int=0;
 public var sourceStrumScale:Float=1; public var noteSpacing:Float=1;
 public var centerReceptors:Bool=false;
 public var members:Array<StrumNote>=[];
 public function new() {}
 function forEach(fn:StrumNote->Void):Void for(s in members) fn(s);
''' + method(source, "\tpublic function resetStrums()") + "\n" + method(
            source, "\tpublic function setCenteredLayout(") + '''
}
class Main {
 static function close(a:Float,b:Float):Void if(Math.abs(a-b)>0.0001)throw a+" != "+b;
 static function main():Void {
  var line=new Line();
  for(i in 0...6) line.members.push(new StrumNote(i,80+i*3,100+i*2));
  for(field in 0...4) for(down in [false,true]) {
   var cx=NightmareVisionPlayfieldLayout.centerX(field,6,1280,112);
   var cy=NightmareVisionPlayfieldLayout.receptorCenterY(720,112,down);
   line.setCenteredLayout(cx,cy);
   for(s in line.members) {
    close(s.x+s.width/2,NightmareVisionPlayfieldLayout.receptorCenterX(field,s.ID,6,1280,112));
    close(s.y+s.height/2,cy);
   }
   line.x+=19; line.y+=7;
   for(s in line.members) s.pendingWidth+=5;
   line.resetStrums();
   for(s in line.members) {
    close(s.x+s.width/2,NightmareVisionPlayfieldLayout.receptorCenterX(field,s.ID,6,1280,112)+19);
    close(s.y+s.height/2,cy+7);
   }
  }
  // Ordinary two-bank charts retain their established top-left placement.
  line.centerReceptors=false; Note.NOTE_AMOUNT=4; line.x=92; line.y=50;
  line.resetStrums();
  for(s in line.members) {close(s.x,92+112*s.ID); close(s.y,50);}
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temporary:
            root = Path(temporary)
            (root / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(root),
                 "--run", "Main"], cwd=ROOT, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
