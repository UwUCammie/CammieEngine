"""Regression coverage for floating-point tap sustains in imported charts."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class SustainNormalizationTest(unittest.TestCase):
    def test_noise_becomes_a_tap_without_shortening_real_holds(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        start = source.index("\tpublic static inline var SUSTAIN_LENGTH_EPSILON:")
        end = source.index("\n\t// Keep chart/tween speed intact", start)
        helper = source[start:end]
        fixture = """class SustainNormalizationTest {
""" + helper + r'''
	static function check(ok:Bool, message:String):Void {
		if (!ok) throw message;
	}
	static function generatedSegments(value:Dynamic, stepCrochet:Float):Int {
		var length = normalizeSustainLength(value);
		var steps = length / stepCrochet;
		var count = 0;
		var sustainSteps = sustainStepCount(length, stepCrochet);
		if (sustainSteps > 0)
			for (i in 0...sustainSteps)
				if (steps > i) count++;
		return count;
	}
	static function donorSegments(value:Float, stepCrochet:Float):Int {
		var steps = value / stepCrochet;
		var count = 0;
		if (steps != 0)
			for (i in 0...(Math.floor(steps) + 2))
				if (steps > i) count++;
		return count;
	}
	static function main() {
		// These are the remainders emitted by imported charts after subtracting
		// beat-aligned timestamps. They must not turn a tap into a hold segment.
		var noiseValues:Array<Dynamic> = [1.13686837721616e-13,
			2.27373675443232e-13, 5.6843418860808e-12,
			"9.66338120633736e-12", -1e-12];
		for (noise in noiseValues) {
			check(normalizeSustainLength(noise) == 0, "floating-point tap noise survived");
			check(generatedSegments(noise, 100) == 0, "noise spawned a sustain segment");
			check(sustainStepCount(noise, 100) == 0, "noise became a sustain step");
		}
		check(normalizeSustainLength(null) == 0, "missing sustain must be a tap");
		check(normalizeSustainLength("0") == 0, "string zero must be a tap");
		check(normalizeSustainLength("not-a-number") == 0, "invalid sustain must be a tap");
		check(normalizeSustainLength(true) == 0, "boolean sustain must be a tap");
        check(normalizeSustainLength(0.001) == 0.001, "short duration was discarded without a step context");
        check(normalizeSustainLength("125.5") == 125.5, "numeric sustain string was not read");
        check(normalizeSustainLength(100, 100) == 0, "one-step legacy tap sentinel survived");
        check(normalizeSustainLength(100 + 1e-10, 100) == 0,
            "rounded one-step legacy tap sentinel survived");
        check(normalizeSustainLength(125, 100) == 125,
            "hold longer than one step was shortened");
        check(sustainStepCount(100 - 1e-10, 100) == 0,
            "one-step-or-shorter legacy tap sentinel became a hold");
		check(sustainStepCount(200 + 1e-10, 100) == 2,
			"near-integer multi-step hold was truncated");
        // Modding Plus reserves one piece for the legacy tap sentinel. Holds
        // longer than one step still use its ceil(steps) piece count.
        check(sustainStepCount(83, 100) == 0,
            "one-step-or-shorter legacy tap sentinel became a hold");
        check(sustainStepCount(125, 100) == 2,
            "partial hold lost its donor-compatible stem");
        check(generatedSegments(90, 100) == 0, "one-step-or-shorter tap gained a segment");
        check(generatedSegments(125, 100) == 2, "partial hold stem was truncated");
        check(generatedSegments(250, 100) == 3, "fractional hold was floored");
        for (value in [0.001, 83., 90., 100.])
            check(generatedSegments(value, 100) == 0,
                "legacy tap sentinel gained a sustain piece");
        for (value in [125., 166.6666667, 250.])
            check(generatedSegments(value, 100) == donorSegments(value, 100),
                "long sustain piece count diverged from Modding Plus");
	}
}
'''
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "SustainNormalizationTest.hx"
            path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder,
                 "-main", "SustainNormalizationTest", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_generation_normalizes_before_all_sustain_consumers(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("swagNote.sustainLength = normalizeSustainLength(songNotes[2], Conductor.stepCrochet);", source)
        sustain2_start = source.index("\tfunction sustain2(")
        sustain2 = source[sustain2_start:source.index("\n\tfunction ", sustain2_start + 1)]
        self.assertIn("var length:Float = normalizeSustainLength(note.sustainLength, Conductor.stepCrochet);", sustain2)
        self.assertIn("note.sustainLength = length;", sustain2)
        self.assertIn("var sustainSteps:Int = sustainStepCount(susLength, Conductor.stepCrochet);", source)
        self.assertIn("return Std.int(Math.ceil(steps));", source)
        generation_start = source.index("swagNote.sustainLength = normalizeSustainLength")
        generation_end = source.index("if (OptionsHandler.options.emuOsuLifts", generation_start)
        generation = source[generation_start:generation_end]
        self.assertIn("var susLength:Float = swagNote.sustainLength;", generation)
        self.assertNotIn("songNotes[2] != null ? songNotes[2] : 0", generation)
        self.assertIn("if (sustainSteps > 0 && !ModifierState.namedModifiers.nos.value)", generation)
        self.assertNotIn("Math.floor(susLength)", generation)

    def test_partial_hold_has_a_stem_before_the_end_cap(self):
        note = (ROOT / "source/Note.hx").read_text()
        constructor = note[note.index("public function new("):note.index("\n\tpublic function switchType", note.index("public function new("))]
        self.assertIn("animation.play('holdend')", constructor)
        self.assertIn("if (prevNote.isSustainNote)", constructor)
        self.assertIn("prevNote.animation.play('hold')", constructor)

    def test_fnia_ugh_one_step_values_are_legacy_taps(self):
        import json

        fixture = ROOT / "assets/data/fnia-ugh/fnia-ugh-hard.json"
        if not fixture.is_file():
            self.skipTest(f"mounted FNiA Ugh chart fixture unavailable: {fixture}")
        chart = json.loads(fixture.read_text())['song']
        self.assertEqual(chart['bpm'], 160)
        step_crochet = 60000 / chart['bpm'] / 4
        lengths = [note[2] for section in chart['notes'] for note in section['sectionNotes']]
        one_step = [length for length in lengths if abs(length - step_crochet) < 1e-6]
        three_step = [length for length in lengths if abs(length - step_crochet * 3) < 1e-6]
        self.assertEqual(len(one_step), 104)
        self.assertEqual(len(three_step), 56)
        self.assertEqual(len([length for length in lengths if length == 0]), 373)
        self.assertEqual(len([length for length in lengths if 0 < length <= step_crochet]), 104)


if __name__ == "__main__":
    unittest.main()
