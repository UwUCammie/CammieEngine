from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
ROOT=Path(__file__).resolve().parents[2]
class ScriptOriginTest(unittest.TestCase):
 def test_extension_precedence_and_missing_paths(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder)
   (root/'Main.hx').write_text("""class Main {
    static function main() {
     var files=['assets/data/example/modchart.hscript','assets/data/example/modchart.lua','assets/data/example/ui.hxs','assets/data/example/legacy.lua'];
     function resolve(path) return CompatScriptOrigin.resolve(path,['hscript','hxs'],function(p)return files.indexOf(p)>=0);
     if(resolve('assets/data/example/modchart')!=files[0]) throw 'native precedence';
     if(resolve(files[1])!=files[1]) throw 'explicit source';
     if(resolve('assets/data/example/ui')!=files[2]) throw 'hxs origin';
     if(resolve('assets/data/example/legacy.hscript')!=files[3]) throw 'Lua fallback';
     if(resolve('assets/data/example/missing')!='assets/data/example/missing') throw 'fabricated origin';
    }
   }""")
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',folder,'--run','Main'],capture_output=True,text=True)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
