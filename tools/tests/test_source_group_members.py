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
 public function arrayOps(group:Dynamic,a:Dynamic,b:Dynamic):String {
  var members=group.members;var out=[];members.resize(0);
  var push=members.push;out.push(push(a));members.unshift(b);members.insert(1,a);
  var it=members.iterator();out.push(it.next()==b);
  var kv=members.keyValueIterator().next();out.push(kv.key==0 && kv.value==b);
  out.push(members.contains(a));out.push(members.indexOf(a));out.push(members.lastIndexOf(a));
  out.push(members.map(function(value){return value.value();}).join(":"));
  out.push(members.filter(function(value){return value.value()>2;})[0]==a);
  out.push(members.copy()[0]==b);out.push(members.slice(1,2)[0]==a);
  members.sort(function(left,right){return left.value()-right.value();});
  out.push(members.pop()==a);out.push(members.shift()==b);out.push(members.splice(0,1)[0]==a);
  out.push(members.concat([a,b])[1]==b);members.push(a);out.push(members.remove(a));out.push(members.length);
  return out.join("|");
 }
 public function replaceMembers(group:Dynamic,values:Dynamic):Bool {group.members=values;return group.members==values;}
 public function plain(value:Dynamic):Bool {var members=[];members[0]=value;return members[0]==value;}
 public function recycle(group:Dynamic,type:Dynamic):Dynamic {var captured=group.recycle;return captured(type);}
}
"""
   (module/'Member.hx').write_text(member,encoding='utf-8');(module/'Runner.hx').write_text(runner,encoding='utf-8')
   (module/'OwnedGroup.hx').write_text('''package demo;import flixel.group.FlxGroup;
class OwnedGroup extends FlxGroup {
 public function new(){super();}
 public function writeBare(values:Dynamic):Bool {members=values;return members==values;}
 public function writeThis(values:Dynamic):Bool {this.members=values;return this.members==values;}
 public function first():Dynamic {return members[0];}
}
''',encoding='utf-8')
   (base/'Member.hx').write_text(member.replace('package demo;','package;'),encoding='utf-8')
   (base/'Runner.hx').write_text(runner.replace('package demo;','package;').replace('for (member in group.members)', 'for (member in (cast group.members:Array<Dynamic>))').replace('public function arrayOps(group:Dynamic,a:Dynamic,b:Dynamic)', 'public function arrayOps(group:flixel.group.FlxSpriteGroup,a:Member,b:Member)').replace('var members=group.members;var out=[];', 'var members:Array<Member>=cast group.members;var out:Array<Dynamic>=[];'),encoding='utf-8')
   (base/'Main.hx').write_text(r'''import flixel.FlxSprite;import flixel.FlxBasic;import flixel.group.FlxSpriteGroup;
import flixel.group.FlxGroup.FlxTypedGroup;
class Main {
 static function check(ok:Bool,why:String):Void {if(!ok) throw why;}
 static function main():Void {
  var bindings:Map<String,Dynamic>=['flixel.FlxSprite'=>FlxSprite,'flixel.group.FlxGroup'=>FlxTypedGroup];
  var a=CodenameScriptClassLoader.load(Sys.args()[0],['demo.Runner','demo.OwnedGroup'],bindings,new Map());
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
  var arrays=new FlxSpriteGroup(),nativeArrays=new FlxSpriteGroup();
  @:privateAccess replacement._interp.variables.set('custom',2);nativeReplacement.custom=2;
  var result=runner.callFunction('arrayOps',[arrays,member,replacement]);
  var nativeResult=new Runner().arrayOps(nativeArrays,cast oracle,nativeReplacement);
  check(result==nativeResult,'structural array operations differ: '+result+' / '+nativeResult);
  var values:Array<Dynamic>=[member,replacement];
  check(runner.callFunction('replaceMembers',[basics,values]),'whole members replacement preserves input array identity');
  check(runner.callFunction('sum',[basics])==11 && basics.members[0]!=member,'whole replacement retains native storage and source reads');
  var owned=a.scope.createInstance('demo.OwnedGroup');
  check(owned.callFunction('writeBare',[[member]]) && owned.callFunction('first',[])==member,'inherited bare members replacement');
  check(owned.callFunction('writeThis',[[replacement]]) && owned.callFunction('first',[])==replacement,'inherited explicit members replacement');
  var iterator=a.scope.bindNativeMethod(arrays.members,'iterator',Reflect.field(arrays.members,'iterator'));
  var retained=Reflect.callMethod(null,iterator,[]);
  // Raw array assignment intentionally leaves group length management to native behavior.
  a.scope.release();check(b.scope.isActive(),'borrower release changed ownership');
  var rejected=false;try retained.hasNext() catch (_:Dynamic) rejected=true;check(rejected,'retained iterator accepted released caller');
  arrays.destroy();nativeArrays.destroy();
  group.destroy();factories.destroy();capped.destroy();basics.destroy();expected.destroy();b.scope.release();
  Sys.println('source group member operations passed');
 }
}
''',encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,*FLIXEL_ARGS,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-ex/git/src'),'-cp',str(base),'--run','Main',str(owner)],cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=90)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('source group member operations passed',result.stdout)
if __name__=='__main__':unittest.main()
