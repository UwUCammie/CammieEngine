"""Execute shared map, instance and group semantics from donor script APIs."""
from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''
import haxe.ds.StringMap;
import haxe.ds.IntMap;
class Item {
 public var value:Int = 3;
 public var destroyed:Bool = false;
 public function new() {}
 public function increment(amount:Int):Int return value += amount;
 public function destroy():Void destroyed = true;
}
class Group {
 public var members:Array<Dynamic> = [];
 public function new() {}
 public function add(item:Dynamic):Dynamic { members.push(item); return item; }
 public function insert(index:Int, item:Dynamic):Dynamic { members.insert(index,item); return item; }
 public function remove(item:Dynamic, splice:Bool):Dynamic return members.remove(item) ? item : null;
}
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var strings = new StringMap<Dynamic>();
  strings.set('name', 42);
  var ints = new IntMap<Dynamic>(); ints.set(4, false);
  var read = function(o:Dynamic, k:String):Dynamic return Reflect.getProperty(o,k);
  var write = function(o:Dynamic, k:String, v:Dynamic):Bool { Reflect.setProperty(o,k,v); return true; };
  check(SourceScriptReflection.read(strings,'name',true,read)==42,'string map');
  check(SourceScriptReflection.read(ints,'4',true,read)==false,'integer map zero-like value');
  check(SourceScriptReflection.read(ints,'bad',true,read)==null,'invalid integer map key');
  check(SourceScriptReflection.write(strings,'name',false,true,write),'write map');
  check(strings.get('name')==false,'map setter value');
  var item = new Item();
  var references:Map<String,Dynamic> = ['item'=>item];
  var args:Array<Dynamic> = ['ordinary::string',[SourceScriptReflection.INSTANCE_PREFIX+'item'],7];
  var parsed:Array<Dynamic> = cast SourceScriptReflection.parseInstances(args,
   function(path,type) return references.get(path));
  check(parsed[0]=='ordinary::string' && parsed[1][0]==item && parsed[2]==7,'recursive sentinels');
  check(args[1][0]!=item,'argument input ownership');
  check(SourceScriptReflection.parseInstances('##OTHER::item',function(p,t) return item)=='##OTHER::item','wrong sentinel');
  var nested:Dynamic = {child:item};
  check(SourceScriptReflection.call(nested,['child','increment'],[2],read)==5,'nested receiver method');
  check(item.value==5,'method affected live instance');
  check(SourceScriptReflection.call(nested,['absent','increment'],[],read)==null,'missing receiver');
  var group = new Group();
  var second = new Item();
  check(SourceScriptReflection.addToGroup(group,item),'group add');
  check(SourceScriptReflection.addToGroup(group,second,0),'group insert');
  check(group.members[0]==second && group.members[1]==item,'insert order');
  check(SourceScriptReflection.removeFromGroup(group,0,null,false),'group remove without destroy');
  check(!second.destroyed && group.members.length==1,'preserve removed object');
  check(SourceScriptReflection.removeFromGroup(group,-1,item,true) && item.destroyed,'tagged group destroy');
  var array:Array<Dynamic> = [second];
  check(SourceScriptReflection.removeFromGroup(array,0,null,true) && !second.destroyed,'source indexed-array ownership');
  array.push(second);
  check(SourceScriptReflection.removeFromGroup(array,0,second,true) && second.destroyed,'source tagged-array destroy');
  check(!SourceScriptReflection.removeFromGroup(array,9,null,true),'missing index');
  check(ScriptCallbackResult.stopsGate(ScriptCallbackResult.STOP),'modern stop');
  check(ScriptCallbackResult.stopsGate(ScriptCallbackResult.STOP_ALL),'stop all gate');
  check(!ScriptCallbackResult.stopsGate(ScriptCallbackResult.STOP_LUA),'Lua dispatch stop is not gameplay gate');
  check(ScriptCallbackResult.stopsGate('Function_Stop') && ScriptCallbackResult.stopsGate(true),'legacy returns');
  check(ScriptCallbackResult.continues(ScriptCallbackResult.CONTINUE),'modern continue');
 }
}
'''

class SourceScriptReflectionTest(unittest.TestCase):
    def test_shared_live_object_operations(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            (Path(directory) / 'Main.hx').write_text(MAIN, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', directory,
                                     '-main', 'Main', '--interp'], text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

if __name__ == '__main__':
    unittest.main()
