"""Read-only donor coverage for the named generic engine regressions.

These tests deliberately execute small extracted engine helpers or their data
boundary, rather than copying a donor chart into assets/.  The donor files are
hashed before and after each case so a regression test cannot quietly become an
import-time rewrite.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"
DEFAULT_DONOR = Path("/run/media/cammie/External Storage/modding-plus-fnf")
DONOR = Path(os.environ.get("REGRESSION_DONOR_ROOT", str(DEFAULT_DONOR)))


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"unterminated method: {marker}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_haxe(fixture: str, *args: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory(prefix="named-donor-", dir=ROOT / "tmp") as folder:
        path = Path(folder) / "NamedDonorRegressionTest.hx"
        path.write_text(fixture, encoding="utf-8")
        return subprocess.run(
            [
                str(HAXE),
                "-cp",
                folder,
                "-cp",
                str(ROOT / "source"),
                "-cp",
                str(HSCRIPT),
                "--run",
                "NamedDonorRegressionTest",
                *args,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )


def last_json(stdout: str) -> dict:
    lines = [line for line in stdout.splitlines() if line.strip().startswith("{")]
    if not lines:
        raise AssertionError(stdout)
    return json.loads(lines[-1])


class NamedRegressionDonorTest(unittest.TestCase):
    def test_cycles_wrath_section_flags_reach_generic_crossfade_resolver(self):
        fixture_path = DONOR / "assets/data/cycles-wrath/cycles-wrath-hard.json"
        if not fixture_path.is_file():
            self.skipTest(f"mounted Cycles Wrath donor unavailable: {fixture_path}")

        before = sha256(fixture_path)
        chart = json.loads(fixture_path.read_text(encoding="utf-8"))["song"]
        sections = chart["notes"]
        expected_bf = sum(section.get("crossfadeBf") is True for section in sections)
        expected_dad = sum(section.get("crossfadeDad") is True for section in sections)
        self.assertGreater(expected_bf, 0)
        self.assertGreater(expected_dad, 0)

        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        resolver = extract_method(play_state, "private static function sectionHasCrossFade(")
        resolver = resolver.replace("section:SwagSection", "section:Dynamic")
        fixture = """import haxe.Json;
import sys.io.File;

