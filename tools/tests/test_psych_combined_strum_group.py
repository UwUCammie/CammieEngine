"""Psych's combined receptor group maps to the two native live strumlines."""

from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"


def source_method(source: str, name: str) -> str:
    match = re.search(r"\bfunction\s+" + name + r"\s*\(", source)
    if match is None:
        raise AssertionError(f"missing {name}")
    start = source.index("{", match.end())
    depth = 0
    for index in range(start, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[match.start():index + 1]
    raise AssertionError(f"unclosed {name}")


class PsychCombinedStrumGroupTest(unittest.TestCase):
    def test_group_access_uses_live_enemy_then_player_receptors(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        source = (ROOT / "source" / "PlayState.hx").read_text()
        methods = "\n".join(
            source_method(source, name)
            for name in (
                "compatGroupMember",
                "compatGetPropertyFromGroup",
                "compatSetPropertyFromGroup",
            )
        )
        fixture = r'''class FixtureGroup {
 public var members:Array<Dynamic>;
 public function new(members:Array<Dynamic>) this.members = members;
}
class PsychCombinedStrumGroupFixture {
 static function receptors(offset:Int, count:Int):Array<Dynamic> {
  var result:Array<Dynamic> = [];
  for (i in 0...count) result.push({y: offset + i});
  return result;
 }
 static function main() {
  var enemy4 = receptors(100, 4);
  var player4 = receptors(200, 4);
  var legacyItems = [{y: 900}];
  var four = new ExtractedBridge(new FixtureGroup(enemy4),
   new FixtureGroup(player4), new FixtureGroup(legacyItems));
  if (four.getGroup("strumLineNotes", 0, "y") != 100
   || four.getGroup("strumLineNotes", 3, "y") != 103
   || four.getGroup("strumLineNotes", 4, "y") != 200
   || four.getGroup("STRUMLINENOTES", 7, "y") != 203)
   throw "4-key combined group ordering was not enemy then player";
  if (four.groupMember("strumLineNotes", -1) != null
   || four.groupMember("strumLineNotes", 8) != null)
   throw "combined group returned an out-of-range receptor";
  four.setGroup("strumLineNotes", 6, "y", 250);
  if (player4[2].y != 250)
   throw "combined group write did not reach the live player receptor";
  if (four.getGroup("legacy", 0, "y") != 900)
   throw "ordinary group lookup changed";

  var enemy8 = receptors(1000, 8);
  var player8 = receptors(2000, 8);
  var eight = new ExtractedBridge(new FixtureGroup(enemy8),
   new FixtureGroup(player8), new FixtureGroup(legacyItems));
  if (eight.getGroup("strumLineNotes", 7, "y") != 1007
   || eight.getGroup("strumLineNotes", 8, "y") != 2000
   || eight.getGroup("strumLineNotes", 15, "y") != 2007
   || eight.groupMember("strumLineNotes", 16) != null)
   throw "8-key combined group did not use the live side lengths";
  Sys.println("OK");
 }
}
class ExtractedBridge {
 var enemyStrums:FixtureGroup;
 var playerStrums:FixtureGroup;
 var legacy:FixtureGroup;
 public function new(enemy:FixtureGroup, player:FixtureGroup, legacy:FixtureGroup) {
  enemyStrums = enemy;
  playerStrums = player;
  this.legacy = legacy;
 }
 function compatNoteSplashAt(_index:Int):Dynamic return null;
 function compatGetProperty(groupName:Dynamic):Dynamic
  return Std.string(groupName).toLowerCase() == "legacy" ? legacy : null;
 function compatReadPath(target:Dynamic, path:String):Dynamic
  return target == null ? null : Reflect.getProperty(target, path);
 function compatWritePath(target:Dynamic, path:String, value:Dynamic):Bool {
  if (target == null) return false;
  Reflect.setProperty(target, path, value);
  return true;
 }
 public function groupMember(name:Dynamic, index:Dynamic):Dynamic
  return compatGroupMember(name, index);
 public function getGroup(name:Dynamic, index:Dynamic, property:Dynamic):Dynamic
  return compatGetPropertyFromGroup(name, index, property);
 public function setGroup(name:Dynamic, index:Dynamic, property:Dynamic, value:Dynamic):Void
  compatSetPropertyFromGroup(name, index, property, value);
 __METHODS__
}'''.replace("__METHODS__", methods)
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "PsychCombinedStrumGroupFixture.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "-cp", str(ROOT / "source"),
                 "--run", "PsychCombinedStrumGroupFixture"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
