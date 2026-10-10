"""Exercise Codename MusicBeatGroup owner classes through native Flixel hooks."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class CodenameMusicBeatGroupTest(unittest.TestCase):
    def test_owner_update_super_dispatch_and_teardown(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            stubs = {
                "flixel/system/FlxAssets.hx": 'package flixel.system; typedef FlxGraphicAsset = Dynamic;',
                "flixel/FlxBasic.hx": '''package flixel;
class FlxBasic {
 public var updates:Int=0; public var destroys:Int=0; public var exists:Bool=true;
 public var active:Bool=true; public var visible:Bool=true; public var alive:Bool=true;
 public function new() {}
 public function update(elapsed:Float):Void updates++;
 public function draw():Void {}
 public function kill():Void { alive=false; exists=false; }
 public function revive():Void { alive=true; exists=true; }
 public function destroy():Void { destroys++; exists=false; }
}''',
                "flixel/FlxSprite.hx": '''package flixel;
class FlxSprite extends FlxBasic {
 public var x:Float=0; public var y:Float=0;
 public function new(x:Float=0,y:Float=0,?graphic:Dynamic) { super(); this.x=x; this.y=y; }
 function updateAnimation(elapsed:Float):Void {}
}''',
                "flixel/text/FlxText.hx": """package flixel.text;
