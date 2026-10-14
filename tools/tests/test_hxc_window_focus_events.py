"""V-Slice scripts listening to window focus get engine-owned, state-scoped events."""
import json
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

SONG_SCRIPT = '''import lime.app.Application;
class FocusSong extends Song {
  var paused = false;
  function new() { super('focus-song'); }
  function onCreate(event) {
    super.onCreate(event);
    var lost = function(?_) { paused = true; };
    Application.current.window.onFocusOut.add(lost);
    Application.current.window.onFocusIn.add(function() { paused = false; });
  }
}
'''


class HxcWindowFocusEventsTest(unittest.TestCase):
    def run_main(self, main: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'Main.hx').write_text(main, newline='\n')
            return subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True, timeout=300)

    def test_application_focus_listeners_are_routed_to_engine_events(self):
        result = self.run_main('''class Main {
 static function main() {
  var result = HxcCompat.analyze(%s, 'scripts/songs/focus-song.hxc');
  var code:String = result.generatedHscript;
  if (code.indexOf("HxcCompatRuntime.windowFocusEvent('out').add(lost)") < 0)
   throw 'focus-out listener was not routed: ' + code;
  if (code.indexOf("HxcCompatRuntime.windowFocusEvent('in').add(") < 0)
   throw 'focus-in listener was not routed';
  if (code.indexOf('Application.current.window') >= 0)
   throw 'a script still reaches the process window directly';
 }
}
''' % json.dumps(SONG_SCRIPT))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_event_runs_script_listeners_and_forgets_them(self):
        result = self.run_main('''class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main() {
  var messages:Array<String> = [];
  haxe.Log.trace = function(v:Dynamic, ?p:haxe.PosInfos) messages.push(Std.string(v));
  var event = new HxcWindowEvent();
  var calls = 0;
  var listener = function(?unused:Dynamic) calls++;
  event.add(listener);
  event.add(listener);
  event.add(null);
  event.add('not a function');
  event.dispatch();
  check(calls == 1, 'a listener added twice ran twice, or the dispatch did not reach it');
  check(event.has(listener), 'has() lost the listener');
  // One failing listener must not stop the others or escape to the window.
  event.add(function() throw 'broken');
  var after = 0;
  event.add(function() after++);
  event.dispatch();
  check(calls == 2 && after == 1, 'a failing listener stopped the rest');
  check(messages.length == 1 && messages[0].indexOf('broken') >= 0, 'the failure was hidden');
  // A listener may remove itself while it runs.
  var once = 0;
  var self:Dynamic = null;
  self = function() { once++; event.remove(self); };
  event.add(self);
  event.dispatch();
  event.dispatch();
  check(once == 1 && calls == 4 && after == 3, 'self-removal during dispatch failed');
  event.remove(listener);
  event.dispatch();
  check(calls == 4 && after == 4, 'remove() kept the listener');
  event.removeAll();
  event.dispatch();
  check(after == 4, 'removeAll() kept a listener');
 }
}
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_listeners_end_with_their_state(self):
        result = self.run_main('''class Main {
 static function main() {
  var out = HxcWindowEvent.focus('out');
  var gained = HxcWindowEvent.focus('in');
  if (out == gained || HxcWindowEvent.focus('out') != out || HxcWindowEvent.focus('in') != gained)
   throw 'each focus kind must be one shared event';
  var runs = 0;
  out.add(function() runs++);
  gained.add(function() runs++);
  HxcWindowEvent.clearScriptListeners();
  out.dispatch();
  gained.dispatch();
  if (runs != 0) throw 'a listener outlived its state';
 }
}
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        source = (ROOT / 'source/HxcWindowEvent.hx').read_text(encoding='utf-8')
        # In the game both events forward lime's own event and are cleared before each state switch.
        self.assertIn('window.onFocusIn.add(event.dispatch);', source)
        self.assertIn('window.onFocusOut.add(event.dispatch);', source)
        self.assertIn('flixel.FlxG.signals.preStateSwitch.add(clearScriptListeners);', source)


if __name__ == '__main__':
    unittest.main()
