"""Historical NV text preset delegates exact defaults and arguments to Flixel."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from tools.haxe_flixel_math_stubs import write_flixel_point_stub
ROOT=Path(__file__).resolve().parents[2]
class NvTextHelperTest(unittest.TestCase):
    def test_script_defaults_and_explicit_format_forwarding(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            work=FixturePath(directory)
            write_flixel_point_stub(work)
            files={
                'flixel/util/FlxColor.hx': "package flixel.util;abstract FlxColor(Int) from Int to Int {public static inline var WHITE:Int=-1;public static inline var TRANSPARENT:Int=0;}",
                'flixel/text/FlxText.hx': """package flixel.text;
 typedef FlxTextAlign=String;
 enum FlxTextBorderStyle {NONE;OUTLINE;SHADOW;}
 class FlxText {
 public var calls:Array<Array<Dynamic>>=[];public function new(){}
 public function setFormat(f:String,s:Int,c:Int,a:FlxTextAlign,b:FlxTextBorderStyle,bc:Int,e:Bool):FlxText {calls.push([f,s,c,a,b,bc,e]);return this;}
 }
 """,
                'Main.hx': r"""import flixel.text.FlxText;import flixel.text.FlxText.FlxTextBorderStyle;
 class Main {
 static function check(ok:Bool,label:String)if(!ok)throw label;
 static function main(){
 var txt=new FlxText();var interp=new NightmareVisionScriptInterp({});
 interp.variables.set('setTxtFormat',NightmareVisionTextHelpers.setTxtFormat);
 interp.variables.set('txt',txt);interp.variables.set('outline',FlxTextBorderStyle.OUTLINE);
 var parser=new NightmareVisionScriptParser();
 interp.execute(parser.parseString("setTxtFormat(txt);setTxtFormat(txt,'native/font.ttf',32,0xFFABCDEF,'center',outline,0xFF123456,false);setTxtFormat(txt,null,14);"));
 check(txt.calls.length==3,'all calls dispatched');var a=txt.calls[0];
 check(a[0]==null&&a[1]==8&&a[2]==-1&&a[3]==null&&a[4]==null&&a[5]==0&&a[6]==true,'historical defaults');
 var b=txt.calls[1];check(b[0]=='native/font.ttf'&&b[1]==32&&b[2]==0xFFABCDEF&&b[3]=='center'&&b[4]==OUTLINE&&b[5]==0xFF123456&&b[6]==false,'explicit native values');
 check(txt.calls[2][0]==null&&txt.calls[2][1]==14&&txt.calls[2][2]==-1&&txt.calls[2][6]==true,'partial arguments retain defaults');interp.release();
 }
 }
 """}
            for name,value in files.items():
                p=work/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value)
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',str(work),'--main','Main','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=45)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        seed=(ROOT/'source/PlayState.hx').read_text()
        common=seed.split('public static function seedNightmareVisionCommon(',1)[1].split('public static function ',1)[0]
        self.assertIn("'setTxtFormat' => NightmareVisionTextHelpers.setTxtFormat",common)
if __name__=='__main__':unittest.main()
