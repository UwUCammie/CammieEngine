"""Raw historical Set Property paths and tag precedence against the pinned source."""
from pathlib import Path
import re,subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from test_source_event_preparation import extract_method
ROOT=Path(__file__).resolve().parents[2];REV='7f96eb3b5a60352413229bf134bd348b79ad5fe6'
class HistoricalPropertyEventTest(unittest.TestCase):
 def test_paths_values_root_selection_and_failure_order(self):
  def source(path):return subprocess.check_output(['git','-C',str(ROOT.parent/'fnf_sources/NightmareVision'),'show',REV+':'+path],text=True)
  lua=source('source/meta/data/scripts/FunkinLua.hx');upstream=source('source/meta/states/PlayState.hx');play=(ROOT/'source/PlayState.hx').read_text()
  helpers='\n'.join('public static '+extract_method(lua,'function '+name+'(') for name in ['getPropertyLoopThingWhatever','getObjectDirectly','getVarInArray'])
  reference_lookup=extract_method(upstream,'function getLuaObject(').replace('getLuaObject','sourceLuaObject').replace(':FlxSprite',':Dynamic')
  event=extract_method(upstream,'function triggerEventNote(')
  cases=re.split(r'(?=^\t\t\tcase )',event,flags=re.M)
  case=next(c for c in cases if c.startswith("\t\t\tcase 'Set Property':"))
  case=case.split('\n\t\t}',1)[0]
  reference='function sourceEvent(value1:String,value2:String){switch("Set Property"){'+case+'}notifications++;}'
  actual=extract_method(play,'function historicalSetProperty(')
  lookup=extract_method(play,'public function getLuaObject(')
  host=r'''import Type.ValueType;
class GameOverSubstate {public static var instance:Dynamic;}
class FunkinLua {
 public static function getInstance():Dynamic return PlayState.instance.isDead?GameOverSubstate.instance:PlayState.instance;
 __HELPERS__
}
class Probe {
 public var value:Dynamic='old';public var items:Array<Dynamic>=[{value:'item'},[{value:'nested'}]];
 public var child(get,never):Dynamic;var s:PlayState;public var kid:Dynamic={value:'child'};
 public function new(s:PlayState)this.s=s;
 function get_child():Dynamic {s.events.push('child');if(s.mode==1)throw 'getter';if(s.mode==2)s.probe=new Probe(s);if(s.mode==3)s.notifications++;return kid;}
}
class PlayState {
 public static var instance:PlayState;public var isDead:Bool;public var nightmareVisionLegacyFieldCameras=true;public var actual:Bool;public var mode:Int;
 public var modchartObjects:Map<String,Dynamic>=[];public var modchartSprites:Map<String,Dynamic>=[];public var modchartTexts:Map<String,Dynamic>=[];
 public var notifications=0;public var events:Array<String>=[];public var probe:Probe;public var original:Probe;public var stringMap:Map<String,Dynamic>=[];public var intMap:Map<Int,Dynamic>=[];
 public var raw:Dynamic=12;public var other:Dynamic;
 public function new(actual:Bool,mode:Int,dead:Bool){this.actual=actual;this.mode=mode;isDead=dead;instance=this;probe=new Probe(this);original=probe;
  stringMap=['a'=>{value:'map'}];intMap=[1=>{value:'int'}];modchartObjects=['shared'=>{value:'object'},'nil'=>null];modchartSprites=['shared'=>{value:'sprite'},'nil'=>{value:'nilSprite'}];modchartTexts=['shared'=>{value:'text'},'textOnly'=>{value:'textOnly'}];
  other={probe:new Probe(this),raw:'dead',stringMap:['a'=>{value:'deadMap'}]};GameOverSubstate.instance=other;
 }
 function compatFindObject(tag:String):Dynamic return null;
 function historicalReadProperty(t:Dynamic,k:String):Dynamic return Reflect.getProperty(t,k);
 function historicalWriteProperty(t:Dynamic,k:String,v:Dynamic):Void Reflect.setProperty(t,k,v);
 public function dispatch(path:String,value:String):Void {if(actual){historicalSetProperty(path,value);notifications++;}else sourceEvent(path,value);}
 public function run(path:String,value:String):String {var error=false;try dispatch(path,value)catch(_:Dynamic)error=true;
  var result:Array<Dynamic>=[error,notifications,raw,Std.isOfType(raw,String),probe.value,original.value,original.kid.value,probe.kid.value,original.items[0].value,original.items[1][0].value,other.probe.value,other.probe.kid.value,other.raw,stringMap.get('a').value,intMap.get(1).value,modchartObjects.get('shared').value,modchartSprites.get('shared').value,modchartTexts.get('shared').value,modchartTexts.get('textOnly').value,events.join('|')];return result.join(';');}
 __METHODS__
}
class Main {static function main(){var count=0;
 var paths:Array<String>=[null,'','raw',' Raw','raw ','probe.value','Probe.value','probe.child.value','probe.items[0].value','probe.items[1][0].value','probe.items[0]','probe.items[bad].value','probe..value','.value','missing.value','stringMap.a.value','intMap.1.value','shared.value','textOnly.value','nil.value','modchartTexts.shared.value','modchartObjects.shared.value'];
 for(dead in [false,true])for(mode in 0...4)for(path in paths)for(value in [null,'','0','false','1.25','FFAABB','raw string']){
  var expected=new PlayState(false,mode,dead).run(path,value);var actual=new PlayState(true,mode,dead).run(path,value);
  if(expected!=actual)throw dead+':'+mode+':'+path+':'+value+'\n'+expected+'\n'+actual;count++;
 }
 for(actual in [false,true]) {var s=new PlayState(actual,0,false);if(s.getLuaObject('shared')!=s.modchartObjects.get('shared')||s.getLuaObject('textOnly',false)!=null||s.getLuaObject('textOnly')!=s.modchartTexts.get('textOnly')||s.getLuaObject('nil')!=null)throw 'lookup precedence';}
 trace(count+' property path/value cases');
 }}'''.replace('__HELPERS__',helpers).replace('__METHODS__',actual+'\n'+lookup+'\n'+reference_lookup+'\n'+reference)
  # Both extracted lookup paths use the same source tag maps; selection happens at the public boundary.
  host=host.replace('if (!nightmareVisionLegacyFieldCameras) return compatFindObject(tag);','if (!actual) return sourceLuaObject(tag,text);')
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder);(work/'Main.hx').write_text(host);(work/'SourceScriptReflection.hx').write_text((ROOT/'source/SourceScriptReflection.hx').read_text())
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
