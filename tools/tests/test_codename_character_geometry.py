"""Execute Character's live Codename draw and screen geometry methods."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def method(source, marker):
    start = source.index(marker)
    brace = source.index('{', start)
    depth = 0
    for at in range(brace, len(source)):
        depth += (source[at] == '{') - (source[at] == '}')
        if depth == 0:
            return source[start:at + 1]
    raise AssertionError(marker)


class CodenameCharacterGeometryTest(unittest.TestCase):
    def test_screen_shift_draw_reversal_bounds_and_restore(self):
        source = (ROOT / 'source/Character.hx').read_text()
        methods = '\n'.join(method(source, marker) for marker in (
            '\toverride public function getScreenPosition(',
            '\toverride function prepareDrawMatrix(',
            '\toverride public function isSimpleRender(',
            '\t@:keep public function isFlippedOffsets(',
            '\toverride public function getScreenBounds(',
            '\tfunction codenameRestoreDraw(',
            '\toverride public function draw(',
        ))
        fixture = '''class FlxCamera {}
class FlxAngle { public static inline var TO_RAD:Float=0.017453292519943295; }
class FlxMatrix {
 public var tx:Float=0; public var ty:Float=0;
 public function new() {}
 public function translate(x:Float,y:Float):Void {tx+=x;ty+=y;}
 public function scale(x:Float,y:Float):Void {tx*=x;ty*=y;}
 public function rotateWithTrig(c:Float,s:Float):Void {
  var old=tx; tx=old*c-ty*s; ty=old*s+ty*c;
 }
}
class FlxPoint {
 public var x:Float; public var y:Float;
 public function new(x:Float=0,y:Float=0) {this.x=x;this.y=y;}
 public function add(x:Float,y:Float):FlxPoint {this.x+=x;this.y+=y;return this;}
 public function set(x:Float,y:Float):FlxPoint {this.x=x;this.y=y;return this;}
}
class FlxRect {
 public var x:Float=0; public var y:Float=0; public var width:Float=0;
 public function new() {}
}
class CodenameCharacterEvent { public function new() {} }
class PlayState { public static var instance:Dynamic=null; }
class FakeSprite {
 public var x:Float=100; public var y:Float=200; public var scale=new FlxPoint(2,3);
 public var angle:Float=0;
 public var flipX=false; public var offset=new FlxPoint();
 public var throwDraw=false; public var lastDraw:Dynamic=null;
 public var throwBounds=false;
 public var lastBoundsScaleX:Float=0;
 public function new() {}
 public function getScreenPosition(?result:FlxPoint,?camera:FlxCamera):FlxPoint {
  if(result==null) result=new FlxPoint(); return result.set(x,y);
 }
 public function getScreenBounds(?rect:FlxRect,?camera:FlxCamera):FlxRect {
  lastBoundsScaleX=scale.x;
  if(throwBounds) throw 'bounds failure';
  if(rect==null) rect=new FlxRect();
  var matrix=new FlxMatrix(); prepareDrawMatrix(matrix,camera);
  rect.x=matrix.tx; rect.y=matrix.ty;
  rect.width=Math.abs(scale.x)*10;
  return rect;
 }
 public function prepareDrawMatrix(matrix:FlxMatrix,camera:FlxCamera):Void {
  matrix.scale(scale.x,scale.y);
  matrix.translate(x-offset.x,y-offset.y);
 }
 public function isSimpleRender(?camera:FlxCamera):Bool return true;
 public function draw():Void {
  var bounds=getScreenBounds();
  lastDraw={x:x,y:y,flipX:flipX,scaleX:scale.x,boundsX:bounds.x,
   boundsY:bounds.y,boundsScaleX:lastBoundsScaleX};
  if(throwDraw) throw 'draw failure';
 }
}
class Character extends FakeSprite {
 public var codenameLiveDefinition:Dynamic={};
 public var codenameRuntime:Dynamic;
 public var log:Array<String>=[];
 public var frameOffset=new FlxPoint(); public var extraOffset=new FlxPoint();
 public var frameOffsetAngle:Null<Float>=null;
 public var ghostDraw=false; public var debugMode=false;
 public var isPlayer=true; public var playerOffsets=false;
 var codenameBaseFlipped=false; var codenameReverseDrawProcedure=false;
 public function new() {
  super(); var self=this;
  codenameRuntime={event:function(name:String,_e:Dynamic):Dynamic {
   self.log.push(name); return _e;
  }};
 }
 public function hxcBaseScreenPosition(?result:FlxPoint,?camera:FlxCamera):FlxPoint
  return super.getScreenPosition(result,camera);
''' + methods + '''
}
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main():Void {
  var actor=new Character();
  actor.frameOffset.set(7,-4); actor.offset.set(-3,-5);
  actor.extraOffset.set(11,13);
  var screen=actor.getScreenPosition();
  check(screen.x==100 && screen.y==200,'frameOffset changed script-visible screen position');
  check(!actor.isSimpleRender(),'live frameOffset skipped complex matrix path');
  check(actor.isFlippedOffsets(),'player/offset mismatch not reversed');
  actor.draw();
  check(actor.log.join(',')=='draw,postDraw','draw script callback order');
  check(actor.lastDraw.x==111 && actor.lastDraw.y==213 && actor.lastDraw.flipX
   && actor.lastDraw.scaleX==-2,'temporary draw geometry');
  check(actor.lastDraw.boundsScaleX==2 && actor.lastDraw.boundsX==100
   && actor.lastDraw.boundsY==230,'bounds compensation/frame/global offsets');
  check(actor.x==100 && actor.y==200 && !actor.flipX && actor.scale.x==2
   && actor.getScreenPosition().x==100,'draw did not restore actor');
  actor.ghostDraw=true; actor.log.resize(0); actor.draw();
  check(actor.lastDraw.x==100 && actor.lastDraw.y==200 && actor.lastDraw.flipX
   && actor.lastDraw.scaleX==-2 && actor.x==100 && actor.y==200,
   'ghost draw applied extraOffset or failed to restore flip');
  actor.ghostDraw=false; actor.throwDraw=true; actor.log.resize(0);
  var thrown=false;
  try actor.draw() catch (_:Dynamic) thrown=true;
  check(thrown && actor.log.join(',')=='draw' && actor.x==100 && actor.y==200
   && !actor.flipX && actor.scale.x==2,'thrown draw leaked temporary state');
  actor.throwDraw=false; actor.throwBounds=true; actor.log.resize(0);
  thrown=false;
  try actor.draw() catch (_:Dynamic) thrown=true;
  check(thrown && actor.x==100 && actor.y==200 && !actor.flipX && actor.scale.x==2,
   'thrown bounds leaked temporary reversal');
  actor.throwBounds=false; actor.isPlayer=false; actor.flipX=true;
  check(actor.isFlippedOffsets(),'runtime flip difference not reversed');
  actor.draw();
  check(!actor.lastDraw.flipX && actor.flipX && actor.scale.x==2,
   'runtime flip reversal not restored');
  actor.codenameLiveDefinition=null; actor.log.resize(0);
  actor.draw();
  check(actor.log.length==0 && actor.lastDraw.x==100 && actor.lastDraw.y==200
   && actor.lastDraw.scaleX==2 && actor.getScreenPosition().x==100
   && actor.isSimpleRender(),
   'non-Codename render geometry changed');
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as work:
            work = Path(work)
            (work / 'Main.hx').write_text(fixture, newline='\n')
            # The extracted draw method only needs these smoke hooks. Adding the
            # whole source classpath resolves the production harness instead,
            # which pulls Flixel and the complete Character dependency graph
            # into this deliberately renderer-free fixture.
            (work / 'RuntimeSmokeHarness.hx').write_text('''class RuntimeSmokeHarness {
 public static function profileEnabled():Bool return false;
 public static function profileSection(_name:String,_seconds:Float):Void {}
}''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', work,
                                     '--run', 'Main'], cwd=ROOT,
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
