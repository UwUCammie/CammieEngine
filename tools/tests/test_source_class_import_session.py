"""Persistent owner imports preserve live identity and roll back rejected batches."""
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_psych_compiled_stage_runtime import ROOT, FLIXEL_ARGS, haxe_env


class SourceClassImportSessionTest(unittest.TestCase):
    def test_incremental_identity_rollback_retry_and_owner_isolation(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            base=Path(folder)
            owners=[]
            for name in ('one','two'):
                owner=base/name
                for package in ('demo','other'):
                    (owner/'source'/package).mkdir(parents=True)
                (owner/'source/demo/Counter.hx').write_text("""package demo;
class Counter {
 public static var count:Int=0;
 public function new() {count++;}
 public function next():Int {return ++count;}
 public function current():Int {return count;}
}
""",encoding='utf-8')
                (owner/'source/demo/Later.hx').write_text("""package demo;import demo.Counter;
class Later {public function new() {} public function current():Int {return Counter.count;}}
""",encoding='utf-8')
                (owner/'source/other/Counter.hx').write_text('package other;class Counter {public function new() {}}',encoding='utf-8')
                (owner/'source/demo/Bad.hx').write_text('package demo;import other.Counter;class Wrong {}',encoding='utf-8')
                (owner/'source/demo/NativeBad.hx').write_text('package demo;import b.Native;class Wrong {}',encoding='utf-8')
                owners.append(owner)
            (base/'Main.hx').write_text("""import CodenameScriptClassLoader;
class Main {
 static function check(ok:Bool,why:String):Void {if(!ok) throw why;}
 static function main():Void {
  var nativeA={id:1},nativeB={id:2};
  var bindings:Map<String,Dynamic>=['a.Native'=>nativeA,'b.Native'=>nativeB];
  var loader=CodenameScriptClassLoader.open(Sys.args()[0],bindings,new Map());
  var scope=loader.scope;
  var first=loader.importClasses(['demo.Counter']);check(first.diagnostics.length==0,'initial import');
  var symbol=scope.resolveClassSymbol('demo.Counter');
  var object=scope.createInstance('demo.Counter');
  check(object.callFunction('next',[])==2,'initial static storage');
  var again=loader.importClasses(['demo.Counter','demo.Later']);
  check(again.scope==scope && again.diagnostics.length==0,'same scope');
  check(scope.resolveClassSymbol('demo.Counter')==symbol,'stable class symbol');
  check(scope.createInstance('demo.Later').callFunction('current',[])==2,'dependency shares statics');
  check(object.callFunction('current',[])==2,'old instance survives');
  // An import collision from a rejected batch must not remove an old alias.
  for(i in 0...100) {
   var failed=loader.importClasses(['demo.Bad']);
   check(failed.diagnostics.length>0 && !failed.imports.iterator().hasNext(),'reject entire batch');
   check(scope.findDescriptor('other.Counter')==null,'dependency did not leak');
   check(scope.resolveClassSymbol('Counter')==symbol,'alias survives failed batch');
  }
  check(object.callFunction('next',[])==3,'static values survive failed batches');
  sys.io.File.saveContent(Sys.args()[0]+'/source/demo/Bad.hx','package demo;import other.Counter;class Bad {public function new() {}}');
  var recovered=loader.importClasses(['demo.Bad']);
  check(recovered.diagnostics.length==0,'retry after fixing source');
  check(scope.findDescriptor('other.Counter')!=null,'dependency admitted on success');
  check(scope.findDescriptor('Counter')==null,'successful collision is ambiguous');
  check(scope.resolveClassSymbol('demo.Counter')==symbol,'qualified identity retained');
  check(first.diagnostics.length==0,'old result snapshot unchanged');
  var isolated=CodenameScriptClassLoader.open(Sys.args()[1],new Map(),new Map());
  isolated.importClasses(['demo.Counter']);
  check(isolated.scope.resolveClassSymbol('demo.Counter')!=symbol,'owners isolated');
  check(isolated.scope.createInstance('demo.Counter').callFunction('current',[])==1,'isolated statics');
  // Failed multi-import batches must remove successful siblings as well.
  var failedSession=CodenameScriptClassLoader.open(Sys.args()[1],new Map(),new Map());
  var failure=failedSession.importClasses(['demo.Later','missing.Class']);
  check(failure.diagnostics.length>0 && failedSession.scope.findDescriptor('demo.Counter')==null,'batch dependency rollback');
  check(failedSession.importClasses(['demo.Later']).diagnostics.length==0,'clean retry');
  // A caller mutating its original map cannot replace an admitted native binding.
  bindings.set('a.Native',nativeB);
  check(loader.importClasses(['a.Native']).diagnostics.length==0,'native import');
  check(scope.findBinding('a.Native')==nativeA,'native binding snapshot');
  // Registration exceptions restore earlier bindings and descriptors, too.
  var before=scope.findBinding('a.Native');var threw=false;
  try scope.registerImports(function() {scope.seed('a.Native',nativeB);throw 'injected';return true;}) catch(e:Dynamic) threw=true;
  check(threw && scope.findBinding('a.Native')==before,'exception rollback');
  scope.release();var rejected=false;
  try loader.importClasses(['demo.Counter']) catch(e:Dynamic) rejected=true;
  check(rejected,'released loader cannot revive source scope');
  isolated.scope.release();failedSession.scope.release();
  Sys.println('persistent source import session passed');
 }
}
""",encoding='utf-8')
            result=subprocess.run([*HAXE_COMMAND,*FLIXEL_ARGS,'-cp',str(ROOT/'source'),
                '-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-ex/git/src'),
                '-cp',str(base),'--run','Main',*[str(p) for p in owners]],
                cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=90)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('persistent source import session passed',result.stdout)


    def test_lexical_statics_match_native_haxe_with_inheritance_and_shadowing(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            base=Path(folder);owner=base/'owner';modules=owner/'source/demo';modules.mkdir(parents=True)
            (modules/'Counter.hx').write_text("""package demo;
class Counter {
 public static var count:Int=3;
 public function new() {count++;}
 public function current():Int return count;
 public function assign(value:Int):Int {count=value;return count;}
 public function compound():Int {count+=2;return count;}
 public function increments():String {return count++ + ':' + ++count + ':' + count--;}
 public function shadow(count:Int):Int {count+=5;return count;}
 public function local():Int {var count=50;count++;return count;}
}
""",encoding='utf-8')
            (modules/'Child.hx').write_text("""package demo;import demo.Counter;
class Child extends Counter {
 public static var count:Int=40;
 public function new() {super();}
 public function inheritedRead():Int return count;
 public function inheritedWrite():Int {count=19;return count;}
}
""",encoding='utf-8')
            (base/'Native.hx').write_text("""class Native {
 static function main() {
  var a=new demo.Counter(),b=new demo.Counter();
  Sys.println(a.current()+':'+b.current());
  Sys.println(a.assign(7)+':'+b.compound()+':'+a.increments());
  Sys.println(a.shadow(20)+':'+a.local()+':'+b.current());
  var c=new demo.Child();
  Sys.println(c.inheritedRead()+':'+c.inheritedWrite()+':'+c.current()+':'+a.current());
 }
}
""",encoding='utf-8')
            (base/'Actual.hx').write_text("""class Actual {
 static function call(o:Dynamic,n:String,?args:Array<Dynamic>):Dynamic return o.callFunction(n,args==null?[]:args);
 static function main() {
  var loader=CodenameScriptClassLoader.open(Sys.args()[0],new Map(),new Map());
  var loaded=loader.importClasses(['demo.Counter','demo.Child']);if(loaded.diagnostics.length>0) throw loaded.diagnostics;
  var a=loader.scope.createInstance('demo.Counter'),b=loader.scope.createInstance('demo.Counter');
  Sys.println(call(a,'current')+':'+call(b,'current'));
  Sys.println(call(a,'assign',[7])+':'+call(b,'compound')+':'+call(a,'increments'));
  Sys.println(call(a,'shadow',[20])+':'+call(a,'local')+':'+call(b,'current'));
  var c=loader.scope.createInstance('demo.Child');
  Sys.println(call(c,'inheritedRead')+':'+call(c,'inheritedWrite')+':'+call(c,'current')+':'+call(a,'current'));
  loader.scope.release();
 }
}
""",encoding='utf-8')
            outputs=[]
            for main in ('Native','Actual'):
                command=[*HAXE_COMMAND]
                if main=='Actual':
                    command += [*FLIXEL_ARGS,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-ex/git/src')]
                else:
                    command += ['-cp',str(owner/'source')]
                result=subprocess.run([*command,'-cp',str(base),'--run',main,str(owner)],cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=90)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                outputs.append(result.stdout)
            self.assertEqual(outputs[1],outputs[0])


if __name__=='__main__':
    unittest.main()