class FlxText extends flixel.FlxSprite {
 public function new(x:Float=0,y:Float=0,width:Float=0,?text:String,size:Int=8,embedded:Bool=true) super(x,y);
}""",
                "flixel/ProbeSprite.hx": '''package flixel;
class ProbeSprite extends FlxSprite {
 public var beats:Int=0; public var steps:Int=0; public var measures:Int=0;
 public function new() super();
 public function beatHit(value:Int):Void beats++;
 public function stepHit(value:Int):Void steps++;
 public function measureHit(value:Int):Void measures++;
}''',
                "flixel/group/FlxGroup.hx": '''package flixel.group;
import flixel.FlxBasic;
class FlxTypedGroup<T:FlxBasic> extends FlxBasic {
 public var members:Array<T>=[];
 public var maxSize:Int;
 public function new(?maxSize:Int=0) { super(); this.maxSize=maxSize; }
 public function add(value:T):T { members.push(value); return value; }
 public function insert(index:Int,value:T):T { members.insert(index,value); return value; }
 public function remove(value:T,splice:Bool=false):T { members.remove(value); return value; }
 public function forEach(callback:T->Void,recurse:Bool=false):Void { for(member in members) if(member!=null) callback(member); }
 public function getFirst(test:T->Bool):T { for(member in members) if(member!=null && test(member)) return member;return null; }
 public function recycle(?objectClass:Class<T>,?objectFactory:Void->T,force=false,revive=true):T {
  var value:T=objectFactory==null ? Type.createInstance(objectClass,[]) : objectFactory();
  return add(value);
 }
}
class FlxGroup extends FlxTypedGroup<FlxBasic> { public function new() super(); }''',
                "flixel/group/FlxSpriteGroup.hx": '''package flixel.group;
import flixel.FlxSprite;
typedef FlxSpriteGroup = FlxTypedSpriteGroup<FlxSprite>;
class FlxTypedSpriteGroup<T:FlxSprite> extends FlxSprite {
 public var group:flixel.group.FlxGroup.FlxTypedGroup<T>;
 public var members:Array<T>=[];
 public function new(x:Float=0,y:Float=0,?maxSize:Int=0) { super(x,y); }
 public function add(value:T):T { members.push(value); return value; }
 override public function update(elapsed:Float):Void for(member in members) if(member!=null) member.update(elapsed);
 override public function destroy():Void {
  if(members!=null) for(member in members) if(member!=null) member.destroy();
  members=null; super.destroy();
 }
}''',
                "flixel/tweens/FlxTween.hx": '''package flixel.tweens;
class FlxTween { public function new() {} }''',
                "flixel/util/FlxColor.hx": '''package flixel.util;
typedef FlxColor = Dynamic;''',
                "Main.hx": '''import hscript.ParserEx;
import hscript.ScriptClass;

class Main {
 static function main():Void {
  var scope = new hscript.ScriptClassScope();
  var probe:Dynamic = {updates:0,beats:0,steps:0,measures:0,destroys:0};
  scope.seed('probe',probe);
  scope.bindImport(['funkin','backend','MusicBeatGroup'],CodenameMusicBeatGroupCompat);
  var source = [
   'import funkin.backend.MusicBeatGroup;',
   'class RobloxTextbox extends MusicBeatGroup {',
   ' public function new(x:Float,y:Float){super(x,y);}',
   ' public function update(dt:Float):Void {probe.updates++;super.update(dt);}',
   ' public function beatHit(value:Int):Void {probe.beats++;super.beatHit(value);}',
   ' public function stepHit(value:Int):Void {probe.steps++;super.stepHit(value);}',
   ' public function measureHit(value:Int):Void {probe.measures++;super.measureHit(value);}',
   ' public function destroy():Void {probe.destroys++;super.destroy();}',
   '}'
  ].join('\\n');
  scope.registerModule(new ParserEx().parseModule(source));
  var script = scope.createInstance('RobloxTextbox',[14,27]);
  if(script==null) throw 'owner class did not instantiate';
  var native:CodenameMusicBeatGroupCompat=cast script.superClass;
  native.bindOwnerScript(cast script);
  var child = new flixel.ProbeSprite();
  native.add(child);
  native.update(0.016);
  if(probe.updates!=1 || child.updates!=1 || native.x!=14 || native.y!=27)
   throw 'native update did not dispatch the owner override and one guarded super call';
  native.beatHit(2); native.stepHit(8); native.measureHit(2);
  if(probe.beats!=1 || child.beats!=1 || probe.steps!=1 || child.steps!=1
   || probe.measures!=1 || child.measures!=1)
   throw 'owner beat hooks or MusicBeatGroup child forwarding failed';
  native.destroy();
  if(probe.destroys!=1 || child.destroys!=1 || native.destroys!=1)
   throw 'owner and native group teardown did not happen exactly once: '+probe.destroys+','+child.destroys+','+native.destroys;
  native.destroy();
  if(probe.destroys!=1 || child.destroys!=1 || native.destroys!=1)
   throw 'repeated teardown was not idempotent';
  var second = scope.createInstance('RobloxTextbox',[0,0]);
  var secondNative:CodenameMusicBeatGroupCompat=cast second.superClass;
  secondNative.bindOwnerScript(cast second);
  var secondChild = new flixel.ProbeSprite();
  secondNative.add(secondChild);
  secondNative.update(0.016);
  if(probe.updates!=2 || secondChild.updates!=1)
   throw 'second owner class was not independently attached';
  scope.release();
  secondNative.update(0.016);
  if(probe.updates!=2 || secondChild.updates!=2)
   throw 'released owner callback ran again or native children stopped updating';
  secondNative.destroy();
  if(probe.destroys!=1 || secondChild.destroys!=1 || secondNative.destroys!=1)
   throw 'inactive scope did not use native group teardown';
  Sys.println('MusicBeatGroup owner lifecycle ok');
 }
}''',
            }
            for relative, content in stubs.items():
                path = base / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline='\n')

            result = subprocess.run(
                [
                    *HAXE_COMMAND,
                    "-D",
                    "flixel",
                    "-cp",
                    str(ROOT / "source"),
                    "-cp",
                    str(ROOT / ".haxelib/hscript/2,5,0"),
                    "-cp",
                    str(ROOT / ".haxelib/hscript-ex/git/src"),
                    "-cp",
                    str(base),
                    "--run",
                    "Main",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("MusicBeatGroup owner lifecycle ok", result.stdout)

    def test_import_alias_and_constructor_attachment_are_shared(self):
        bindings = (ROOT / "source/CodenameImportBindings.hx").read_text(encoding="utf-8")
        interp = (ROOT / "source/CodenameScriptInterp.hx").read_text(encoding="utf-8")
        self.assertIn("bindings.set('funkin.backend.MusicBeatGroup', CodenameMusicBeatGroupCompat);", bindings)
        self.assertIn("bindings.set('flixel.util.FlxSpriteUtil', CodenameFlxSpriteUtilCompat.facade());", bindings)
        self.assertIn("bindings.set('flixel.FlxMath', FlxMath);", bindings)
        self.assertIn(".bindOwnerScript(cast scriptClass);", interp)


if __name__ == "__main__":
    unittest.main()
