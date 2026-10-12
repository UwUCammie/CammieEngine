"""Psych stage creation precedes UI/note groups, even with HUD-camera props."""
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

class PsychStageHudOrderTest(unittest.TestCase):
    def test_stage_creation_order_preserves_notes_and_later_overlays(self):
        source = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        start = source.index('\tfunction layerPsychStageBeforeHud(')
        end = source.index('\n\tfunction nativeStageHudMembers(', start)
        helper = source[start:end].replace('FlxBasic', 'Item')
        own_start = source.index('\tfunction registerPsychStageCreatedMembers(')
        own_end = source.index('\n\tfunction registerStageSprites(', own_start)
        ownership = source[own_start:own_end].replace('FlxBasic', 'Item')
        self.assertIn("if (usehaxe == 'stage' && interp.variables.get('__psychScoreGlobals') == true)\n\t\t\t\tlayerPsychStageBeforeHud(stageSprites);", source)
        fixture = r'''class Item {public var name:String; public function new(n:String) name=n;}
class StageOrderProbe {
 var members:Array<Item>=[]; var hud:Array<Item>=[]; var owned:Array<Item>=[];
 function registerStageSprite(item:Item):Void if(owned.indexOf(item)<0)owned.push(item);
 function new() {}
 function nativeStageHudMembers():Array<Item> return hud;
 function remove(item:Item,splice:Bool):Void members.remove(item);
 function insert(index:Int,item:Item):Void members.insert(index,item);
''' + ownership + helper + r'''
 static function main() {
  var p=new StageOrderProbe();
  var actor=new Item("actor"); var back=new Item("back");
  var receptor=new Item("receptor"); var notes=new Item("notes");
  var red=new Item("red"); var split=new Item("split");
  var untouched=new Item("untouched");
  p.hud=[null,receptor,notes];
  p.members=[back,actor,receptor,notes,red,untouched,split];
  p.registerPsychStageCreatedMembers([back,actor,receptor,notes,untouched]);
  if(p.owned.length!=2 || p.owned[0]!=red || p.owned[1]!=split)throw "Lua tag-created stage sprites lost ownership";
  p.layerPsychStageBeforeHud(p.owned);
  var names=[for (m in p.members) m.name].join(",");
  if(names!="back,actor,red,split,receptor,notes,untouched") throw names;
  // Song onCreatePost and runtime setObjectOrder may intentionally cover notes.
  p.members.remove(red); p.members.push(red);
  if(p.members[p.members.length-1]!=red) throw "explicit order was clamped";
  var empty=new StageOrderProbe(); empty.members=[red,split];
  empty.layerPsychStageBeforeHud([red,split]);
  if(empty.members[0]!=red || empty.members[1]!=split) throw "missing HUD moved props";
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'StageOrderProbe.hx').write_text(fixture, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'StageOrderProbe', '--interp'], cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

if __name__ == '__main__':
    unittest.main()
