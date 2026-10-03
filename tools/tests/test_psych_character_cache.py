from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PsychCharacterCacheTest(unittest.TestCase):
    def test_nightmare_vision_bank_reuses_actors_and_transfers_alpha(self):
        fixture = r'''class FakeCharacter {
 public var requestedCharacter:String;
 public var alpha:Float;
 public function new(name:String, alpha:Float=1) {
  requestedCharacter=name; this.alpha=alpha;
 }
}
class Main {
 static function check(value:Bool,message:String):Void if(!value) throw message;
 static function main():Void {
  var initial=new FakeCharacter('bf',0.72);
  var constructions=0;
  var activations=0;
  var bank=new NightmareVisionCharacterBank(initial,function(name:String):Dynamic {
   constructions++; return new FakeCharacter(name);
  },function(old:Dynamic,next:Dynamic):Void activations++);
  check(bank.map.get('bf')==initial,'initial actor is cached by source identity');
  var dusk=bank.addToList('dusk');
  check(dusk==bank.addToList('dusk') && constructions==1,'pre-added actor is reused');
  check(dusk.alpha==0.00001,'new actor uses Psych hidden alpha');
  check(bank.change('dusk')==dusk,'cached actor becomes current');
  check(initial.alpha==0.0001 && dusk.alpha==0.72,'change transfers alpha and hides old actor');
  check(activations==1,'activation callback runs after a real change');
  check(bank.change('dusk')==dusk && activations==1,'same identity is a no-op');
  check(bank.change('bf')==initial,'switching back reuses the initial actor');
  check(dusk.alpha==0.0001 && initial.alpha==0.72 && activations==2,
   'cached actor alpha is transferred back on the next change');
  bank.release();
  check(bank.map.iterator().hasNext()==false && bank.parent==null,'release drops cache references');

  // Psych keys by resolved curCharacter. The shared cache accepts the identity
  // accessor explicitly, while the NMV facade uses requestedCharacter.
  var psychInitial:Dynamic={curCharacter:'bf',alpha:0.5};
  var psych=new PsychCharacterCache<Dynamic>(psychInitial,
   function(actor:Dynamic):String return actor.curCharacter,
   function(name:String):Dynamic return {curCharacter:name,alpha:1},
   function(old:Dynamic,next:Dynamic):Void {});
  check(psych.map.get('bf')==psychInitial,'Psych identity accessor controls cache keys');
  check(psych.addToList('dad').curCharacter=='dad' && psych.map.exists('dad'),
   'new Psych actor is cached under resolved character identity');
  Sys.println('psych-character-cache-ok');
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = Path(folder)
            (work / 'Main.hx').write_text(fixture, newline='\n')
            shutil.copy2(ROOT / 'source/PsychCharacterCache.hx', work / 'PsychCharacterCache.hx')
            shutil.copy2(ROOT / 'source/NightmareVisionCharacterBank.hx', work / 'NightmareVisionCharacterBank.hx')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(work), '--run', 'Main'],
                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('psych-character-cache-ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
