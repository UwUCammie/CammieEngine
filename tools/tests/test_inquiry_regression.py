"""Regression coverage for Inquiry's cross-difficulty visuals and timing.

Inquiry's hard chart intentionally contains gameplay data of its own, but some
of its visual metadata is absent.  These tests exercise the generic resolver
and the stage script without changing any chart data.
"""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def run_haxe(fixture: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "InquiryRegressionTest.hx"
        path.write_text(fixture)
        return subprocess.run(
            [
                str(ROOT / ".tools/haxe/haxe"),
                "-cp",
                folder,
                "-cp",
                str(ROOT / "source"),
                "-cp",
                str(ROOT / ".haxelib/hscript/2,5,0"),
                "-main",
                "InquiryRegressionTest",
                "--interp",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )


class InquiryRegressionTest(unittest.TestCase):
    def test_missing_visuals_fall_back_without_replacing_gameplay(self):
        normal_fixture = ROOT / "assets/data/inquiry/inquiry.json"
        hard_fixture = ROOT / "assets/data/inquiry/inquiry-hard.json"
        if not normal_fixture.is_file() or not hard_fixture.is_file():
            self.skipTest(f"mounted Inquiry chart fixtures unavailable: {normal_fixture}, {hard_fixture}")
        normal = json.loads(normal_fixture.read_text())["song"]
        hard = json.loads(hard_fixture.read_text())["song"]
        self.assertEqual(normal["stage"], "inquiry")
        self.assertEqual(normal["gf"], "gfglitched")
        # The authored hard chart keeps its foreign visual id.  Runtime
        # sibling resolution, rather than a chart edit, supplies scrapeface.
        self.assertEqual(hard["player2"], "scrappy")
        self.assertNotIn("stage", hard)
        self.assertNotIn("gf", hard)

        source = (ROOT / "source/Song.hx").read_text()
        fields_start = source.index("\tstatic var gameplayFields")
        fields_end = source.index("\tstatic var registryCache", fields_start)
        fields = source[fields_start:fields_end]
        chart_has_value_start = source.index("\tstatic function chartHasValue(")
        chart_has_value_end = source.index("\n\tstatic function readRegistry", chart_has_value_start)
        chart_has_value = source[chart_has_value_start:chart_has_value_end]
        resolve_start = source.index("\tpublic static function resolveChartData(")
        resolve_end = source.index("\n\tstatic function visualValueIsValid", resolve_start)
        resolve = source[resolve_start:resolve_end]
        visual_valid_start = source.index("\tstatic function visualValueIsValid(")
        visual_valid_end = source.index("\n\tstatic function hasGraphicVisuals", visual_valid_start)
        visual_valid = source[visual_valid_start:visual_valid_end]

        fixture = """class InquiryRegressionTest {
""" + fields + chart_has_value + """
	static function isValidVisualValue(field:String, value:Dynamic):Bool return false;
""" + resolve + visual_valid + """
	static function check(condition:Bool, message:String):Void {
		if (!condition) throw message;
	}

	static function main() {
		// This models Inquiry-hard: notes/timing are present, but several
		// visual fields are missing or stale.  The explicit dad remains valid.
		var requested:Dynamic = {
			song: 'inquiry', notes: [1, 2, 3], bpm: 174, needsVoices: true,
			speed: 2.25, events: [['Add Camera Zoom', '0.1', '0.1']], mania: 0,
			player1: 'bf', player2: 'dad', gf: '', stage: 'missing-stage',
			uiType: 'missing-ui', cutsceneType: 'missing-cutscene',
			forceLayout: 'missing-layout', uiLayoutType: '', stageID: 7
		};
		var base:Dynamic = {
			player1: 'missing-player', player2: 'missing-opponent',
			gf: 'missing-gf', stage: 'missing-stage', uiType: 'missing-ui',
			cutsceneType: 'missing-cutscene', forceLayout: 'missing-layout'
		};
		var sibling:Dynamic = {
			player1: 'sibling-bf', player2: 'scrapeface', gf: 'gfglitched',
			stage: 'inquiry', uiType: 'inquiry-ui', cutsceneType: 'fleetway',
			forceLayout: 'inquiry-layout', uiLayoutType: 'inquiry-layout', stageID: 9
		};
		var valid = new Map<String, Bool>();
		for (value in [
			'player1=bf', 'player2=dad', 'player2=scrapeface',
			'gf=gfglitched', 'stage=inquiry', 'uiType=inquiry-ui',
			'cutsceneType=fleetway', 'forceLayout=inquiry-layout',
			'uiLayoutType=inquiry-layout', 'stageID=7'
		]) valid.set(value, true);

		var resolved = resolveChartData(requested, [sibling], base, valid);
		check(resolved.song == 'inquiry', 'song gameplay field was replaced');
		check(resolved.notes == requested.notes, 'notes gameplay field was replaced');
		check(resolved.bpm == 174, 'bpm gameplay field was replaced');
		check(resolved.speed == 2.25, 'speed gameplay field was replaced');
		check(resolved.events == requested.events, 'events gameplay field was replaced');
		check(resolved.player1 == 'bf', 'valid requested player was replaced');
		check(resolved.player2 == 'dad', 'valid requested opponent was replaced');
		check(resolved.gf == 'gfglitched', 'missing girlfriend did not use sibling visuals');
		check(resolved.stage == 'inquiry', 'missing stage did not use sibling visuals');
		check(resolved.uiType == 'inquiry-ui', 'missing UI did not use sibling visuals');
		check(resolved.cutsceneType == 'fleetway', 'missing cutscene did not use sibling visuals');
		check(resolved.forceLayout == 'inquiry-layout', 'missing layout did not use sibling visuals');
		check(resolved.stageID == 7, 'valid requested stage ID was replaced');
	}
}
"""
        result = run_haxe(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_inquiry_spam_drain_and_red_alpha_are_elapsed_based(self):
        fixture = ROOT / "assets/images/custom_stages/inquiry.hscript"
        if not fixture.is_file():
            self.skipTest(f"mounted Inquiry stage fixture unavailable: {fixture}")
        script = fixture.read_text()
        update = script[script.index("function update"):script.index("function stepHit")]
        self.assertIn("currentPlayState.health -= 0.006", update)
        self.assertIn("red.alpha += 0.007", update)

        fixture = """import hscript.Interp;
import hscript.Parser;

class Sprite {
	public var alpha:Float = 0;
	public function new() {}
}
class Sound {
	public var volume:Float = 0;
	public function new() {}
	public function play():Void {}
}
class JustPressed {
	public var SPACE:Bool = false;
	public function new() {}
}
class Keys {
	public var justPressed:JustPressed = new JustPressed();
	public function new() {}
}
class Camera {
	public var zoom:Float = 0.8;
	public function new() {}
}
class FlxGProxy {
	public var keys:Keys = new Keys();
	public var camera:Camera = new Camera();
	public function new() {}
}
class State {
	public var health:Float;
	public function new(value:Float) health = value;
}

class InquiryRegressionTest {
	static function runAtFps(stageUpdate:String, fps:Int):Array<Float> {
		stageUpdate = EngineCompat.normalizeLegacyFrameDeltas(stageUpdate).source;
		var interp = new Interp();
		var state = new State(1.0);
		var rage = new Sprite();
		var red = new Sprite();
		var flx = new FlxGProxy();
		var spam = new Sound();
		interp.variables.set('frameRateScale', function(elapsed:Float):Float return Math.max(0, elapsed * 60));
		interp.variables.set('currentPlayState', state);
		interp.variables.set('health', 1.0);
		interp.variables.set('rage', rage);
		interp.variables.set('red', red);
		interp.variables.set('spam', spam);
		interp.variables.set('FlxG', flx);
		interp.variables.set('activate', 1);
		interp.variables.set('drain', 1);
		interp.execute(new Parser().parseString(stageUpdate));
		var update:Dynamic = interp.variables.get('update');
		for (_ in 0...fps) {
			flx.keys.justPressed.SPACE = false;
			update(1.0 / fps);
		}
		return [state.health, red.alpha];
	}

	static function close(a:Float, b:Float):Bool return Math.abs(a - b) < 0.00001;

	static function main() {
		var at30 = runAtFps(""" + json.dumps(update) + """, 30);
		var at60 = runAtFps(""" + json.dumps(update) + """, 60);
		var at120 = runAtFps(""" + json.dumps(update) + """, 120);
		if (!close(at30[0], at60[0]) || !close(at60[0], at120[0]))
			throw 'Inquiry health drain changes with FPS: ' + at30[0] + ', ' + at60[0] + ', ' + at120[0];
		if (!close(at30[1], at60[1]) || !close(at60[1], at120[1]))
			throw 'Inquiry red alpha changes with FPS: ' + at30[1] + ', ' + at60[1] + ', ' + at120[1];
		if (!close(at60[0], 0.64) || !close(at60[1], 0.42))
			throw 'Unexpected one-second Inquiry rates: health=' + at60[0] + ', red=' + at60[1];
	}
}
"""
        result = run_haxe(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_inquiry_shake_uses_flixel_elapsed_duration(self):
        fixture = ROOT / "assets/images/custom_stages/inquiry.hscript"
        if not fixture.is_file():
            self.skipTest(f"mounted Inquiry stage fixture unavailable: {fixture}")
        stage = fixture.read_text()
        self.assertIn("FlxG.camera.shake(0.04, 0.08);", stage)

        camera = (ROOT / ".haxelib/flixel/6,1,2/flixel/FlxCamera.hx").read_text()
        update_start = camera.index("\tfunction updateShake(elapsed:Float):Void")
        update_end = camera.index("\n\t/**", update_start)
        update_shake = camera[update_start:update_end]
        self.assertIn("_fxShakeDuration -= elapsed;", update_shake)
        self.assertNotIn("_fxShakeDuration -= 1", update_shake)


if __name__ == "__main__":
    unittest.main()
