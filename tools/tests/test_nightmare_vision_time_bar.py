"""Execute the shared HUD construction with source and native bar graphics."""
from pathlib import Path
from haxe_test_support import FixturePath as Path, HAXE_COMMAND
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

class NightmareVisionTimeBarTest(unittest.TestCase):
    def test_source_bar_dimensions_text_and_native_fallback(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        start = source.index("\t\tvar sourceTimeHUD = nightmareVisionScripts != null;")
        end = source.index("\n\t\t// old-engine global sprite names", start)
        construction = source[start:end]
        fixture = r'''
class Point { public function new() {} public function set():Void {} }
class Sprite {
 public var x:Float; public var y:Float; public var width:Float; public var height:Float;
 public var cameras:Array<Dynamic>; public var scrollFactor = new Point();
 public function new(x:Float=0,y:Float=0) {this.x=x;this.y=y;}
 public function loadGraphic(graphic:Dynamic):Sprite {
  width=Std.isOfType(graphic,String)?601:graphic.width;
  height=Std.isOfType(graphic,String)?19:graphic.height; return this;
 }
 public function screenCenter(axis:Dynamic):Void x=(1280-width)/2;
}
class Text extends Sprite {
 public var size:Int; public var borderSize:Float;
 public function new(x:Float,y:Float,width:Float,text:String,size:Int) {
  super(x,y);this.width=width;this.size=size;height=size+10;
 }
 public function setFormat(font:String,size:Int,color:Dynamic,align:Dynamic,style:Dynamic,border:Dynamic):Void this.size=size;
}
class Bar extends Sprite {
 public var numDivisions:Int;
 public function new(x:Float,y:Float,direction:Dynamic,width:Int,height:Int,parent:Dynamic,field:String,min:Int,max:Int) {
  super(x,y);this.width=width;this.height=height;
 }
 public function createFilledBar(empty:Dynamic,fill:Dynamic):Void {}
}
class Paths {
 public var usesSharedRatingPrefix:Bool; public var UI_PREFIX='UI/';
 public var selected:String;
 public function new(legacy:Bool) usesSharedRatingPrefix=legacy;
 public function image(key:String):Dynamic {selected=key;return {width:400,height:19};}
}
class FlxG { public static var height=720; public static var width=1280; }
class FlxColor {public static var WHITE=1;public static var BLACK=2;public static var GRAY=3;public static var LIME=4;}
class FlxTextBorderStyle {public static var OUTLINE=1;}
class Main {
 static var X=1; static var CENTER=1; static var LEFT_TO_RIGHT=1;
 var nightmareVisionScripts:Dynamic; var nightmareVisionPaths:Paths;
 var downscroll:Bool; var camHUD:Dynamic;
 var SONG:Dynamic={compatPreserveSongTitle:false,song:'source-song'};
 var songPosBG:Sprite; var songPosBar:Bar; var songName:Text;
 function new(source:Bool,down:Bool,legacy:Bool) {
  nightmareVisionScripts=source?{}:null;downscroll=down;nightmareVisionPaths=new Paths(legacy);
 }
 function build():Void {
CONSTRUCTION
 }
 static function main():Void {
  for (legacy in [true,false]) for (down in [true,false]) {
   var hud=new Main(true,down,legacy);hud.build();
   if(hud.nightmareVisionPaths.selected != (legacy?'timeBar':'UI/timeBar')) throw 'source layout selection';
   if(hud.songPosBG.width!=400 || hud.songPosBar.width!=394 || hud.songPosBar.height!=13) throw 'source fill dimensions';
   if(hud.songPosBar.x!=hud.songPosBG.x+3 || hud.songPosBar.y!=hud.songPosBG.y+3) throw 'source fill inset';
   if(hud.songName.size!=32 || hud.songName.width!=1280 || hud.songName.y!=(down?676:19)) throw 'source timer label';
   if(hud.songPosBG.y!=hud.songName.y+hud.songName.height/4) throw 'source timer baseline';
   // A script can swap a larger decorative border without enlarging the fill.
   hud.songPosBG.loadGraphic({width:416,height:38});
   if(hud.songPosBar.width!=394) throw 'border swap changed source fill';
  }
  var native=new Main(false,false,false);native.build();
  if(native.songPosBG.width!=601 || native.songPosBar.width!=593 || native.songPosBar.height!=11 || native.songName.size!=16) throw 'native HUD changed';
 }
}
'''.replace("CONSTRUCTION", construction).replace("new FlxSprite", "new Sprite").replace("new FlxText", "new Text").replace("new FlxBar", "new Bar")
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder)/"Main.hx").write_text(fixture)
            result=subprocess.run([*HAXE_COMMAND,"-cp",folder,"-main","Main","--interp"],capture_output=True,text=True,cwd=ROOT)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn("for (object in [cast songPosBar, cast songPosBG, cast songName])", source)
        self.assertIn("if (useSongBar && !sourceTimeHUD)", source)

if __name__ == "__main__":
    unittest.main()
