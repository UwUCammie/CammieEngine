"""frame_stats reports unrounded mean update, draw and render cost and the batch count.

The harness clock steps in whole milliseconds, so the p50 figures read 0 or 1 ms
for almost every gameplay frame and cannot show a sub-millisecond change. A mean
over a one-second window can. The render mean uses the same window the hitch
tracker times (end of flixel's draw to OpenFL's render end), and drawCallsMean
reads flixel's own per-frame batch counter. meanOf runs here in the interpreter.
"""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_native_asset_resolution import extract_method
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class FrameStatsMeansTest(unittest.TestCase):
    def test_summary_fields_and_reset(self):
        source = (ROOT / 'source/RuntimeSmokeHarness.hx').read_text(encoding='utf-8')
        summary = extract_method(source, 'static function emitFrameSummary(')
        for field in ('updateMeanMs: meanOf(updateCosts)', 'drawMeanMs: meanOf(drawCosts)',
                      'renderMeanMs: renderCosts.length == 0 ? null : meanOf(renderCosts)',
                      'drawCallsMean: meanOf(drawCallCounts)'):
            self.assertIn(field, summary)
        for samples in ('renderCosts.resize(0);', 'drawCallCounts.resize(0);'):
            self.assertIn(samples, summary)
        post = extract_method(source, 'static function onFramePostDraw(')
        self.assertIn('drawCallCounts.push(flixel.graphics.tile.FlxDrawBaseItem.drawCalls);', post)

    def test_mean_of_samples(self):
        source = (ROOT / 'source/RuntimeSmokeHarness.hx').read_text(encoding='utf-8')
        mean = extract_method(source, 'static function meanOf(')
        fixture = '''
class Main {
	''' + mean + '''
	static function main() {
		if (meanOf([]) != 0) throw 'empty window';
		if (meanOf([1, 0, 0, 1]) != 0.5) throw 'whole-millisecond samples average below one';
		if (Math.abs(meanOf([0.25, 0.5, 2.25]) - 1) > 1e-12) throw 'mean';
		Sys.println('ok');
	}
}
'''
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'Main', '--interp'],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
