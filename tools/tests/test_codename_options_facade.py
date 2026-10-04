"""Exercise the shared Codename Options import facade without the game target."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class CodenameOptionsFacadeTest(unittest.TestCase):
    def test_import_maps_known_reads_and_preserves_native_settings(self):
        bindings = (ROOT / "source/CodenameImportBindings.hx").read_text()
        self.assertIn(
            "bindings.set('funkin.options.Options', new CodenameOptionsFacade());",
            bindings,
        )
        mod_bindings = (ROOT / "source/CodenameModBindings.hx").read_text()
        self.assertIn("for (name in bindings.keys())", mod_bindings)
        self.assertNotIn(
            "interp.variables.set('Options', {downscroll:OptionsHandler.options.downscroll});",
            mod_bindings,
            "owner-scoped seeds must retain the full detached Options facade",
        )
        self.assertIn("'P1_NOTE_LEFT'", (ROOT / "source/CodenameOptionsFacade.hx").read_text())
        self.assertIn("keyToString:function(key:Dynamic)", (ROOT / "source/CodenameModBindings.hx").read_text())
        controls_source = (ROOT / "source/Controls.hx").read_text()
        self.assertIn("applyCodenameMenuKeys();", controls_source)
        self.assertIn("Reflect.field(FlxG.save.data, 'codenameMenuKeys')", controls_source)
        self.assertIn("'UP', 'DOWN', 'LEFT', 'RIGHT'", controls_source)

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "CodenameOptionsQualityCompat.hx").write_text(
                (ROOT / "source/CodenameOptionsQualityCompat.hx").read_text()
            , newline='\n')
            (base / "FramerateOptionsCompat.hx").write_text(
                (ROOT / "source/FramerateOptionsCompat.hx").read_text(), newline='\n'
            )
            (base / "OptionsHandler.hx").write_text("""class OptionsHandler {
 public static var options:Dynamic = {
 downscroll:true, useCustomInput:false, offset:12.5, zoomCamera:true,
  fpsCap:120, unlimitedFPS:false, flashingLights:true, autoPause:true, antialiasing:true,
 quality:1, week6PixelPerfect:true,
  gameplayShaders:true, lowMemoryMode:false, gpuOnlyBitmaps:true,
  naughtyness:true, volumeMusic:0.8, volumeSFX:0.7, useCharColor:true, untouched:"keep"
 };
 public static inline var MAX_FPS_CAP:Int=2147483647;
 public static function sanitizeFpsCap(value:Dynamic):Int {
  if (value==null || !(Std.isOfType(value, Int) || Std.isOfType(value, Float))) return 60;
  var fps:Float=value;
  if (!Math.isFinite(fps) || fps<=0) return 60;
  return Std.int(Math.floor(Math.min(MAX_FPS_CAP, fps)+0.5));
 }
 public static function applyDisplayOptions(opt:Dynamic):Void
  flixel.FlxSprite.defaultAntialiasing=opt.antialiasing;
 public static function applyAudioOptions(opt:Dynamic):Void {
  flixel.FlxG.sound.defaultMusicGroup.volume=opt.volumeMusic;
  flixel.FlxG.sound.defaultSoundGroup.volume=opt.volumeSFX;
 }
}
""", newline='\n')
            (base / "Controls.hx").write_text("""class Controls {
 public var bindings:Map<String,Array<Int>> = new Map();
 public function new(seed:Map<String,Array<Int>>) {
  for (name in seed.keys()) bindings.set(name,seed.get(name).copy());
 }
 public function getKeyboardBindingsByName(name:String):Array<Int> {
  var keys=bindings.get(name); return keys==null?[]:keys.copy();
 }
 public function setKeyboardBindingsByName(name:String,keys:Array<Int>):Void
  bindings.set(name,keys.copy());
}
""", newline='\n')
            (base / "PlayerSettings.hx").write_text("""class PlayerSettings {
 public static var player1:PlayerSettings = new PlayerSettings(makeControls());
 public static var player2:PlayerSettings = new PlayerSettings(makeControls());
 public var controls:Controls;
 public function new(controls:Controls) this.controls=controls;
 static function makeControls():Controls {
  var keys:Map<String,Array<Int>>=new Map();
  keys.set('LEFT',[65,37]); keys.set('DOWN',[83,40]); keys.set('UP',[87,38]); keys.set('RIGHT',[68,39]);
  keys.set('LEFT_MENU',[65,37]); keys.set('DOWN_MENU',[83,40]); keys.set('UP_MENU',[87,38]); keys.set('RIGHT_MENU',[68,39]);
  keys.set('ACCEPT',[90,32,13]); keys.set('BACK',[8,27]); keys.set('RESET',[82]); keys.set('PAUSE',[80,13,27]);
  return new Controls(keys);
 }
}
""", newline='\n')
            (base / "flixel/input/keyboard/FlxKey.hx").parent.mkdir(parents=True, exist_ok=True)
            (base / "flixel/input/keyboard/FlxKey.hx").write_text("""package flixel.input.keyboard;
