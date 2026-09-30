"""Codename lifecycle stays scoped and keeps its callback ABI separate."""

from pathlib import Path
import subprocess
import tempfile
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenamePlayStateLifecycleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "source/PlayState.hx").read_text()

    def test_selected_namespace_and_authored_stage(self):
        source = self.source
        def method(name):
            start = source.index("\tfunction " + name + "(")
            brace = source.index("{", start)
            depth = 0
            for index in range(brace, len(source)):
                depth += (source[index] == "{") - (source[index] == "}")
                if depth == 0:
                    return source[start:index + 1]
            raise AssertionError(name)

        selected_root = method("codenameSelectedRoot")
        source_folder = method("codenameSourceFolder")
        script_plan = method("getCodenameScriptPlan")
        stage_loader = method("loadCodenameStageCompat")
        song_loader = method("loadCodenameSongScripts")
        self.assertIn("entry.engine == ImportEngine.CODENAME", selected_root)
        self.assertIn("CompatScriptManifest.selectedRoot(manifest)", selected_root)
        self.assertIn("sourceOwner", source_folder)
        self.assertIn("destination.toLowerCase() == storage.toLowerCase()", source_folder)
        self.assertIn("CodenameScriptPlan.metadataPath(root, source)", script_plan)
        self.assertIn("plan.song.toLowerCase() == source.toLowerCase()", script_plan)
        self.assertIn("CodenameScriptDiscovery.withinRoot(root, path)", script_plan)
        self.assertIn("CodenameScriptPlan.selectedStage(plan, codenameDifficulty(Reflect.fields(plan.stages)))", stage_loader)
        self.assertIn("CodenameScriptDiscovery.discover(root, null, null, stage)", stage_loader)
        self.assertIn("var selected = codenameDifficulty(scriptDifficulties);", song_loader)
        self.assertIn("CodenameScriptDiscovery.discover(root, plan.song", song_loader)

    def test_ordered_lifecycle_and_cleanup(self):
        source = self.source
        self.assertIn("codenameScriptScopes.push(scope);", source)
        self.assertIn("if (!callCodenameScript(scope, 'create', []))", source)
        self.assertIn("callCodenameScript(scope, 'postCreate', [])", source)
        self.assertIn("dispatchCodenamePostCreate();", source)
        self.assertIn("callCodenameScripts('onSongStart', []);", source)
        self.assertIn("callCodenameScripts('onStartSong', []);", source)
        self.assertIn("callCodenameScripts('update', [elapsed]);", source)
        self.assertIn("callCodenameScripts('stepHit', [curStep]);", source)
        self.assertIn("callCodenameScripts('beatHit', [curBeat]);", source)
        self.assertIn("callCodenameScripts('destroy', []);", source)
        self.assertIn("scope.interp.release();", source)
        self.assertIn("releaseCodenameStageScripts();", source)
        self.assertIn("if (codenameSongScriptsLoaded) return;", source)
        self.assertIn("loadCodenameStageCompat(stageName);", source)
        self.assertIn("codename-scene-order-after-stage:", source)
        self.assertIn("stageSprites.remove(sprite);", source)

    def test_codename_post_update_runs_after_native_and_psych_post_update(self):
        start = self.source.index("\toverride public function update(elapsed:Float) {")
        end = self.source.index("\n\t/** Drive the real hit route", start)
        update = self.source[start:end]
        native_update = update.index("super.update(elapsed);")
        psych_post = update.index("callAllHScript('updatePost', [elapsed]);")
        codename_post = update.index("callCodenameScripts('postUpdate', [elapsed]);")
        self.assertLess(native_update, psych_post)
        self.assertLess(psych_post, codename_post)

    def test_codename_default_strum_globals_are_live_and_state_matches_flxg(self):
        start = self.source.index("\tfunction seedCodenameScriptGlobals(")
        brace = self.source.index("{", start)
        depth = 0
        for index in range(brace, len(self.source)):
            depth += (self.source[index] == "{") - (self.source[index] == "}")
            if depth == 0:
                method = self.source[start:index + 1]
                break
        else:
            self.fail("seedCodenameScriptGlobals was not terminated")
        fixture = '''
class FlxG { public static var state:Dynamic; }
class Lib { public static var application:Dynamic = null; }
class CodenameScriptInterp {
 public var variables:Map<String,Dynamic>=new Map();
 public var globals:Map<String,{read:Void->Dynamic,write:Dynamic->Void}>=new Map();
 public function new() {}
 public function bindLiveGlobal(name:String,read:Void->Dynamic,write:Dynamic->Void):Void
   globals.set(name,{read:read,write:write});
 public function resolve(name:String):Dynamic
   return variables.exists(name) ? variables.get(name) : globals.get(name).read();
 public function assign(name:String,value:Dynamic):Void globals.get(name).write(value);
}
class Main {
 var enemyStrums:Dynamic;
 var playerStrums:Dynamic;
 var subState:Dynamic;
 var health:Float=1;
 var codenameInputLines:Array<Dynamic>=[];
 function getCodenameInputLine(index:Int):Dynamic
   return index<0 || index>=codenameInputLines.length ? null : codenameInputLines[index];
 function bindCodenameActorAliases(_interp:CodenameScriptInterp):Void {}
 public function new() {}
''' + method + '''
 static function main():Void {
   var game=new Main();
   var stateRef={}; FlxG.state=stateRef;
   var cpuBefore={}; var playerBefore={};
   var cpuLine={lineIndex:0}; var playerLine={lineIndex:1};
   game.codenameInputLines=[cpuLine,playerLine];
   game.enemyStrums=cpuBefore; game.playerStrums=playerBefore;
   var interp=new CodenameScriptInterp(); game.seedCodenameScriptGlobals(interp);
   if(interp.variables.get('state')!=stateRef) throw 'state must alias FlxG.state';
   var healthBinding=interp.globals.get('health');
   if(healthBinding==null || healthBinding.read()!=1) throw 'health must be a live gameplay global';
   game.health=0.25;
   if(interp.resolve('health')!=0.25) throw 'health global became stale';
   healthBinding.write(1.5);
   if(game.health!=1.5) throw 'health assignment did not reach PlayState';
   if(interp.resolve('cpuStrums')!=cpuBefore || interp.resolve('playerStrums')!=playerBefore)
     throw 'strum globals must expose the native groups';
   if(interp.resolve('cpu')!=cpuLine || interp.resolve('player')!=playerLine)
     throw 'Codename aliases must resolve source line 0 and line 1';
   var replacementCpuLine={lineIndex:0};
   game.codenameInputLines[0]=replacementCpuLine;
   if(interp.resolve('cpu')!=replacementCpuLine)
     throw 'cpu alias must follow the live source-line view';
   var cpuAfter={}; game.enemyStrums=cpuAfter;
   if(interp.resolve('cpuStrums')!=cpuAfter) throw 'cpuStrums should stay live';
   var nested={}; game.subState=nested;
   if(interp.resolve('subState')!=nested) throw 'subState should stay live';
   var playerAfter={}; interp.assign('playerStrums',playerAfter);
   if(game.playerStrums!=playerAfter || interp.resolve('playerStrums')!=playerAfter)
     throw 'playerStrums assignment should route to its native field';
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            (Path(work) / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", work, "--run", "Main"],
                cwd=ROOT, text=True, capture_output=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_events_stay_separate_from_native_positional_dispatch(self):
        source = self.source
        self.assertIn("CodenameEventDispatch.run(authored, callCodenameEvent", source)
        self.assertNotIn("callCodenameScripts('onEvent'", source)
        self.assertNotIn("hscriptStates.set(usehaxe, interp)", source)

    def test_pause_switches_only_after_native_substate_transitions(self):
        source = self.source
        opened = source.index("super.openSubState(SubState);")
        paused = source.index("if (paused) setCodenameScriptsPaused(true);", opened)
        self.assertLess(opened, paused)
        closed = source.index("super.closeSubState();")
        resumed = source.index("if (resumeEventVideo) setCodenameScriptsPaused(false);", closed)
        self.assertLess(closed, resumed)
        cancelled = source.index("pauseEvent.eventCanceled == true")
        actual_open = source.index("openSubState(new PauseSubState", cancelled)
        self.assertLess(cancelled, actual_open)

    def test_real_scene_bindings_borrow_hud_and_keep_removed_owned_props(self):
        source = self.source

        def method(name):
            start = source.index("\tfunction " + name + "(")
            brace = source.index("{", start)
            depth = 0
            for index in range(brace, len(source)):
                depth += (source[index] == "{") - (source[index] == "}")
                if depth == 0:
                    return source[start:index + 1]
            raise AssertionError(name)

        begin = source.index("\t\tvar placeOne = function(value:Dynamic",
                             source.index("\tfunction loadCodenameScript("))
        end = source.index("\t\tvar gameAlpha =", begin)
        bindings = source[begin:end]
        helpers = "\n".join(method(name) for name in (
            "codenameMembership", "codenameBorrowedNode"))
        fixture = '''class FlxBasic {
 public var name:String; public var cameras:Array<Dynamic>;
 public var destroyed=false;
 public function new(name:String) this.name=name;
 public function destroy():Void destroyed=true;
}
class FakeInterp {
 public var variables:Map<String,Dynamic>=[];
 public var scriptDisabled:Bool=false;
 public function new() {}
 public function claimSceneObject(_value:Dynamic):Void {}
 public function nativeFlxBasic(value:Dynamic):FlxBasic
   return Std.isOfType(value,FlxBasic) ? cast value : null;
 public function disableScript():Void scriptDisabled=true;
}
class RuntimeSmokeHarness {
 public static function enabled():Bool return false;
 public static function markStep(_value:String):Void {}
}
class Main {
 static inline var BEHIND_GF=1;
 static inline var BEHIND_DAD=2;
 static inline var BEHIND_BF=4;
 var members:Array<FlxBasic>=[];
 var stageSprites:Array<FlxBasic>=[];
 var codenameScriptScopes:Array<Dynamic>=[];
 var codenameSceneMembership:CodenameSceneMembership<FlxBasic>=null;
 var healthBarBG:FlxBasic; var gf:FlxBasic; var dad:FlxBasic; var boyfriend:FlxBasic;
 var camGame:Dynamic={};
 public function new() {}
 function isScriptObject(value:Dynamic):Bool return Std.isOfType(value,FlxBasic);
 function protectedStageObject(value:Dynamic):Bool return value==gf || value==dad || value==boyfriend;
 function nativeStageHudMembers():Array<FlxBasic> return [healthBarBG];
 function registerStageSprite(sprite:Dynamic):Void if(stageSprites.indexOf(sprite)<0) stageSprites.push(sprite);
 function hasExplicitCameras(sprite:FlxBasic):Bool return sprite.cameras!=null;
 function remove(sprite:FlxBasic, ?splice:Bool=false):Void members.remove(sprite);
 function insert(index:Int,sprite:FlxBasic):Void members.insert(index,sprite);
 function addHscriptSprite(sprite:Dynamic,position:Null<Int>):Void {
   var basic:FlxBasic=cast sprite; members.remove(basic);
   if(position==0) members.push(basic); else members.insert(0,basic);
 }
''' + helpers + '''
 function run():Void {
   var file={relative:"stage.hx",family:"stage"};
   var interp=new FakeInterp();
   var scope={file:file,interp:interp,owned:new Array<FlxBasic>(),postCreated:false,
     failedCallbacks:new Map<String,Bool>()};
   codenameScriptScopes.push(scope);
   gf=new FlxBasic("gf"); healthBarBG=new FlxBasic("hud");
   members=[healthBarBG,gf];
''' + bindings + '''
   var removeNode:Dynamic=interp.variables.get("remove");
   var addNode:Dynamic=interp.variables.get("add");
   var insertNode:Dynamic=interp.variables.get("insert");
   var behindGF:Dynamic=interp.variables.get("addBehindGF");
   removeNode(healthBarBG);
   if(members.indexOf(healthBarBG)>=0 || scope.owned.length!=0 || healthBarBG.destroyed)
     throw "HUD should be borrowed";
   insertNode(0,healthBarBG);
   if(members[0]!=healthBarBG) throw "borrowed insert";
   var sceneGF=new FlxBasic("scene-gf"), sceneDad=new FlxBasic("scene-dad");
   var sceneBF=new FlxBasic("scene-bf"), view=new FlxBasic("view");
   gf=sceneGF; dad=sceneDad; boyfriend=sceneBF;
   members=[sceneGF,sceneDad,sceneBF];
   insertNode(members.indexOf(sceneGF),view);
   insertNode(members.indexOf(sceneDad),view);
   insertNode(members.indexOf(sceneBF),view);
   if(members.indexOf(view)!=0 || members.indexOf(sceneGF)!=1)
     throw "repeated Codename insert moved view past the first actor";
   removeNode(view);
   insertNode(2,view);
   if(members.indexOf(view)!=2) throw "remove then insert should explicitly reorder";
   behindGF(healthBarBG);
   if(members[0]!=healthBarBG || members[1]!=gf) throw "borrowed behind GF";
   var prop=new FlxBasic("prop"); addNode(prop); removeNode(prop);
   if(scope.owned.indexOf(prop)<0 || members.indexOf(prop)>=0) throw "removed owned prop lost";
   var other=new FlxBasic("other");
   codenameScriptScopes.push({owned:[other]});
   addNode(other);
   if(scope.owned.indexOf(other)>=0 || members.indexOf(other)>=0) throw "foreign object stolen";
   codenameMembership().release(scope);
   if(members[0]!=healthBarBG || healthBarBG.destroyed) throw "HUD membership rollback";
 }
 static function main():Void new Main().run();
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            work = Path(work)
            (work / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", work, "--run", "Main"],
                cwd=ROOT, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_real_helpers_dispatch_order_and_release_owned_objects(self):
        source = self.source

        def method(name):
            marker = "\tfunction " + name + "("
            start = source.index(marker)
            signature_end = re.search(r"\):(?:Bool|Void|String)\s*\{", source[start:])
            self.assertIsNotNone(signature_end, name)
            brace = start + signature_end.end() - 1
            depth = 0
            for index in range(brace, len(source)):
                depth += (source[index] == "{") - (source[index] == "}")
                if depth == 0:
                    return source[start:index + 1]
            raise AssertionError(name)

        helpers = "\n".join(method(name) for name in (
            "callCodenameScript", "callCodenameScripts", "releaseCodenameScope",
            "releaseCodenameStageScripts", "dispatchCodenamePostCreate",
            "setCodenameScriptsPaused", "codenameDifficulty"))
        fixture = '''typedef CodenameScriptFile = { var relative:String; var family:String; }
class FlxBasic {
  public var destroyed = false;
  public function new() {}
  public function destroy():Void destroyed = true;
}
class FakeCamera { public var alpha:Float = 1; public function new() {} }
class CodenameScriptDiscovery {
  public static function safeName(value:String):Bool return value != null && value != "" && value.indexOf("/") < 0;
}
class CodenameScriptInterp {
  public var variables:Map<String,Dynamic> = [];
  public var importedCallbacks:Map<String,Array<{callback:Dynamic,origin:String}>> = [];
  public var released = false;
  public var scriptDisabled:Bool = false;
  public function new() {}
  public function release():Void released = true;
  public function disableScript():Void scriptDisabled = true;
  public var paused = false;
  public function setPaused(value:Bool):Void paused = value;
}
class Main {
  public function new() {}
  var codenameScriptScopes:Array<{file:CodenameScriptFile, interp:CodenameScriptInterp,
    owned:Array<FlxBasic>, postCreated:Bool, failedCallbacks:Map<String,Bool>}> = [];
  var codenameCharacterScopes:Array<Dynamic> = [];
  var codenamePublicScriptGlobals:Dynamic = {
    releaseScope:function(_scope:String):Void {},
    detach:function(_interp:Dynamic):Void {}
  };
  var characterRefreshes:Int = 0;
  var comboGroup:Dynamic=null;
 var codenameNativeEventTweens:Map<String,Dynamic> = [];
  var codenameNativeEventResumeTweens:Map<String,Dynamic> = [];
  var members:Array<FlxBasic> = [];
  var stageSprites:Array<FlxBasic> = [];
  var codenameSceneMembership:CodenameSceneMembership<FlxBasic> = null;
  var camGame = new FakeCamera();
  var camHUD = new FakeCamera();
  var boyfriend:Dynamic = null; var dad:Dynamic = null; var gf:Dynamic = null;
  var curStage:Dynamic = null; var curStep = 7; var curBeat = 2;
  var storyDifficultyText = "HARD";
  var log:Array<String> = [];
  function protectedStageObject(_value:Dynamic):Bool return false;
  function remove(sprite:FlxBasic):Void { members.remove(sprite); }
  function removeGlobalSpriteReferences(_sprite:FlxBasic):Void {}
  function refreshCodenameHudBindings(_interp:CodenameScriptInterp):Void {}
  function refreshCodenameCharacterScopes():Void characterRefreshes++;
  function commitCodenameScriptLineActors():Void {}
  // Runtime visual telemetry is smoke-only; lifecycle tests do not configure it.
  function markCodenameRuntimeVisuals(_scope:Dynamic, _callback:String,
      ?_event:Dynamic):Void {}
''' + helpers + '''
  function make(family:String, failPost:Bool = false):Dynamic {
    var interp = new CodenameScriptInterp();
    var file:CodenameScriptFile = {relative:family + ".hx", family:family};
    var scope = {file:file, interp:interp, owned:new Array<FlxBasic>(),
      postCreated:false, failedCallbacks:new Map<String,Bool>()};
    interp.variables.set("create", function() log.push(family + ":create"));
    interp.variables.set("postCreate", function() {
      log.push(family + ":postCreate");
      if (failPost) { camGame.alpha = 0; throw "post failed"; }
    });
    interp.variables.set("onSongStart", function() log.push(family + ":songStart"));
    interp.variables.set("update", function(_elapsed:Float) log.push(family + ":update"));
    interp.variables.set("destroy", function() log.push(family + ":destroy"));
    codenameScriptScopes.push(scope);
    return scope;
  }
  function run():Void {
    var stage = make("stage");
    var song = make("song");
    var actor:Dynamic = {codenameGamePostCreated:false};
    var actorPaused = false;
    var actorRuntime:Dynamic = {
      call:function(name:String,_args:Array<Dynamic>):Bool {
        log.push("actor:" + name); return true;
      },
      setPaused:function(value:Bool):Void actorPaused = value
    };
    codenameCharacterScopes.push({actor:actor,runtime:actorRuntime});
    callCodenameScripts("create", []);
    dispatchCodenamePostCreate();
    dispatchCodenamePostCreate();
    if (!actor.codenameGamePostCreated || characterRefreshes != 2)
      throw "actor gamePostCreate refresh/count";
    callCodenameScripts("onSongStart", []);
    callCodenameScripts("update", [0.5]);
    if (log.join(",") != "stage:create,song:create,actor:gamePostCreate,stage:postCreate,song:postCreate,stage:songStart,song:songStart,stage:update,song:update")
      throw log.join(",");
    if (codenameDifficulty(["hard", "easy"]) != "hard"
        || codenameDifficulty(["Hard", "hard"]) != "") throw "difficulty case selection";
    storyDifficultyText = "hard";
    if (codenameDifficulty(["Hard", "hard"]) != "hard") throw "exact difficulty";
    setCodenameScriptsPaused(true);
    if (!stage.interp.paused || !song.interp.paused || !actorPaused) throw "pause";
    setCodenameScriptsPaused(false);
    if (stage.interp.paused || song.interp.paused || actorPaused) throw "resume";
    var failures = 0;
    song.interp.variables.set("update", function(_elapsed:Float) { failures++; throw "bad update"; });
    callCodenameScripts("update", [0.5]); callCodenameScripts("update", [0.5]);
    if (failures != 1) throw "repeated failing callback";
    var prop = new FlxBasic();
    stage.owned.push(prop); members.push(prop); stageSprites.push(prop);
    releaseCodenameStageScripts();
    if (codenameScriptScopes.length != 1 || !stage.interp.released || !prop.destroyed
      || members.indexOf(prop) >= 0 || stageSprites.indexOf(prop) >= 0) throw "stage leak";
    var broken = make("difficulty", true);
    dispatchCodenamePostCreate();
    if (camGame.alpha != 1 || !broken.interp.released || codenameScriptScopes.length != 1)
      throw "postCreate rollback";
    if (song.interp.released) throw "released unrelated song";
  }
  static function main():Void new Main().run();
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            work = Path(work)
            (work / "Main.hx").write_text(fixture)
            # This fixture extracts production lifecycle helpers without
            # Flixel. The newly instrumented callback path only needs inert
            # profiling hooks, so resolve this local shim before the project
            # classpath (which contains the full Flixel-backed harness).
            (work / "RuntimeSmokeHarness.hx").write_text('''class RuntimeSmokeHarness {
 public static function profileEnabled():Bool return false;
 public static function profileSection(_name:String,_seconds:Float):Void {}
}''')
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", work, "--run", "Main"],
                cwd=ROOT, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
