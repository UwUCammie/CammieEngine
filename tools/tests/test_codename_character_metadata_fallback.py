"""Keep owner metadata safe for legacy-script Codename death actors."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for position in range(opening, len(source)):
        if source[position] == "{":
            depth += 1
        elif source[position] == "}":
            depth -= 1
            if depth == 0:
                return source[start : position + 1]
    raise AssertionError(marker)


class CodenameCharacterMetadataFallbackTest(unittest.TestCase):
    def test_metadata_without_live_definition_uses_initialized_animation_names(self):
        source = (ROOT / "source/Character.hx").read_text()
        orientation = method(source, "\tfunction applyCodenameCharacterOrientation(")
        fixture = r'''class FakeAnimation {
 public var frames:Array<Int>;
 public function new(frames:Array<Int>) this.frames=frames;
}
class FakeAnimationController {
 var names:Array<String>=["singLEFT","singRIGHT","singLEFT-alt","singRIGHT-alt"];
 var animations:Map<String,FakeAnimation>=[
  "singLEFT"=>new FakeAnimation([1]),"singRIGHT"=>new FakeAnimation([2]),
  "singLEFT-alt"=>new FakeAnimation([3]),"singRIGHT-alt"=>new FakeAnimation([4])
 ];
 public function new() {}
 public function getNameList():Array<String> return names;
 public function getByName(name:String):FakeAnimation return animations.get(name);
}
class Character {
 public var codenameLiveDefinition:Dynamic;
 public var isPlayer:Bool;
 public var flipX:Bool;
 public var animation:FakeAnimationController;
 public var animOffsets:Map<String,Array<Dynamic>>=[
  "singLEFT"=>[10,11],"singRIGHT"=>[20,21],
  "singLEFT-alt"=>[30,31],"singRIGHT-alt"=>[40,41]
 ];
 public function new(player:Bool, definition:Dynamic) {
  isPlayer=player; codenameLiveDefinition=definition; flipX=false;
  animation=new FakeAnimationController();
 }
__METHOD__
 public function applyMetadata(metadata:Dynamic):Void
  applyCodenameCharacterOrientation(metadata);
}
class Main {
 static function check(ok:Bool,label:String):Void if(!ok) throw label;
 static function main():Void {
  var legacyDeath=new Character(true,null);
  legacyDeath.applyMetadata({playerOffsets:false});
  check(legacyDeath.flipX,"player slot flip should still apply from owner metadata");
  check(legacyDeath.animation.getByName("singLEFT").frames[0]==2
   && legacyDeath.animation.getByName("singRIGHT").frames[0]==1,
   "legacy death actor must use initialized animation names when no XML definition exists");
  check(legacyDeath.animation.getByName("singLEFT-alt").frames[0]==4
   && legacyDeath.animation.getByName("singRIGHT-alt").frames[0]==3,
   "suffix animations must remain part of Codename orientation");

  var native=new Character(true,{animations:[{name:"singRIGHT-alt"}]});
  native.applyMetadata({playerOffsets:false});
  check(native.animation.getByName("singLEFT-alt").frames[0]==4,
   "live Codename definitions must retain their authored animation-name source");
 }
}'''.replace("__METHOD__", orientation)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            folder = Path(scratch)
            (folder / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", str(folder), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
