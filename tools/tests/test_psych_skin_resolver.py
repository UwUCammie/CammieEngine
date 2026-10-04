"""Interpreter coverage for bounded, owner-scoped Psych note skin paths."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import shutil
import subprocess
import tempfile
import unittest
import os


ROOT = Path(__file__).resolve().parents[2]


class PsychSkinResolverTest(unittest.TestCase):
    @unittest.skipIf(os.name == 'nt', 'requires a case-sensitive filesystem fixture')
    def test_owner_pairs_pixel_and_unscoped_fallback(self):
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = Path(folder)
            shutil.copyfile(ROOT / 'source/PsychSkinResolver.hx', work / 'PsychSkinResolver.hx')

            def asset(path):
                target = work / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b'fixture')

            first = 'assets/imported_mods/first'
            second = 'assets/imported_mods/second'
            asset(f'{first}/images/noteSkins/Same.png')
            asset(f'{first}/images/noteSkins/Same.xml')
            asset(f'{second}/images/noteSkins/Same.png')
            asset(f'{second}/images/noteSkins/Same.xml')
            asset(f'{first}/images/noteSkins/Partial.png')
            asset(f'{second}/images/noteSkins/Partial.xml')
            asset(f'{first}/shared/images/noteSkins/Shared.png')
            asset(f'{first}/shared/images/noteSkins/Shared.xml')
            asset(f'{first}/images/noteSkins/Variant.png')
            asset(f'{first}/images/noteSkins/Variant.xml')
            asset(f'{first}/images/noteSkins/Variant-red.png')
            asset(f'{first}/images/noteSkins/Complete.png')
            asset(f'{first}/images/noteSkins/Complete.xml')
            asset(f'{first}/images/noteSkins/Complete-red.png')
            asset(f'{first}/images/noteSkins/Complete-red.xml')
            asset(f'{first}/images/a/b/c/d/e/f/g/h/i/Deep.png')
            asset(f'{first}/images/a/b/c/d/e/f/g/h/i/Deep.xml')
            asset(f'{first}/images/pixelUI/Pix.png')
            asset(f'{first}/images/pixelUI/PixENDS.png')
            asset(f'{first}/images/pixelUI/Pix-red.png')
            asset(f'{first}/images/pixelUI/PixENDS-red.png')
            asset(f'{first}/images/pixelUI/Broken.png')
            asset('assets/images/noteSkins/Legacy.png')
            asset('assets/images/noteSkins/Legacy.xml')
            asset('assets/images/custom_ui/ui_packs/normal/NOTE_assets.png')
            asset('assets/images/custom_ui/ui_packs/normal/NOTE_assets.xml')
            asset(f'{first}/images/noteSkins/Case.png')
            asset(f'{first}/images/noteSkins/Case.xml')
            asset(f'{first}/images/noteSkins/case.png')

            (work / 'Probe.hx').write_text(r'''
class Probe {
  static function check(value:Bool, message:String):Void
    if (!value) throw message;
  static function main():Void {
    var first = 'assets/imported_mods/first';
    var second = 'assets/imported_mods/second';
    var a = PsychSkinResolver.resolve('noteSkins/Same', first, false);
    var b = PsychSkinResolver.resolve('noteSkins/Same', second, false);
    check(a != null && b != null && a.image != b.image, 'same key must keep owners apart');
    check(a.image == first + '/images/noteSkins/Same.png', 'first image');
    check(a.metadata == first + '/images/noteSkins/Same.xml', 'first xml');
    check(b.image == second + '/images/noteSkins/Same.png', 'second image');
    var partial = PsychSkinResolver.resolveDetailed('noteSkins/Partial', first, false);
    check(partial.descriptor == null && partial.reason.indexOf('Partial.xml') >= 0,
      'must diagnose incomplete first-owner pair');
    check(PsychSkinResolver.resolve('noteSkins/Shared', first, false).image ==
      first + '/shared/images/noteSkins/Shared.png', 'shared path');
    check(PsychSkinResolver.resolve('noteSkins/Variant', first, false, '-red').key ==
      'noteSkins/Variant', 'incomplete postfix must fall back to base');
    check(PsychSkinResolver.resolve('noteSkins/Complete', first, false, '-red').image ==
      first + '/images/noteSkins/Complete-red.png', 'complete postfix wins');
    check(PsychSkinResolver.resolve('a/b/c/d/e/f/g/h/i/Deep', first, false) != null,
      'deep logical path remains valid');
    var pixel = PsychSkinResolver.resolve('Pix', first, true);
    check(pixel != null && pixel.metadata == null && pixel.endsImage ==
      first + '/images/pixelUI/PixENDS.png', 'pixel sheet and ENDS');
    var pixelVariant = PsychSkinResolver.resolve('Pix', first, true, '-red');
    check(pixelVariant != null && pixelVariant.image ==
      first + '/images/pixelUI/Pix-red.png' && pixelVariant.endsImage ==
      first + '/images/pixelUI/PixENDS-red.png', 'pixel postfix follows ENDS');
    var broken = PsychSkinResolver.resolveDetailed('Broken', first, true);
    check(broken.descriptor == null && broken.reason.indexOf('BrokenENDS.png') >= 0,
      'pixel ENDS required');
    check(PsychSkinResolver.resolve('noteSkins/Legacy', first, false) == null,
      'scoped owner cannot fall through to global');
    check(PsychSkinResolver.resolve('noteSkins/Legacy', '', false).image ==
      'assets/images/noteSkins/Legacy.png', 'unscoped global fallback');
    check(PsychSkinResolver.resolve('noteSkins/NOTE_assets', first, false).image ==
      'assets/images/custom_ui/ui_packs/normal/NOTE_assets.png',
      'missing source engine base skin must use the native base atlas');
    check(PsychSkinResolver.resolveDetailed('noteSkins/NOTE_assets', first, false)
      .descriptor.nativeDefaultFallback, 'native fallback is explicitly classified');
    check(!PsychSkinResolver.resolveDetailed('noteSkins/Same', first, false)
      .descriptor.nativeDefaultFallback, 'authored owner atlas keeps RGB enabled');
    for (bad in ['../escape', '/absolute', 'a//b', 'a/./b', 'a\\b', 'C:/drive',
      'a.png'])
      check(PsychSkinResolver.resolveDetailed(bad, first, false).reason.indexOf('unsafe') >= 0,
        'unsafe key ' + bad);
    check(PsychSkinResolver.resolveDetailed('noteSkins/Same',
      'assets/imported_mods/../second', false).reason.indexOf('unsafe owner') >= 0,
      'unsafe owner');
    var ambiguous = PsychSkinResolver.resolveDetailed('noteSkins/Case', first, false);
    check(ambiguous.descriptor == null && ambiguous.reason.indexOf('ambiguous case') >= 0,
      'case variant collision');
  }
}
''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(work), '-main', 'Probe', '--interp'],
                cwd=work, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
