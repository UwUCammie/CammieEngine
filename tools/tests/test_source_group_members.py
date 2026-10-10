"""Native group replacement/recycling and source member array access."""
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath as Path
from test_psych_compiled_stage_runtime import ROOT,FLIXEL_ARGS,haxe_env
class SourceGroupMembersTest(unittest.TestCase):
 def test_members_and_native_sprite_group_semantics(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   base=Path(folder);owner=base/'owner';module=owner/'source/demo';module.mkdir(parents=True)
   member="""package demo;import flixel.FlxSprite;
class Member extends FlxSprite {
 public var custom:Int=9;
 public function new(){super(3,4);}
 public function value():Int return custom;
}
"""
   runner="""package demo;
class Runner {
 public function new(){}
 public function replace(group:Dynamic,old:Dynamic,value:Dynamic):Dynamic {var captured=group.replace;return captured(old,value);}
 public function write(group:Dynamic,value:Dynamic):Dynamic {var members=group.members;return members[0]=value;}
 public function writeInner(group:Dynamic,value:Dynamic):Dynamic {var members=group.group.members;return members[0]=value;}
 public function sum(group:Dynamic):Int {var result=0;for (member in group.members) if(member!=null) result+=member.value();return result;}
 public function plain(value:Dynamic):Bool {var members=[];members[0]=value;return members[0]==value;}
 public function recycle(group:Dynamic,type:Dynamic):Dynamic {var captured=group.recycle;return captured(type);}
}
"""
   (module/'Member.hx').write_text(member,encoding='utf-8');(module/'Runner.hx').write_text(runner,encoding='utf-8')
   (base/'Member.hx').write_text(member.replace('package demo;','package;'),encoding='utf-8')
   (base/'Main.hx').write_text(r'''import flixel.FlxSprite;import flixel.FlxBasic;import flixel.group.FlxSpriteGroup;
import flixel.group.FlxGroup.FlxTypedGroup;
class Main {
 static function check(ok:Bool,why:String):Void {if(!ok) throw why;}
 static function main():Void {
  var bindings:Map<String,Dynamic>=['flixel.FlxSprite'=>FlxSprite];
  var a=CodenameScriptClassLoader.load(Sys.args()[0],['demo.Runner'],bindings,new Map());
  var b=CodenameScriptClassLoader.load(Sys.args()[0],['demo.Member'],bindings,new Map());
  check(a.diagnostics.concat(b.diagnostics).length==0,'load');
  var runner=a.scope.createInstance('demo.Runner');var type=b.scope.resolveClassSymbol('demo.Member');
  var group=new FlxSpriteGroup(50,60),expected=new FlxSpriteGroup(50,60);
  group.alpha=0.4;expected.alpha=0.4;
  var member=runner.callFunction('recycle',[group,type]);var oracle=expected.recycle(Member);
  check(group.members[0].x==oracle.x && group.members[0].alpha==oracle.alpha,'recycle must not apply preAdd');
  group.members[0].kill();oracle.kill();
  check(runner.callFunction('recycle',[group,type])==member && expected.recycle(Member)==oracle,'reuse source identity');
  var replacement=b.scope.createInstance('demo.Member');var nativeReplacement=new Member();
  check(runner.callFunction('replace',[group,member,replacement])==replacement,'captured replacement source result');expected.replace(oracle,nativeReplacement);
  check(group.members[0].x==nativeReplacement.x && group.members[0].y==nativeReplacement.y && group.members[0].alpha==nativeReplacement.alpha,'replace native preAdd');
  var absent=b.scope.createInstance('demo.Member'),uninserted=b.scope.createInstance('demo.Member');var nativeUninserted=new Member();
  check(runner.callFunction('replace',[group,absent,uninserted])==null && expected.replace(new Member(),nativeUninserted)==null,'absent replacement result');
  @:privateAccess var uninsertedNative:FlxSprite=b.scope.unwrapOwnedFlxBasic(uninserted);
  check(uninsertedNative.x==nativeUninserted.x && uninsertedNative.alpha==nativeUninserted.alpha,'native failed replacement still preAdds');
  var array=group.members;
  check(runner.callFunction('write',[group,member])==member && array==group.members,'indexed assignment returns source and keeps array');
  check(group.members[0].x==oracle.x && group.members[0].alpha==oracle.alpha,'indexed assignment does not apply group transforms');
  check(runner.callFunction('sum',[group])==9,'raw member loop restores source method');
  check(runner.callFunction('writeInner',[group,replacement])==replacement && runner.callFunction('sum',[group])==9,'internal members array preserves sprite storage');
  check(runner.callFunction('plain',[member]),'ordinary array untouched');
  var factories=new FlxSpriteGroup(50,60);
  var factory=a.scope.bindNativeMethod(factories,'recycle',Reflect.field(factories,'recycle'));
  check(Reflect.callMethod(null,factory,[null,function(){return absent;}])==absent,'factory-only source recycling');
  check(factories.members[0].x==3,'factory-only recycle has no preAdd');
  var capped=new FlxSpriteGroup(20,30,1);var first=runner.callFunction('recycle',[capped,type]);
  check(runner.callFunction('recycle',[capped,type])==first && capped.length==1,'native capped rotation');
  var basics=new FlxTypedGroup<FlxBasic>();
  basics.add(new FlxBasic());check(runner.callFunction('write',[basics,member])==member && runner.callFunction('sum',[basics])==9,'basic group indexed write');
  // Raw array assignment intentionally leaves group length management to native behavior.
  a.scope.release();check(b.scope.isActive(),'borrower release changed ownership');
  group.destroy();factories.destroy();capped.destroy();basics.destroy();expected.destroy();b.scope.release();
  Sys.println('source group member operations passed');
 }
}
''',encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,*FLIXEL_ARGS,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-ex/git/src'),'-cp',str(base),'--run','Main',str(owner)],cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=90)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('source group member operations passed',result.stdout)
if __name__=='__main__':unittest.main()
