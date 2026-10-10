"""Compare single/recursive instance parsing and raw lookup with pinned Psych."""
from pathlib import Path
import subprocess,tempfile,unittest,os,shutil
from haxe_test_support import HAXE_COMMAND,ROOT
from test_source_event_preparation import extract_method

class PsychInstanceArgumentsTest(unittest.TestCase):
 def test_source_parser_and_path_contract(self):
  donor=ROOT.parent/'fnf_sources/FNF-PsychEngine'
  def source(path):return subprocess.check_output(['git','-C',str(donor),'show','5c67ced49e5a98535298a6daa3f8f4ec79ac8399:'+path],text=True)
  reflection=source('source/psychlua/ReflectionFunctions.hx');utils=source('source/psychlua/LuaUtils.hx')
  methods='\n'.join('public static '+extract_method(reflection,'function '+name+'(') for name in ['parseSingleInstance','parseInstances','parseInstanceArray'])
  lookup='public static '+extract_method(utils,'function getVarInArray(')
  fixture=r'''using StringTools;
class MusicBeatState {
 public var item:Dynamic={value:"field",rows:[["field-row"]]};public var nullish:Dynamic={value:"fallback"};public var rows:Dynamic=[["state-row"]];
 public function new(){}public static function getVariables():Dynamic return Main.registry();
}
class PlayState {public static var instance:Dynamic;}
class FixtureClass {public static var item:Dynamic={value:"class",rows:[["class-row"]]};}
class LuaUtils {__LOOKUP__ public static function isMap(v:Dynamic):Bool return v.exists!=null&&v.keyValueIterator!=null;}
class Donor {static final instanceStr:Dynamic="##PSYCHLUA_STRINGTOOBJ";__METHODS__}
class Main {
 static var events:Array<String>;static var values:Map<String,Dynamic>;static var calls:Int;static var mode:Int;
 public static function registry():Dynamic {events.push("registry");calls++;if(mode==3&&calls==2)values.set("item",{value:"changed"});return values;}
 public static function resolve(name:String):Dynamic {events.push("class:"+name);return name=="FixtureClass"?FixtureClass:null;}
 public static function property(obj:Dynamic,key:String):Dynamic {events.push("property:"+key);return Reflect.getProperty(obj,key);}
 static function part(obj:Dynamic,key:String):Dynamic return SourceScriptReflection.readPsychInstancePart(obj,key,function(v)return Std.isOfType(v,MusicBeatState),registry,property);
 static function run(donor:Bool,input:Dynamic,recursive:Bool,m:Int):String {
  events=[];calls=0;mode=m;values=[];PlayState.instance=new MusicBeatState();
  if(m>0){values.set("item",m==2?null:{value:"variable",rows:[["variable-row"]]});values.set("rows",m==2?null:[["registry-row"]]);values.set("nullish",null);}
  var output:String;
  try {var value=donor?(recursive?Donor.parseInstances(input):Donor.parseSingleInstance(input)):(recursive?SourceScriptReflection.parsePsychInstances(input,function()return PlayState.instance,resolve,part):SourceScriptReflection.parsePsychSingleInstance(input,function()return PlayState.instance,resolve,part));output=Std.string(value);}
  catch(e:Dynamic){output="error";}
  return events.join("|")+"=>"+output;
 }
 static function main(){
  var prefix="##PSYCHLUA_STRINGTOOBJ::";
  var inputs:Array<Dynamic>=[null,0,42,true,false,"short","plain::short","ordinary text long enough::item.value",prefix+"item.value",prefix+" item . value ",prefix+"item.rows[0][0]",prefix+"rows[0][0]",prefix+"nullish.value",prefix+"item.rows[0][0]::FixtureClass",prefix+"item.value::FixtureClass",prefix+"item.value::missing",prefix+"missing.child",prefix+"rows['0']",prefix+"rows[no]",prefix+"rows[0",prefix,prefix+"::",prefix+"item..value",{value:4},[],[prefix+"item.value"],[prefix+"item.value",[prefix+"nullish.value",7]], [for(i in 0...24) prefix+"item.value"]];
  var count=0;
  for(input in inputs)for(recursive in [false,true])for(mode in 0...4){var expected=run(true,input,recursive,mode),actual=run(false,input,recursive,mode);if(expected!=actual)throw Std.string(input)+" recursive="+recursive+" mode="+mode+" expected="+expected+" actual="+actual;count++;}
  trace("instance-parser-cases:"+count);
 }
}
'''.replace('__METHODS__',methods.replace('Type.resolveClass','Main.resolve')).replace('__LOOKUP__',lookup.replace('Reflect.getProperty','Main.property'))
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=Path(folder);(work/'Main.hx').write_text(fixture)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'-main','Main','--interp'],capture_output=True,text=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('instance-parser-cases:224',result.stdout)
   if os.name=='nt':
    compiler=ROOT/'.tools/llvm-mingw-windows';cpp=work/'cpp'
    env={**os.environ,'HAXEPATH':str(ROOT/'.tools/haxe'),'NEKOPATH':str(ROOT/'.tools/neko'),'HAXELIB_PATH':str(ROOT/'.haxelib'),'MINGW_ROOT':str(compiler),'HXCPP_MINGW_EXE':'x86_64-w64-mingw32-clang++.exe','HXCPP_AR':'llvm-ar.exe','HXCPP_RANLIB':'llvm-ranlib.exe','HXCPP_STRIP':'llvm-strip.exe','HXCPP_RC':'llvm-windres.exe'}
    env['PATH']=os.pathsep.join((str(ROOT/'.tools/haxe'),str(ROOT/'.tools/neko'),str(compiler/'bin'),env.get('PATH','')))
    built=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'-main','Main','-cpp',str(cpp),'-D','HXCPP_M64','-D','HXCPP_MINGW','-D','HXCPP_RC=llvm-windres.exe'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=120)
    self.assertEqual(built.returncode,0,(built.stdout+built.stderr)[-4000:])
    for name in ('libc++.dll','libunwind.dll','libwinpthread-1.dll'):shutil.copy2(ROOT/'export/release/windows/bin'/name,cpp/name)
    native=subprocess.run([str(cpp/'Main.exe')],cwd=cpp,env=env,capture_output=True,text=True,timeout=30)
    self.assertEqual(native.returncode,0,native.stdout+native.stderr)
    self.assertIn('instance-parser-cases:224',native.stdout)

