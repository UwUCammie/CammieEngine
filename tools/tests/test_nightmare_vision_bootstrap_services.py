"""Pinned NV bootstrap service behavior and native Flixel API checks."""
import os
import shutil
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND


ROOT = Path(__file__).resolve().parents[2]


MODULES = (
    "NightmareVisionBootstrapServices.hx",
    "NightmareVisionSourceDiagnostics.hx",
    "NightmareVisionSound.hx",
    "NightmareVisionRatioScaleMode.hx",
    "NightmareVisionHotReloadPlugin.hx",
    "NightmareVisionFullScreenPlugin.hx",
    "NightmareVisionDebugTextPlugin.hx",
)


class NightmareVisionBootstrapServicesTest(unittest.TestCase):
    def test_owner_lifecycle_and_hot_reload_order_on_pinned_flixel(self):
        if not (ROOT / ".tools/haxe/haxe.exe" if os.name == "nt" else ROOT / ".tools/haxe/haxe").is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        main = r'''
import flixel.FlxG;
import flixel.util.FlxColor;
import NightmareVisionBootstrapServices;
import NightmareVisionHotReloadPlugin;
import NightmareVisionSourceDiagnostics;

class FixtureControls {
 public var soft:Bool=false;
 public var hard:Bool=false;
 public var SOFT_RELOAD(get,never):Bool;
 public var HARD_RELOAD(get,never):Bool;
 public function new() {}
 function get_SOFT_RELOAD():Bool return soft;
 function get_HARD_RELOAD():Bool return hard;
}

class FixtureKeyManager<Key:Int> {
 public var preventDefaultKeys:Array<Key>;
 public function new(keys:Array<Key>) this.preventDefaultKeys = keys;
}

@:access(NightmareVisionBootstrapServices)
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var keyManager = new FixtureKeyManager<Int>([8, 9]);
  var originalContainer:Dynamic = Reflect.field(keyManager, 'preventDefaultKeys');
  var originalValues:Array<Int> = (cast originalContainer:Array<Int>).copy();
  var restoreKeys = NightmareVisionBootstrapServices.installRawFieldOverride(
   keyManager, 'preventDefaultKeys', function() keyManager.preventDefaultKeys = [13]);
  var sourceContainer:Dynamic = Reflect.field(keyManager, 'preventDefaultKeys');
  var sourceValues:Array<Int> = cast sourceContainer;
  check(sourceContainer != originalContainer && sourceValues.length == 1 && sourceValues[0] == 13,
   'the owner installs a new raw generic key container with its source value');
  restoreKeys();
  var restoredValues:Array<Int> = cast Reflect.field(keyManager, 'preventDefaultKeys');
  check(Reflect.field(keyManager, 'preventDefaultKeys') == originalContainer
   && restoredValues.length == originalValues.length
   && restoredValues[0] == originalValues[0] && restoredValues[1] == originalValues[1],
   'release restores the exact prior generic key container and values');

  var restoreAfterReplacement = NightmareVisionBootstrapServices.installRawFieldOverride(
   keyManager, 'preventDefaultKeys', function() keyManager.preventDefaultKeys = [13]);
  var replacementOwnerKeys:Array<Int> = [4, 5];
  keyManager.preventDefaultKeys = replacementOwnerKeys;
  restoreAfterReplacement();
  var replacementValues:Array<Int> = cast Reflect.field(keyManager, 'preventDefaultKeys');
  check(Reflect.field(keyManager, 'preventDefaultKeys') == replacementOwnerKeys
   && replacementValues.length == 2 && replacementValues[0] == 4 && replacementValues[1] == 5,
   'release leaves a replacement owner key container and its values untouched');

  var liveKeyManager:Dynamic = keyManager;
  var replacementKeyManager = new FixtureKeyManager<Int>([3]);
  var restoreAfterManagerReplacement = NightmareVisionBootstrapServices.installRawFieldOverride(
   keyManager, 'preventDefaultKeys', function() keyManager.preventDefaultKeys = [13],
   function() return liveKeyManager == keyManager);
  var ownerKeyContainer:Dynamic = Reflect.field(keyManager, 'preventDefaultKeys');
  liveKeyManager = replacementKeyManager;
  restoreAfterManagerReplacement();
  var retainedOwnerValues:Array<Int> = cast Reflect.field(keyManager, 'preventDefaultKeys');
  check(Reflect.field(keyManager, 'preventDefaultKeys') == ownerKeyContainer
   && retainedOwnerValues.length == 1 && retainedOwnerValues[0] == 13
   && replacementKeyManager.preventDefaultKeys.length == 1 && replacementKeyManager.preventDefaultKeys[0] == 3,
   'release leaves both a replacement manager and the retired manager container untouched');

  var paths = new NightmareVisionPaths('assets/imported_mods/selected');
  var badOwner = false;
  try new NightmareVisionBootstrapServices('assets/imported_mods/other', {}, paths,
   function() return null, function() {}, function() {}, function() {})
  catch (error:Dynamic) badOwner = Std.string(error).indexOf('Paths does not belong') >= 0;
  check(badOwner, 'services must reject a Paths lease owned by another package');

  var services = new NightmareVisionBootstrapServices('assets/imported_mods/selected',
   {globalAntialiasing:true, autoPause:true, inDevMode:true}, paths,
   function() return null, function() {}, function() {}, function() {},
   function(_name:String, _value:Dynamic) {});
  check(!services.scriptTracingReady(), 'trace binding starts disabled before the donor step');
  services.initializeFunkinScript();
  check(services.scriptTracingReady(), 'the donor FunkinScript step enables owner trace configuration');
  var earlyTraceRejected = false;
  try services.configure(new NightmareVisionScriptInterp())
  catch (error:Dynamic) earlyTraceRejected = Std.string(error).indexOf('DebugTextPlugin has not been initialized') >= 0;
  check(earlyTraceRejected, 'trace configuration requires the source DebugText service');
  services.release();
  check(!services.scriptTracingReady(), 'released source tracing is disabled');

  var console:Array<String> = [];
  var diagnostics = new NightmareVisionSourceDiagnostics('assets/imported_mods/selected',
   'assets/imported_mods/selected/__nmv_core', function(message:String) console.push(message));
  diagnostics.reportError('bad-script', 'module', 'parse failure');
  check(console.length == 1 && console[0].indexOf('[ERROR] [bad-script]: PARSING ERROR: parse failure') >= 0,
   'module errors retain their source label and immediate console output');
  var debugMessages:Array<String> = [];
  var debugColours:Array<FlxColor> = [];
  diagnostics.bindDebugText(function(message:String, colour:FlxColor) {
   debugMessages.push(message); debugColours.push(colour);
  });
  check(debugMessages.length == 1 && debugMessages[0].indexOf('PARSING ERROR: parse failure') >= 0
   && debugColours[0] == FlxColor.fromRGB(255, 64, 64),
   'queued module errors reach the owner DebugText sink in source error red');
  var diagnosticInterp = new NightmareVisionScriptInterp();
  diagnostics.bindIris(diagnosticInterp);
  check(diagnosticInterp.variables.exists('Iris')
   && diagnosticInterp.importBindings.exists('crowplexus.iris.Iris')
   && diagnosticInterp.sourceError != null,
   'source scripts resolve an owner-bound Iris facade by identifier and import');
  Reflect.callMethod(null, diagnosticInterp.sourceError,
   ['unknown target', {fileName:'assets/imported_mods/selected/__nmv_core/scripts/test.hx',
    lineNumber:11,className:'Fixture',methodName:'main'}]);
  check(debugMessages[1].indexOf('[scripts/test.hx:11] - unknown target') >= 0
   && debugColours[1] == FlxColor.fromRGB(255, 64, 64),
   'the interpreter internal error callback uses the source error route');
  var iris:Dynamic = diagnosticInterp.variables.get('Iris');
  Reflect.callMethod(iris, Reflect.field(iris, 'print'), ['printed']);
  Reflect.callMethod(iris, Reflect.field(iris, 'warn'), ['warning']);
  Reflect.callMethod(iris, Reflect.field(iris, 'error'), ['failure']);
  check(debugMessages.length == 5 && debugMessages[2].indexOf('[scripts/test.hx:7] - printed') >= 0
   && debugMessages[3].indexOf('warning') >= 0 && debugMessages[4].indexOf('failure') >= 0,
   'owner Iris print, warn, and error use the current source position');
  check(debugColours[2] == FlxColor.WHITE && debugColours[3] == FlxColor.YELLOW
   && debugColours[4] == FlxColor.fromRGB(255, 64, 64),
   'owner Iris methods retain donor print, warning, and error colors');
  diagnostics.release();

  var controls = new FixtureControls();
  var prefs:Dynamic = {inDevMode:true};
  var events:Array<String> = [];
  var plugin = new NightmareVisionHotReloadPlugin(prefs, function() return controls,
   function() events.push('reset'), function() events.push('populate'),
   function() events.push('config'), function() events.push('clear-cache'));
  controls.soft = true;
  controls.hard = true;
  plugin.update(1 / 60);
  check(events.join(',') == 'reset,config,populate,reset,config',
   'soft and hard actions retain donor callback ordering when both are pressed');
  FlxG.signals.preStateCreate.dispatch(null);
  check(events.join(',') == 'reset,config,populate,reset,config,clear-cache',
   'hard reload clears only the owner cache immediately before state creation');

  events.resize(0);
  prefs.inDevMode = false;
  plugin.update(1 / 60);
  check(events.length == 0, 'release builds honor the source inDevMode hot-reload gate');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            for name in MODULES:
                shutil.copyfile(ROOT / "source" / name, work / name)
            (work / "NightmareVisionPaths.hx").write_text(r'''package;