class FlxKey { public static var toStringMap:Map<Int,String>=[65=>'A',37=>'LEFT']; }
""", newline='\n')
            (base / "flixel/Save.hx").write_text("""package flixel;
class Save { public var data:Dynamic={keys:{left:[65,37]}};public var flushes:Int=0;
 public function new(){} public function flush():Bool {flushes++;return true;} }
""", newline='\n')
            (base / "flixel/FlxG.hx").write_text("""package flixel;
class FlxG { public static var save:Save=new Save();public static var autoPause:Bool=true;
 public static var updateFramerate:Int=60;public static var drawFramerate:Int=60;
 public static var fixedTimestep:Bool=true;public static var game:FlxGame=new FlxGame();
 public static var sound:Dynamic={defaultMusicGroup:{volume:1.0},defaultSoundGroup:{volume:1.0}}; }
""", newline='\n')
            (base / "flixel/FlxGame.hx").write_text("""package flixel;
class FlxGame { var _maxAccumulation:Float=1; public function new() {} }
""", newline='\n')
            (base / "flixel/FlxSprite.hx").write_text("""package flixel;
class FlxSprite { public static var defaultAntialiasing:Bool=false;
 public var antialiasing:Bool=defaultAntialiasing; public function new(){} }
""", newline='\n')
            (base / "flixel/FlxBasic.hx").write_text("""package flixel;
class FlxBasic {}
""", newline='\n')
            (base / "flixel/group/FlxGroup.hx").parent.mkdir(parents=True, exist_ok=True)
            (base / "flixel/group/FlxGroup.hx").write_text("""package flixel.group;
class FlxGroup {}
class FlxTypedGroup<T> {}
""", newline='\n')
            (base / "flixel/group/FlxSpriteGroup.hx").write_text("""package flixel.group;
class FlxSpriteGroup {}
class FlxTypedSpriteGroup<T> {}
""", newline='\n')
            (base / "flixel/tweens/FlxTween.hx").parent.mkdir(parents=True, exist_ok=True)
            (base / "flixel/tweens/FlxTween.hx").write_text("""package flixel.tweens;
