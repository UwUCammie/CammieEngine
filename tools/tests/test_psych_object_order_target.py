"""setObjectOrder/getObjectOrder work in the container scripts are drawing in."""
import subprocess
import tempfile
import unittest

from base_helper_fixtures import copy_sources, play_state_method
from haxe_test_support import HAXE_COMMAND, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

FIXTURE = r'''
class FlxBasic { public var tag:String; public function new(tag:String) this.tag = tag; }
class Group {
 public var members:Array<FlxBasic> = [];
 public var splices:Array<Bool> = [];
 public function new(tags:String) for (tag in tags.split('')) members.push(new FlxBasic(tag));
 public function remove(item:FlxBasic, splice:Bool = false):FlxBasic { splices.push(splice); members.remove(item); return item; }
 public function insert(index:Int, item:FlxBasic):FlxBasic { members.insert(index, item); return item; }
 public function find(tag:String):FlxBasic { for (item in members) if (item.tag == tag) return item; return null; }
 public function order():String return [for (item in members) item.tag].join('');
}
class PsychCustomSubstate { public static var instance:Dynamic = null; }
class GameOverSubstate extends Group { public static var instance:GameOverSubstate = null; public var extras:Group = new Group('xyz'); }
class Main extends Group {
 var isDead:Bool = false;
 var named:Map<String, FlxBasic> = [];
 public var layer:Group = new Group('123');
 public var list:Array<FlxBasic> = [];
 function compatFindObject(name:Dynamic):Dynamic return named.get(Std.string(name));
__METHODS__
 static function same(actual:Dynamic, expected:Dynamic, label:String):Void
  if (actual != expected) throw label + ': got ' + Std.string(actual) + ', wanted ' + Std.string(expected);
 static function main() {
  // The shared step, on a plain array.
  var array:Array<Dynamic> = ['a', 'b', 'c', 'd'];
  SourceScriptReflection.reorderMember(array, 'b', 3);
  same(array.join(''), 'acdb', 'array move forward');
  SourceScriptReflection.reorderMember(array, 'b', 0);
  same(array.join(''), 'bacd', 'array move back');
  SourceScriptReflection.reorderMember(array, 'b', 99, true);
  same(array.join(''), 'acdb', 'clamped high');
  SourceScriptReflection.reorderMember(array, 'b', -5, true);
  same(array.join(''), 'bacd', 'clamped low');
  same(SourceScriptReflection.memberIndex(array, 'c'), 2, 'array index');
  same(SourceScriptReflection.memberIndex(array, 'nope'), -1, 'missing array member');
  same(SourceScriptReflection.memberIndex(null, 'c'), -1, 'missing container');
  same(SourceScriptReflection.reorderMember(null, 'c', 0), false, 'missing container is not reordered');
  same(SourceScriptReflection.reorderMember(12.5, 'c', 0, true), false, 'a number is not a container');
  same(SourceScriptReflection.reorderMember({name: 'plain'}, 'c', 0, true), false, 'an object without members is not a container');

  // The same step on a group, which has to splice.
  var group = new Group('abcd');
  SourceScriptReflection.reorderMember(group, group.find('a'), 2, true);
  same(group.order(), 'bcad', 'group move'); same(group.splices.join(','), 'true', 'group removal must splice');
  same(SourceScriptReflection.memberIndex(group, group.find('a')), 2, 'group index');
  var loose = new FlxBasic('z');
  SourceScriptReflection.reorderMember(group, loose, 1, true);
  same(group.order(), 'bzcad', 'an object not in the container is inserted without a removal');
  same(group.splices.length, 1, 'no removal for a non-member');

  // Which container a script reorder lands in.
  var state = {name: 'state', layer: 'state-layer'};
  var dead = {name: 'dead', layer: 'dead-layer'};
  var sub = {name: 'sub'};
  same(SourceScriptReflection.orderContainer(state, null, null), state, 'plain state');
  same(SourceScriptReflection.orderContainer(state, sub, null), sub, 'open custom substate wins over the state');
  same(SourceScriptReflection.orderContainer(state, null, dead), dead, 'game over stands in for the state');
  same(SourceScriptReflection.orderContainer(state, sub, dead), sub, 'custom substate wins over game over');
  same(SourceScriptReflection.orderContainer(state, sub, null, 'layer'), 'state-layer', 'a named group beats the substate');
  same(SourceScriptReflection.orderContainer(state, sub, dead, ' layer '), 'dead-layer', 'named group on the game over screen');
  same(SourceScriptReflection.orderContainer(state, sub, null, 'missing'), null, 'unknown group');
  same(SourceScriptReflection.orderContainer(state, sub, null, '  '), sub, 'blank group name is no group');

  // Through the script callbacks.
  var play = new Main('ABCD');
  for (item in play.members) play.named.set(item.tag, item);
  for (item in play.layer.members) play.named.set(item.tag, item);
  play.list = [play.find('A'), play.find('B'), play.find('C')];
  play.compatSetObjectOrder('B', 3);
  same(play.order(), 'ACDB', 'no group, nothing open: the state, as before');
  same(play.compatGetObjectOrder('B'), 3, 'state order');
  play.compatSetObjectOrder('B', 0, true);
  same(play.order(), 'BACD', 'an old boolean third argument is not a group');
  play.compatSetObjectOrder('3', 0, 'layer');
  same(play.layer.order(), '312', 'named group reorder'); same(play.order(), 'BACD', 'state untouched by a group reorder');
  same(play.compatGetObjectOrder('3', 'layer'), 0, 'named group order');
  same(play.compatGetObjectOrder('3'), -1, 'group member is not in the state');
  play.compatSetObjectOrder('C', 0, 'list');
  same([for (item in play.list) item.tag].join(''), 'CAB', 'named array reorder');
  same(play.compatGetObjectOrder('C', 'list'), 0, 'named array order');
  play.compatSetObjectOrder('A', 0, 'isDead');
  same(play.order(), 'BACD', 'a group name that is not a list changes nothing');
  play.compatSetObjectOrder('A', 0, 'noSuchGroup');
  same(play.order(), 'BACD', 'unknown group changes nothing'); same(play.compatGetObjectOrder('A', 'noSuchGroup'), -1, 'unknown group order');

  var sub2 = new Group('st');
  for (item in sub2.members) play.named.set(item.tag, item);
  PsychCustomSubstate.instance = sub2;
  play.compatSetObjectOrder('t', 0);
  same(sub2.order(), 'ts', 'open custom substate is reordered'); same(play.order(), 'BACD', 'state untouched while a substate is open');
  same(play.compatGetObjectOrder('t'), 0, 'substate order');
  PsychCustomSubstate.instance = null;

  var over = new GameOverSubstate('mn');
  for (item in over.members) play.named.set(item.tag, item);
  GameOverSubstate.instance = over;
  play.compatSetObjectOrder('n', 0);
  same(over.order(), 'mn', 'game over screen is not the target while alive');
  play.isDead = true;
  play.compatSetObjectOrder('n', 0);
  same(over.order(), 'nm', 'game over screen is the target once dead'); same(play.compatGetObjectOrder('n'), 0, 'game over order');
  play.named.set('y', over.extras.find('y'));
  play.compatSetObjectOrder('y', 0, 'extras');
  same(over.extras.order(), 'yxz', 'named group is looked up on the game over screen');
  same(play.reorderObject(play.find('A'), 0), true, 'base function reports the reorder');
 }
}
'''


