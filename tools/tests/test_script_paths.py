from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ScriptPathTest(unittest.TestCase):
    def test_cutscene_script_without_asset_folder(self):
        fixtures = [
            ROOT / 'assets/images/custom_ui/ui_layouts/postal.hscript',
            ROOT / 'assets/images/custom_cutscenes/video.hscript',
        ]
        if not all(path.is_file() for path in fixtures):
            self.skipTest('mounted script-path fixtures unavailable: ' + ', '.join(str(path) for path in fixtures))
        source = (ROOT / 'source/FNFAssets.hx').read_text()
        start = source.index('\tstatic public function getHscript(')
        method = source[start:source.index('\n\t}', start) + 3]
        text_start = source.index('    public static function getText(')
        text_method = source[text_start:source.index('\n    }', text_start) + 6]
        fixture = '''import haxe.io.Path;
import sys.io.File;
class Assets {public static function exists(p:String)return false;public static function getPath(p:String):String return null;public static function getText(p:String):String return null;}
class CoolUtil {public static var HSCRIPT_EXT=["hscript"];}
class AssetType {public static var TEXT=0;}
class ScriptPathTest {
 static function getAmbigAsset(paths:Array<String>,exts:Array<String>,type:Int):String {
  for(p in paths) for(e in exts) if(sys.FileSystem.exists(p+"."+e)) return sys.io.File.getContent(p+"."+e);
  return null;
 }
''' + method + text_method + '''
 static function isInScope(p:String)return true;
 static function main(){
  var layout="assets/images/custom_ui/ui_layouts/postal/../postal.hscript";
  if(getText(layout)!=sys.io.File.getContent("assets/images/custom_ui/ui_layouts/postal.hscript"))throw "Layout path must normalize";
  var path="assets/images/custom_cutscenes/video/../video";
  if(getHscript(path)==null)throw "Cutscene script must load without its optional asset directory";
  if(getHscript(path)!=getHscript("assets/images/custom_cutscenes/video"))throw "Paths must resolve identically";
 }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'ScriptPathTest.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'ScriptPathTest', '--interp'], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
