"""Generic, manifest-scoped HXC game-over replacement adapter coverage."""
from haxe_test_support import HAXE_COMMAND

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


def hx_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


@unittest.skipUnless(HAXE.is_file(), "portable Haxe toolchain unavailable")
class HxcGameOverAdapterTest(unittest.TestCase):
    def run_fixture(self, files: dict[str, str]) -> subprocess.CompletedProcess:
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="hxc-gameover-", dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            for name, content in files.items():
                (temp / name).write_text(content, newline='\n')
            env = os.environ.copy()
            env["TMPDIR"] = str(ROOT / "tmp")
            return subprocess.run(
                [
                    *HAXE_COMMAND,
                    "-cp", str(ROOT / "source"),
                    "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                    "-cp", folder,
                    "-main", "Main", "--interp",
                ],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )

    def test_literal_module_roster_and_replacement_are_translated_as_data(self):
        module = r'''class GenericGameOver extends Module {
  var acceptedPlayers = ["hero-one", 'hero-two'];
  var active = true;
  override function onSubStateOpenEnd(change) {
    if (Std.isOfType(change.targetState, GameOverSubState)) {
      if (!acceptedPlayers.contains(PlayState.instance.currentChart.characters.player)) return;
      var replacement = CharacterDataParser.fetchCharacter('hero-death');
      if (replacement != null) {
        GameOverSubState.instance.boyfriend.destroy();
        GameOverSubState.instance.boyfriend = replacement;
      }
    }
  }
}'''
        dynamic_roster = module.replace(
            '["hero-one", \'hero-two\']', 'getAcceptedPlayers()'
        )
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(module)}, "assets/imported_mods/generic/scripts/module.hxc");
    var adapter = 'HxcCompatRuntime.handleImportedGameOverReplacement(change, hxcAssetRoot, '
      + '["hero-one", "hero-two"], "hero-death");';
    if (!result.moduleSafe || !result.moduleInitializationSafe
      || result.generatedHscript.indexOf(adapter) < 0
      || result.generatedHscript.indexOf("GameOverSubState.instance") >= 0)
      fail("literal adapter missing or unsafe: " + result.moduleSafetyReasons.join(",")
        + "\\n" + result.generatedHscript);
    new Parser().parseString(result.generatedHscript);

    var dynamicResult = HxcCompat.analyze({hx_string(dynamic_roster)},
      "assets/imported_mods/generic/scripts/module.hxc");
    if (dynamicResult.generatedHscript.indexOf("handleImportedGameOverReplacement") >= 0)
      fail("dynamic roster entered literal-only adapter");
    Sys.println("hxc-gameover-literal-data-ok");
  }}
}}'''
        result = self.run_fixture({"Main.hx": main})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("hxc-gameover-literal-data-ok", result.stdout)

    def test_runtime_requires_import_scope_and_authored_roster(self):
        main = '''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var state = {SONG: {player1: "hero-two"}, curStage: {stageId: "stage"}};
    HxcCompatRuntime.bindActiveState(state);
    var target = new GameOverSubState();
    var event = {targetState: target};
    var roster:Array<Dynamic> = ["hero-one", "hero-two"];
    if (!HxcCompatRuntime.handleImportedGameOverReplacement(event,
      "assets/imported_mods/generic", roster, "hero-death"))
      fail("valid scoped hand-off was rejected");
    if (!target.applied || target.replacement.curCharacter != "hero-death"
      || target.root != "assets/imported_mods/generic")
      fail("native boundary did not receive the literal payload and manifest root");

    target.applied = false;
    if (HxcCompatRuntime.handleImportedGameOverReplacement(event,
      "assets/images", roster, "hero-death") || target.applied)
      fail("non-manifest root was accepted");
    state.SONG.player1 = "unlisted-player";
    if (HxcCompatRuntime.handleImportedGameOverReplacement(event,
      "assets/imported_mods/generic", roster, "hero-death") || target.applied)
      fail("player outside authored roster was accepted");
    Sys.println("hxc-gameover-runtime-scope-ok");
  }
}'''
        character = '''class Character {
  public var curCharacter:String;
  public function new(x:Float, y:Float, id:String, isPlayer:Bool) curCharacter = id;
  public static function characterExists(id:String):Bool return id == "hero-death";
}'''
        target = '''class GameOverSubState {
  public var applied:Bool = false;
  public var replacement:Character;
  public var root:String = "";
  public function new() {}
  public function hxcApplyImportedGameOverCharacter(actor:Character, stage:Dynamic,
    assetRoot:Dynamic):Bool {
    applied = true;
    replacement = actor;
    root = Std.string(assetRoot);
    return true;
  }
}'''
        result = self.run_fixture(
            {"Main.hx": main, "Character.hx": character, "GameOverSubState.hx": target}
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("hxc-gameover-runtime-scope-ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
