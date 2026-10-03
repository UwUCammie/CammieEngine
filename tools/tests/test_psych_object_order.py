"""Psych setObjectOrder removes, then inserts at the requested final index."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PsychObjectOrderTest(unittest.TestCase):
    def test_forward_backward_same_and_bounded_positions(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        start = source.index("\tfunction compatSetObjectOrder(")
        end = source.index("\n\tfunction compatRandomInt(", start)
        methods = source[start:end]
        fixture = '''class FlxBasic {
  public var tag:String;
  public function new(tag:String) this.tag = tag;
}
class State {
  public var members:Array<FlxBasic> = [];
  public function new() {
    for (tag in ['A','B','C','D']) members.push(new FlxBasic(tag));
  }
  function compatFindObject(name:Dynamic):Dynamic {
    for (item in members) if (item.tag == Std.string(name)) return item;
    return null;
  }
  function remove(item:FlxBasic, splice:Bool):Void { members.remove(item); }
  function insert(index:Int, item:FlxBasic):Void { members.insert(index, item); }
''' + methods + '''
  public function order():String return [for (item in members) item.tag].join('');
}
class Main {
  static function main() {
    var s = new State();
    s.compatSetObjectOrder('B', 3);
    if (s.order() != 'ACDB' || s.compatGetObjectOrder('B') != 3)
      throw 'forward move must use final index verbatim';
    s.compatSetObjectOrder('B', 0);
    if (s.order() != 'BACD') throw 'backward move';
    s.compatSetObjectOrder('A', 1);
    if (s.order() != 'BACD') throw 'same index changed order';
    s.compatSetObjectOrder('B', 999);
    if (s.order() != 'ACDB') throw 'high position must clamp to top';
    s.compatSetObjectOrder('B', -99);
    if (s.order() != 'BACD') throw 'low position must clamp to bottom';
    s.compatSetObjectOrder('missing', 2);
    if (s.order() != 'BACD' || s.compatGetObjectOrder('missing') != -1)
      throw 'missing object changed display list';
  }
}'''
        fixture = fixture.replace("function compatSetObjectOrder(",
                                  "public function compatSetObjectOrder(", 1)
        fixture = fixture.replace("function compatGetObjectOrder(",
                                  "public function compatGetObjectOrder(", 1)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run([
                *HAXE_COMMAND, "-cp", tmp,
                "-main", "Main", "--interp",
            ], cwd=ROOT, text=True, capture_output=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
