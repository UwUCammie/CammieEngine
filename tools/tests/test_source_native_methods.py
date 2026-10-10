"""Shared captured native group/tween calls preserve source identity and ownership."""
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath as Path
from test_psych_compiled_stage_runtime import ROOT,FLIXEL_ARGS,haxe_env
class SourceNativeMethodTest(unittest.TestCase):
 def test_methods_members_foreign_owner_tweens_and_release(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   base=Path(folder);owner=base/'owner';module=owner/'source/demo';module.mkdir(parents=True)
   (module/'Member.hx').write_text('''package demo;import flixel.FlxObject;
class Member extends FlxObject {
 public var ticks:Int=0;
 public var destroyed:Int=0;
 public function new(){super();}
 public function stats():String return ticks+":"+destroyed;
 override public function update(elapsed:Float):Void {ticks++;}
 override public function destroy():Void {destroyed++;super.destroy();}
}
''')
   (module/'Runner.hx').write_text('''package demo;
class Runner {
 public function new(){}
 public function put(group:Dynamic,member:Dynamic):Dynamic {var add=group.add;return add(member);}
 public function take(group:Dynamic,member:Dynamic):Dynamic {var remove=group.remove;return remove(member,true);}
}
''')
   (module/'GroupOwner.hx').write_text('''package demo;import flixel.group.FlxGroup;
class GroupOwner extends FlxGroup {
 public function new(){super();}
 public function put(member:Dynamic):Dynamic {var captured=add;return captured(member);}
 public function take(member:Dynamic):Dynamic {var captured=this.remove;return captured(member,true);}
}
''')
   (base/'Main.hx').write_text('''import flixel.FlxBasic;import flixel.FlxObject;
import flixel.group.FlxGroup.FlxTypedGroup;import flixel.tweens.FlxTween;
class Main {
 static function check(ok:Bool,why:String):Void {if(!ok) throw why;}
 static function main():Void {
  var bindings:Map<String,Dynamic>=['flixel.FlxObject'=>FlxObject,'flixel.group.FlxGroup'=>FlxTypedGroup];
  var a=CodenameScriptClassLoader.load(Sys.args()[0],['demo.Member','demo.Runner','demo.GroupOwner'],bindings,new Map());
  var b=CodenameScriptClassLoader.load(Sys.args()[0],['demo.Member'],bindings,new Map());
  if(a.diagnostics.length>0 || b.diagnostics.length>0) throw a.diagnostics.concat(b.diagnostics);
  var member=b.scope.createInstance('demo.Member'),group=new FlxTypedGroup<FlxBasic>();
  var add=a.scope.bindNativeMethod(group,'add',Reflect.field(group,'add'));
  check(add==a.scope.bindNativeMethod(group,'add',Reflect.field(group,'add')),'stable captured method identity');
  check(Reflect.callMethod(null,add,[member])==member,'add returns source member');
  check(a.scope.unwrapIndexedMember(group.members[0])==member,'indexed foreign member identity');
  var seen:Dynamic=null;
  var each=a.scope.bindNativeMethod(group,'forEach',Reflect.field(group,'forEach'));
  Reflect.callMethod(null,each,[function(value:Dynamic){seen=value;}]);
  check(seen==member,'forEach actual owner');group.update(0.1);
  check(member.callFunction('stats',[])=='1:0','native update forwards to source class');
  var ownedGroup=a.scope.createInstance('demo.GroupOwner');
  check(ownedGroup.callFunction('put',[member])==member,'captured inherited bare add');
  check(ownedGroup.callFunction('take',[member])==member,'captured inherited property remove');
  ownedGroup.callFunction('destroy',[]);
  var runner=a.scope.createInstance('demo.Runner');
  check(runner.callFunction('take',[group,member])==member && group.length==0,'captured source-class removal');
  check(runner.callFunction('put',[group,member])==member && group.length==1,'captured source-class add');
  @:privateAccess FlxTween.globalManager=new flixel.tweens.FlxTween.FlxTweenManager();
  var tweenMethod=a.scope.bindNativeMethod(FlxTween,'tween',Reflect.field(FlxTween,'tween'));
  var tween:FlxTween=Reflect.callMethod(null,tweenMethod,[member,{x:25},1]);
  @:privateAccess tween.update(1);tween.cancel();
  @:privateAccess var native:FlxObject=cast b.scope.unwrapOwnedFlxBasic(member);
  check(native.x==25,'foreign tween targets native base');
  a.scope.release();check(b.scope.isActive(),'borrower release killed actual owner');
  var rejected=false;try Reflect.callMethod(null,add,[member]) catch(e:Dynamic) rejected=true;
  check(rejected,'retained native method accepted released caller');
  group.update(0.1);group.destroy();check(member.callFunction('stats',[])=='2:1','source lifecycle after borrower release');b.scope.release();
  Sys.println('shared native source methods passed');
 }
}
''')
   result=subprocess.run([*HAXE_COMMAND,*FLIXEL_ARGS,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-ex/git/src'),'-cp',str(base),'--run','Main',str(owner)],cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=90)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('shared native source methods passed',result.stdout)
if __name__=='__main__':unittest.main()
