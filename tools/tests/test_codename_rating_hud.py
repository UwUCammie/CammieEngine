"""Source ratio formatting and rating-only color range on the actual HUD helper."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

class CodenameRatingHudTest(unittest.TestCase):
    def test_unknown_ratio_color_and_replacement(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        start = source.index('\tfunction updateCodenameRatingHud():Void {')
        end = source.index('\n\tfunction syncCodenameAccuracyHud()', start)
        body = source[start:end]
        main = '''class Label {
 public var text:String=''; public var formats:Array<Dynamic>=[];
 public function new(){}
 public function removeFormat(f:Dynamic) {formats=[for(r in formats)if(r.format!=f)r];}
 public function addFormat(f:Dynamic,start:Int,end:Int) formats.push({format:f,start:start,end:end});
}
class Main {
 var accuracyTxt=new Label(); var curRating:CodenameComboRating=null;
 var codenameAccuracy:Float=-1;
 var codenameRatingFormat:flixel.text.FlxTextFormat=null;
 var codenameRatingFormatColor:Null<Int>=null;
 public function new(){}
''' + body + '''
 static function check(v:Bool,s:String) if(!v)throw s;
 static function main() {
  var game=new Main();game.updateCodenameRatingHud();
  check(game.accuracyTxt.text=='Accuracy:-% - [N/A]'&&game.curRating.rating=='[N/A]','initial unknown accuracy');
  var other=new flixel.text.FlxTextFormat(123);game.accuracyTxt.addFormat(other,0,8);
  game.curRating=new CodenameComboRating(0.7,'CUSTOM',0xFF112233);
  game.codenameAccuracy=.8;game.updateCodenameRatingHud();game.updateCodenameRatingHud();
  check(game.accuracyTxt.text=='Accuracy:80% - CUSTOM','ratio became percent twice');
  check(game.accuracyTxt.formats.length==2,'leaked or removed unrelated format');
  var range=game.accuracyTxt.formats[1];
  check(range.start==game.accuracyTxt.text.length-6&&range.end==game.accuracyTxt.text.length&&range.format.color==0xFF112233,'rating color range');
  game.curRating=new CodenameComboRating(0,'X',0xFFABCDEF);game.codenameAccuracy=.98765;game.updateCodenameRatingHud();
  check(game.accuracyTxt.text=='Accuracy:98.77% - X','source quantize semantics');
  game.accuracyTxt=null;game.updateCodenameRatingHud();
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp', prefix='rating-hud-') as temp:
            base=Path(temp);(base/'flixel/text').mkdir(parents=True)
            (base/'flixel/text/FlxTextFormat.hx').write_text('package flixel.text;class FlxTextFormat {public var color(default,null):Int;public function new(c:Int) color=c;}')
            (base/'Main.hx').write_text(main)
            result=subprocess.run([str(ROOT/'.tools/haxe/haxe'),'-cp',str(ROOT/'source'),'-cp',temp,'-main','Main','--interp'],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
