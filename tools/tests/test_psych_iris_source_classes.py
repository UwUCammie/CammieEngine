"""Real Iris and owner-class loader integration, including borrowed lifetime."""
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_psych_compiled_stage_runtime import ROOT, FLIXEL_ARGS, haxe_env

class PsychIrisSourceClassesTest(unittest.TestCase):
    def test_shared_sessions_construction_reflection_and_script_close(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            base=Path(directory)
            for name in ('one','two'):
                modules=base/name/'source/demo';modules.mkdir(parents=True)
                (modules/'Counter.hx').write_text('''package demo;
class Counter {
 public static var count:Int=0;
 public var value:Int=4;
 public function new() {count++;}
 public function next():Int return ++count;
 public function add(n:Int):Int {value+=n;return value;}
}
''',encoding='utf-8')
                (modules/'Native.hx').write_text('package demo; class Native {invalid syntax}',encoding='utf-8')
                (modules/'Bad.hx').write_text('package demo; class Wrong {}',encoding='utf-8')
                (modules/'ExtraStage.hx').write_text('''package demo; import backend.BaseStage;
class ExtraStage extends BaseStage {
 public var ticks:Int=0;
 override public function create():Void {ticks=10;new BaseStage();}
 override public function stepHit():Void {ticks++;}
}
''',encoding='utf-8')
            (base/'HxcCompatRuntime.hx').write_text('class HxcCompatRuntime {public static function getZIndex(o:Dynamic):Dynamic return 0; public static function setZIndex(o:Dynamic,v:Dynamic,?op:String="="):Dynamic return v; public static function getProperty(o:Dynamic,n:String):Dynamic return Reflect.getProperty(o,n); public static function setProperty(o:Dynamic,n:String,v:Dynamic):Dynamic {Reflect.setProperty(o,n,v);return v;}}')
            (base/'Main.hx').write_text('''class Main {
 static function check(ok:Bool,why:String):Void {if(!ok) throw why;}
 static function bridge(session:PsychSourceClassSession):SourceIrisBridge {
  var b=new SourceIrisBridge({});b.evaluator.bindSourceClasses(session);b.variables.set("Type",Type);b.variables.set("Reflect",Reflect);return b;
 }
 static function main():Void {
  var scene:Dynamic={stages:[],members:[]};
  var context=new SourceStageContext(function() return scene,function() return scene,function(_) return true,function(_) return null);
  var bindings:Map<String,Dynamic>=['backend.BaseStage'=>PsychBaseStageCompat,'demo.Native'=>haxe.crypto.Md5];
  var session=new PsychSourceClassSession(Sys.args()[0],scene,bindings,context);
  var a=bridge(session),b=bridge(session);
  a.evaluate('import demo.Counter; item=new Counter(); item.value=7; direct=item.add(3); method=item.add; captured=method(2); Counter.count=20; stat=item.next();','first');
  check(a.variables.get('direct')==10 && a.variables.get('captured')==12 && a.variables.get('stat')==21,'Iris source access/calls');
  var item=a.variables.get('item'),symbol=a.variables.get('Counter');
  a.variables.set('Native',haxe.crypto.Md5);a.evaluate('import demo.Native; digest=Native.encode("test");','native-precedence');
  check(a.variables.get('digest')=='098f6bcd4621d373cade4e832627b4f6','explicit native binding precedence');
  var collision=bridge(session);collision.variables.set('Counter',123);var rejectedAlias=false;
  try collision.evaluate('import demo.Counter;','collision') catch(e:Dynamic) rejectedAlias=Std.string(e).indexOf('Conflicting source class alias')>=0;
  check(rejectedAlias && collision.variables.get('Counter')==123,'source alias conflict must preserve existing value');collision.release();
  b.variables.set('item',item);
  b.evaluate('import demo.Counter; shared=Counter.count; reflected=Type.resolveClass("demo.Counter"); made=Type.createInstance(reflected,[]); same=Type.getClass(item)==Counter; name=Type.getClassName(Counter); Reflect.setProperty(item,"value",30); method=Reflect.field(item,"add"); result=Reflect.callMethod(item,method,[2]);','second');
  check(b.variables.get('shared')==21 && b.variables.get('same')==true && b.variables.get('reflected')==symbol && b.variables.get('name')=='demo.Counter' && b.variables.get('result')==32,'reflection and identity');
  a.release();
  b.evaluate('import demo.Counter; retained=item.add(1); stat=Counter.count;','after-close');
  check(b.variables.get('retained')==33 && b.variables.get('stat')==22,'script close released owner');
  var bad=false;try b.evaluate('import demo.Bad;','bad') catch(e:Dynamic) bad=Std.string(e).indexOf('demo.Bad')>=0;
  check(bad,'attributable failed import');b.evaluate('import demo.Counter; recovered=item.add(1);','retry');
  check(b.variables.get('recovered')==34,'failed import damaged owner');
  var other=new PsychSourceClassSession(Sys.args()[1],scene,bindings,context),c=bridge(other);
  c.variables.set('foreign',item);
  c.evaluate('import demo.Counter; own=new Counter(); ownCount=Counter.count; shared=foreign.add(1);','isolation');
  check(c.variables.get('Counter')!=symbol && c.variables.get('ownCount')==1 && c.variables.get('shared')==35,'owner isolation/explicit sharing');
  b.evaluate('import demo.ExtraStage; stage=new ExtraStage();','stage');
  var stage=b.variables.get('stage');b.release();
  check(scene.stages.length==2 && scene.stages[0]==stage,'stage registration after script close');
  session.call(stage,'stepHit',[]);check(session.read(stage,'ticks')==11,'stage callback after script close');
  session.call(stage,'destroy',[]);session.release();
  var released=false;try c.evaluate('value=foreign.value;','released') catch(e:Dynamic) released=true;
  check(released,'released object remained usable');c.release();other.release();
  Sys.println('Iris source class sessions passed');
 }
}
''',encoding='utf-8')
            args=list(FLIXEL_ARGS);idx=args.index('flixel');args[idx-1:idx+1]=['-cp',str(ROOT/'.haxelib/flixel/6,1,2')]
            result=subprocess.run([*HAXE_COMMAND,*args,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-ex/git/src'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',str(base),'--run','Main',str(base/'one'),str(base/'two')],cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=90)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('Iris source class sessions passed',result.stdout)

if __name__=='__main__':unittest.main()
