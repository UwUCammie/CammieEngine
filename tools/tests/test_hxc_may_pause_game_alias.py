"""Regression coverage for the V-Slice mayPauseGame compatibility alias."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"


class HxcMayPauseGameAliasTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.play_state = (ROOT / "source/PlayState.hx").read_text()

    def test_alias_uses_the_native_pause_gate(self):
        source = self.play_state
        self.assertTrue("if (controls.PAUSE && startedCountdown && canPause" in source,
                        "Configured pause action must respect countdown and canPause gates")
        self.assertIn("canPause = false;", source)
        start = source.index("\tpublic var mayPauseGame(get, set):Bool;")
        end = source.index("\n\t// scale the Image Flash overlay", start)
        alias = source[start:end]
        self.assertIn("return canPause;", alias)
        self.assertIn("canPause = value;", alias)

    def test_hscript_reads_and_writes_the_live_pause_gate(self):
        source = self.play_state
        start = source.index("\tpublic var mayPauseGame(get, set):Bool;")
        end = source.index("\n\t// scale the Image Flash overlay", start)
        alias = source[start:end]
        fixture = '''import hscript.Interp;
import hscript.Parser;
class HxcMayPauseGameAliasTest {
	var canPause:Bool = true;
	public function new() {}
''' + alias + '''
	static function main() {
		var state = new HxcMayPauseGameAliasTest();
		var interp = new Interp();
		interp.variables.set("state", state);
		interp.execute(new Parser().parseString(
			"if (!state.mayPauseGame) throw 'pause should start enabled'; "
			+ "state.mayPauseGame = false; "
			+ "if (state.mayPauseGame) throw 'false write was not visible'; "
			+ "state.mayPauseGame = true; "
			+ "if (!state.mayPauseGame) throw 'true write was not visible'"
		));
		if (!state.canPause || !state.mayPauseGame)
			throw 'HScript pause alias did not restore the native gate';
		state.canPause = false;
		if (state.mayPauseGame)
			throw 'song-end native gate change was not visible through alias';
	}
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "HxcMayPauseGameAliasTest.hx"
            path.write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", str(HSCRIPT), "-cp", folder,
                 "-main", "HxcMayPauseGameAliasTest", "--interp"],
                capture_output=True, text=True, cwd=ROOT, timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
