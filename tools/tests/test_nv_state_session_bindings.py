"""Behavioral seam checks for the NV source session and FlxG state bindings."""
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]

FIXTURE_TYPE_RENAMES = {
	"NightmareVisionHighscoreBindings": "FixtureHighscoreBindings",
	"NightmareVisionHighscore": "FixtureHighscore",
	"NightmareVisionMainMetadata": "FixtureMainMetadata",
	"NightmareVisionMainRuntime": "FixtureMainRuntime",
	"NightmareVisionMainBindings": "FixtureMainBindings",
	"NightmareVisionInitState": "FixtureInitState",
	"NightmareVisionSplashState": "FixtureSplashState",
	"NightmareVisionBootstrapServices": "FixtureBootstrapServices",
	"CodenameOwnerSaveData": "FixtureOwnerSaveData",
    "NightmareVisionModsContext": "OwnerMods",
    "NightmareVisionPaths": "OwnerPaths",
    "NightmareVisionClientPrefs": "OwnerPrefs",
    "NightmareVisionDifficultyAdapter": "OwnerDifficulty",
    "NightmareVisionScriptInterp": "FixtureScriptInterp",
    "NightmareVisionTitleState": "FixtureTitleState",
    "NightmareVisionMainMenuState": "FixtureMainMenuState",
    "NightmareVisionFlashingState": "FixtureFlashingState",
    "NightmareVisionUnportedState": "FixtureUnportedState",
    "NightmareVisionScriptedState": "FixtureScriptedState",
    "NightmareVisionMusicBeatSubstateHost": "FixtureMusicBeatSubstateHost",
    "NightmareVisionMusicBeatSubstate": "FixtureMusicBeatSubstate",
    "NightmareVisionScriptGroup": "FixtureScriptGroup",
    "NightmareVisionScriptBindings": "FixtureScriptBindings",
    "NightmareVisionModConfigBindings": "FixtureModConfigBindings",
    "NightmareVisionInputBindings": "FixtureInputBindings",
    "NightmareVisionMusicBeatState": "FixtureMusicBeatState",
    "NightmareVisionPluginHost": "FixturePluginHost",
    "NightmareVisionSpriteRegistry": "FixtureSpriteRegistry",
    "NightmareVisionAlphabetRegistry": "FixtureAlphabetRegistry",
    "NightmareVisionInputScope": "InputScope",
    "NightmareVisionConductor": "Conductor",
    "ImportedFreeplayCaller": "FixtureImportedFreeplayCaller",
    "FreeplayState": "FixtureFreeplayState",
    "PlayState": "FixturePlayState",
    "CoolUtil": "FixtureCoolUtil",
}


def fixture_rename(source: str) -> str:
    for original, replacement in FIXTURE_TYPE_RENAMES.items():
        source = source.replace(original, replacement)
    return source


def extract_method(source: str, marker: str) -> str:
    """Extract a Haxe method while ignoring braces in comments and strings."""
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    quote = None
    line_comment = False
    block_comment = False
    escaped = False
    index = brace
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and following == "/":
                block_comment = False
                index += 1
        elif quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char == "/" and following == "/":
            line_comment = True
            index += 1
        elif char == "/" and following == "*":
            block_comment = True
            index += 1
        elif char in ("'", '"'):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
        index += 1
    raise AssertionError(f"unterminated Haxe method: {marker}")


SESSION_METHODS = (
    "public static function adopt(",
    "public static function leaseForChart(",
    "public function new(mods:",
    "function ensureAlive(",
    "public function initializeSourceControls():Void {",
    "public function createStateFactory(",
    "public function switchState(",
    "public function resetState(",
    "public function switchWithTransition(",
    "public function requestedStateName(",
    "public function stateRedirectPath(",
    "public function scriptExists(",
    "public function makeScriptState(",
    "public function destroyState(",
    "public function afterPostStateSwitch(",
    "function onPreStateCreate(",
    "function onPostStateSwitch(",
    "public function substateHost():",
    "public function releaseStateResources(",
    "public function release():Void {",
    "public function install(",
)


