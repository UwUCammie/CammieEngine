"""Behavior of Psych's six Lua achievement callbacks over the owner service."""
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND, TEST_TMP

ROOT = Path(__file__).resolve().parents[2]
HSCRIPT = ROOT / ".haxelib/hscript/2,7,0"


class PsychAchievementsLuaBindingsTest(unittest.TestCase):
    def test_lua_callbacks_keep_donor_defaults_failures_and_owner_isolation(self):
        fixture = r'''
import hscript.Interp;
import PsychAchievementInfo;

class OwnerSave {
 public var fields:Map<String,Dynamic>=new Map();
 public var writes:Array<String>=[];
 public var flushes:Int=0;
 public function new() {}
 public function getField(name:String):Dynamic {
  var value=fields.get(name);
  return value==null?null:haxe.Json.parse(haxe.Json.stringify(value));
 }
 public function setField(name:String,value:Dynamic):Dynamic {
  writes.push(name);fields.set(name,haxe.Json.parse(haxe.Json.stringify(value)));return value;
 }
 public function flush():Void flushes++;
}
class OwnerHooks {
 public var active:Bool=true; public var now:Int=1000; public var sounds:Array<String>=[];
 public var reports:Array<String>=[]; public var popups:Array<String>=[];
 public function new() {}
 public function host(root:String):PsychAchievementsHost {
  var paths:Dynamic={};Reflect.setField(paths,'__sourceOwnerRoot',function() return root);
  return {ownerActive:function() return active,paths:paths,
   achievementSources:function() return [],readText:function(_path:String):Null<String> return null,
   report:function(message:String) reports.push(message),
   playConfirmSound:function(key:String,volume:Float) sounds.push(key+':'+volume),
   nowMillis:function() return now,showingPopups:function() return popups.length>0,
   showPopup:function(id:String,info:PsychAchievementInfo,_endFunc:Void->Void) popups.push(id)};
 }
}
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function invoke(interp:Interp,name:String,args:Array<Dynamic>):Dynamic {
  var callback:Dynamic=interp.variables.get(name);
  if(!Reflect.isFunction(callback)) throw 'missing registered Lua callback '+name;
  return Reflect.callMethod(null,callback,args);
 }
 static function main():Void {
  var callbacks=['getAchievementScore','setAchievementScore','addAchievementScore',
   'unlockAchievement','isAchievementUnlocked','achievementExists'];
  var saveA=new OwnerSave();var saveB=new OwnerSave();
  var hooksA=new OwnerHooks();var hooksB=new OwnerHooks();
  var rootA='assets/imported_mods/psych-lua-a';var rootB='assets/imported_mods/psych-lua-b';
  var serviceA=new PsychAchievements(rootA,saveA,hooksA.host(rootA));
  var serviceB=new PsychAchievements(rootB,saveB,hooksB.host(rootB));
  serviceA.init();serviceB.init();
  serviceA.createAchievement('progress',{name:'Progress',description:'A',maxScore:3});
  serviceB.createAchievement('progress',{name:'Progress B',description:'B',maxScore:3});
  var interpA=new Interp();var interpB=new Interp();
  var luaReportsA:Array<String>=[];var luaReportsB:Array<String>=[];
  PsychAchievementsLuaBindings.install(interpA,serviceA,function(message:String) luaReportsA.push(message));
  PsychAchievementsLuaBindings.install(interpB,serviceB,function(message:String) luaReportsB.push(message));
  for(name in callbacks) check(Reflect.isFunction(interpA.variables.get(name)),
   'the donor Lua name must be registered: '+name);

  check(invoke(interpA,'getAchievementScore',['progress'])==0
   && !saveA.fields.exists('achievementsVariables'),
   'getAchievementScore initializes the source counter without saving');
  check(invoke(interpA,'setAchievementScore',['progress'])==0
   && serviceA.variables.get('progress')==0 && saveA.flushes==1,
   'setAchievementScore defaults value to zero and saveIfNotUnlocked to true');
  check(invoke(interpA,'addAchievementScore',['progress'])==1
   && serviceA.variables.get('progress')==1 && saveA.flushes==2,
   'addAchievementScore defaults value to one and saveIfNotUnlocked to true');
  check(invoke(interpA,'setAchievementScore',['progress',2,false])==2
   && saveA.flushes==2,
   'setAchievementScore forwards the explicit no-flush preference');
  check(invoke(interpA,'addAchievementScore',['progress'])==3
   && serviceA.isUnlocked('progress') && hooksA.popups.join(',')=='progress'
   && invoke(interpA,'isAchievementUnlocked',['progress'])==true,
   'wrappers delegate threshold unlock and the source default popup behavior');
  check(invoke(interpA,'getAchievementScore',['progress'])==3,
   'getAchievementScore returns maxScore after the service unlocks the record');

  check(invoke(interpA,'getAchievementScore',['missing'])==-1
   && invoke(interpA,'setAchievementScore',['missing'])==-1
   && invoke(interpA,'addAchievementScore',['missing'])==-1,
   'the three missing score callbacks return minus one');
  check(invoke(interpA,'unlockAchievement',['missing'])==null
   && invoke(interpA,'isAchievementUnlocked',['missing'])==null
   && invoke(interpA,'achievementExists',['missing'])==false,
   'missing unlock and unlocked checks return null, while exists returns false');
  check(luaReportsA.join('|')==[
   'getAchievementScore: Couldnt find achievement: missing',
   'setAchievementScore: Couldnt find achievement: missing',
   'addAchievementScore: Couldnt find achievement: missing',
   'unlockAchievement: Couldnt find achievement: missing',
   'isAchievementUnlocked: Couldnt find achievement: missing'].join('|'),
   'only the five source-logged missing callbacks report diagnostics');

  check(invoke(interpB,'getAchievementScore',['progress'])==0
   && serviceB.get('progress').name=='Progress B' && serviceA.get('progress').name=='Progress',
   'two Lua scopes share callback names but keep independent achievement services');
  hooksA.active=false;
  var inactive=false;
  try invoke(interpA,'getAchievementScore',['progress']) catch(_ :Dynamic) inactive=true;
  check(inactive,'registered closures validate the owner through the service on every call');
  interpA.variables.clear();interpB.variables.clear();
  serviceA.release();serviceB.release();
 }
}
'''
        with tempfile.TemporaryDirectory(prefix="psych-achievements-lua-", dir=TEST_TMP) as scratch:
            scratch = Path(scratch)
            (scratch / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(HSCRIPT), "-cp", str(scratch),
                 "-cp", str(ROOT / ".haxelib/tjson/1,4,0"), "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
