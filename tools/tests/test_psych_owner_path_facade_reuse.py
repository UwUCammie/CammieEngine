"""Engine bridge calls share one Psych owner Paths facade per owner."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath

ROOT = Path(__file__).resolve().parents[2]


def bridge_members():
    source = (ROOT / "source/PsychOwnerPaths.hx").read_text(encoding="utf-8")
    start = source.index("\tstatic var bridgeFacades")
    end = source.index("\tpublic static function create(")
    return source[start:end]


class PsychOwnerPathFacadeReuseTest(unittest.TestCase):
    def test_bridge_facade_is_reused_until_refresh_release_or_clear(self):
        stubs = {
            "ImportRefreshManager.hx": "class ImportRefreshManager {public static var generation:Int = 0;}",
            "PsychOwnerSoundCache.hx": """class PsychOwnerSoundCache {
 public static var owners:Map<String, PsychOwnerSoundCache> = new Map();
 var released = false;
 public function new() {}
 public static function forOwner(owner:String):PsychOwnerSoundCache {
  var cache = owners.get(owner);
  if (cache == null || cache.released) {cache = new PsychOwnerSoundCache(); owners.set(owner, cache);}
  return cache;
 }
 public function release():Void released = true;
 public function isReleased():Bool return released;
}""",
            "PsychOwnerPaths.hx": "class PsychOwnerPaths {\n" + bridge_members() + """
 public static var built:Int = 0;
 public static function create(ownerRoot:String, ?initialLibrary:String):Dynamic {
  if (ownerRoot == null || ownerRoot == 'missing') throw 'A valid selected import owner root is required';
  built++;
  PsychOwnerSoundCache.forOwner(ownerRoot);
  return {owner:ownerRoot, serial:built};
 }
}""",
            "Main.hx": """class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main() {
  var first = PsychOwnerPaths.bridgeFacade('assets/imported_mods/a');
  for (_ in 0...10) check(PsychOwnerPaths.bridgeFacade('assets/imported_mods/a') == first, 'bridge facade was rebuilt');
  check(PsychOwnerPaths.built == 1, 'repeated bridge calls built more facades');
  var other = PsychOwnerPaths.bridgeFacade('assets/imported_mods/b');
  check(other != first && other.owner == 'assets/imported_mods/b', 'owners shared a facade');
  ImportRefreshManager.generation++;
  var refreshed = PsychOwnerPaths.bridgeFacade('assets/imported_mods/a');
  check(refreshed != first, 'an import refresh kept an old facade');
  PsychOwnerSoundCache.forOwner('assets/imported_mods/a').release();
  var afterRelease = PsychOwnerPaths.bridgeFacade('assets/imported_mods/a');
  check(afterRelease != refreshed, 'a retired owner kept a facade bound to its released sound cache');
  check(PsychOwnerPaths.bridgeFacade('assets/imported_mods/a') == afterRelease, 'the rebuilt facade was not reused');
  PsychOwnerPaths.clearBridgeFacades();
  check(PsychOwnerPaths.bridgeFacade('assets/imported_mods/a') != afterRelease, 'clearing kept a facade');
  var built = PsychOwnerPaths.built;
  var failed = 0;
  for (_ in 0...2) try PsychOwnerPaths.bridgeFacade('missing') catch (_:Dynamic) failed++;
  check(failed == 2 && PsychOwnerPaths.built == built, 'an invalid owner was cached');
  failed = 0;
  try PsychOwnerPaths.bridgeFacade(null) catch (_:Dynamic) failed++;
  check(failed == 1, 'a null owner produced a facade');
 }
}""",
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = FixturePath(directory)
            for name, content in stubs.items():
                (work / name).write_text(content, encoding="utf-8")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_bridge_uses_shared_facade_and_scripts_keep_their_own(self):
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        start = play.index("function compatPsychPathCall(")
        body = play[start:play.index("\n\t}", start)]
        self.assertIn("PsychOwnerPaths.bridgeFacade(ownerRoot)", body)
        self.assertNotIn("PsychOwnerPaths.create(", body)
        # Script-visible Paths objects hold level and translation state and
        # must stay private to each script.
        self.assertIn("interp.variables.set('Paths', PsychOwnerPaths.create(", play)
        self.assertNotIn("variables.set('Paths', PsychOwnerPaths.bridgeFacade(", play)
        destroy = play[play.index("override public function destroy()"):]
        self.assertIn("PsychOwnerPaths.clearBridgeFacades();", destroy)


if __name__ == "__main__":
    unittest.main()
