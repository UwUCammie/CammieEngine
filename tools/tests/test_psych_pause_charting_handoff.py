"""Execute the pause actions through Psych and non-Psych transition paths."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_psych_charting_handoff import method

ROOT = Path(__file__).resolve().parents[2]


class PsychPauseChartingHandoffTest(unittest.TestCase):
    def test_pause_editor_entry_and_captured_owner_menu_reset(self):
        source = (ROOT / 'source/PauseSubState.hx').read_text(encoding='utf-8')
        self.assertIn('case "Charting":\n\t\t\t\t\t\topenPauseChartEditor();', source)
        # Exit asks any pause script first, then leaves through exitPauseToMenu.
        self.assertIn('case "Exit to menu":\n\t\t\t\t\t\treturnToMain();', source)
        self.assertIn('scriptHooks.allows(PauseMenuHooks.EXIT)) exitPauseToMenu();',
                      method(source, 'public function returnToMain()'))
        methods = '\n'.join(method(source, marker) for marker in (
            'function openPauseChartEditor()', 'function exitPauseToMenu()',
        ))
        # The pause menu leaves through the song's shared exit, so run that too.
        self.assertIn('PlayState.exitToMenu();', method(source, 'function exitPauseToMenu()'))
        play_source = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        exit_to_menu = method(play_source, 'public static function exitToMenu(')
        fixture = '''@:access(PauseSubState)
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var pause = new PauseSubState();
  var host = new PlayState();
  PlayState.instance = host;
  PlayState.owner = 'assets/imported_mods/A';
  pause.openPauseChartEditor();
  check(host.editorEntries == 1 && PsychOwnerChartingMode.get(PlayState.owner)
   && !host.canResync && Std.isOfType(LoadingState.last, ChartingState),
   'Psych pause editor entry bypassed the shared gameplay helper');
  PsychOwnerChartingMode.set('assets/imported_mods/B', true);
  for (story in [false, true]) {
   PlayState.owner = 'assets/imported_mods/A';
   PlayState.isStoryMode = story;
   PlayState.balls = 4;
   PlayState.watchedCutscene = true;
   host.canResync = true;
   PsychOwnerChartingMode.set(PlayState.owner, true);
   LoadingState.checkSourceOrder = true;
   pause.exitPauseToMenu();
   check(!PsychOwnerChartingMode.get('assets/imported_mods/A')
    && PsychOwnerChartingMode.get('assets/imported_mods/B'), 'exit cleared the post-switch owner');
   check(Std.isOfType(LoadingState.last, story ? StoryMenuState : FreeplayState)
    && FlxG.camera.followLerp == 0, 'Psych exit lost menu choice or camera reset');
  }
  LoadingState.checkSourceOrder = false;
  for (dialect in ['native', 'Nightmare Vision']) {
   PlayState.owner = '';
   PlayState.isStoryMode = false;
   host.canResync = true;
   PlayState.balls = 7;
   PlayState.watchedCutscene = true;
   FlxG.camera.followLerp = 1;
   var entries = host.editorEntries;
   pause.openPauseChartEditor();
   check(host.editorEntries == entries && Std.isOfType(LoadingState.last, ChartingState),
    dialect + ' editor path changed');
   pause.exitPauseToMenu();
   check(host.canResync && PlayState.balls == 7 && PlayState.watchedCutscene
    && FlxG.camera.followLerp == 1 && PsychOwnerChartingMode.get('assets/imported_mods/B'),
    dialect + ' exit acquired Psych lifecycle effects');
  }
 }
}
class PauseSubState {
 public function new() {}
 @@METHODS@@
}
class PlayState {
 public static var instance:PlayState;
 public static var owner:String = '';
 public static var isStoryMode:Bool = false;
 public static var balls:Int = 0;
 public static var watchedCutscene:Bool = false;
 public var canResync:Bool = true;
 public var editorEntries:Int = 0;
 public function new() {}
 public static function psychChartingOwnerRoot():String return owner;
 static function skipNextSongTransition(skip:Bool):Void {}
 @@EXIT@@
 private function openChartEditor():Void {
  editorEntries++;
  canResync = false;
  PsychOwnerChartingMode.set(owner, true);
  LoadingState.last = new ChartingState();
 }
}
class LoadingState {
 public static var last:Dynamic;
 public static var checkSourceOrder:Bool = false;
 public static function loadAndSwitchState(state:Dynamic):Void {
  if (checkSourceOrder) {
   if (PlayState.instance.canResync || PlayState.balls != 0 || PlayState.watchedCutscene)
    throw 'Psych pre-switch menu reset order';
   if (!PsychOwnerChartingMode.get('assets/imported_mods/A')) throw 'flag cleared before donor switch';
   PlayState.owner = 'assets/imported_mods/B';
  }
  last = state;
 }
}
class ImportedMenuEntry { public static function returnToFreeplay():Void LoadingState.loadAndSwitchState(new FreeplayState()); }
class FlxG {
 public static var camera:Dynamic = {followLerp:1.0};
 public static var sound:Dynamic = {playMusic:function(path:Dynamic):Void throw 'pause exit started menu music'};
}
class Paths { public static function music(key:String):String return key; }
class ChartingState { public function new() {} }
class FreeplayState { public function new() {} }
class StoryMenuState { public function new() {} }
'''.replace('@@METHODS@@', methods).replace('@@EXIT@@', exit_to_menu)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            Path(folder, 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                                     '--main', 'Main', '--interp'], cwd=ROOT,
                                    capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
