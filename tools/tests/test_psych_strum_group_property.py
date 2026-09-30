"""Psych group access must honor FlxSpriteGroup's members getter."""

from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


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


class PsychStrumGroupPropertyTest(unittest.TestCase):
    def test_live_group_getter_is_used_for_psych_group_and_bracket_access(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        source = (ROOT / "source/PlayState.hx").read_text()
        method_names = (
            "compatPathIndex", "compatReadPathPart", "compatWritePathPart",
            "compatGroupMember", "compatGetPropertyFromGroup", "compatSetPropertyFromGroup",
        )
        methods = "\n".join(source_method(source, name) for name in method_names)
        fixture = r'''class GetterGroup {
 public var members(get, never):Array<Dynamic>;
 var items:Array<Dynamic>;
 public var reads:Int = 0;
 public function new(items:Array<Dynamic>) this.items = items;
 function get_members():Array<Dynamic> { reads++; return items; }
}
class EmptyGroup {
 public var members:Array<Dynamic> = [];
 public function new() {}
}
class PsychStrumGroupPropertyFixture {
 static function main() {
  var left:Dynamic = {x: 100.0};
  var right:Dynamic = {x: 200.0};
  var group = new GetterGroup([left, right]);
  var bridge = new ExtractedBridge(group);
  if(bridge.getGroup("playerStrums", 1, "x") != 200.0)
   throw "getPropertyFromGroup missed getter-backed members";
  bridge.setGroup("playerStrums", 0, "x", 125.0);
  if(left.x != 125.0) throw "setPropertyFromGroup missed getter-backed members";
  if(bridge.readBracket(group, "[1]") != right)
   throw "bracket read missed getter-backed members";
  bridge.writeBracket(group, "[1]", left);
  if(group.members[1] != left) throw "bracket write missed getter-backed members";
  if(group.reads < 4) throw "members getter was not invoked";
  Sys.println("OK");
 }
}
class ExtractedBridge {
 var group:Dynamic;
 var enemyStrums:EmptyGroup;
 var playerStrums:EmptyGroup;
 var boyfriend:Dynamic;
 var dad:Dynamic;
 var gf:Dynamic;
 var iconP1:Dynamic;
 var iconP2:Dynamic;
 public function new(group:Dynamic) {
  this.group = group;
  enemyStrums = new EmptyGroup();
  playerStrums = new EmptyGroup();
 }
 function compatGetProperty(_name:Dynamic):Dynamic return group;
 function compatNoteSplashAt(_index:Int):Dynamic return null;
 function compatCoercePropertyValue(_target:Dynamic, _field:String, value:Dynamic):Dynamic return value;
 function compatReadPath(target:Dynamic, path:String):Dynamic return compatReadPathPart(target, path);
 function compatWritePath(target:Dynamic, path:String, value:Dynamic):Bool return compatWritePathPart(target, path, value);
 public function getGroup(g:Dynamic, n:Dynamic, p:Dynamic):Dynamic return compatGetPropertyFromGroup(g, n, p);
 public function setGroup(g:Dynamic, n:Dynamic, p:Dynamic, value:Dynamic):Void compatSetPropertyFromGroup(g, n, p, value);
 public function readBracket(target:Dynamic, path:String):Dynamic return compatReadPathPart(target, path);
 public function writeBracket(target:Dynamic, path:String, value:Dynamic):Bool return compatWritePathPart(target, path, value);
 __METHODS__
}'''.replace("__METHODS__", methods)
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "PsychStrumGroupPropertyFixture.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "-cp", str(ROOT / "source"),
                 "--run", "PsychStrumGroupPropertyFixture"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
