"""Focused HXC character death-overlay compatibility coverage."""
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
DONOR = (
    Path("/run/media/cammie/External Storage/FNF-Example-Mods")
    / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/characters/bf-doki.hxc"
)


def hx_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


@unittest.skipUnless(HAXE.is_file(), "portable Haxe toolchain unavailable")
class HxcDeathOverlayTest(unittest.TestCase):
    def run_fixture(self, source: str) -> subprocess.CompletedProcess:
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="hxc-death-overlay-", dir=ROOT / "tmp") as folder:
            main = Path(folder) / "Main.hx"
            main.write_text(source, newline='\n')
            env = os.environ.copy()
            env["TMPDIR"] = str(ROOT / "tmp")
            return subprocess.run(
                [
                    *HAXE_COMMAND,
                    "-cp", str(ROOT / "source"),
                    "-cp", str(folder),
                    "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                    "-main", "Main", "--interp",
                ],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )

    def test_synthetic_overlay_hook_is_structurally_bounded(self):
        source = r'''
class OverlayCharacter extends SparrowCharacter {
    var deathOverlay:Dynamic;
    function createOverlay() {
        deathOverlay = FunkinSprite.createSparrow(42, -1, 'characters/death_overlay');
        var opponent = PlayState.instance.currentStage.getDad();
        deathOverlay.x = opponent.originalPosition.x;
        deathOverlay.y = opponent.originalPosition.y;
        deathOverlay.animation.addByPrefix('firstDeath', 'Retry Start', 24, true);
        deathOverlay.visible = true;
    }
    function playAnimation(name:String, restart:Bool, ignoreOther:Bool) {
        if (name == 'firstDeath') {
            GameOverSubState.instance.resetCameraZoom();
            this.alpha = 0;
            createOverlay();
            deathOverlay.screenCenter();
            GameOverSubState.instance.add(deathOverlay);
            PlayState.instance.tweenCameraToPosition(deathOverlay.getGraphicMidpoint().x,
                deathOverlay.getGraphicMidpoint().y, 0);
            FlxG.state.subState.mustNotExit = true;
            deathOverlay.animation.play('firstDeath');
        }
        super.playAnimation(name, restart, ignoreOther);
    }
    function onAnimationFinished(name:String) {
        if (name == 'firstDeath') Application.current.window.close();
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, "scripts/characters/overlay.hxc");
    if (result.kind != "character" || result.characterHookGaps.length != 0)
      fail("overlay hook gap: " + result.characterHookGaps.join(","));
    var generated = result.generatedHscript;
    for (required in ["gameOverCreateOverlay", "gameOverAddOverlay", "gameOverSetMustNotExit",
      "gameOverCloseWindow", "gameOverSetOverlayX", "gameOverSetOverlayY"])
      if (generated.indexOf(required) < 0) fail("missing overlay bridge: " + required + "\\n" + generated);
    if (generated.indexOf("FunkinSprite.createSparrow") >= 0
      || generated.indexOf("Application.current.window.close") >= 0
      || generated.indexOf("GameOverSubState.instance") >= 0)
      fail("donor overlay graph escaped: " + generated);
    new Parser().parseString(generated);
    if (HxcCompatRuntime.currentVariation != "") fail("variation default is not empty");
    if (HxcCompatRuntime.gameOverCloseWindow()) fail("window close was not rejected");
    if (HxcCompatRuntime.gameOverAddOverlay(null)) fail("unowned overlay was not rejected");
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_character_effect_sparrow_uses_generic_sprite_adapter(self):
        source = r'''
class EffectCharacter extends SparrowCharacter {
    var exSpikes:Dynamic;
    var deathSprite:Dynamic;
    function onAdd() {
        exSpikes = FunkinSprite.createSparrow(42, -1, 'images/floor_spikes');
        exSpikes.alpha = 0.8;
    }
    function createDeathSprite() {
        deathSprite = FunkinSprite.createSparrow(42, -1, 'characters/death_screen');
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, "scripts/characters/effects.hxc");
    if (result.kind != "character") fail("character effect was not classified");
    var generated = result.generatedHscript;
    if (generated.indexOf("HxcCompatRuntime.createFunkinSpriteSparrow(hxcAssetRoot, 42, -1, 'images/floor_spikes')") < 0)
      fail("ordinary effect sprite missed generic adapter: " + generated);
    if (generated.indexOf("deathSprite = HxcCompatRuntime.gameOverCreateOverlay(hxcAssetRoot, 'characters/death_screen')") < 0)
      fail("death-prefixed overlay missed game-over adapter: " + generated);
    if (generated.indexOf("exSpikes = HxcCompatRuntime.gameOverCreateOverlay") >= 0)
      fail("ordinary effect sprite was treated as a game-over overlay: " + generated);
    new Parser().parseString(generated);
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_create_sparrow_alias_is_planned_without_dynamic_media_walk(self):
        main = r'''class Main {
  static function main() {
    var refs = HxcAssetPlanner.literalReferences(
      "var skin = 'characters/death_overlay';"
      + "var overlay = FunkinSprite.createSparrow(42, -1, skin);");
    if (refs.length != 1 || refs[0].kind != 'sparrow'
      || refs[0].key != 'characters/death_overlay')
      throw 'death overlay atlas was not planned';
    Sys.println('hxc-death-overlay-planner-ok');
  }
}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("hxc-death-overlay-planner-ok", result.stdout)

    @unittest.skipUnless(DONOR.is_file(), "mounted bf-doki HXC donor unavailable")
    def test_mounted_bf_doki_hook_is_read_only_and_emits_bounded_overlay(self):
        before = DONOR.read_bytes()
        source = DONOR.read_text(errors="ignore")
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, {hx_string(str(DONOR))});
    if (result.kind != "character" || result.characterHookGaps.length != 0
      || result.characterBaseGaps.length != 0)
      fail("mounted bf-doki gap: " + result.characterHookGaps.join(",") + "/"
        + result.characterBaseGaps.join(","));
    if (result.generatedHscript.indexOf("gameOverCreateOverlay") < 0
      || result.generatedHscript.indexOf("gameOverCloseWindow") < 0
      || result.generatedHscript.indexOf("gameOverSetMustNotExit") < 0)
      fail("mounted overlay adapter missing: " + result.generatedHscript);
    new Parser().parseString(result.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(before, DONOR.read_bytes())


if __name__ == "__main__":
    unittest.main()
