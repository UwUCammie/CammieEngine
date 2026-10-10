"""Pinned Psych variable callbacks compared through mutation/reentry providers."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,ROOT
from test_source_event_preparation import extract_method

class SourceScriptVariablesTest(unittest.TestCase):
 def test_source_order_and_returns(self):
  donor=ROOT.parent/'fnf_sources/FNF-PsychEngine'
  def source(path):return subprocess.check_output(['git','-C',str(donor),'show','5c67ced49e5a98535298a6daa3f8f4ec79ac8399:'+path],text=True)
  lua=source('source/psychlua/FunkinLua.hx');hscript=source('source/psychlua/HScript.hx')
  callbacks=[]
  for text,prefix,names in [(lua,'lua',['setVar','getVar']),(hscript,'hs',['setVar','getVar','removeVar'])]:
   for name in names:
    token='"'+name+'"' if prefix=='lua' else "'"+name+"'"
    offset=text.index(token);start=text.index('function(',offset)
    body=extract_method(text[start:],'function(')
    callbacks.append('public static var '+prefix+name+' = '+body+';')
  fixture=r'''class MusicBeatState {public static function getVariables():Dynamic return Main.registry();}
class ReflectionFunctions {public static function parseSingleInstance(v:Dynamic):Dynamic return Main.convert(v);}
class Donor {__CALLBACKS__}
class Main {
 public static var active:Dynamic;static var a:Dynamic;static var b:Dynamic;static var reads:Int;static var scenario:Int;static var events:Array<String>;
 static function map(id:String):Dynamic return {
  exists:function(n:String):Bool {events.push(id+".exists:"+n);if((scenario&4)!=0)active=b;return (scenario&1)==0;},
  get:function(n:String):Dynamic {events.push(id+".get:"+n);return id;},
  set:function(n:String,v:Dynamic):Void {events.push(id+".set:"+n+":"+Std.string(v));},
  remove:function(n:String):Bool {events.push(id+".remove:"+n);return (scenario&8)==0;}
 };
 public static function registry():Dynamic {reads++;events.push("registry:"+reads);if((scenario&2)!=0&&reads==2)active=b;return active;}
 public static function convert(v:Dynamic):Dynamic {events.push("convert:"+Std.string(v));active=b;return "resolved";}
 static function run(source:Bool,kind:Int,mode:Int):String {
  reads=0;scenario=mode;events=[];a=map("a");b=map("b");active=a;
  var result:Dynamic=null;
  try {result=source?switch(kind){case 0:Donor.luasetVar("tag","marker");case 1:Donor.luagetVar("tag");case 2:Donor.hssetVar("tag","marker");case 3:Donor.hsgetVar("tag");default:Donor.hsremoveVar("tag");}:switch(kind){
   case 0:SourceScriptVariables.set(registry,"tag","marker",convert);
   case 1:SourceScriptVariables.get(registry,"tag");
   case 2:SourceScriptVariables.set(registry,"tag","marker");
   case 3:SourceScriptVariables.get(registry,"tag",true);
   default:SourceScriptVariables.remove(registry,"tag");
  };}catch(e:Dynamic){result="error:"+Std.string(e);}
  return events.join("|")+"=>"+Std.string(result);
 }
 static function main(){for(kind in 0...5)for(mode in 0...16){var wanted=run(true,kind,mode),actual=run(false,kind,mode);if(wanted!=actual)throw kind+":"+mode+" expected "+wanted+" got "+actual;}trace("variable-callbacks:80");}
}
'''.replace('__CALLBACKS__','\n'.join(callbacks))
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=Path(folder);(work/'Main.hx').write_text(fixture)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'-main','Main','--interp'],text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('variable-callbacks:80',result.stdout)
