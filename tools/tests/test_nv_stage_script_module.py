"""Real Iris Stage handle phases and public result identity."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest
from tools.haxe_flixel_math_stubs import write_flixel_point_stub
from test_source_event_preparation import extract_method
ROOT = Path(__file__).resolve().parents[2]

class StageModuleTest(unittest.TestCase):
    def test_unregistered_handle_errors_results_and_shareable_pointer(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            write_flixel_point_stub(work)
            (work / 'Main.hx').write_text(r'''
import crowplexus.iris.Iris.IrisCall;
class Main {
 static function check(v:Bool, message:String):Void { if(!v) throw message; }
 static function main() {
  var errors:Array<String> = [];
  var report = function(name:String, phase:String, error:Dynamic):Void {errors.push(name+"#"+phase);};
  var group = new NightmareVisionScriptGroup(null, report);
  var shared = group.sharedFields;
  shared.set("sharedValue", 17);
  var handle = NightmareVisionScriptModule.fromSource("selected/path/script.hx", '
   var ownHandle=script;
   var beforeRegistered=gameGroup.exists(script.name);
   var topShared=sharedValue;
   function own() return ownHandle;
   function registered() return beforeRegistered;
   function sampled() return topShared;
   function value() return 29;
   function onLoad() {
    var duplicate=makeDuplicate();
    gameGroup.addScript(duplicate);
   }
  ', null, shared, function(interp) {
   interp.variables.set("gameGroup",group);
   interp.variables.set("makeDuplicate",function() {
    return NightmareVisionScriptModule.fromSource("selected/path/script.hx", "", null, shared, null, report);
   });
  },report);
  check(!handle.parsingFailed(), "source initialization");
  check(handle.callValue("own")==handle, "real self before execute");
  check(handle.callValue("registered")==false && group.members.length==0, "unregistered execution");
  check(handle.callValue("sampled")==17, "shared identity before execution");
  handle.set("added",3);handle.set("added",4,false);
  check(handle.get("added")==3, "nonoverriding set");
  var result=handle.call("value");
  check(Std.isOfType(result,IrisCall) && result.funName=="value" && result.signature==handle.get("value") && result.returnValue==29,"real IrisCall");
  check(handle.callValue("value")==29,"raw internal boundary");
  var rerun=NightmareVisionScriptModule.fromSource("rerun", "bump(); 41;", null, shared,
   function(i) {i.variables.set("bump",function() {shared.set("runs",(shared.exists("runs")?shared.get("runs"):0)+1);});},report);
  check(shared.get("runs")==1 && rerun.execute()==41 && shared.get("runs")==2,"source repeated execute value");
  handle.set("context",3);
  handle.set("receiverRead",function() return handle.get("context"));
  var injected:Map<String,Dynamic>=["context"=>9,"missingPrevious"=>7];
  var receiver={tag:"source"};
  check(handle.executeFunc("receiverRead",null,receiver,injected)==9,"source executeFunc temporary vars");
  check(injected.get("this")==receiver && handle.get("context")==3 && handle.interp.variables.exists("missingPrevious") && handle.get("missingPrevious")==null,"source extraVars mutation/null restore");
  rerun.destroy();
  handle.call("onLoad");
  check(group.members.length==1 && group.members[0]!=handle && !group.addScript(handle),"reentrant duplicate registration identity");
  var oldShared=group.sharedFields;
  var replacement:Map<String,Dynamic> = new Map();
  group.scriptShareables=replacement;
  check(group.sharedFields==replacement && group.members[0].interp.sharedFields==oldShared,"pointer replacement does not rebind");
  var firstParent={tag:"initial"};group.parent=firstParent;
  check(group.members[0].interp.sharedFields==replacement,"changed parent rebinds current shareables");
  group.scriptShareables=oldShared;group.parent=firstParent;
  check(group.members[0].interp.sharedFields==replacement,"same nonnull parent does not rebind");
  group.parent=null;check(group.members[0].interp.sharedFields==oldShared,"null parent triggers current shareables rebind");
  for(code in ["var broken = ;", "throw \"top-level\";"]) {
   var bad=NightmareVisionScriptModule.fromSource("bad",code,null,oldShared,null,report);
   check(bad.parsingFailed() && bad.parsingException!=null && !bad.released,"failed real handle retained");
   bad.destroy();check(bad.released && bad.interp==null,"failed handle release");
  }
  var instances:Map<String,NightmareVisionScriptModule>=[];
  var named=NightmareVisionScriptModule.fromSource("same.hx", "public var ownName=script.name;", null, shared, null, report,true,instances,"ownerLabel");
  var suffix=NightmareVisionScriptModule.fromSource("same.hx", "", null, shared, null, report,true,instances);
  check(named.name=="same.hx" && suffix.name=="same.hx_1" && instances.get(named.name)==named && named.modFolder=="ownerLabel","source name reservation before execute");
  named.destroy();
  var reused=NightmareVisionScriptModule.fromSource("same.hx", "", null, shared, null, report,false,instances);
  check(reused.name=="same.hx" && !instances.exists(reused.name) && !reused.initialized,"unexecuted does not reserve name");
  reused.execute();check(instances.get(reused.name)==reused,"public execute reserves instance");
  suffix.destroy();reused.destroy();
  var presetFailure:Dynamic={tag:"preset"};var caught:Dynamic=null;
  try NightmareVisionScriptModule.fromSource("preset", "", null, shared,function(_) {throw presetFailure;},report) catch(e:Dynamic)caught=e;
  check(caught==presetFailure,"preset failure propagates outside execute error boundary");
  var stale=NightmareVisionScriptModule.fromSource("stale", "if(failNow) throw \"old\"; 8;",null,shared,function(i)i.variables.set("failNow",true),report);
  var firstError=stale.parsingException;stale.set("failNow",false);
  check(stale.execute()==8 && stale.parsingException==firstError,"successful retry retains original parsing exception");stale.destroy();
  var pendingA=NightmareVisionScriptModule.fromSource("pending", "",null,shared,null,report,false,instances);
  var pendingB=NightmareVisionScriptModule.fromSource("pending", "",null,shared,null,report,false,instances);
  check(pendingA.name==pendingB.name,"unexecuted source names are not reserved");
  pendingA.execute();pendingB.execute();check(instances.get("pending")==pendingB,"later execution overwrites map");
  pendingA.destroy();check(!instances.exists("pending") && !pendingB.released,"source destroy blindly removes name only");pendingB.destroy();
  check(errors.length==3,"syntax and runtime errors attributable");
  handle.destroy();group.destroy();
  check(handle.call("value")==null && handle.get("value")==false,"released source handle");
 }
}
''', encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(ROOT / '.haxelib/hscript-iris/1,1,3'), '-cp', str(work), '-main', 'Main', '--interp'], capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_scoped_source_class_constructors_statics_extensions_and_stale_io(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            write_flixel_point_stub(work)
            (work / 'Main.hx').write_text(r'''
import NightmareVisionScriptBindings.NightmareVisionScriptContext;
class ScriptPaths implements NightmareVisionScriptPaths {
 public var scriptExtensions(default,null):Array<String>=["hx","hxs","hscript"];
 public var scriptInstances(default,null):Map<String,NightmareVisionScriptModule>=[];
 public var files:Map<String,String>=["owner/found.custom"=>"var folderBefore=script.modFolder; function earlyFolder() return folderBefore; 12;"];
 public var probes=0;public function new(){}
 public function getPath(file:String,?parentFolder:String,checkMods:Bool=false):String {probes++;return "owner/"+file;}
 public function exists(path:String):Bool {probes++;return files.exists(path);}
 public function getModFolder(path:String,?exclude:String):String return "capturedLabel";
}
class Main {
 static function check(value:Bool, message:String):Void {if(!value)throw message;}
 static function main() {
  var paths=new ScriptPaths();var active=true;var reads=0;
  var context:NightmareVisionScriptContext=null;
  context={paths:paths,read:function(path) {reads++;return paths.files.get(path);},
   requireActive:function() {if(!active)throw "released";},parent:function()return null,
   configure:function(child) NightmareVisionScriptBindings.install(child,context),
   report:function(n,p,e) {throw n+"#"+p+":"+e;}};
  var interpreter=new NightmareVisionScriptInterp();NightmareVisionScriptBindings.install(interpreter,context);
  interpreter.execute(new NightmareVisionScriptParser().parseString('
   import funkin.scripts.FunkinScript;
   import Type;
   import Reflect;
   FunkinScript.H_EXTS.unshift("custom");
   resolved=FunkinScript.getPath("found");
   suffixCheck=FunkinScript.isHxFile("not-dot-custom");
   created=FunkinScript.fromFile(resolved);
   deferred=new FunkinScript("public var answer=37; 14;","deferred",false);
   typeMade=Type.createInstance(Type.resolveClass("funkin.scripts.FunkinScript"),["5;","type",false]);
   reflected=Reflect.field(FunkinScript,"fromString")("9;","reflect",false);
  '));
  var created:NightmareVisionScriptModule=cast interpreter.variables.get("created");
  check(interpreter.variables.get("resolved")=="owner/found.custom" && interpreter.variables.get("suffixCheck")==true,"mutable source extensions and suffix semantics");
  check(created.name=="owner/found.custom" && created.modFolder=="capturedLabel" && created.callValue("earlyFolder")=="capturedLabel","modFolder exists before top-level execution");
  check(created.interp.sharedFields==null,"null shareables source constructor");
  var deferred:NightmareVisionScriptModule=cast interpreter.variables.get("deferred");
  check(!deferred.initialized && !paths.scriptInstances.exists("deferred") && deferred.execute()==14,"autoExecute false and explicit execute");
  var typeMade:NightmareVisionScriptModule=cast interpreter.variables.get("typeMade");
  var reflected:NightmareVisionScriptModule=cast interpreter.variables.get("reflected");
  check(Std.isOfType(typeMade,NightmareVisionScriptModule) && Std.isOfType(reflected,NightmareVisionScriptModule),"actual source constructor paths");
  check(interpreter.sourceClassScope().resolveClass("funkin.scripts.FunkinScript")==NightmareVisionScriptModule,"real runtime Class identity");
  var prior=reads;active=false;var failure:Dynamic=null;
  try interpreter.execute(new NightmareVisionScriptParser().parseString('FunkinScript.fromFile("owner/found.custom");')) catch(e:Dynamic) failure=e;
  check(failure=="released" && reads==prior,"stale captured factory fails before file IO");
  created.destroy();deferred.destroy();typeMade.destroy();reflected.destroy();interpreter.release();
 }
}
''',encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(ROOT / '.haxelib/hscript-iris/1,1,3'), '-cp', str(work), '-main', 'Main', '--interp'], capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_actual_current_state_preset_and_authoritative_folder(self):
        production=(ROOT/'source/PlayState.hx').read_text()
        configure=extract_method(production,'static function configureNightmareVisionStandalone(')
        for original in ['NightmareVisionPaths','NightmareVisionClientPrefs','NightmareVisionPluginRuntime','NightmareVisionModsContext','NightmareVisionDifficultyAdapter']:
            configure=configure.replace(original,'Dynamic')
        folder=production[production.index('var entryPath = entry != null'):production.index('NightmareVisionStageBindings.install(interp, paths',production.index('var entryPath = entry != null'))]
        path_source=(ROOT/'source/NightmareVisionPaths.hx').read_text(encoding='utf-8')
        get_folder=extract_method(path_source,'public function getModFolder(')
        alias=extract_method(path_source,'function sourceAliasPath(')
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            work=Path(directory);write_flixel_point_stub(work)
            main=r'''
import NightmareVisionScriptBindings.NightmareVisionScriptContext;
import haxe.io.Path;
import sys.FileSystem;
using StringTools;
class FlxG {public static var state:Dynamic;}
class NightmareVisionSourceBindings {public static function bindOwner(i:NightmareVisionScriptInterp,r:String,f:String,?context:Dynamic,?options:Dynamic):Void {if(f!=null)i.variables.set("modFolder",f);}}
// Configuration and SDK effects have their own actual-adapter/native probes;
// this fixture isolates source module folder authority and current-state seeding.
class NightmareVisionModConfigBindings {public static function install(i:Dynamic,c:Dynamic,t:Dynamic):Void {}}
class MusicBeatState {}
class FixtureModFamily {public function familyDirectories():Array<String> return [];}
class FixturePaths implements NightmareVisionScriptPaths {
 public var modFamily:FixtureModFamily=null;
 function providerForDirectory(name:String):FixturePaths return this;
 // IO is a stated fixture boundary; the real family Paths module tests physical roots.
 function scopeAssetPath(p:String):Null<String> return p==root || p.startsWith(root+'/') ? p : null;
 public static inline var MODS_DIRECTORY="content";public var sourceDirectory:Null<String>="ownerLabel";
 public var root:String;public var scriptExtensions(default,null):Array<String>=["hx"];
 public var scriptInstances(default,null):Map<String,NightmareVisionScriptModule>=[];
 public function new(r:String)root=r;
 public function getPath(p:String,?f:String,b:Bool=false):String return p;
 public function exists(p:String):Bool return true;
 '''+get_folder+alias+r'''
}
class PlayState {
 public static var instance:PlayState;public var nightmareVisionPaths:FixturePaths;
 public var scripts:NightmareVisionScriptGroup;public var calls:Array<String>=[];
 public function new(p:FixturePaths){nightmareVisionPaths=p;scripts=new NightmareVisionScriptGroup(this);}
 public function seedNightmareVision(i:NightmareVisionScriptInterp,e:NightmareVisionScriptDiscovery.NightmareVisionScriptEntry,p:Dynamic):Void {
  calls.push("game");seedNightmareVisionCommon(i,nightmareVisionPaths,null,null,null,null,null,e);
  i.variables.set("game",this);i.variables.set("inPlaystate",true);
 }
 public static function seedNightmareVisionCommon(interp:NightmareVisionScriptInterp, paths:Dynamic,prefs:Dynamic,plugins:Dynamic,mods:Dynamic,difficulty:Dynamic,clock:Dynamic=null,entry:NightmareVisionScriptDiscovery.NightmareVisionScriptEntry=null):Void {
  if(mods==null)mods={optionSession:null,nativeConfig:null};
'''+folder+r'''
 }
'''+configure.replace('static function','public static function',1)+r'''
}
class Main {
 static function check(v:Bool,m:String):Void {if(!v)throw m;}
 static function main() {
  var paths=new FixturePaths("owner");var play=new PlayState(paths);PlayState.instance=play;FlxG.state=play;
  var context:NightmareVisionScriptContext={paths:paths,read:function(p)return "function proof() return [game,inPlaystate,modFolder,script.modFolder,game.scripts];",requireActive:function(){},parent:function()return FlxG.state,
   configure:function(i) PlayState.configureNightmareVisionStandalone(i,paths,null,null,null,null),report:function(n,p,e){throw n+"#"+p+":"+e;}};
  var module=NightmareVisionScriptModule.fromFile("owner/file.hx",null,true,null,null,context);
  var proof:Array<Dynamic>=module.call("proof").returnValue;
  check(proof[0]==play&&proof[1]==true&&proof[2]=="ownerLabel"&&proof[3]=="ownerLabel"&&proof[4]==play.scripts,"actual current-state folder/preset");
  var replacement=new NightmareVisionScriptGroup(play);play.scripts=replacement;
  proof=module.call("proof").returnValue;check(proof[4]==replacement,"live source group pointer");
  var explicit=NightmareVisionScriptModule.fromString("function proof() return [modFolder,script.modFolder];","explicit",true,null,"custom",context);
  proof=explicit.call("proof").returnValue;check(proof[0]=="custom"&&proof[1]=="custom","explicit fromString folder authoritative");
  var overrideFile=NightmareVisionScriptModule.fromFile("owner/file.hx",null,true,null,"fileOverride",context);
  proof=overrideFile.call("proof").returnValue;check(proof[2]=="fileOverride"&&proof[3]=="fileOverride","explicit fromFile folder authoritative");
  FlxG.state={menu:true};var outside=NightmareVisionScriptModule.fromString("function proof() return [game,inPlaystate,modFolder];","outside",true,null,null,context);
  proof=outside.call("proof").returnValue;check(proof[0]==FlxG.state&&proof[1]==false&&proof[2]==null,"nonplay current state and explicit null folder");
  FlxG.state=play;
  check(paths.getModFolder("C:/private/owner/scripts/plugins/Utils.hx","scripts")=="","absolute discovery path is not a source root prefix");
  for(scope in ["plugin","global","event","character"]) {
   var entry:NightmareVisionScriptDiscovery.NightmareVisionScriptEntry={scope:scope,name:"file",path:FileSystem.absolutePath("owner/"+scope+".hx"),relative:"scripts/"+scope+"/file.hx"};
   var loaded=NightmareVisionScriptModule.fromSource(scope,"var before=[modFolder,script.modFolder];function proof() return before;",play,null,
    function(i)PlayState.seedNightmareVisionCommon(i,paths,null,null,null,null,null,entry),function(n,p,e){throw e;},true,null,null);
   proof=loaded.call("proof").returnValue;
   check(proof[0]=="ownerLabel"&&proof[1]=="ownerLabel","internal "+scope+" owner-relative folder before execute");loaded.destroy();
  }
  var coreEntry:NightmareVisionScriptDiscovery.NightmareVisionScriptEntry={scope:"plugin",name:"core",path:FileSystem.absolutePath("owner/__nmv_core/scripts/plugins/core.hx"),relative:"__nmv_core/scripts/plugins/core.hx"};
  var core=NightmareVisionScriptModule.fromSource("core","var before=[modFolder,script.modFolder];function proof() return before;",play,null,
   function(i)PlayState.seedNightmareVisionCommon(i,paths,null,null,null,null,null,coreEntry),function(n,p,e){throw e;},true,null,"old-value");
  proof=core.call("proof").returnValue;check(proof[0]==""&&proof[1]=="","internal core folder reset to empty before execute");core.destroy();
  for(scope in ["standalone","stage-standalone"]) for(value in [null,"","explicit"]) {
   var entry:NightmareVisionScriptDiscovery.NightmareVisionScriptEntry={scope:scope,name:"caller",path:"C:/private/owner/caller.hx",relative:"scripts/caller.hx"};
   var caller=NightmareVisionScriptModule.fromSource("caller","var before=[modFolder,script.modFolder];function proof() return before;",play,null,
    function(i)PlayState.seedNightmareVisionCommon(i,paths,null,null,null,null,null,entry),function(n,p,e){throw e;},true,null,value);
   proof=caller.call("proof").returnValue;check(proof[0]==value&&proof[1]==value,"caller "+scope+" explicit/null/empty metadata remains authoritative");caller.destroy();
  }
  module.destroy();explicit.destroy();overrideFile.destroy();outside.destroy();
 }
}
'''
            (work/'Main.hx').write_text(main,encoding='utf-8')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-5000:])

    def test_backend_follows_actual_group_pointer_replacement_without_reconciliation(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            work=Path(directory);write_flixel_point_stub(work)
            (work/'Main.hx').write_text(r'''
class Main {static function ok(v:Bool,m:String):Void {if(!v)throw m;}static function main(){
 var main=new NightmareVisionScriptGroup();var events=new NightmareVisionScriptGroup();var notes=new NightmareVisionScriptGroup();
 var old=main;var oldModule=main.loadSource("old","function tick() return 1;");
 var plan:NightmareVisionScriptDiscovery.NightmareVisionScriptPlan={root:"owner",baseAssetsRoot:"owner/core",song:"tutorial",stage:"stage",scripts:[],coverageNotes:[]};
 var backend=new NightmareVisionGameplayScripts(null,plan,function(p)return "",function(i,e,a){},function(n,p,e){throw e;},null,null,
 {main:function()return main,setMain:function(v)return main=v,events:function()return events,setEvents:function(v)return events=v,notes:function()return notes,setNotes:function(v)return notes=v});
 ok(backend.call("tick")==1,"initial actual group");
 var replacement=new NightmareVisionScriptGroup();replacement.loadSource("new","function tick() return 7;");main=replacement;
 ok(backend.group==replacement&&backend.call("tick")==7&&!oldModule.released&&old.members[0]==oldModule,"live pointer without old group reconciliation");
 var other=new NightmareVisionScriptGroup();backend.group=other;ok(main==other,"backend setter publishes actual pointer");
 var eventReplacement=new NightmareVisionScriptGroup();var noteReplacement=new NightmareVisionScriptGroup();backend.eventGroup=eventReplacement;backend.noteTypeGroup=noteReplacement;
 ok(events==eventReplacement&&notes==noteReplacement,"secondary pointers follow same contract");
 main=null;var error:Dynamic=null;try backend.call("tick")catch(e:Dynamic)error=e;ok(error!=null&&main==null,"authored null preserves source dispatch failure");
 main=other;backend.destroy();ok(other.released&&eventReplacement.released&&noteReplacement.released&&!old.released&&!replacement.released,"destroy only current groups");
 old.destroy();replacement.destroy();
}}
''',encoding='utf-8')
            r=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(r.returncode,0,(r.stdout+r.stderr)[-4000:])
