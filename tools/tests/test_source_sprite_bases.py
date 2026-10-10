"""Text and nested sprite-group source subclasses share native lifecycle dispatch."""
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_psych_compiled_stage_runtime import ROOT, FLIXEL_ARGS, haxe_env

class SourceSpriteBasesTest(unittest.TestCase):
 def test_nested_group_and_text_match_compiled_haxe(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   base=Path(folder);owner=base/'owner';module=owner/'source/demo';module.mkdir(parents=True)
   modules={
    'Label':"""package demo;import flixel.text.FlxText;
class Label extends FlxText {
 public var ticks:Int=0;public var draws:Int=0;public var destroyed:Int=0;public var kills:Int=0;public var revives:Int=0;
 public function new(){super(3,4,120,'shared text',14,false);}
 override public function update(dt:Float):Void {ticks++;super.update(dt);}
 override public function draw():Void {draws++;}
 override public function kill():Void {kills++;super.kill();}
 override public function revive():Void {revives++;super.revive();}
 override public function destroy():Void {destroyed++;super.destroy();}
 public function stats():String return ticks+":"+draws+":"+destroyed+":"+kills+":"+revives;
}
""",
    'Panel':"""package demo;import flixel.group.FlxSpriteGroup;import demo.Label;
class Panel extends FlxSpriteGroup {
 public var ticks:Int=0;public var draws:Int=0;public var destroyed:Int=0;public var label:Label;
 public function new(){super(10,20);label=new Label();add(label);}
 override public function update(dt:Float):Void {ticks++;super.update(dt);}
 override public function draw():Void {draws++;super.draw();}
 override public function destroy():Void {destroyed++;super.destroy();}
 public function stats():String return ticks+":"+draws+":"+destroyed;
 public function labelStats():String return label.stats();
 public function change():Void {label.text='changed text';label.size=16;label.alignment='center';}
 public function textState():String return label.text+":"+label.size+":"+label.alignment;
}
"""}
   for name,code in modules.items():
    (module/(name+'.hx')).write_text(code,encoding='utf-8')
    (base/(name+'.hx')).write_text(code.replace('package demo;','package;').replace('import demo.Label;','import Label;'),encoding='utf-8')
   (base/'Main.hx').write_text(r'''import flixel.FlxSprite;import flixel.text.FlxText;
import flixel.group.FlxSpriteGroup;import flixel.group.FlxSpriteGroup.FlxTypedSpriteGroup;
class Main {
 static function check(ok:Bool,why:String):Void {if(!ok) throw why;}
 static function main():Void {
  var bindings:Map<String,Dynamic>=['flixel.text.FlxText'=>FlxText,'flixel.group.FlxSpriteGroup'=>FlxTypedSpriteGroup];
  var loaded=CodenameScriptClassLoader.load(Sys.args()[0],['demo.Panel'],bindings,new Map());
  check(loaded.diagnostics.length==0,'load '+loaded.diagnostics);
  var oracle=new Panel();var panel=loaded.scope.createInstance('demo.Panel');
  var outer=new FlxSpriteGroup(7,9),expected=new FlxSpriteGroup(7,9);
  var add=loaded.scope.bindNativeMethod(outer,'add',Reflect.field(outer,'add'));
  check(Reflect.callMethod(null,add,[panel])==panel,'group source identity');expected.add(oracle);
  var native:FlxSpriteGroup=cast outer.members[0];var label:FlxText=cast native.members[0];
  check(Std.isOfType(native,PsychScriptClassSpriteGroup) && Std.isOfType(label,PsychScriptClassText),'native group and text types');
  check(loaded.scope.unwrapIndexedMember(native)==panel,'nested source identity');
  outer.x+=6;expected.x+=6;outer.alpha=0.4;expected.alpha=0.4;outer.scrollFactor.set(0.2,0.3);expected.scrollFactor.set(0.2,0.3);
  check(label.x==oracle.label.x && label.y==oracle.label.y && label.alpha==oracle.label.alpha && label.scrollFactor.x==oracle.label.scrollFactor.x,'nested native transforms');
  outer.update(0.1);expected.update(0.1);outer.draw();expected.draw();panel.callFunction('update',[0.2]);oracle.update(0.2);
  check(panel.callFunction('stats',[])==oracle.stats() && panel.callFunction('labelStats',[])==oracle.labelStats(),'nested callbacks and super once');
  panel.callFunction('change',[]);oracle.change();
  check(panel.callFunction('textState',[])==oracle.textState() && label.textField.text==oracle.label.textField.text,'native text properties');
  native.kill();oracle.kill();native.revive();oracle.revive();
  check(panel.callFunction('labelStats',[])==oracle.labelStats() && label.exists==oracle.label.exists,'group kill/revive traverses authored children');
  native.destroy();oracle.destroy();
  check(panel.callFunction('stats',[])==oracle.stats() && panel.callFunction('labelStats',[])==oracle.labelStats(),'nested cleanup once');
  check(label.textField==null && native.group==null,'native text/group resources released');
  native.destroy();loaded.scope.release();
  Sys.println('source text and sprite group passed');
 }
}
''',encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,*FLIXEL_ARGS,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-ex/git/src'),'-cp',str(base),'--run','Main',str(owner)],cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=90)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('source text and sprite group passed',result.stdout)
if __name__=='__main__':unittest.main()
