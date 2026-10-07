"""Exercise the real Nightmare Vision Init host through its real bootstrap."""
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionInitHostTest(unittest.TestCase):
    def test_real_host_runs_ordered_bootstrap_and_preserves_both_startup_requests(self):
        main = r'''
import flixel.FlxState;
class TitleState extends FlxState { public function new() super(); }
class ReplacementTitleState extends FlxState { public function new() super(); }
class SplashState extends FlxState { public function new() super(); }
class PluginState extends FlxState { public function new() super(); }

class HostHarness {
 public static var calls:Array<String> = [];
 public static function add(value:String):Void calls.push(value);
 public static function reset():Void calls = [];
}

class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  HostHarness.reset();
  var session = new NightmareVisionStateSession();
  var host = new NightmareVisionInitHost(session, function():Void HostHarness.add('base-create'));
  new NightmareVisionBootstrap<FlxState>(host).run();
  var expected = 'controls,preferences,highscores,week-restore,antialiasing,rpc,global-mods,top-mod,'
   + 'flixel-services,funkin-script,hot-reload,mount-plugins:false,debug-text,fullscreen,video,tracy,'
   + 'populate-plugins,switch:0,path:music/freakyMenu.ogg:null:false,owner-cache,'
   + 'permanent:core/music/freakyMenu.ogg,base-create,typed-initial:TitleState,switch:1';
  check(HostHarness.calls.join(',') == expected,
   'the real Init host must preserve donor work, owner music pinning, and selection order: ' + HostHarness.calls.join(','));
  check(session.bootstrapComplete, 'bootstrapComplete must be set after native FlxState.create');
  check(session.queued.length == 2,
   'plugin onLoad state request must remain queued before the final Init startup request');
  check(Type.getClassName(Type.getClass(session.queued[0]())) == 'PluginState',
   'the plugin startup request must retain its state constructor');
  check(Type.getClassName(Type.getClass(session.queued[1]())) == 'TitleState',
   'the typed startMeta initialState factory must retain the selected class');

  // The selected startMeta class is captured when the final Init request is
  // made, rather than looked up when the queued constructor is later invoked.
  HostHarness.reset();
  var captured = new NightmareVisionStateSession();
  captured.startMeta.initialState = TitleState;
  var capturedHost = new NightmareVisionInitHost(captured, function():Void {});
  new NightmareVisionBootstrap<FlxState>(capturedHost).run();
  captured.startMeta.initialState = ReplacementTitleState;
  check(Type.getClassName(Type.getClass(captured.queued[1]())) == 'TitleState',
   'startMeta.initialState must be read as a typed class and snapshotted into its constructor');

  // A writable Substate scriptPrefix may literally be "states". The state
  // selection contract is still based on the actual constructor metadata.
  HostHarness.reset();
  var splash = new NightmareVisionStateSession();
  splash.startMeta.skipSplash = false;
  splash.prefs.view.toggleSplashScreen = true;
  var splashHost = new NightmareVisionInitHost(splash, function():Void {});
  new NightmareVisionBootstrap<FlxState>(splashHost).run();
  check(HostHarness.calls.indexOf('state-factory:Splash') >= 0
   && Type.getClassName(Type.getClass(splash.queued[1]())) == 'SplashState',
   'enabled Splash must be selected after plugins and base create');

  HostHarness.reset();
  RuntimeSmokeHarness.smokeEnabled = true;
  var smoke = new NightmareVisionStateSession();
  new NightmareVisionBootstrap<FlxState>(new NightmareVisionInitHost(smoke, function():Void {})).run();
  check(HostHarness.calls.indexOf('rpc') < 0,
   'the native smoke mode must continue to suppress the external Discord RPC');
  RuntimeSmokeHarness.smokeEnabled = false;
 }
}
'''
        session_stub = r'''
package;
import flixel.FlxState;
import Main.HostHarness;
class SourceStartMeta {
 public var skipSplash:Bool;
 public var initialState:Class<FlxState>;
 public function new(skip:Bool, initial:Class<FlxState>) {
  skipSplash = skip; initialState = initial;
 }
}
class Highscores { public function new() {} public function load():Void HostHarness.add('highscores'); }
class ModManager {
 public function new() {}
 public function pushGlobalMods():Void HostHarness.add('global-mods');
 public function loadTopMod():Void HostHarness.add('top-mod');
}
class NativeServices {
 public function new() {}
 public function applyDefaultAntialiasing():Void HostHarness.add('antialiasing');
 public function configureFlixelServices():Void HostHarness.add('flixel-services');
 public function initializeFunkinScript():Void HostHarness.add('funkin-script');
 public function initializeHotReloadPlugin():Void HostHarness.add('hot-reload');
 public function initializeDebugTextPlugin():Void HostHarness.add('debug-text');
 public function initializeFullScreenPlugin():Void HostHarness.add('fullscreen');
 public function initializeVideoPluginWhenEnabled():Void HostHarness.add('video');
 public function initializeTracyWhenEnabled():Void HostHarness.add('tracy');
}
class AssetSounds {
 public function new() {}
 public function addPermanentKey(key:String):Void HostHarness.add('permanent:' + key);
}
class AssetCache {
 public var currentTrackedSounds:AssetSounds = new AssetSounds();
 public function new() {}
}
class Paths {
 public function new() {}
 public function getPath(path:String, ?library:String, checkMods:Bool = true):String {
  HostHarness.add('path:' + path + ':' + (library == null ? 'null' : library) + ':' + checkMods);
  return 'core/' + path;
 }
 public function getOwnerAssetCache():AssetCache { HostHarness.add('owner-cache'); return new AssetCache(); }
}
class PrefView { public var toggleSplashScreen:Bool = true; public function new() {} }
class Prefs { public var view:PrefView = new PrefView(); public function new() {} }
class NightmareVisionStateSession {
 public var queued:Array<Void->FlxState> = [];
 public var highscores:Highscores = new Highscores();
 public var mods:ModManager = new ModManager();
 public var prefs:Prefs = new Prefs();
 public var startMeta:SourceStartMeta = new SourceStartMeta(true, Main.TitleState);
 public var paths:Paths = new Paths();
 public var bootstrapComplete:Bool = false;
 public var nativeServices:NativeServices = new NativeServices();
 public function new() {}
 public function initializeSourceControls():Void HostHarness.add('controls');
 public function loadSourcePreferences():Void HostHarness.add('preferences');
 public function loadHighscores():Void HostHarness.add('highscores');
 public function restoreCompletedWeeks():Void HostHarness.add('week-restore');
 public function services():NativeServices return nativeServices;
 public function mountPlugins(boot:Bool):Void HostHarness.add('mount-plugins:' + boot);
 public function populatePlugins():Void {
  HostHarness.add('populate-plugins');
  switchState(function():FlxState return new Main.PluginState());
 }
 public function startupConstructor(initial:Class<FlxState>):Void->FlxState {
  HostHarness.add('typed-initial:' + Type.getClassName(initial));
  var selected:Class<FlxState> = initial;
  return function():FlxState return Type.createInstance(selected, []);
 }
 public function createStateFactory(name:String):Void->FlxState {
  HostHarness.add('state-factory:' + name);
  return function():FlxState return new Main.SplashState();
 }
 public function switchState(constructor:Void->FlxState):Void {
  HostHarness.add('switch:' + queued.length);
  queued.push(constructor);
 }
}
'''
        runtime_smoke_stub = r'''
class RuntimeSmokeHarness {
 public static var smokeEnabled:Bool = false;
 public static function enabled():Bool return smokeEnabled;
}
'''
        discord_stub = r'''
import Main.HostHarness;
class DiscordClient { public static function initialize():Void HostHarness.add('rpc'); }
'''
        host_source = (ROOT / "source/NightmareVisionInitHost.hx").read_text(encoding="utf-8")
        # Exercise the production cpp-only RPC branch on the portable eval
        # target without changing the host method body.
        host_source = host_source.replace("#if cpp", "#if testCpp")
        with tempfile.TemporaryDirectory(prefix="nmv-init-host-", dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(main, encoding="utf-8", newline="\n")
            (work / "NightmareVisionStateSession.hx").write_text(session_stub, encoding="utf-8", newline="\n")
            (work / "RuntimeSmokeHarness.hx").write_text(runtime_smoke_stub, encoding="utf-8", newline="\n")
            (work / "Discord.hx").write_text(discord_stub, encoding="utf-8", newline="\n")
            (work / "NightmareVisionInitHost.hx").write_text(host_source, encoding="utf-8", newline="\n")
            (work / "flixel").mkdir()
            (work / "flixel/FlxG.hx").write_text("package flixel; class FlxG {}\n", encoding="utf-8")
            (work / "flixel/FlxState.hx").write_text("package flixel; class FlxState { public function new() {} }\n", encoding="utf-8")
            result = subprocess.run(
                [*HAXE_COMMAND, "-D", "testCpp", "-cp", str(ROOT / "source"), "-cp", str(work),
                 "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
