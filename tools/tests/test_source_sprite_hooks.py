"""Native sprite hooks reach authored overrides without replacing Flixel algorithms."""
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_psych_compiled_stage_runtime import ROOT, FLIXEL_ARGS, haxe_env

class SourceSpriteHooksTest(unittest.TestCase):
 def test_native_hitbox_and_render_callbacks(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   base=Path(folder);owner=base/'owner';module=owner/'source/demo';module.mkdir(parents=True)
   classes={}
   for name,native,ctor in [('Shape','flixel.FlxSprite','super(3,4);'),('Label','flixel.text.FlxText',"super(3,4,100,'hooks',12,false);"),('Panel','flixel.group.FlxSpriteGroup','super(3,4);')]:
    short=native.split('.')[-1]
    classes[name]=f"""package demo;import {native};import flixel.FlxCamera;
class {name} extends {short} {{
 public var hitboxes:Int=0;public var simple:Int=0;public var complex:Int=0;public var lastCamera:Dynamic;
 public function new(){{{ctor}}}
 override public function updateHitbox():Void {{hitboxes++;super.updateHitbox();offset.x+=7;}}
 override function drawSimple(camera:FlxCamera):Void {{simple++;lastCamera=camera;}}
 override function drawComplex(camera:FlxCamera):Void {{complex++;lastCamera=camera;}}
 public function cameraValue():Dynamic return lastCamera;
 public function stats():String return hitboxes+":"+simple+":"+complex;
}}
"""
   classes['Child']="""package demo;import demo.Shape;import flixel.FlxCamera;
class Child extends Shape {
 public function new(){super();}
 override public function updateHitbox():Void {super.updateHitbox();offset.x+=5;}
 override function drawComplex(camera:FlxCamera):Void {super.drawComplex(camera);complex+=3;}
 public function writes():Int {complex=8;this.complex+=2;complex++;return complex;}
 public function shadow(complex:Int):Int {complex+=2;return complex;}
}
"""
   classes['Inherited']="""package demo;import flixel.FlxSprite;
class Inherited extends FlxSprite {public function new(){super(3,4);}}
"""
   for name,code in classes.items():
    (module/(name+'.hx')).write_text(code,encoding='utf-8')
    (base/(name+'.hx')).write_text(code.replace('package demo;','package;').replace('import demo.Shape;','import Shape;'),encoding='utf-8')
   (base/'Main.hx').write_text(r"""import flixel.FlxSprite;import flixel.text.FlxText;import flixel.FlxCamera;import flixel.group.FlxSpriteGroup.FlxTypedSpriteGroup;
class Main {
 static function check(ok:Bool,why:String):Void {if(!ok) throw why;}
 static function main():Void {
  var bindings:Map<String,Dynamic>=['flixel.FlxSprite'=>FlxSprite,'flixel.text.FlxText'=>FlxText,'flixel.FlxCamera'=>FlxCamera,'flixel.group.FlxSpriteGroup'=>FlxTypedSpriteGroup];
  var loaded=CodenameScriptClassLoader.load(Sys.args()[0],['demo.Shape','demo.Label','demo.Panel','demo.Child','demo.Inherited'],bindings,new Map());
  check(loaded.diagnostics.length==0,'load '+loaded.diagnostics);
  var camera=Type.createEmptyInstance(FlxCamera);
  var classes:Array<Class<FlxSprite>>=[Shape,Label,Panel,Child];var names=['Shape','Label','Panel','Child'];
  for(i in 0...names.length) {
   var source=loaded.scope.createInstance('demo.'+names[i]);var expected=Type.createInstance(classes[i],[]);
   @:privateAccess var native:FlxSprite=cast loaded.scope.unwrapOwnedFlxBasic(source);
   native.scale.set(2,3);expected.scale.set(2,3);
   native.updateHitbox();expected.updateHitbox();
   @:privateAccess native.drawSimple(camera);@:privateAccess expected.drawSimple(camera);
   @:privateAccess native.drawComplex(camera);@:privateAccess expected.drawComplex(camera);
   check(source.callFunction('stats',[])==Reflect.callMethod(expected,Reflect.field(expected,'stats'),[]),'native hook counts '+names[i]+': '+source.callFunction('stats',[])+' vs '+Reflect.callMethod(expected,Reflect.field(expected,'stats'),[]));
   check(native.width==expected.width && native.height==expected.height && native.offset.x==expected.offset.x && native.origin.x==expected.origin.x,'native hitbox super and authored offset '+names[i]);
   check(source.callFunction('cameraValue',[])==camera,'camera identity '+names[i]);
   source.callFunction('updateHitbox',[]);expected.updateHitbox();
   check(source.callFunction('stats',[])==Reflect.callMethod(expected,Reflect.field(expected,'stats'),[]),'direct source hook does not recurse '+names[i]);
   if(names[i]=='Child') {
    check(source.callFunction('writes',[])==Reflect.callMethod(expected,Reflect.field(expected,'writes'),[]),'inherited writes return updated field');
    check(source.callFunction('shadow',[20])==22,'argument shadowing retains local value');
    check(source.callFunction('stats',[])==Reflect.callMethod(expected,Reflect.field(expected,'stats'),[]),'inherited plain explicit compound and increment writes share storage');
   }
   native.destroy();expected.destroy();
   @:privateAccess native.drawComplex(camera);native.updateHitbox();
  }
  var inherited=loaded.scope.createInstance('demo.Inherited');
  @:privateAccess var inheritedNative:FlxSprite=cast loaded.scope.unwrapOwnedFlxBasic(inherited);
  inheritedNative.scale.set(2,3);inheritedNative.updateHitbox();
  var inheritedExpected=new Inherited();inheritedExpected.scale.set(2,3);inheritedExpected.updateHitbox();
  check(inheritedNative.width==inheritedExpected.width && inheritedNative.offset.x==inheritedExpected.offset.x,'missing authored override falls back to native hook');
  inheritedNative.destroy();inheritedExpected.destroy();
  loaded.scope.release();Sys.println('source sprite hooks passed');
 }
}
""",encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,*FLIXEL_ARGS,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-ex/git/src'),'-cp',str(base),'--run','Main',str(owner)],cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=90)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('source sprite hooks passed',result.stdout)
if __name__=='__main__':unittest.main()
