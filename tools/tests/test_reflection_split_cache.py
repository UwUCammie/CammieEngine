"""Property paths reuse their split pieces without changing what they resolve."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


FIXTURE = r'''class Box {
 public var x:Float = 3;
 public var items:Array<Dynamic>;
 public var child:Box;
 public function new(?depth:Int = 0) {
  items = [10, [20, 30]];
  if (depth < 2) child = new Box(depth + 1);
 }
}
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main() {
  for (path in ['a', 'a.b', 'a..b', '.a', 'a.', '', 'game.boyfriend.scale.x']) {
   var first = SourceScriptReflection.dotParts(path);
   var again = SourceScriptReflection.dotParts(path);
   check(first.join('|') == path.split('.').join('|') && first.length == path.split('.').length,
    'split pieces changed for ' + path);
   check(first == again, 'repeated path was split again: ' + path);
  }
  for (i in 0...3000) {
   var path = 'root' + i + '.field';
   check(SourceScriptReflection.dotParts(path).join('|') == 'root' + i + '|field', 'overflow changed ' + path);
  }
  check(@:privateAccess SourceScriptReflection.dotPartsCount <= 1024, 'split cache was not bounded');

  var registry:Map<String, Dynamic> = ['shared' => [1, 2, 3]];
  var reads:Array<String> = [];
  var readProperty = function(object:Dynamic, key:String):Dynamic {reads.push(key); return Reflect.getProperty(object, key);};
  var writeProperty = function(object:Dynamic, key:String, value:Dynamic):Void Reflect.setProperty(object, key, value);
  var isState = function(value:Dynamic):Bool return false;
  var box = new Box();
  check(SourceScriptReflection.readPsychInstancePart(box, 'x', isState, () -> registry, readProperty) == 3,
   'plain field read changed');
  SourceScriptReflection.writePsychPathPart(box, 'x', 9, isState, () -> registry, readProperty, writeProperty);
  check(box.x == 9, 'plain field write changed');
  // Indexed parts still take the split route (string indices are a native
  // target feature, so only the routing is checked here).
  var routed = false;
  try SourceScriptReflection.readPsychInstancePart(box, 'items[1]', isState, () -> registry, readProperty)
  catch (_:Dynamic) routed = true;
  check(reads.join(',') == 'x,items', 'property reads changed: ' + reads.join(','));
  Sys.println('OK');
 }
}
'''


class ReflectionSplitCacheTest(unittest.TestCase):
    def test_split_pieces_are_shared_and_paths_resolve_as_before(self):
        source = (ROOT / 'source/SourcePsychReflection.hx').read_text(encoding='utf-8')
        hot = source[source.index('\tpublic function object('):source.index('\tfunction groupMembers(')]
        self.assertNotIn(".split('.')", hot)
        # call() shifts its pieces, so it must keep a private split.
        self.assertIn("var parts=path.split('.');\n\t\tvar variable:Dynamic", source)
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'Main.hx').write_text(FIXTURE, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                                     '-main', 'Main', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('OK', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
