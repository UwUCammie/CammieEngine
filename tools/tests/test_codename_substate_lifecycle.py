"""Codename substate callbacks receive their source event without losing old zero-arg hooks."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameSubstateLifecycleTest(unittest.TestCase):
    def test_playstate_supplies_substate_event(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("callCodenameScripts('onSubstateOpen', [new CodenameGameEvent()])", source)
        self.assertIn("callCodenameScripts('onSubstateClose', [new CodenameGameEvent()])", source)
        self.assertLess(source.index("callCodenameScripts('onSubstateClose'"),
                        source.index("super.closeSubState();"))

    def test_hscript_accepts_eventful_and_legacy_zero_arg_callbacks(self):
        fixture = '''import hscript.Parser;
import hscript.Interp;
class Main {
 static function main() {
  var parser = new Parser();
  var interp = new Interp();
  var order:Array<String>=[];
  interp.variables.set('order', order);
  interp.execute(parser.parseString(
   'function withEvent(event) { order.push(event.kind); } '
   + 'function withoutEvent() { order.push("zero"); }'));
  var event:Dynamic={kind:'substate'};
  Reflect.callMethod(null, interp.variables.get('withEvent'), [event]);
  Reflect.callMethod(null, interp.variables.get('withoutEvent'), [event]);
  if (order.join(',')!='substate,zero') throw order.join(',');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            (Path(directory) / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run([
                *HAXE_COMMAND, "-cp", directory,
                "-cp", str(ROOT / ".haxelib/hscript/2,5,0"), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
