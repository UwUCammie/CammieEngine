"""Pin Codename line geometry to its native receptor placement formula."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameStrumlineLayoutTest(unittest.TestCase):
    def test_source_line_position_size_spacing_and_visibility(self):
        fixture = r'''
class Main {
 static function check(ok:Bool,message:String):Void if(!ok)throw message;
 static function close(actual:Float,expected:Float,message:String):Void
  if(Math.abs(actual-expected)>0.00001)throw message+': '+actual+' != '+expected;
 static function main():Void {
  var opponent:Dynamic={type:0,keyCount:4,strumLinePos:0.25,strumPos:[0,50],
   strumScale:1,strumSpacing:1,visible:true};
  var left=CodenameStrumlineLayout.resolve(opponent,1280,50,112,4);
  close(left.x,96,'type 0 normalized bank start');
  close(left.y,50,'authored y placement');
  close(left.spacing,1,'default spacing');
  close(left.scale,1,'default scale');
  check(left.visible && left.keyCount==4,'default line presentation');

  var player:Dynamic={type:1,keyCount:4,strumLinePos:0.75,strumPos:[0,50],
   strumScale:1,strumSpacing:1,visible:true};
  var right=CodenameStrumlineLayout.resolve(player,1280,50,112,4);
  close(right.x,736,'type 1 normalized bank start');

  var custom:Dynamic={type:2,keyCount:6,strumLinePos:0.25,strumPos:[250,90],
   strumScale:0.5,strumSpacing:2,visible:false};
  var authored=CodenameStrumlineLayout.resolve(custom,1280,50,112,4);
  close(authored.x,250,'nonzero strumPos x is absolute');
  close(authored.y,90,'strumPos y is direct');
  close(authored.spacing,2,'authored spacing');
  close(authored.scale,0.5,'authored receptor scale');
  check(!authored.visible && authored.keyCount==6,
   'hidden state and full authored lane count must survive the host lane limit');

  custom.strumPos=[0,90];
  var normalized=CodenameStrumlineLayout.resolve(custom,1280,50,112,4);
  close(normalized.x,12,'zero strumPos x uses the full authored key count and scale');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            folder = Path(work)
            (folder / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", str(folder), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
