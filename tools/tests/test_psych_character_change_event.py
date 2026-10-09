"""Keep imported character events on the source cached ownership path."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[2]

def extract_block(source, marker):
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"Unclosed block: {marker}")


class CharacterChangeEventTest(unittest.TestCase):
    def test_event_and_script_changes_reuse_the_same_live_group(self):
        source = (ROOT/'source/PlayState.hx').read_text()
        helper = source[source.index('function changeNightmareVisionCharacterEvent'):source.index('function switchCharacter')]
        publish = extract_block(source, 'function publishNightmareVisionCharacter(')
        fixture = r'''
using StringTools;
class Character {
 public var curCharacter:String;public var alpha:Float=1;public var danceEveryNumBeats:Int=2;
 public var animation:Dynamic = {curAnim:{name:'idle',curFrame:0}};
 public function new(name:String)curCharacter=name;
 public function playAnim(name:String,force:Bool)animation.curAnim={name:name,curFrame:0};
}
class GroupFixture {
 public var parent:Character;public var map:Map<String,Character>=[];
 public function new(actor:Character){parent=actor;map.set(actor.curCharacter,actor);}
 public function addToList(name:String):Character {var old=map.get(name);if(old!=null)return old;var actor=new Character(name);actor.alpha=.00001;map.set(name,actor);return actor;}
 public function change(name:String):Character {if(parent.curCharacter!=name){var next=addToList(name);var alpha=parent.alpha;parent.alpha=.0001;parent=next;parent.alpha=alpha;}return parent;}
}
class Main {
 var nightmareVisionLegacyFieldCameras=false;
 var boyfriend=new Character('player');var dad=new Character('opponent');var gf=new Character('support');var gfSpeed=2;
 var groups:Map<Int,GroupFixture>=new Map();var hud=0;var holdClaimUpdates=0;
 function new(){}
 function nightmareVisionCharacterGroup(type:Int):GroupFixture {
  if(groups.exists(type))return groups[type];var group=new GroupFixture(type==0?boyfriend:type==1?dad:gf);groups[type]=group;return group;
 }
 function refreshCharacterHUD():Void hud++;
 function updateNightmareVisionHoldClaims():Void holdClaimUpdates++;
 PUBLISH
 HELPER
 static function check(ok:Bool,message:String)if(!ok)throw message;
 static function main(){
  var host=new Main();var old=host.dad;old.alpha=.4;
  var bank=host.nightmareVisionCharacterGroup(1);
  bank.addToList('opponent-variant');
  host.changeNightmareVisionCharacterEvent('dad','opponent-variant');
  check(old.alpha==.0001&&host.dad.alpha==.4,'event did not hide old/cache alpha');
  check(host.holdClaimUpdates==1,'published character change must refresh hold claims');
  var variant=host.dad;variant.animation.curAnim={name:'singUP',curFrame:3};
  bank.change('opponent');
  check(host.dad==variant&&bank.parent==old,'direct group change must not publish game role');
  host.publishNightmareVisionCharacter('opponent',1);
  check(host.dad==old&&variant.alpha==.0001,'script path lost event cache');
  check(host.holdClaimUpdates==2,'direct source publication must refresh hold claims');
  host.dad.animation.curAnim={name:'singLEFT',curFrame:4};
  host.changeNightmareVisionCharacterEvent('1','opponent-variant');
  check(host.dad==variant&&host.dad.animation.curAnim.name=='singLEFT'&&host.dad.animation.curAnim.curFrame==4,'related identity frame carry');
  check(host.holdClaimUpdates==3,'related event publication must refresh hold claims');
  host.changeNightmareVisionCharacterEvent('gf','support-variant');
  check(host.gf.danceEveryNumBeats==4,'source GF dance multiplier');
  check(host.holdClaimUpdates==4,'GF publication must refresh hold claims');
 }
}
'''.replace('HELPER',helper).replace('PUBLISH',publish)
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
        native_dispatch = extract_block(source, 'function fireNativeSongEvent(e:Dynamic)')
        event_start = native_dispatch.index("case 'Change Character':")
        event_end = native_dispatch.index("case 'Change Stage':", event_start)
        event = native_dispatch[event_start:event_end]
        self.assertLess(event.index('changeNightmareVisionCharacterEvent'), event.index('switchCharacter'))
        helper = source[source.index('function changeNightmareVisionCharacterEvent'):source.index('function switchCharacter')]
        self.assertIn('publishNightmareVisionCharacter(name, type)',helper)
        self.assertIn('nightmareVisionCharacterGroup(type).change(name)', extract_block(source, 'function publishNightmareVisionCharacter('))
        self.assertNotIn('.destroy()',helper)
        self.assertIn('anim.curFrame',helper)
