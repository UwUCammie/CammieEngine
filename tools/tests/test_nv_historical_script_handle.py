"""Pinned historical public HScript calls over the shared real Iris module."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from test_nv_hit_order import extract_method
from tools.haxe_flixel_math_stubs import write_flixel_point_stub
ROOT=Path(__file__).resolve().parents[2]
REV='7f96eb3b5a60352413229bf134bd348b79ad5fe6'
class HistoricalScriptHandleTest(unittest.TestCase):
 def test_pinned_returns_receiver_restore_errors_and_stop(self):
  donor=ROOT.parent/'fnf_sources/NightmareVision'
  if not donor.is_dir():self.skipTest('pinned source unavailable')
  source=subprocess.check_output(['git','show',REV+':source/meta/data/scripts/FunkinHScript.hx'],cwd=donor,text=True)
  methods='\n'.join(extract_method(source,prefix+n+'(') for prefix,n in [('override public function ','stop'),('override public function ','get'),('override public function ','set'),('public function ','exists'),('override public function ','call'),('public function ','executeFunc')]).replace('override public','public')
  main=r'''class Reference {
 public var interpreter:hscript.Interp=new hscript.Interp();static var Function_Continue=0;
 public function new(){}
 __METHODS__
}
class Main {
 static function check(b:Bool,m:String){if(!b)throw m;}
 static function main(){
  var errors:Array<String>=[];
  var module=NightmareVisionScriptModule.fromSource('legacy','function value(){return result;} function identity(){return this==script;} function nested(){return script.call("identity",[]);} function broken(){throw "fixture-error";} function empty(){} function voidResult(){return;} var nonFunction=4;',{},[],function(i){var s:NightmareVisionScriptModule=cast i.variables.get('script');s.historicalCalls=true;},function(n,c,e)errors.push(c));
  var ref=new Reference();ref.set('value',function()return ref.get('result'));var parser=new hscript.Parser();parser.allowJSON=true;ref.interpreter.execute(parser.parseString('function empty(){} function voidResult(){return;}'));ref.set('nonFunction',4);
  var vals:Array<Dynamic>=[null,0,1,2,false,'text',[3]];
  for(value in vals){module.set('result',value);ref.set('result',value);check(haxe.Json.stringify(module.call('value',[]))==haxe.Json.stringify(ref.call('value',[])),'pinned return');}
  for(name in ['missing','empty','voidResult','nonFunction']){var actual=module.call(name,[]);var expected=ref.call(name,[]);check(haxe.Json.stringify(actual)==haxe.Json.stringify(expected),'pinned absent/void/non-function '+name+' '+actual+'/'+expected);}
  ref.set('self',ref);ref.interpreter.execute(parser.parseString('function identity(){return this==self;} function nested(){return self.call("identity",[]);}'));
  check(module.call('identity',[])==ref.call('identity',[])&&module.call('nested',[])==ref.call('nested',[]),'pinned own receiver including nested calls');
  check(module.interp.variables.exists('this')==ref.interpreter.variables.exists('this')&&module.get('this')==ref.get('this')&&module.get('this')==null,'pinned absent receiver restored as null entry');
  module.set('this','previous');module.call('broken',[]);check(module.get('this')=='previous'&&errors.length==1,'error receiver restoration and diagnostic');
  var extra:Map<String,Dynamic>=['result'=>'temporary'];var old=module.get('result');
  check(module.executeFunc('value',[],module,extra)=='temporary'&&extra.get('this')==module&&module.get('result')==old&&module.get('this')=='previous','shared executeFunc map restoration');
  check(module.call('identity')==true,'omitted zero-argument callback');
  var caller=new NightmareVisionScriptInterp();caller.variables.set('target',module);caller.variables.set('Reflect',caller.sourceClassScope().reflectFacade());
  caller.execute(new NightmareVisionScriptParser().parseString('var f=target.call;if(f("identity",[])!=true||Reflect.callMethod(target,Reflect.field(target,"call"),["identity",[]])!=true)throw "saved/reflected raw result";'));
  var registry=new NightmareVisionLegacyScriptRegistry();registry.add(module);check(registry.callOnScripts('identity',[])==true,'registry uses same receiver contract');
  var modern=NightmareVisionScriptModule.fromSource('modern','function value()return 19;',null,[],null,function(n,c,e)throw e);
  check(modern.call('value',[]).returnValue==19,'modern Iris record preserved');
  var vars=module.interp.variables;var refVars=ref.interpreter.variables;
  module.stop();ref.stop();module.stop();ref.stop();check(module.interp==null&&!vars.iterator().hasNext()&&!refVars.iterator().hasNext(),'stop clears retained globals and is repeatable');
  for(op in ['get','set','exists','call']){
   var a=false,b=false;try switch(op){case 'get':module.get('x');case 'set':module.set('x',1);case 'exists':module.exists('x');case 'call':module.call('x',[]);}catch(e:Dynamic)a=true;
   try switch(op){case 'get':ref.get('x');case 'set':ref.set('x',1);case 'exists':ref.exists('x');case 'call':ref.call('x',[]);}catch(e:Dynamic)b=true;
   check(a==b&&a,'stopped access fails '+op);
  }
  check(modern.call('value',[]).returnValue==19,'other script survives stop');modern.destroy();caller.release();
 }
}'''.replace('__METHODS__',methods)
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder);write_flixel_point_stub(work);(work/'Main.hx').write_text(main)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
