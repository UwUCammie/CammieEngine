"""Compiled/source native returns and lexical setter storage, including closures."""
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath as Path
from test_psych_compiled_stage_runtime import ROOT,FLIXEL_ARGS,haxe_env

CLASSES={
'Graphic':"""package demo;import flixel.FlxSprite;import flixel.system.FlxAssets.FlxGraphicAsset;
class Graphic extends FlxSprite {
 public var loads:Int=0;public var argsSeen:String='';
 public function new(graphic:Dynamic) super(2,3,graphic);
 override public function loadGraphic(graphic:FlxGraphicAsset,animated:Bool=false,frameWidth:Int=0,frameHeight:Int=0,unique:Bool=false,?key:String):FlxSprite {
  loads++;argsSeen+=animated+':'+frameWidth+':'+frameHeight+':'+unique+':'+(key==null?'none':key)+';';
  super.loadGraphic(graphic,animated,frameWidth,frameHeight,unique,key);return this;
 }
 public function stats():String return loads+':'+argsSeen;
}
""",
'Clip':"""package demo;import flixel.FlxSprite;import flixel.math.FlxRect;
class Clip extends FlxSprite {
 public var calls:Int=0;public var alphaCalls:Int=0;public var other:Clip;
 public var escaped:Void->Dynamic;public var escapedAlpha:Void->Dynamic;public var external:Void->Void;
 public function new() super();
 override function set_clipRect(rect:FlxRect):FlxRect {
  calls++;if(calls>20) throw 'setter recursion';clipRect=rect;
  if(frames!=null) frame=frames.frames[animation.frameIndex];
  if(other!=null) other.clipRect=rect;
  escaped=function(){(this).clipRect=rect;return (this).clipRect;};
  if(external!=null){var callback=external;external=null;callback();}
  return rect;
 }
 override function set_alpha(value:Float):Float {
  alphaCalls++;alpha=value;this.alpha+=0.25;var previous=alpha++;--this.alpha;
  escapedAlpha=function named(){alpha+=0.125;return this.alpha;};
  if(value==999) throw 'setter failure';return previous+0.5;
 }
 public function write(rect:FlxRect):Void {clipRect=rect;}
 public function prepare(rect:FlxRect):Void {external=function(){clipRect=rect;};}
 public function runEscaped():Dynamic return escaped();
 public function runAlpha():Dynamic return escapedAlpha();
 public function assignAlpha(value:Float):Void {alpha=value;}
 public function stats():String return calls+':'+alphaCalls+':'+alpha+':'+(clipRect==null?'null':clipRect.x+','+clipRect.y);
}
""",
'Child':"""package demo;import demo.Clip;import flixel.math.FlxRect;
class Child extends Clip {
 public var childCalls:Int=0;
 public function new() super();
 override function set_clipRect(rect:FlxRect):FlxRect {childCalls++;return super.set_clipRect(rect);}
 override public function stats():String return super.stats()+':'+childCalls;
}
""",
'Rounded':"""package demo;import flixel.FlxSprite;import flixel.math.FlxRect;
class Rounded extends FlxSprite {
 public var calls:Int=0;
 public function new() super();
 override function set_clipRect(rect:FlxRect):FlxRect {calls++;return super.set_clipRect(rect);}
}
"""
}
class SourceNativeAccessorsTest(unittest.TestCase):
 def test_native_results_backing_storage_closures_and_failures(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   base=Path(folder);owner=base/'owner';module=owner/'source/demo';module.mkdir(parents=True)
   for name,code in CLASSES.items():
    (module/(name+'.hx')).write_text(code,encoding='utf-8')
    (base/(name+'.hx')).write_text(code.replace('package demo;','package;').replace('import demo.Clip;','import Clip;'),encoding='utf-8')
   (base/'Main.hx').write_text("""import flixel.FlxSprite;import flixel.math.FlxRect;import flixel.graphics.FlxGraphic;import openfl.display.BitmapData;
class Main {
 static function check(ok:Bool,why:String):Void {if(!ok) throw why;}
 static function main():Void {
  var graph=FlxGraphic.fromBitmapData(new BitmapData(8,6,true,0xFF225588),false,'accessor',false);graph.persist=true;
  var bindings:Map<String,Dynamic>=['flixel.FlxSprite'=>FlxSprite,'flixel.math.FlxRect'=>FlxRect];
  var loaded=CodenameScriptClassLoader.load(Sys.args()[0],['demo.Graphic','demo.Clip','demo.Child','demo.Rounded'],bindings,new Map());
  check(loaded.diagnostics.length==0,'load '+loaded.diagnostics);
  var graphic=loaded.scope.createInstance('demo.Graphic',[graph]),expectedGraphic=new Graphic(graph);
  @:privateAccess var nativeGraphic:FlxSprite=cast loaded.scope.unwrapOwnedFlxBasic(graphic);
  check(nativeGraphic.loadGraphic(graph,true,4,3,false,'selected')==nativeGraphic,'source this converted to native return');expectedGraphic.loadGraphic(graph,true,4,3,false,'selected');
  check(graphic.callFunction('stats',[])==expectedGraphic.stats(),'constructor and native graphic override args: '+graphic.callFunction('stats',[])+' vs '+expectedGraphic.stats());
  check(nativeGraphic.frameWidth==4 && nativeGraphic.frameHeight==3,'native loading algorithm retained');
  for(name in ['Clip','Child']) {
   var source=loaded.scope.createInstance('demo.'+name),other=loaded.scope.createInstance('demo.Clip');
   var expected:Clip=name=='Child'?new Child():new Clip(),expectedOther=new Clip();expected.other=expectedOther;
   @:privateAccess loaded.scope.accessInterpreter().set(source,'other',other);
   @:privateAccess var native:FlxSprite=cast loaded.scope.unwrapOwnedFlxBasic(source);
   var rect=new FlxRect(1.25,2.75,3.5,4.25),rect2=new FlxRect(6.25,7.75,2.5,1.25);
   var compare=function(label:String){var actual=source.callFunction('stats',[]),want=expected.stats();check(actual==want,label+' '+name+': '+actual+' vs '+want);check(other.callFunction('stats',[])==expectedOther.stats(),'other receiver '+label);};
   native.clipRect=rect;expected.clipRect=rect;compare('native set');
   check(native.clipRect==rect && native.clipRect.x==1.25,'authored fractional rect and return identity');
   check(source.callFunction('runEscaped',[])==expected.runEscaped(),'escaped backing return');compare('escaped');
   source.callFunction('prepare',[rect2]);expected.prepare(rect2);native.clipRect=rect;expected.clipRect=rect;compare('external closure resets lexical context');
   source.callFunction('write',[rect2]);expected.write(rect2);compare('ordinary source write');
   @:privateAccess var result=native.set_alpha(0.125);@:privateAccess var wantResult=expected.set_alpha(0.125);
   check(result==wantResult,'typed setter return');compare('alpha arithmetic');
   check(source.callFunction('runAlpha',[])==expected.runAlpha(),'escaped named closure increment');compare('alpha closure');
   var failed=false;try native.alpha=999 catch(e:Dynamic) failed=Std.string(e).indexOf('setter failure')>=0;
   try expected.alpha=999 catch(e:Dynamic) {} check(failed,'native exception preserved');compare('failed setter');
   source.callFunction('assignAlpha',[0.5]);expected.assignAlpha(0.5);compare('after failure');
   native.clipRect=null;expected.clipRect=null;compare('nullable setter');
   native.destroy();expected.destroy();expectedOther.destroy();
  }
  var rounded=loaded.scope.createInstance('demo.Rounded');@:privateAccess var nativeRounded:FlxSprite=cast loaded.scope.unwrapOwnedFlxBasic(rounded);
  var rect=new FlxRect(1.25,2.75,3.5,4.25);nativeRounded.clipRect=rect;check(rect.x==1 && rect.y==3,'explicit native super retains rounding');
  var fallback=loaded.scope.createInstance('demo.Graphic',[graph]);@:privateAccess var nativeFallback:FlxSprite=cast loaded.scope.unwrapOwnedFlxBasic(fallback);
  nativeFallback.alpha=2;check(nativeFallback.alpha==1,'unoverridden native setter clamps');
  nativeGraphic.destroy();expectedGraphic.destroy();loaded.scope.release();check(graph.useCount==0,'native graphic cleanup');graph.destroy();
  Sys.println('source native accessor contracts passed');
 }
}
""",encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,*FLIXEL_ARGS,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-ex/git/src'),'-cp',str(base),'--run','Main',str(owner)],cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=90)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('source native accessor contracts passed',result.stdout)
if __name__=='__main__':unittest.main()