class NVStateSessionBindingsTest(unittest.TestCase):
    def test_selected_redirect_reset_scope_bindings_cleanup_and_real_flxg_view(self):
        session_source = (ROOT / "source/NightmareVisionStateSession.hx").read_text(encoding="utf-8")
        view_source = (ROOT / "source/NightmareVisionFlxGView.hx").read_text(encoding="utf-8")
        play_source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        self.assertIn("public var hasPendingSwitch(get, never):Bool", session_source)
        self.assertIn("var result = factory.construct(request, resetConstructor);", session_source)
        self.assertIn("factory.resetState()", session_source)
        self.assertIn("scope.bindStaticField(type, 'new'", session_source)
        self.assertIn("view.bindStateRequests(switchState, resetState)", session_source)
        self.assertIn("stateRequests.clear();", view_source)
        self.assertIn("if (!sourceSession.bootstrapComplete) sourceSession.loadHighscores();", play_source)
        self.assertIn("mainRuntime.install();", session_source)
        self.assertIn("mainRuntime.release();", session_source)
        self.assertIn("startFullScreen:false", session_source)
        self.assertNotIn("startFullscreen:", session_source)

        extracted_methods = [extract_method(session_source, marker) for marker in SESSION_METHODS]
        for marker in ("function installBindings(", "public function installBindings(",
                       "function installStateBindings(", "public function installStateBindings("):
            if marker in session_source:
                extracted_methods.append(extract_method(session_source, marker))
                break
        methods = "\n\n".join(extracted_methods)
        play_adopt = extract_method(play_source, "public static function adoptNightmareVisionStateServices(")
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            session_fixture = fixture_rename(SESSION_FIXTURE.replace("__SESSION_METHODS__", methods))
            session_fixture = session_fixture.replace(
                "public function substateHost():FixtureMusicBeatSubstate.FixtureMusicBeatSubstateHost",
                "public function substateHost():Dynamic",
            )
            (work / "NightmareVisionStateSession.hx").write_text(session_fixture, encoding="utf-8")
            (work / "NightmareVisionVideoSprite.hx").write_text(
                "class NightmareVisionVideoSprite { public static function destroyForState(state:Dynamic):Void {} }",
                encoding="utf-8",
            )
            (work / "StateSessionFixtureTypes.hx").write_text(fixture_rename(
                FIXTURE_TYPES.replace("__PLAY_ADOPT__", play_adopt)
            ), encoding="utf-8")
            (work / "Main.hx").write_text(fixture_rename(MAIN_FIXTURE), encoding="utf-8")
            (work / "NightmareVisionSaveFacade.hx").write_text(SAVE_STUB, encoding="utf-8")
            (work / "CompatScriptClock.hx").write_text(CLOCK_STUB, encoding="utf-8")
            (work / "CompatScriptInputSnapshot.hx").write_text(INPUT_STUB, encoding="utf-8")
            (work / "flixel/FlxState.hx").parent.mkdir(parents=True)
            (work / "flixel/FlxState.hx").write_text(FLX_STATE_STUB, encoding="utf-8")
            (work / "flixel/FlxG.hx").write_text(FLX_G_STUB, encoding="utf-8")
            (work / "flixel/addons/transition/FlxTransitionableState.hx").parent.mkdir(parents=True)
            (work / "flixel/addons/transition/FlxTransitionableState.hx").write_text(
                TRANSITION_STUB, encoding="utf-8"
            )
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--main", "Main", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


SESSION_FIXTURE = r'''package;
import flixel.FlxG;
import flixel.FlxState;
import flixel.addons.transition.FlxTransitionableState;
import haxe.ds.ObjectMap;
import NightmareVisionModTransition;
import NightmareVisionStateFactory.INightmareVisionStateFactoryHost;
import NightmareVisionStateFactory.NightmareVisionStateTransitionOverrides;
import StateSessionFixtureTypes.Conductor;
import StateSessionFixtureTypes.FixtureLog;
import StateSessionFixtureTypes.InputScope;
import StateSessionFixtureTypes.CoolUtil;
import StateSessionFixtureTypes.NightmareVisionFlashingState;
import StateSessionFixtureTypes.NightmareVisionInputBindings;
import StateSessionFixtureTypes.NightmareVisionMainMenuState;
import StateSessionFixtureTypes.NightmareVisionModConfigBindings;
import StateSessionFixtureTypes.NightmareVisionMainBindings;
import StateSessionFixtureTypes.NightmareVisionMusicBeatState;
import StateSessionFixtureTypes.NightmareVisionMusicBeatSubstate;
import StateSessionFixtureTypes.NightmareVisionScriptBindings;
import StateSessionFixtureTypes.NightmareVisionScriptInterp;
import StateSessionFixtureTypes.NightmareVisionScriptedState;
import StateSessionFixtureTypes.NightmareVisionMusicBeatSubstate;
import StateSessionFixtureTypes.NightmareVisionUnportedState;
import StateSessionFixtureTypes.NightmareVisionTitleState;
import StateSessionFixtureTypes.OwnerConfig;
import StateSessionFixtureTypes.OwnerDifficulty;
import StateSessionFixtureTypes.OwnerMods;
import StateSessionFixtureTypes.OwnerPaths;
import StateSessionFixtureTypes.OwnerPrefs;
import StateSessionFixtureTypes.PluginRuntime;
import StateSessionFixtureTypes.NightmareVisionScriptGroup;
import StateSessionFixtureTypes.ImportedFreeplayCaller;
import StateSessionFixtureTypes.NightmareVisionAlphabetRegistry;
import StateSessionFixtureTypes.NightmareVisionPluginHost;
import StateSessionFixtureTypes.NightmareVisionSpriteRegistry;
import StateSessionFixtureTypes.PlayState;
import StateSessionFixtureTypes.FreeplayState;
import StateSessionFixtureTypes.NightmareVisionHighscore;
import StateSessionFixtureTypes.NightmareVisionHighscoreBindings;
import StateSessionFixtureTypes.NightmareVisionMainMetadata;
import StateSessionFixtureTypes.NightmareVisionMainRuntime;
import StateSessionFixtureTypes.NightmareVisionMainBindings;
import StateSessionFixtureTypes.NightmareVisionInitState;
import StateSessionFixtureTypes.NightmareVisionSplashState;
import StateSessionFixtureTypes.NightmareVisionBootstrapServices;
import StateSessionFixtureTypes.CodenameOwnerSaveData;

class NightmareVisionStateSession implements INightmareVisionStateFactoryHost {
 public static var active(default, null):NightmareVisionStateSession;
 public final mods:OwnerMods;
 public final paths:OwnerPaths;
 public final prefs:OwnerPrefs;
 public final difficulty:OwnerDifficulty;
 public final config:OwnerConfig;
 public final factory:NightmareVisionStateFactory;
 public final highscoreSave:CodenameOwnerSaveData;
 public final highscores:NightmareVisionHighscore;
 public final mainRuntime:NightmareVisionMainRuntime;
 public var startMeta:Dynamic;
 var bootstrapServices:NightmareVisionBootstrapServices;
 public var plugins:PluginRuntime;
 public var menuVocals:Dynamic;
 public var configureScript:FixtureScriptInterp->Void;
 public var titleInitialized:Bool = false;
 public var titleClosedState:Bool = false;
 public var flashingLeftState:Bool = false;
 public var mainMenuSelected:Int = 0;
 public var released(default, null):Bool = false;
 final inputs:InputScope;
 final conductor = new Conductor();
 final states:ObjectMap<FlxState, String> = new ObjectMap();
 final redirectNames:Map<String, String> = new Map();
 final postCallbacks:Array<Void->Void> = [];
 final previousSkipIn:Bool;
 final previousSkipOut:Bool;
 var requestedSwitch:Bool = false;
 public var hasPendingSwitch(get, never):Bool;
 function get_hasPendingSwitch():Bool return requestedSwitch && !released;
 public function titleInit():Void {titleInitialized=true;}
 public function services():NightmareVisionBootstrapServices {FixtureLog.events.push('services:create');return new NightmareVisionBootstrapServices();}
 public function reloadSourceControls():Void {}
 public function loadSourcePreferences():Void {}
 public function startupConstructor(type:Dynamic):Void->FlxState return function() return new FlxState();
 __SESSION_METHODS__
 public function stateHost():Dynamic return {session:this};
 public var lastScriptRequest:Dynamic;
 public function createScriptAt(prefix:String, name:String, parent:Dynamic, group:NightmareVisionScriptGroup):Dynamic {
  lastScriptRequest={prefix:prefix,name:name,parent:parent,group:group};return null;
 }
 public function getTransitionOverrides():NightmareVisionStateTransitionOverrides
  return {transitionIn:config.transitionIn, transitionOut:config.transitionOut};
 public function setTransitionOverrides(value:NightmareVisionStateTransitionOverrides):Void {
  config.transitionIn = value.transitionIn; config.transitionOut = value.transitionOut;
 }
 public function warnMissingRedirect(requestedName:String, ownerPath:String):Void {
  FixtureLog.events.push('warning:' + requestedName + ':' + ownerPath);
 }
 public function setTransSkip(skipIn:Bool = true, skipOut:Bool = true):Void {
  FlxTransitionableState.skipNextTransIn = skipIn;
  FlxTransitionableState.skipNextTransOut = skipOut;
 }
 public function report(name:String, callback:String, error:Dynamic):Void
  FixtureLog.events.push('report:' + name + ':' + callback);
}
'''


