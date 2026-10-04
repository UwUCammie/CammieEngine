"""Pin fast scene-transition duration scaling and Flixel handoff ordering."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class SceneTransitionTimingTest(unittest.TestCase):
    def test_opt_in_clones_durations_and_preserves_transition_completion_flow(self):
        helper = (ROOT / "source/SceneTransitionTiming.hx").read_text(encoding="utf-8")
        music_beat_state = (ROOT / "source/MusicBeatState.hx").read_text(encoding="utf-8")
        transition_methods = "\n".join(
            extract_method(music_beat_state, marker)
            for marker in (
                "override public function transitionIn()",
                "override public function transitionOut(?onExit:Void->Void)",
            )
        )

        fixture = r'''import flixel.addons.transition.TransitionData;
import flixel.math.FlxPoint;
import flixel.math.FlxRect;

class TransitionTimingMain {
  static function check(value:Bool, message:String):Void {
    if (!value) throw message;
  }

  static function close(actual:Float, expected:Float):Bool
    return Math.abs(actual - expected) < 0.0000001;

  static function sourceTransition():TransitionData {
    var data = new TransitionData('fade', 0xFF000000, 0.9,
      new FlxPoint(0, 1), {asset:'diamond', width:32, height:32, frameRate:48},
      new FlxRect(1, 2, 300, 200), 'top');
    data.tweenOptions = {ease:'linear', onComplete:'authored'};
    return data;
  }

  static function main():Void {
    var data = sourceTransition();
    var options = data.tweenOptions;
    var authoredCallback = Reflect.field(options, 'onComplete');
    var state = new MusicBeatState(data, data);

    OptionsHandler.options = {fastSceneTransitions:false};
    state.transitionIn();
    check(state.seenIn == data && close(state.seenIn.duration, 0.9),
      'disabled option changed the transition data');
    check(state.transIn == data, 'disabled transition reference was not retained');

    OptionsHandler.options = {fastSceneTransitions:true};
    state.transitionIn();
    var incomingCopy = state.seenIn;
    check(incomingCopy != data && close(incomingCopy.duration, 0.3),
      'incoming transition did not use one third of its authored duration');
    check(state.transIn == data && close(data.duration, 0.9),
      'incoming scaling mutated or retained the shared default data');
    check(incomingCopy.direction != data.direction && incomingCopy.region != data.region,
      'scaled transition aliases mutable geometry from its default');
    check(incomingCopy.tileData == data.tileData,
      'scaled transition changed its visual asset');
    check(incomingCopy.tweenOptions != options
      && Reflect.field(incomingCopy.tweenOptions, 'onComplete') == authoredCallback,
      'scaled transition did not preserve tween options in a private object');

    // Reusing the same shared TransitionData must keep scaling at one third.
    state.transitionIn();
    check(close(state.seenIn.duration, 0.3) && close(data.duration, 0.9),
      'repeated transition accumulated duration scaling');

    state.events = [];
    var callbackOrder:Array<String> = [];
    state.transitionOut(function():Void callbackOrder.push('switch'));
    var outgoingCopy = state.seenOut;
    check(outgoingCopy != data && close(outgoingCopy.duration, 0.3),
      'outgoing transition did not use one third of its authored duration');
    check(state.transOut == data && close(data.duration, 0.9),
      'outgoing scaling mutated or retained the shared default data');
    check(callbackOrder.length == 0,
      'state-switch callback ran before the transition completed');
    check(state.events.join(',') == 'out-start,tween-started',
      'outgoing transition setup order changed');
    state.completeOutgoingTransition();
    check(callbackOrder.join(',') == 'switch',
      'state-switch callback was lost or invoked more than once');
    check(state.events.join(',') == 'out-start,tween-started,out-finished,callback-return',
      'completion callback order changed');
    check(Reflect.field(options, 'onComplete') == authoredCallback,
      'Flixel callback setup mutated the shared default tween options');

    // The temporary field swap is restored even if Flixel throws while making
    // its transition substate.
    state.throwIn = true;
    try {
      state.transitionIn();
      throw 'incoming failure was not propagated';
    } catch (error:Dynamic) {
      check(Std.string(error) == 'expected transition creation failure',
        'incoming transition changed exception semantics: ' + Std.string(error));
    }
    check(state.transIn == data, 'incoming error retained temporary transition data');
    state.throwOut = true;
    try {
      state.transitionOut(function():Void callbackOrder.push('unexpected'));
      throw 'outgoing failure was not propagated';
    } catch (error:Dynamic) {
      check(Std.string(error) == 'expected transition creation failure',
        'outgoing transition changed exception semantics: ' + Std.string(error));
    }
    check(state.transOut == data, 'outgoing error retained temporary transition data');

    check(close(SceneTransitionTiming.sceneDuration(2 / 3), 2 / 9),
      'Codename native scene transition duration was not scaled');
    OptionsHandler.options = {fastSceneTransitions:false};
    check(close(SceneTransitionTiming.sceneDuration(2 / 3), 2 / 3),
      'Codename native scene transition changed while the option was disabled');
  }
}'''
        transition_data_stub = r'''package flixel.addons.transition;
import flixel.math.FlxPoint;
import flixel.math.FlxRect;
enum TransitionCameraMode { TOP; NEW; DEFAULT; }
typedef TransitionTileData = {asset:Dynamic, width:Int, height:Int, ?frameRate:Int};
class TransitionData {
  public var type:String;
  public var color:Int;
  public var duration:Float;
  public var direction:FlxPoint;
  public var tileData:TransitionTileData;
  public var tweenOptions:Dynamic;
  public var region:FlxRect;
  public var cameraMode:Dynamic;
  public function new(type:String, color:Int, duration:Float, direction:FlxPoint,
    tileData:TransitionTileData, region:FlxRect, cameraMode:Dynamic) {
    this.type = type;
    this.color = color;
    this.duration = duration;
    this.direction = direction;
    this.tileData = tileData;
    this.region = region;
    this.cameraMode = cameraMode;
    tweenOptions = {onComplete:null};
  }
}'''
        point_stub = r'''package flixel.math;
class FlxPoint {
  public var x:Float;
  public var y:Float;
  public function new(x:Float = 0, y:Float = 0) { this.x = x; this.y = y; }
}'''
        rect_stub = r'''package flixel.math;
class FlxRect {
  public var x:Float;
  public var y:Float;
  public var width:Float;
  public var height:Float;
  public function new(x:Float, y:Float, width:Float, height:Float) {
    this.x = x; this.y = y; this.width = width; this.height = height;
  }
}'''
        options_stub = r'''class OptionsHandler {
  public static var options:Dynamic = {fastSceneTransitions:false};
}'''
        state_stub = f'''import flixel.addons.transition.TransitionData;
class FlxTransitionableState {{
  public var transIn:TransitionData;
  public var transOut:TransitionData;
  public var seenIn:TransitionData;
  public var seenOut:TransitionData;
  public var throwIn:Bool = false;
  public var throwOut:Bool = false;
  public var events:Array<String> = [];
  var pendingOutro:Void->Void;
  public function new(transIn:TransitionData, transOut:TransitionData) {{
    this.transIn = transIn; this.transOut = transOut;
  }}
  public function transitionIn():Void {{
    events.push('in-start'); seenIn = transIn;
    if (throwIn) throw 'expected transition creation failure';
    events.push('in-started');
  }}
  public function transitionOut(?onExit:Void->Void):Void {{
    events.push('out-start'); seenOut = transOut;
    if (throwOut) throw 'expected transition creation failure';
    Reflect.setField(transOut.tweenOptions, 'onComplete', 'flixel-finish');
    pendingOutro = onExit;
    events.push('tween-started');
  }}
  public function completeOutgoingTransition():Void {{
    events.push('out-finished');
    var callback = pendingOutro; pendingOutro = null;
    if (callback != null) callback();
    events.push('callback-return');
  }}
}}'''
        music_state_stub = f'''class MusicBeatState extends FlxTransitionableState {{
{transition_methods}
}}'''

        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            files = {
                "TransitionTimingMain.hx": fixture,
                "FlxTransitionableState.hx": state_stub,
                "MusicBeatState.hx": music_state_stub,
                "OptionsHandler.hx": options_stub,
                "flixel/addons/transition/TransitionData.hx": transition_data_stub,
                "flixel/math/FlxPoint.hx": point_stub,
                "flixel/math/FlxRect.hx": rect_stub,
            }
            for relative, contents in files.items():
                target = work / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(contents, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", directory,
                 "--main", "TransitionTimingMain", "--interp"],
                cwd=directory, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_native_codename_bridge_scales_its_base_scene_tween_only(self):
        source = (ROOT / "source/CodenameMusicBeatTransition.hx").read_text(encoding="utf-8")
        self.assertIn("SceneTransitionTiming.sceneDuration(2 / 3)", source)
        self.assertNotIn("SceneTransitionTiming", (ROOT / "source/CodenameMusicBeatTransitionRuntime.hx").read_text(
            encoding="utf-8"))
        music_beat_state = (ROOT / "source/MusicBeatState.hx").read_text(encoding="utf-8")
        self.assertIn("SceneTransitionTiming.forStateTransition(original)", music_beat_state)
        self.assertEqual(music_beat_state.count("SceneTransitionTiming.forStateTransition(original)"), 2)


if __name__ == "__main__":
    unittest.main()
