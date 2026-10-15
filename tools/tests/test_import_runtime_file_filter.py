"""Bundled programs and runtimes in a mod's asset folders are never copied."""
from haxe_test_support import HAXE_COMMAND

from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class ImportRuntimeFileFilterTest(unittest.TestCase):
    def test_programs_and_runtimes_are_skipped_and_assets_are_kept(self):
        fixture = r'''class FilterFixture {
  static function check(value:Bool, message:String) if (!value) throw message;
  static function main() {
    for (path in ['tool/tool.exe', 'tool\\Runtime.DLL', 'lib/os.py', 'lib/os.pyc', 'lib/_ssl.pyd',
        'run.bat', 'setup.ps1', 'native/lime.ndll', 'src/main.cpp', 'include/api.h'])
      check(ImportRuntimeFileFilter.neverLoaded(path), 'program file kept: ' + path);
    // Anything a script or the engine can read stays, including models and
    // arbitrary text that a mod reads through generic file APIs.
    for (path in ['images/a.png', 'music/a.ogg', 'videos/a.mp4', 'data/a.json', 'scripts/a.hx',
        'scripts/a.lua', 'shaders/a.frag', 'models/a.obj', 'notes/readme.txt', 'LICENSE', '.hidden',
        'odd.', 'fonts/a.ttf'])
      check(!ImportRuntimeFileFilter.neverLoaded(path), 'loadable file skipped: ' + path);
    check(!ImportRuntimeFileFilter.neverLoaded(null), 'null path');

    // A compiled asset list that names native video plugins publishes only
    // the files the engine can load.
    var files:Array<Dynamic> = [{sourcePath:'game/plugins/libvlc_plugin.dll', destinationPath:'out/plugins/libvlc_plugin.dll'},
      {sourcePath:'game/assets/images/a.png', destinationPath:'out/images/a.png'}];
    var copied:Array<String> = [];
    var plan:Dynamic = {failed:false, cancelled:false, files:files, identityPublication:null};
    SourceMappedAssetPublisher.publish(cast plan, function(source:String, destination:String) copied.push(destination));
    check(copied.join(',') == 'out/images/a.png', 'mapped publication copied: ' + copied.join(','));
    copied = [];
    var view:Dynamic = {failed:false, cancelled:false, files:files};
    SourceMappedAssetPublisher.publishView(cast view, function(source:String, destination:String) copied.push(destination));
    check(copied.join(',') == 'out/images/a.png', 'mapped view copied: ' + copied.join(','));
  }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "FilterFixture.hx").write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"),
                                     "--run", "FilterFixture"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
