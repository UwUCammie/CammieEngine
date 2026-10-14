"""Psych's onCreatePost character preload must keep an actor for the native swap."""
from haxe_test_support import HAXE_COMMAND

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]


class PsychCharacterPreloadBridgeTest(unittest.TestCase):
    def test_preload_binding_preserves_role_and_ignores_unavailable_characters(self):
        play = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("interp.variables.set('addCharacterToList', compatAddCharacterToList);", play)
        self.assertIn("interp.variables.set('hideHud', camHUD != null && !camHUD.visible);", play)
        start = play.index("\tfunction compatAddCharacterToList(")
        end = play.index("\n\t}", start) + 3
        method = play[start:end]
        slot_start = play.index("\tstatic function changeCharacterSlot(")
        method += play[slot_start:play.index("\n\t}", slot_start) + 3]
        fixture = '''using StringTools;
class Character {
  public static function characterExists(name:String):Bool return name == "bf-jam-car" || name == "gf-swag" || name == "listed-dad";
}
class FakeCharacterBank {
  public var names:Array<String> = [];
  public function new() {}
  public function addToList(name:String):Void names.push(name);
}
class PlayState {
  var warmed:Array<String> = [];
  var nightmareVisionScripts:Dynamic = null;
  var banks:Map<Int, FakeCharacterBank> = new Map();
  public function new() {}
  function nightmareVisionCharacterBank(role:Int):FakeCharacterBank {
    if (!banks.exists(role)) banks.set(role, new FakeCharacterBank());
    return banks.get(role);
  }
  function addNightmareVisionCharacterToList(name:String,role:Int):Void nightmareVisionCharacterBank(role).addToList(name);
  function warmCharacterAtlas(name:String, isPlayer:Bool = false):Void
    warmed.push(name + ":" + isPlayer);
  function preloadSwapCharacter(slot:String, name:String, wanted:Int = 1):Void
    warmed.push(name + ":" + slot);
  var listed:Array<String> = [];
  // Only "listed-dad" can go in a Psych role map in this fixture.
  function publishPsychRoleCharacter(slot:String, name:String):Bool {
    if (name != "listed-dad") return false;
    listed.push(name + ":" + slot);
    return true;
  }
''' + method + '''
  static function main():Void {
    var state = new PlayState();
    state.compatAddCharacterToList(" bf-jam-car ", "boyfriend");
    state.compatAddCharacterToList("gf-swag", "gf");
    state.compatAddCharacterToList("missing", "dad");
    state.compatAddCharacterToList(null, "boyfriend");
    if (state.warmed.join(",") != "bf-jam-car:boyfriend,gf-swag:gf")
      throw "Psych character preload did not preserve selected role or missing dependency";
    // An actor listed in the role map is the swap's actor; no second copy.
    state.compatAddCharacterToList(" listed-dad ", "dad");
    if (state.listed.join(",") != "listed-dad:dad" || state.warmed.join(",") != "bf-jam-car:boyfriend,gf-swag:gf")
      throw "listed role actor was also preloaded: " + state.listed.join(",") + " / " + state.warmed.join(",");

    // The Nightmare Vision host retains these preloads in the role bank.
    var warmedBefore = state.warmed.join(",");
    state.nightmareVisionScripts = {};
    state.compatAddCharacterToList(" gf-swag ", "gf");
    state.compatAddCharacterToList("opponent-alt", "1");
    state.compatAddCharacterToList(" ", "gf");
    if (state.banks.get(2).names.join(",") != "gf-swag")
      throw "Nightmare Vision GF preload did not use the retained role bank";
    if (state.banks.get(1).names.join(",") != "opponent-alt")
      throw "Psych numeric role 1 did not remain the opponent role";
    if (state.warmed.join(",") != warmedBefore)
      throw "Nightmare Vision preload constructed and destroyed a temporary actor";
  }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "PlayState.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", folder, "-main", "PlayState", "--interp"],
                cwd=folder, env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
