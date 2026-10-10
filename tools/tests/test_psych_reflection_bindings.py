"""Exercise the registered Psych reflection API with a minimal host boundary."""
from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HOST = r'''
enum abstract DisplayLayer(Int) from Int to Int { var BEHIND_NONE = 0; var BEHIND_ALL = 7; }
class PlayState {
 public static inline var BEHIND_NONE = 0;
 public static inline var BEHIND_ALL = 7;
 public var psychScriptVariables:Map<String,Dynamic> = [];
 public var nativeMember:Dynamic;
 public var objects:Map<String,Dynamic> = [];
 public var added:Dynamic;
 public var layer:Int;
 public function new() {}
 public function compatPathTokens(path:String):Array<String> return path.split('.');
 public function compatPathIndex(key:String):String return key;
 public function compatPropertyRoot(name:String):Dynamic return objects.get(name);
 public function compatResolveClass(name:Dynamic):Dynamic return name == 'Item' ? Main.Item : null;
 public function compatReadPathPart(object:Dynamic,key:String):Dynamic {
  if(object==null)return null;
  if(StringTools.startsWith(key,'['))return (cast object:Array<Dynamic>)[Std.parseInt(key.substr(1,key.length-2))];
  return Reflect.getProperty(object,key);
 }
 public function compatWritePathPart(object:Dynamic,key:String,value:Dynamic):Bool {
  if(object==null)return false; Reflect.setProperty(object,key,value); return true;
 }
 public function compatSetProperty(path:Dynamic,value:Dynamic):Void psychScriptVariables.set(path,value);
 public function compatGroupMember(group:Dynamic,index:Dynamic):Dynamic return group=='strumLineNotes' ? nativeMember : null;
 public function addHscriptSprite(object:Dynamic,layer:Int):Void {added=object;this.layer=layer;}
}
'''
MAIN = r'''
class Item extends flixel.FlxBasic {
 public var amount:Int;
 public function new(amount:Int=1) {super();this.amount=amount;}
 public function add(value:Int):Int return amount += value;
}
class Main {
 static function check(value:Bool,message:String):Void if(!value)throw message;
 static function invoke(interp:hscript.Interp,name:String,args:Array<Dynamic>):Dynamic
  return Reflect.callMethod(null,interp.variables.get(name),args);
 static function main():Void {
  var host=new PlayState();
  var interp=new hscript.Interp();
  var legacyReads=0; var legacyWrites=0;
  interp.variables.set('getProperty',function(path:Dynamic):Dynamic {legacyReads++;return 77;});
  interp.variables.set('setProperty',function(path:Dynamic,value:Dynamic):Void legacyWrites++);
  interp.variables.set('getPropertyFromClass',function(cls:Dynamic,path:Dynamic):Dynamic return 88);
  interp.variables.set('setPropertyFromClass',function(cls:Dynamic,path:Dynamic,value:Dynamic):Void {});
  new PsychReflectionBindings(host,interp).install();
  check(invoke(interp,'getProperty',['health',false])==77 && legacyReads==1,'retain legacy getter');
  check(invoke(interp,'setProperty',['health',2,false,false])==2 && legacyWrites==1,'setter return');
  var maps:Map<String,Dynamic>=['row'=>{value:false}];
  host.psychScriptVariables.set('map',maps);
  check(invoke(interp,'getProperty',['map.row.value',true])==false,'map traversal');
  invoke(interp,'setProperty',['map.row.value',12,true,false]);
  check(invoke(interp,'getProperty',['map.row.value',true])==12,'map write');
  check(invoke(interp,'createInstance',['  created.item  ','Item',[5]])==true,'create object');
  check(invoke(interp,'createInstance',['createditem','Item',[99]])==false,'preserve named object');
  check(invoke(interp,'callMethod',['createditem.add',[4]])==9,'instance method');
  var item=host.psychScriptVariables.get('createditem');
  host.nativeMember=item;
  check(invoke(interp,'getPropertyFromGroup',['strumLineNotes',0,'amount',false])==9,'native receptor alias');
  invoke(interp,'setPropertyFromGroup',['strumLineNotes',0,'amount',11,false,false]);
  check(item.amount==11,'live receptor alias setter');
  var sentinel=invoke(interp,'instanceArg',['createditem',null]);
  invoke(interp,'setProperty',['slot',sentinel,true,true]);
  check(host.psychScriptVariables.get('slot')==item,'instance argument resolves to same object');
  invoke(interp,'addInstance',['createditem',false]);
  check(host.added==item && host.layer==PlayState.BEHIND_ALL,'add object with actor ordering');
  var group:Array<Dynamic>=[]; host.psychScriptVariables.set('group',group);
  invoke(interp,'addToGroup',['group','createditem',-1]);
  check(group.length==1 && group[0]==item,'group API same instance');
  invoke(interp,'removeFromGroup',['group',0,null,false]);
  check(group.length==0,'group removal');
 }
}
'''

class PsychReflectionBindingsTest(unittest.TestCase):
    def test_registered_optional_arguments_and_instance_lifetime(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            root = Path(directory)
            (root / 'flixel').mkdir()
            (root / 'flixel/FlxBasic.hx').write_text('package flixel; class FlxBasic { public function new(){} public function destroy():Void{} }')
            # Native reflection mode; source classes have actual connected fixtures.
            host = HOST.replace(' public function new() {}', ' public var psychStageLibrary:String;public function selectedPsychSkinRoot():String return null;public function psychLuaNativeClassScope(p:Dynamic):SourceNativeClassScope return new SourceNativeClassScope(); public function new() {}', 1)
            (root / 'PsychOwnerPaths.hx').write_text('class PsychOwnerPaths {public static function create(r:String,?l:String):Dynamic return null;}')
            (root / 'SourceIrisBridge.hx').write_text('class SourceIrisBridge extends hscript.Interp {public var evaluator:Dynamic;}')
            # State-class registration is covered by the connected state registry probe.
            (root / 'PsychStateClassBindings.hx').write_text('class PsychStateClassBindings {public static function installScope(s:Dynamic):Void {} public static function install(i:Dynamic):Void {}}')
            (root / 'PlayState.hx').write_text(host)
            (root / 'Main.hx').write_text(MAIN)
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                                     '-cp', str(ROOT / '.haxelib/hscript/2,5,0'), '-cp', directory,
                                     '-main', 'Main', '--interp'], text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

if __name__ == '__main__':
    unittest.main()
