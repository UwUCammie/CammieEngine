"""Source pause scripts on the native pause menu: leave-action vetoes and menu notifications."""
import re
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''class Main {
 static function check(v:Bool, s:String):Void if (!v) throw s;
 static function main():Void {
  var calls:Array<String> = [];
  var answers = new Map<String, Dynamic>();
  var released = 0;
  var hooks = NightmareVisionPauseScripts.hooksFor(function(name, args) {
   calls.push(name + (args.length > 0 ? ':' + args[0] : ''));
   return answers.get(name);
  }, function() released++);

  answers.set('onExit', NightmareVisionScriptGroup.STOP_FUNC);
  check(!hooks.allows(PauseMenuHooks.EXIT), 'onExit returning STOP_FUNC cancels the exit');
  check(hooks.allows(PauseMenuHooks.RESTART), 'onRestart with no answer lets the restart run');
  answers.set('onOptions', NightmareVisionScriptGroup.CONTINUE_FUNC);
  check(hooks.allows(PauseMenuHooks.OPTIONS), 'CONTINUE_FUNC lets the options screen open');
  answers.set('onRestart', '##PSYCHLUA_FUNCTIONSTOP');
  check(hooks.allows(PauseMenuHooks.RESTART), 'only the source STOP_FUNC cancels');
  check(hooks.allows('resume'), 'actions with no source callback are never asked');

  hooks.created();
  hooks.regenerated();
  answers.set('onChangeSelection', NightmareVisionScriptGroup.STOP_FUNC);
  check(!hooks.selectionChanged(3), 'onChangeSelection can skip the highlight refresh');
  hooks.update(0.5);
  check(calls.join(',') == 'onExit,onRestart,onOptions,onRestart,onCreatePost,onRegenMenu,onChangeSelection:3,onUpdate:0.5',
   'callback names and order: ' + calls.join(','));

  calls = [];
  hooks.destroy();
  hooks.destroy();
  check(calls.join(',') == 'onDestroy' && released == 1, 'onDestroy runs once, then the group is released');
  check(hooks.allows(PauseMenuHooks.EXIT), 'a released script cannot block leaving');
  hooks.update(1);
  check(calls.length == 1, 'a released script hears nothing more');

  var plain = new PauseMenuHooks();
  check(plain.allows(PauseMenuHooks.EXIT), 'a menu with no handler allows every action');

  // Source pause scripts guard onExit with a flag, call returnToMain() from
  // inside it and return STOP_FUNC: the inner exit runs once, the outer stops.
  var exits = 0;
  var guard = false;
  var reentrant:PauseMenuHooks = null;
  var returnToMain = function() if (reentrant.allows(PauseMenuHooks.EXIT)) exits++;
  reentrant = NightmareVisionPauseScripts.hooksFor(function(name, args):Dynamic {
   if (name != 'onExit') return null;
   if (guard) return null;
   guard = true;
   returnToMain();
   return NightmareVisionScriptGroup.STOP_FUNC;
  }, function() {});
  returnToMain();
  check(exits == 1, 're-entrant exit leaves exactly once: ' + exits);
 }
}
'''


def nv_constants():
    group = (ROOT / 'source/NightmareVisionScriptGroup.hx').read_text(encoding='utf-8')
    lines = []
    for name in ['CONTINUE_FUNC', 'STOP_FUNC']:
        value = re.search(r'public static inline var ' + name + r':Int = (\d+);', group).group(1)
        lines.append('\tpublic static inline var %s:Int = %s;' % (name, value))
    return 'package;\nclass NightmareVisionScriptGroup {\n' + '\n'.join(lines) + '\n}\n'


class NightmareVisionPauseScriptTest(unittest.TestCase):
    def test_hooks_map_to_source_callbacks(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            source = (ROOT / 'source/NightmareVisionPauseScripts.hx').read_text(encoding='utf-8')
            # Only the decoder-free mapping runs here; attach() needs a live session.
            start = source.index('\t/** Load the owner')
            end = source.index('\t/** The source callback name')
            (work / 'NightmareVisionPauseScripts.hx').write_text(source[:start] + source[end:], encoding='utf-8')
            (work / 'PauseMenuHooks.hx').write_text(
                (ROOT / 'source/PauseMenuHooks.hx').read_text(encoding='utf-8'), encoding='utf-8')
            (work / 'NightmareVisionScriptGroup.hx').write_text(nv_constants(), encoding='utf-8')
            (work / 'Main.hx').write_text(MAIN, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '--main', 'Main', '--interp'],
                                    cwd=work, capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_native_pause_menu_consults_the_hooks(self):
        pause = (ROOT / 'source/PauseSubState.hx').read_text(encoding='utf-8')
        self.assertIn('scriptHooks = PlayState.instance.pauseMenuHooks(this);', pause)
        self.assertIn('scriptHooks.allows(PauseMenuHooks.EXIT)) exitPauseToMenu();', pause)
        self.assertIn('!scriptHooks.allows(PauseMenuHooks.OPTIONS)) return;', pause)
        self.assertIn('!scriptHooks.allows(PauseMenuHooks.RESTART)) return;', pause)
        menu = pause[pause.index('switch (daSelected) {'):]
        self.assertIn('case "Restart Song":\n\t\t\t\t\t\trestartSong();', menu.replace('\r\n', '\n'))
        self.assertIn('case "Exit to menu":\n\t\t\t\t\t\treturnToMain();', menu.replace('\r\n', '\n'))
        self.assertIn('case "Change Options":\n\t\t\t\t\t\ttoOptions();', menu.replace('\r\n', '\n'))
        make = pause[pause.index('function makeMenuItems('):pause.index('public function returnToMain()')]
        self.assertIn('scriptHooks.regenerated()', make)
        # Source order on open: onChangeSelection and onRegenMenu, then onCreatePost.
        opened = pause[pause.index('scriptHooks = PlayState.instance.pauseMenuHooks(this);'):]
        opened = opened[:opened.index('scriptHooks.created();')]
        self.assertLess(opened.index('changeSelection();'), opened.index('scriptHooks.regenerated();'))
        destroy = pause[pause.index('override function destroy() {'):]
        self.assertLess(destroy.index('hooks.destroy()'), destroy.index('hxcClearPauseOverlay();'))

    def test_nightmare_vision_owner_supplies_the_pause_script(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        hooks = play[play.index('public function pauseMenuHooks('):]
        hooks = hooks[:hooks.index('NightmareVisionPauseScripts.attach(sourceSession, menu);')]
        self.assertIn('sourceSession.mods != nightmareVisionActiveMods', hooks)
        adapter = (ROOT / 'source/NightmareVisionPauseScripts.hx').read_text(encoding='utf-8')
        self.assertIn("SCRIPT_PREFIX = 'substates'", adapter)
        self.assertIn("SCRIPT_NAME = 'PauseSubState'", adapter)
        self.assertLess(adapter.index('group.parent = menu;'), adapter.index("group.call('onLoad', []);"))
        session = (ROOT / 'source/NightmareVisionStateSession.hx').read_text(encoding='utf-8')
        self.assertIn("interp.bindImport('funkin.states.substates.PauseSubState', PauseSubState);", session)
        self.assertIn("interp.variables.set('PauseSubState', PauseSubState);", session)


if __name__ == '__main__':
    unittest.main()
