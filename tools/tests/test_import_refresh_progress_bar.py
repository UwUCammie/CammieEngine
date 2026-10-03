"""The shared refresh overlay polls coordinator status and renders its state."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


STUBS = {
    "flixel/FlxBasic.hx": r'''package flixel;
class FlxBasic {
 public var active:Bool = true;
 public var visible:Bool = true;
 public function new() {}
 public function update(elapsed:Float):Void {}
}''',
    "flixel/Point.hx": r'''package flixel;
class Point {
 public var x:Float; public var y:Float;
 public function new(x:Float=0,y:Float=0) { this.x=x; this.y=y; }
 public function set(x:Float=0,y:Float=0):Void { this.x=x; this.y=y; }
}''',
    "flixel/FlxSprite.hx": r'''package flixel;
class FlxSprite extends FlxBasic {
 public var x:Float=0; public var y:Float=0; public var width:Float=0; public var height:Float=0;
 public var alpha:Float=1; public var color:Int=0; public var scale:Point=new Point(1,1);
 public var origin:Point=new Point(); public var scrollFactor:Point=new Point();
 public function new(?x:Float=0,?y:Float=0) { super(); this.x=x; this.y=y; }
 public function makeGraphic(width:Int,height:Int,color:Int):FlxSprite {
  this.width=width; this.height=height; this.color=color; return this;
 }
 public function setPosition(x:Float=0,y:Float=0):Void { this.x=x; this.y=y; }
}''',
    "flixel/FlxG.hx": r'''package flixel;
class FlxG { public static var width:Int=1280; public static var height:Int=720; }''',
    "flixel/util/FlxColor.hx": r'''package flixel.util;
class FlxColor {
 public static inline var WHITE:Int=0xFFFFFFFF;
 public static function fromRGB(r:Int,g:Int,b:Int,a:Int=255):Int return (a<<24)|(r<<16)|(g<<8)|b;
}''',
    "flixel/text/FlxText.hx": r'''package flixel.text;
import flixel.FlxSprite;
class FlxText extends FlxSprite {
 public var text:String; public var wordWrap:Bool=true;
 public function new(x:Float=0,y:Float=0,width:Float=0,text:String="",size:Int=8) {
  super(x,y); this.width=width; this.text=text;
 }
}''',
    "flixel/group/FlxGroup.hx": r'''package flixel.group;
import flixel.FlxBasic;
class FlxTypedGroup<T:FlxBasic> extends FlxBasic {
 public var members:Array<T>=[];
 public function new(maxSize:Int=0) { super(); }
 public function add(value:T):T { members.push(value); return value; }
 override public function update(elapsed:Float):Void {
  for (member in members) if (member.active) member.update(elapsed);
 }
}''',
    "ImportRefreshManager.hx": r'''class ImportRefreshManager {
 public static var calls:Int=0;
 public static var failNext:Bool=false;
 public static var snapshot:Dynamic={busy:false,label:"",fraction:0.0,complete:false,changed:false,blocked:false};
 public static function browseTick():Dynamic {
  calls++;
  if(failNext) { failNext=false; throw "coordinator unavailable"; }
  return snapshot;
 }
 public static function setStatus(status:Dynamic):Void snapshot=status;
}''',
}


MAIN = r'''class Main {
 static function check(value:Bool,message:String):Void if(!value) throw message;
 static function main():Void {
  var overlay=new ImportRefreshProgressBar();
  check(overlay.active&&!overlay.visible,"overlay must keep polling while hidden");
  overlay.update(0.016);
  check(ImportRefreshManager.calls==1&&!overlay.visible,"idle poll or visibility");

  ImportRefreshManager.setStatus({busy:true,label:"Copying imported mods",fraction:0.375,
   complete:false,changed:false,blocked:false});
  overlay.update(0.016);
  check(overlay.visible&&overlay.active,"busy overlay was hidden or stopped polling");
  check(overlay.statusText.text=="Copying imported mods","coordinator label was lost");
  check(Math.abs(overlay.progressFraction()-0.375)<0.0001
   &&Math.abs(overlay.progressFill.scale.x-0.375)<0.0001,"progress fraction was not drawn");

  var second=new ImportRefreshProgressBar();
  second.update(0.016);
  check(second.visible&&ImportRefreshManager.calls==3,"multiple menu pollers did not share status");

  ImportRefreshManager.setStatus({busy:false,label:"Local changes need review",fraction:0.0,
   complete:false,changed:false,blocked:true});
  overlay.update(0.016);
  check(overlay.visible&&overlay.statusText.text=="Local changes need review",
   "blocked refresh state was not surfaced");

  ImportRefreshManager.setStatus({busy:false,label:"",fraction:1.0,
   complete:true,changed:true,blocked:false});
  overlay.update(0.016);
  check(overlay.visible&&overlay.statusText.text=="Imported mods refreshed",
   "completed refresh did not show a brief confirmation");
  overlay.update(3.0);
  check(!overlay.visible,"completion toast did not dismiss itself");
  var calls=ImportRefreshManager.calls;
  overlay.update(0.016);
  check(!overlay.visible&&ImportRefreshManager.calls==calls+1,
   "hidden overlay stopped polling for later queued work");

  ImportRefreshManager.failNext=true;
  overlay.update(0.016);
  check(overlay.visible&&overlay.statusText.text.indexOf("Import refresh failed:")==0,
   "coordinator failure was hidden from the user");
 }
}'''


class ImportRefreshProgressBarTest(unittest.TestCase):
    def test_overlay_polls_shared_status_and_shows_busy_blocked_and_completion(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "ImportRefreshProgressBar.hx").write_text(
                (ROOT / "source/ImportRefreshProgressBar.hx").read_text()
            , newline='\n')
            for relative, content in STUBS.items():
                target = base / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, newline='\n')
            (base / "Main.hx").write_text(MAIN, newline='\n')
            process = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(base), "--run", "Main"],
                cwd=base, text=True, capture_output=True, timeout=60,
            )
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)


if __name__ == "__main__":
    unittest.main()
