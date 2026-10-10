"""Compare inherited owner-script method dispatch with compiled Haxe classes."""
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_psych_compiled_stage_runtime import ROOT, FLIXEL_ARGS, haxe_env

CLASSES={
 'Base': """package demo;
class Base {
 public var during:String;
 public function new() {during=ping('ctor');}
 public function ping(value:String='default'):String return 'base:'+value;
 public static function stamp():String return 'base-static';
 public function staticCall():String return stamp();
 private function privatePing():String return 'base-private';
 public function privateCall():String return privatePing();
 public function wide(a:Int,b:Int=2,c:Int=3,d:Int=4,e:Int=5,f:Int=6):String return ''+(a+b+c+d+e+f);
 public function capture():String->String return ping;
 public function capturedWide():String {var method=wide;return method(1,2,3,4,5,6)+':'+method(7);}
 public function run():String return during+'|'+ping('bare')+'|'+this.ping('this')+'|'+privateCall()+'|'+staticCall();
 public function local(ping:String->String):String return ping('local');
 public function fail():Void {}
 public function recover():String {try {fail();} catch(error:Dynamic) {} return ping('after');}
}
""",
 'Middle': """package demo;import demo.Base;
class Middle extends Base {
 public function new() super();
 override public function ping(value:String='default'):String return 'middle:'+super.ping(value);
 public function inheritedCall():String return ping('middle-body');
}
""",
 'Child': """package demo;import demo.Middle;
class Child extends Middle {
 public function new() super();
 override public function ping(value:String='default'):String return 'child:'+super.ping(value);
 public static function stamp():String return 'child-static';
 override private function privatePing():String return 'child-private';
 override public function wide(a:Int,b:Int=2,c:Int=3,d:Int=4,e:Int=5,f:Int=6):String return 'child-wide:'+super.wide(a,b,c,d,e,f);
 override public function fail():Void {throw 'child failure';}
 public function explicitSuper(value:String):String return super.ping(value);
}
"""}

class ScriptClassVirtualMethodsTest(unittest.TestCase):
 def test_native_and_script_inheritance_calls_references_defaults_and_shadowing_match(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
   base=Path(directory);owner=base/'owner';sources=owner/'source/demo';sources.mkdir(parents=True)
   for name,code in CLASSES.items(): (sources/(name+'.hx')).write_text(code,encoding='utf-8')
   main="""class Main {
 static function main() {
  SETUP
  var output:Array<String>=[];
  output.push(child.run());output.push(child.inheritedCall());
  var captured=child.capture();output.push(captured('captured'));
  output.push(child.explicitSuper('explicit-super'));
  output.push(child.capturedWide());
  output.push(child.local(function(value) return 'local:'+value));
  output.push(child.recover());
  Sys.println(output.join('\\n'));
 }
}
"""
   native=base/'native';actual=base/'actual';native.mkdir();actual.mkdir()
   (native/'Main.hx').write_text(main.replace('SETUP','var child=new demo.Child();'),encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(native),'-cp',str(owner/'source'),'--run','Main'],cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=30)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr);expected=result.stdout
   setup="""var loaded=CodenameScriptClassLoader.load(Sys.args()[0],['demo.Child'],new Map(),new Map());
  if(loaded.diagnostics.length!=0) throw loaded.diagnostics;
  var child:hscript.AbstractScriptClass=loaded.scope.createInstance('demo.Child');"""
   (actual/'Main.hx').write_text(main.replace('SETUP',setup),encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(actual),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-ex/git/src'),*FLIXEL_ARGS,'--run','Main',str(owner)],cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=90)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertEqual(result.stdout,expected)

if __name__=='__main__': unittest.main()
