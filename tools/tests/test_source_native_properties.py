"""Compare shared native property callbacks with identical compiled Flixel subclasses."""
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath as Path
from test_psych_compiled_stage_runtime import ROOT,FLIXEL_ARGS,haxe_env

COMMON = """
 public var events:String='';public var escaped:Void->Bool;
 override function set_visible(value:Bool):Bool {events+='v;';visible=value;escaped=function(){this.visible=!visible;return this.visible;};return visible;}
 override function set_active(value:Bool):Bool {events+='a;';return super.set_active(value);}
 override function set_exists(value:Bool):Bool {events+='e;';return super.set_exists(value);}
 override function set_alive(value:Bool):Bool {events+='l;';return super.set_alive(value);}
 override function get_camera():FlxCamera {events+='gc;';return super.get_camera();}
 override function set_camera(value:FlxCamera):FlxCamera {events+='sc;';return super.set_camera(value);}
 override function get_cameras():Array<FlxCamera> {events+='gcs;';return super.get_cameras();}
 override function set_cameras(value:Array<FlxCamera>):Array<FlxCamera> {events+='scs;';return super.set_cameras(value);}
 public function runEscaped():Bool return escaped();
 public function stats():String return events+':'+visible+':'+active+':'+exists+':'+alive;
 public function writeFlags():Void {visible=false;active=true;exists=true;alive=false;}
"""
GEOMETRY = """
 override function set_x(value:Float):Float {events+='x;';return super.set_x(value+0.25);}
 override function set_y(value:Float):Float {events+='y;';this.y=value;return y;}
 override function set_width(value:Float):Float {events+='w;';return super.set_width(value);}
 override function set_height(value:Float):Float {events+='h;';return super.set_height(value);}
 override function get_width():Float {events+='gw;';return super.get_width();}
 override function get_height():Float {events+='gh;';return super.get_height();}
"""
def classes():
 result={}
 for name,native,ctor in [('Basic','flixel.FlxBasic','super();'),('Object','flixel.FlxObject','super(2,3,4,5);'),('Sprite','flixel.FlxSprite','super(2,3);'),('Text','flixel.text.FlxText',"super(2,3,120,'test',14,false);"),('Group','flixel.group.FlxSpriteGroup','super(2,3,4);')]:
  result[name]='package demo;import '+native+';import flixel.FlxCamera;class '+name+' extends '+native.split('.')[-1]+' { public function new() {'+ctor+'events+="ready;";}'+COMMON+(GEOMETRY if name!='Basic' else '')+'}'
 result['Child']='package demo;import demo.Sprite;class Child extends Sprite {public function new() super();override function set_visible(value:Bool):Bool {events+="child;";return super.set_visible(value);}}'
 return result

MAIN = """import flixel.FlxBasic;import flixel.FlxObject;import flixel.FlxSprite;import flixel.FlxCamera;import flixel.text.FlxText;import flixel.group.FlxSpriteGroup.FlxTypedSpriteGroup;
class Main {
 static function check(ok:Bool,label:String):Void {if(!ok)throw label;}
 static function main():Void {
  var bindings:Map<String,Dynamic>=['flixel.FlxBasic'=>FlxBasic,'flixel.FlxObject'=>FlxObject,'flixel.FlxSprite'=>FlxSprite,'flixel.FlxCamera'=>FlxCamera,'flixel.text.FlxText'=>FlxText,'flixel.group.FlxSpriteGroup'=>FlxTypedSpriteGroup];
  var names=['Basic','Object','Sprite','Text','Group','Child'];var types:Array<Class<Dynamic>>=[Basic,Object,Sprite,Text,Group,Child];
  var loaded=CodenameScriptClassLoader.load(Sys.args()[0],[for(n in names)'demo.'+n],bindings,new Map());
  check(loaded.diagnostics.length==0,'load '+loaded.diagnostics);
  // Camera identity suffices for setters/getters and avoids a renderer requirement.
  var first:FlxCamera=Type.createEmptyInstance(FlxCamera),second:FlxCamera=Type.createEmptyInstance(FlxCamera);
  @:privateAccess FlxCamera._defaultCameras=[first];
  for(i in 0...names.length) {
   var source=loaded.scope.createInstance('demo.'+names[i]),expected:FlxBasic=Type.createInstance(types[i],[]);
   @:privateAccess var native:FlxBasic=cast loaded.scope.unwrapOwnedFlxBasic(source);
   var compare=function(label:String) {var actual=source.callFunction('stats',[]),want=Reflect.callMethod(expected,Reflect.field(expected,'stats'),[]);check(actual==want,names[i]+' '+label+': '+actual+' != '+want);};
   compare('constructor');native.visible=false;expected.visible=false;compare('native flag');
   check(source.callFunction('runEscaped',[])==Reflect.callMethod(expected,Reflect.field(expected,'runEscaped'),[]),'escaped backing result');compare('escaped backing');
   native.active=false;expected.active=false;native.exists=false;expected.exists=false;native.alive=false;expected.alive=false;compare('flags');
   native.revive();expected.revive();compare('revive');native.kill();expected.kill();compare('kill');
   source.callFunction('writeFlags',[]);Reflect.callMethod(expected,Reflect.field(expected,'writeFlags'),[]);compare('source flags');
   native.camera=second;expected.camera=second;check(native.camera==expected.camera && native.camera==second,'camera identity');
   // Match the extra reference-side getter used by the identity assertion.
   var ignored=expected.camera;compare('camera');
   var cams=[first,second];native.cameras=cams;expected.cameras=cams;
   check(native.cameras==expected.cameras,'camera array identity');compare('camera array');
   Reflect.setProperty(native,'cameras',null);Reflect.setProperty(expected,'cameras',null);
   check(native.cameras==expected.cameras,'default cameras');compare('reflected null cameras');
   if(i>0) {
    var a:FlxObject=cast native,b:FlxObject=cast expected;
    a.x=10;b.x=10;a.y=20;b.y=20;a.width=30;b.width=30;a.height=40;b.height=40;
    check(a.x==b.x && a.y==b.y && a.width==b.width && a.height==b.height,'geometry');compare('geometry');
   }
   native.destroy();expected.destroy();
  }
  loaded.scope.release();Sys.println('native property parity passed');
 }
}
"""
class SourceNativePropertiesTest(unittest.TestCase):
 def test_property_callbacks_match_compiled_native_classes(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   base=Path(folder);owner=base/'owner';module=owner/'source/demo';module.mkdir(parents=True)
   for name,code in classes().items():
    (module/(name+'.hx')).write_text(code,encoding='utf-8')
    (base/(name+'.hx')).write_text(code.replace('package demo;','package;').replace('import demo.Sprite;','import Sprite;'),encoding='utf-8')
   (base/'Main.hx').write_text(MAIN,encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,*FLIXEL_ARGS,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-ex/git/src'),'-cp',str(base),'--run','Main',str(owner)],cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=90)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('native property parity passed',result.stdout)
