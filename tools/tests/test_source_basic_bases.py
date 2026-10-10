"""Core native Flixel bases share source lifecycle, recursive groups and release."""
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath as Path
from test_psych_compiled_stage_runtime import ROOT,FLIXEL_ARGS,haxe_env
class SourceBasicBasesTest(unittest.TestCase):
 def test_core_native_bases_and_reentrant_release(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   base=Path(folder);owner=base/'owner';module=owner/'source/demo';module.mkdir(parents=True)
   modules={
    'Token':"""package demo;import flixel.FlxBasic;
class Token extends FlxBasic {
 public var ticks:Int=0;public var draws:Int=0;public var kills:Int=0;public var revives:Int=0;public var destroyed:Int=0;
 public function new(){super();}
 override public function update(dt:Float):Void {ticks++;super.update(dt);}
 override public function draw():Void {draws++;}
 override public function kill():Void {kills++;super.kill();}
 override public function revive():Void {revives++;super.revive();}
 override public function destroy():Void {destroyed++;super.destroy();}
 public function stats():String return ticks+":"+draws+":"+kills+":"+revives+":"+destroyed;
}
""",
    'Actor':"""package demo;import flixel.FlxObject;
class Actor extends FlxObject {
 public var ticks:Int=0;public var kills:Int=0;public var revives:Int=0;public var destroyed:Int=0;
 public var onUpdate:Dynamic=null;public var onDestroy:Dynamic=null;
 public function new(){super(2,3,14,15);velocity.set(10,0);}
 override public function update(dt:Float):Void {if(onUpdate!=null) onUpdate();ticks++;super.update(dt);}
 override public function draw():Void {}
 override public function kill():Void {kills++;super.kill();}
 override public function revive():Void {revives++;super.revive();}
 override public function destroy():Void {destroyed++;if(onDestroy!=null) onDestroy();super.destroy();}
 public function stats():String return ticks+":"+kills+":"+revives+":"+destroyed;
}
""",
    'Cluster':"""package demo;import flixel.group.FlxGroup;import demo.Token;import demo.Actor;
class Cluster extends FlxGroup {
 public var token:Token;public var actor:Actor;public var ticks:Int=0;public var destroyed:Int=0;
 public function new(){super(4);token=new Token();actor=new Actor();add(token);add(actor);}
 override public function update(dt:Float):Void {ticks++;super.update(dt);}
 override public function destroy():Void {destroyed++;super.destroy();}
 public function stats():String return ticks+":"+destroyed+"/"+token.stats()+"/"+actor.stats();
 public function stopToken():Void {token.active=false;token.visible=false;}
 public function killToken():Void token.kill();
 public function reviveActor():Void actor.revive();
}
"""}
   for name,code in modules.items():
    (module/(name+'.hx')).write_text(code,encoding='utf-8')
    (base/(name+'.hx')).write_text(code.replace('package demo;','package;').replace('import demo.','import '),encoding='utf-8')
   (base/'Main.hx').write_text(r'''import flixel.FlxBasic;import flixel.FlxObject;import flixel.group.FlxGroup.FlxTypedGroup;
class Main {
 static function check(ok:Bool,why:String):Void {if(!ok) throw why;}
 static function load(root:String):CodenameScriptClassLoader.CodenameScriptClassLoad {
  var result=CodenameScriptClassLoader.load(root,['demo.Cluster'],['flixel.FlxBasic'=>FlxBasic,'flixel.FlxObject'=>FlxObject,'flixel.group.FlxGroup'=>FlxTypedGroup],new Map());
  check(result.diagnostics.length==0,'load '+result.diagnostics);return result;
 }
 static function main():Void {
  var loaded=load(Sys.args()[0]),scope=loaded.scope,source=scope.createInstance('demo.Cluster');
  var expected=new Cluster(),outer=new FlxTypedGroup<FlxBasic>(),nativeOuter=new FlxTypedGroup<FlxBasic>();
  var add=scope.bindNativeMethod(outer,'add',Reflect.field(outer,'add'));Reflect.callMethod(null,add,[source]);nativeOuter.add(expected);
  var cluster:PsychScriptClassGroup=cast outer.members[0];var token:PsychScriptClassBasic=cast cluster.members[0];var actor:PsychScriptClassObject=cast cluster.members[1];
  check(actor.x==2 && actor.y==3 && actor.width==14 && actor.height==15,'native object constructor');
  outer.update(0.1);nativeOuter.update(0.1);outer.draw();nativeOuter.draw();
  source.callFunction('stopToken',[]);expected.stopToken();outer.update(0.1);nativeOuter.update(0.1);outer.draw();nativeOuter.draw();
  check(source.callFunction('stats',[])==expected.stats() && actor.x==expected.actor.x,'shared native motion and immediate active/visible state');
  var seen=[];var each=scope.bindNativeMethod(outer,'forEachOfType',Reflect.field(outer,'forEachOfType'));
  Reflect.callMethod(null,each,[FlxBasic,function(value:Dynamic){seen.push(value);},true]);
  check(seen.length==3 && seen[2]==source,'recursive traversal recognizes source group native identity');
  source.callFunction('killToken',[]);expected.killToken();cluster.kill();expected.kill();source.callFunction('reviveActor',[]);expected.reviveActor();cluster.revive();expected.revive();
  check(source.callFunction('stats',[])==expected.stats() && token.exists==expected.token.exists && actor.exists==expected.actor.exists,'authored kill and revive once');
  cluster.kill();expected.kill();cluster.destroy();expected.destroy();
  check(source.callFunction('stats',[])==expected.stats() && cluster.members==null && actor.velocity==null,'killed nested members release native resources once');
  cluster.destroy();scope.release();
  var second=load(Sys.args()[0]),item=second.scope.createInstance('demo.Cluster');
  @:privateAccess var group:PsychScriptClassGroup=cast second.scope.unwrapOwnedFlxBasic(item);
  var child:PsychScriptClassObject=cast group.members[1];var childSource=child.scriptOwner();
  var continued=false,destroyed=0;
  @:privateAccess childSource._interp.variables.set('onUpdate',function(){second.scope.release();continued=second.scope.isActive();});
  @:privateAccess childSource._interp.variables.set('onDestroy',function(){destroyed++;second.scope.release();});
  group.update(0.1);
  check(continued && !second.scope.isActive() && destroyed==1 && group.members==null && child.velocity==null,'release inside update and destroy is deferred and nonrecursive');
  group.update(0.1);group.destroy();second.scope.release();check(destroyed==1,'released adapters remain inert');
  var third=load(Sys.args()[0]),failing=third.scope.createInstance('demo.Cluster');
  @:privateAccess var failingGroup:PsychScriptClassGroup=cast third.scope.unwrapOwnedFlxBasic(failing);
  var failingActor:PsychScriptClassObject=cast failingGroup.members[1];
  @:privateAccess failingActor.scriptOwner()._interp.variables.set('onUpdate',function(){third.scope.release();throw 'expected callback failure';});
  var failed=false;try failingGroup.update(0.1) catch (error:Dynamic) failed=Std.string(error).indexOf('expected callback failure')>=0;
  check(failed && !third.scope.isActive() && failingGroup.members==null && failingActor.velocity==null,'throwing lifecycle releases after unwinding and preserves original error');
  Sys.println('core native source bases passed');
 }
}
''',encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,*FLIXEL_ARGS,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-ex/git/src'),'-cp',str(base),'--run','Main',str(owner)],cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=90)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('core native source bases passed',result.stdout)
if __name__=='__main__':unittest.main()
