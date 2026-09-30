"""Keep Psych direction labels and named offsets intact for imported characters."""

from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "tmp"
PSYCH_ARCHIVE = ROOT / "tmp/psych-archive-source/FNF-PsychEngine-main"
PSYCH_CHARACTER = PSYCH_ARCHIVE / "source/objects/Character.hx"
PSYCH_BF = PSYCH_ARCHIVE / "assets/shared/characters/bf.json"


class PsychCharacterOrientationTest(unittest.TestCase):
    def test_runtime_uses_selected_psych_definition_and_psych_slot_flip(self):
        if not PSYCH_CHARACTER.is_file() or not PSYCH_BF.is_file():
            self.skipTest("mounted Psych source archive is unavailable")

        psych_source = PSYCH_CHARACTER.read_text()
        self.assertIn("flipX = (json.flip_x != isPlayer);", psych_source)
        self.assertIn("if(anim.offsets != null && anim.offsets.length > 1) addOffset", psych_source)

        bf_metadata = PSYCH_BF.read_text()
        self.assertIn('"flip_x": true', bf_metadata)

        character_source = (ROOT / "source/Character.hx").read_text()
        self.assertIn("PsychCharacterOrientation.authoredFlipX(curCharacter", character_source)
        self.assertIn("flipX = PsychCharacterOrientation.flipX(psychAuthoredFlipX, isPlayer);",
                      character_source)
        # The legacy direction swap is skipped only when a Psych owner definition
        # was found; non-Psych custom characters retain the existing behavior.
        self.assertIn(
            "if (codenameCharacterMeta == null && psychAuthoredFlipX == null && isPlayer && !noFlip)",
            character_source,
        )

        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            work = Path(folder)
            (work / "PsychCharacterOrientation.hx").write_text(
                (ROOT / "source/PsychCharacterOrientation.hx").read_text())
            psych_json = work / "scope/shared/characters/bf.json"
            psych_json.parent.mkdir(parents=True)
            shutil.copyfile(PSYCH_BF, psych_json)
            (work / "scope/characters/native.json").parent.mkdir(parents=True)
            (work / "scope/characters/native.json").write_text('{"flip_x":false}')
            (work / "PsychCharacterOrientationProbe.hx").write_text(r'''import PsychCharacterOrientation;
import sys.io.File;
class PsychCharacterOrientationProbe {
  static function check(ok:Bool, label:String):Void if (!ok) throw label;
  static function main():Void {
    var readText = function(path:String):Null<String>
      return sys.FileSystem.exists(path) ? File.getContent(path) : null;
    var authored = PsychCharacterOrientation.authoredFlipX("bf", "scope", readText);
    check(authored == true, "BF flip_x was not read from the selected shared character JSON");
    check(!PsychCharacterOrientation.flipX(authored, true),
      "Psych BF player flip must equal authored true XOR player slot");
    check(PsychCharacterOrientation.flipX(authored, false),
      "Psych BF opponent flip must preserve authored true");
    var native = PsychCharacterOrientation.authoredFlipX("native", "scope", readText);
    check(native == false, "an explicit Psych flip_x false must remain distinguishable from missing JSON");
    check(PsychCharacterOrientation.flipX(native, true),
      "Psych player slot must invert explicit authored false");
    check(PsychCharacterOrientation.authoredFlipX("missing", "scope", readText) == null,
      "missing metadata must leave the native orientation path enabled");
    check(PsychCharacterOrientation.authoredFlipX("../bf", "scope", readText) == null,
      "unsafe character ids must not read owner metadata");

    var json:Dynamic = haxe.Json.parse(File.getContent("scope/shared/characters/bf.json"));
    var directions:Map<String,Dynamic> = new Map();
    for (animation in (cast json.animations:Array<Dynamic>)) {
      if (StringTools.startsWith(animation.anim, "sing"))
        directions.set(animation.anim, animation);
    }
    var expected:Map<String,Array<Int>> = ["singLEFT"=>[5,-6], "singDOWN"=>[-20,-51],
      "singUP"=>[-46,27], "singRIGHT"=>[-48,-7]];
    for (name in expected.keys()) {
      var animation=directions.get(name);
      check(animation != null, "source BF lacks " + name);
      check(animation.offsets[0] == expected.get(name)[0]
        && animation.offsets[1] == expected.get(name)[1],
        "Psych source " + name + " offsets changed while resolving orientation");
    }
  }
}''')
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(work), "--run",
                 "PsychCharacterOrientationProbe"],
                cwd=work, env={**os.environ, "TMPDIR": str(TMP)},
                capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
