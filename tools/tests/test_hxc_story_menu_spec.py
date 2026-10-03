"""Structural coverage for complete HXC StoryMenu modules."""
from haxe_test_support import HAXE_COMMAND

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
DONOR = Path(
    "/run/media/cammie/External Storage/FNF-Example-Mods/v-slice/"
    "Vs Tricky/scripts/modules/StoryConfirmMouth.hxc"
)
TRICKY = DONOR.with_name("TrickyVocalVolumeSetter.hxc")
HAXE = ROOT / ".tools/haxe/haxe"


def hx_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


class HxcStoryMenuSpecTest(unittest.TestCase):
    def test_complete_behavior_is_structural_and_partial_copy_stays_unsupported(self):
        if not DONOR.exists():
            self.skipTest("mounted Vs Tricky V-Slice fixture is unavailable")
        if not TRICKY.exists():
            self.skipTest("mounted Tricky vocal module fixture is unavailable")
        source = DONOR.read_text(errors="ignore")
        tricky = TRICKY.read_text(errors="ignore")
        renamed = source.replace("StoryConfirmJaws", "AuthoredStoryBoundary")
        renamed = renamed.replace('"clown"', '"authored-level"')
        renamed = renamed.replace("jawSpr", "helperSprite")
        renamed = renamed.replace("createJaws", "makeCharacterHelper")
        partial = source.replace("camera.stopFX();", "camera.startFX();")
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var full = HxcCompat.analyze({hx_string(source)}, "scripts/modules/unrelated-file.hxc");
    var renamed = HxcCompat.analyze({hx_string(renamed)}, "scripts/modules/renamed-file.hxc");
    for (result in [full, renamed]) {{
      if (result.kind != "module" || !result.moduleSafe || !result.moduleInitializationSafe
        || result.storyMenuSpec == null || hasCode(result, "unsupported-hxc-module-body"))
        fail("complete StoryMenu module was rejected: spec=" + result.storyMenuSpec
          + " module=" + result.moduleSafe + " init=" + result.moduleInitializationSafe
          + " reasons=" + result.moduleSafetyReasons.join(","));
      if (result.generatedHscript.indexOf("HxcCompatRuntime.createStoryCharacterHelper") < 0
        || result.generatedHscript.indexOf("FunkinSprite") >= 0
        || result.generatedHscript.indexOf("Paths.sound") >= 0)
        fail("StoryMenu helper did not stay behind generic native boundary: " + result.generatedHscript);
      new Parser().parseString(result.generatedHscript);
    }}
    var spec = renamed.storyMenuSpec;
    if (spec.levelId != "authored-level" || spec.songIndex != 0
      || spec.transitionDelay != 1 || spec.characterHelperField != "helperSprite"
      || spec.characterHelperName != "makeCharacterHelper")
      fail("authored StoryMenu values were not extracted: " + spec);
    if (renamed.generatedHscript.indexOf("function makeCharacterHelper") < 0
      || renamed.generatedHscript.indexOf("var helperSprite") < 0
      || renamed.generatedHscript.indexOf("jawSpr") >= 0)
      fail("renamed StoryMenu helper retained donor identifier: " + renamed.generatedHscript);
    var incomplete = HxcCompat.analyze({hx_string(partial)}, "scripts/modules/other-name.hxc");
    if (incomplete.storyMenuSpec != null || incomplete.moduleSafe
      || !hasCode(incomplete, "unsupported-hxc-module-body"))
      fail("partial StoryMenu behavior was incorrectly covered");
    new Parser().parseString(incomplete.generatedHscript);
    var unrelated = HxcCompat.analyze({hx_string(tricky)}, "scripts/modules/other-module.hxc");
    if (unrelated.storyMenuSpec != null || !unrelated.moduleSafe
      || unrelated.generatedHscript.indexOf("setPlayerVocalVolume") < 0)
      fail("StoryMenu structural match captured an unrelated native vocal module");
  }}
}}'''
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            (temp / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(temp),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"), "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