FIXTURE_TYPES = r'''package;
import flixel.FlxState;
using StringTools;

class FixtureLog {
 public static var events:Array<String> = [];
 public static var pendingAtTitle:Array<Bool> = [];
 public static var lastTitle:NightmareVisionTitleState;
 public static function clear():Void {events.resize(0);pendingAtTitle.resize(0);lastTitle=null;}
}

class OwnerConfig {
 public var transitionIn:Dynamic = 'base';
 public var transitionOut:Dynamic = 'base';
 public var released:Bool = false;
 public function new() {}
 public function release():Void {released=true;FixtureLog.events.push('release:config');}
}
class OwnerMods {
 public var ownerRoot:String;
 public var currentModConfig:Dynamic;
 public var nativeConfig:Dynamic;
 public var released:Bool = false;
 public var selected:String;
 public var authorized:Array<String>;
 public function new(root:String, config:Dynamic, selected:String) {
  ownerRoot=root;currentModConfig=config;nativeConfig=new OwnerConfig();this.selected=selected;authorized=[selected];
 }
 public function selectedRoot():String return selected;
 public function authorizedRoots():Array<String> return authorized;
 public function release():Void {released=true;FixtureLog.events.push('release:mods');}
}
class OwnerPaths {
 public var root:String;
 public var selectedRoot:String;
 public var files:Map<String,Bool> = new Map();
 public var lookups:Int = 0;
 public var released:Bool = false;
 public var authorizedRoots:Array<String>;
 public function new(root:String, selected:String, authorized:Array<String>) {
  this.root=root;selectedRoot=selected;authorizedRoots=authorized;
 }
 public function getPath(path:String, ?parent:String, checkMods:Bool=true):String {
  lookups++;
  if (path == null || path == '') return path;
  for (root in authorizedRoots) if (path == root || path.startsWith(root + '/')) return path;
  return selectedRoot + '/' + path;
 }
 public function scopeAssetPath(path:String):Null<String> {
  if (path == null) return null;
  for (root in authorizedRoots) if (path == root || path.startsWith(root + '/')) return path;
  return null;
 }
 public function exists(path:String):Bool return files.exists(path) && files.get(path);
 public function sanitize(path:String):String return path.toLowerCase();
 public function isDirectory(path:String):Bool return false;
 public function releaseOwnerAssets():Void {released=true;FixtureLog.events.push('release:paths');}
}
class OwnerPrefs {
 public var view:Dynamic = {noteOffset:0.0};
 public var released:Bool = false;
 public function new() {}
 public function canReuseFor(root:String):Bool return !released;
 public function release():Void {released=true;FixtureLog.events.push('release:prefs');}
}
class OwnerDifficulty {
 public var released:Bool = false;
 public function new() {}
 public function canReuseFor(root:String):Bool return !released;
 public function getDifficultyFilePath(index:Int):String return 'normal';
 public function release():Void {released=true;FixtureLog.events.push('release:difficulty');}
}
class InputScope {
 public var controls:Dynamic = {};
 public var destroyed:Bool = false;
 public function new(root:String, view:Dynamic, source:Bool, chart:Bool) {}
 public function resetControls():Void FixtureLog.events.push('inputs:reset');
 public function destroy():Void {destroyed=true;FixtureLog.events.push('release:input');}
}
class Conductor { public function new() {} }
class PluginRuntime {}
class CodenameOwnerSaveData {
 public function new(root:String) {}
 public function getField(name:String):Dynamic return null;
}
class NightmareVisionHighscore {
 public function new(save:Dynamic,sanitize:String->String,difficulty:Int->String) {}
 public function release():Void {}
}
class NightmareVisionHighscoreBindings {
 public static function install(interp:Dynamic,scores:Dynamic,requireActive:Void->Void):Void {}
}
class NightmareVisionMainMetadata {
 public static var NMV_VERSION='1.0';
 public static var PSYCH_VERSION='0.5.2h';
 public static var FUNKIN_VERSION='0.2.7';
}
class NightmareVisionMainRuntime {
 public final ownerRoot:String;
 var installed:Bool=false;
 public function new(ownerRoot:String) {this.ownerRoot=ownerRoot;FixtureLog.events.push('main:construct:' + ownerRoot);}
 public function install():Void {if (!installed) {installed=true;FixtureLog.events.push('main:install');}}
 public function release():Void {if (installed) {installed=false;FixtureLog.events.push('main:release');}}
 public function onResize(width:Int,height:Int):Void FixtureLog.events.push('main:resize');
}
class NightmareVisionMainBindings {
 public static var calls:Int=0;
 public static var lastStartMeta:Dynamic;
 public static var lastRuntime:NightmareVisionMainRuntime;
 public static function install(interp:NightmareVisionScriptInterp,startMeta:Dynamic,
  runtime:NightmareVisionMainRuntime):Void {
  calls++;lastStartMeta=startMeta;lastRuntime=runtime;
  interp.variables.set('Main',NightmareVisionMainMetadata);
  interp.bindImport('Main',NightmareVisionMainMetadata);
  interp.scope.bindRuntimeClass('Main',NightmareVisionMainMetadata);
  interp.scope.bindStaticField(NightmareVisionMainMetadata,'startMeta',function() return startMeta);
 }
}
class NightmareVisionInitState extends FlxState {
 public function new(session:Dynamic) {super();}
}
class NightmareVisionSplashState extends FlxState {
 public function new(host:Dynamic) {super();}
}
class NightmareVisionBootstrapServices {
 public function new() {}
 public function scriptTracingReady():Bool return false;
 public function configure(interp:Dynamic):Void {}
 public function release():Void {}
}
class NightmareVisionInputBindings {
 public static function install(interp:NightmareVisionScriptInterp, root:String,
  inputOwner:Dynamic->Dynamic, parent:Dynamic->Dynamic):Void {}
}
class NightmareVisionPluginHost {
 public static function releaseOtherOwner(root:String):Void FixtureLog.events.push('release:plugins');
}
class NightmareVisionSpriteRegistry { public static function enterSession(root:String):Void {} }
class NightmareVisionAlphabetRegistry { public static function enterSession(root:String):Void {} }
class ImportedFreeplayCaller {
 public static var lastPackage:String;
 public static var captures:Int = 0;
 public static function capturePackage(root:String):Void {lastPackage=root;captures++;}
}

class NightmareVisionScriptBindings {
 public static function getPath(path:String, paths:OwnerPaths):String {
  var candidate=paths.getPath(path + '.hscript',null,true);
  return paths.exists(candidate) ? candidate : path;
 }
}
class NightmareVisionModConfigBindings {
 public static var installs:Int = 0;
 public static function install(interp:NightmareVisionScriptInterp, config:OwnerConfig, owner:Dynamic):Void {
  installs++;
  interp.variables.set('MusicBeatState', owner);
  interp.bindImport('funkin.backend.MusicBeatState', owner);
  interp.scope.bindRuntimeClass('funkin.backend.MusicBeatState', owner);
 }
}

class NightmareVisionTitleState extends FlxState {
 public final session:Dynamic;
 public function new(session:Dynamic) {
  super('TitleState');this.session=session;FixtureLog.lastTitle=this;
  FixtureLog.pendingAtTitle.push(Reflect.getProperty(session,'hasPendingSwitch') == true);
  FixtureLog.events.push('construct:TitleState');
 }
}
class NightmareVisionMainMenuState extends FlxState {
 public final session:Dynamic;
 public function new(session:Dynamic) {super('MainMenuState');this.session=session;}
}
class NightmareVisionFlashingState extends FlxState {
 public final session:Dynamic;
 public function new(session:Dynamic) {super('FlashingState');this.session=session;}
}
class NightmareVisionUnportedState extends FlxState {
 public function new(name:String, session:Dynamic) super('Unported:' + name);
}
class PlayState extends FlxState {
 public static var nightmareVisionActiveMods:OwnerMods;
 public static var nightmareVisionActivePrefs:OwnerPrefs;
 public static var nightmareVisionActiveDifficulty:OwnerDifficulty;
 public var root:String;
 public function new(?root:String='') {super('PlayState');this.root=root;}
 public function nightmareVisionSelectedRoot():String return root;
 public static function activeNightmareVisionInputScope(owner:Dynamic):Dynamic return null;
 __PLAY_ADOPT__
}
class FreeplayState extends FlxState { public function new() super('FreeplayState'); }
class ExternalState extends FlxState { public function new() super('ExternalState'); }
class NightmareVisionScriptedState extends NightmareVisionMusicBeatState {
  public final scriptName:String;
  public final host:Dynamic;
  public function new(name:String, host:Dynamic) {
  super(host);logName='ScriptedState';scriptName=name;this.host=host;
  FixtureLog.events.push('script:onLoad:' + name);
 }
}
class NightmareVisionMusicBeatState extends FlxState {
 public final sourceHost:Dynamic;
 public function new(host:Dynamic) {super('MusicBeatState');sourceHost=host;}
}
class NightmareVisionMusicBeatSubstate {
 public final sourceHost:Dynamic;
 public function new(host:Dynamic) {sourceHost=host;}
}
typedef NightmareVisionMusicBeatSubstateHost = Dynamic;
class NightmareVisionScriptGroup {}
class CoolUtil {}

class BindingRecord {
 public final type:Dynamic; public final name:String;
 public final getter:Void->Dynamic; public final setter:Dynamic->Dynamic;
 public function new(type:Dynamic,name:String,getter:Void->Dynamic,setter:Dynamic->Dynamic) {
  this.type=type;this.name=name;this.getter=getter;this.setter=setter;
 }
}
class RuntimeClassScope {
 public var runtimeClasses:Map<String,Dynamic> = new Map();
 public var statics:Array<BindingRecord> = [];
 public function new() {}
 public function bindRuntimeClass(path:String,type:Dynamic):Void runtimeClasses.set(path,type);
 public function bindStaticField(type:Dynamic,name:String,getter:Void->Dynamic,?setter:Dynamic->Dynamic):Void
  statics.push(new BindingRecord(type,name,getter,setter));
 public function readStatic(type:Dynamic,name:String):Dynamic {
  for (binding in statics) if (binding.type == type && binding.name == name) return binding.getter();
  return null;
 }
 public function writeStatic(type:Dynamic,name:String,value:Dynamic):Void {
  for (binding in statics) if (binding.type == type && binding.name == name && binding.setter != null) {
   binding.setter(value);return;
  }
  throw 'missing static setter: ' + name;
 }
}
class ConstructorBinding {
 public final type:Dynamic; public final make:Array<Dynamic>->Dynamic;
 public function new(type:Dynamic,make:Array<Dynamic>->Dynamic) {this.type=type;this.make=make;}
}
class NightmareVisionScriptInterp {
 public var variables:Map<String,Dynamic> = new Map();
 public var imports:Map<String,Dynamic> = new Map();
 public var scope:RuntimeClassScope = new RuntimeClassScope();
 public var constructors:Array<ConstructorBinding> = [];
 public var parent:Dynamic;
 public function new() {}
 public function sourceClassScope():RuntimeClassScope return scope;
 public function bindImport(path:String,type:Dynamic):Void imports.set(path,type);
 public function bindConstructorFactory(type:Dynamic,make:Array<Dynamic>->Dynamic,superFactory:Dynamic):Void
  constructors.push(new ConstructorBinding(type,make));
 public function construct(type:Dynamic,args:Array<Dynamic>):Dynamic {
  for (binding in constructors) if (binding.type == type) return binding.make(args);
  throw 'missing constructor factory';
 }
}
'''


