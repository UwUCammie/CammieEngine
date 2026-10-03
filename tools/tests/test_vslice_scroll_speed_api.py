"""Exercise the production V-Slice strumline speed methods without launching audio."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    first_statement_end = source.index(";", start)
    if first_statement_end < opening:
        return source[start:first_statement_end + 1]
    depth = 0
    for position in range(opening, len(source)):
        if source[position] == "{":
            depth += 1
        elif source[position] == "}":
            depth -= 1
            if depth == 0:
                return source[start:position + 1]
    raise AssertionError(marker)


class VSliceScrollSpeedApiTest(unittest.TestCase):
    def test_source_hud_zoom_alias_tracks_native_resting_zoom(self):
        play = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("@:keep public var defaultHUDCameraZoom(get, set):Float;", play)
        getter = method(play, "function get_defaultHUDCameraZoom():Float")
        setter = method(play, "function set_defaultHUDCameraZoom(value:Float):Float")
        fixture = r'''
class Main {
 public var defaultHudZoom:Float=1;
 public var defaultHUDCameraZoom(get,set):Float;
 public function new() {}
__GETTER__
__SETTER__
 public static function main():Void {
  var state=new Main();
  state.defaultHudZoom=1.25;
  if(Reflect.getProperty(state,'defaultHUDCameraZoom')!=1.25) throw 'source read';
  Reflect.setProperty(state,'defaultHUDCameraZoom',1.5);
  if(state.defaultHudZoom!=1.5) throw 'source write';
 }
}
'''.replace("__GETTER__", getter).replace("__SETTER__", setter)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            folder = Path(scratch)
            (folder / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(folder), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_per_line_speed_reset_tween_target_and_invalid_input(self):
        strumline = (ROOT / "source/Strumline.hx").read_text()
        play = (ROOT / "source/PlayState.hx").read_text()
        methods = "\n".join(
            method(strumline, marker) for marker in (
                "function get_scrollSpeed():Float",
                "function set_scrollSpeed(value:Float):Float",
                "public function hasScrollSpeedOverride():Bool",
                "public function resetScrollSpeed(?newScrollSpeed:Null<Float>):Void",
            )
        )
        cancel = method(play, "function cancelVSliceScrollTweens():Void")
        tween = method(play, "function tweenVSliceScrollSpeed(speed:Dynamic")
        fixture = r'''
class FlxEase {
 public static function linear(value:Float):Float return value;
}
class FlxTween {
 public var canceled:Bool=false;
 public function new() {}
 public function cancel():Void canceled=true;
 public static function tween(object:Dynamic, fields:Dynamic, duration:Float, options:Dynamic):FlxTween {
  if(duration<=0) throw 'expected positive tween duration';
  Reflect.setProperty(object,'scrollSpeed',Reflect.field(fields,'scrollSpeed'));
  return new FlxTween();
 }
}
class Strumline {
 public var scrollSpeed(get,set):Float;
 var sourceScrollSpeed:Null<Float>=null;
 public function new() {}
__STRUM_METHODS__
}
class PlayState {
 public static var daScrollSpeed:Float=2;
 public static var SONG:Dynamic={speed:3.0};
 var playerStrums:Strumline=new Strumline();
 var enemyStrums:Strumline=new Strumline();
 var playbackRate:Float=1;
 var vSliceScrollTweens:Array<FlxTween>=[];
 var vSliceScrollTargets:Array<{line:Strumline,speed:Float}>=[];
__CANCEL__
__TWEEN__
 public function new() {}
 public function test():Void {
  check(playerStrums.scrollSpeed==2 && !playerStrums.hasScrollSpeedOverride(),'native default');
  playerStrums.resetScrollSpeed();
  check(playerStrums.scrollSpeed==3 && playerStrums.hasScrollSpeedOverride(),'chart reset');
  playerStrums.scrollSpeed=Math.NaN;
  check(playerStrums.scrollSpeed==3,'invalid setter must preserve speed');
  playerStrums.resetScrollSpeed(2);
  check(playerStrums.scrollSpeed==2,'explicit reset');
  tweenVSliceScrollSpeed(1.1,0,null,['playerStrumline','opponentStrumline']);
  check(playerStrums.scrollSpeed==1.1 && enemyStrums.scrollSpeed==1.1,'two line immediate speed');
  tweenVSliceScrollSpeed(1.2,1.0,null,['playerStrumline']);
  check(playerStrums.scrollSpeed==1.2 && enemyStrums.scrollSpeed==1.1,'selected line tween');
  check(vSliceScrollTargets.length==1 && vSliceScrollTweens.length==1,'source target tracking');
  tweenVSliceScrollSpeed(null,1.0,null,['playerStrumline']);
  check(playerStrums.scrollSpeed==1.2,'invalid source speed must not change line');
 }
 static function check(condition:Bool,label:String):Void if(!condition) throw label;
 static function main():Void new PlayState().test();
}
'''.replace("__STRUM_METHODS__", methods).replace("__CANCEL__", cancel).replace("__TWEEN__", tween)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            folder = Path(scratch)
            (folder / "PlayState.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(folder), "--run", "PlayState"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_source_camera_zoom_direct_and_stage_relative_modes(self):
        play = (ROOT / "source/PlayState.hx").read_text()
        zoom = method(play, "public function tweenCameraZoom(zoom:Float")
        fixture = r'''
class FlxEase {
 public static function linear(value:Float):Float return value;
}
class FlxTween {
 public var canceled:Bool=false;
 public static var lastDuration:Float=0;
 public function new() {}
 public function cancel():Void canceled=true;
 public static function tween(object:Dynamic, fields:Dynamic, duration:Float, options:Dynamic):FlxTween {
  lastDuration=duration;
  Reflect.setProperty(object,'currentCameraZoom',Reflect.field(fields,'currentCameraZoom'));
  return new FlxTween();
 }
}
class Main {
 var curCamZoom:FlxTween;
 var curStage:Dynamic={defaultZoom:0.8};
 var defaultCamZoom:Float=0.75;
 var playbackRate:Float=1;
 var currentCameraZoom:Float=1;
 public function new() {}
 function ensureGameplayCameraBinding():Void {}
__ZOOM__
 static function check(condition:Bool,label:String):Void if(!condition) throw label;
 public static function main():Void {
  var state=new Main();
  state.tweenCameraZoom(1.5,0,false);
  check(Math.abs(state.currentCameraZoom-1.2)<0.00001,'stage relative zoom');
  state.tweenCameraZoom(0.9,2,true);
  check(Math.abs(state.currentCameraZoom-0.9)<0.00001,'direct zoom');
  check(FlxTween.lastDuration==2,'duration is seconds');
  var previous=state.curCamZoom;
  state.tweenCameraZoom(1.1,0,true);
  check(previous.canceled && Math.abs(state.currentCameraZoom-1.1)<0.00001,'cancel previous tween');
  state.tweenCameraZoom(Math.NaN,0,true);
  check(Math.abs(state.currentCameraZoom-1.1)<0.00001,'reject invalid zoom');
 }
}
'''.replace("__ZOOM__", zoom)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            folder = Path(scratch)
            (folder / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(folder), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
