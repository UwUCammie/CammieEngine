"""Keep authored V-Slice left/right animations attached to their directions."""
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def block(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for position in range(opening, len(source)):
        if source[position] == "{":
            depth += 1
        elif source[position] == "}":
            depth -= 1
            if depth == 0:
                return source[start:position + 1]
    raise AssertionError(marker)


class VSliceCharacterOrientationTest(unittest.TestCase):
    def test_vslice_preserves_authored_pairs_while_legacy_player_still_swaps(self):
        source = (ROOT / "source/Character.hx").read_text()
        orientation = block(
            source,
            "if (codenameCharacterMeta == null && psychAuthoredFlipX == null && isPlayer && !noFlip)",
        )
        fixture = '''
class FakeAnimationDef {
 public var frames:Array<Int>;
 public function new(values:Array<Int>) frames=values;
}
class FakeAnimation {
 public var definitions:Map<String, FakeAnimationDef>=new Map();
 public function new() {}
 public function getByName(name:String):FakeAnimationDef return definitions.get(name);
 public function getNameList():Array<String> return [for (name in definitions.keys()) name];
}
class Main {
 var codenameCharacterMeta:Dynamic=null;
 var psychAuthoredFlipX:Null<Bool>=null;
 var isPlayer:Bool=true;
 var noFlip:Bool=false;
 var flipX:Bool=true;
 var likeBf:Bool=false;
 var isDie:Bool=false;
 var animation:FakeAnimation=new FakeAnimation();
 var animOffsets:Map<String,Array<Dynamic>>=new Map();
 var vSliceBaseFrames:Dynamic=null;
 public function new() {}
 function orient():Void {
__ORIENTATION__
 }
 static function check(ok:Bool, label:String):Void if(!ok) throw label;
 static function actor(imported:Bool):Main {
  var value=new Main();
  value.animation.definitions.set('singLEFT',new FakeAnimationDef([1]));
  value.animation.definitions.set('singRIGHT',new FakeAnimationDef([3]));
  value.animOffsets.set('singLEFT',[10,11]);
  value.animOffsets.set('singRIGHT',[20,21]);
  if(imported) value.vSliceBaseFrames={};
  return value;
 }
 static function main():Void {
  var imported=actor(true);
  imported.orient();
  check(!imported.flipX,'V-Slice BF slot should still apply its horizontal flip');
  check(imported.animation.getByName('singLEFT').frames[0]==1,
   'V-Slice singLEFT must keep the donor left frames');
  check(imported.animation.getByName('singRIGHT').frames[0]==3,
   'V-Slice singRIGHT must keep the donor right frames');
  check(imported.animOffsets.get('singLEFT')[0]==10 && imported.animOffsets.get('singRIGHT')[0]==20,
   'V-Slice offsets must stay attached to the authored animation names');

  var legacy=actor(false);
  legacy.orient();
  check(!legacy.flipX,'legacy BF slot should still apply its horizontal flip');
  check(legacy.animation.getByName('singLEFT').frames[0]==3 &&
   legacy.animation.getByName('singRIGHT').frames[0]==1,
   'legacy player-facing frame swap changed');
  check(legacy.animOffsets.get('singLEFT')[0]==20 && legacy.animOffsets.get('singRIGHT')[0]==10,
   'legacy offsets must follow their reassigned frame lists');

  var psych=actor(false);
  psych.psychAuthoredFlipX=true;
  psych.orient();
  check(psych.flipX && psych.animation.getByName('singLEFT').frames[0]==1,
   'Psych orientation path was changed');

  var codename=actor(false);
  codename.codenameCharacterMeta={playerOffsets:false};
  codename.orient();
  check(codename.flipX && codename.animation.getByName('singLEFT').frames[0]==1,
   'Codename orientation path was changed');
 }
}
'''.replace("__ORIENTATION__", orientation)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            folder = Path(scratch)
            (folder / "Main.hx").write_text(fixture)
            (folder / "CharacterAnimationOrientation.hx").write_text(
                (ROOT / "source/CharacterAnimationOrientation.hx").read_text()
            )
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(folder), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