MAIN_FIXTURE = r'''package;
import flixel.FlxG;
import flixel.FlxState;
import NightmareVisionFlxGView;
import StateSessionFixtureTypes.ExternalState;
import StateSessionFixtureTypes.FixtureLog;
import StateSessionFixtureTypes.FreeplayState;
import StateSessionFixtureTypes.ImportedFreeplayCaller;
import StateSessionFixtureTypes.NightmareVisionModConfigBindings;
import StateSessionFixtureTypes.NightmareVisionMainBindings;
import StateSessionFixtureTypes.NightmareVisionMusicBeatState;
import StateSessionFixtureTypes.NightmareVisionMusicBeatSubstate;
import StateSessionFixtureTypes.NightmareVisionScriptInterp;
import StateSessionFixtureTypes.NightmareVisionScriptedState;
import StateSessionFixtureTypes.NightmareVisionTitleState;
import StateSessionFixtureTypes.NightmareVisionUnportedState;
import StateSessionFixtureTypes.OwnerConfig;
import StateSessionFixtureTypes.OwnerDifficulty;
import StateSessionFixtureTypes.OwnerMods;
import StateSessionFixtureTypes.OwnerPaths;
import StateSessionFixtureTypes.OwnerPrefs;
import StateSessionFixtureTypes.PlayState;

class Main {
 static function check(ok:Bool,message:String):Void if (!ok) throw message;
 static function call(fn:Dynamic,args:Array<Dynamic>):Dynamic return Reflect.callMethod(null,fn,args);
 static function ordered(events:Array<String>,before:String,after:String):Bool {
  return events.indexOf(before) >= 0 && events.indexOf(after) >= 0
   && events.indexOf(before) < events.indexOf(after);
 }
 static function expectThrow(fn:Void->Void,fragment:String):Void {
  var caught=false;try fn() catch (error:Dynamic) caught=Std.string(error).indexOf(fragment)>=0;
  check(caught,'expected error containing ' + fragment);
 }
 static function main():Void {
  FixtureLog.clear();
  var lease='assets/imported_mods/family';
  var ownerA=lease + '/a';
  var ownerB=lease + '/b';
  var configA:Dynamic={stateRedirects:{TitleState:'WelcomeA'}};
  var mods=new OwnerMods(lease,configA,ownerA);
  var paths=new OwnerPaths(lease,ownerA,[lease]);
  paths.files.set(ownerA + '/scripts/states/WelcomeA.hscript',true);
  mods.nativeConfig=new OwnerConfig();
  var prefs=new OwnerPrefs();
  var difficulty=new OwnerDifficulty();
  var session=NightmareVisionStateSession.adopt(mods,paths,prefs,difficulty);
  var mainRuntime:Dynamic=Reflect.field(session,'mainRuntime');
  check(mainRuntime!=null && Reflect.field(mainRuntime,'ownerRoot')==lease,
   'each captured session must construct its Main runtime for the immutable owner root');
  check(Reflect.hasField(session.startMeta,'startFullScreen')
   && !Reflect.hasField(session.startMeta,'startFullscreen'),
   'source start metadata must use the donor startFullScreen spelling');
  session.initializeSourceControls();
  check(ordered(FixtureLog.events,'main:install','services:create')
   && ordered(FixtureLog.events,'services:create','inputs:reset'),
   'source Main listeners must install before services and input controls are prepared');
  check(NightmareVisionStateSession.active==session,
   'adopting owner services must activate the source-bound session');
  check(NightmareVisionStateSession.adopt(mods,paths,prefs,difficulty)==session,
   'adopting the same mods context must preserve the captured source session');
  check(NightmareVisionStateSession.leaseForChart(ownerA)==lease,
   'the authenticated selected family package must receive its family service lease');
  check(NightmareVisionStateSession.leaseForChart(ownerB)==ownerB,
   'a foreign family package must retain its actual chart root');
  mods.authorized=[];
  check(NightmareVisionStateSession.leaseForChart(ownerA)==ownerA,
   'a selected package outside the captured authorization set must retain its chart root');
  mods.authorized=[ownerA];
  PlayState.adoptNightmareVisionStateServices(session);
  check(PlayState.nightmareVisionActiveMods==mods && PlayState.nightmareVisionActivePrefs==prefs
   && PlayState.nightmareVisionActiveDifficulty==difficulty,
   'source gameplay construction must adopt the session owner services');

  var nativeCalls=0;
  var nativeFlxG:Dynamic={
   switchState:function(next:Dynamic) {nativeCalls++;return 'native-switch';},
   resetState:function() {nativeCalls++;return 'native-reset';}
  };
  var save=new NightmareVisionSaveFacade();
  var view=new NightmareVisionFlxGView(nativeFlxG,save);
  check(call(view.getField('switchState'),[null])=='native-switch' && nativeCalls==1,
   'unbound FlxG view must continue forwarding native state requests');
  var interp=new NightmareVisionScriptInterp();
  interp.variables.set('FlxG',view);
  session.install(interp);
  check(FixtureMainBindings.calls==1 && FixtureMainBindings.lastStartMeta==session.startMeta
   && FixtureMainBindings.lastRuntime==mainRuntime,
   'session installation must pass its captured metadata and Main runtime into owner bindings');
  check(FixtureLog.events.filter(function(event) return event=='main:install').length==1,
   'Init setup and state binding must share one idempotently installed Main listener lease');
  check(nativeCalls==1,'install must replace only the captured view state request fields');
  check(interp.imports.get('funkin.states.TitleState')==NightmareVisionTitleState
   && interp.scope.runtimeClasses.get('funkin.states.TitleState')==NightmareVisionTitleState,
   'source import and runtime class lookup must bind the owner title type');
  check(NightmareVisionModConfigBindings.installs==1,
   'session install must attach this owner config to the interpreter');

  var musicBeatType:Dynamic=interp.imports.get('funkin.backend.MusicBeatState');
  check(musicBeatType==NightmareVisionMusicBeatState
   && interp.variables.get('MusicBeatState')==musicBeatType
   && interp.scope.runtimeClasses.get('funkin.backend.MusicBeatState')==musicBeatType,
   'MusicBeatState source class must be imported and available to runtime lookup');
  var musicBeat:Dynamic=interp.construct(musicBeatType,[]);
  check(Std.isOfType(musicBeat,NightmareVisionMusicBeatState)
   && (cast musicBeat:NightmareVisionMusicBeatState).sourceHost.session==session,
   'MusicBeatState constructor factory must capture its source host');
  var musicBeatNew:Dynamic=interp.scope.readStatic(musicBeatType,'new');
  var musicBeatFromScope:Dynamic=call(musicBeatNew,[]);
  check(Std.isOfType(musicBeatFromScope,NightmareVisionMusicBeatState)
   && (cast musicBeatFromScope:NightmareVisionMusicBeatState).sourceHost.session==session,
   'MusicBeatState class-scope .new must use its captured constructor');

  var substateType:Dynamic=interp.imports.get('funkin.backend.MusicBeatSubstate');
  check(substateType==NightmareVisionMusicBeatSubstate
   && interp.variables.get('MusicBeatSubstate')==substateType
   && interp.scope.runtimeClasses.get('funkin.backend.MusicBeatSubstate')==substateType,
   'MusicBeatSubstate must be available by source import and runtime lookup');
  var substate:Dynamic=interp.construct(substateType,[]);
  var substateHost:Dynamic=(cast substate:NightmareVisionMusicBeatSubstate).sourceHost;
  check(Reflect.field(substateHost,'session')==session
   && Reflect.isFunction(Reflect.field(substateHost,'createSubstateScript')),
   'MusicBeatSubstate constructor must retain the captured session and script callback');
  var substateScript:Dynamic=Reflect.field(substateHost,'createSubstateScript');
  call(substateScript,['substates','CapturedSubstate',substate,null]);
  check(Reflect.field(session.lastScriptRequest,'name')=='CapturedSubstate'
   && Reflect.field(session.lastScriptRequest,'parent')==substate,
   'substate host must route script creation with the original name and parent');
  var substateNew:Dynamic=interp.scope.readStatic(substateType,'new');
  var substateFromScope:Dynamic=call(substateNew,[]);
  check(Std.isOfType(substateFromScope,NightmareVisionMusicBeatSubstate)
   && Reflect.field((cast substateFromScope:NightmareVisionMusicBeatSubstate).sourceHost,'session')==session,
   'MusicBeatSubstate class-scope .new must retain this source session');

  var scriptedType:Dynamic=interp.imports.get('funkin.scripting.ScriptedState');
  check(scriptedType==NightmareVisionScriptedState
   && interp.variables.get('ScriptedState')==scriptedType
   && interp.scope.runtimeClasses.get('funkin.scripting.ScriptedState')==scriptedType,
   'ScriptedState wrapper must bind as the source script class');
  var directScript:Dynamic=interp.construct(scriptedType,['KeepOriginalScriptName']);
  check(Std.isOfType(directScript,NightmareVisionScriptedState)
   && (cast directScript:NightmareVisionScriptedState).scriptName=='KeepOriginalScriptName'
   && Reflect.field((cast directScript:NightmareVisionScriptedState).host,'session')==session,
   'direct ScriptedState construction must preserve the requested name and captured session');
  var scriptedNew:Dynamic=interp.scope.readStatic(scriptedType,'new');
  var scopedScript:Dynamic=call(scriptedNew,['ScopedOriginalName']);
  check((cast scopedScript:NightmareVisionScriptedState).scriptName=='ScopedOriginalName'
   && Reflect.field((cast scopedScript:NightmareVisionScriptedState).host,'session')==session,
   'ScriptedState class-scope .new must preserve its source name and captured session');

  var genericState:Dynamic=session.createStateFactory('AdditionalSourceState')();
  check(Std.isOfType(genericState,NightmareVisionUnportedState)
   && session.requestedStateName(genericState)=='AdditionalSourceState',
   'generic source constructor provider must retain an unported source class name');

  var titleType:Dynamic=interp.imports.get('funkin.states.TitleState');
  var importedTitle:Dynamic=interp.construct(titleType,[]);
  check(Std.isOfType(importedTitle,NightmareVisionTitleState)
   && (cast importedTitle:NightmareVisionTitleState).session==session,
   'constructor factory must capture this session instead of consulting a later active session');
  var newClosure:Dynamic=interp.scope.readStatic(titleType,'new');
  var scopeTitle:Dynamic=call(newClosure,[]);
  check(Std.isOfType(scopeTitle,NightmareVisionTitleState)
   && (cast scopeTitle:NightmareVisionTitleState).session==session,
   'source class-scope .new must return the same captured owner constructor');
  var initializedGetter:Dynamic=interp.scope.readStatic(titleType,'initialized');
  check(initializedGetter==false,'TitleState.initialized must start in the captured session');
  interp.scope.writeStatic(titleType,'initialized',true);
  check(session.titleInitialized,'TitleState.initialized writes must reach the captured session');

  var switchRequest:Dynamic=view.getField('switchState');
  call(switchRequest,[session.createStateFactory('TitleState')]);
  check(Std.isOfType(FlxG.state,NightmareVisionScriptedState),
   'configured owner title should be redirected through the real session request method');
  var scripted:NightmareVisionScriptedState=cast FlxG.state;
  check(scripted.scriptName=='WelcomeA' && Reflect.field(scripted.host,'session')==session,
   'redirect wrapper must keep the source name and captured session host');
  check(paths.lookups==1 && ordered(FixtureLog.events,'destroy:TitleState','script:onLoad:WelcomeA'),
   'selected package lookup and intended-state destruction must precede scripted onLoad');
  check(ordered(FixtureLog.events,'script:onLoad:WelcomeA','create:ScriptedState'),
   'scripted create must follow constructor onLoad');
  check(FixtureLog.pendingAtTitle.indexOf(true)>=0 && !session.hasPendingSwitch,
   'the source request readiness flag spans construction and clears before the switch completes');
  FlxG.signals.postStateSwitch.dispatch([]);

  var retained=session.factory.lastConstructor;
  var lookupsBeforeReset=paths.lookups;
  call(view.getField('resetState'),[]);
  check(Std.isOfType(FlxG.state,NightmareVisionScriptedState)
   && (cast FlxG.state:NightmareVisionScriptedState).scriptName=='WelcomeA',
   'reset must run the exact redirected constructor captured on the first request');
  check(paths.lookups==lookupsBeforeReset && session.factory.lastConstructor==retained,
   'reset must not re-read stateRedirects or replace its captured constructor');
  FlxG.signals.postStateSwitch.dispatch([]);

  // Flixel's legacy state-instance overload uses a fresh no-arg constructor
  // for reset. The instance is used once, then the source factory is replayed.
  mods.currentModConfig={stateRedirects:{}};
  var legacyInstance:FlxState=session.createStateFactory('FreeplayState')();
  call(switchRequest,[legacyInstance]);
  check(FlxG.state==legacyInstance,'legacy instance request must use the supplied state the first time');
  FlxG.signals.postStateSwitch.dispatch([]);
  var freeplayCaptures=ImportedFreeplayCaller.captures;
  call(view.getField('resetState'),[]);
  check(Std.isOfType(FlxG.state,FreeplayState) && FlxG.state!=legacyInstance
   && ImportedFreeplayCaller.captures==freeplayCaptures+1,
   'legacy reset must use the source createStateFactory closure and build a fresh FreeplayState');
  FlxG.signals.postStateSwitch.dispatch([]);

  // Switch the family selection to a package whose configured redirect is
  // absent, then change back before reset to prove fallback constructor capture.
  mods.currentModConfig={stateRedirects:{TitleState:'MissingB'}};
  mods.selected=ownerB;
  paths.selectedRoot=ownerB;
  var missingLookups=paths.lookups;
  call(switchRequest,[session.createStateFactory('TitleState')]);
  check(Std.isOfType(FlxG.state,NightmareVisionTitleState)
   && FixtureLog.lastTitle!=null && !FixtureLog.lastTitle.destroyed,
   'missing selected-owner script must warn and retain the requested native title');
  check(FixtureLog.events.indexOf('warning:TitleState:' + ownerB + '/scripts/states/MissingB')>=0,
   'missing owner script diagnostic must name the selected package path');
  check(paths.lookups==missingLookups+2,
   'missing-script resolution should check the script candidate and scope its selected-owner fallback');
  FlxG.signals.postStateSwitch.dispatch([]);
  mods.currentModConfig=configA;
  mods.selected=ownerA;
  paths.selectedRoot=ownerA;
  var beforeFallbackReset=paths.lookups;
  call(view.getField('resetState'),[]);
  check(Std.isOfType(FlxG.state,NightmareVisionTitleState),
   'failed redirect must retain the requested native constructor for reset');
  check(paths.lookups==beforeFallbackReset,
   'reset after a failed redirect must not re-check a newly available config redirect');
  FlxG.signals.postStateSwitch.dispatch([]);

  // An unrelated destination retires the owner after old-state destruction
  // and before that destination creates its UI.
  FixtureLog.events.resize(0);
  call(switchRequest,[function():Dynamic return new ExternalState()]);
  check(session.released && NightmareVisionStateSession.active==null,
   'leaving the imported owner must release and detach its session');
  check(ordered(FixtureLog.events,'destroy:TitleState','release:plugins')
   && ordered(FixtureLog.events,'release:plugins','release:config')
   && ordered(FixtureLog.events,'release:config','release:paths')
   && ordered(FixtureLog.events,'release:paths','release:mods')
   && ordered(FixtureLog.events,'release:difficulty','create:ExternalState'),
   'owner cleanup must run after old-state destroy and before unrelated-state create');
  expectThrow(function() call(switchRequest,[session.createStateFactory('TitleState')]),
   'Released source session');
  view.release();
  expectThrow(function() view.getField('switchState'), 'FlxG view has been released');
  check(FixtureLog.events.indexOf('main:release')>=0,
   'releasing the captured state session must release its Main event listeners');

  var coldRoot=lease + '/cold';
  var coldMods=new OwnerMods(coldRoot,{},coldRoot);
  var coldPaths=new OwnerPaths(coldRoot,coldRoot,[coldRoot]);
  coldMods.nativeConfig=new OwnerConfig();
  var coldSession=NightmareVisionStateSession.adopt(coldMods,coldPaths,new OwnerPrefs(),new OwnerDifficulty());
  var coldInterp=new NightmareVisionScriptInterp();
  coldSession.install(coldInterp);
  var coldRuntime:Dynamic=Reflect.field(coldSession,'mainRuntime');
  check(FixtureLog.events.indexOf('main:install')>=0
   && FixtureMainBindings.calls==2 && FixtureMainBindings.lastRuntime==coldRuntime,
   'cold gameplay binding must install and bind its owner Main runtime without Init controls');
  coldSession.release();
 }
}
'''


