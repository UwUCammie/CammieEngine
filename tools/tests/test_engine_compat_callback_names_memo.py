"""Callback name lookups are remembered instead of rebuilt per interpreter call."""
from haxe_test_support import HAXE_COMMAND, FixturePath

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FIXTURE = r'''class CallbackNamesMemoFixture {
	static function fail(message:String):Void throw message;
	static function same(names:Array<String>, expected:Array<String>, label:String):Void {
		if (names.join(",") != expected.join(",")) fail(label + ": " + names.join(","));
	}
	static function main() {
		var update = EngineCompat.callbackNames("update");
		if (EngineCompat.callbackNames("update") != update) fail("update list rebuilt");
		same(update, ["update", "onUpdate"], "update");
		var pause = EngineCompat.callbackNames("onPause");
		if (EngineCompat.callbackNames("onPause") != pause) fail("pause list rebuilt");
		same(pause, ["onPause", "pause"], "pause");
		same(EngineCompat.callbackNames("startCountdown"), ["onStartCountdown"], "startCountdown");
		same(EngineCompat.callbackNames("songEnd"), ["songEnd", "onEndSong", "onSongEnd"], "songEnd");
		same(EngineCompat.callbackNames("songEnd"), ["songEnd", "onEndSong", "onSongEnd"], "songEnd again");
		// spelling is still kept apart: the cache is keyed on the exact name
		same(EngineCompat.callbackNames("UPDATE"), ["UPDATE", "onUpdate"], "upper");
		if (EngineCompat.callbackNames(null).length != 0) fail("null name");
		if (EngineCompat.canonicalCallback("ONUPDATE") != "update") fail("canonical lookup");
		if (EngineCompat.canonicalCallback("onUpdate") != "update") fail("canonical repeat");
		if (EngineCompat.canonicalCallback("somethingElse") != "somethingElse") fail("canonical passthrough");
		// argument shaping reads the remembered lowercase names the same way
		for (round in 0...2) {
			if (EngineCompat.callbackArguments("start", "onCreate", ["song"]).length != 0) fail("onCreate args");
			var eventArgs = EngineCompat.callbackArguments("event", "onEvent", ["a", "b", "c", "d"]);
			if (eventArgs.length != 3 || eventArgs[2] != "c") fail("onEvent args");
			var plain = EngineCompat.callbackArguments("custom", "customThing", [1, 2]);
			if (plain.length != 2 || plain[1] != 2) fail("plain args");
		}
		// names passed in by scripts cannot grow the cache without bound
		for (i in 0...700) EngineCompat.callbackNames("scriptCall" + i);
		var late = EngineCompat.callbackNames("scriptCall699");
		same(late, ["scriptCall699"], "late name");
		if (EngineCompat.callbackNames("scriptCall699") == late) fail("cache grew past its limit");
		if (EngineCompat.callbackNames("update") != update) fail("early entry lost");
		Sys.println("OK");
	}
}'''


class EngineCompatCallbackNamesMemoTest(unittest.TestCase):
    def test_callback_names_are_shared_and_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            (FixturePath(folder) / "CallbackNamesMemoFixture.hx").write_text(FIXTURE, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                 "-main", "CallbackNamesMemoFixture", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def test_broadcast_callers_only_read_the_shared_list(self):
        # A caller that pushed into the list would corrupt every later lookup.
        callers = 0
        for path in sorted((ROOT / "source").rglob("*.hx")):
            source = path.read_text(encoding="utf-8", errors="replace")
            for line in source.splitlines():
                if "callbackNames(" in line and "function callbackNames(" not in line:
                    callers += 1
                    self.assertIn("for (candidate in EngineCompat.callbackNames(", line, path.name)
        self.assertGreater(callers, 0)


if __name__ == "__main__":
    unittest.main()
