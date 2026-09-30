"""Regression coverage for the V-Slice stage countdown state alias."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
DONOR_STAGE = Path(
    "/run/media/cammie/External Storage/FNF-Example-Mods/v-slice/"
    "HatsuneMiku-ProjectFunkin-V-Slice/scripts/stages/concert2.hxc"
)


class HxcIsInCountdownAliasTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.play_state = (ROOT / "source/PlayState.hx").read_text()

    def test_playstate_exposes_a_live_alias_of_native_starting_song(self):
        source = self.play_state
        self.assertIn("public var isInCountdown(get, set):Bool;", source)
        self.assertIn("function get_isInCountdown():Bool", source)
        self.assertIn("function set_isInCountdown(value:Bool):Bool", source)
        getter = source[
            source.index("function get_isInCountdown") : source.index("function set_isInCountdown")
        ]
        setter = source[
            source.index("function set_isInCountdown") : source.index("var hxcScriptInCutscene")
        ]
        self.assertIn("return startingSong;", getter)
        self.assertIn("startingSong = value;", setter)
        start_song = source[source.index("\tfunction startSong():Void {") :]
        self.assertIn("startingSong = false;", start_song[:500])

    def test_haxe_alias_reads_and_writes_the_backing_state(self):
        source = self.play_state
        alias_start = source.index("\tpublic var isInCountdown(get, set):Bool;")
        alias_end = source.index("\t// V-Slice exposes the cutscene gate", alias_start)
        alias = source[alias_start:alias_end]
        fixture = """class HxcIsInCountdownAliasTest {
	var startingSong:Bool = true;
	public function new() {}
""" + alias + """
	static function main() {
		var state = new HxcIsInCountdownAliasTest();
		if (!state.isInCountdown) throw 'alias did not read active startup state';
		state.isInCountdown = false;
		if (state.startingSong || state.isInCountdown) throw 'alias write did not update backing state';
		state.isInCountdown = true;
		if (!state.startingSong || !state.isInCountdown) throw 'alias could not restore startup state';
	}
}
"""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "HxcIsInCountdownAliasTest.hx"
            path.write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder,
                 "-main", "HxcIsInCountdownAliasTest", "--interp"],
                capture_output=True, text=True, cwd=ROOT, timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_future_sound_stage_uses_the_alias_during_countdown(self):
        if not DONOR_STAGE.is_file():
            self.skipTest("mounted Future Sound donor stage is unavailable")
        stage = DONOR_STAGE.read_text(errors="ignore")
        callback = stage[stage.index("public override function onCountdownStart") :]
        self.assertIn("PlayState.instance.isInCountdown = true;", callback)
        self.assertLess(callback.index("isInCountdown = true"), callback.index("startSong();"))


if __name__ == "__main__":
    unittest.main()
