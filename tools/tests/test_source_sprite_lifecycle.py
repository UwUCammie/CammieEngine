"""Source FlxSprite callbacks retain native sprite-group storage and transforms."""
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_psych_compiled_stage_runtime import ROOT, FLIXEL_ARGS, haxe_env

class SourceSpriteLifecycleTest(unittest.TestCase):
 def test_native_transforms_virtual_callbacks_and_explicit_super(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   base=Path(folder);owner=base/'owner';module=owner/'source/demo';module.mkdir(parents=True)
   parent="""package demo;import flixel.FlxSprite;
class Parent extends FlxSprite {
 public var updates:Int=0;public var draws:Int=0;public var kills:Int=0;public var revives:Int=0;public var destroyed:Int=0;public var animations:Int=0;
 public function new(){super(4,6);velocity.set(10,0);}
 override public function update(dt:Float):Void {updates++;super.update(dt);}
 override function updateAnimation(dt:Float):Void {animations++;super.updateAnimation(dt);}
 override public function draw():Void {draws++;}
 override public function kill():Void {kills++;super.kill();}
 override public function revive():Void {revives++;super.revive();}
 override public function destroy():Void {destroyed++;super.destroy();}
 public function stepNative(dt:Float):Void {super.update(dt);}
 public function stats():String return updates+":"+draws+":"+kills+":"+revives+":"+destroyed+":"+animations;
}
"""
   child="""package demo;import demo.Parent;
class Child extends Parent {
 public var childUpdates:Int=0;
 public function new(){super();}
 override public function update(dt:Float):Void {childUpdates++;super.update(dt);}
 public function count():Int return childUpdates;
}
"""
   (module/'Parent.hx').write_text(parent,encoding='utf-8');(module/'Child.hx').write_text(child,encoding='utf-8')
   # Compile the identical callback bodies as native classes for the oracle.
   (base/'Parent.hx').write_text(parent.replace('package demo;','package;'),encoding='utf-8')
   (base/'Child.hx').write_text(child.replace('package demo;import demo.Parent;','package;'),encoding='utf-8')
   (base/'Main.hx').write_text(r'''import flixel.FlxSprite;import flixel.FlxBasic;
import flixel.group.FlxSpriteGroup;import flixel.group.FlxGroup.FlxTypedGroup;
class Main {
 static function check(ok:Bool,why:String):Void {if(!ok) throw why;}
 static function main():Void {
  var bindings:Map<String,Dynamic>=['flixel.FlxSprite'=>FlxSprite];
  var loaded=CodenameScriptClassLoader.load(Sys.args()[0],['demo.Child'],bindings,new Map());
  var caller=CodenameScriptClassLoader.open(Sys.args()[0],bindings,new Map());
  check(loaded.diagnostics.length==0,'load '+loaded.diagnostics);
  var source=loaded.scope.createInstance('demo.Child');var oracle=new Child();
  var group=new FlxSpriteGroup(10,20),expected=new FlxSpriteGroup(10,20);
  group.alpha=0.5;expected.alpha=0.5;group.scrollFactor.set(0.3,0.4);expected.scrollFactor.set(0.3,0.4);
  var add=caller.scope.bindNativeMethod(group,'add',Reflect.field(group,'add'));
  check(Reflect.callMethod(null,add,[source])==source,'sprite add identity');expected.add(oracle);
  var sprite=group.members[0];
  check(Std.isOfType(sprite,PsychScriptClassSprite),'actual native sprite, no composed duplicate');
  check(caller.scope.unwrapIndexedMember(sprite)==source,'sprite member identity');
  group.x=15;expected.x=15;group.alpha=0.25;expected.alpha=0.25;
  check(sprite.x==oracle.x && sprite.y==oracle.y && sprite.alpha==oracle.alpha && sprite.scrollFactor.x==oracle.scrollFactor.x,'native group transformations');
  group.update(0.1);expected.update(0.1);group.draw();expected.draw();
  source.callFunction('update',[0.2]);oracle.update(0.2);
  source.callFunction('stepNative',[0.1]);oracle.stepNative(0.1);
  check(source.callFunction('stats',[])==oracle.stats() && source.callFunction('count',[])==oracle.count(),'native/source/explicit-super callbacks');
  check(sprite.x==oracle.x,'native motion runs once');
  group.active=false;expected.active=false;sprite.active=false;oracle.active=false;
  group.update(0.1);expected.update(0.1);sprite.visible=false;oracle.visible=false;group.draw();expected.draw();
  check(source.callFunction('stats',[])==oracle.stats(),'native member active/visible gates');
  sprite.kill();oracle.kill();sprite.revive();oracle.revive();
  check(source.callFunction('stats',[])==oracle.stats() && sprite.exists==oracle.exists,'native kill/revive overrides');
  var remove=caller.scope.bindNativeMethod(group,'remove',Reflect.field(group,'remove'));
  check(Reflect.callMethod(null,remove,[source,true])==source,'remove source identity');expected.remove(oracle,true);
  var basics=new FlxTypedGroup<FlxBasic>();
  var basicAdd=caller.scope.bindNativeMethod(basics,'add',Reflect.field(basics,'add'));
  Reflect.callMethod(null,basicAdd,[source]);check(basics.members[0]==sprite,'same sprite in basic and sprite groups');
  sprite.kill();
  var recycled=caller.scope.recycleScriptClass(basics,[loaded.scope.resolveClassSymbol('demo.Parent')]);
  check(recycled.handled && recycled.value==source && basics.length==1,'sprite recycling uses source subtype');
  caller.scope.release();check(loaded.scope.isActive(),'caller release preserves owner');
  basics.destroy();source.callFunction('stats',[]);check(Std.string(source.callFunction('stats',[])).split(':')[4]=='1','destroy callback exactly once');
  check(loaded.scope.accessInterpreter()!=null,'scope still live');
  loaded.scope.release();group.destroy();expected.destroy();oracle.destroy();
  Sys.println('source sprite lifecycle passed');
 }
}
''',encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,*FLIXEL_ARGS,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-ex/git/src'),'-cp',str(base),'--run','Main',str(owner)],cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=90)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('source sprite lifecycle passed',result.stdout)
if __name__=='__main__':unittest.main()
