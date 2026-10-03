from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]


def extract_method(source, signature):
    start = source.index(signature)
    brace = source.index('{', start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f'unterminated method: {signature}')


class DemoHealthTest(unittest.TestCase):
    def test_successful_player_notes_heal_with_sustain_scaling(self):
        s=(ROOT/'source/PlayState.hx').read_text()
        method=extract_method(s, '\tfunction applyDemoHealth(')
        code='''class Note {
 public var mustPress=true;public var isSustainNote=false;public var safe=true;public var gain=0.04;
 public function new(){}public function canAutoHit()return safe;public function getHealth(r:String)return gain;
}
class Test {var demoMode=true;var health=1.;public function new(){}
''' + method + '''
 static function main(){var t=new Test();var n=new Note();
 t.applyDemoHealth(n);if(Math.abs(t.health-1.04)>0.00001)throw 'Tap did not heal';
 n.isSustainNote=true;t.applyDemoHealth(n);if(Math.abs(t.health-1.048)>0.00001)throw 'Wrong sustain healing';
 n.safe=false;t.applyDemoHealth(n);if(Math.abs(t.health-1.048)>0.00001)throw 'Hazard healed';
 n.safe=true;n.mustPress=false;t.applyDemoHealth(n);if(Math.abs(t.health-1.048)>0.00001)throw 'Opponent healed player';
 n.mustPress=true;t.demoMode=false;t.applyDemoHealth(n);if(Math.abs(t.health-1.048)>0.00001)throw 'Changed ordinary autoplay';
 t.demoMode=true;t.health=1.999;t.applyDemoHealth(n);if(t.health!=2)throw 'Health overflow';
 }
}'''
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'Test.hx').write_text(code, newline='\n')
            p=subprocess.run([*HAXE_COMMAND,'-cp',d,'-main','Test','--interp'],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