class PsychObjectOrderTargetTest(unittest.TestCase):
    def test_group_argument_and_active_container(self):
        methods = "\n".join(play_state_method(marker) for marker in (
            "function compatSetObjectOrder(", "function compatGetObjectOrder(", "function objectOrderContainer(",
            "public function reorderObject(", "public function objectOrder("))
        methods = methods.replace("\tfunction compat", "\tpublic function compat")
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(FIXTURE.replace("__METHODS__", methods), newline="\n")
            copy_sources(folder, "SourceScriptReflection.hx")
            result = subprocess.run([*HAXE_COMMAND, "-cp", folder, "-main", "Main", "--interp"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_both_script_families_share_the_reorder_step(self):
        reflection = (ROOT / "source/SourceScriptReflection.hx").read_text(encoding="utf-8")
        legacy = reflection[reflection.index("public static function setLegacyObjectOrder("):]
        legacy = legacy[:legacy.index("\n\t}") + 3]
        self.assertIn("removeMember(instance(), object);", legacy)
        self.assertIn("insertMember(instance(), object, position);", legacy)
        self.assertIn("SourceScriptReflection.reorderMember(", play_state_method("public function reorderObject("))
        self.assertNotIn("members.indexOf", play_state_method("function compatSetObjectOrder("))


if __name__ == "__main__":
    unittest.main()
