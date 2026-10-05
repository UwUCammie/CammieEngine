"""Exercise Psych charting state and editor handoff against extracted code."""
import re
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]


def method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"Unclosed source method: {marker}")


class PsychChartingHandoffTest(unittest.TestCase):
    def test_owner_property_callback_gate_and_explicit_editor_handoff(self):
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        editor = (ROOT / "source/ChartingState.hx").read_text(encoding="utf-8")
        compat = (ROOT / "source/EngineCompat.hx").read_text(encoding="utf-8")
        lifecycle = (ROOT / "source/PsychEndSongLifecycle.hx").read_text(encoding="utf-8")

        property_decl = re.search(
            r"@:keep public static var chartingMode\(get, set\):Bool;", play
        )
        self.assertIsNotNone(property_decl)
        play_methods = "\n".join(
            method(play, marker)
            for marker in (
                "static function get_chartingMode()",
                "static function set_chartingMode(value:Bool)",
                "@:keep public static function psychChartingOwnerRoot()",
                "@:keep function shouldReturnToPsychChartEditor()",
                "@:keep function shouldRoutePsychChartingAfterSelectedEndSong(",
                "function openChartEditor()",
                "@:keep public function sourceGameOverResetForMenu()",
            )
        )
        editor_methods = "\n".join(
            method(editor, marker)
            for marker in (
                "@:keep public function beginTestPlay(fromCurrentPosition:Bool = false)",
                "@:keep public function exitPsychChartEditor()",
            )
        )

        self.assertIn("case 'chartingMode':\n\t\t\t\treturn chartingMode;", play)
        self.assertIn(
            "EngineCompat.legacyClassProperty(Std.string(className), Std.string(path)) == 'chartingMode'",
            play,
        )
        self.assertIn("chartingMode = value == true;", play)
        self.assertIn("FlxG.keys.justPressed.ESCAPE && !typingShit.hasFocus", editor)
        self.assertIn("&& !layoutTextField.hasFocus && !chartEventInputsFocused()", editor)
        self.assertIn("if (psychChartingOwnerRoot() != '')\n\t\t\t\topenChartEditor();", play)
        self.assertNotIn(
            "PlayState.chartingMode = false",
            method(editor, "override public function destroy()"),
        )

        end_song = method(play, "function endSong(?force:Bool = false)")
        self.assertEqual(end_song.count("callAllHScript('songEnd'"), 1)
        selected = end_song.index("if (selectedDisposition != PsychEndSongLifecycle.CONTINUE_NATIVE)")
        route = end_song.index("shouldRoutePsychChartingAfterSelectedEndSong(selectedDisposition)")
        providers = end_song.index("var globalResults:Array<Dynamic> = []")
        stage_end = end_song.index("runPsychStageEndCallback()")
        self.assertLess(selected, route)
        self.assertLess(route, providers)
        self.assertLess(route, stage_end)

        end_for_real = method(play, "function endForReal()")
        self.assertLess(end_for_real.index("Highscore.saveScore("),
                        end_for_real.index("if (shouldReturnToPsychChartEditor())"))
        self.assertLess(end_for_real.index("if (shouldReturnToPsychChartEditor())"),
                        end_for_real.index("if (isStoryMode)"))
        self.assertIn("beginTestPlay(FlxG.keys.pressed.SHIFT);", editor)

        engine_method = method(
            compat, "public static function legacyClassProperty(className:String, path:String)"
        )
        lifecycle_method = method(lifecycle, "public static function selectedDisposition(")
        main = r'''using StringTools;
@:access(PlayState)
@:access(ChartingState)
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  Song.rows.set('psych-a', {engine:'Psych', root:'assets/imported_mods/A'});
  Song.rows.set('psych-b', {engine:'Psych', root:'assets/imported_mods/B'});
  Song.rows.set('native', {engine:'Codename', root:'assets/imported_mods/C'});
  Song.rows.set('nightmare', {engine:'Nightmare Vision', root:'assets/imported_mods/NV'});
  PlayState.SONG = {folder:'psych-a'};
  check(!PlayState.chartingMode, 'Psych owner default should be false');
  PlayState.chartingMode = true;
  check(PlayState.chartingMode && PsychOwnerChartingMode.get('assets/imported_mods/A'),
   'static property did not write the selected Psych owner');
  check(EngineCompat.legacyClassProperty('PlayState', 'chartingMode') == 'chartingMode',
   'exact legacy class alias missing');
  check(EngineCompat.legacyClassProperty('states.PlayState', '.chartingMode') == 'chartingMode',
   'qualified exact legacy class alias missing');
  check(EngineCompat.legacyClassProperty('OtherPlayState', 'chartingMode') == '',
   'non-exact class name was treated as the PlayState alias');

  var host = new PlayState();
  host.sourceScoreOwner = true;
  host.activePsychRoot = 'assets/imported_mods/A';
  PlayState.instance = host;
  FlxG.state = host;
  PlayState.SONG = {folder:'psych-b'};
  check(PlayState.psychChartingOwnerRoot() == 'assets/imported_mods/A',
   'active gameplay owner was replaced by a mutable chart object');
  check(host.shouldReturnToPsychChartEditor(), 'Psych source owner should hand back to editor');
  check(host.shouldRoutePsychChartingAfterSelectedEndSong(
   PsychEndSongLifecycle.selectedDisposition(false, false)), 'continuing selected callback should route');
  check(!host.shouldRoutePsychChartingAfterSelectedEndSong(
   PsychEndSongLifecycle.selectedDisposition(false, true)), 'Function_Stop must keep callback ownership');
  check(!host.shouldRoutePsychChartingAfterSelectedEndSong(
   PsychEndSongLifecycle.selectedDisposition(true, false)), 'cancelled event must keep outro ownership');

  // ChartingState has no live PlayState. Its newly selected SONG resolves to
  // its own Psych owner rather than carrying the prior scene's root.
  FlxG.state = {};
  check(PlayState.psychChartingOwnerRoot() == 'assets/imported_mods/B'
   && !PlayState.chartingMode, 'editor metadata did not resolve its selected chart owner');
  PlayState.chartingMode = true;
  check(PsychOwnerChartingMode.get('assets/imported_mods/B')
   && PsychOwnerChartingMode.get('assets/imported_mods/A'), 'editor owner did not retain independent state');
  PlayState.SONG = {folder:'native'};
  check(PlayState.psychChartingOwnerRoot() == '' && !PlayState.chartingMode,
   'native charts must not inherit a Psych owner flag');
  PlayState.chartingMode = true;
  PlayState.SONG = {folder:'nightmare'};
  check(PlayState.psychChartingOwnerRoot() == '' && !PlayState.chartingMode,
   'NV charts must not inherit a Psych owner flag');
  host.sourceScoreNightmare = true;
  FlxG.state = host;
  PlayState.SONG = {folder:'psych-a'};
  check(PlayState.psychChartingOwnerRoot() == '' && !PlayState.chartingMode,
   'active NV owner must not reuse the prior Psych chart flag');
  host.sourceScoreNightmare = false;
  FlxG.state = {};

  // Test play preserves SHIFT's requested position and selected chart.
  PlayState.SONG = {folder:'psych-b'};
  PlayState.startingPosition = 7;
  Conductor.songPosition = 42.5;
  var editor = new ChartingState();
  editor._song = {folder:'psych-b', needsVoices:true};
  editor.curSection = 4;
  editor.beginTestPlay(true);
  check(PlayState.SONG == editor._song && PlayState.startingPosition == 42.5
   && editor.lastSection == 4, 'SHIFT test play lost chart identity or startingPosition');
  check(editor.autosaves == 1 && editor.vocalStops == 1 && !FlxG.mouse.visible
   && Std.isOfType(LoadingState.lastState, PlayState), 'test-play handoff missed editor cleanup');

  // Re-enter source gameplay using the editor-selected owner and check the
  // shared openChartEditor helper's donor transition effects.
  PlayState.SONG = {folder:'psych-a'};
  host.activePsychRoot = 'assets/imported_mods/A';
  host.sourceScoreNightmare = false;
  PlayState.instance = host;
  FlxG.state = host;
  FlxG.camera = new FakeCamera();
  FlxG.sound = new FakeSoundSystem();
  LoadingState.lastState = null;
  host.openChartEditor();
  check(PlayState.chartingMode && !host.canResync && !host.persistentUpdate && host.paused,
   'openChartEditor did not set the donor transition state');
  check(FlxG.camera.followLerp == 0 && FlxG.sound.music.stops == 1 && host.vocalPauses == 1,
   'openChartEditor did not stop gameplay music/vocals or reset camera follow');
  check(Std.isOfType(LoadingState.lastState, ChartingState), 'openChartEditor did not enter ChartingState');

  // The GameOver menu clears only this song owner's retained state.
  PlayState.SONG = {folder:'psych-a'};
  PsychOwnerChartingMode.set('assets/imported_mods/A', true);
  PsychOwnerChartingMode.set('assets/imported_mods/B', true);
  host.balls = 3;
  host.watchedCutscene = true;
  host.sourceGameOverResetForMenu();
  check(!PsychOwnerChartingMode.get('assets/imported_mods/A')
   && PsychOwnerChartingMode.get('assets/imported_mods/B')
   && host.balls == 0 && !host.watchedCutscene,
   'GameOver menu reset did not clear only its current Psych owner');

  // Explicit ESC equivalent saves the editor autosave, clears its own owner,
  // and exits. Calling the method after that is harmless.
  PlayState.SONG = {folder:'psych-a'};
  PlayState.chartingMode = true;
  FlxG.state = editor;
  check(editor.exitPsychChartEditor(), 'explicit source editor exit was rejected');
  check(!PlayState.chartingMode && editor.autosaves == 2 && editor.vocalStops == 2
   && !FlxG.mouse.visible && Std.isOfType(LoadingState.lastState, FreeplayState)
   && PsychOwnerChartingMode.get('assets/imported_mods/B'),
   'explicit exit did not save, clear the owner, and return to Freeplay');
  check(!editor.exitPsychChartEditor(), 'a second exit should not clear a different owner');
 }
}
class ImportEngine { public static inline var PSYCH:String = 'Psych'; }
class Song {
 public static var rows:Map<String,Dynamic> = new Map();
 public static function storageFolder(chart:Dynamic):String return chart == null ? '' : chart.folder;
 public static function characterOwnerEngineForSong(folder:String):String {
  var row = rows.get(folder); return row == null ? '' : row.engine;
 }
 public static function characterRootForSong(folder:String, engine:String):String {
  var row = rows.get(folder); return row == null || row.engine.toLowerCase() != engine.toLowerCase() ? '' : row.root;
 }
}
class Conductor { public static var songPosition:Float = 0; }
class FakeCamera { public var followLerp:Float = 1; public function new() {} }
class FakeMusic { public var stops:Int = 0; public function new() {} public function stop():Void stops++; }
class FakeSoundSystem { public var music:FakeMusic = new FakeMusic(); public function new() {} }
class FakeMouse { public var visible:Bool = true; public function new() {} }
class FlxG {
 public static var state:Dynamic;
 public static var camera:FakeCamera = new FakeCamera();
 public static var sound:FakeSoundSystem = new FakeSoundSystem();
 public static var mouse:FakeMouse = new FakeMouse();
}
class LoadingState { public static var lastState:Dynamic; public static function loadAndSwitchState(value:Dynamic):Void lastState = value; }
class FreeplayState { public function new() {} }
class DiscordClient {
 public static function changePresence(a:Dynamic, b:Dynamic, c:Dynamic, d:Dynamic):Void {}
 public static function resetClientID():Void {}
}
class PlayState {
 public static var SONG:Dynamic;
 public static var instance:Null<PlayState>;
 public static var startingPosition:Float = 0;
 @@PROPERTY@@
 public var sourceScoreOwner:Bool = false;
 public var sourceScoreNightmare:Bool = false;
 public var activePsychRoot:String = '';
 public var canResync:Bool = true;
 public var persistentUpdate:Bool = true;
 public var paused:Bool = false;
 public var vocalPauses:Int = 0;
 public var balls:Int = 0;
 public var watchedCutscene:Bool = false;
 public function new() {}
 public function selectedPsychSkinRoot():Null<String> return activePsychRoot;
 public function pauseVocals():Void vocalPauses++;
 @@PLAY_METHODS@@
}
class ChartingState {
 public var _song:Dynamic;
 public var curSection:Int = 0;
 public var lastSection:Int = 0;
 public var charDropdown:Dynamic;
 public var autosaves:Int = 0;
 public var vocalStops:Int = 0;
 public function new() {}
 function autosaveSong():Void autosaves++;
 function stopEditorVocals():Void vocalStops++;
 @@EDITOR_METHODS@@
}
class EngineCompat {
 @@ENGINE_METHOD@@
}
class PsychEndSongLifecycle {
 public static inline var CONTINUE_NATIVE:Int = 0;
 public static inline var HOLD_FOR_SCRIPT:Int = 1;
 public static inline var RELEASE_FOR_OUTRO:Int = 2;
 @@LIFECYCLE_METHOD@@
}
'''
        main = main.replace("@@PROPERTY@@", property_decl.group(0))
        main = main.replace("@@PLAY_METHODS@@", play_methods)
        main = main.replace("@@EDITOR_METHODS@@", editor_methods)
        main = main.replace("@@ENGINE_METHOD@@", engine_method)
        main = main.replace("@@LIFECYCLE_METHOD@@", lifecycle_method)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            (work / "Main.hx").write_text(main, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                 "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
