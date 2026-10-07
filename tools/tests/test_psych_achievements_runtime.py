"""Compile the owner-pool adapter against narrow platform/popup stubs."""
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND, TEST_TMP

ROOT = Path(__file__).resolve().parents[2]
TJSON = ROOT / ".haxelib/tjson/1,4,0"


class PsychAchievementsRuntimeTest(unittest.TestCase):
    def test_factory_contract_keeps_lifecycle_out_of_playstate(self):
        source = (ROOT / "source/PsychAchievementsRuntime.hx").read_text(encoding="utf-8")
        self.assertIn("static function adopt(", source)
        self.assertIn("public static function retainOwners(roots:Array<String>)", source)
        self.assertIn("public static function releaseAll()", source)
        self.assertIn("PsychOwnerAssetPath.withinOwner(ownerRoot, path)", source)
        self.assertIn("authorizedSourcePaths.get", source)
        self.assertIn("var antialiasing:Void->Bool", source)
        self.assertIn("#if windows", source)
        self.assertIn("#if sys\nimport sys.FileSystem;", source)
        self.assertNotIn("PlayState", source)

    def test_per_owner_runtime_reuse_sources_popup_and_retirement(self):
        if not Path(HAXE_COMMAND[0]).is_file() or not TJSON.is_dir():
            raise unittest.SkipTest("portable Haxe or pinned TJSON is unavailable")

        main = r'''package;
import openfl.display.Sprite;
import openfl.display.Stage;
import PsychAchievementInfo;
import PsychAchievementPopup.PsychAchievementPopupAssets;
import PsychAchievementsHost.PsychAchievementSource;
import PsychAchievementsRuntime.PsychAchievementsRuntimeContext;

class RuntimeFixtureMain {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main():Void {
  var args=Sys.args();
  var rootA=args[0]; var rootB=args[1]; var outside=args[2];
  var basePath=rootA+'/data/achievements.json';
  var modPath=rootA+'/mods/not-enabled/achievements.json';
  var reads:Array<String>=[]; var reports:Array<String>=[]; var sounds:Array<String>=[];
  var aaA=true;
  var ownerAPaths:Dynamic={}; Reflect.setField(ownerAPaths,'__sourceOwnerRoot',function() return rootA);
  var ownerBPaths:Dynamic={}; Reflect.setField(ownerBPaths,'__sourceOwnerRoot',function() return rootB);
  var asset:PsychAchievementPopupAssets={
   fileExists:function(path:String):Bool return false,
   image:function(key:String):Dynamic return null,
   font:function(key:String):String return 'owner/fonts/'+key
  };
  var assetsA:Map<String,PsychAchievementPopupAssets>=new Map(); assetsA.set('',asset);
  var assetsB:Map<String,PsychAchievementPopupAssets>=new Map(); assetsB.set('',asset);
  var contextA:PsychAchievementsRuntimeContext={
   sources:[{path:basePath,mod:null},{path:outside,mod:null},{path:modPath,mod:'not-enabled'}],
   readText:function(path:String):Null<String> {reads.push(path);return sys.io.File.getContent(path);},
   report:function(message:String):Void reports.push(message),
   playConfirmSound:function(key:String,volume:Float):Void sounds.push(key+':'+volume),
   assetFacades:assetsA, phrase:function(key:String,fallback:String):String return 'phrase:'+fallback,
   antialiasing:function():Bool return aaA,stage:new Stage(),game:new Sprite()
  };
  var contextB:PsychAchievementsRuntimeContext={
   sources:[],readText:function(path:String):Null<String> return null,
   report:function(message:String):Void {},
   playConfirmSound:function(key:String,volume:Float):Void {},
   assetFacades:assetsB,phrase:function(key:String,fallback:String):String return fallback,
   antialiasing:function():Bool return false,stage:new Stage(),game:new Sprite()
  };

  var saveA=new CodenameOwnerSaveData(rootA);
  var saveB=new CodenameOwnerSaveData(rootB);
  var first=PsychAchievementsRuntime.adopt(rootA,ownerAPaths,saveA,contextA);
  check(first.service.exists('from_base') && first.service.get('from_base').name=='From retained JSON',
   'the runtime must initialize and load the caller-authorized base JSON after entering the owner pool');
  check(reads.length==1 && StringTools.replace(reads[0],String.fromCharCode(92),'/').toLowerCase()==basePath.toLowerCase(),
   'only the authenticated owner base file should be read: '+reads.join('|')+' expected '+basePath);
  check(reports.length==2 && reports[0].indexOf('outside the captured owner')>=0
   && reports[1].indexOf('authorized asset facade')>=0,
   'out-of-owner files and unseeded mod sources should be refused and reported');
  var ownerMismatch=false;
  try PsychAchievementsRuntime.adopt(rootA,ownerBPaths,saveA,contextA)
  catch(error:Dynamic) ownerMismatch=Std.string(error).indexOf('does not match')>=0;
  check(ownerMismatch && !first.released,
   'a captured Paths facade for a different owner must fail without disturbing the existing service');
  var invalidRetainSet=false;
  try PsychAchievementsRuntime.retainOwners([outside])
  catch(_ :Dynamic) invalidRetainSet=true;
  check(invalidRetainSet && !first.released,
   'an invalid retained-owner set must be rejected before releasing any active provider');

  var alternateContext:PsychAchievementsRuntimeContext={
   sources:[],readText:function(path:String):Null<String> return null,
   report:function(message:String):Void {},playConfirmSound:function(key:String,volume:Float):Void {},
   assetFacades:assetsA,phrase:function(key:String,fallback:String):String return fallback,
   antialiasing:function():Bool return false,stage:new Stage(),game:new Sprite()
  };
  var reused=PsychAchievementsRuntime.adopt(rootA,ownerAPaths,new CodenameOwnerSaveData(rootA),alternateContext);
  check(reused==first && reads.length==1 && first.service.exists('from_base'),
   'same-owner transitions must reuse maps, captured services, and popup manager without reloading');

  first.service.createAchievement('runtime_popup',{name:'Runtime popup',description:'owned'});
  check(first.service.unlock('runtime_popup',false)=='runtime_popup'
   && sounds.join(',')=='confirmMenu:0.5',
   'achievement unlock should continue using this owner runtime audio callback');
  first.service.startPopup('runtime_popup');
  aaA=false;
  first.service.startPopup('runtime_popup');
  check(first.popupCount==2 && first.service.showingPopups
   && PsychAchievementPopup.antialiasingValues.join(',')=='true,false',
   'each popup should read the current owner antialiasing preference through the captured live callback');

  var second=PsychAchievementsRuntime.adopt(rootB,ownerBPaths,saveB,contextB);
  check(second!=first && second.service.exists('friday_night_play'),
   'a second imported provider gets a distinct service and save view');
  PsychAchievementsRuntime.retainOwners([rootB]);
  check(first.released && first.popupCount==0 && PsychAchievementPopup.created==2
   && PsychAchievementPopup.destroyed==2,
   'retiring one owner removes only its popup and owner service');
  check(!second.released && second.service.exists('friday_night_play'),
   'the retained provider must remain usable when another owner retires');
  PsychAchievementsRuntime.releaseAll();
  check(second.released,'releaseAll retires the remaining distinct owner service');
  PsychAchievementsRuntime.releaseAll();
 }
}
'''
        stubs = {
            "openfl/Lib.hx": "package openfl; class Lib { public static function getTimer():Int return 1000; }\n",
            "openfl/display/Sprite.hx": r'''package openfl.display;
class Sprite { public var children:Array<Sprite>=[]; public function new() {}
 public function addChild(child:Sprite):Sprite {children.push(child);return child;}
 public function removeChild(child:Sprite):Sprite {children.remove(child);return child;}
 public function contains(child:Sprite):Bool return children.indexOf(child)>=0;
}
''',
            "openfl/display/Stage.hx": "package openfl.display; class Stage extends Sprite { public function new() super(); }\n",
            "PsychAchievementPopup.hx": r'''package;
import openfl.display.Sprite;
import openfl.display.Stage;
import PsychAchievementInfo;
typedef PsychAchievementPopupAssets={var fileExists:String->Bool;var image:String->Dynamic;var font:String->String;}
typedef PsychAchievementPopupHost={var ownerRoot:String;var assetsForAchievementMod:Null<String>->PsychAchievementPopupAssets;
 var antialiasing:Void->Bool;var phrase:String->String->String;var stage:Stage;var game:Sprite;
 var now:Void->Float;var ownerActive:Void->Bool;var registerPopup:PsychAchievementPopup->Void;
 var unregisterPopup:PsychAchievementPopup->Void;}
class PsychAchievementPopup {
 public static var created:Int=0; public static var destroyed:Int=0;
 public static var antialiasingValues:Array<Bool>=[];
 public var intendedY:Float=0; var host:PsychAchievementPopupHost; var done:Bool=false;
 public function new(id:String,end:Void->Void,info:PsychAchievementInfo,host:PsychAchievementPopupHost) {
  this.host=host;created++;antialiasingValues.push(host.antialiasing());host.registerPopup(this);
 }
 public function destroy():Void {if(done)return;done=true;destroyed++;host.unregisterPopup(this);}
}
''',
            "PsychOwnerPaths.hx": r'''package;
class PsychOwnerPaths { public static function ownerRoot(facade:Dynamic):String {
 var get=Reflect.field(facade,'__sourceOwnerRoot');
 return get==null?'':Std.string(Reflect.callMethod(facade,get,[]));
} }
''',
            "PsychOwnerAssetPath.hx": r'''package;
import haxe.io.Path;
import sys.FileSystem;
using StringTools;
typedef PsychOwnerAssetPathResult={var path:String;var owned:Bool;var blocked:Bool;var unavailable:Bool;}
class PsychOwnerAssetPath {
 public static function normalizeOwner(value:String):String {
  if(value==null)return '';var p=Path.normalize(value.replace('\\','/'));
  return FileSystem.isDirectory(p)?p:'';
 }
 public static function cleanId(value:String):String {
  if(value==null)return null;var p=value.replace('\\','/').trim();
  if(p==''||p.startsWith('/')||p.indexOf(':')>=0||p.split('/').indexOf('..')>=0)return null;
  while(p.startsWith('./'))p=p.substr(2);return p;
 }
 public static function resolve(owner:String,id:String):PsychOwnerAssetPathResult {
  var p=cleanId(id);if(p==null)return {path:null,owned:false,blocked:true,unavailable:false};
  if(p.toLowerCase().startsWith(owner.toLowerCase()+'/'))p=p.substr(owner.length+1);
  else if(p.toLowerCase().startsWith('assets/imported_mods/'))
   return {path:null,owned:false,blocked:true,unavailable:false};
  if(p.startsWith('assets/'))p=p.substr(7);
  var candidate=Path.normalize(Path.join([owner,p]));
  return {path:candidate,owned:withinOwner(owner,candidate),blocked:false,unavailable:!FileSystem.exists(candidate)};
 }
 public static function withinOwner(owner:String,path:String):Bool {
  if(owner==null||path==null||!FileSystem.exists(owner)||!FileSystem.exists(path))return false;
  var base=Path.normalize(FileSystem.fullPath(owner)).toLowerCase();
  var candidate=Path.normalize(FileSystem.fullPath(path)).toLowerCase();
  return candidate.startsWith(base+'/');
 }
}
''',
            "CompatScriptManifest.hx": r'''package;
import haxe.io.Path; using StringTools;
class CompatScriptManifest { public static function destinationKey(root:String):String
 return root==null?'':Path.normalize(root.replace('\\','/')).toLowerCase(); }
''',
            "CodenameOwnerSaveData.hx": r'''package;
class CodenameOwnerSaveData {
 public var owner:String;var values:Map<String,Dynamic>=new Map();
 public function new(root:String,?storage:Dynamic)owner=root;
 public function getField(key:String):Dynamic return values.get(key);
 public function setField(key:String,value:Dynamic):Dynamic {values.set(key,value);return value;}
 public function flush():Void {}
}
''',
        }

        with tempfile.TemporaryDirectory(prefix="psych-achievement-runtime-", dir=TEST_TMP) as directory:
            work = Path(directory)
            owner_a = work / "assets/imported_mods/owner-a"
            owner_b = work / "assets/imported_mods/owner-b"
            outside = work / "assets/imported_mods/other/achievements.json"
            (owner_a / "data").mkdir(parents=True)
            (owner_a / "mods/not-enabled").mkdir(parents=True)
            (owner_b / "data").mkdir(parents=True)
            outside.parent.mkdir(parents=True)
            (owner_a / "data/achievements.json").write_text(
                '[{"save":"from_base","name":"From retained JSON","description":"owner data"}]',
                encoding="utf-8",
            )
            (owner_a / "mods/not-enabled/achievements.json").write_text("[]", encoding="utf-8")
            outside.write_text("[]", encoding="utf-8")
            (work / "RuntimeFixtureMain.hx").write_text(main, encoding="utf-8", newline="\n")
            for relative, content in stubs.items():
                target = work / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [
                    *HAXE_COMMAND,
                    "-cp", str(ROOT / "source"), "-cp", str(work), "-cp", str(TJSON),
                    "--run", "RuntimeFixtureMain",
                    str(owner_a), str(owner_b), str(outside),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
