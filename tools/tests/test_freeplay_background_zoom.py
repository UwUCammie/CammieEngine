from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class FreeplayBackgroundZoomTest(unittest.TestCase):
    """The SHIFT zoom-out in freeplay must not expose black borders.

    Camera zoom scales everything drawn through the camera, background
    included, so the background has to be scaled by the inverse of the zoom to
    keep covering the screen.
    """

    def test_background_scales_inverse_of_camera_zoom(self):
        source = (ROOT / 'source/FreeplayState.hx').read_text()
        start = source.index('\tstatic function backgroundScaleFor(')
        method = source[start:source.index('\n\t}\n', start) + len('\n\t}\n')]
        fixture = 'class BackgroundZoomTest {\n' + method + '''
 static function main(){
  var w = 1280.0;
  var h = 720.0;
  // at the SHIFT zoom the background must span at least the whole camera view
  var zoom = 0.65;
  var s = backgroundScaleFor(zoom);
  var viewW = w / zoom;
  var viewH = h / zoom;
  var bgW = w * s;
  var bgH = h * s;
  if (bgW < viewW || bgH < viewH) throw 'Zoomed-out view not fully covered: ' + bgW + 'x' + bgH + ' vs ' + viewW + 'x' + viewH;
  // no zoom -> no scaling (the normal view must be untouched)
  if (backgroundScaleFor(1) != 1) throw 'Full zoom should not scale the background, got ' + backgroundScaleFor(1);
  if (backgroundScaleFor(1.2) != 1) throw 'Zoom-in should not scale the background, got ' + backgroundScaleFor(1.2);
  // never zero/negative, and degenerate input stays sane
  if (backgroundScaleFor(0.01) <= 1) throw 'Zooming out must grow the background';
  if (backgroundScaleFor(0) != 1 || backgroundScaleFor(-1) != 1) throw 'Non-positive zoom must be a no-op';
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'BackgroundZoomTest.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'BackgroundZoomTest', '--interp'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_update_applies_background_scale(self):
        source = (ROOT / 'source/FreeplayState.hx').read_text()
        update = source[source.index('\toverride function update('):]
        self.assertIn('backgroundScaleFor(FlxG.camera.zoom)', update)
        self.assertIn('bg.updateHitbox()', update)
        self.assertIn('bg.screenCenter()', update)


if __name__ == '__main__':
    unittest.main()
