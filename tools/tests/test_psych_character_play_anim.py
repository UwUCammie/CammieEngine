"""Legacy Psych character animation callback preserves upstream role routing."""
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[2]

class PsychCharacterPlayAnimTest(unittest.TestCase):
    def test_roles_missing_animation_and_optional_girlfriend(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        start = source.index('function compatCharacterPlayAnim(')
        end = source.index('\n\tfunction compatObjectPlayAnimation', start)
        method = source[start:end]
        self.assertIn("interp.variables.set('characterPlayAnim', compatCharacterPlayAnim)", source)
        fixture = """
class Character {
 public var plays=0;public var forced=false;
 public function new() {}
 public function hasAnimation(name:String):Bool return name=='idle';
 public function playAnim(name:String, force:Bool) {plays++;forced=force;}
}
class Main {
 var boyfriend=new Character();var dad=new Character();var gf=new Character();
 function new() {}
 METHOD
 static function main() {
  var s=new Main();
  s.compatCharacterPlayAnim('DAD','idle',true);
  s.compatCharacterPlayAnim('girlfriend','idle');
  s.compatCharacterPlayAnim('boyfriend','idle');
  s.compatCharacterPlayAnim('unknown','idle');
  s.compatCharacterPlayAnim('dad','missing',true);
  if(s.dad.plays!=1||!s.dad.forced||s.gf.plays!=1||s.gf.forced||s.boyfriend.plays!=2)
   throw 'legacy role or force semantics differ from Psych';
  s.gf=null;s.compatCharacterPlayAnim('gf','idle');
 }
}
""".replace('METHOD',method)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            (Path(folder)/'Main.hx').write_text(fixture)
            result=subprocess.run([str(ROOT/'.tools/haxe/haxe'),'-cp',folder,'--main','Main','--interp'],
                                  cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
