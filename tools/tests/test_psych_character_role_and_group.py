"""One role lookup and one shared group view per role for character callbacks."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_psych_charting_handoff import method

ROOT = Path(__file__).resolve().parents[2]


class PsychCharacterRoleAndGroupTest(unittest.TestCase):
    def test_roles_resolve_like_psych_and_groups_are_shared_views(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        methods = '\n'.join(method(play, marker) for marker in (
            'public function characterForRole(',
            'static function characterGroupRole(',
            'public function characterGroupForRole(',
            'public function characterGroupPosition(',
            'public function setCharacterGroupPosition(',
            'function getHaxeActor(',
            'function compatCharacterDance(',
            'function compatCharacterPlayAnim(',
        ))
        fixture = '''class Character {
 public var name:String; public var x:Float = 0; public var y:Float = 0; public var danced:Int = 0;
 public var played:String = '';
 public function new(name:String, x:Float) {this.name = name; this.x = x;}
 public function dance():Void danced++;
 public function hasAnimation(name:String):Bool return true;
 public function playAnim(name:String, force:Bool):Void played = name;
}
class Info {public var x:Float; public var y:Float; public function new(x:Float, y:Float) {this.x = x; this.y = y;}}
class PsychBaseStageActorGroupCompat {
 var host:Main; public var role:String;
 public function new(host:Main, role:String) {this.host = host; this.role = role;}
 public var x(get, set):Float;
 function get_x():Float return host.info(role).x;
 function set_x(value:Float):Float {
  var actor = host.characterForRole(role);
  actor.x += value - host.info(role).x;
  return host.info(role).x = value;
 }
 public var y(get, set):Float;
 function get_y():Float return host.info(role).y;
 function set_y(value:Float):Float return host.info(role).y = value;
}
class Main {
 var boyfriend = new Character('bf', 770);
 var dad = new Character('dad', 100);
 var gf = new Character('gf', 400);
 var boyfriendGroup:Dynamic = null; var dadGroup:Dynamic = null; var gfGroup:Dynamic = null;
 var infos:Map<String, Info> = ['bf' => new Info(700, 400), 'dad' => new Info(90, 100), 'gf' => new Info(380, 130)];
 public function info(role:String):Info return infos.get(role);
 var psychCharacterGroups:Map<String, PsychBaseStageActorGroupCompat>;
 function receptorAt(index:Int):Dynamic return {receptor: index};
 public function new() {}
 @@METHODS@@
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var state = new Main();
  for (role in ['dad', 'Opponent', ' DAD ']) check(state.characterForRole(role) == state.dad, role + ' is dad');
  for (role in ['gf', 'Girlfriend']) check(state.characterForRole(role) == state.gf, role + ' is gf');
  for (role in ['bf', 'boyfriend', 'player', 'nonsense', '', null, '1'])
   check(state.characterForRole(role) == state.boyfriend, role + ' falls back to the boyfriend');

  // Psych reads the group's stage anchor, not the sprite position.
  check(state.characterGroupPosition('opponent', 'x') == 90, 'getCharacterX reads the group');
  check(state.characterGroupPosition('whatever', 'y') == 400, 'unknown role reads the boyfriend group');
  state.setCharacterGroupPosition('dad', 'x', 140);
  check(state.info('dad').x == 140 && state.dad.x == 150, 'setCharacterX moves the group and its actor');
  var first = state.characterGroupForRole('dad');
  check(first == state.characterGroupForRole('opponent'), 'one view per role');
  check(first != state.characterGroupForRole('gf'), 'roles keep separate views');

  // Nightmare Vision's real groups win when they exist.
  var real:Dynamic = {x: 5, y: 6};
  state.gfGroup = real;
  check(state.characterGroupForRole('girlfriend') == real, 'real group ignored');

  // Named actor lookups share the role table; numbers stay strum indices.
  check(state.getHaxeActor('opponent') == state.dad, 'opponent actor');
  check(state.getHaxeActor('gf') == state.gf && state.getHaxeActor('bf') == state.boyfriend, 'named actors');
  check(state.getHaxeActor('3').receptor == 3, 'numeric strum lookup kept');
  check(state.getHaxeActor('unknown-tag') == null, 'unknown name is not an actor');
  state.compatCharacterDance('nonsense');
  check(state.boyfriend.danced == 1, 'characterDance falls back to the boyfriend');
  state.compatCharacterPlayAnim('opponent', 'hey');
  check(state.dad.played == 'hey', 'characterPlayAnim uses the role table');
 }
}'''.replace('@@METHODS@@', methods)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            Path(folder, 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '--main', 'Main', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_property_roots_and_compiled_stage_use_the_shared_group(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        root = method(play, 'function compatPropertyRoot(')
        case = root[root.index("case 'boyfriendgroup' | 'dadgroup' | 'gfgroup':"):]
        self.assertIn("characterGroupForRole(root.substr(0, root.length - 'Group'.length))", case[:300])
        cameras = method(play, 'public function setPsychStageGroupCameras(')
        self.assertIn('characterForRole(role)', cameras)
        stage = (ROOT / 'source/PsychBaseStageCompat.hx').read_text(encoding='utf-8')
        group = method(stage, 'function actorGroup(')
        self.assertLess(group.index('readField(field)'), group.index("callTarget(host, 'characterGroupForRole', [role])"))
        self.assertLess(group.index("'characterGroupForRole'"), group.index('new PsychBaseStageActorGroupCompat('))


if __name__ == '__main__':
    unittest.main()
