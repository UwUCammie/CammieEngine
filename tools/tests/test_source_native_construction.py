"""Source overrides observe the same native-super construction order as Haxe."""
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath as Path
from test_psych_compiled_stage_runtime import ROOT,FLIXEL_ARGS,haxe_env
class SourceNativeConstructionTest(unittest.TestCase):
 def test_constructor_virtual_hooks_and_release(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   base=Path(folder);owner=base/'owner';module=owner/'source/demo';module.mkdir(parents=True)
   classes={}
   for name,native,ctor in [('Body','flixel.FlxObject','super(2,3,14,15);'),('Shape','flixel.FlxSprite','super(2,3);'),('Label','flixel.text.FlxText',"super(2,3,120,'constructor',14,false);"),('Panel','flixel.group.FlxSpriteGroup','super(2,3,4);')]:
    before='x=99;' if name=='Body' else ''
    group='' if name!='Panel' else "override function initGroup(maxSize:Int):Void {order+='group-before>';super.initGroup(maxSize+2);order+='group-after>'; }"
    frames='' if name=='Body' else 'override public function drawFrame(force:Bool=false):Void {framesSeen++;super.drawFrame(force);}'
    classes[name]=f"""package demo;import {native};
class {name} extends {native.split('.')[-1]} {{
 public var order:String='';public var initCalls:Int=0;public var framesSeen:Int=0;
 public function new(){{order+='before>';{before}{ctor}order+='after>';}}
 override function initVars():Void {{order+='init-before>';initCalls++;super.initVars();order+='init-after>';}}
 {frames}
 {group}
 public function stats():String return order+initCalls+':'+framesSeen;
}}
"""
   classes['Child']="""package demo;import demo.Body;
class Child extends Body {
 public var childCalls:Int=0;
 public function new(){super();}
 override function initVars():Void {childCalls++;super.initVars();}
 override public function stats():String return super.stats()+':'+childCalls;
}
"""
   classes['PanelChild']="""package demo;import demo.Panel;
class PanelChild extends Panel {
 public var seenSize:Int=0;
 public function new(){super();}
 override function initGroup(maxSize:Int):Void {seenSize=maxSize;super.initGroup(maxSize+3);}
 override public function stats():String return super.stats()+':'+seenSize+':'+maxSize;
}
"""
   classes['Reentrant']="""package demo;import flixel.FlxObject;
class Reentrant extends FlxObject {
 public var complete:Bool=false;
 public function new(){super();complete=true;}
 override function initVars():Void {super.initVars();releaseProbe(this);}
 override public function destroy():Void {destroyProbe(complete);super.destroy();}
}
"""
   classes['Broken']="""package demo;import flixel.FlxObject;
class Broken extends FlxObject {
 public function new(){super();}
 override function initVars():Void {super.initVars();failProbe(this);}
}
"""
   for name,code in classes.items():
    (module/(name+'.hx')).write_text(code,encoding='utf-8')
    if name not in ('Reentrant','Broken'):(base/(name+'.hx')).write_text(code.replace('package demo;','package;').replace('import demo.Body;','import Body;').replace('import demo.Panel;','import Panel;'),encoding='utf-8')
   (base/'Main.hx').write_text(r"""import flixel.FlxObject;import flixel.FlxSprite;import flixel.text.FlxText;import flixel.group.FlxSpriteGroup.FlxTypedSpriteGroup;
class Main {
 static function check(ok:Bool,why:String):Void {if(!ok)throw why;}
 static function main():Void {
  var bindings:Map<String,Dynamic>=['flixel.FlxObject'=>FlxObject,'flixel.FlxSprite'=>FlxSprite,'flixel.text.FlxText'=>FlxText,'flixel.group.FlxSpriteGroup'=>FlxTypedSpriteGroup];
  var loaded=CodenameScriptClassLoader.load(Sys.args()[0],['demo.Body','demo.Shape','demo.Label','demo.Panel','demo.Child','demo.PanelChild'],bindings,new Map());
  check(loaded.diagnostics.length==0,'load '+loaded.diagnostics);
  var types:Array<Class<Dynamic>>=[Body,Shape,Label,Panel,Child,PanelChild];var names=['Body','Shape','Label','Panel','Child','PanelChild'];
  for(i in 0...names.length){
   var source=loaded.scope.createInstance('demo.'+names[i]),expected:Dynamic=Type.createInstance(types[i],[]);
   var actual=source.callFunction('stats',[]),want=Reflect.callMethod(expected,Reflect.field(expected,'stats'),[]);
   check(actual==want,'construction '+names[i]+': '+actual+' vs '+want);
   @:privateAccess var native:FlxObject=cast loaded.scope.unwrapOwnedFlxBasic(source);
   check(native.x==expected.x && native.y==expected.y && native.velocity!=null,'native constructor state '+names[i]);
   if(names[i]=='Panel' || names[i]=='PanelChild') check((cast native:FlxTypedSpriteGroup<FlxSprite>).maxSize==(cast expected:FlxTypedSpriteGroup<FlxSprite>).maxSize,'authored initGroup argument and storage');
   native.destroy();expected.destroy();
  }
  loaded.scope.release();
  var failing=CodenameScriptClassLoader.load(Sys.args()[0],['demo.Broken','demo.Body'],bindings,new Map());
  var partial:hscript.ScriptClass=null;
  failing.scope.seed('failProbe',function(value:hscript.ScriptClass){partial=value;throw 'expected constructor failure';});
  var failed=false;try failing.scope.createInstance('demo.Broken') catch(error:Dynamic) failed=Std.string(error).indexOf('expected constructor failure')>=0;
  check(failed && partial!=null && failing.scope.isActive(),'failed native construction retains cleanup ownership');
  var afterFailure=failing.scope.createInstance('demo.Body');check(afterFailure!=null,'construction depth unwinds after exception');
  failing.scope.release();var partialNative:FlxObject=cast partial.superClass;
  check(partialNative.velocity==null && !failing.scope.isActive(),'partial constructor native resources released');
  var released=CodenameScriptClassLoader.load(Sys.args()[0],['demo.Reentrant'],bindings,new Map());
  var captured:Dynamic=null,destroyed=0,completed=false,live=false;
  released.scope.seed('releaseProbe',function(value:Dynamic){captured=value;released.scope.release();live=released.scope.isActive();});
  released.scope.seed('destroyProbe',function(value:Bool){destroyed++;completed=value;});
  var rejected=false;try released.scope.createInstance('demo.Reentrant') catch(error:Dynamic) rejected=Std.string(error).indexOf('released')>=0;
  check(rejected && live && completed && destroyed==1 && !released.scope.isActive(),'construction release waits for source constructor then rejects disposed result');
  @:privateAccess var held:FlxObject=cast (cast captured:hscript.ScriptClass).superClass;
  check(held.velocity==null,'constructor-release native cleanup');held.destroy();released.scope.release();check(destroyed==1,'cleanup once');
  Sys.println('source native construction passed');
 }
}
""",encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,*FLIXEL_ARGS,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-ex/git/src'),'-cp',str(base),'--run','Main',str(owner)],cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=90)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('source native construction passed',result.stdout)
if __name__=='__main__':unittest.main()
