"""Psych's psychlua.LuaUtils helpers that HScript and runHaxeCode import, on the engine's own objects."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

STUBS = {
    'flixel/FlxCamera.hx': 'package flixel;\nclass FlxCamera { public var name:String; public function new(n:String) name = n; }',
    'flixel/FlxState.hx': 'package flixel;\nclass FlxState { public function new() {} }',
    'flixel/FlxG.hx': 'package flixel;\nclass FlxG { public static var state:FlxState; public static var camera = new FlxCamera("game"); }',
    'flixel/tweens/FlxTween.hx': 'package flixel.tweens;\nenum FlxTweenType { BACKWARD; LOOPING; PERSIST; PINGPONG; ONESHOT; }\nclass FlxTween {}',
    'openfl/display/BlendMode.hx': 'package openfl.display;\nenum BlendMode { NORMAL; ADD; }',
    'CoolUtil.hx': '''class CoolUtil {
 public static function getEaseFromString(ease:String):Float->Float return function(t) return t;
 public static function getBlendFromString(blend:String):openfl.display.BlendMode return openfl.display.BlendMode.NORMAL;
}''',
    'MusicBeatState.hx': 'class MusicBeatState extends flixel.FlxState { public var variables:Map<String, Dynamic> = []; public var boyfriendGroup:Dynamic = {x: 4}; }',
    'PlayState.hx': '''class PlayState extends MusicBeatState {
 public static var instance:PlayState;
 public var luaTagged:Map<String, Dynamic> = [];
 function compatCameraForName(name:Dynamic):flixel.FlxCamera return new flixel.FlxCamera(name);
 public function getLuaObject(tag:String, text:Bool = true):Dynamic return luaTagged.get(tag);
}''',
}

MAIN = r'''class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main() {
  check(PsychLuaUtilsCompat.isOfTypes(3, [String, Int]) && !PsychLuaUtilsCompat.isOfTypes('x', [Int, Bool]), 'isOfTypes');
  var map:Map<String, Dynamic> = ['a' => 1];
  check(PsychLuaUtilsCompat.isMap(map) && !PsychLuaUtilsCompat.isMap({a: 1}) && !PsychLuaUtilsCompat.isMap(null), 'isMap');
  check(PsychLuaUtilsCompat.isLuaSupported(null) && PsychLuaUtilsCompat.isLuaSupported([1]) && PsychLuaUtilsCompat.isLuaSupported({a: 1})
   && !PsychLuaUtilsCompat.isLuaSupported(new flixel.FlxCamera('x')), 'isLuaSupported');
  var group:Dynamic = {child: {value: 2}, table: map};
  check(PsychLuaUtilsCompat.getGroupStuff(group, 'child.value') == 2, 'dotted group read');
  PsychLuaUtilsCompat.setGroupStuff(group, 'child.value', 5);
  check(group.child.value == 5, 'dotted group write');
  PsychLuaUtilsCompat.setGroupStuff(group, 'table.b', 7, true);
  check(map.get('b') == 7 && PsychLuaUtilsCompat.getGroupStuff(group, 'table.b', true) == 7, 'map access when allowed');
  var nested:Map<String, Dynamic> = ['inner' => {value: 9}];
  check(PsychLuaUtilsCompat.getGroupStuff({table: nested}, 'table.inner.value', true) == 9, 'reads step through maps when allowed');
  check(PsychLuaUtilsCompat.getGroupStuff({table: nested}, 'table.inner.value') == null, 'maps are not read through unless allowed');
  // An object that only looks like a map is still called, never cast.
  var lookalike:Dynamic = {store: new Map<String, Dynamic>()};
  lookalike.exists = function(k:String) return lookalike.store.exists(k);
  lookalike.keyValueIterator = function() return lookalike.store.keyValueIterator();
  lookalike.get = function(k:String) return lookalike.store.get(k);
  lookalike.set = function(k:String, v:Dynamic) lookalike.store.set(k, v);
  PsychLuaUtilsCompat.setGroupStuff({holder: lookalike}, 'holder.key', 3, true);
  check(PsychLuaUtilsCompat.getGroupStuff({holder: lookalike}, 'holder.key', true) == 3, 'duck-typed maps');
  var game = new PlayState();
  PlayState.instance = game;
  flixel.FlxG.state = game;
  game.variables.set('tagged', 'sprite');
  check(PsychLuaUtilsCompat.getObjectDirectly('game') == game && PsychLuaUtilsCompat.getObjectDirectly('this') == game, 'game aliases');
  check(PsychLuaUtilsCompat.getObjectDirectly('tagged') == 'sprite', 'script variables come first');
  check(PsychLuaUtilsCompat.getObjectDirectly('boyfriendGroup').x == 4, 'then fields of the state');
  game.luaTagged.set('luaSprite', 'tagged-by-lua');
  game.luaTagged.set('tagged', 'lua-wins');
  check(PsychLuaUtilsCompat.getObjectDirectly('luaSprite') == 'tagged-by-lua', 'in a song, Lua-tagged objects are found');
  check(PsychLuaUtilsCompat.getObjectDirectly('tagged') == 'lua-wins', 'in a song, the Lua getProperty lookup decides first');
  flixel.FlxG.state = new flixel.FlxState();
  check(PsychLuaUtilsCompat.getObjectDirectly('tagged') == null, 'a non-song state has no script variables');
  check(PsychLuaUtilsCompat.typeToString(1) == 'boolean' && PsychLuaUtilsCompat.typeToString(5) == 'table'
   && PsychLuaUtilsCompat.typeToString(0) == 'nil' && PsychLuaUtilsCompat.typeToString(-1) == 'nil'
   && PsychLuaUtilsCompat.typeToString(9) == 'unknown', 'typeToString');
  check(PsychLuaUtilsCompat.cameraFromString('hud').name == 'hud', 'cameras still route through the song');
 }
}
'''


class PsychLuaUtilsFacadeTest(unittest.TestCase):
    def test_lua_utils_helpers(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            root = Path(folder)
            for relative, text in STUBS.items():
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                (root / relative).write_text(text, newline='\n')
            (root / 'PsychLuaUtilsCompat.hx').write_text(
                (ROOT / 'source/PsychLuaUtilsCompat.hx').read_text(encoding='utf-8'), newline='\n')
            (root / 'Main.hx').write_text(MAIN, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'Main', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_bound_for_hscript_and_run_haxe_code(self):
        bindings = (ROOT / 'source/PsychHscriptSourceBindings.hx').read_text(encoding='utf-8')
        self.assertIn("variables.set('LuaUtils', PsychLuaUtilsCompat);", bindings)
        aliases = (ROOT / 'source/PsychHscriptCompat.hx').read_text(encoding='utf-8')
        self.assertIn("'psychlua.LuaUtils' => 'LuaUtils'", aliases)


if __name__ == '__main__':
    unittest.main()