class NamedDonorRegressionTest {
""" + resolver + r'''
	static function check(value:Bool, message:String):Void {
		if (!value) throw message;
	}
	static function main():Void {
		var root:Dynamic = Json.parse(File.getContent(Sys.args()[0]));
		var song:Dynamic = Reflect.field(root, 'song');
		var sections:Array<Dynamic> = cast Reflect.field(song, 'notes');
		var bfFlags = 0;
		var dadFlags = 0;
		for (section in sections) {
			var bf = Reflect.field(section, 'crossfadeBf') == true;
			var dad = Reflect.field(section, 'crossfadeDad') == true;
			var shared = Reflect.field(section, 'crossFade') == true;
			if (bf) bfFlags++;
			if (dad) dadFlags++;
			check(!bf || sectionHasCrossFade(section, true), 'BF section flag was not consumed');
			check(!dad || sectionHasCrossFade(section, false), 'Dad section flag was not consumed');
			if (!bf && !shared)
				check(!sectionHasCrossFade(section, true), 'unflagged BF section gained crossfade');
			if (!dad && !shared)
				check(!sectionHasCrossFade(section, false), 'unflagged Dad section gained crossfade');
		}
		Sys.println(Json.stringify({bf: bfFlags, dad: dadFlags}));
	}
}
'''
        result = run_haxe(fixture, str(fixture_path))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = last_json(result.stdout)
        self.assertEqual(payload["bf"], expected_bf)
        self.assertEqual(payload["dad"], expected_dad)
        self.assertEqual(sha256(fixture_path), before)

    def test_cycles_encore_unknown_suffix_is_discovered_and_selectable(self):
        donor_song = "cycles-encore-springless"
        fixture_path = DONOR / f"assets/data/{donor_song}/{donor_song}-encore.json"
        if not fixture_path.is_file():
            self.skipTest(f"mounted Springless Cycles donor unavailable: {fixture_path}")

        before = sha256(fixture_path)
        manager = (ROOT / "source/DifficultyManager.hx").read_text(encoding="utf-8")
        suffix_method = extract_method(manager, "public static function difficultySuffixFromChartFile(")
        discover_method = extract_method(manager, "static function discoverSongDifficulties(")
        selectable_method = extract_method(manager, "static function readSourceSelectableDifficulties(")
        unsupported_method = extract_method(manager, "static function readSourceUnsupportedDifficulties(")
        ensure_method = extract_method(manager, "static function ensureDifficultyDefinition(")
        add_support_method = extract_method(manager, "public static function addSongSupport(")
        ending_method = extract_method(manager, "public static function getDiffEnding(")
        self.assertNotIn(donor_song, manager)

        fixture = (
            """import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

class FNFAssets {
	public static function exists(path:String):Bool return FileSystem.exists(path);
	public static function getText(path:String):String return File.getContent(path);
}
class CoolUtil {
	public static function parseJson(raw:String):Dynamic return Json.parse(raw);
}
class ImportEngine {
	public static inline var NIGHTMARE_VISION:String = 'Nightmare Vision';
}

class NamedDonorRegressionTest {
	static var diffJson:Dynamic = {
		defaultDiff: 1,
		difficulties: [
			{name: 'easy', offset: 0, anim: 'EASY'},
			{name: 'normal', offset: 10, anim: 'NORMAL'},
			{name: 'hard', offset: 20, anim: 'HARD'}
		]
	};
	static var supportedDiff:Map<String, Array<Int>> = new Map<String, Array<Int>>();
        """
            + "\n".join((suffix_method, discover_method, selectable_method,
                          unsupported_method, ensure_method, add_support_method, ending_method))
            + r'''
	static function check(value:Bool, message:String):Void {
		if (!value) throw message;
	}
	static function main():Void {
		var donorRoot = Sys.args()[0];
		Sys.setCwd(donorRoot);
		discoverSongDifficulties('cycles-encore-springless');
		var suffix = difficultySuffixFromChartFile('cycles-encore-springless',
			'cycles-encore-springless-encore.json');
		check(suffix == 'encore', 'donor suffix was not recognized: ' + suffix);
		var index = ensureDifficultyDefinition(suffix);
		check(index >= 0, 'foreign difficulty was not registered');
		check(getDiffEnding(index) == '-encore', 'registered suffix is not selectable');
		addSongSupport('cycles-encore-springless');
		var supported = supportedDiff.get('cycles-encore-springless');
		check(supported != null && supported.indexOf(index) >= 0,
			'foreign chart was not added to the song support map');
		Sys.println(Json.stringify({suffix: suffix, index: index, ending: getDiffEnding(index)}));
	}
}
'''
        )
        result = run_haxe(fixture, str(DONOR))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = last_json(result.stdout)
        self.assertEqual(payload["suffix"], "encore")
        self.assertEqual(payload["ending"], "-encore")
        self.assertEqual(sha256(fixture_path), before)

    def test_fnia_ugh_one_step_taps_and_three_step_holds_use_generic_normalizer(self):
        fixture_path = DONOR / "assets/data/fnia-ugh/fnia-ugh-hard.json"
        if not fixture_path.is_file():
            self.skipTest(f"mounted FNiA Ugh donor unavailable: {fixture_path}")

        before = sha256(fixture_path)
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        start = play_state.index("\tpublic static inline var SUSTAIN_LENGTH_EPSILON:")
        end = play_state.index("\n\t// Keep chart/tween speed intact", start)
        sustain_helpers = play_state[start:end]
        fixture = """import haxe.Json;
import sys.io.File;

class NamedDonorRegressionTest {
""" + sustain_helpers + r'''
	static function check(value:Bool, message:String):Void {
		if (!value) throw message;
	}
	static function main():Void {
		var root:Dynamic = Json.parse(File.getContent(Sys.args()[0]));
		var song:Dynamic = Reflect.field(root, 'song');
		var bpm:Float = Std.parseFloat(Std.string(Reflect.field(song, 'bpm')));
		var stepCrochet = 60000 / bpm / 4;
		var oneStep = 0;
		var threeStep = 0;
		var zero = 0;
		var sections:Array<Dynamic> = cast Reflect.field(song, 'notes');
		for (section in sections) {
			var rows:Array<Dynamic> = cast Reflect.field(section, 'sectionNotes');
			for (row in rows) {
				var length:Float = Std.parseFloat(Std.string(row[2]));
				if (length == 0) zero++;
				if (Math.abs(length - stepCrochet) < 0.000001) {
					oneStep++;
					check(normalizeSustainLength(length, stepCrochet) == 0,
						'one-step tap sentinel became a hold');
				}
				if (Math.abs(length - stepCrochet * 3) < 0.000001) {
					threeStep++;
					check(sustainStepCount(length, stepCrochet) == 3,
						'three-step hold lost a sustain piece');
				}
			}
		}
		check(oneStep == 104, 'unexpected one-step count: ' + oneStep);
		check(threeStep == 56, 'unexpected three-step count: ' + threeStep);
		check(zero == 373, 'unexpected zero-length count: ' + zero);
		Sys.println(Json.stringify({oneStep: oneStep, threeStep: threeStep, zero: zero}));
	}
}
'''
        result = run_haxe(fixture, str(fixture_path))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = last_json(result.stdout)
        self.assertEqual(payload, {"oneStep": 104, "threeStep": 56, "zero": 373})
        self.assertEqual(sha256(fixture_path), before)

    def test_locked_target_sequence_stays_absolute_while_colorful_stays_additive(self):
        locked_path = DONOR / "assets/data/locked/locked.json"
        colorful_path = DONOR / "assets/data/colorful/colorful.json"
        if not locked_path.is_file() or not colorful_path.is_file():
            self.skipTest(f"mounted camera donors unavailable: {locked_path}, {colorful_path}")

        before = {locked_path: sha256(locked_path), colorful_path: sha256(colorful_path)}
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        methods = "\n".join(
            extract_method(play_state, marker)
            for marker in (
                "public static function cameraZoomEventIsAbsolute(",
                "public static function cameraZoomIntroUsesTargets(",
                "public static function cameraZoomEventValue(",
                "public static function cameraZoomEventTargets(",
            )
        )
        fixture = """import haxe.Json;
import sys.io.File;

class NamedDonorRegressionTest {
""" + methods + r'''
	static function check(value:Bool, message:String):Void {
		if (!value) throw message;
	}
	static function close(a:Float, b:Float):Bool return Math.abs(a - b) < 0.000001;
	static function zoomEvents(song:Dynamic):Array<Array<Float>> {
		var result:Array<Array<Float>> = [];
		var rows:Array<Dynamic> = cast Reflect.field(song, 'events');
		for (row in rows) {
			var rowValues:Array<Dynamic> = cast row;
			var time:Float = Std.parseFloat(Std.string(rowValues[0]));
			var events:Array<Dynamic> = cast rowValues[1];
			for (event in events) {
				var values:Array<Dynamic> = cast event;
				if (Std.string(values[0]).toLowerCase() == 'add camera zoom')
					result.push([time, Std.parseFloat(Std.string(values[1])), Std.parseFloat(Std.string(values[2]))]);
			}
		}
		return result;
	}
	static function firstNoteTime(song:Dynamic):Float {
		var first = 1e30;
		var sections:Array<Dynamic> = cast Reflect.field(song, 'notes');
		for (section in sections) {
			var rows:Array<Dynamic> = cast Reflect.field(section, 'sectionNotes');
			for (row in rows) {
				var time = Std.parseFloat(Std.string(row[0]));
				if (time < first) first = time;
			}
		}
		return first;
	}
	static function main():Void {
		var lockedRoot:Dynamic = Json.parse(File.getContent(Sys.args()[0]));
		var colorfulRoot:Dynamic = Json.parse(File.getContent(Sys.args()[1]));
		var locked:Dynamic = Reflect.field(lockedRoot, 'song');
		var colorful:Dynamic = Reflect.field(colorfulRoot, 'song');
		var lockedEvents = zoomEvents(locked);
		var firstNote = firstNoteTime(locked);
		var introCount = 0;
		for (event in lockedEvents)
			if (event[0] >= -0.000001 && event[0] < firstNote - 0.000001
				&& cameraZoomEventIsAbsolute(event[1], event[2])) introCount++;
		check(lockedEvents.length >= 5, 'Locked target sequence is incomplete');
		check(cameraZoomIntroUsesTargets(lockedEvents[0][0], firstNote,
			lockedEvents[0][1], lockedEvents[0][2], introCount, 0.5),
			'Locked sequence was not recognized as an intro target');
		var game = 0.5;
		var hud = 1.0;
		for (index in 0...5) {
			var targets = cameraZoomEventTargets(game, hud, lockedEvents[index][1], lockedEvents[index][2], true);
			game = targets[0];
			hud = targets[1];
		}
		check(close(game, 0.9), 'Locked target sequence stacked instead of replacing game zoom');
		check(close(hud, 1.0), 'Locked target sequence changed HUD zoom');

		var pulses = zoomEvents(colorful);
		check(pulses.length > 0, 'Colorful pulse fixture is empty');
		check(!cameraZoomEventIsAbsolute(pulses[0][1], pulses[0][2]),
			'ordinary paired pulse was reclassified as an absolute target');
		var pulseTargets = cameraZoomEventTargets(0.5, 1.0, pulses[0][1], pulses[0][2], false);
		check(close(pulseTargets[0], 0.56), 'ordinary game pulse stopped being additive');
		check(close(pulseTargets[1], 1.03), 'ordinary HUD pulse stopped being additive');
		Sys.println(Json.stringify({locked: lockedEvents.length, intro: introCount, pulses: pulses.length}));
	}
}
'''
        result = run_haxe(fixture, str(locked_path), str(colorful_path))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = last_json(result.stdout)
        self.assertGreaterEqual(payload["locked"], 5)
        self.assertGreater(payload["intro"], 1)
        self.assertGreater(payload["pulses"], 0)
        self.assertEqual({locked_path: sha256(locked_path), colorful_path: sha256(colorful_path)}, before)


if __name__ == "__main__":
    unittest.main()
