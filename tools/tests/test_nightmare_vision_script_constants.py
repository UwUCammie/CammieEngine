"""Execute NMV constant bindings, dynamic state lookup and group stop semantics."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionScriptConstantsTest(unittest.TestCase):
    def test_constants_import_state_lookup_and_return_values(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            (work / 'Main.hx').write_text(r'''
class Main {
 static function check(ok:Bool, why:String) if (!ok) throw why;
 static function main() {
  var state:Dynamic = {name:'gameplay'};
  var constants = new NightmareVisionScriptConstants(function() return state);
  var calls:Array<String> = [];
  var group = new NightmareVisionScriptGroup(null, function(name, phase, error) {
   throw name + ':' + phase + ':' + Std.string(error);
  });
  function configure(interp:NightmareVisionScriptInterp) {
   interp.variables.set('ScriptConstants', constants);
   interp.bindImport('funkin.scripting.ScriptConstants', constants);
   interp.variables.set('record', function(text:String) calls.push(text));
  }
  check(group.loadSource('first', '
   import funkin.scripting.ScriptConstants;
   function current() return ScriptConstants.getInstance();
   function stop() { record("first"); return ScriptConstants.STOP_FUNC; }
   function halt() { record("halt"); return ScriptConstants.HALT_FUNC; }
  ', configure) != null, 'first module');
  check(group.loadSource('second', '
   function stop() { record("second"); return ScriptConstants.CONTINUE_FUNC; }
   function halt() { record("unreachable"); return ScriptConstants.STOP_FUNC; }
  ', configure) != null, 'second module');
  var first = group.getScript('first');
  check(first.call('current') == state, 'live play state');
  state = {name:'gameover'};
  check(first.call('current') == state, 'live game over state');
  state = {name:'menu'};
  check(first.call('current') == state, 'live menu state');
  state = null;
  check(first.call('current') == null, 'pending gameover may have no instance yet');
  check(group.call('stop') == 1 && calls.join(',') == 'first,second', 'STOP broadcasts and retains stop');
  calls = [];
  check(group.call('halt') == 0 && calls.join(',') == 'halt', 'HALT ends broadcast');
  group.destroy();
 }
}
''')
            for defines in ([], ['-D', 'hscriptPos']):
                result = subprocess.run([
                    str(ROOT / '.tools/haxe/haxe'), '-cp', str(ROOT / 'source'),
                    '-cp', str(ROOT / '.haxelib/hscript-iris/1,1,3'),
                    '-cp', str(work), *defines, '--run', 'Main'],
                    cwd=ROOT, text=True, capture_output=True, timeout=45)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_gameplay_binding_uses_live_state_and_gameover_lifetime(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        start = source.index('var constants = new NightmareVisionScriptConstants(')
        binding = source[start:source.index("interp.bindImport('funkin.states.PlayState'", start)]
        self.assertIn('var current = FlxG.state;', binding)
        self.assertIn('Std.isOfType(current, PlayState)', binding)
        self.assertIn('play.psychGameOverTransitionPending', binding)
        self.assertIn('return GameOverSubstate.instance;', binding)
        self.assertIn("interp.variables.set('ScriptConstants', constants)", binding)
        self.assertIn("interp.bindImport('funkin.scripting.ScriptConstants', constants)", binding)


if __name__ == '__main__':
    unittest.main()
