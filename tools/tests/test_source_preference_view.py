"""Gameplay reads shared owner preferences through one live view."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath

ROOT = Path(__file__).resolve().parents[2]


FIXTURE = r'''
class Main {
 static function eq(actual:Dynamic, expected:Dynamic, name:String):Void
  if (actual != expected) throw name + ': expected ' + expected + ', got ' + actual;

 static function main():Void {
  var psych:Dynamic = {data:{antialiasing:false, hideHud:true, healthBarAlpha:0.25, timeBarType:'Disabled',
   ghostTapping:false, camZooms:false, noteOffset:12.5, hitsoundVolume:0.5, cacheOnGPU:true},
   view:{antialiasing:true, hideHud:false}};
  var nv:Dynamic = {view:{globalAntialiasing:false, hideHud:true, healthBarAlpha:0.75, timeBarType:'Song Name',
   ghostTapping:false, camZooms:false, noteOffset:-3, hitsoundVolume:1, gpuCaching:false},
   data:{globalAntialiasing:true, hideHud:false}};

  // Each owner answers from its own object and its own spelling.
  eq(SourceGameplayPreferences.antialiasing(psych, false, true), false, 'psych antialiasing');
  eq(SourceGameplayPreferences.antialiasing(nv, true, true), false, 'nightmare antialiasing uses its older name');
  eq(SourceGameplayPreferences.hideHud(psych, false), true, 'psych hideHud');
  eq(SourceGameplayPreferences.hideHud(nv, true), true, 'nightmare hideHud');
  eq(SourceGameplayPreferences.healthBarAlpha(psych, false), 0.25, 'psych healthBarAlpha');
  eq(SourceGameplayPreferences.healthBarAlpha(nv, true), 0.75, 'nightmare healthBarAlpha');
  eq(SourceGameplayPreferences.timeBarType(psych, false), 'Disabled', 'psych timeBarType');
  eq(SourceGameplayPreferences.timeBarType(nv, true), 'Song Name', 'nightmare timeBarType');
  eq(SourceGameplayPreferences.ghostTapping(psych, false, true), false, 'psych ghostTapping');
  eq(SourceGameplayPreferences.ghostTapping(nv, true, true), false, 'nightmare ghostTapping');
  eq(SourceGameplayPreferences.camZooms(psych, false, true), false, 'psych camZooms');
  eq(SourceGameplayPreferences.camZooms(nv, true, true), false, 'nightmare camZooms');
  eq(SourceGameplayPreferences.noteOffset(psych, false, 99), 12.5, 'psych noteOffset');
  eq(SourceGameplayPreferences.noteOffset(nv, true, 99), -3, 'nightmare noteOffset');
  eq(SourceGameplayPreferences.hitsoundVolume(psych, false), 0.5, 'psych hitsoundVolume');
  eq(SourceGameplayPreferences.hitsoundVolume(nv, true), 1, 'nightmare hitsoundVolume');
  eq(SourceGameplayPreferences.cacheOnGPU(psych, false, false), true, 'psych cacheOnGPU');
  eq(SourceGameplayPreferences.cacheOnGPU(nv, true, true), false, 'nightmare gpu caching uses its own name');

  // Nothing is sampled: a script changing the owner object is seen at once.
  psych.data.antialiasing = true; psych.data.healthBarAlpha = 0; psych.data.timeBarType = 'Time Left';
  nv.view.globalAntialiasing = true; nv.view.hideHud = false; nv.view.noteOffset = 40;
  eq(SourceGameplayPreferences.antialiasing(psych, false, false), true, 'psych live antialiasing');
  eq(SourceGameplayPreferences.healthBarAlpha(psych, false), 0, 'a live zero alpha is a value, not a missing one');
  eq(SourceGameplayPreferences.timeBarType(psych, false), 'Time Left', 'psych live timeBarType');
  eq(SourceGameplayPreferences.antialiasing(nv, true, false), true, 'nightmare live antialiasing');
  eq(SourceGameplayPreferences.hideHud(nv, true), false, 'nightmare live hideHud');
  eq(SourceGameplayPreferences.noteOffset(nv, true, 0), 40, 'nightmare live noteOffset');
  var replaced:Dynamic = {hideHud:false, healthBarAlpha:0.5};
  psych.data = replaced;
  eq(SourceGameplayPreferences.hideHud(psych, false), false, 'a replaced data object is read');
  eq(SourceGameplayPreferences.healthBarAlpha(psych, false), 0.5, 'a replaced data object is read for numbers');

  // No owner, a missing field or a wrong kind of value: the supplied default.
  eq(SourceGameplayPreferences.antialiasing(null, false, true), true, 'no owner keeps the host antialiasing on');
  eq(SourceGameplayPreferences.antialiasing(null, true, false), false, 'no owner keeps the host antialiasing off');
  eq(SourceGameplayPreferences.hideHud(null, false), false, 'no owner shows the hud');
  eq(SourceGameplayPreferences.healthBarAlpha(null, true), 1, 'no owner keeps the health bar opaque');
  eq(SourceGameplayPreferences.timeBarType(null, false), 'Time Left', 'no owner keeps the time bar');
  eq(SourceGameplayPreferences.noteOffset(null, false, 7.5), 7.5, 'no owner uses the host offset');
  eq(SourceGameplayPreferences.ghostTapping(null, true, true), true, 'no owner uses the host ghost tapping');
  eq(SourceGameplayPreferences.antialiasing(psych, false, true), true, 'a missing field uses the host default');
  eq(SourceGameplayPreferences.noteOffset(psych, false, 7.5), 7.5, 'a missing number uses the host default');
  var odd:Dynamic = {data:{hideHud:'yes', healthBarAlpha:'half', timeBarType:5, noteOffset:Math.NaN, camZooms:null}};
  eq(SourceGameplayPreferences.hideHud(odd, false), false, 'text is not a switch');
  eq(SourceGameplayPreferences.healthBarAlpha(odd, false), 1, 'text is not a number');
  eq(SourceGameplayPreferences.timeBarType(odd, false), 'Time Left', 'a number is not text');
  eq(SourceGameplayPreferences.noteOffset(odd, false, 2), 2, 'NaN is not an offset');
  eq(SourceGameplayPreferences.camZooms(odd, false, true), true, 'null is not a switch');
  eq(SourceGameplayPreferences.liveFloat(odd, false, 'healthBarAlpha', 0.3), 0.3, 'liveFloat fallback');
  eq(SourceGameplayPreferences.liveString(psych, false, 'absent', 'kept'), 'kept', 'liveString fallback');

  // An owner that lost its preference object is a real fault, not a default.
  var threw = false;
  try SourceGameplayPreferences.hideHud({data:null}, false) catch (error:Dynamic)
   threw = Std.string(error).indexOf('no data object for hideHud') >= 0;
  if (!threw) throw 'a psych owner without data was read as a default';
  threw = false;
  try SourceGameplayPreferences.healthBarAlpha({data:{}}, true) catch (error:Dynamic)
   threw = Std.string(error).indexOf('no view object for healthBarAlpha') >= 0;
  if (!threw) throw 'a nightmare owner without a view was read as a default';
 }
}
'''


class SourcePreferenceViewTest(unittest.TestCase):
    def test_shared_names_resolve_live_from_the_active_owner(self):
        with tempfile.TemporaryDirectory(prefix='source-pref-view-', dir=ROOT / 'tmp') as folder:
            scratch = FixturePath(folder)
            (scratch / 'Main.hx').write_text(FIXTURE, encoding='utf-8', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(scratch), '--main', 'Main', '--interp'],
                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hud_reads_go_through_the_view(self):
        source = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        # The owner spelling and the host fallback live in one place now.
        self.assertNotIn('psychClientPrefs == null ? OptionsHandler.options.antialiasing', source)
        self.assertNotIn('nightmareVisionPrefs.view.antialiasing', source)
        self.assertNotIn('psychClientPrefs.data.healthBarAlpha', source)
        self.assertIn('SourceGameplayPreferences.healthBarAlpha(nightmareVisionPrefs, true)', source)
        self.assertIn('SourceGameplayPreferences.hideHud(psychClientPrefs, false)', source)


if __name__ == '__main__':
    unittest.main()
