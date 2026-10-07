"""Owner-isolated Psych 1.0.4 achievements service and class binding checks."""
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND, TEST_TMP
from tools.haxe_flixel_math_stubs import write_flixel_point_stub

ROOT = Path(__file__).resolve().parents[2]
IRIS = ROOT / ".haxelib/hscript-iris/1,1,3"


class PsychAchievementsTest(unittest.TestCase):
    def test_service_tracks_donor_api_without_native_global_save_or_mod_state(self):
        source = (ROOT / "source/PsychAchievements.hx").read_text(encoding="utf-8")
        bindings = (ROOT / "source/PsychAchievementsBindings.hx").read_text(encoding="utf-8")
        host = (ROOT / "source/PsychAchievementsHost.hx").read_text(encoding="utf-8")
        for contract in (
            "public var achievements:Map<String, PsychAchievementInfo>",
            "public var variables:Map<String, Float>",
            "public var achievementsUnlocked:Array<String>",
            "public function init():Void",
            "public function get(name:String)",
            "public function exists(name:String)",
            "public function load():Void",
            "public function save():Void",
            "public function getScore(name:String)",
            "public function setScore(name:String",
            "public function addScore(name:String",
            "public function unlock(name:String",
            "public function isUnlocked(name:String)",
            "public function reloadList():Void",
            "public function createAchievement(name:String",
            "public var showingPopups(get, never):Bool",
        ):
            self.assertIn(contract, source)
        self.assertIn("'backend.Achievements'", bindings)
        self.assertIn("scope.bindRuntimeClass", bindings)
        self.assertIn("host.achievementSources()", source)
        self.assertNotIn("Mods.currentModDirectory", source)
        self.assertNotIn("FlxG.save", source)
        self.assertIn("PsychAchievementInfo", host)

    def test_owner_state_reload_scoring_popup_and_source_class_reflection(self):
        fixture = r'''
import haxe.ds.StringMap;
import PsychAchievementInfo;
import PsychAchievementsHost.PsychAchievementSource;

class OwnerSave {
 public var fields:Map<String,Dynamic> = new Map();
 public var writes:Array<String> = [];
 public var reads:Array<String> = [];
 public var flushes:Int = 0;
 public function new() {}
 public function getField(name:String):Dynamic {
  reads.push(name); var value=fields.get(name);
  return value == null ? null : haxe.Json.parse(haxe.Json.stringify(value));
 }
 public function setField(name:String,value:Dynamic):Dynamic {
  writes.push(name); fields.set(name,haxe.Json.parse(haxe.Json.stringify(value))); return value;
 }
 public function flush():Void flushes++;
}
class OwnerHooks {
 public var active:Bool=true; public var now:Int=1000; public var popupActive:Bool=false;
 public var sounds:Array<String>=[]; public var reports:Array<String>=[];
 public var popupIDs:Array<String>=[]; public var popupInfo:Array<Dynamic>=[];
 public var texts:Map<String,String>=new Map(); public var sources:Array<PsychAchievementSource>=[];
 public function new() {}
 public function host(root:String):PsychAchievementsHost {
  var paths:Dynamic={}; Reflect.setField(paths,'__sourceOwnerRoot',function() return root);
  return {ownerActive:function() return active,paths:paths,
   achievementSources:function() return sources,
   readText:function(path:String):Null<String> return texts.get(path),
   report:function(message:String) reports.push(message),
   playConfirmSound:function(key:String,volume:Float) sounds.push(key+':'+volume),
   nowMillis:function() return now,
   showingPopups:function() return popupActive,
   showPopup:function(id:String,info:PsychAchievementInfo,endFunc:Void->Void) {
    popupIDs.push(id); popupInfo.push(info);
   }};
 }
}
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function expectThrow(fn:Void->Void,fragment:String):Void {
  var caught=false; try fn() catch(error:Dynamic) caught=Std.string(error).indexOf(fragment)>=0;
  check(caught,'expected exception containing '+fragment);
 }
 static function main():Void {
  var rootA='assets/imported_mods/psych-a'; var rootB='assets/imported_mods/psych-b';
  var saveA=new OwnerSave(); var saveB=new OwnerSave();
  var hooksA=new OwnerHooks(); var hooksB=new OwnerHooks();
  hooksA.sources=[{path:'a/base',mod:null},{path:'a/one',mod:'one'},
   {path:'a/broken',mod:'broken'},{path:'a/two',mod:'two'}];
  hooksA.texts.set('a/base','[{"save":"custom","name":"Base Custom","description":"From base"}]');
  hooksA.texts.set('a/one','[{"save":"scored","name":"Progress","description":"Count it","maxScore":2},null,{"name":"Missing key"}]');
  hooksA.texts.set('a/broken','[');
  hooksA.texts.set('a/two','[{"save":"custom","name":"Duplicate","description":"Ignored"},{"save":"mod-two","name":"Second Mod","description":"Two"}]');
  var hostA=hooksA.host(rootA); var hostB=hooksB.host(rootB);
  var serviceA=new PsychAchievements(rootA,saveA,hostA);
  var serviceB=new PsychAchievements(rootB,saveB,hostB);
  serviceA.init(); serviceB.init();
  check(serviceA.achievements.exists('friday_night_play') && serviceA.get('friday_night_play').hidden,
   'init installs the source Friday achievement and its hidden flag');
  check(serviceA.achievements.exists('ur_bad') && serviceA.achievements.exists('ur_good')
   && serviceA.achievements.exists('oversinging') && serviceA.achievements.exists('hype')
   && serviceA.achievements.exists('two_keys') && serviceA.achievements.exists('toastie')
   && serviceA.achievements.exists('pessy_easter_egg'),
   'init installs the Psych core defaults when base-game compile flags are absent');
  serviceA.reloadList();
  check(serviceA.get('custom').name=='Base Custom' && serviceA.get('custom').ID==8
   && serviceA.get('custom').mod==null,
   'base JSON follows default IDs and remains unowned by a mod');
  check(serviceA.get('scored').maxScore==2 && serviceA.get('scored').ID==9
   && serviceA.get('scored').mod=='one',
   'the ordered first enabled mod is recorded on source achievement metadata');
  check(serviceA.get('mod-two').ID==10 && serviceA.get('mod-two').mod=='two'
   && serviceA.get('custom').name=='Base Custom',
   'later mod entries keep order and duplicate save keys are ignored');
  check(hooksA.reports.length==3 && hooksA.reports[0].indexOf('Achievement #2 is invalid.')>=0
   && hooksA.reports[1].indexOf('Missing valid "save" value.')>=0
   && hooksA.reports[2].indexOf('Error loading achievements.json:')>=0,
   'invalid entries and malformed JSON report while later ordered files continue');

  // A changed enabled list removes the previous mod entries and only reads
  // paths supplied by this owner host.
  hooksA.sources=[{path:'a/base2',mod:null},{path:'a/next',mod:'next'}];
  hooksA.texts.set('a/base2','[{"save":"custom","name":"Current Base","description":"reload"}]');
  hooksA.texts.set('a/next','[{"save":"next-achievement","name":"Next","description":"enabled"}]');
  serviceA.reloadList();
  check(!serviceA.exists('scored') && !serviceA.exists('mod-two') && serviceA.exists('next-achievement')
   && serviceA.get('custom').name=='Base Custom',
   'reloadList drops prior mod records while preserving duplicate base records');

  serviceA.createAchievement('score_test',{name:'Score',description:'Progress',maxScore:2});
  check(serviceA.getScore('score_test')==0 && !saveA.fields.exists('achievementsVariables'),
   'a score read initializes the live value without persisting it');
  serviceA.setScore('score_test',1,false);
  check(serviceA.getScore('score_test')==1 && saveA.fields.exists('achievementsVariables')
   && saveA.flushes==0,
   'setScore writes owner state while saveIfNotUnlocked false skips an explicit flush');
  serviceA.addScore('score_test');
  check(serviceA.getScore('score_test')==2 && serviceA.isUnlocked('score_test')
   && hooksA.sounds.length==1 && hooksA.sounds[0]=='confirmMenu:0.5'
   && hooksA.popupIDs.join(',')=='score_test'
   && hooksA.popupInfo[0].name=='Score',
   'reaching maxScore unlocks, clamps, plays the source sound, saves, and sends popup metadata');
  check(saveA.flushes==2,
   'unlock flushes once and score update performs the source post-save flush');
  check(serviceA.addScore('score_test')==2,
   'an already-unlocked score returns the configured maxScore');
  serviceA.createAchievement('manual_unlock',{name:'Manual',description:'No popup'});
  check(serviceA.unlock('manual_unlock',false)=='manual_unlock'
   && serviceA.unlock('manual_unlock',false)==null && hooksA.popupIDs.length==1,
   'unlock can suppress the popup and repeated unlocks return null');
  hooksA.popupActive=true;
  check(serviceA.showingPopups,'showingPopups delegates to the captured owner popup manager');

  // JSON-restored owner maps are typed, isolated, and continue supporting live writes.
  saveA.fields.set('achievementsUnlocked',['custom']);
  saveA.fields.set('achievementsVariables',{persisted:3.5});
  var restored=new PsychAchievements(rootA,saveA,hostA);
  restored.load();
  check(restored.isUnlocked('custom') && restored.variables.get('persisted')==3.5
   && Std.isOfType(restored.variables,StringMap),
   'load restores the source fields into live owner-local collections');
  restored.variables.set('direct-write',7);
  restored.save();
  check(saveA.fields.exists('achievementsUnlocked') && saveA.fields.exists('achievementsVariables'),
   'save writes the donor field names through the private owner save adapter');
  check(serviceB.achievementsUnlocked.length==0 && !serviceB.variables.exists('persisted')
   && !saveB.fields.exists('achievementsVariables'),
   'another imported owner cannot read or mutate this achievement save');

  var unknownRejected=false;
  try serviceA.unlock('missing') catch(_ :Dynamic) unknownRejected=true;
  check(unknownRejected && hooksA.reports[hooksA.reports.length-1].indexOf('does not exists!')>=0,
   'unlock reports then throws for an unknown save key');
  var disabledScoreRejected=false;
  try serviceA.getScore('custom') catch(error:Dynamic)
   disabledScoreRejected=Std.string(error).indexOf('score disabled')>=0;
  check(disabledScoreRejected,'score calls reject achievements without a positive maxScore');

  // The source static class token remains the same native type but its maps and
  // calls resolve through this interpreter's service and release guard.
  var interp=new NightmareVisionScriptInterp();
  var active=true; var requireActive:Void->Void=function():Void if(!active) throw 'owner inactive';
  PsychAchievementsBindings.install(interp,serviceA,requireActive);
  var parser=new NightmareVisionScriptParser();
  interp.execute(parser.parseString('import Type; import Reflect; import backend.Achievements as Ach; '
   +'resolved=Type.resolveClass("backend.Achievements"); '
   +'shortResolved=Type.resolveClass("Achievements"); '
   +'resolvedName=Type.getClassName(resolved); '
   +'hasMap=Reflect.hasField(Ach,"achievements"); '
   +'fieldList=Reflect.fields(Ach); classFields=Type.getClassFields(Ach); '
   +'scriptScore=Ach.getScore("script-score"); Ach.createAchievement("script-score",'
   +'{name:"Script Score",description:"from HScript",maxScore:4}); '
   +'Ach.addScore("script-score",1); direct=Ach.achievements.get("script-score").name; '
   +'capturedMethod=Ach.getScore; reflectedMethod=Reflect.field(Ach,"getScore"); '
   +'reflectedValue=Reflect.callMethod(Ach,reflectedMethod,["script-score"]);',
   'psych-achievements-owner'));
  check(interp.variables.get('resolved')==PsychAchievements
   && interp.variables.get('shortResolved')==PsychAchievements
   && interp.variables.get('resolvedName')=='backend.Achievements'
   && interp.variables.get('hasMap')==true,
   'Type import and direct Reflect access keep the real scoped class identity');
  check((cast interp.variables.get('fieldList'):Array<String>).indexOf('reloadList')>=0
   && (cast interp.variables.get('classFields'):Array<String>).indexOf('showingPopups')>=0,
   'Reflect.fields and Type.getClassFields discover bound source statics');
  check(interp.variables.get('scriptScore')==-1 && interp.variables.get('direct')=='Script Score'
   && interp.variables.get('reflectedValue')==1 && serviceA.getScore('script-score')==1,
   'the imported static API reads and mutates only its owner service');
  active=false;
  var guarded=false;
  try interp.execute(parser.parseString('inactive=Ach.achievements;','psych-achievements-inactive'))
  catch(_ :Dynamic) guarded=true;
  var capturedGuarded=false;
  try Reflect.callMethod(null,interp.variables.get('capturedMethod'),['script-score'])
  catch(_ :Dynamic) capturedGuarded=true;
  check(guarded && capturedGuarded,
   'static reads and previously captured method handles enforce the owner guard');

  var luaScope=new SourceNativeClassScope(); luaScope.installReflectionBindings();
  var luaActive=true; var requireLua:Void->Void=function():Void if(!luaActive) throw 'Lua owner inactive';
  serviceB.createAchievement('lua-score',{name:'Lua score',description:'owner B',maxScore:3});
  PsychAchievementsBindings.installScope(luaScope,serviceB,requireLua);
  var luaToken=luaScope.resolveClass('backend.Achievements');
  var luaShort=luaScope.resolveClass('Achievements');
  var luaAdd:Dynamic=luaScope.read(luaToken,'addScore');
  Reflect.callMethod(luaToken,luaAdd,['lua-score',2]);
  check(luaToken==luaShort && serviceB.getScore('lua-score')==2,
   'the shared native class scope serves Lua class reflection from the same owner service');
  luaActive=false;
  var luaGuarded=false;
  try Reflect.callMethod(luaToken,luaAdd,['lua-score',1]) catch(_ :Dynamic) luaGuarded=true;
  check(luaGuarded,'the shared scope method handle checks its captured source guard on call');
  luaScope.release();
  serviceA.release();
  var released=false;
  try serviceA.exists('custom') catch(_ :Dynamic) released=true;
  check(released,'released services reject retained calls');
  interp.release(); restored.release(); serviceB.release();
 }
}
'''
        runtime_stub = r'''
class HxcCompatRuntime {
 static var targets:Array<Dynamic>=[]; static var values:Array<Int>=[];
 static function find(target:Dynamic):Int return targets.indexOf(target);
 public static function clear():Void {targets.resize(0);values.resize(0);}
 public static function getZIndex(target:Dynamic):Dynamic {var i=find(target);return i<0?0:values[i];}
 public static function setZIndex(target:Dynamic,value:Dynamic,?op:String='='):Dynamic {
  var next=Std.int(Std.parseFloat(Std.string(value)));var i=find(target);
  if(i<0){targets.push(target);values.push(next);}else values[i]=next;return next;
 }
}
'''
        with tempfile.TemporaryDirectory(prefix="psych-achievements-", dir=TEST_TMP) as scratch:
            scratch = Path(scratch)
            write_flixel_point_stub(scratch)
            (scratch / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            (scratch / "HxcCompatRuntime.hx").write_text(runtime_stub, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(IRIS), "-cp", str(scratch),
                 "-cp", str(ROOT / ".haxelib/tjson/1,4,0"),
                 "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
