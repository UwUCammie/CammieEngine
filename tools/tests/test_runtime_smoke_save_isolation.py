"""Native smoke saves use the pinned Flixel path rule in a private runtime tree."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP
from test_freeplay_random_difficulty import extract_method

ROOT = Path(__file__).resolve().parents[2]


class RuntimeSmokeSaveIsolationTest(unittest.TestCase):
    def test_opt_in_and_actual_flixel_save_path(self):
        save = (ROOT / '.haxelib/flixel/6,1,2/flixel/util/FlxSave.hx').read_text()
        path_method = extract_method(save, 'static function getPath(').replace(
            'static function getPath(', 'public static function getPath(', 1)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            folder = Path(directory)
            (folder / 'lime/system').mkdir(parents=True)
            (folder / 'lime/system/System.hx').write_text('''package lime.system;
class System {public static var __applicationStorageDirectory="original";
public static var applicationStorageDirectory(get,never):String;
static function get_applicationStorageDirectory():String return __applicationStorageDirectory;}''')
            (folder / 'RuntimeSmokeHarness.hx').write_text('''class RuntimeSmokeHarness {
public static var active=false; public static function enabled():Bool return active;}''')
            (folder / 'SavePath.hx').write_text('''class SavePath {
static function getDefaultLocalPath():String return "company";
''' + path_method + '\n}\n')
            (folder / 'Main.hx').write_text('''class Main {static function main() {
Sys.setCwd(Sys.args()[0]);
Sys.putEnv("CAMMIE_SMOKE_SAVE_ROOT","tmp/private-save");
RuntimeSmokeSaveIsolation.install();
if(lime.system.System.__applicationStorageDirectory!="original") throw "ordinary save changed";
RuntimeSmokeHarness.active=true;
for(invalid in ["../outside","tmp/../outside","tmp/C:/outside","C:/outside","tmp\\\\outside"]) {
 Sys.putEnv("CAMMIE_SMOKE_SAVE_ROOT",invalid);var rejected=false;
 try RuntimeSmokeSaveIsolation.install() catch(_:Dynamic) rejected=true;
 if(!rejected||lime.system.System.__applicationStorageDirectory!="original") throw "unsafe save root";
}
Sys.putEnv("CAMMIE_SMOKE_SAVE_ROOT","tmp/private-save");
RuntimeSmokeSaveIsolation.install();
var expected=haxe.io.Path.normalize(Sys.getCwd()+"/tmp/private-save/bulbyVR/save0.sol");
var actual=haxe.io.Path.normalize(SavePath.getPath("bulbyVR","save0"));
if(actual!=expected) throw "pinned Flixel save escaped: "+actual;
sys.FileSystem.createDirectory(haxe.io.Path.directory(actual));
sys.io.File.saveContent(actual,"private only");
if(!sys.FileSystem.exists(expected)) throw "private save not written";
Sys.println("private-smoke-saves-ok");
}}''')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                '-cp', directory, '--run', 'Main', directory], cwd=ROOT,
                capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('private-smoke-saves-ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
