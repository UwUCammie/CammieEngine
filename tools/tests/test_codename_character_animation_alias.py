"""Codename's hasAnim API must resolve on native imported Characters."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import json
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class CodenameCharacterAnimationAliasTest(unittest.TestCase):
    def test_source_callback_uses_native_character_animation_query(self):
        compat_source = (ROOT / "source/CodenameScriptInterp.hx").read_text()
        source_field = extract_method(compat_source, "function sourceField(")
        self.assertIn("if (field == 'hasAnim') return 'hasAnimation';", source_field)

        character_source = (ROOT / "source/Character.hx").read_text()
        self.assertIn("public function hasAnimation(name:String):Bool", character_source)
        self.assertIn("return name != null && animation != null && animation.exists(name);",
                      character_source)

        fixture = r"""import hscript.Interp;
import hscript.Parser;

class Actor implements CodenameCharacterAccess {
 public var codenameSourceId:String;
 public var animations:Array<String>;
 public var calls:Array<String> = [];
 public function new(id:String, animations:Array<String>) {
  codenameSourceId = id;
  this.animations = animations;
 }
 public function hasAnimation(name:String):Bool
  return name != null && animations.indexOf(name) >= 0;
 public function playAnim(name:String, force:Bool=false, reverse:Bool=false, frame:Int=0):Void
  calls.push('native:' + name + ':' + force);
 public function codenamePlayAnim(name:String, ?force:Null<Bool>, context:Dynamic=null,
  reverse:Bool=false, frame:Int=0):Void calls.push('source:' + name + ':' + force);
 public function codenameTryDance():Void {}
}

class CompatInterp extends Interp {
 var scriptObject:Dynamic = null;
 var scriptObjectAliases:Map<String, String> = new Map();
 var scriptObjectFields:Map<String, Bool> = new Map();
 SOURCE_FIELD
 override function get(object:Dynamic, field:String):Dynamic
  return super.get(object, sourceField(object, field));
}

class Main {
 static function check(ok:Bool, why:String):Void if (!ok) throw why;
 static function main():Void {
  var borrowedActor = new Actor(null, ['cheer']);
  var sourceActor = new Actor('codename-stage-actor', ['cheer']);
  var strumLines = {members:[null, null, {characters:[borrowedActor, sourceActor]}]};
  var interp = new CompatInterp();
  interp.variables.set('strumLines', strumLines);
  interp.variables.set('gf', {});
  interp.variables.set('combo', 50);
  interp.variables.set('canPlayGFAnims', true);
  interp.execute(new Parser().parseString(SCRIPT_SOURCE));
  var callback:Dynamic = interp.variables.get('onPostNoteHit');
  callback({note:{strumLine:{cpu:false}}});
  check(borrowedActor.calls.join(',') == 'native:cheer:true',
   'hasAnim was not bridged for a borrowed Character without Codename identity');
  check(sourceActor.calls.join(',') == 'source:cheer:true',
   'Codename source actor did not retain its playAnim compatibility route');
 }
}
""".replace("SOURCE_FIELD", source_field).replace("SCRIPT_SOURCE", json.dumps(
            "function onPostNoteHit(e) {\n"
            + " if (canPlayGFAnims && e.note.strumLine.cpu == false) {\n"
            + "  if (gf != null) {\n"
            + "   for (chars in strumLines.members[2].characters) {\n"
            + "    if (combo == 50) {\n"
            + "     if (chars.hasAnim('combo50')) chars.playAnim('combo50', true);\n"
            + "     else if (chars.hasAnim('cheer')) chars.playAnim('cheer', true);\n"
            + "    }\n"
            + "   }\n"
            + "  }\n"
            + " }\n"
            + "}\n"))

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            main = Path(folder) / "Main.hx"
            main.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND,
                 "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", folder, "--run", "Main"],
                cwd=ROOT, text=True, capture_output=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn('[hscript-null-access] call to "hasAnim"', result.stdout)


if __name__ == "__main__":
    unittest.main()
