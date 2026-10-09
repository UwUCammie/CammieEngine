"""Execute live historical registry mutations against the pinned source methods."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from test_nv_hit_order import extract_method
from tools.haxe_flixel_math_stubs import write_flixel_point_stub
ROOT=Path(__file__).resolve().parents[2]
REV='7f96eb3b5a60352413229bf134bd348b79ad5fe6'
class LegacyRegistryTest(unittest.TestCase):
 def test_pinned_live_arrays_mutations_and_dispatch(self):
  donor=ROOT.parent/'fnf_sources/NightmareVision'
  if not donor.is_dir():self.skipTest('pinned source unavailable')
  source=subprocess.check_output(['git','show',REV+':source/meta/states/PlayState.hx'],cwd=donor,text=True)
  methods='\n'.join(extract_method(source,'public function '+n+'(') for n in ['callOnScripts','setOnScripts','callScript','callOnHScripts','callOnLuas']).replace('FunkinScript','Entry').replace('#if LUA_ALLOWED','').replace('#else\n\t\treturn Globals.Function_Continue;\n\t\t#end','')
  main=r'''
class Globals {public static var Function_Continue=0;public static var Function_Halt=2;}
class Entry {
 public var scriptName:String;public var fn:(String,Array<Dynamic>)->Dynamic;public var vars:Map<String,Dynamic>=[];
 public function new(n:String,f:(String,Array<Dynamic>)->Dynamic){scriptName=n;fn=f;}
 public function call(n:String,a:Array<Dynamic>):Dynamic return fn(n,a);
 public function set(n:String,v:Dynamic){vars.set(n,v);}
}
class Reference {
 public var funkyScripts:Array<Dynamic>=[];public var hscriptArray:Array<Dynamic>=[];public var luaArray:Array<Dynamic>=[];
 public var eventScripts:Map<String,Dynamic>=[];public var notetypeScripts:Map<String,Dynamic>=[];
 public function new(){}
 __METHODS__
}
class Main {
 static function check(b:Bool,m:String){if(!b)throw m;}
 static function run(actual:Bool,mutation:Int,ret:Dynamic,ignore:Bool,explicit:Bool,filter:Bool):String {
  var ref=new Reference();var registry=new NightmareVisionLegacyScriptRegistry(function()return ref.eventScripts,function(n)return ref.eventScripts.exists(n)||ref.notetypeScripts.exists(n));
  var log:Array<String>=[];var list:Array<Dynamic>=[];var once=false;
  var late=new Entry('late',function(n,a){log.push('late');return 'late-result';});
  var first=new Entry('first',function(n,a){
   log.push('first');
   if(!once){once=true;switch(mutation){
    case 0:list.push(late);
    case 1:list.shift();
    case 2:list.splice(1,1);
    case 3:list.reverse();
    case 4:registry.funkyScripts=[late];ref.funkyScripts=registry.funkyScripts;
    case 5:ref.notetypeScripts.set('second',null);
    case 6:ref.eventScripts.remove('event');
    case 7:list.insert(1,late);
   }}
   return ret;
  });
  var second=new Entry('second',function(n,a){log.push('second');return 1;});
  var event=new Entry('event',function(n,a){log.push('event');return 0;});
  list.push(first);list.push(second);registry.funkyScripts=list;ref.funkyScripts=list;
  registry.hscriptArray=list;ref.hscriptArray=list;registry.luaArray=[second];ref.luaArray=[second];
  ref.eventScripts.set('event',event);
  var selected=explicit?list:null;
  var result=actual?registry.callOnScripts('probe',[7],ignore,[],selected,filter):ref.callOnScripts('probe',[7],ignore,[],selected,filter);
  var result2=actual?registry.callOnLuas('lua',[8]):ref.callOnLuas('lua',[8]);
  if(actual)registry.setOnScripts('value',9,list);else ref.setOnScripts('value',9,list);
  var names=[for(e in list)e.scriptName];
  var current=actual?registry.funkyScripts:ref.funkyScripts;
  return haxe.Json.stringify([log,result,result2,names,[for(e in current)e.scriptName],[for(e in list)e.vars.get('value')]]);
 }
 static function main(){
  var values:Array<Dynamic>=[null,0,1,2,'text',false,0.25];
  for(m in 0...8)for(r in values)for(i in [false,true])for(e in [false,true])for(f in [false,true])
   check(run(true,m,r,i,e,f)==run(false,m,r,i,e,f),'live source mutation '+m+'/'+r+'/'+i+'/'+e+'/'+f);
  var reg=new NightmareVisionLegacyScriptRegistry();var ref=new Reference();var calls=0;
  var a=new Entry('same',function(n,args){calls++;return 2;});var b=new Entry('same',function(n,args){calls++;return 'last';});
  reg.funkyScripts=[a,b];ref.funkyScripts=[a,b];
  check(reg.callScript('same','x',[])==ref.callScript('same','x',[])&&calls==4,'string selection preserves duplicates and ignores halt');
  check(reg.callScript([a,b],'x',[])=='last','explicit arrays bypass special filter');
  var old=reg.funkyScripts;reg.funkyScripts=[];reg.callOnScripts('x',[],true,null,old,false);check(calls==8,'replaced array keeps old identity');
 }
}
'''.replace('__METHODS__',methods)
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder);write_flixel_point_stub(work);(work/'Main.hx').write_text(main)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
