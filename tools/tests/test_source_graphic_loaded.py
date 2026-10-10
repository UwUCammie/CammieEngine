"""Compiled/source comparison of constructor and native graphic-load callbacks."""
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath as Path
from test_psych_compiled_stage_runtime import ROOT,FLIXEL_ARGS,haxe_env

class SourceGraphicLoadedTest(unittest.TestCase):
 def test_real_graphic_load_order_storage_and_super(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   base=Path(folder);owner=base/'owner';module=owner/'source/demo';module.mkdir(parents=True)
   classes={}
   for name,native,ctor in [('Shape','flixel.FlxSprite','super(2,3,graphic);'),('Label','flixel.text.FlxText',"super(2,3,120,'graphic',14,false);"),('Panel','flixel.group.FlxSpriteGroup','super(2,3,4);')]:
    classes[name]=f"""package demo;import {native};
class {name} extends {native.split('.')[-1]} {{
 public var loads:Int=0; public var events:String='';
 public function new(graphic:Dynamic) {{{ctor}events+='complete;';}}
 override public function graphicLoaded():Void {{loads++;events+=frameWidth+'x'+frameHeight+';';super.graphicLoaded();offset.set(2,3);}}
 public function stats():String return loads+':'+events;
}}
"""
   classes['Child']="""package demo;import demo.Shape;
class Child extends Shape {
 public var childLoads:Int=0;
 public function new(graphic:Dynamic) super(graphic);
 override public function graphicLoaded():Void {childLoads++;super.graphicLoaded();loads+=2;}
 override public function stats():String return super.stats()+':'+childLoads;
}
"""
   classes['Inherited']='package demo;import flixel.FlxSprite;class Inherited extends FlxSprite {public function new(graphic:Dynamic) super(2,3,graphic);}'
   for name,code in classes.items():
    (module/(name+'.hx')).write_text(code,encoding='utf-8')
    (base/(name+'.hx')).write_text(code.replace('package demo;','package;').replace('import demo.Shape;','import Shape;'),encoding='utf-8')
   (base/'Main.hx').write_text("""import flixel.FlxSprite;import flixel.text.FlxText;import flixel.graphics.FlxGraphic;import openfl.display.BitmapData;import flixel.group.FlxSpriteGroup.FlxTypedSpriteGroup;
class Main {
 static function check(ok:Bool,why:String):Void {if(!ok) throw why;}
 static function main():Void {
  var first=FlxGraphic.fromBitmapData(new BitmapData(8,6,true,0xFF3388AA),false,'first',false);
  var second=FlxGraphic.fromBitmapData(new BitmapData(12,9,true,0xFF996622),false,'second',false);
  first.persist=true;second.persist=true;
  var bindings:Map<String,Dynamic>=['flixel.FlxSprite'=>FlxSprite,'flixel.text.FlxText'=>FlxText,'flixel.group.FlxSpriteGroup'=>FlxTypedSpriteGroup];
  var loaded=CodenameScriptClassLoader.load(Sys.args()[0],['demo.Shape','demo.Label','demo.Panel','demo.Child','demo.Inherited'],bindings,new Map());
  check(loaded.diagnostics.length==0,'load '+loaded.diagnostics);
  var types:Array<Class<FlxSprite>>=[Shape,Label,Panel,Child];var names=['Shape','Label','Panel','Child'];
  for(i in 0...names.length) {
   var source=loaded.scope.createInstance('demo.'+names[i],[first]),expected=Type.createInstance(types[i],[first]);
   @:privateAccess var native:FlxSprite=cast loaded.scope.unwrapOwnedFlxBasic(source);
   var compare=function(label:String) {
    var actual=source.callFunction('stats',[]),want=Reflect.callMethod(expected,Reflect.field(expected,'stats'),[]);
    check(actual==want,label+' '+names[i]+': '+actual+' vs '+want);
    check(native.frameWidth==expected.frameWidth && native.frameHeight==expected.frameHeight && native.offset.x==expected.offset.x && native.offset.y==expected.offset.y,'graphic state '+label+' '+names[i]);
   };
   compare('constructor');
   check(native.loadGraphic(second)==native && expected.loadGraphic(second)==expected,'native load return identity');compare('loadGraphic');
   native.frames=first.imageFrame;expected.frames=first.imageFrame;compare('frame assignment');
   source.callFunction('graphicLoaded',[]);expected.graphicLoaded();compare('direct source callback');
   native.frames=null;expected.frames=null;compare('clear frames');
   native.destroy();expected.destroy();native.graphicLoaded();
  }
  var inherited=loaded.scope.createInstance('demo.Inherited',[first]);
  @:privateAccess var native:FlxSprite=cast loaded.scope.unwrapOwnedFlxBasic(inherited);
  check(native.graphic==first && native.frameWidth==8 && native.frameHeight==6,'native fallback graphic');
  loaded.scope.release();
  check(first.useCount==0 && second.useCount==0,'graphic users released');first.destroy();second.destroy();
  Sys.println('source graphic hooks passed');
 }
}
""",encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,*FLIXEL_ARGS,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-ex/git/src'),'-cp',str(base),'--run','Main',str(owner)],cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=90)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('source graphic hooks passed',result.stdout)
if __name__=='__main__':unittest.main()
