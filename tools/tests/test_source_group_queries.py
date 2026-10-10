"""Native group retrieval/filter predicates preserve source class identity."""
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath as Path
from test_psych_compiled_stage_runtime import ROOT,FLIXEL_ARGS,haxe_env
class SourceGroupQueriesTest(unittest.TestCase):
 def test_source_and_native_class_filters_predicates_iteration(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   base=Path(folder);owner=base/'owner';module=owner/'source/demo';module.mkdir(parents=True)
   (module/'Member.hx').write_text("""package demo;import flixel.FlxObject;
class Member extends FlxObject {
 public var score:Int=5;
 public function new(){super();}
 public function value():Int return score;
}
""",encoding='utf-8')
   (module/'Child.hx').write_text('package demo;import demo.Member;class Child extends Member {public function new(){super();}}',encoding='utf-8')
   (base/'Main.hx').write_text(r'''import flixel.FlxBasic;import flixel.FlxObject;
import flixel.group.FlxGroup.FlxTypedGroup;import hscript.ScriptClassScope;
class Member extends FlxObject {public var score=5;public function new(){super();}}
class Child extends Member {public function new(){super();}}
class Main {
 static function check(ok:Bool,why:String):Void {if(!ok) throw why;}
 static function invoke(scope:ScriptClassScope,group:Dynamic,name:String,args:Array<Dynamic>):Dynamic {
  return Reflect.callMethod(null,scope.bindNativeMethod(group,name,Reflect.field(group,name)),args);
 }
 static function main():Void {
  var bindings:Map<String,Dynamic>=['flixel.FlxObject'=>FlxObject];
  var owner=CodenameScriptClassLoader.load(Sys.args()[0],['demo.Member','demo.Child'],bindings,new Map());
  var other=CodenameScriptClassLoader.load(Sys.args()[0],['demo.Member'],bindings,new Map());
  check(owner.diagnostics.concat(other.diagnostics).length==0,'load');
  var scope=owner.scope,group=new FlxTypedGroup<FlxBasic>(),native=new FlxTypedGroup<FlxBasic>();
  var member=scope.createInstance('demo.Member'),child=scope.createInstance('demo.Child');
  var a=new Member(),b=new Child();native.add(a);native.add(b);
  invoke(scope,group,'add',[member]);invoke(scope,group,'add',[child]);
  member.callFunction('kill',[]);child.callFunction('kill',[]);a.kill();b.kill();
  var type=scope.resolveClassSymbol('demo.Member');
  check(invoke(scope,group,'getFirstAvailable',[type])==member && native.getFirstAvailable(Member)==a,'source class availability');
  check(invoke(scope,group,'getFirstAvailable',[FlxObject])==member && native.getFirstAvailable(FlxObject)==a,'native superclass sees composed source');
  check(invoke(scope,group,'getFirstAvailable',[FlxObject,true])==null && native.getFirstAvailable(FlxObject,true)==null,'exact native class excludes source subclasses');
  check(invoke(scope,group,'getFirstAvailable',[null,true])==null && native.getFirstAvailable(null,true)==null,'null exact filter');
  check(invoke(scope,group,'getFirstAvailable',[other.scope.resolveClassSymbol('demo.Member')])==null,'same named foreign owner is different class');
  check(invoke(scope,group,'getFirstDead',[])==member && native.getFirstDead()==a,'direct source kill visible immediately');
  check(invoke(scope,group,'recycle',[FlxObject])==member && native.recycle(FlxObject)==a && group.length==native.length,'native recycle reuses authored subclass');
  check(invoke(scope,group,'getFirstExisting',[])==member && invoke(scope,group,'getFirstAlive',[])==member,'native status lookups return source');
  var seen=[];invoke(scope,group,'forEachOfType',[FlxObject,function(value:Dynamic){seen.push(value);},false]);
  var nativeSeen=[];native.forEachOfType(FlxObject,function(value){nativeSeen.push(value);});
  check(seen.length==nativeSeen.length && seen[0]==member && seen[1]==child,'native superclass callback source identity');
  seen=[];invoke(scope,group,'forEachOfType',[type,function(value:Dynamic){seen.push(value);},false]);check(seen.length==2,'source subtype filter');
  var pred=function(value:Dynamic):Bool {return value.callFunction('value',[])==5;};
  check(invoke(scope,group,'getFirst',[pred])==member && invoke(scope,group,'getLast',[pred])==child,'predicate source methods');
  check(invoke(scope,group,'getFirstIndex',[pred])==0 && invoke(scope,group,'getLastIndex',[pred])==1,'predicate indices');
  check(invoke(scope,group,'any',[pred]) && invoke(scope,group,'every',[pred]),'predicate quantifiers');
  var iterator:Dynamic=invoke(scope,group,'iterator',[function(value:Dynamic){return value==child;}]);
  check(iterator.hasNext() && iterator.next()==child && !iterator.hasNext(),'filtered group iterator identity');
  var pairs:Dynamic=invoke(scope,group,'keyValueIterator',[]);var pair=pairs.next();check(pair.key==0 && pair.value==member,'group key value iterator');
  invoke(scope,group,'sort',[function(order:Int,left:Dynamic,right:Dynamic):Int {return order*(left==child?-1:1);},1]);
  check(scope.unwrapIndexedMember(group.members[0])==child,'group sort callback source identity');
  // Use a native nested group to compare native recursive order with source filters.
  var parent=new FlxTypedGroup<FlxBasic>();parent.add(group);seen=[];
  invoke(scope,parent,'forEachOfType',[FlxObject,function(value:Dynamic){seen.push(value);},true]);
  check(seen.length==2 && seen[0]==child && seen[1]==member,'recursive typed traversal retains native child-first order');
  scope.release();var rejected=false;try iterator.hasNext() catch (_:Dynamic) rejected=true;check(rejected,'retained iterator lifetime');
  parent.destroy();native.destroy();other.scope.release();
  Sys.println('source group queries passed');
 }
}
''',encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,*FLIXEL_ARGS,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-ex/git/src'),'-cp',str(base),'--run','Main',str(owner)],cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=90)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('source group queries passed',result.stdout)
if __name__=='__main__':unittest.main()
