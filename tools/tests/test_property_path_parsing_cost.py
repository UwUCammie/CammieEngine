"""Cheaper property path parsing returns exactly what the old code returned."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def method(source, marker):
    start = source.index(marker)
    depth = 0
    for index in range(source.index('{', start), len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError('unterminated ' + marker)


FIXTURE = r'''using StringTools;
class EngineCompat {
__ENGINE__
 // The old implementation, kept verbatim as the reference.
 public static function oldPropertyPath(path:Dynamic):String {
  if (path == null) return '';
  var value = StringTools.trim(Std.string(path));
  if (value == '') return value;
  value = StringTools.replace(value, '\\', '.');
  for (prefix in ['game.', 'currentPlayState.', 'PlayState.instance.', 'states.PlayState.instance.']) {
   if (value.startsWith(prefix)) { value = value.substr(prefix.length); break; }
  }
  if (value == 'states.PlayState' || value == 'PlayState.instance') return 'PlayState';
  if (value.toLowerCase() == 'combogroup.visible') return 'showRatings';
  var dot = value.indexOf('.');
  var root = dot < 0 ? value : value.substr(0, dot);
  var suffix = dot < 0 ? '' : value.substr(dot);
  return propertyRoot(root) + suffix;
 }
}
class Host {
 public var sourceHUDBarMode:Int = 1;
 public var sourceHUDIconMode:Int = 1;
 public function new() {}
__PLAY__
 public function oldBar(name:String):Bool
  return sourceHUDBarMode != 0 && ['healthbar', 'healthbarbg', 'timebar', 'timebarbg', 'songposbar', 'songposbg'].indexOf(name.toLowerCase()) >= 0;
 public function oldIcon(name:String):Bool
  return sourceHUDIconMode != 0 && (name.toLowerCase() == 'iconp1' || name.toLowerCase() == 'iconp2');
 public function oldTokens(path:String):Array<String> {
  var tokens:Array<String> = [];
  if (path == null || StringTools.trim(path) == '') return tokens;
  var clean = StringTools.replace(path, '\\', '.');
  var current = '';
  var i = 0;
  while (i < clean.length) {
   var character = clean.charAt(i);
   if (character == '.') {
    if (StringTools.trim(current) != '') { tokens.push(StringTools.trim(current)); current = ''; }
    i++; continue;
   }
   if (character == '[') {
    if (StringTools.trim(current) != '') { tokens.push(StringTools.trim(current)); current = ''; }
    var close = clean.indexOf(']', i + 1);
    if (close < 0) { current += clean.substr(i); i = clean.length; continue; }
    var index = StringTools.trim(clean.substr(i + 1, close - i - 1));
    if (index.length >= 2) {
     var first = index.charAt(0);
     var last = index.charAt(index.length - 1);
     if ((first == '"' && last == '"') || (first == "'" && last == "'")) index = index.substr(1, index.length - 2);
    }
    if (index != '') tokens.push('[' + index + ']');
    i = close + 1; continue;
   }
   current += character;
   i++;
  }
  if (StringTools.trim(current) != '') tokens.push(StringTools.trim(current));
  return tokens;
 }
}
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main() {
  var host = new Host();
  var paths:Array<String> = [null, '', '   ', 'health', ' boyfriend.x ', 'a..b', 'a. .b', '.a.', 'a\\b\\c',
   'healthColorArray[1]', 'touches.list[0].screenX', 'notes.members[ 2 ].x', "map['key'].value",
   'map["k"]', 'x[]y', 'open[bracket.tail', '  [0]x', 'a [1] b', '[', ']', 'a]b', 'x["q\']', 'é.ü[ä]',
   'iconP1.scale.x', 'a.b.c.d.e.f'];
  for (path in paths) {
   var got = host.compatPathTokens(path).join('|');
   var want = host.oldTokens(path).join('|');
   check(got == want, 'tokens changed for ' + path + ': ' + got + ' / ' + want);
  }
  var names = ['healthBar', 'HEALTHBARBG', 'timeBar', 'timebarBG', 'songPosBar', 'songposbg', 'healthbars',
   'iconP1', 'ICONP2', 'iconP3', 'icon', '', 'x', 'healthBarOverlay', 'songPos', 'iconp1 '];
  for (mode in [0, 1, 2]) {
   host.sourceHUDBarMode = mode; host.sourceHUDIconMode = mode;
   for (name in names) {
    check(host.isSourceHUDBarAlias(name) == host.oldBar(name), 'bar alias changed for ' + name);
    check(host.isSourceHUDIconAlias(name) == host.oldIcon(name), 'icon alias changed for ' + name);
   }
  }
  var inputs:Array<Dynamic> = [null, '', ' game.health ', 'currentPlayState.camFollow.x', 'PlayState.instance',
   'states.PlayState', 'states.PlayState.instance.dad.x', 'comboGroup.visible', 'cameraSpeed', 'camOther.alpha',
   'a\\b', 42, 1.5, true, 'opponentStrums.members[0].x'];
  for (round in 0...2) for (input in inputs)
   check(EngineCompat.propertyPath(input) == EngineCompat.oldPropertyPath(input),
    'propertyPath changed for ' + Std.string(input) + ' on round ' + round);
  for (i in 0...3000) {
   var path = 'game.field' + i + '.x';
   check(EngineCompat.propertyPath(path) == EngineCompat.oldPropertyPath(path), 'cache overflow changed ' + path);
  }
  check(@:privateAccess EngineCompat.propertyPathCount <= 1024, 'property path cache was not bounded');
  Sys.println('OK');
 }
}
'''


class PropertyPathParsingCostTest(unittest.TestCase):
    def test_tokens_aliases_and_paths_match_the_old_code(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        engine = (ROOT / 'source/EngineCompat.hx').read_text(encoding='utf-8')
        tokens = method(play, '\tfunction compatPathTokens(')
        self.assertNotIn('current += character', tokens)
        bar = method(play, '\tfunction isSourceHUDBarAlias(')
        self.assertNotIn('[\'healthbar\'', bar)
        icon = method(play, '\tfunction isSourceHUDIconAlias(')
        play_methods = '\n'.join(m.replace('\tfunction ', ' public function ', 1) for m in (tokens, bar, icon))
        cache_start = engine.index('\tstatic inline var PROPERTY_PATH_CACHE_LIMIT')
        engine_text = engine[cache_start:engine.index('\tpublic static function propertyPath(', cache_start)]
        engine_text += '\n'.join(method(engine, marker) for marker in (
            '\tpublic static function propertyPath(', '\tstatic function resolvePropertyPath(',
            '\tpublic static function propertyRoot('))
        self.assertNotIn("for (prefix in ['game.'", engine_text)
        fixture = FIXTURE.replace('__ENGINE__', engine_text).replace('__PLAY__', play_methods)
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'Main', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('OK', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