class FlxTween {}
""", newline='\n')
            (base / "Conductor.hx").write_text("""class Conductor { public static var songOffset:Float=0; }""", newline='\n')
            (base / "Main.hx").write_text('''import hscript.Interp;
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var options = new CodenameOptionsFacade();
	  trace("FACADE_CONSTRUCTED");
  var allowed:Map<String, Dynamic> = new Map();
  allowed.set("funkin.options.Options", options);
  allowed.set("CoolUtil", {keyToString:CodenameKeyCodeCompat.keyToString});
  var parsed = CodenameScriptParser.prepare(
   'import funkin.options.Options; '
   + 'function run() { '
   + 'if (!Options.downscroll || Options.ghostTapping || Options.songOffset != 12.5 '
   + '|| !Options.camZoomOnBeat || Options.framerate != 120 || !Options.flashingMenu '
   + '|| !Options.antialiasing || !Options.autoPause || !Options.gameplayShaders '
   + '|| !Options.naughtyness || Options.volumeMusic != 0.8 || Options.volumeSFX != 0.7 '
   + '|| !Options.colorHealthBar '
   + '|| Options.quality != 1 || !Options.week6PixelPerfect '
   + '|| Options.lowMemoryMode || !Options.gpuOnlyBitmaps) '
   + 'throw "Codename options read mapping changed"; '
   + 'Reflect.setField(Options, "downscroll", false); '
   + 'Reflect.setField(Options, "ghostTapping", true); '
   + 'Reflect.setField(Options, "songOffset", 55); '
   + 'Reflect.setField(Options, "camZoomOnBeat", false); '
   + 'Reflect.setField(Options, "framerate", 144); '
   + 'Reflect.setField(Options, "flashingMenu", false); '
   + 'Reflect.setField(Options, "naughtyness", false); '
   + 'Reflect.setField(Options, "volumeMusic", 0.3); '
   + 'Reflect.setField(Options, "volumeSFX", 0.4); '
   + 'Reflect.setField(Options, "colorHealthBar", false); '
   + 'Reflect.setField(Options, "week6PixelPerfect", false); '
   + 'Reflect.setField(Options, "quality", 2); '
   + 'Reflect.setField(Options, "autoPause", false); '
   + 'Reflect.setField(Options, "antialiasing", false); '
   + 'Reflect.setField(Options, "gameplayShaders", false); '
   + 'Reflect.setField(Options, "lowMemoryMode", true); '
   + 'Reflect.setField(Options, "gpuOnlyBitmaps", false); '
   + 'if (Options.antialiasing) throw "antialiasing write lost"; '
   + 'if (Options.P1_NOTE_LEFT[0] != 65 || Options.P2_NOTE_LEFT[0] != 37 '
   + '|| Options.P1_LEFT[0] != 65 || Options.P2_LEFT[0] != 37) '
   + 'throw "primary/alternate native control mapping changed"; '
   + 'if (CoolUtil.keyToString(65) != "A" || CoolUtil.keyToString(0) != "NONE") '
   + 'throw "key display mapping changed"; '
   + 'Reflect.setField(Options, "P1_NOTE_LEFT", [74]); '
   + 'Reflect.setField(Options, "P2_NOTE_LEFT", [75]); '
   + 'Reflect.setField(Options, "P1_LEFT", [76]); '
   + 'Reflect.setField(Options, "P2_LEFT", [77]); '
   + 'Options.save(); Options.applySettings(); }', allowed);
  check(parsed.program != null && parsed.diagnostics.length == 0,
   parsed.diagnostics.length == 0 ? "no parsed program" : parsed.diagnostics[0].message);
  var interp = new Interp();
  interp.variables.set("Options", options);
  interp.variables.set("Reflect", Reflect);
  interp.variables.set("CoolUtil", {keyToString:CodenameKeyCodeCompat.keyToString});
  interp.execute(parsed.program);
  var run:Dynamic = interp.variables.get("run");
  run();
  var native:Dynamic = OptionsHandler.options;
  check(Reflect.field(native, "downscroll") == false
   && Reflect.field(native, "useCustomInput") == true
   && Reflect.field(native, "offset") == 55
   && Reflect.field(native, "zoomCamera") == false
   && Reflect.field(native, "fpsCap") == 144
   && Reflect.field(native, "flashingLights") == false
   && Reflect.field(native, "autoPause") == false
   && Reflect.field(native, "antialiasing") == false
   && Reflect.field(native, "gameplayShaders") == false
   && Reflect.field(native, "lowMemoryMode") == true
   && Reflect.field(native, "gpuOnlyBitmaps") == false
   && Reflect.field(native, "quality") == CodenameOptionsQualityCompat.CUSTOM
   && Reflect.field(native, "week6PixelPerfect") == false
   && Reflect.field(native, "naughtyness") == false
   && Reflect.field(native, "volumeMusic") == 0.3
   && Reflect.field(native, "volumeSFX") == 0.4
   && Reflect.field(native, "useCharColor") == false
   && Reflect.field(native, "untouched") == "keep",
   "Codename facade did not persist supported edits exclusively");
  check(PlayerSettings.player1.controls.getKeyboardBindingsByName("LEFT").join(",") == "74,75",
   "P1/P2 writes did not update primary and alternate runtime keys on the same native action");
  check(PlayerSettings.player2.controls.getKeyboardBindingsByName("LEFT").join(",") == "65,37",
   "Codename P1/P2 fields must not rewrite the separate player two control set");
  check(flixel.FlxG.save.data.keys.left.join(",") == "74,75",
   "Codename note keys were not persisted in the existing native key save shape");
  check(flixel.FlxG.save.data.codenameMenuKeys.left.join(",") == "74,75",
   "Codename note key slots were not persisted separately");
  check(flixel.FlxG.save.data.codenameMenuKeys.left_menu.join(",") == "76,77",
   "Codename UI keys were not isolated in their persistent menu binding map");
  check(flixel.FlxG.save.flushes == 4,
   "each explicitly saved key edit should flush the private save object");
  check(flixel.FlxG.autoPause == false && flixel.FlxG.updateFramerate == 144
   && flixel.FlxG.drawFramerate == 144 && !flixel.FlxG.fixedTimestep
   && !flixel.FlxSprite.defaultAntialiasing
   && !new flixel.FlxSprite().antialiasing,
   "applySettings did not update native runtime equivalents and the default on new sprites");
  check(flixel.FlxG.sound.defaultMusicGroup.volume == 0.3
   && flixel.FlxG.sound.defaultSoundGroup.volume == 0.4,
   "Codename music/SFX volume edits did not update their matching Flixel groups");
  check(options.gameplayShaders == false && options.lowMemoryMode == true
   && options.gpuOnlyBitmaps == false && options.week6PixelPerfect == false
   && options.quality == CodenameOptionsQualityCompat.CUSTOM,
   "Codename gameplay option edits must remain available on the detached facade");
  var reloadedOptions = new CodenameOptionsFacade();
  check(reloadedOptions.downscroll == false && reloadedOptions.ghostTapping == true
   && reloadedOptions.songOffset == 55 && reloadedOptions.framerate == 144
   && reloadedOptions.autoPause == false && reloadedOptions.antialiasing == false
   && reloadedOptions.gameplayShaders == false && reloadedOptions.lowMemoryMode == true
   && reloadedOptions.gpuOnlyBitmaps == false && reloadedOptions.naughtyness == false
   && reloadedOptions.volumeMusic == 0.3 && reloadedOptions.volumeSFX == 0.4
   && reloadedOptions.colorHealthBar == false && reloadedOptions.week6PixelPerfect == false
   && reloadedOptions.quality == CodenameOptionsQualityCompat.CUSTOM,
   "a fresh facade did not reload the persisted checkbox and stepper edits");
  var sourceReads = CodenameScriptParser.prepare(
   'function hl17FeatureChoices() { '
   + 'var shaderChoice = Options.gameplayShaders ? "make-shader" : "skip-shader"; '
   + 'var stageChoice = Options.lowMemoryMode ? "skip-flx3d" : "make-flx3d"; '
   + 'return shaderChoice + ":" + stageChoice; }', new Map(),
   "HL17-shared-options-probe");
  check(sourceReads.program != null && sourceReads.sourceUseDiagnostics.length == 0,
   "source-equivalent HL17 option reads did not prepare cleanly");
  interp.variables.set("Options", reloadedOptions);
  interp.execute(sourceReads.program);
  var featureChoices:Dynamic = interp.variables.get("hl17FeatureChoices");
  check(featureChoices() == "skip-shader:skip-flx3d",
   "fresh HL17 scripts did not observe saved gameplayShaders/lowMemoryMode values");
  options.P1_NOTE_LEFT = [0]; options.save();
  var reloaded = new CodenameOptionsFacade();
  check(reloaded.P1_NOTE_LEFT[0] == 0 && reloaded.P2_NOTE_LEFT[0] == 75,
   "unbind of primary note key shifted the alternate into primary after reload");
  check(flixel.FlxG.save.data.codenameMenuKeys.left.join(",") == "0,75"
   && flixel.FlxG.save.data.keys.left.join(",") == "75"
   && PlayerSettings.player1.controls.getKeyboardBindingsByName("LEFT").join(",") == "75",
   "sparse note key slots were not preserved independently from active native keys");
  var saved = flixel.FlxG.save; flixel.FlxG.save = null;
  options.P1_LEFT = [78]; options.save();
  flixel.FlxG.save = saved; options.save();
  check(flixel.FlxG.save.data.codenameMenuKeys.left_menu.join(",") == "78,77",
   "failed UI-key persistence was snapshotted and could not retry");
  check(flixel.FlxG.save.flushes == 6,
   "successful control saves and retry should flush exactly six times");
 }
}
''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(base),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"),
                 "--run", "Main"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[codename-options-effect-unsupported]", result.stdout + result.stderr)
        self.assertNotIn("read returns null", result.stdout + result.stderr,
                         "constructing a facade must not claim unused fields were read")
        self.assertIn("Persisted native edits: quality, downscroll, useCustomInput, offset, zoomCamera, fpsCap, flashingLights, naughtyness, volumeMusic, volumeSFX, useCharColor, autoPause, week6PixelPerfect, antialiasing, gameplayShaders, lowMemoryMode, gpuOnlyBitmaps, P1_NOTE_LEFT, P2_NOTE_LEFT, P1_LEFT, P2_LEFT.", result.stdout + result.stderr)
        self.assertIn("gpuOnlyBitmaps was saved, but this engine has no GPU-only bitmap backend", result.stdout + result.stderr)
        self.assertNotIn("No native adapter for Options.autoPause", result.stdout + result.stderr)
        self.assertIn("Persisted native edits", result.stdout + result.stderr)
        self.assertIn("codename-options-applied", result.stdout + result.stderr)
        self.assertIn("audio groups", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