SAVE_STUB = r'''package;
class NightmareVisionSaveFacade { public function new() {} }
'''
CLOCK_STUB = r'''package;
class CompatScriptClock { public var tickElapsed:Float=1/60; public function new() {} }
'''
INPUT_STUB = r'''package;
class CompatScriptInputSnapshot {
 public function new(keys:Map<String,Int>) {}
 public function sample(keys:Dynamic):Void {}
 public function view(keys:Dynamic,tickIndex:Int,tickCount:Int):Dynamic return {};
 public function finishSourceBatch():Void {}
}
'''


FLX_STATE_STUB = r'''package flixel;
import StateSessionFixtureTypes.FixtureLog;
class FlxState {
 public var logName:String;
 public var destroyed:Bool=false;
 public function new(?logName:String='State') this.logName=logName;
 public function create():Void FixtureLog.events.push('create:' + logName);
 public function destroy():Void {destroyed=true;FixtureLog.events.push('destroy:' + logName);}
}
'''


FLX_G_STUB = r'''package flixel;
import StateSessionFixtureTypes.FixtureLog;
class FixtureSignal {
 var listeners:Array<Dynamic>=[];
 var once:Array<Dynamic>=[];
 public function new() {}
 public function add(callback:Dynamic):Void listeners.push(callback);
 public function addOnce(callback:Dynamic):Void once.push(callback);
 public function remove(callback:Dynamic):Void {listeners.remove(callback);once.remove(callback);}
 public function dispatch(?args:Array<Dynamic>):Void {
  if (args==null) args=[];
  for (callback in listeners.copy()) Reflect.callMethod(null,callback,args);
  var pending=once.copy();once.resize(0);
  for (callback in pending) Reflect.callMethod(null,callback,args);
 }
}
class FixtureSignals {
 public final preStateCreate:FixtureSignal=new FixtureSignal();
 public final postStateSwitch:FixtureSignal=new FixtureSignal();
 public final preStateSwitch:FixtureSignal=new FixtureSignal();
 public function new() {}
}
class FlxG {
 public static var state:FlxState;
 public static final signals:FixtureSignals=new FixtureSignals();
 public static function switchState(next:Void->FlxState):Void {
  signals.preStateSwitch.dispatch([]);
  if (state!=null) state.destroy();
  var target=next();
  signals.preStateCreate.dispatch([target]);
  state=target;
  target.create();
 }
}
'''


TRANSITION_STUB = r'''package flixel.addons.transition;
class FlxTransitionableState {
 public static var skipNextTransIn:Bool=false;
 public static var skipNextTransOut:Bool=false;
}
'''


if __name__ == "__main__":
    unittest.main()
