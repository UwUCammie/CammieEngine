"""An add-on Psych song finds the HUD icons of its import's base mod."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / 'tmp'
TMP.mkdir(exist_ok=True)

PROBE = r'''
class Probe {
  static function check(ok:Bool, label:String):Void if (!ok) throw label;
  // The shape PsychOwnerPaths.create returns: getPath maps a relative file into one root.
  static function facade(root:String):Dynamic {
    var proxy:Dynamic = {};
    Reflect.setField(proxy, 'getPath', function(file:String, ?type:Dynamic):String return root + '/' + file);
    return proxy;
  }
  static function rootOf(paths:Dynamic):String
    return Reflect.callMethod(paths, Reflect.field(paths, 'getPath'), ['x'])
      .split('/x')[0];
  static function main():Void {
    var selected = facade('owner');
    var base = facade('base');
    var other = facade('other');
    var deps:Array<Dynamic> = [base, other];
    check(rootOf(SourceHealthIconRoots.owning(selected, deps, 'images/icons/icon-bffnia.png')) == 'base',
      'the base mod of the import supplies an icon the add-on lacks');
    check(rootOf(SourceHealthIconRoots.owning(selected, deps, 'images/icons/icon-both.png')) == 'owner',
      'the selected owner keeps priority when both hold the icon');
    check(rootOf(SourceHealthIconRoots.owning(selected, deps, 'images/icons/icon-second.png')) == 'other',
      'roots are searched in the order given');
    check(rootOf(SourceHealthIconRoots.owning(selected, deps, 'images/icons/icon-none.png')) == 'owner',
      'nobody holding it leaves the selected owner to answer');
    check(rootOf(SourceHealthIconRoots.owning(selected, [], 'images/icons/icon-bffnia.png')) == 'owner',
      'no dependency roots changes nothing');
    check(rootOf(SourceHealthIconRoots.owning(selected, null, 'images/icons/icon-bffnia.png')) == 'owner',
      'null dependency roots changes nothing');
  }
}
'''


class SourceHealthIconRootsTest(unittest.TestCase):
    def test_icon_lookup_order(self):
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            work = Path(folder)
            for root, names in (('owner', ['icon-both']), ('base', ['icon-bffnia', 'icon-both']),
                                ('other', ['icon-second'])):
                (work / root / 'images/icons').mkdir(parents=True)
                for name in names:
                    (work / root / 'images/icons' / (name + '.png')).write_bytes(b'x')
            (work / 'SourceHealthIconRoots.hx').write_text(
                (ROOT / 'source/SourceHealthIconRoots.hx').read_text(encoding='utf-8'), newline='\n')
            (work / 'FNFAssets.hx').write_text('''class FNFAssets {
  public static function exists(path:String):Bool return path != null && sys.FileSystem.exists(path);
}
''', newline='\n')
            (work / 'openfl/utils').mkdir(parents=True)
            (work / 'openfl/utils/AssetType.hx').write_text(
                'package openfl.utils;\nenum abstract AssetType(String) {var IMAGE = "IMAGE";}\n', newline='\n')
            (work / 'Probe.hx').write_text(PROBE, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(work), '--run', 'Probe'],
                cwd=work, env={**os.environ, 'TMPDIR': str(TMP)}, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hud_owner_uses_the_import_roots_for_psych_only(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        self.assertIn('var dependencies:Array<Dynamic> = nightmare || psychPaths != null ? [] : psychDependencyIconPaths();', play)
        self.assertIn('SourceHealthIconRoots.owning(paths, dependencies,', play)
        start = play.index('function psychDependencyIconPaths(')
        body = play[start:play.index('function isSourceHUDIconAlias(', start)]
        # Only roots the song's own manifest lists, each through a confined owner facade.
        self.assertIn('Song.psychCharacterOwnerRootsForSong(Song.storageFolder(SONG))', body)
        self.assertIn('PsychOwnerAssetPath.normalizeOwner(root)', body)
        self.assertIn('PsychOwnerPaths.bridgeFacade(', body)
        self.assertIn('!= PsychOwnerAssetPath.normalizeOwner(selected)', body)


if __name__ == '__main__':
    unittest.main()
