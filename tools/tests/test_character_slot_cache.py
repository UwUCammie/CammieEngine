"""Change Character takes actors built during loading instead of building mid-song."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_psych_charting_handoff import method

ROOT = Path(__file__).resolve().parents[2]


def run_haxe(test, fixture, *extra):
    with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
        Path(folder, 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
        result = subprocess.run([*HAXE_COMMAND, *extra, '-cp', folder, '--main', 'Main', '--interp'],
                                cwd=ROOT, capture_output=True, text=True, timeout=120)
    test.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class CharacterSlotCacheTest(unittest.TestCase):
    def test_cache_builds_ahead_hands_out_once_and_disposes_leftovers(self):
        run_haxe(self, '''class Actor {
 public var name:String; public var slot:String; public var disposed:Bool = false;
 public function new(slot:String, name:String) {this.slot = slot; this.name = name;}
}
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var built:Array<Actor> = [];
  var cache = new CharacterSlotCache<Actor>(function(slot, name, x, y) {
   if (name == 'broken') return null;
   var actor = new Actor(slot, name); built.push(actor); return actor;
  }, function(actor) actor.disposed = true);
  check(cache.reserve('dad', 'alt', 10, 20) == 1 && built.length == 1, 'first reserve builds one');
  check(cache.reserve('dad', 'alt', 10, 20) == 0 && built.length == 1, 'reserve is idempotent');
  check(cache.reserve('dad', 'alt', 10, 20, 5) == 1 && cache.count('dad', 'alt') == cache.limit, 'limit caps copies');
  check(cache.reserve('boyfriend', 'alt', 0, 0) == 1, 'slots are separate');
  check(cache.reserve('gf', 'broken', 0, 0) == 0, 'failed build is not kept');
  var first = cache.take('dad', 'alt');
  check(first != null && first.actor == built[0] && first.x == 10 && first.y == 20, 'oldest actor and its position');
  var second = cache.take('dad', 'alt');
  check(second != null && second.actor != first.actor, 'each actor is handed out once');
  check(cache.take('dad', 'alt') == null && cache.take('dad', 'unknown') == null, 'empty slot gives null');
  cache.release();
  check(!first.actor.disposed && !second.actor.disposed, 'taken actors belong to the swap');
  check(built[2].disposed, 'leftover actor disposed on release');
  check(cache.count('boyfriend', 'alt') == 0, 'release clears the cache');
 }
}''', '-cp', str(ROOT / 'source'))

    def test_playstate_preloads_every_chart_swap_and_takes_it_at_the_moved_slot(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        methods = '\n'.join(method(play, marker) for marker in (
            'static function changeCharacterSlot(',
            'function preloadSwapCharacter(',
            'function takeSwapCharacter(',
            'static function moveFreshCharacter(',
            'static function disposeSwapCharacter(',
            'function preloadSwapCharacters()',
            'function compatAddCharacterToList(',
        ))
        # swapSlotIndex is a one-line expression body without braces.
        start = play.index('\tstatic function swapSlotIndex(')
        index_line = play[start:play.index('\n\n', start)]
        run_haxe(self, '''using StringTools;
class Point {
 public var x:Float; public var y:Float;
 public function new(x:Float, y:Float) {this.x = x; this.y = y;}
 public function add(dx:Float, dy:Float):Point {x += dx; y += dy; return this;}
}
class Character {
 public var x:Float; public var y:Float; public var name:String; public var destroyed:Bool = false;
 public var curCharacter:String;
 public var originalPosition:Point; public var cameraFocusPoint:Point;
 public function new(x:Float, y:Float, name:String) {
  this.x = x + 5; this.y = y + 7; this.name = name; curCharacter = name;
  originalPosition = new Point(x, y); cameraFocusPoint = new Point(x + 150, y - 100);
 }
 public function destroy():Void {
  if (name == 'throws-on-destroy') throw 'destroy failed';
  destroyed = true;
 }
 public static function characterExists(name:String):Bool return name != 'missing';
}
class CodenameEventDispatch {public static function fromNative(e:Dynamic):Dynamic return null;}
class Main {
 var nightmareVisionScripts:Dynamic = null;
 var nightmareVisionSourceEventsPrepared:Bool = false;
 var swapOffsets = [770.0, 450.0, 400.0, 130.0, 100.0, 100.0];
 var songEvents:Array<Dynamic> = [];
 var SONG:Dynamic = {player1: 'bf', player2: 'dad', gf: 'gf'};
 var swapCharacterCache:CharacterSlotCache<Character>;
 var constructed:Array<String> = [];
 var warmed:Array<String> = [];
 var actors:Array<Character> = [];
 public function new() {}
 function constructSwapCharacter(slot:String, name:String, x:Float, y:Float):Character {
  constructed.push(slot + ':' + name);
  var actor = new Character(x, y, name);
  actors.push(actor);
  return actor;
 }
 function addNightmareVisionCharacterToList(name:String, role:Int):Void throw 'NV path in native fixture';
 function codenameSwapPreloadParams(e:Dynamic):Dynamic return null;
 function codenameSelectedRoot():String return '';
 function currentSongDataPath(name:String):String return 'missing-preload-file.txt';
 function warmCharacterAtlas(name:String, ?isPlayer:Bool = false):Void warmed.push(name);
 @@INDEX@@
 @@METHODS@@
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var state = new Main();
  state.songEvents = [
   {name: 'Change Character', v1: '', v2: 'bf-alt'},
   {name: 'Change Character', v1: 'bf', v2: 'bf'},
   {name: 'Change Character', v1: '1', v2: 'dad-alt'},
   {name: 'Change Character', v1: 'gf', v2: 'gf-alt'},
   {name: 'Change Character', v1: '1', v2: 'dad-alt'},
   {name: 'Change Character', v1: '1', v2: 'dad-alt'},
   {name: 'Change Character', v1: 'dad', v2: 'missing'},
   {name: 'Hey!', v1: '', v2: ''}
  ];
  state.preloadSwapCharacters();
  check(state.constructed.join(',') == 'boyfriend:bf-alt,boyfriend:bf,dad:dad-alt,dad:dad-alt,gf:gf-alt',
   'preloaded ' + state.constructed.join(','));
  check(state.warmed.length == 0, 'chart swaps still used the throwaway atlas warmer');
  // A script preload for an already prepared swap builds nothing more.
  state.compatAddCharacterToList(' dad-alt ', 'dad');
  check(state.constructed.length == 5, 'addCharacterToList duplicated a ready actor');
  state.compatAddCharacterToList('gf-two', 'gf');
  check(state.constructed[5] == 'gf:gf-two', 'addCharacterToList kept nothing for its slot');

  // A script moved the opponent slot after loading.
  state.swapOffsets[4] = 160; state.swapOffsets[5] = 90;
  var built = state.constructed.length;
  var dad = state.takeSwapCharacter('dad', 'dad-alt');
  check(state.constructed.length == built, 'swap built a Character mid-song');
  check(dad.x == 165 && dad.y == 97, 'ready actor not moved with the slot: ' + dad.x + ',' + dad.y);
  check(dad.originalPosition.x == 160 && dad.originalPosition.y == 90, 'original position not moved');
  check(dad.cameraFocusPoint.x == 310 && dad.cameraFocusPoint.y == -10, 'camera focus not moved');
  var again = state.takeSwapCharacter('dad', 'dad-alt');
  check(again != dad && state.constructed.length == built, 'second ready copy');
  var lazy = state.takeSwapCharacter('dad', 'dad-alt');
  check(state.constructed.length == built + 1 && lazy.x == 165, 'past the limit a swap still builds one');
  var bf = state.takeSwapCharacter('boyfriend', 'bf-alt');
  check(bf.x == 775 && bf.y == 457 && state.constructed.length == built + 1, 'unmoved slot keeps its place');

  // The event and the preload read the slot the same way whatever the case.
  check(changeCharacterSlot(' GF ') == 'gf' && changeCharacterSlot('BF') == 'boyfriend'
   && changeCharacterSlot('Boyfriend') == 'boyfriend' && changeCharacterSlot(null) == 'boyfriend'
   && changeCharacterSlot(1) == 'dad' && changeCharacterSlot(2) == 'gf' && changeCharacterSlot('Dad') == 'dad',
   'slot names are case sensitive');
  var cased = new Main();
  cased.songEvents = [{name: 'Change Character', v1: 'GF', v2: 'gf-alt'}];
  cased.preloadSwapCharacters();
  cased.compatAddCharacterToList('gf-alt', 'GF');
  check(cased.constructed.join(',') == 'gf:gf-alt', 'preload slots disagree: ' + cased.constructed.join(','));
  var before = cased.constructed.length;
  cased.takeSwapCharacter(changeCharacterSlot('GF'), 'gf-alt');
  check(cased.constructed.length == before, 'an upper case event missed its preloaded actor');

  // A leftover that fails to destroy does not stop the others being freed.
  var teardown = new Main();
  teardown.compatAddCharacterToList('throws-on-destroy', 'dad');
  teardown.compatAddCharacterToList('dad-alt', 'dad');
  teardown.compatAddCharacterToList('gf-alt', 'gf');
  teardown.swapCharacterCache.release();
  for (actor in teardown.actors)
   check(actor.destroyed == (actor.name != 'throws-on-destroy'), actor.name + ' leftover not freed');
  check(teardown.swapCharacterCache.count('dad', 'dad-alt') == 0 && teardown.swapCharacterCache.count('gf', 'gf-alt') == 0,
   'release stopped at a failing destroy');
 }
}'''.replace('@@INDEX@@', index_line).replace('@@METHODS@@', methods), '-cp', str(ROOT / 'source'))

    def test_switch_character_takes_the_ready_actor_for_every_slot(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        swap = method(play, '\tfunction switchCharacter(charTo:String, charState:String)')
        self.assertNotIn('new Character(', swap)
        for slot in ('boyfriend', 'dad', 'gf'):
            self.assertIn(f"{slot} = takeSwapCharacter('{slot}', charTo);", swap)
        destroy = play[play.index('boyfriendMap=null;dadMap=null;gfMap=null;'):][:200]
        self.assertIn('swapCharacterCache.release()', destroy)


if __name__ == '__main__':
    unittest.main()
