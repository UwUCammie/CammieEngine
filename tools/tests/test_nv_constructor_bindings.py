"""Exercise constructor alias precedence using real Iris and a colliding host class."""
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from tools.haxe_flixel_math_stubs import write_flixel_point_stub

ROOT = Path(__file__).resolve().parents[2]
MAIN = r'''import crowplexus.hscript.Parser;
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main():Void {
  check(Type.getClassName(Controls)=='Controls','colliding host class not linked');
  var parser=new Parser(), interp=new NightmareVisionScriptInterp();
  var ownerA:Dynamic={}, ownerB:Dynamic={};
  interp.variables.set('Controls',ownerA);
  interp.bindImport('funkin.input.Controls',ownerA);
  interp.bindConstructorFactory(ownerA,function(args) return {owner:'A',name:args[0]},null);
  interp.bindConstructorFactory(ownerB,function(args) return {owner:'B',name:args[0]},null);
  interp.execute(parser.parseString('first=new Controls("bare"); qualified=new funkin.input.Controls("qualified");'));
  check(interp.variables.get('first').owner=='A','host class stole seeded constructor');
  check(interp.variables.get('qualified').name=='qualified','qualified owner constructor ignored');
  interp.variables.set('replacement',ownerB);
  interp.execute(parser.parseString('{var Controls=replacement; localResult=new Controls("local");} after=new Controls("after");'));
  check(interp.variables.get('localResult').owner=='B','local constructor did not shadow seeded class');
  check(interp.variables.get('after').owner=='A','local constructor shadow escaped scope');
  interp.variables.remove('Controls');
  interp.execute(parser.parseString('fallback=new Controls("native");'));
  check(interp.variables.get('fallback').name=='native','compiled constructor fallback changed');
  interp.release();
  trace('CONSTRUCTORS_OK');
 }
}'''

class NightmareVisionConstructorBindingsTest(unittest.TestCase):
 def test_seeded_local_qualified_and_host_constructor_resolution(self):
  with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
   work=Path(directory)
   write_flixel_point_stub(work)
   (work / 'Main.hx').write_text(MAIN,newline='\n')
   (work / 'Controls.hx').write_text('class Controls {public var name:String;public function new(name:String) this.name=name;}',newline='\n')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT / 'source'),'-cp',str(ROOT / '.haxelib/hscript-iris/1,1,3'),'-cp',str(work),'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=60)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr)
