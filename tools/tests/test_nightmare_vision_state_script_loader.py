"""Extracted source state loader with real Iris modules and group registration."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_source_event_preparation import extract_method
from tools.haxe_flixel_math_stubs import write_flixel_point_stub

ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionStateScriptLoaderTest(unittest.TestCase):
    def test_extracted_loader_resolves_paths_and_owns_real_iris_handles(self):
        session_source = (ROOT / "source/NightmareVisionStateSession.hx").read_text(encoding="utf-8")
        create_script_at = extract_method(session_source, "public function createScriptAt(")
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            write_flixel_point_stub(work)
            main_source = r'''
import NightmareVisionScriptBindings.NightmareVisionScriptContext;

typedef OwnerEntry = {
 var scope:String;
 var name:String;
 var path:String;
 var relative:String;
}

class FlxG { public static var state:Dynamic; }

class FNFAssets {
 public static var files:Map<String,String>=[];
 public static var reads:Int=0;
 public static function getText(path:String):String {reads++; return files.get(path);}
}

class OwnerPaths implements NightmareVisionScriptPaths {
 public var root:String="/owner";
 public var scriptExtensions(default,null):Array<String>=["hx","hxs","hscript"];
 public var scriptInstances:Map<String,NightmareVisionScriptModule>=[];
 public var lookups:Int=0;
 public function new() {FNFAssets.files=new Map();FNFAssets.reads=0;}
 public function getPath(file:String,?parentFolder:String,checkMods:Bool=false):String return file;
 public function exists(path:String):Bool return FNFAssets.files.exists(path);
 public function getModFolder(path:String,?exclude:String):String return "ownerLabel";
 public function resolveScript(path:String):OwnerEntry {
  lookups++;
  for (extension in scriptExtensions) {
   var selected=root + "/" + path + "." + extension;
   if (FNFAssets.files.exists(selected))
    return {scope:"dynamic",name:path,path:selected,relative:selected.substr(root.length+1)};
  }
  return null;
 }
}

class PlayState {
 public static function seedNightmareVisionCommon(interp:NightmareVisionScriptInterp,
  paths:OwnerPaths,prefs:Dynamic,plugins:Dynamic,mods:Dynamic,difficulty:Dynamic,
  clock:Dynamic=null,entry:OwnerEntry=null):Void {
  interp.variables.set("game",FlxG.state);
  interp.variables.set("inPlaystate",false);
  interp.variables.set("entryScope",entry == null ? null : entry.scope);
  interp.variables.set("entryName",entry == null ? null : entry.name);
  interp.variables.set("readParent",function():Dynamic return interp.parent);
 }
}

class FixtureLoader {
 public var paths:OwnerPaths;
 var prefs:Dynamic={};
 var plugins:Dynamic={};
 var mods:Dynamic={};
 var difficulty:Dynamic={};
 var alive:Bool=true;
 public function new(paths:OwnerPaths) this.paths=paths;
 function ensureAlive():Void if (!alive) throw "released source session";
 function report(name:String,callback:String,error:Dynamic):Void {}
 __CREATE_SCRIPT_AT__
}

class Main {
 static function check(value:Bool,message:String):Void {if(!value)throw message;}
 static function resultName(result:NightmareVisionStateScriptLoadResult):String
  return Type.enumConstructor(result);

 static function main():Void {
  var paths=new OwnerPaths();var loader=new FixtureLoader(paths);
  var oldState:Dynamic={name:"outgoing"};var targetState:Dynamic={name:"incoming"};
  FlxG.state=oldState;
  var sourceCode='var initialValues=[game,readParent(),script.name,script.modFolder,entryScope,entryName,inPlaystate];'
   +'function initialValuesResult() return initialValues;'
   +'function currentParent() return readParent();'
   +'function onLoad() { loadedParent=readParent(); }'
   +'function loadedParentResult() return loadedParent;';

  var statePath="/owner/scripts/states/Welcome.hxs";
  FNFAssets.files.set(statePath,sourceCode);
  var lowerPriorityPath="/owner/scripts/states/Welcome.hscript";
  FNFAssets.files.set(lowerPriorityPath,"throw 'wrong extension selected';");
  var stateGroup=new NightmareVisionScriptGroup(oldState);
  var stateResult=loader.createScriptAt("states","Welcome",targetState,stateGroup,true);
  check(resultName(stateResult)=="Loaded","existing state file returns Loaded");
  var stateModule:NightmareVisionScriptModule=null;
  switch(stateResult) {
   case Loaded(path,sourceName,handle):
    stateModule=handle;
    check(path==statePath && sourceName=="Welcome" && handle.name=="Welcome",
     "state path resolves supported hxs and fromFile uses the selected name");
   default: throw "expected Loaded state result";
  }
  var initial:Array<Dynamic>=cast stateModule.callValue("initialValuesResult");
  check(initial[0]==oldState && initial[1]==oldState && initial[2]=="Welcome"
   && initial[3]=="ownerLabel" && initial[4]=="state" && initial[5]=="Welcome"
   && initial[6]==false,
   "real Iris top-level code receives current FlxG.state and the source preset before group registration");
  check(stateModule.interp.sharedFields==null,
   "fromFile receives no group shareables before source registration");
  stateGroup.parent=targetState;
  check(stateGroup.addScript(stateModule) && stateModule.interp.parent==targetState
   && stateModule.interp.sharedFields==stateGroup.sharedFields,
   "ScriptGroup registration reparents the real interpreter and supplies shared fields");
  stateModule.callValue("onLoad");
  check(stateModule.callValue("currentParent")==targetState
   && stateModule.callValue("loadedParentResult")==targetState,
   "constructor onLoad runs after registration has rebound the interpreter parent");

  var repeatResult=loader.createScriptAt("states","Welcome",targetState,stateGroup,true);
  var repeated:NightmareVisionScriptModule=null;
  switch(repeatResult) {
   case Loaded(path,sourceName,handle):
    repeated=handle;
    check(path==statePath && sourceName=="Welcome" && handle.name=="Welcome_1",
     "state existence checks the full path, then repeated fromFile reserves an Iris-suffixed name");
   default: throw "state loader must not confuse module name with its path key";
  }
  check(stateGroup.exists(statePath)==false && stateGroup.addScript(repeated)
   && stateGroup.members.length==2,
   "the exact donor path check misses selected-name modules and permits the repeated source handle");

  var exactPath="/owner/scripts/states/Already.hx";
  FNFAssets.files.set(exactPath,sourceCode);
  var exactGroup=new NightmareVisionScriptGroup(oldState);
  var exactModule=NightmareVisionScriptModule.fromSource(exactPath,"",oldState,null,null,
   function(name,callback,error){});
  check(exactGroup.addScript(exactModule),"source-path-named fixture registers");
  var readsBeforeExact=FNFAssets.reads;
  var exactResult=loader.createScriptAt("states","Already",targetState,exactGroup,true);
  check(resultName(exactResult)=="AlreadyLoaded" && FNFAssets.reads==readsBeforeExact,
   "state path match returns before fromFile even though the file is present");

  var absentGroup=new NightmareVisionScriptGroup(oldState);
  var absentKey="scripts/states/Absent";
  var absentModule=NightmareVisionScriptModule.fromSource(absentKey,"",oldState,null,null,
   function(name,callback,error){});
  check(absentGroup.addScript(absentModule),"unextended fallback path fixture registers");
  var missingPathResult=loader.createScriptAt("states","Absent",targetState,absentGroup,true);
  var missingPathMatches=false;
  switch(missingPathResult){case AlreadyLoaded(path):missingPathMatches=path==absentKey;default:}
  check(resultName(missingPathResult)=="AlreadyLoaded" && missingPathMatches,
   "state checks scriptGroup.exists on its unextended fallback path before file existence");

  var substatePath="/owner/scripts/substates/Pause.hxs";
  FNFAssets.files.set(substatePath,sourceCode);
  var subGroup=new NightmareVisionScriptGroup(oldState);
  var subResult=loader.createScriptAt("substates","Pause",targetState,subGroup);
  var subModule:NightmareVisionScriptModule=null;
  switch(subResult) {
   case Loaded(path,sourceName,handle):
    subModule=handle;
    check(path==substatePath && sourceName==substatePath && handle.name==substatePath,
     "substate fromFile omits its name so the resolved hxs path becomes the source name");
   default: throw "expected Loaded substate result";
  }
  subGroup.parent=targetState;
  check(subGroup.addScript(subModule),"substate registers after reparenting");
  var subRepeat=loader.createScriptAt("substates","Pause",targetState,subGroup);
  var subRepeatNameMatches=false;
  switch(subRepeat){case Loaded(path,name,handle):subRepeatNameMatches=path==substatePath&&name==substatePath&&handle.name==substatePath+"_1";default:}
  check(subRepeatNameMatches && subGroup.members.length==1,
   "substate skips state-only group existence and resolves its repeated path-derived name");
  var subRepeatHandle:NightmareVisionScriptModule=null;
  switch(subRepeat){case Loaded(_,_,handle):subRepeatHandle=handle;default:}
  check(subGroup.addScript(subRepeatHandle) && subGroup.members.length==2,
   "substate repeated source handles remain group-owned");

  var collisionPath="/owner/scripts/states/SubstateCollision.hx";
  FNFAssets.files.set(collisionPath,sourceCode);
  var collisionGroup=new NightmareVisionScriptGroup(oldState);
  var collisionModule=NightmareVisionScriptModule.fromSource(collisionPath,"",oldState,null,null,
   function(name,callback,error){});
  check(collisionGroup.addScript(collisionModule),"prefix collision fixture registers");
  var collisionReads=FNFAssets.reads;
  // MusicBeatSubstate.scriptPrefix can be assigned "states"; its mode remains
  // substate mode, so it must not inherit the state-only exact-path precheck.
  var collisionResult=loader.createScriptAt("states","SubstateCollision",targetState,collisionGroup);
  var collisionLoaded=false;
  switch(collisionResult){
   case Loaded(path,name,handle):
    collisionLoaded=path==collisionPath && name==collisionPath && handle.name==collisionPath;
    handle.destroy();
   default:
  }
  check(collisionLoaded && FNFAssets.reads==collisionReads+1,
   "substate mode skips the state precheck and keeps the resolved path as the module name even when its prefix is states");

  var brokenPath="/owner/scripts/states/Broken.hx";
  FNFAssets.files.set(brokenPath,"var broken = ;");
  var failedResult=loader.createScriptAt("states","Broken",targetState,new NightmareVisionScriptGroup(oldState),true);
  var failed:NightmareVisionScriptModule=null;
  switch(failedResult){
   case ParseFailed(path,handle):
    failed=handle;
    check(path==brokenPath && handle.parsingFailed() && !handle.released,
     "loader returns its real parse-failed handle without destroying it");
   default: throw "expected ParseFailed result";
  }
  failed.destroy();
  check(failed.released && failed.interp==null && !paths.scriptInstances.exists("Broken"),
   "wrapper cleanup owns failed handle release and removes its reserved source name");

  var missingResult=loader.createScriptAt("states","Missing",targetState,new NightmareVisionScriptGroup(oldState),true);
  check(resultName(missingResult)=="Missing","absence is distinct from parse failure");
  var subMissingGroup=new NightmareVisionScriptGroup(oldState);
  var subMissingKey="scripts/substates/NoFile";
  var subMissingModule=NightmareVisionScriptModule.fromSource(subMissingKey,"",oldState,null,null,
   function(name,callback,error){});
  check(subMissingGroup.addScript(subMissingModule),"substate path-name fixture registers");
  var subMissing=loader.createScriptAt("substates","NoFile",targetState,subMissingGroup);
  check(resultName(subMissing)=="Missing",
   "substate returns missing even when a path-named module exists because it has no precheck");

  stateGroup.destroy();exactGroup.destroy();absentGroup.destroy();subGroup.destroy();collisionGroup.destroy();subMissingGroup.destroy();
 }
}
'''.replace("__CREATE_SCRIPT_AT__", create_script_at)
            (work / "Main.hx").write_text(main_source, encoding="utf-8")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript-iris/1,1,3"),
                 "-cp", str(work), "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
