"""Psych's onCreatePost character preload must reach the native atlas warmer."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class PsychCharacterPreloadBridgeTest(unittest.TestCase):
    def test_preload_binding_preserves_role_and_ignores_unavailable_characters(self):
        play = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("interp.variables.set('addCharacterToList', compatAddCharacterToList);", play)
        self.assertIn("interp.variables.set('hideHud', camHUD != null && !camHUD.visible);", play)
        start = play.index("\tfunction compatAddCharacterToList(")
        end = play.index("\n\t}", start) + 3
        method = play[start:end]
        fixture = '''using StringTools;
class Character {
  public static function characterExists(name:String):Bool return name == "bf-jam-car" || name == "gf-swag";
}
class PlayState {
  var warmed:Array<String> = [];
  public function new() {}
  function warmCharacterAtlas(name:String, isPlayer:Bool = false):Void
    warmed.push(name + ":" + isPlayer);
''' + method + '''
  static function main():Void {
    var state = new PlayState();
    state.compatAddCharacterToList(" bf-jam-car ", "boyfriend");
    state.compatAddCharacterToList("gf-swag", "gf");
    state.compatAddCharacterToList("missing", "dad");
    state.compatAddCharacterToList(null, "boyfriend");
    if (state.warmed.join(",") != "bf-jam-car:true,gf-swag:false")
      throw "Psych character preload did not preserve selected role or missing dependency";
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "PlayState.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder, "-main", "PlayState", "--interp"],
                cwd=folder, env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
