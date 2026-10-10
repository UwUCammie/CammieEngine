"""Cross-owner source recycling compared with pinned native Flixel groups."""
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_psych_compiled_stage_runtime import ROOT, FLIXEL_ARGS, haxe_env


class SourceCrossOwnerRecycleTest(unittest.TestCase):
 def test_class_identity_factory_rotation_and_lifetime(self):
  with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
   base = Path(folder)
   owner = base / 'owner'
   module = owner / 'source/demo'
   module.mkdir(parents=True)
   (module / 'Particle.hx').write_text("""package demo;import flixel.FlxBasic;
class Particle extends FlxBasic {
 public var destroyed:Int=0;
 public function new(){super();}
 override public function destroy():Void {destroyed++;super.destroy();}
 public function count():Int return destroyed;
}
""", encoding='utf-8')
   (module / 'Child.hx').write_text("""package demo;import demo.Particle;
class Child extends Particle {public function new(){super();}}
""", encoding='utf-8')
   (base / 'Main.hx').write_text(r'''import flixel.FlxBasic;
import flixel.group.FlxGroup.FlxTypedGroup;
import hscript.ScriptClassScope;
class Particle extends FlxBasic {public function new(){super();}}
class Child extends Particle {public function new(){super();}}
class OtherParticle extends FlxBasic {public function new(){super();}}
class Main {
 static function check(ok:Bool,why:String):Void {if(!ok) throw why;}
 static function rejected(run:Void->Void,why:String):Void {
  var failed=false;try run() catch(e:Dynamic) failed=true;check(failed,why);
 }
 static function call(scope:ScriptClassScope,group:FlxTypedGroup<FlxBasic>,args:Array<Dynamic>):Dynamic {
  var captured=scope.bindNativeMethod(group,'recycle',Reflect.field(group,'recycle'));
  return Reflect.callMethod(null,captured,args);
 }
 static function main():Void {
  var bindings:Map<String,Dynamic>=['flixel.FlxBasic'=>FlxBasic];
  var a=CodenameScriptClassLoader.load(Sys.args()[0],['demo.Particle','demo.Child'],bindings,new Map());
  var b=CodenameScriptClassLoader.load(Sys.args()[0],['demo.Particle','demo.Child'],bindings,new Map());
  var c=CodenameScriptClassLoader.load(Sys.args()[0],['demo.Particle'],bindings,new Map());
  check(a.diagnostics.concat(b.diagnostics).concat(c.diagnostics).length==0,'load diagnostics');
  var symbol=b.scope.resolveClassSymbol('demo.Particle');
  var child=b.scope.createInstance('demo.Child');
  var sameName=a.scope.createInstance('demo.Particle');
  var group=new FlxTypedGroup<FlxBasic>();
  var ownBridge:FlxBasic=a.scope.unwrapNativeGroupArguments(group,'add',[sameName])[0];
  var childBridge:FlxBasic=a.scope.unwrapNativeGroupArguments(group,'add',[child])[0];
  group.add(ownBridge);group.add(childBridge);ownBridge.kill();childBridge.kill();
  var native=new FlxTypedGroup<FlxBasic>();var other=new OtherParticle();var nativeChild=new Child();
  native.add(other);native.add(nativeChild);other.kill();nativeChild.kill();
  check(native.recycle(Particle,null,false,false)==nativeChild,'native subtype oracle');
  check(call(a.scope,group,[symbol,null,false,false])==child && !childBridge.exists,'subtype uses actual owner; revive false');
  check(call(a.scope,group,[symbol])==child && childBridge.exists,'revive true');
  childBridge.kill();nativeChild.kill();
  var exact=call(a.scope,group,[symbol,null,true]);var nativeExact=native.recycle(Particle,null,true);
  check(exact!=child && exact!=sameName && Type.getClass(nativeExact)==Particle,'force excludes child and same-named foreign class');
  check(group.length==native.length && group.length==3,'native grow count');
  var exactBridge=group.members[2];exactBridge.kill();
  check(call(a.scope,group,[symbol,null,true])==exact,'reuse exact foreign class');
  var factories=new FlxTypedGroup<FlxBasic>();var third=c.scope.createInstance('demo.Particle');
  check(call(a.scope,factories,[symbol,function(){return third;}])==third,'factory keeps returned actual owner');
  var empty=new FlxTypedGroup<FlxBasic>();
  check(call(a.scope,empty,[symbol,function(){return null;}])==null && empty.length==0,'null factory');
  var rotating=new FlxTypedGroup<FlxBasic>(1),nativeRotating=new FlxTypedGroup<FlxBasic>(1);
  var rotated=call(a.scope,rotating,[symbol]);nativeRotating.recycle(Particle);
  rotating.members[0].kill();nativeRotating.members[0].kill();
  check(call(c.scope,rotating,[a.scope.resolveClassSymbol('demo.Particle'),function(){throw 'factory called at capacity';return null;},true,false])==rotated,'capacity ignores class/factory');
  nativeRotating.recycle(OtherParticle,null,true,false);
  check(rotating.members[0].exists==nativeRotating.members[0].exists,'capacity preserves revive false');
  var retained=a.scope.bindNativeMethod(rotating,'recycle',Reflect.field(rotating,'recycle'));
  a.scope.release();
  rejected(function(){Reflect.callMethod(null,retained,[symbol]);},'released caller');
  check(b.scope.isActive() && c.scope.isActive(),'borrower release transfers no ownership');
  check(call(c.scope,rotating,[symbol])==rotated && rotating.members[0].exists,'other live caller revives actual owner');
  group.destroy();rotating.destroy();factories.destroy();empty.destroy();
  check(exact.callFunction('count',[])==1 && third.callFunction('count',[])==1,'destroy exactly once');
  b.scope.release();
  rejected(function(){call(c.scope,new FlxTypedGroup<FlxBasic>(),[symbol]);},'released class owner');
  var doomed=c.scope.resolveClassSymbol('demo.Particle');var unpublished=new FlxTypedGroup<FlxBasic>();
  rejected(function(){call(c.scope,unpublished,[doomed,function(){c.scope.release();return new FlxBasic();}]);},'factory releases caller');
  check(unpublished.length==0,'no insertion after factory releases caller');
  native.destroy();nativeRotating.destroy();unpublished.destroy();
  Sys.println('cross-owner recycling passed');
 }
}
''', encoding='utf-8')
   result = subprocess.run([*HAXE_COMMAND, *FLIXEL_ARGS, '-cp', str(ROOT/'source'),
    '-cp', str(ROOT/'.haxelib/hscript/2,5,0'), '-cp', str(ROOT/'.haxelib/hscript-ex/git/src'),
    '-cp', str(base), '--run', 'Main', str(owner)], cwd=ROOT, env=haxe_env(),
    capture_output=True, text=True, timeout=90)
   self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
   self.assertIn('cross-owner recycling passed', result.stdout)

if __name__ == '__main__': unittest.main()
