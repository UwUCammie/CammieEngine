"""Mounted HXC character audio settings execute through the native adapter."""
from haxe_test_support import HAXE_COMMAND

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
FIXTURE = (
    DONOR
    / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/characters/bf-pixelbar.hxc"
)


@unittest.skipUnless(FIXTURE.is_file(), "mounted bf-pixelbar HXC fixture is unavailable")
class MountedHxcGameOverSuffixTest(unittest.TestCase):
    def test_mounted_character_callback_executes_suffix_adapter(self):
        source = FIXTURE.read_text(errors="ignore")
        game_over = (ROOT / "source/GameOverSubstate.hx").read_text(errors="ignore")
        pause = (ROOT / "source/PauseSubState.hx").read_text(errors="ignore")
        play_state = (ROOT / "source/PlayState.hx").read_text(errors="ignore")
        self.assertIn("resolveBlueBallTrack", game_over)
        self.assertIn("resolveGameOverTrack", game_over)
        self.assertIn("HxcCompatRuntime.pauseMusicSuffix", pause)
        self.assertIn("HxcCompatRuntime.resetGameOverSettings();", play_state)
        encoded_source = json.dumps(source, ensure_ascii=False)
        encoded_path = json.dumps(str(FIXTURE), ensure_ascii=False)
        main = f'''import hscript.Interp;
import hscript.Parser;

class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    HxcCompatRuntime.resetGameOverSettings();
    var result = HxcCompat.analyze({encoded_source}, {encoded_path});
    var startSafe = false;
    for (callback in (cast result.callbackAdapters:Array<Dynamic>))
      if (callback.sourceName == "onCreate" && callback.canonicalName == "start" && callback.safe)
        startSafe = true;
    if (!startSafe) fail("mounted onCreate callback was not executable");
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == "unsupported-hxc-character-hook"
        || finding.code == "unsupported-hxc-script")
        fail("suffix callback retained a parser gap: " + finding.code);

    var generated = result.generatedHscript;
    if (generated.indexOf("setGameOverMusicSuffix('-doki')") < 0
      || generated.indexOf("setGameOverBlueBallSuffix('-pixel')") < 0
      || generated.indexOf("setPauseMusicSuffix('-doki')") < 0)
      fail("central suffix setters were not emitted: " + generated);
    new Parser().parseString(generated);

    var interp = new Interp();
    interp.variables.set("HxcCompatRuntime", HxcCompatRuntime);
    interp.variables.set("hxcCharacter", function() return null);
    interp.execute(new Parser().parseString(generated));
    var start:Dynamic = interp.variables.get("start");
    if (start == null) fail("generated start callback missing");
    start(null);
    if (HxcCompatRuntime.gameOverMusicSuffix != "-doki"
      || HxcCompatRuntime.gameOverBlueBallSuffix != "-pixel"
      || HxcCompatRuntime.pauseMusicSuffix != "-doki")
      fail("suffix adapter did not receive mounted callback writes");

    if (HxcCompatRuntime.resolveGameOverTrack("gameOver.ogg", "tmp/missing", true) != "gameOver.ogg")
      fail("missing suffix track did not fall back safely");
    HxcCompatRuntime.clearActiveState();
    if (HxcCompatRuntime.gameOverMusicSuffix != ""
      || HxcCompatRuntime.gameOverBlueBallSuffix != ""
      || HxcCompatRuntime.pauseMusicSuffix != "")
      fail("state cleanup leaked suffix state");
    HxcCompatRuntime.resetGameOverSettings();
    Sys.println("mounted-hxc-gameover-suffix-ok");
  }}
}}
'''
        with tempfile.TemporaryDirectory(prefix="hxc-gameover-suffix-", dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            (temp / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(temp),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-main", "Main", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("mounted-hxc-gameover-suffix-ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
