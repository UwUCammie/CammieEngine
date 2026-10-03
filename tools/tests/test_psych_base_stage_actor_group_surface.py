"""Psych stage actor-group facade mirrors the used FlxSpriteGroup surface."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
FLIXEL_ARGS = [
    "-lib", "openfl", "-lib", "lime", "-lib", "flixel",
    "-D", "FLX_STANDARD_ASSETS_DIRECTORY", "-D", "FLX_DEFAULT_SOUND_EXT=ogg",
    "-D", "FLX_SOUND_SYSTEM", "-D", "FLX_GAMEINPUT_API",
]


class PsychBaseStageActorGroupSurfaceTest(unittest.TestCase):
    def test_group_transforms_members_and_retains_state_ownership(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            base = Path(folder)
            (base / "HxcCompatRuntime.hx").write_text(
                """class HxcCompatRuntime {
 static var values:haxe.ds.ObjectMap<Dynamic,Int> = new haxe.ds.ObjectMap();
 public static function getZIndex(value:Dynamic):Int return value == null || !values.exists(value) ? 0 : values.get(value);
 public static function setZIndex(value:Dynamic,index:Int):Void if (value != null) values.set(value,index);
}
""",
                encoding="utf-8",
             newline='\n')
            (base / "PsychGroupSurfaceProbe.hx").write_text(
                r'''import flixel.FlxSprite;
class PsychGroupSurfaceProbe {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var actor = new FlxSprite(117, 207);
  var members:Array<Dynamic> = [actor];
  var synchronizedCamera:Dynamic = null;
  var info:Dynamic = {x:100.0,y:200.0};
  var host:Dynamic = {
   gf:actor,
   curStage:{gfInfo:info},
   members:members,
   add:function(value:Dynamic):Dynamic { members.push(value); return value; },
   insert:function(index:Int,value:Dynamic):Dynamic { members.insert(index,value); return value; },
   remove:function(value:Dynamic,splice:Bool=false):Dynamic { members.remove(value); return value; },
   setPsychStageGroupCameras:function(role:String,value:Array<Dynamic>):Void {
    synchronizedCamera = value == null || value.length == 0 ? null : value[0];
    actor.cameras = cast value;
   },
   syncPsychStageGroupAnchor:function(_role:String,_axis:String,_value:Float):Void {}
  };
  var group = new PsychBaseStageActorGroupCompat(host,'gf');
  check(group.members.length == 1 && group.members[0] == actor,'active actor missing from members');
  group.visible = false;
  check(!actor.visible,'group visibility did not reach actor');
  group.visible = true;
  check(actor.visible,'group visibility did not restore actor');
  group.scrollFactor.set(0.7,0.6);
  check(actor.scrollFactor.x == 0.7 && actor.scrollFactor.y == 0.6,'scrollFactor.set did not reach actor');
  var camera:Dynamic = {name:'hud'};
  group.camera = camera;
  check(group.camera == camera && synchronizedCamera == camera,'camera assignment did not synchronize');
  group.zIndex = 5;
  check(group.zIndex == 5,'zIndex facade did not update');

  var child = new FlxSprite(2,3);
  child.visible = false;
  check(group.add(child) == child,'add did not return its child');
  check(child.x == 102 && child.y == 203,'add did not apply group anchor');
  check(group.members.length == 2 && group.members[1] == child,'added child missing from members');
  check(members.length == 2 && members[1] == child,'added child missing from host state');
  check(child.scrollFactor.x == 0.7 && child.scrollFactor.y == 0.6,'add did not inherit scroll factor');
  check(child.cameras != null && child.cameras.length == 1 && child.cameras[0] == camera,'add did not inherit camera');
  check(!child.visible,'default group visibility revealed an authored-hidden child');

  group.x = 125;
  group.y = 230;
  check(actor.x == 142 && actor.y == 237,'group translation changed actor offset');
  check(child.x == 127 && child.y == 233,'group translation did not move child');
  check(group.remove(child, true) == child,'remove did not return its child');
  check(group.members.length == 1 && members.length == 1,'remove left child in group or state');
  check(child.exists,'removing a child destroyed state-owned object');
  var visibleChild = new FlxSprite(0,0);
  group.visible = false;
  check(group.add(visibleChild) == visibleChild && !visibleChild.visible,
   'invisible flattened group did not hide a subsequently-added child');
  group.clear();
  check(members.length == 0 && actor.exists,'clear destroyed a cached actor instead of removing state membership');
 }
}''',
                encoding="utf-8",
             newline='\n')
            env = dict(os.environ)
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
            env["PATH"] = os.pathsep.join(
                [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
            )
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(base), "-cp", str(ROOT / "source"),
                 *FLIXEL_ARGS, "--run", "PsychGroupSurfaceProbe"],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_nmv_character_group_keeps_character_api_separate(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            base = Path(folder)
            (base / "HxcCompatRuntime.hx").write_text(
                """class HxcCompatRuntime {
 static var values:haxe.ds.ObjectMap<Dynamic,Int> = new haxe.ds.ObjectMap();
 public static function getZIndex(value:Dynamic):Int return value == null || !values.exists(value) ? 0 : values.get(value);
 public static function setZIndex(value:Dynamic,index:Int):Void if (value != null) values.set(value,index);
}
""",
                encoding="utf-8",
             newline='\n')
            (base / "NightmareVisionGroupProbe.hx").write_text(
                r'''import flixel.math.FlxPoint;
class NightmareVisionGroupProbe {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var initial:Dynamic = {x:10.0,y:20.0,alpha:1.0,visible:true,cameras:null,
   scrollFactor:new FlxPoint(1,1),requestedCharacter:'bf',curCharacter:'bf'};
  var members:Array<Dynamic>=[initial];
  var host:Dynamic={
   boyfriend:initial,
   curStage:{bfInfo:{x:10.0,y:20.0}},
   members:members,
   add:function(value:Dynamic):Dynamic { members.push(value); return value; },
   insert:function(index:Int,value:Dynamic):Dynamic { members.insert(index,value); return value; },
   remove:function(value:Dynamic,splice:Bool=false):Dynamic { members.remove(value); return value; },
   setPsychStageGroupCameras:function(_role:String,_value:Array<Dynamic>):Void {},
   syncPsychStageGroupAnchor:function(_role:String,_axis:String,_value:Float):Void {}
  };
  var bank:NightmareVisionCharacterBank=null;
  var parentWrites=0;
  var group=new NightmareVisionCharacterGroupCompat(host,'bf',function() return bank,
   null,function(value:Dynamic):Dynamic { parentWrites++; return value; });
  check(group.members.length==1 && group.parent==initial,'pre-bank group read failed');
  group.type=0;
  check(group.type==0 && !group.gfCheck,'role metadata mismatch');
  bank=new NightmareVisionCharacterBank(initial,function(name:String):Dynamic {
   var character:Dynamic={x:0.0,y:0.0,alpha:1.0,visible:true,cameras:null,
    scrollFactor:new FlxPoint(1,1),requestedCharacter:name,curCharacter:name};
   // PlayState owns the actor directly; authored character setup writes its
   // per-character factor after construction and before the proxy observes it.
   members.push(character);
   character.scrollFactor.set(0.95,0.95);
   return character;
  },function(_old:Dynamic,next:Dynamic):Void { host.boyfriend=next; });
  var cached=group.addToList('mobian_bf',0);
  check(cached!=null && cached.alpha==0.00001,'addToList did not construct/cache a hidden actor');
  check(cached.scrollFactor.x==0.95 && cached.scrollFactor.y==0.95,
   'construction did not retain the authored per-character scroll factor');
  check(group.map.get('mobian_bf')==cached && group.members.contains(cached),'cache map/member view mismatch');
  check(cached.scrollFactor.x==0.95 && cached.scrollFactor.y==0.95,
   'lazy group observation clobbered the authored per-character scroll factor');
  group.scrollFactor.set(0.5,0.5);
  check(cached.scrollFactor.x==0.5 && cached.scrollFactor.y==0.5,
   'explicit group scrollFactor.set did not override observed cached members');
  var directParent:Dynamic={requestedCharacter:'direct',curCharacter:'direct'};
  group.parent=directParent;
  check(group.parent==directParent && parentWrites==1 && host.boyfriend==initial,
   'parent assignment activated or alpha-transferred a character');
  group.parent=initial;
  check(group.change('mobian_bf')==cached && group.parent==cached,'change did not activate the cached actor');
  var extra:Dynamic={x:0.0,y:0.0,alpha:1.0,visible:true,cameras:null,
   scrollFactor:new FlxPoint(1,1),requestedCharacter:'cutscene',curCharacter:'cutscene'};
  check(group.addChar(extra)==extra && group.map.get('cutscene')==extra,'addChar did not cache the supplied actor');
 }
}''',
                encoding="utf-8",
             newline='\n')
            env = dict(os.environ)
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["LD_LIBRARY_PATH"] = str(ROOT / ".tools/neko")
            env["PATH"] = os.pathsep.join(
                [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
            )
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(base), "-cp", str(ROOT / "source"),
                 *FLIXEL_ARGS, "--run", "NightmareVisionGroupProbe"],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
