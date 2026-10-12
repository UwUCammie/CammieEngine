"""Native HUD markup expires on replacement, without clearing authored formats."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
ROOT = Path(__file__).resolve().parents[2]

class SourceScoreTextTest(unittest.TestCase):
    def test_rank_ranges_follow_the_text_that_created_them(self):
        with tempfile.TemporaryDirectory(prefix="score-markup-", dir=ROOT / "tmp") as folder:
            root = FixturePath(folder)
            text = root / "flixel/text"
            text.mkdir(parents=True)
            (text / "FlxText.hx").write_text(r'''package flixel.text;
class FlxText {
 public var text(default,set):String = "";
 public var formats:Array<Dynamic> = [];
 public function new() {text = "";}
 function set_text(value:String):String return text = value;
 public function addFormat(format:FlxTextFormat, start:Int, end:Int):Void formats.push({format:format,start:start,end:end});
 public function removeFormat(format:FlxTextFormat):Void {
  for (entry in formats.copy()) if (entry.format == format) formats.remove(entry);
 }
}
class FlxTextFormat {
 public var color:Int;
 public function new(color:Int) this.color = color;
}
''', encoding="utf-8")
            (root / "Main.hx").write_text(r'''import flixel.text.FlxText.FlxTextFormat;
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var label = new SourceScoreText();
  var authored = new FlxTextFormat(0xFF44FF44);
  label.addFormat(authored,0,5);
  label.text = "Score: 1,234 | Misses: 0 | Accuracy: 96.42% [FC]\n";
  var start = label.text.indexOf("FC");
  label.applySourceFormat(0xFFF16439,start,start+2);
  check(label.formats.length == 2,"native rank plus authored format");
  var nativeFormat = label.formats[1].format;
  label.text = label.text;
  check(label.formats.length == 2,"same string retains intentional rank colour");
  Reflect.setProperty(label,"text","Score: 1234 | Misses: 0 | Rating: EXCELLENT (96.42%) - FC");
  check(label.formats.length == 1 && label.formats[0].format == authored,"replacement cannot colour unrelated accuracy digits or erase authored formats");
  start = label.text.lastIndexOf("FC");
  label.applySourceFormat(0xFFF16439,start,start+2);
  check(label.formats[1].format == nativeFormat,"unchanged rank reuses its format");
  label.applySourceFormat(0xFFFFFF00,start,start+2);
  check(label.formats.length == 2 && label.formats[1].format.color == 0xFFFFFF00,"rank changes replace exactly one range");
  label.applySourceFormat(0xFFF16439,-1,2);
  check(label.formats.length == 1,"absent rank does not colour from index zero");
  label.applySourceFormat(0xFFF16439,0,9999);
  check(label.formats.length == 1,"invalid range is not added");
  for (i in 0...1000) {
   label.text = "Accuracy: 96.42% [FC]\n";
   label.applySourceFormat(0xFFF16439,17,19);
   label.text = "Rating: EXCELLENT (96.42%) - FC";
  }
  check(label.formats.length == 1,"repeated competing updates never accumulate stale ranges");
  label.applySourceFormat(0xFFF16439,27,29);
  label.text = null;
  check(label.formats.length == 1,"clearing text retires native markup too");
 }
}
''', encoding="utf-8")
            result = subprocess.run([*HAXE_COMMAND,"-cp",str(ROOT / "source"),"-cp",str(root),"--main","Main","--interp"],cwd=ROOT,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__ == "__main__":
    unittest.main()
