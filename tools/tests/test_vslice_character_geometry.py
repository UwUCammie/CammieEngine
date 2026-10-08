"""Execute the character render path against V-Slice's scaled offset convention."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for position in range(opening, len(source)):
        if source[position] == "{":
            depth += 1
        elif source[position] == "}":
            depth -= 1
            if depth == 0:
                return source[start : position + 1]
    raise AssertionError(marker)


class VSliceCharacterGeometryTest(unittest.TestCase):
    def test_existing_import_snapshots_global_offsets_before_stage_placement(self):
        source = (ROOT / "source/Character.hx").read_text()
        capture = method(source, "\tfunction captureLegacyVSliceGlobalOffsets(")
        self.assertIn('captureLegacyVSliceGlobalOffsets();', source)
        fixture = '''
class Character {
 public var vSliceBaseFrames:Dynamic;
 public var vSliceGlobalOffsetsAuthored=false;
 public var vSliceGlobalOffsetX:Float=0;
 public var vSliceGlobalOffsetY:Float=0;
 public var playerOffsetX:Int=0;
 public var playerOffsetY:Int=0;
 public function new(imported:Bool) vSliceBaseFrames=imported ? {} : null;
 CAPTURE
 public function init():Void captureLegacyVSliceGlobalOffsets();
}
class Main {
 static function main():Void {
  var legacy=new Character(true);
  legacy.playerOffsetX=17;legacy.playerOffsetY=14;legacy.init();
  legacy.playerOffsetX=900;legacy.playerOffsetY=800;
  if (legacy.vSliceGlobalOffsetX!=17 || legacy.vSliceGlobalOffsetY!=14)
   throw 'legacy CharacterData offsets changed with stage placement';
  var current=new Character(true);
  current.vSliceGlobalOffsetsAuthored=true;
  current.vSliceGlobalOffsetX=-25;current.vSliceGlobalOffsetY=-20;
  current.playerOffsetX=100;current.init();
  if (current.vSliceGlobalOffsetX!=-25 || current.vSliceGlobalOffsetY!=-20)
   throw 'explicit source offsets were overwritten';
  var ordinary=new Character(false);
  ordinary.playerOffsetX=17;ordinary.init();
  if (ordinary.vSliceGlobalOffsetX!=0) throw 'non-V-Slice character changed';
 }
}
'''.replace('CAPTURE', capture)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            folder = Path(scratch)
            (folder / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(folder), '--run', 'Main'],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_opening_idle_hitbox_precedes_stage_feet_anchor(self):
        source = (ROOT / "source/Character.hx").read_text()
        start = source.index("\t\tdance();\n", source.index("imageFile = PsychCharacterImage.resolve"))
        end = source.index("\n\t\tif (codenameCharacterMeta", start)
        opening = source[start:end]
        fixture = '''
class Character {
 public var vSliceBaseFrames:Dynamic;
 public var width:Float=935;
 public var height:Float=943;
 public var x:Float=0;
 public var y:Float=0;
 public var animation:String='singDOWN';
 public function new(imported:Bool) vSliceBaseFrames=imported ? {} : null;
 public function dance():Void animation='idle';
 public function markDeathConstructionStage(_stage:String):Void {}
 public function updateHitbox():Void {
  if (animation=='idle') { width=581; height=918; }
 }
 public function open():Void {
__OPENING__
 }
 public function place(feetX:Float,feetY:Float):Void {
  x=feetX-width/2;y=feetY-height;
 }
}
class Main {
 static function check(ok:Bool,why:String):Void if(!ok) throw why;
 static function main():Void {
  var imported=new Character(true);
  imported.open();imported.place(800,345);
  check(imported.width==581 && imported.height==918,'idle hitbox was not restored');
  check(imported.x==509.5 && imported.y==-573,'stage feet anchor used sing frame');
  var singLeftX=imported.x-VSliceCharacterGeometry.screenShift(291,0,1);
  check(singLeftX==218.5,'authored singLEFT offset moved stage anchor');
  var ordinary=new Character(false);
  ordinary.open();ordinary.place(800,345);
  check(ordinary.width==935 && ordinary.x==332.5,'non-V-Slice sizing changed');
 }
}
'''.replace('__OPENING__', opening)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            folder = Path(scratch)
            (folder / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(folder),
                 '--run', 'Main'], cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_scaled_direction_offsets_preserve_hitbox_base_and_trim(self):
        source = (ROOT / "source/Character.hx").read_text()
        methods = "\n".join(method(source, marker) for marker in (
            "\tpublic function hxcBaseScreenPosition(",
            "\tfunction applyVSliceScreenOffset(",
            "\toverride public function getScreenPosition(",
            "\tpublic function getCurrentAnimationOffset(",
            "\tpublic function getCurrentGlobalOffset(",
            "\tpublic function playAnim(",
        )).replace("[AnimName, Force, false, Reversed]", "[cast AnimName, Force, false, Reversed]")
        fixture = """
