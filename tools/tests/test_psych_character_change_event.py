"""Keep imported character events on the source cached ownership path."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[2]
class CharacterChangeEventTest(unittest.TestCase):
    def test_event_and_script_changes_reuse_the_same_live_bank(self):
        source = (ROOT/'source/PlayState.hx').read_text()
        helper = source[source.index('function changeNightmareVisionCharacterEvent'):source.index('function switchCharacter')]
        fixture = r'''
using StringTools;
class Character {
 public var curCharacter:String;public var alpha:Float=1;public var danceEvery:Int=2;
 public var animation:Dynamic = {curAnim:{name:'idle',curFrame:0}};
 public function new(name:String)curCharacter=name;
 public function playAnim(name:String,force:Bool)animation.curAnim={name:name,curFrame:0};
}
class Main {
 var boyfriend=new Character('player');var dad=new Character('opponent');var gf=new Character('support');var gfSpeed=2;
 var banks:Map<Int,PsychCharacterCache<Dynamic>>=new Map();
 function new(){}
 function nightmareVisionCharacterBank(type:Int):PsychCharacterCache<Dynamic> {
  if(banks.exists(type))return banks[type];
  var initial=type==0?boyfriend:type==1?dad:gf;
  var bank=new PsychCharacterCache<Dynamic>(initial,function(actor)return actor.curCharacter,
   function(name)return new Character(name),function(old,next){
    if(type==0)boyfriend=next;else if(type==1)dad=next;else gf=next;
   });banks[type]=bank;return bank;
 }
 HELPER
 static function check(ok:Bool,message:String)if(!ok)throw message;
 static function main(){
  var host=new Main();var old=host.dad;old.alpha=.4;
  var bank=host.nightmareVisionCharacterBank(1);
  bank.addToList('opponent-variant');
  host.changeNightmareVisionCharacterEvent('dad','opponent-variant');
  check(old.alpha==.0001&&host.dad.alpha==.4,'event did not hide old/cache alpha');
  var variant=host.dad;variant.animation.curAnim={name:'singUP',curFrame:3};
  bank.change('opponent');
  check(host.dad==old&&variant.alpha==.0001,'script path lost event cache');
  host.dad.animation.curAnim={name:'singLEFT',curFrame:4};
  host.changeNightmareVisionCharacterEvent('1','opponent-variant');
  check(host.dad==variant&&host.dad.animation.curAnim.name=='singLEFT'&&host.dad.animation.curAnim.curFrame==4,'related identity frame carry');
  host.changeNightmareVisionCharacterEvent('gf','support-variant');
  check(host.gf.danceEvery==4,'source GF dance multiplier');
 }
}
'''.replace('HELPER',helper)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            Path(folder,'Main.hx').write_text(fixture, newline='\n')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',folder,'--main','Main','--interp'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_source_role_aliases_and_native_event_cache_boundary(self):
        haxe = ROOT / '.tools/haxe/haxe'
        if not haxe.exists():
            self.skipTest('portable Haxe unavailable')
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            Path(folder, 'Main.hx').write_text("""
class Main {
 static function main() {
  var names:Array<String> = [null,'','bf','boyfriend','0','1','dad','opponent','2','gf','girlfriend','3'];
  var expected = [0,0,0,0,0,1,1,1,2,2,2,3];
  for(i in 0...names.length) if(PsychCharacterChangeEvent.role(names[i]) != expected[i]) throw 'role ' + i;
 }
}
""", newline='\n')
            result = subprocess.run([str(haxe),'-cp',str(ROOT/'source'),'-cp',folder,'--main','Main','--interp'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        source = (ROOT/'source/PlayState.hx').read_text()
        event = source[source.index("case 'Change Character':"):source.index("case 'Change Stage':")]
        self.assertLess(event.index('changeNightmareVisionCharacterEvent'), event.index('switchCharacter'))
        helper = source[source.index('function changeNightmareVisionCharacterEvent'):source.index('function switchCharacter')]
        self.assertIn('nightmareVisionCharacterBank(type).change(name)',helper)
        self.assertNotIn('.destroy()',helper)
        self.assertIn('anim.curFrame',helper)
