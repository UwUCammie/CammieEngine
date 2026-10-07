"""Pinned source Init ordering, splash selection, and plugin switch contracts."""
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionBootstrapTest(unittest.TestCase):
    def test_bootstrap_contract_is_typed_and_keeps_native_work_in_host(self):
        source = (ROOT / "source/NightmareVisionBootstrap.hx").read_text(encoding="utf-8")
        for operation in (
            "initializeControls():Void",
            "loadPreferences():Void",
            "loadHighscores():Void",
            "restoreCompletedWeeks():Void",
            "applyDefaultAntialiasing():Void",
            "initializeDiscord():Void",
            "pushGlobalMods():Void",
            "loadTopMod():Void",
            "configureFlixelServices():Void",
            "initializeFunkinScript():Void",
            "initializeHotReloadPlugin():Void",
            "initializeModPlugin():Void",
            "initializeDebugTextPlugin():Void",
            "initializeFullScreenPlugin():Void",
            "populateModPlugin():Void",
            "retainPermanentMenuMusicAsset():Void",
            "createBaseState():Void",
            "startMetaSkipsSplash():Bool",
            "splashScreenEnabled():Bool",
            "initialStateConstructor():Void->TState",
            "splashStateConstructor():Void->TState",
            "switchStartup(constructor:Void->TState):Void",
        ):
            self.assertIn(operation, source)
        self.assertNotIn("flixel.", source)
        self.assertNotIn("Dynamic", source)
        self.assertNotIn("Type.createInstance", source)

    def test_init_order_splash_choice_and_plugin_queued_constructor(self):
        main = r'''
import NightmareVisionBootstrap.INightmareVisionBootstrapHost;

class RecordingHost implements INightmareVisionBootstrapHost<String> {
 public var calls:Array<String> = [];
 public var queued:Array<Void->String> = [];
 public var pending:Null<Void->String>;
 public var throwAt:Null<String>;
 public var skipSplash:Bool = false;
 public var splashEnabled:Bool = true;
 public var pluginRequestsStartup:Bool = false;

 public function new() {}
 function step(name:String):Void {
  calls.push(name);
  if (throwAt == name) throw 'failed:' + name;
 }
 public function initializeControls():Void step('controls');
 public function loadPreferences():Void step('preferences');
 public function loadHighscores():Void step('highscores');
 public function restoreCompletedWeeks():Void step('week-completed');
 public function applyDefaultAntialiasing():Void step('default-antialiasing');
 public function initializeDiscord():Void step('discord');
 public function pushGlobalMods():Void step('global-mods');
 public function loadTopMod():Void step('load-top-mod');
 public function configureFlixelServices():Void step('flixel-services');
 public function initializeFunkinScript():Void step('funkin-script');
 public function initializeHotReloadPlugin():Void step('hot-reload-plugin');
 public function initializeModPlugin():Void step('mod-plugin');
 public function initializeDebugTextPlugin():Void step('debug-text-plugin');
 public function initializeFullScreenPlugin():Void step('fullscreen-plugin');
 public function initializeVideoPluginWhenEnabled():Void step('video-plugin-if-enabled');
 public function initializeTracyWhenEnabled():Void step('tracy-if-enabled');
 public function populateModPlugin():Void {
  step('populate-plugin');
  if (pluginRequestsStartup) {
   calls.push('plugin-onLoad');
   switchStartup(function():String return 'source-plugin-request');
  }
 }
 public function retainPermanentMenuMusicAsset():Void step('menu-music-cache-key');
 public function createBaseState():Void step('base-create');
 public function startMetaSkipsSplash():Bool {
  step('skip-splash');
  return skipSplash;
 }
 public function splashScreenEnabled():Bool {
  step('splash-enabled');
  return splashEnabled;
 }
 public function initialStateConstructor():Void->String {
  step('start-meta-initial-state-class');
  return function():String return 'source-initial-state';
 }
 public function splashStateConstructor():Void->String {
  step('splash-class');
  return function():String return 'source-splash-state';
 }
 public function switchStartup(constructor:Void->String):Void {
  step('switch-startup');
  queued.push(constructor);
  pending = constructor;
 }
}

class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var host = new RecordingHost();
  host.pluginRequestsStartup = true;
  host.skipSplash = true;
  new NightmareVisionBootstrap<String>(host).run();
  check(host.calls.join(',') == 'controls,preferences,highscores,week-completed,default-antialiasing,discord,global-mods,load-top-mod,flixel-services,funkin-script,hot-reload-plugin,mod-plugin,debug-text-plugin,fullscreen-plugin,video-plugin-if-enabled,tracy-if-enabled,populate-plugin,plugin-onLoad,switch-startup,menu-music-cache-key,base-create,skip-splash,start-meta-initial-state-class,switch-startup',
   'Init must preserve donor operations and their exact relative order');
  check(host.queued.length == 2,
   'a source request from plugin onLoad must be queued before the final Init startup request');
  check(host.queued[0]() == 'source-plugin-request' && host.pending() == 'source-initial-state',
   'plugin and startMeta closures must retain their typed source states');
  check(host.calls.indexOf('plugin-onLoad') < host.calls.indexOf('start-meta-initial-state-class'),
   'startup state selection must happen only after plugin population and base create');

  var splash = new RecordingHost();
  splash.skipSplash = false;
  splash.splashEnabled = true;
  new NightmareVisionBootstrap<String>(splash).run();
  check(splash.pending() == 'source-splash-state'
   && splash.calls.indexOf('start-meta-initial-state-class') < 0,
   'enabled splash selects Splash without first reading the initialState class');

  var disabled = new RecordingHost();
  disabled.skipSplash = false;
  disabled.splashEnabled = false;
  new NightmareVisionBootstrap<String>(disabled).run();
  check(disabled.pending() == 'source-initial-state',
   'disabled splash selects Main.startMeta.initialState');

  var failed = new RecordingHost();
  failed.throwAt = 'load-top-mod';
  var threw = false;
  try new NightmareVisionBootstrap<String>(failed).run() catch (_:Dynamic) threw = true;
  check(threw && failed.calls.join(',') == 'controls,preferences,highscores,week-completed,default-antialiasing,discord,global-mods,load-top-mod',
   'bootstrap failures must propagate and stop later host operations');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(main, encoding="utf-8")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--main", "Main", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
