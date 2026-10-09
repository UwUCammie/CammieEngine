"""Native countdown must not override live source character dance decisions."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameCountdownDanceTest(unittest.TestCase):
    def test_countdown_dance_ownership(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        start = source.index('startTimer = new FlxTimer().start(', source.index('public function startCountdown()'))
        body = source[source.index('{', start) + 1:source.index('var introAssets:', start)]
        fixture = '''class Actor {
 public var codenameLiveDefinition:Dynamic=null;
 public var calls=0;
 public function new() {}
 public function dance():Void calls++;
}
class Main {
 var dad=new Actor(); var boyfriend=new Actor(); var gf=new Actor();
 var duoMode=false; var opponentPlayer=false;
 var nightmareVisionLegacyFieldCameras=false;var tmr={loopsLeft:3};var due=false;
 function girlfriendDanceDue(beat:Int):Bool {if(beat!=tmr.loopsLeft)throw 'countdown passed wrong beat';return due;}
 public function new() {}
 function countdown():Void {''' + body + '''}
 static function main() {
  var state=new Main();
  state.countdown();
  if(state.dad.calls!=1 || state.boyfriend.calls!=0 || state.gf.calls!=1)
   throw 'legacy countdown changed';
  state.opponentPlayer=true;state.countdown();
  if(state.dad.calls!=2 || state.boyfriend.calls!=1 || state.gf.calls!=2)
   throw 'opponent-control countdown changed';
  state.dad.codenameLiveDefinition={};state.boyfriend.codenameLiveDefinition={};state.gf.codenameLiveDefinition={};
  state.countdown();
  if(state.dad.calls!=2 || state.boyfriend.calls!=1 || state.gf.calls!=2)
   throw 'countdown bypassed source dance ownership';
  state.gf.codenameLiveDefinition=null;state.countdown();
  if(state.gf.calls!=3 || state.dad.calls!=2)
   throw 'mixed source/native actors must remain independent';
  state.nightmareVisionLegacyFieldCameras=true;state.countdown();if(state.gf.calls!=3)throw 'historical countdown ignored source gate';
  state.due=true;state.countdown();if(state.gf.calls!=4)throw 'historical countdown did not consume source gate';
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as work:
            (Path(work) / 'Main.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', work,
                                     '--run', 'Main'], cwd=ROOT, capture_output=True,
                                    text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
