"""Scoped V-Slice character texture warm-up survives the HXC safety gate."""
from haxe_test_support import HAXE_COMMAND

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
BFHELL = (Path("/run/media/cammie/External Storage/FNF-Example-Mods")
          / "v-slice/Vs Tricky/scripts/characters/bfhell.hxc")


@unittest.skipUnless(BFHELL.is_file(), "mounted Vs Tricky character is unavailable")
class HxcCharacterTextureCacheTest(unittest.TestCase):
    def test_literal_scoped_warm_up_and_game_over_suffix_execute(self):
        source = json.dumps(BFHELL.read_text(encoding="utf-8"))
        path = json.dumps(str(BFHELL))
        main = f'''import hscript.Interp;
import hscript.Parser;

class Main {{
  static function main() {{
    var result = HxcCompat.analyze({source}, {path});
    if (result.characterHookGaps.indexOf("onCreate") >= 0)
      throw "literal scoped warm-up remained unsafe";
    var generated = result.generatedHscript;
    if (generated.indexOf("hxcCacheTexture(Paths.image(") < 0
      || generated.indexOf("setGameOverMusicSuffix") < 0
      || generated.indexOf("setGameOverBlueBallSuffix") < 0)
      throw "bounded character operations were omitted: " + generated;
    var parser = new Parser();
    var expression = parser.parseString(generated);
    var interp = new Interp();
    var images = 0;
    var warmed = 0;
    interp.variables.set("Paths", {{image: function(key:String, ?library:String) {{
      if (key != "characters/signDeath" || library != "shared")
        throw "wrong scoped texture key";
      images++;
      return "owned-bitmap";
    }}}});
    interp.variables.set("hxcCacheTexture", function(asset:Dynamic) {{
      if (asset != "owned-bitmap") throw "warm-up lost scoped image";
      warmed++;
    }});
    interp.variables.set("HxcCompatRuntime", HxcCompatRuntime);
    interp.variables.set("hxcCharacter", function() return null);
    HxcCompatRuntime.resetGameOverSettings();
    interp.execute(expression);
    var start:Dynamic = interp.variables.get("start");
    if (start == null) throw "character start hook missing";
    start(null);
    if (images != 1 || warmed != 1
      || HxcCompatRuntime.gameOverMusicSuffix != "Trickster"
      || HxcCompatRuntime.gameOverBlueBallSuffix != "-sign")
      throw "character warm-up or suffix behavior did not execute";
    var unsafe = HxcCompat.analyze(
      'class Example extends Character {{ function onCreate() {{ Paths.image("donor-only"); }} }}',
      'scripts/characters/example.hxc');
    if (unsafe.characterHookGaps.indexOf("onCreate") < 0)
      throw "unbounded Paths.image was incorrectly accepted";
    Sys.println("hxc-character-texture-cache-ok");
  }}
}}
'''
        with tempfile.TemporaryDirectory(prefix="hxc-character-texture-", dir=ROOT / "tmp") as folder:
            temporary = Path(folder)
            (temporary / "Main.hx").write_text(main, encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(temporary),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-main", "Main", "--interp"], cwd=ROOT, capture_output=True,
                text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("hxc-character-texture-cache-ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
