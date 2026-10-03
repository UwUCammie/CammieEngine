"""Psych skin imports retain selected-owner sheets and existing destination bytes."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "tmp"


class PsychSkinImportAssetsTest(unittest.TestCase):
    def test_selected_owner_complete_pairs_and_missing_only_repair(self):
        TMP.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="psych-skin-import-", dir=TMP) as work:
            fixture = Path(work)
            (fixture / "SkinImportFixture.hx").write_text(r'''
import sys.FileSystem;
import sys.io.File;
class SkinImportFixture {
  static function put(path:String, content:String):Void {
    FileSystem.createDirectory(haxe.io.Path.directory(path));
    File.saveContent(path, content);
  }
  static function main():Void {
    var chart:Dynamic = {song:{arrowSkin:'custom/RED'}};
    put('donor-a/images/noteSkins/NOTE_assets.png', 'a-default-png');
    put('donor-a/images/noteSkins/NOTE_assets.xml', 'a-default-xml');
    put('donor-a/images/custom/RED.png', 'a-red-png');
    put('donor-a/images/custom/RED.xml', 'a-red-xml');
    put('donor-a/images/pixelUI/custom/RED.png', 'a-red-pixel');
    put('donor-a/images/pixelUI/custom/REDENDS.png', 'a-red-ends');
    put('donor-a/shared/images/pixelUI/PIX.png', 'a-pixel');
    put('donor-a/shared/images/pixelUI/PIXENDS.png', 'a-ends');
    put('donor-a/images/BROKEN.png', 'orphan');
    put('donor-a/images/MIXED.png', 'orphan-sparrow');
    put('donor-a/images/pixelUI/MIXED.png', 'mixed-pixel');
    put('donor-a/images/pixelUI/MIXEDENDS.png', 'mixed-ends');
    put('donor-a/data/song/Note.lua', "setPropertyFromGroup('unspawnNotes', i, 'texture', 'PIX')\nsetProperty('notes[0].texture', 'BROKEN')\nsetProperty('notes[1].texture', 'MIXED')");
    put('donor-b/images/custom/RED.png', 'b-red-png');
    put('donor-b/images/custom/RED.xml', 'b-red-xml');
    var a = 'assets/imported_mods/a';
    var b = 'assets/imported_mods/b';
    var first = PsychSkinImportAssets.copy('donor-a/', a, [chart]);
    if (first.copied != 10 || first.failed != 0) throw 'first copy count ' + first.copied;
    if (File.getContent(a + '/images/custom/RED.png') != 'a-red-png') throw 'owner a';
    if (File.getContent(a + '/images/pixelUI/custom/REDENDS.png') != 'a-red-ends') throw 'same key pixel';
    if (FileSystem.exists(a + '/images/BROKEN.png')) throw 'orphan copied';
    if (FileSystem.exists(a + '/images/MIXED.png')) throw 'incomplete Sparrow copied';
    if (File.getContent(a + '/images/pixelUI/MIXEDENDS.png') != 'mixed-ends') throw 'pixel hidden by Sparrow';
    if (File.getContent(a + '/shared/images/pixelUI/PIXENDS.png') != 'a-ends') throw 'pixel end';
    if (first.diagnostics.length == 0) throw 'missing incomplete diagnostics';
    var second = PsychSkinImportAssets.copy('donor-b', b, [chart]);
    if (second.copied != 2 || File.getContent(b + '/images/custom/RED.png') != 'b-red-png') throw 'owner b';
    var missingDefault = false;
    for (diagnostic in second.diagnostics)
      if (diagnostic.indexOf('noteSkins/NOTE_assets') >= 0) missingDefault = true;
    if (!missingDefault) throw 'missing default diagnostic';
    put('assets/images/custom_ui/ui_packs/normal/NOTE_assets.png', 'host-default-png');
    put('assets/images/custom_ui/ui_packs/normal/NOTE_assets.xml', 'host-default-xml');
    var hostDefault = PsychSkinImportAssets.copy('donor-b', 'assets/imported_mods/c', [{song:{arrowSkin:''}}]);
    for (diagnostic in hostDefault.diagnostics)
      if (diagnostic.indexOf('noteSkins/NOTE_assets') >= 0) throw 'false host default diagnostic';
    put(a + '/images/custom/RED.png', 'user-override');
    var repair = PsychSkinImportAssets.copy('donor-a', a, [chart]);
    if (repair.copied != 0 || File.getContent(a + '/images/custom/RED.png') != 'user-override') throw 'overwrite';
    if (PsychSkinImportAssets.chartKeys([{song:{arrowSkin:''}}]).length != 1) throw 'empty default';
    if (PsychSkinImportAssets.chartKeys([{song:{arrowSkin:'../escape'}}]).length != 2) throw 'chart read';
    var unsafe = PsychSkinImportAssets.copy('donor-a', a, [{song:{arrowSkin:'../escape'}}]);
    if (unsafe.diagnostics.length == 0 || FileSystem.exists('assets/imported_mods/escape.png')) throw 'unsafe';
    put('archive/assets/shared/images/noteSkins/NOTE_assets.png', 'archive-default-png');
    put('archive/assets/shared/images/noteSkins/NOTE_assets.xml', 'archive-default-xml');
    put('archive/assets/shared/images/pixelUI/noteSkins/NOTE_assets.png', 'archive-pixel');
    put('archive/assets/shared/images/pixelUI/noteSkins/NOTE_assetsENDS.png', 'archive-ends');
    FileSystem.createDirectory('archive/assets/base_game');
    var archive = PsychSkinImportAssets.copy('archive/assets/base_game',
      'assets/imported_mods/archive', [{song:{arrowSkin:''}}]);
    if (archive.copied != 4 || archive.failed != 0) throw 'sibling shared copy';
    if (File.getContent('assets/imported_mods/archive/shared/images/noteSkins/NOTE_assets.png')
      != 'archive-default-png') throw 'sibling sheet ownership';
    if (File.getContent('assets/imported_mods/archive/shared/images/pixelUI/noteSkins/NOTE_assetsENDS.png')
      != 'archive-ends') throw 'sibling pixel ownership';
    for (diagnostic in archive.diagnostics)
      if (diagnostic.indexOf('sheet not found') >= 0) throw 'false missing sibling diagnostic';
  }
}
''', newline='\n')
            command = [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                       "-cp", str(fixture), "-main", "SkinImportFixture", "--interp"]
            result = subprocess.run(command, cwd=fixture, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
