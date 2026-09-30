"""Generic elapsed-time normalization for legacy HScript update hooks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HScript = ROOT / ".haxelib/hscript/2,5,0"
DONOR = Path("/run/media/cammie/External Storage/modding-plus-fnf")


def run_haxe(fixture: str, *args: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory(prefix="legacy-frame-delta-", dir=ROOT / "tmp") as folder:
        path = Path(folder) / "LegacyFrameDeltaTest.hx"
        path.write_text(fixture)
        return subprocess.run(
            [str(HAXE), "-cp", folder, "-cp", str(ROOT / "source"), "-cp", str(HScript),
             "--run", "LegacyFrameDeltaTest", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )


FIXTURE = r'''import haxe.Json;
import hscript.Interp;
import hscript.Parser;
import sys.io.File;

class LegacySprite {
	public var alpha:Float = 0;
	public function new() {}
}
class LegacySound {
	public var volume:Float = 0;
	public function new() {}
	public function play():Void {}
}
class LegacyJustPressed {
	public var SPACE:Bool = false;
	public function new() {}
}
class LegacyKeys {
	public var justPressed:LegacyJustPressed = new LegacyJustPressed();
	public function new() {}
}
class LegacyCamera {
	public var zoom:Float = 0.8;
	public function new() {}
}
class LegacyFlxG {
	public var keys:LegacyKeys = new LegacyKeys();
	public var camera:LegacyCamera = new LegacyCamera();
	public function new() {}
}
class LegacyState {
	public var health:Float;
	public var demoMode:Bool = false;
	public function new(value:Float) health = value;
}

class LegacyFrameDeltaTest {
	static function check(condition:Bool, message:String):Void {
		if (!condition) throw message;
	}

	static function close(a:Float, b:Float):Bool return Math.abs(a - b) < 0.00001;

	static function runAtFps(updateSource:String, fps:Int):Array<Float> {
		var interp = new Interp();
		var state = new LegacyState(1.0);
		var rage = new LegacySprite();
		var red = new LegacySprite();
		var flx = new LegacyFlxG();
		var spam = new LegacySound();
		interp.variables.set('frameRateScale', function(elapsed:Float):Float return Math.max(0, elapsed * 60));
		interp.variables.set('currentPlayState', state);
		interp.variables.set('health', 1.0);
		interp.variables.set('rage', rage);
		interp.variables.set('red', red);
		interp.variables.set('spam', spam);
		interp.variables.set('FlxG', flx);
		interp.variables.set('setDefaultZoom', function(value:Float):Void flx.camera.zoom = value);
		interp.variables.set('activate', 1);
		interp.variables.set('drain', 0);
		interp.execute(new Parser().parseString(updateSource));
		var update:Dynamic = interp.variables.get('update');
		for (_ in 0...fps) {
			flx.keys.justPressed.SPACE = false;
			update(1.0 / fps);
		}
		return [state.health, red.alpha];
	}

	static function updateOnly(source:String):String {
		var start = source.indexOf('function update');
		var end = source.indexOf('function stepHit', start);
		if (start < 0 || end < 0) throw 'Inquiry update hook was not found';
		return source.substr(start, end - start);
	}

	static function main():Void {
		if (Sys.args().length == 0) {
			var source = "function update(elapsed) {\n"
				+ "  // ignored += 9.9;\n"
				+ "  var text = 'ignored += 8.8;';\n"
				+ "  value += 0.5;\n"
				+ "  count += 1;\n"
				+ "  already += 0.25 * frameRateScale(elapsed);\n"
				+ "  unclear += getDelta();\n"
				+ "}";
			var result = EngineCompat.normalizeLegacyFrameDeltas(source);
			check(result.rewritten == 1, 'unexpected rewrite count: ' + result.rewritten);
			check(result.source.indexOf('value += 0.5 * frameRateScale(elapsed);') >= 0, 'decimal delta was not scaled');
			check(result.source.indexOf('count += 1;') >= 0, 'integer counter was changed');
			check(result.source.indexOf('already += 0.25 * frameRateScale(elapsed);') >= 0, 'existing elapsed expression was changed');
			check(result.source.indexOf('ignored += 9.9;') >= 0, 'comment was changed');
			check(result.source.indexOf('ignored += 8.8;') >= 0, 'string was changed');
			check(result.diagnostics.length == 1, 'ambiguous mutation was not diagnosed');
			check(result.diagnostics[0].code == 'legacy-frame-delta-ambiguous', 'wrong diagnostic code');
			Sys.println('ok');
			return;
		}

		var path = Sys.args()[0];
		var raw = File.getContent(path);
		var result = EngineCompat.normalizeLegacyFrameDeltas(raw);
		var update = updateOnly(result.source);
		var at30 = runAtFps(update, 30);
		var at60 = runAtFps(update, 60);
		var at120 = runAtFps(update, 120);
		check(result.rewritten == 2, 'Inquiry should have two decimal rewrites, got ' + result.rewritten);
		check(at30.length == 2 && at60.length == 2 && at120.length == 2, 'missing FPS result');
		check(close(at30[0], at60[0]) && close(at60[0], at120[0]), 'health drain varies by FPS');
		check(close(at30[1], at60[1]) && close(at60[1], at120[1]), 'red alpha varies by FPS');
		check(close(at60[0], 0.64), 'unexpected one-second health rate: ' + at60[0]);
		check(close(at60[1], 0.42), 'unexpected one-second alpha rate: ' + at60[1]);
		Sys.println(Json.stringify({rewritten: result.rewritten, diagnostics: result.diagnostics.length,
			at30: at30, at60: at60, at120: at120}));
	}
}
'''


class LegacyFrameDeltaNormalizerTest(unittest.TestCase):
    def test_only_safe_decimal_deltas_are_rewritten(self):
        result = run_haxe(FIXTURE)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok", result.stdout)

    def test_inquiry_donor_is_normalized_in_memory_at_multiple_fps(self):
        script = DONOR / "assets/images/custom_stages/inquiry.hscript"
        if not script.is_file():
            self.skipTest(f"mounted Inquiry donor unavailable: {script}")
        before = hashlib.sha256(script.read_bytes()).hexdigest()
        result = run_haxe(FIXTURE, str(script))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(payload["rewritten"], 2)
        self.assertEqual(payload["diagnostics"], 0)
        self.assertEqual(hashlib.sha256(script.read_bytes()).hexdigest(), before)