class FlxCamera {}
class FlxPoint {
  public var x:Float;
  public var y:Float;
  public function new(x:Float = 0, y:Float = 0) { this.x = x; this.y = y; }
  public function set(x:Float, y:Float):FlxPoint { this.x = x; this.y = y; return this; }
  public function add(x:Float, y:Float):FlxPoint { this.x += x; this.y += y; return this; }
  public function subtract(point:FlxPoint):FlxPoint { x -= point.x; y -= point.y; return this; }
}
class FakeAnim {
  public var name:String;
  public function new(name:String) this.name = name;
}
class FakeAnimation {
  public var curAnim:FakeAnim;
  public function new() {}
  public function exists(_name:String):Bool return true;
  public function play(name:String, force:Bool, reversed:Bool, frame:Int):Void curAnim = new FakeAnim(name);
}
class CodenameCharacterEvent {
  public var animName:String;
  public var force:Null<Bool>;
  public var reverse:Bool;
  public var startingFrame:Int;
  public var context:Dynamic;
  public var cancelled:Bool = false;
  public function new() {}
}
class Conductor { public static var songPosition:Float = 0; }
class PlayState { public static var instance:Dynamic = null; }
// The separately verified NV Stage channel must remain inactive for V-Slice.
class NightmareVisionFunkinSpriteAnimation {
  public static function transformOffset(sprite:Dynamic,input:FlxPoint,base:FlxPoint,output:FlxPoint):FlxPoint
    throw 'NV Stage offsets unexpectedly entered the V-Slice fixture';
}
class FakePlayState {
  public function new() {}
  public function sourceNoteTimingMode():Int return 0;
  public function dispatchHxcCharacterScreenPosition(actor:Character, result:FlxPoint,
    camera:FlxCamera):FlxPoint {
    // Translated super.getScreenPosition restarts from the native Bopper base.
    var base = actor.hxcBaseScreenPosition(result, camera);
    base.x += 5;
    return base;
  }
}
class FakeSprite {
  public var x:Float = 100;
  public var y:Float = 200;
  public var width:Float = 100;
  public var height:Float = 200;
  public var frameWidth:Float = 100;
  public var frameHeight:Float = 200;
  public var scale:FlxPoint = new FlxPoint(1, 1);
  public var offset:FlxPoint = new FlxPoint();
  public function new() {}
  public function getScreenPosition(?result:FlxPoint, ?camera:FlxCamera):FlxPoint {
    if (result == null) result = new FlxPoint();
    return result.set(x, y);
  }
  public function updateHitbox():Void {
    width = Math.abs(scale.x) * frameWidth;
    height = Math.abs(scale.y) * frameHeight;
    offset.set(-0.5 * (width - frameWidth), -0.5 * (height - frameHeight));
  }
}
class Character extends FakeSprite {
  var sourceStageAnimOffset:Null<FlxPoint> = null;
  var sourceStageOffsetBase:Null<FlxPoint> = null;
  var sourceStageOffsetScratch:Null<FlxPoint> = null;
  public var vSliceBaseFrames:Dynamic;
  public var animation:FakeAnimation = new FakeAnimation();
  public var canPlayAnimations:Bool = true;
  public var animOffsets:Map<String, Array<Dynamic>> = [];
  public var playerOffsetX:Int = 12;
  public var playerOffsetY:Int = -8;
  public var vSliceGlobalOffsetX:Float = 12;
  public var vSliceGlobalOffsetY:Float = -8;
  public var isDie:Bool = false;
  public var specialAnim:Bool = false;
  var sourceDanceNightmare:Bool = false;
  public var likeGf:Bool = false;
  public var debugMode:Bool = false;
  public var frameOffset:FlxPoint = new FlxPoint();
  public var globalOffset:FlxPoint = new FlxPoint();
  public var isPlayer:Bool = false;
  public var playerOffsets:Bool = false;
  public function codenameApplyGlobalOffset():Void {
    offset.set(globalOffset.x * (isPlayer != playerOffsets ? 1 : -1), -globalOffset.y);
  }
  public var danced:Bool = false;
  public var codenameLiveDefinition:Dynamic = null;
  public var codenameVisualBuilding:Bool = false;
  public var codenameBuildingAnimations:Array<Dynamic> = null;
  public var codenameRuntime:Dynamic = null;
  public var codenameAnimationContext:Dynamic = null;
  public var codenamePendingForce:Null<Bool> = null;
  public var codenameHasPendingForce:Bool = false;
  public var lastAnimContext:Dynamic = null;
  public var lastHit:Float = 0;
  public var codenameAnimationLock:Bool = false;
  public function applyVSliceAnimationAsset(name:String):Void {}
  public function getCurrentAnimation():String return animation.curAnim == null ? '' : animation.curAnim.name;
""" + methods + """
}
class Main {
  static function close(actual:Float, expected:Float, context:String):Void {
    if (Math.abs(actual - expected) > 0.0001) throw context + ': ' + actual + ' != ' + expected;
  }
  static function check(actor:Character, name:String, animX:Float, animY:Float,
    trimX:Float, trimY:Float, context:String):Void {
    actor.playAnim(name);
    var baseX = -0.5 * (actor.width - actor.frameWidth);
    var baseY = -0.5 * (actor.height - actor.frameHeight);
    close(actor.offset.x, baseX, context + ' base x');
    close(actor.offset.y, baseY, context + ' base y');
    var screen = actor.getScreenPosition();
    // FlxSprite draw subtracts its hitbox offset; Sparrow adds the frame trim.
    var renderedX = screen.x - actor.offset.x + trimX;
    var renderedY = screen.y - actor.offset.y + trimY;
    close(renderedX, actor.x - baseX - (animX - actor.vSliceGlobalOffsetX) * actor.scale.x + trimX, context + ' rendered x');
    close(renderedY, actor.y - baseY - (animY - actor.vSliceGlobalOffsetY) * actor.scale.y + trimY, context + ' rendered y');
  }
  static function main() {
    for (scale in [1.05, 1.9]) {
      var actor = new Character();
      actor.vSliceBaseFrames = {};
      actor.scale.set(scale, scale);
      actor.updateHitbox();
      // Stage.addCharacter places the feet, then BaseCharacter.setScale
      // reapplies CharacterData.globalOffsets to the world position.
      actor.x = 500 - actor.width / 2 + actor.playerOffsetX;
      actor.y = 700 - actor.height + actor.playerOffsetY;
      // Repositioning may edit native slot placement after import. It must not
      // replace V-Slice CharacterData.globalOffsets used by animation drawing.
      actor.playerOffsetX = 88;
      actor.playerOffsetY = 61;
      close(actor.getCurrentGlobalOffset(0), 12, 'authored global x ' + scale);
      close(actor.getCurrentGlobalOffset(1), -8, 'authored global y ' + scale);
      actor.animOffsets.set('idle', [0, 0]);
      actor.animOffsets.set('singLEFT', [20, -30]);
      actor.animOffsets.set('singDOWN', [-13, 14]);
      actor.animOffsets.set('singUP', [7, 35]);
      actor.animOffsets.set('singRIGHT', [-25, -9]);
      check(actor, 'idle', 0, 0, 0, 0, 'idle ' + scale);
      check(actor, 'singLEFT', 20, -30, 4, 9, 'left ' + scale);
      check(actor, 'singDOWN', -13, 14, 11, 3, 'down ' + scale);
      check(actor, 'singUP', 7, 35, 2, 17, 'up ' + scale);
      check(actor, 'singRIGHT', -25, -9, 9, 6, 'right ' + scale);
      var base = actor.hxcBaseScreenPosition();
      close(base.x, 500 - actor.width / 2 + 12 - (-25 - 12) * scale,
        'stage placement plus Bopper global x ' + scale);
      close(base.y, 700 - actor.height - 8 - (-9 + 8) * scale,
        'stage placement plus Bopper global y ' + scale);
      PlayState.instance = new FakePlayState();
      var hooked = actor.getScreenPosition();
      close(hooked.x, base.x + 5, 'HXC super applied base once ' + scale);
      close(hooked.y, base.y, 'HXC super kept base y ' + scale);
      PlayState.instance = null;
    }
    var legacy = new Character();
    legacy.animOffsets.set('singLEFT', [20, -30]);
    legacy.playAnim('singLEFT');
    close(legacy.offset.x, 20, 'legacy x');
    close(legacy.offset.y, -30, 'legacy y');
  }
}
"""
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(fixture, newline='\n')
            env = os.environ.copy()
            env["TMPDIR"] = folder
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr + "\n" +
                         "\n".join(f"{line}: {text}" for line, text in enumerate(fixture.splitlines(), 1)
                                   if 98 <= line <= 110))


if __name__ == "__main__":
    unittest.main()
