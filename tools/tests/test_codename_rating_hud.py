"""Source ratio formatting and rating-only color range on the actual HUD helper."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
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
 public var text:String=''; public var _formatRanges:Array<Dynamic>=[]; public var edits:Int=0;
 public var formats(get,never):Array<Dynamic>;
 function get_formats() return [for(r in _formatRanges){format:r.format,start:r.range.start,end:r.range.end}];
 public function new(){}
 public function removeFormat(f:Dynamic) {edits++;_formatRanges=[for(r in _formatRanges)if(r.format!=f)r];}
 public function addFormat(f:Dynamic,start:Int,end:Int) {edits++;_formatRanges.push({format:f,range:{start:start,end:end}});}
}
class Main {
 var accuracyTxt=new Label(); var curRating:CodenameComboRating=null;
 var codenameAccuracy:Float=-1;
 var codenameRatingFormat:flixel.text.FlxTextFormat=null;
 var codenameRatingFormatColor:Null<Int>=null;
 var codenameRatingLabel:String=null; var codenameRatingRatio:Float=0;
 var codenameRatingName:String=null; var codenameRatingText:Label=null;
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
  // An unchanged frame must not touch the formats: each edit forces a redraw.
  var edits=game.accuracyTxt.edits;game.updateCodenameRatingHud();game.updateCodenameRatingHud();
  check(game.accuracyTxt.edits==edits&&game.accuracyTxt.text=='Accuracy:98.77% - X','unchanged frame left alone');
  // Anything that changes what is shown still rebuilds it, exactly as before.
  game.accuracyTxt.text='script wrote this';game.updateCodenameRatingHud();
  check(game.accuracyTxt.text=='Accuracy:98.77% - X'&&game.accuracyTxt.edits==edits+2,'foreign text replaced');
  game.accuracyTxt._formatRanges=[];game.updateCodenameRatingHud();
  check(game.accuracyTxt.formats.length==1&&game.accuracyTxt.formats[0].format.color==0xFFABCDEF,'dropped colour range restored');
  game.curRating=new CodenameComboRating(0,'X',0xFF010203);game.updateCodenameRatingHud();
  check(game.accuracyTxt.formats.length==1&&game.accuracyTxt.formats[0].format.color==0xFF010203,'new rating colour applied');
  game.curRating=new CodenameComboRating(0,'LONGER',0xFF010203);game.updateCodenameRatingHud();
  var last=game.accuracyTxt.formats[0];
  check(game.accuracyTxt.text=='Accuracy:98.77% - LONGER'&&last.start==game.accuracyTxt.text.length-6,'new rating name applied');
  game.codenameAccuracy=.5;game.updateCodenameRatingHud();
  check(game.accuracyTxt.text=='Accuracy:50% - LONGER','new ratio applied');
  var replacement=new Label();replacement.text=game.accuracyTxt.text;game.accuracyTxt=replacement;game.updateCodenameRatingHud();
  check(replacement.formats.length==1,'replacement text object receives its colour range');
  game.accuracyTxt=null;game.updateCodenameRatingHud();
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp', prefix='rating-hud-') as temp:
            base=Path(temp);(base/'flixel/text').mkdir(parents=True)
            (base/'flixel/text/FlxTextFormat.hx').write_text('package flixel.text;class FlxTextFormat {public var color(default,null):Int;public function new(c:Int) color=c;}', newline='\n')
            (base/'Main.hx').write_text(main, newline='\n')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',temp,'-main','Main','--interp'],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
