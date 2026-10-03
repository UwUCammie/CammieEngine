from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
class NightmareVisionSustainLayoutTest(unittest.TestCase):
 def test_source_rounding_head_time_and_frame_independence(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   Path(folder,'Main.hx').write_text('class Main {\n static function main() {\n  {\n   if (NightmareVisionSustainLayout.segmentCount(62.4,125)!=0) throw "sub-half-step";\n   if (NightmareVisionSustainLayout.segmentCount(62.5,125)!=2) throw "half-step rounding";\n   if (NightmareVisionSustainLayout.segmentCount(500,125)!=5) throw "terminal piece";\n   if (NightmareVisionSustainLayout.segmentCount(0,125)!=0) throw "empty hold";\n   if (NightmareVisionSustainLayout.segmentTime(1000,0,125)!=1000) throw "head anchor";\n   if (NightmareVisionSustainLayout.segmentTime(1000,4,125)!=1500) throw "endpoint";\n   if (NightmareVisionSustainLayout.segmentCount(500,15000/150)!=6) throw "changed section tempo";\n  }\n }\n}', newline='\n')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',folder,'-main','Main','--interp'],capture_output=True,text=True)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