class NightmareVisionPaths {
 public final root:String;
 public final CORE_DIRECTORY:String;
 public function new(root:String) {this.root=root; CORE_DIRECTORY=root + '/__nmv_core';}
 public function font(key:String, checkMods:Bool=true):String return 'assets/fonts/' + key + '.ttf';
 public function exists(path:String):Bool return true;
 public function getOwnerAssetCache():Dynamic return new FixtureAssetCache();
}
class FixtureAssetCache {
 public function new() {}
 public function clearStoredMemory():Void {}
 public function clearUnusedMemory():Void {}
}
''', encoding="utf-8", newline="\n")
            (work / "NightmareVisionScriptInterp.hx").write_text(r'''package;
class NightmareVisionScriptInterp {
 public var variables:Map<String,Dynamic> = new Map();
 public var importBindings:Map<String,Dynamic> = new Map();
 public var sourceError:Dynamic;
 public function new() {}
 public function bindImport(path:String, value:Dynamic):Void importBindings.set(path, value);
 public function posInfos():haxe.PosInfos
  return {fileName:'assets/imported_mods/selected/__nmv_core/scripts/test.hx',lineNumber:7,className:'Fixture',methodName:'main'};
}
''', encoding="utf-8", newline="\n")
            (work / "Main.hx").write_text(main, encoding="utf-8", newline="\n")
            env = os.environ.copy()
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["HAXEPATH"] = str(ROOT / ".tools/haxe")
            env["NEKOPATH"] = str(ROOT / ".tools/neko")
            env["PATH"] = os.pathsep.join((env["HAXEPATH"], env["NEKOPATH"], env.get("PATH", "")))
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "-lib", "flixel", "-lib", "flixel-addons",
                 "-lib", "openfl", "-lib", "lime", "-lib", "hxvlc", "-lib", "hscript-iris",
                 "--macro", "flixel.system.macros.FlxDefines.run()", "--interp", "-main", "Main"],
                cwd=work, env=env, capture_output=True, text=True, timeout=75,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('printed', result.stdout)
        self.assertIn('warning', result.stdout)
        self.assertIn('failure', result.stdout)

    def test_native_contract_uses_typed_source_services_and_conditional_restore(self):
        source = (ROOT / "source/NightmareVisionBootstrapServices.hx").read_text(encoding="utf-8")
        for contract in (
            "applySourceSoundKeys(", "scriptTracingReady():Bool", "FlxG.fixedTimestep = false",
            "game.focusLostFramerate = 60", "keys.preventDefaultKeys = sourcePreventDefaultKeys",
            "installRawFieldOverride(keys, 'preventDefaultKeys'",
            "Reflect.field(target, field) == installedContainer",
            "Reflect.setField(target, field, previousContainer)",
            "function() return FlxG.keys == keys",
            "new NightmareVisionRatioScaleMode()", "new NightmareVisionSound()",
            "FlxG.signals.preStateSwitch.add(resetOwnerScale)",
            "FlxG.signals.preStateSwitch.remove(resetOwnerScale)",
            "paths.getOwnerAssetCache()", "Handle.init()", "TracyProfiler.frameMark()",
            "FlxSprite.defaultAntialiasing == sourceDefaultAntialiasing",
            "FlxG.sound.muteKeys == sourceMuteKeys", "FlxG.sound.music == sourceMusic",
            "Source DebugText font assets/fonts/consolas.ttf are missing",
            "public function reportError(name:String, callback:String, error:Dynamic)",
            "diagnostics.bindIris(interp)",
            "applySourceAudioPreferences(volume:Dynamic, muted:Dynamic)",
            "captureAudioBaseline()", "restoreAudioPreferences()",
            "previousAudioVolume = FlxG.sound.volume", "previousAudioMuted = FlxG.sound.muted",
            "if (FlxG.sound.volume == sourceAudioVolume)",
            "if (FlxG.sound.muted == sourceAudioMuted)",
        ):
            self.assertIn(contract, source)
        self.assertNotIn("FlxG.keys.preventDefaultKeys == sourcePreventDefaultKeys", source)
        self.assertNotIn("FlxG.updateFramerate =", source)
        self.assertNotIn("FlxG.drawFramerate =", source)
        self.assertNotIn("Iris.warn =", source)
        self.assertNotIn("Iris.error =", source)

        diagnostics = (ROOT / "source/NightmareVisionSourceDiagnostics.hx").read_text(encoding="utf-8")
        for contract in (
            "interp.bindImport('crowplexus.iris.Iris', facade)",
            "Iris.logLevel(severity, value, position)",
            "FlxColor.YELLOW", "FlxColor.WHITE", "PARSING ERROR:",
            "pending.push({message:message, colour:colour})",
        ):
            self.assertIn(contract, diagnostics)
        self.assertNotIn("Iris.warn =", diagnostics)
        self.assertNotIn("Iris.error =", diagnostics)

        full_screen = (ROOT / "source/NightmareVisionFullScreenPlugin.hx").read_text(encoding="utf-8")
        self.assertIn("writeOwnerSave('fullscreen', FlxG.fullscreen)", full_screen)
        self.assertNotIn("writeOwnerSave", full_screen.split("public function release()", 1)[1])
        self.assertIn("if (hasSourceFullscreen && FlxG.fullscreen == lastSourceFullscreen)", full_screen)


if __name__ == "__main__":
    unittest.main()
