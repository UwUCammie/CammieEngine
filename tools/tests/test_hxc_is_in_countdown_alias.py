"""Regression coverage for the V-Slice stage countdown state alias."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
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
	var startedCountdown:Bool = false;
	var hxcCountdownStopRequested:Bool = false;
	var startCalls:Int = 0;
	public function new() {}
	function startCountdown():Void startCalls++;
""" + alias + """
	static function main() {
		var state = new HxcIsInCountdownAliasTest();
		if (!state.isInCountdown) throw 'alias did not read active startup state';
		state.isInCountdown = false;
		if (state.startingSong || state.isInCountdown) throw 'alias write did not update backing state';
		state.isInCountdown = true;
		if (!state.startingSong || !state.isInCountdown) throw 'alias could not restore startup state';
		// A write while no script held the countdown only records the request.
		if (state.startCalls != 0 || !state.hxcScriptCountdownRequested || state.hxcSilentPreRoll)
			throw 'a plain write started a countdown';
		// A script that cancelled the countdown and then sets isInCountdown gets
		// the lead-in clock without the 3-2-1-Go, once.
		state.hxcScriptCountdownRequested = false;
		state.hxcCountdownCancelledPending = true;
		state.isInCountdown = true;
		if (state.startCalls != 1 || !state.hxcSilentPreRoll || state.hxcCountdownCancelledPending)
			throw 'a held countdown did not start its silent lead-in';
		state.isInCountdown = true;
		if (state.startCalls != 1) throw 'the lead-in started twice';
		// A running countdown or a script stop is never restarted by the alias.
		var running = new HxcIsInCountdownAliasTest();
		running.hxcCountdownCancelledPending = true;
		running.startedCountdown = true;
		running.isInCountdown = true;
		var stopped = new HxcIsInCountdownAliasTest();
		stopped.hxcCountdownCancelledPending = true;
		stopped.hxcCountdownStopRequested = true;
		stopped.isInCountdown = true;
		if (running.startCalls != 0 || stopped.startCalls != 0) throw 'alias restarted a running or stopped countdown';
	}
}
"""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "HxcIsInCountdownAliasTest.hx"
            path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder,
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
