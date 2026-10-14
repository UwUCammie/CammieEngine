"""One combined receptor index: opponent lanes first, player lanes after."""
import subprocess
import tempfile
import unittest

from base_helper_fixtures import copy_sources, play_state_method
from haxe_test_support import HAXE_COMMAND, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

FIXTURE = r'''
typedef Character = Dynamic;
class Line { public var members:Array<Dynamic>; public function new(members:Array<Dynamic>) this.members = members; }
class Main {
 var enemyStrums:Line;
 var playerStrums:Line;
 var boyfriend:Dynamic = 'bf-actor';
 var gf:Dynamic = 'gf-actor';
 var dad:Dynamic = 'dad-actor';
 function new(enemy:Line, player:Line) { enemyStrums = enemy; playerStrums = player; }
__METHODS__
 static function slot(index:Int, opponents:Int, players:Int, wrap:Bool = false):String {
  var found = CombinedReceptorIndex.resolve(index, opponents, players, wrap);
  return found == null ? 'none' : (found[0] == CombinedReceptorIndex.OPPONENT ? 'opp' : 'plr') + found[1];
 }
 static function same(actual:Dynamic, expected:Dynamic, label:String):Void
  if (actual != expected) throw label + ': got ' + Std.string(actual) + ', wanted ' + Std.string(expected);
 static function main() {
  // Four and four.
  same(slot(0, 4, 4), 'opp0', '4+4 first'); same(slot(3, 4, 4), 'opp3', '4+4 last opponent');
  same(slot(4, 4, 4), 'plr0', '4+4 first player'); same(slot(7, 4, 4), 'plr3', '4+4 last');
  same(slot(8, 4, 4), 'none', 'a group read past the end sees nothing');
  same(slot(8, 4, 4, true), 'opp0', 'a note tween past the end wraps');
  same(slot(13, 4, 4, true), 'plr1', 'wrap lands on the player side');
  same(slot(-1, 4, 4), 'none', 'negative index'); same(slot(-1, 4, 4, true), 'none', 'negative index never wraps');
  // One side missing.
  same(slot(2, 4, 0), 'opp2', '4+0'); same(slot(4, 4, 0), 'none', '4+0 end'); same(slot(5, 4, 0, true), 'opp1', '4+0 wrap');
  same(slot(0, 0, 4), 'plr0', '0+4 starts on the player'); same(slot(3, 0, 4), 'plr3', '0+4 last');
  same(slot(0, 0, 0), 'none', 'no receptors'); same(slot(0, 0, 0, true), 'none', 'no receptors, wrapping');
  // Lane counts come from the lines, not from a fixed key count.
  same(slot(5, 6, 4), 'opp5', '6+4 opponent'); same(slot(6, 6, 4), 'plr0', '6+4 player');
  same(slot(9, 6, 4), 'plr3', '6+4 last'); same(slot(10, 6, 4, true), 'opp0', '6+4 wrap');
  same(slot(4, 4, 9), 'plr0', '4+9 player'); same(slot(12, 4, 9), 'plr8', '4+9 last');
  same(CombinedReceptorIndex.count(4, 4), 8, 'count'); same(CombinedReceptorIndex.count(6, 4), 10, 'uneven count');
  same(CombinedReceptorIndex.count(-1, 4), 4, 'a missing line counts as empty');

  // The state lookup reads the live lines, so a rebuilt line is seen at once.
  var state = new Main(new Line(['e0', 'e1', 'e2', 'e3', 'e4', 'e5']), new Line(['p0', 'p1', 'p2', 'p3']));
  same(state.receptorCount(), 10, 'receptor count'); same(state.receptorAt(5), 'e5', 'sixth opponent lane');
  same(state.receptorAt(6), 'p0', 'first player lane'); same(state.receptorAt(10), null, 'past the end');
  same(state.receptorAt(10, true), 'e0', 'wrapped'); same(state.receptorAt(-2), null, 'negative');
  state.enemyStrums = new Line(['n0', 'n1']);
  same(state.receptorAt(1), 'n1', 'rebuilt line'); same(state.receptorAt(2), 'p0', 'player follows the rebuilt line');
  // The old actor helper shares the lookup and no longer walks off an array.
  same(state.getHaxeActor(1), 'n1', 'actor by number'); same(state.getHaxeActor('3'), 'p1', 'actor by number text');
  same(state.getHaxeActor(99), null, 'actor past the end'); same(state.getHaxeActor('nobody'), null, 'unknown actor name');
  same(state.getHaxeActor('bf'), 'bf-actor', 'named actor'); same(state.getHaxeActor('dad'), 'dad-actor', 'named actor');
  same(state.getHaxeActor('opponent'), 'dad-actor', 'named roles share the character role table');
  state.playerStrums = null;
  same(state.receptorCount(), 2, 'missing player line'); same(state.receptorAt(2), null, 'missing player line lookup');
 }
}
'''


class CombinedReceptorIndexTest(unittest.TestCase):
    def test_side_and_lane_for_every_line_shape(self):
        methods = "\n".join(play_state_method(marker) for marker in (
            "public function receptorCount(", "public function receptorAt(", "function getHaxeActor(",
            "public function characterForRole(", "static function characterGroupRole("))
        methods = methods.replace("\tfunction getHaxeActor(", "\tpublic function getHaxeActor(")
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(FIXTURE.replace("__METHODS__", methods), newline="\n")
            copy_sources(folder, "CombinedReceptorIndex.hx")
            result = subprocess.run([*HAXE_COMMAND, "-cp", folder, "-main", "Main", "--interp"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_every_script_path_uses_the_one_lookup(self):
        for marker in ("function compatGroupMember(", "function compatNoteTarget(", "function getHaxeActor(",
                       "function captureLuaDefaultStrums("):
            body = play_state_method(marker)
            self.assertIn("receptorAt(", body, marker)
            self.assertNotIn("NOTE_AMOUNT", body, marker)
            self.assertNotIn("strumLineNotes.members", body, marker)
        bindings = (ROOT / "source/PsychSourceBindings.hx").read_text(encoding="utf-8")
        self.assertIn("host.receptorAt(note, true)", bindings)
        self.assertNotIn("host.strumLineNotes", bindings)


if __name__ == "__main__":
    unittest.main()
