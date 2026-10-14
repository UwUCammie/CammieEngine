"""Psych and NV alphabet registries share one owner context registry."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import ROOT, HAXE_COMMAND


MAIN = r'''class FakeContext {
 public var owner:String; public var released = false; public var rebinds = 0;
 public function new(owner:String) this.owner = owner;
 public function release():Void released = true;
 public function rebindOwner(owner:String):Void {this.owner = owner; rebinds++;}
}
class Main {
 static function eq(actual:Dynamic, expected:Dynamic, label:String):Void
  if (actual != expected) throw label + ': ' + actual + ' != ' + expected;
 static function main() {
  var sessions = 0;
  var registry = new SourceOwnerContextRegistry<FakeContext>(function(c) c.release(), function() sessions++);
  registry.enterSession('assets/imported_mods/a');
  eq(sessions, 1, 'first session');
  var created = 0;
  function get(root:String, owner:String):FakeContext
   return registry.get(root, function() {created++; return new FakeContext(owner);}, function(c) c.rebindOwner(owner));
  var first = get('assets/imported_mods/a', 'view-1');
  var again = get('assets/imported_mods/a', 'view-2');
  eq(first, again, 'same root reuses the context');
  eq(created, 1, 'created once');
  eq(first.owner, 'view-2', 'reuse points it at the newest owner view');
  eq(first.rebinds, 1, 'rebound once');
  var other = get('assets/imported_mods/b', 'view-3');
  registry.enterSession('assets/imported_mods/a');
  eq(first.released, false, 'same primary owner keeps its contexts');
  eq(sessions, 1, 'no session change');
  registry.enterSession('assets/imported_mods/c');
  eq(first.released && other.released, true, 'a new primary owner releases every context');
  eq(registry.existing('assets/imported_mods/a'), null, 'released contexts are forgotten');
  eq(sessions, 2, 'session change reported');
  registry.enterSession(null);
  eq(sessions, 3, 'leaving to no owner');
  registry.enterSession('');
  eq(sessions, 3, 'empty and null roots are the same session');
  var fresh = get('assets/imported_mods/a', 'view-4');
  eq(fresh == first, false, 'a new session makes a new context');
  trace('registry-ok');
 }
}
'''


class SourceOwnerContextRegistryTest(unittest.TestCase):
    def test_reuse_rebind_release_and_empty_root(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = Path(folder)
            (work / 'Main.hx').write_text(MAIN, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(work),
                '-main', 'Main', '--interp'], cwd=work, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('registry-ok', result.stdout)

    def test_both_alphabet_registries_use_it(self):
        for name in ('NightmareVisionAlphabetRegistry.hx', 'PsychAlphabetRegistry.hx'):
            text = (ROOT / 'source' / name).read_text(encoding='utf-8')
            self.assertIn('new SourceOwnerContextRegistry<', text, name)
            self.assertNotIn('static var primaryRoot', text, name + ' keeps its own session state')


if __name__ == '__main__':
    unittest.main()
