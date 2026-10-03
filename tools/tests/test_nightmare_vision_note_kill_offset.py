"""Keep the NMV note retirement window synchronized with source song speed."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    quote = None
    escaped = False
    line_comment = False
    block_comment = False
    index = opening
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and following == "/":
                block_comment = False
                index += 1
        elif quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char == "/" and following == "/":
            line_comment = True
            index += 1
        elif char == "/" and following == "*":
            block_comment = True
            index += 1
        elif char in ('"', "'"):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
        index += 1
    raise AssertionError(f"unterminated method: {marker}")


class NightmareVisionNoteKillOffsetTest(unittest.TestCase):
    @unittest.skipUnless(HAXE.is_file(), "portable Haxe is unavailable")
    def test_initial_speed_direct_changes_and_tweens_match_source_setter(self):
        play_state = (ROOT / "source/PlayState.hx").read_text()
        refresh = extract_method(play_state, "function refreshNightmareVisionNoteKillOffset(")
        setter = extract_method(play_state, "function set_scrollSpeed(")
        song_speed_getter = extract_method(play_state, "function get_songSpeed(")
        song_speed_setter = extract_method(play_state, "function set_songSpeed(")
        compat_getter = extract_method(play_state, "function compatGetProperty(")
        compat_setter = extract_method(play_state, "function compatSetProperty(")
        tween = extract_method(play_state, "public function tweenScrollSpeed(")
        initializer = extract_method(play_state, "function initializeNightmareVisionScripts(")
        interp_source = (ROOT / "source/NightmareVisionScriptInterp.hx").read_text()

        speed_setup = play_state.index("daScrollSpeed = OptionsHandler.options.scrollSpeed")
        initialize_call = play_state.index("initializeNightmareVisionScripts();", speed_setup)
        self.assertLess(speed_setup, initialize_call)
        self.assertLess(initializer.index("nightmareVisionScripts = new"),
                        initializer.index("refreshNightmareVisionNoteKillOffset();"))
        self.assertLess(initializer.index("refreshNightmareVisionNoteKillOffset();"),
                        initializer.index("nightmareVisionScripts.loadScope('stage')"))
        self.assertIn("onUpdate: function(_) refreshNightmareVisionNoteKillOffset()", tween)
        self.assertIn("refreshNightmareVisionNoteKillOffset();", setter)
        self.assertIn("@:keep public var songSpeed(get, set):Float;", play_state)
        self.assertIn("return daScrollSpeed;", song_speed_getter)
        self.assertIn("return scrollSpeed = value;", song_speed_setter)
        self.assertIn("if (hasParentWriteField(id))", interp_source)
        self.assertIn("Reflect.setProperty(parent, id, value);", interp_source)
        self.assertIn("new NightmareVisionGameplayScripts(this, plan,", play_state)
        self.assertIn("if (root.toLowerCase() == 'songspeed')\n\t\t\treturn daScrollSpeed;", compat_getter)
        speed_case = compat_setter.split("case 'songspeed':", 1)[1].split("case 'cpucontrolled'", 1)[0]
        self.assertIn("songSpeed = speed;", speed_case)
        self.assertNotIn("SONG.speed", speed_case)

        fixture = r'''class Conductor {
 public static var stepCrochet:Float = 125;
 public static function stepsToTime(steps:Float):Float return steps * stepCrochet;
}
class FlxEase { public static var linear:Dynamic = null; }
class FlxTween {
 public static var updates:Array<Float> = [];
 public static function tween(target:Dynamic, properties:Dynamic, duration:Float,
  options:Dynamic):Dynamic {
  var update = Reflect.field(options, 'onUpdate');
  PlayState.daScrollSpeed = 0.5;
  Reflect.callMethod(null, update, [null]);
  updates.push(PlayState.instance.noteKillOffset);
  PlayState.daScrollSpeed = Reflect.field(properties, 'daScrollSpeed');
  Reflect.callMethod(null, update, [null]);
  updates.push(PlayState.instance.noteKillOffset);
  return null;
 }
}
class PlayState {
 public static var SONG:Dynamic = {speed:1.0};
 public static var instance:PlayState;
 public static var daScrollSpeed:Float = 1;
 public static var dynamicScrollTarget:Float = 0;
 public static var chartSpeed:Float = 1;
 public static var effectiveScrollSpeed(get, never):Float;
 static function get_effectiveScrollSpeed():Float
  return dynamicScrollTarget > 0 ? dynamicScrollTarget : daScrollSpeed;
 public var playbackRate(get, never):Float;
 function get_playbackRate():Float return 1;
 public var noteKillOffset:Float = 350;
 public var nightmareVisionScripts:Dynamic;
 public var scrollSpeed(get, set):Float;
 public function new() { instance = this; }
 function get_scrollSpeed():Float return daScrollSpeed;
 public var songSpeed(get, set):Float;
 function get_songSpeed():Float return daScrollSpeed;
 function set_songSpeed(value:Float):Float return scrollSpeed = value;
 function tweenVSliceScrollSpeed(eventInfo:Dynamic, ?duration:Dynamic,
  ?ease:Dynamic, ?lines:Dynamic):Void {}
 SETTER
 REFRESH
 TWEEN
}
@:access(PlayState)
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var state = new PlayState();
  state.nightmareVisionScripts = {};
  PlayState.daScrollSpeed = 2;
  PlayState.dynamicScrollTarget = 0;
  state.refreshNightmareVisionNoteKillOffset();
  check(state.noteKillOffset == 175,
   'initial noteKillOffset did not use the selected positive chart speed');

  state.noteKillOffset = 42;
  check(state.noteKillOffset == 42,
   'an authored noteKillOffset was overwritten without a speed change');
 state.scrollSpeed = 0.5;
 check(state.noteKillOffset == 700,
   'direct speed change did not refresh the source formula');
 PlayState.chartSpeed = 1;
 state.songSpeed = 2;
 check(state.songSpeed == 2 && state.noteKillOffset == 175 && PlayState.chartSpeed == 1,
  'source songSpeed assignment did not refresh the offset without rewriting chart speed');
 state.noteKillOffset = 56;
 Reflect.setProperty(state, 'songSpeed', 0.5);
 check(state.songSpeed == 0.5 && state.noteKillOffset == 700 && PlayState.chartSpeed == 1,
  'reflective HScript-style songSpeed assignment bypassed the source setter');

 Conductor.stepCrochet = 150;
  state.noteKillOffset = 77;
  state.tweenScrollSpeed({scroll:2.0, duration:2.0, ease:'linear', absolute:true});
  check(FlxTween.updates.length == 2 && FlxTween.updates[0] == 700
   && FlxTween.updates[1] == 175 && state.noteKillOffset == 175,
   'speed tween did not refresh the offset at each interpolated speed');

  state.nightmareVisionScripts = null;
  state.noteKillOffset = 66;
  state.scrollSpeed = 3;
  check(state.noteKillOffset == 66,
   'non-NMV scroll speed changed the existing note retirement behavior');
 }
        }'''.replace("SETTER", setter).replace("REFRESH", refresh).replace("TWEEN", tween)

        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            (work / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--main", "Main", "--interp"],
                cwd=ROOT, env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True, text=True, timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
