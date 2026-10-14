"""Psych's addCharacterToList lists the actor in dadMap/boyfriendMap/gfMap.

Psych scripts swap characters with `game.dad = game.dadMap.get(name)` after
registering the name with addCharacterToList. The map must hold the actor under
its exact name, a native Change Character must reuse it, and a null role write
must not reach native update and draw code.
"""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_psych_charting_handoff import method

ROOT = Path(__file__).resolve().parents[2]


def until_blank_line(source: str, marker: str) -> str:
    start = source.index(marker)
    return source[start:source.index('\n\n', start)]


class PsychRoleMapCharacterListTest(unittest.TestCase):
    def test_add_character_to_list_fills_role_maps_and_native_swap_reuses_them(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        braced = '\n'.join(method(play, marker) for marker in (
            'static function changeCharacterSlot(',
            'function preloadSwapCharacter(',
            'function takeSwapCharacter(',
            'static function moveFreshCharacter(',
            'static function disposeSwapCharacter(',
            'function compatAddCharacterToList(',
            'function publishPsychRoleCharacter(',
            'function idlePsychRoleCharacter(',
            'function characterInSlot(',
            'function detachIdlePsychRoleCharacter(',
            'function adoptIdlePsychRoleCharacter(',
            'function forgetPsychRoleCharacter(',
            'function realignIdlePsychRoleActors(',
            'function set_dad(',
            'function set_gf(',
            'function set_boyfriend(',
            'static function refuseNullRoleActor(',
        ))
        lines = '\n'.join(until_blank_line(play, marker) for marker in (
            '\tstatic function swapSlotIndex(',
            '\tstatic function psychRoleMapFor(',
            '\t@:keep public function addCharacterToList(',
        ))
        start = play.index('\tvar idlePsychRoleActors:')
        idle_field = play[start:play.index(';', start) + 1]
        fixture = '''using StringTools;
class Point {
 public var x:Float; public var y:Float;
 public function new(x:Float, y:Float) {this.x = x; this.y = y;}
 public function add(dx:Float, dy:Float):Point {x += dx; y += dy; return this;}
 public function set(x:Float, y:Float):Point {this.x = x; this.y = y; return this;}
}
class Character {
 public var x:Float; public var y:Float; public var alpha:Float = 1;
 public var curCharacter:String; public var characterType:String = '';
 public var likeGf:Bool = false; public var destroyed:Bool = false;
 public var scrollFactor:Point = new Point(1, 1);
 public var originalPosition:Point; public var cameraFocusPoint:Point;
 public function new(x:Float, y:Float, name:String) {
  if (name == 'broken') throw 'bad character file';
  this.x = x + 5; this.y = y + 7; curCharacter = name;
  originalPosition = new Point(x, y); cameraFocusPoint = new Point(x + 150, y - 100);
 }
 public function setPosition(x:Float, y:Float):Void {this.x = x; this.y = y;}
 public function destroy():Void destroyed = true;
 public static function characterExists(name:String):Bool return name != 'missing';
}
class PlayState {
 var nightmareVisionScripts:Dynamic = null;
 var psychStageCharacterRoot:String = null;
 var curStage:Dynamic = null;
 var swapOffsets = [770.0, 450.0, 400.0, 130.0, 100.0, 100.0];
 var swapCharacterCache:CharacterSlotCache<Character>;
 public var boyfriendMap:Map<String, Character> = new Map();
 public var dadMap:Map<String, Character> = new Map();
 public var gfMap:Map<String, Character> = new Map();
 public var dad(default, set):Character;
 public var gf(default, set):Character;
 public var boyfriend(default, set):Character;
 public var members:Array<Dynamic> = [];
 public var constructed:Array<String> = [];
 public function new(withGf:Bool) {
  if (withGf) gf = new Character(400, 130, 'gf');
  dad = new Character(100, 100, 'dad');
  boyfriend = new Character(770, 450, 'bf');
  if (withGf) members.push(gf);
  members.push(dad); members.push(boyfriend);
 }
 function add(object:Dynamic):Dynamic {if (members.indexOf(object) < 0) members.push(object); return object;}
 function insert(at:Int, object:Dynamic):Dynamic {if (members.indexOf(object) < 0) members.insert(at, object); return object;}
 function remove(object:Dynamic, splice:Bool = false):Dynamic {
  var at = members.indexOf(object);
  if (at >= 0) {if (splice) members.splice(at, 1); else members[at] = null;}
  return object;
 }
 function constructSwapCharacter(slot:String, name:String, x:Float, y:Float):Character {
  constructed.push(slot + ':' + name);
  return new Character(x, y, name);
 }
 // The stage's character folder gives other offsets than the native ones.
 function stageCharacterOffset(actor:Character, role:String):Array<Float>
  return psychStageCharacterRoot == null ? [10, 20] : [30, -5];
 function addNightmareVisionCharacterToList(name:String, role:Int):Void throw 'NV path in Psych fixture';
 @@IDLE@@
 @@LINES@@
 @@METHODS@@
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var state = new PlayState(true);
  var oldDad = state.dad;
  state.compatAddCharacterToList(' Glitchy-Red-Mad ', 'dad');
  var listed = state.dadMap.get('Glitchy-Red-Mad');
  check(listed != null, 'dadMap.get returned null after addCharacterToList');
  check(listed.curCharacter == 'Glitchy-Red-Mad' && listed.characterType == 'dad', 'wrong listed actor');
  check(listed.alpha == 0.00001, 'listed actor is visible before the swap: ' + listed.alpha);
  check(listed.x == 115 && listed.y == 127, 'listed actor not placed in the slot: ' + listed.x + ',' + listed.y);
  check(state.members.indexOf(listed) == state.members.indexOf(oldDad) + 1, 'listed actor not right above the role actor');
  check(state.constructed.join(',') == 'dad:Glitchy-Red-Mad', 'built ' + state.constructed.join(','));
  state.compatAddCharacterToList('Glitchy-Red-Mad', 'dad');
  check(state.constructed.length == 1, 'a second addCharacterToList built another actor');
  check(state.swapCharacterCache == null || state.swapCharacterCache.count('dad', 'Glitchy-Red-Mad') == 0,
   'the listed actor was also kept in the swap cache');

  // The script swap Psych mods run from an event.
  state.dad.alpha = 0.00001;
  state.dad = state.dadMap.get('Glitchy-Red-Mad');
  state.dad.alpha = 1;
  check(state.dad == listed && oldDad.alpha == 0.00001 && state.members.indexOf(oldDad) >= 0, 'script swap');

  // A failed lookup must not leave a null role actor behind.
  state.dad = state.dadMap.get('never-listed');
  check(state.dad == listed, 'null dad write was kept');
  Reflect.setProperty(state, 'dad', null);
  Reflect.setProperty(state, 'boyfriend', null);
  Reflect.setProperty(state, 'gf', null);
  check(state.dad == listed && state.boyfriend != null && state.gf != null, 'reflected null role write was kept');

  // HScript's game.addCharacterToList(name, type) uses Psych's numbers.
  state.addCharacterToList('bf-alt', 0);
  state.addCharacterToList('gf-alt', 2);
  check(state.boyfriendMap.get('bf-alt') != null && state.gfMap.get('gf-alt') != null, 'numeric types not listed');
  check(state.boyfriendMap.get('bf-alt').x == 785 && state.gfMap.get('gf-alt').scrollFactor.x == 0.95, 'numeric placement');
  state.compatAddCharacterToList('missing', 'dad');
  check(!state.dadMap.exists('missing'), 'a missing character was listed');

  // Psych lists nothing for gf when the stage has none; the swap still preloads.
  var noGf = new PlayState(false);
  noGf.compatAddCharacterToList('gf-alt', 'gf');
  check(!noGf.gfMap.exists('gf-alt') && noGf.swapCharacterCache.count('gf', 'gf-alt') == 1, 'gf-less stage');

  // An actor a chart swap already built is listed instead of building another.
  var chart = new PlayState(true);
  chart.preloadSwapCharacter('dad', 'pre');
  chart.compatAddCharacterToList('pre', 'dad');
  check(chart.constructed.join(',') == 'dad:pre' && chart.dadMap.get('pre') != null, 'chart actor not reused');

  // A native Change Character takes the listed actor as if freshly built.
  var native = new PlayState(true);
  native.compatAddCharacterToList('alt', 'dad');
  var waiting = native.dadMap.get('alt');
  native.swapOffsets[4] = 150; native.swapOffsets[5] = 90;
  var previous = native.dad;
  native.forgetPsychRoleCharacter(previous);
  native.detachIdlePsychRoleCharacter('dad', 'alt');
  check(native.members.indexOf(waiting) < 0, 'listed actor still in the scene when layers are read');
  var taken = native.takeSwapCharacter('dad', 'alt');
  check(taken == waiting && native.constructed.length == 1, 'native swap built a new actor');
  check(taken.alpha == 1, 'adopted actor kept the hidden alpha');
  check(taken.x == 155 && taken.y == 97, 'adopted actor not placed like a fresh one: ' + taken.x + ',' + taken.y);
  check(taken.originalPosition.x == 150 && taken.originalPosition.y == 90, 'slot move not carried');
  check(native.dadMap.get('alt') == taken, 'adopted actor left the role map');
  native.dad = taken;
  // Taken already: the next swap to the same name builds its own.
  var again = native.takeSwapCharacter('dad', 'alt');
  check(again != taken && native.constructed.length == 2, 'the current actor was handed out twice');
  // The destroyed previous actor must not come back from the map.
  native.forgetPsychRoleCharacter(taken);
  check(!native.dadMap.exists('alt'), 'destroyed actor still listed');

  // A script that put the listed actor in the role keeps it out of native swaps.
  var shown = new PlayState(true);
  shown.compatAddCharacterToList('alt', 'dad');
  shown.dad = shown.dadMap.get('alt');
  shown.detachIdlePsychRoleCharacter('dad', 'alt');
  check(shown.members.indexOf(shown.dad) >= 0, 'the current actor was taken out of the scene');
  check(shown.takeSwapCharacter('dad', 'alt') != shown.dad, 'the current actor was adopted');

  // A broken character is reported and skipped like the swap preload does,
  // and is not built a second time.
  var broken = new PlayState(true);
  broken.compatAddCharacterToList('broken', 'dad');
  check(!broken.dadMap.exists('broken'), 'broken character listed');
  check(broken.constructed.join(',') == 'dad:broken', 'broken character retried: ' + broken.constructed.join(','));
  check(broken.swapCharacterCache == null || broken.swapCharacterCache.count('dad', 'broken') == 0, 'broken character cached');

  // Listed by a global script before the stage: the stage's character folder
  // and anchors carry the idle actor where Psych's startCharacterPos puts it.
  var early = new PlayState(true);
  early.compatAddCharacterToList('early', 'dad');
  var idle = early.dadMap.get('early');
  check(idle.x == 115 && idle.y == 127, 'early listing placement: ' + idle.x + ',' + idle.y);
  early.psychStageCharacterRoot = 'mods/owner';
  early.swapOffsets[4] = 300; early.swapOffsets[5] = 200;
  early.realignIdlePsychRoleActors();
  check(idle.x == 335 && idle.y == 202, 'stage did not carry the idle actor: ' + idle.x + ',' + idle.y);
  check(idle.originalPosition.x == 300 && idle.originalPosition.y == 200, 'slot move not carried on realign');
  early.realignIdlePsychRoleActors();
  check(idle.x == 335 && idle.y == 202, 'a second realign moved the actor again');
  var adopted = early.takeSwapCharacter('dad', 'early');
  check(adopted == idle && adopted.x == 305 && adopted.y == 207, 'adopt after realign: ' + adopted.x + ',' + adopted.y);

  // An actor a script put in the role is placed by the stage; only its record follows.
  var inRole = new PlayState(true);
  inRole.compatAddCharacterToList('early', 'dad');
  inRole.dad = inRole.dadMap.get('early');
  inRole.psychStageCharacterRoot = 'mods/owner';
  inRole.swapOffsets[4] = 300;
  inRole.realignIdlePsychRoleActors();
  check(inRole.dad.x == 115 && inRole.dad.y == 127, 'realign moved the actor in the role');
 }
}'''.replace('@@IDLE@@', idle_field).replace('@@LINES@@', lines).replace('@@METHODS@@', braced)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            Path(folder, 'PlayState.hx').write_text(fixture, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                                     '--main', 'PlayState', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_role_fields_refuse_null_and_switch_character_forgets_destroyed_actors(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        for role in ('dad', 'gf', 'boyfriend'):
            self.assertIn(f'public var {role}(default, set):Character;', play)
        swap = method(play, '\tfunction switchCharacter(charTo:String, charState:String)')
        self.assertIn('forgetPsychRoleCharacter(previousStageActor);', swap)
        anchor = method(play, 'public function syncPsychStageGroupAnchor(')
        self.assertIn('realignIdlePsychRoleActors();', anchor)
        self.assertIn("setAllHaxeVar('stage', curStage);\n\t\trealignIdlePsychRoleActors();", play)


if __name__ == '__main__':
    unittest.main()
