"""Bounded HXC shader callback and zero-duration camera compatibility."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DDTO = (Path("/run/media/cammie/External Storage/FNF-Example-Mods") /
        "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE")
MARKOV = DDTO / "scripts/songs/markov-lyrics.hxc"


def hx_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


class HxcShaderCallbackLoweringTest(unittest.TestCase):
    def _run(self, main: str, *args: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory(prefix="hxc-shader-callback-", dir=ROOT / "tmp") as folder:
            source = Path(folder) / "Main.hx"
            source.write_text(main)
            command = [str(HAXE), "-cp", str(ROOT / "source"),
                       "-cp", str(ROOT / ".haxelib/hscript/2,5,0"), "-cp", folder,
                       "--run", "Main", *args]
            return subprocess.run(command, cwd=ROOT, capture_output=True,
                                  text=True, timeout=120)

    def test_source_backed_boolean_filter_switch_preserves_order_and_rejects_unknowns(self):
        source = '''import flixel.addons.display.FlxRuntimeShader;
import openfl.filters.ShaderFilter;
import openfl.utils.Assets;
import funkin.Paths;
import funkin.play.PlayState;
import funkin.play.song.Song;
import funkin.modding.module.Module;
import funkin.save.Save;
class FilterChoiceSong extends Song {
  var first = new FlxRuntimeShader(Assets.getText(Paths.frag("First")));
  var firstFilter = new ShaderFilter(first);
  var second = new FlxRuntimeShader(Assets.getText(Paths.frag("Second")));
  var secondFilter = new ShaderFilter(second);
  function new() { super("fixture"); save = ColorPreferences.getColorSave(); }
  function onCountdownStart(event) {
    super.onCountdownStart(event);
    first.setFloat("strength", 0.5);
    second.setFloat("strength", 0.25);
    var selected = switch (save.enabled) {
      case true: [firstFilter, secondFilter];
      case false: [secondFilter];
    }
    PlayState.instance.camGame.filters = selected;
  }
}
class ColorPreferences extends Module {
  var defaultOptions = {enabled: true};
  function new() {
    super("ColorPreferences", 1);
    if (!Save.instance.modOptions.exists("ColorOptions"))
      Save.instance.modOptions.set("ColorOptions", defaultOptions);
    save = Save.instance.modOptions.get("ColorOptions");
  }
  public static function getColorSave() { return Save.instance.modOptions.get("ColorOptions"); }
}'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(message:String):Void throw message;
  static function countdown(result:Dynamic):Dynamic {{
    for (callback in (cast result.callbackAdapters:Array<Dynamic>))
      if (callback.sourceName == "onCountdownStart") return callback;
    return null;
  }}
  static function main() {{
    var source = {hx_string(source)};
    var accepted = HxcCompat.analyze(source, "scripts/songs/filter-choice.hxc");
    var callback = countdown(accepted);
    var body:String = callback == null ? "" : callback.body;
    if (callback == null || !callback.safe
      || body.indexOf("preferenceEnabled(save, \\\"enabled\\\")") < 0
      || body.indexOf("switch (save.enabled)") >= 0
      || body.indexOf("\\\"first\\\"") < 0 || body.indexOf("\\\"second\\\"") < 0
      || body.indexOf("HxcCompatRuntime.assignFilters(PlayState.instance.camGame, selected)") < 0)
      fail("bounded boolean filter switch did not preserve source behavior: " + body);
    for (finding in accepted.diagnostics)
      if ((finding.code == "unsupported-hxc-callback-body"
          || finding.code == "unsupported-hxc-shader-callback")
        && finding.message.indexOf("onCountdownStart") >= 0)
        fail("safe preference switch retained warning: " + finding.message);
    new Parser().parseString(accepted.generatedHscript);

    var reversed = HxcCompat.analyze(StringTools.replace(source,
      "case true: [firstFilter, secondFilter];\\n      case false: [secondFilter];",
      "case false: [secondFilter];\\n      case true: [firstFilter, secondFilter];"),
      "scripts/songs/filter-choice.hxc");
    var reversedCallback = countdown(reversed);
    if (reversedCallback == null || !reversedCallback.safe
      || reversedCallback.body != body)
      fail("source case order changed the selected filter lists");

    var dynamicFilter = HxcCompat.analyze(StringTools.replace(source,
      "[firstFilter, secondFilter]", "[chooseFilter(), secondFilter]"),
      "scripts/songs/filter-choice.hxc");
    if (countdown(dynamicFilter).safe)
      fail("dynamic filter expression escaped descriptor ownership");
    var unownedSave = HxcCompat.analyze(StringTools.replace(source,
      "ColorPreferences.getColorSave()", "External.getSave()"),
      "scripts/songs/filter-choice.hxc");
    if (countdown(unownedSave).safe)
      fail("unowned preference source escaped scoped save proof");
    var extraCameraWrite = HxcCompat.analyze(StringTools.replace(source,
      "PlayState.instance.camGame.filters = selected;",
      "PlayState.instance.camGame.filters = selected; PlayState.instance.camGame.filtersEnabled = false;"),
      "scripts/songs/filter-choice.hxc");
    if (countdown(extraCameraWrite).safe)
      fail("unowned camera filter state was silently accepted");
  }}
}}'''
        result = self._run(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_safe_local_helper_and_zero_duration_instant_ease_are_accepted(self):
        source = '''import flixel.addons.display.FlxRuntimeShader;
import openfl.filters.ShaderFilter;
import openfl.utils.Assets;
import funkin.Paths;
import funkin.play.PlayState;
import funkin.play.song.Song;
import flixel.tweens.FlxEase;
class CameraSong extends Song {
  var staticShader = new FlxRuntimeShader(Assets.getText(Paths.frag("StaticShader")));
  var filter = new ShaderFilter(staticShader);
  function resetScene():Void {
    PlayState.instance.playerStrumline.visible = true;
  }
  function onCountdownStart(event:Dynamic):Void {
    super.onCountdownStart(event);
    PlayState.instance.camGame.filters = [filter];
    resetScene();
    PlayState.instance.tweenCameraToPosition(4, 5, 0, FlxEase.instant);
  }
}'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(message:String):Void throw message;
  static function countdown(result:Dynamic):Dynamic {{
    for (callback in (cast result.callbackAdapters:Array<Dynamic>))
      if (callback.sourceName == "onCountdownStart") return callback;
    return null;
  }}
  static function main() {{
    var source = {hx_string(source)};
    var accepted = HxcCompat.analyze(source, "scripts/songs/camera-song.hxc");
    var callback = countdown(accepted);
    if (callback == null || !callback.safe)
      fail("bounded callback/helper was rejected: " + accepted.diagnostics);
    if (Std.string(callback.body).indexOf("resetScene()") < 0
      || Std.string(callback.body).indexOf("tweenCameraToPosition(4, 5, 0)") < 0
      || Std.string(callback.body).indexOf("FlxEase.instant") >= 0)
      fail("safe helper or exact zero-duration call lowering failed: " + callback.body);
    for (finding in accepted.diagnostics)
      if ((finding.code == "unsupported-hxc-shader-callback"
          || finding.code == "unsupported-hxc-callback-body")
        && finding.message.indexOf("onCountdownStart") >= 0)
        fail("accepted callback kept an unsupported warning: " + finding.message);
    new Parser().parseString(accepted.generatedHscript);

    var nonzero = HxcCompat.analyze(StringTools.replace(source, 
      "tweenCameraToPosition(4, 5, 0, FlxEase.instant)",
      "tweenCameraToPosition(4, 5, 1, FlxEase.instant)"), "scripts/songs/camera-song.hxc");
    var nonzeroCallback = countdown(nonzero);
    if (nonzeroCallback == null || nonzeroCallback.safe
      || Std.string(nonzeroCallback.body).indexOf("tweenCameraToPosition(4, 5, 1, FlxEase.instant)") < 0)
      fail("nonzero-duration easing call was broadened: " + nonzeroCallback.body);

    var dynamicEase = HxcCompat.analyze(StringTools.replace(source, 
      "tweenCameraToPosition(4, 5, 0, FlxEase.instant)",
      "tweenCameraToPosition(4, 5, 0, chooseEase())"), "scripts/songs/camera-song.hxc");
    var dynamicCallback = countdown(dynamicEase);
    if (dynamicCallback == null || dynamicCallback.safe
      || Std.string(dynamicCallback.body).indexOf("tweenCameraToPosition(4, 5, 0, chooseEase())") < 0)
      fail("dynamic easing call was broadened: " + dynamicCallback.body);
  }}
}}'''
        result = self._run(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_arbitrary_shader_pulse_helper_lowers_contract_and_keeps_unknown_operations_visible(self):
        source = '''import openfl.utils.Assets;
import openfl.filters.ShaderFilter;
import flixel.addons.display.FlxRuntimeShader;
import flixel.tweens.FlxTween;
import flixel.tweens.FlxEase;
import flixel.util.FlxTimer;
import funkin.Paths;
import funkin.audio.FunkinSound;
import funkin.play.PlayState;
import funkin.play.song.Song;
class PulseProbe extends Song {
  var fieldNoise = new FlxRuntimeShader(Assets.getText(Paths.frag("Noise")));
  var filterNoise = new ShaderFilter(fieldNoise);
  var opacity:Float = 0;
  function applyFilter(event) {
    PlayState.instance.camGame.filters = [filterNoise];
  }
  function onUpdate(event) {
    fieldNoise.setFloat("opacity", opacity);
  }
  function pulseVisual(duration:Float, sound:String):Void {
    if (sound != null && sound.length > 0) FunkinSound.playOnce(Paths.sound(sound));
    PlayState.instance.camGame.filtersEnabled = true;
    FlxTween.num(0, 1, 0.25, {ease: FlxEase.quadOut}, function(value:Float) { opacity = value; });
    new FlxTimer().start(duration, function(tmr:FlxTimer) {
      PlayState.instance.camGame.filtersEnabled = false;
    });
  }
}'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(message:String):Void throw message;
  static function has(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function analyze(source:String):Dynamic
    return HxcCompat.analyze(source, "scripts/songs/pulse-probe.hxc");
  static function main() {{
    var accepted = analyze({hx_string(source)});
    var descriptor:Dynamic = accepted.runtimeShaderDescriptor;
    if (descriptor == null || descriptor.pulseHelper != "pulseVisual"
      || descriptor.pulseComplete != true || descriptor.pulseDuration != 0.25
      || descriptor.pulseEase != "quadOut" || descriptor.pulseUniform != "opacity")
      fail("generic pulse contract was not captured: " + descriptor);
    if (has(accepted, "unsupported-hxc-shader-pulse-body"))
      fail("fully recognized pulse helper kept a warning");
    var generated:String = accepted.generatedHscript;
    if (generated.indexOf("HxcCompatRuntime.isNonemptyString(sound)") < 0
      || generated.indexOf("hxcPaths.sound(sound)") < 0
      || generated.indexOf("FlxEase.quadOut") < 0
      || generated.indexOf("\\\"opacity\\\"") < 0)
      fail("pulse helper did not preserve guarded audio/ease/uniform semantics: " + generated);
    new Parser().parseString(generated);

    var partial = analyze(StringTools.replace({hx_string(source)},
      "PlayState.instance.camGame.filtersEnabled = true;",
      "unhandledVisualOperation();\\n    PlayState.instance.camGame.filtersEnabled = true;"));
    if (!has(partial, "unsupported-hxc-shader-pulse-body"))
      fail("unhandled pulse operation lost its explicit warning");
    var partialGenerated:String = partial.generatedHscript;
    if (partialGenerated.indexOf("function pulseVisual") < 0
      || partialGenerated.indexOf("unhandledVisualOperation") >= 0)
      fail("partial helper should emit only the bounded pulse contract: " + partialGenerated);
    new Parser().parseString(partialGenerated);
  }}
}}'''
        result = self._run(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_markov_pulse_helper_matches_source_contract(self):
        if not MARKOV.is_file():
            self.skipTest("DDTO++ Markov HXC donor is not mounted")
        source = MARKOV.read_text(errors="ignore")
        main = f'''import hscript.Parser;
class Main {{
  static function fail(message:String):Void throw message;
  static function has(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function countdown(result:Dynamic):Dynamic {{
    for (callback in (cast result.callbackAdapters:Array<Dynamic>))
      if (callback.sourceName == "onCountdownStart") return callback;
    return null;
  }}
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, {hx_string(str(MARKOV))});
    var callback = countdown(result);
    if (callback == null)
      fail("countdown callback adapter missing");
    if (Std.string(callback.body).indexOf("conductorUpdate") < 0
      || Std.string(callback.body).indexOf("tweenCameraToPosition(PlayState.instance.curStage.getDad().cameraFocusPoint.x, PlayState.instance.curStage.getDad().cameraFocusPoint.y, 0)") < 0
      || Std.string(callback.body).indexOf("FlxEase.instant") >= 0)
      fail("zero-duration camera ease was not lowered: " + callback.body);
    if (has(result, "unsupported-hxc-shader-pulse-body"))
      fail("fully recognized donor pulse helper kept a warning");
    var descriptor:Dynamic = result.runtimeShaderDescriptor;
    if (descriptor == null || descriptor.pulseHelper != "funnyGlitch"
      || descriptor.pulseComplete != true || descriptor.pulseSoundParameter != "sound")
      fail("source pulse contract was not recognized: " + descriptor);
    var generated:String = result.generatedHscript;
    if (generated.indexOf("HxcCompatRuntime.isNonemptyString(sound)") < 0
      || generated.indexOf("hxcPaths.sound(sound)") < 0
      || generated.indexOf("FlxEase.circOut") < 0
      || generated.indexOf("pulseShader(__hxcShaderHandle, 0, 1, 0.5, duration") < 0)
      fail("source behavior was not lowered into the native adapter: " + generated);
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == "unsupported-hxc-shader-pulse-body")
        fail("fully recognized pulse helper kept a warning: " + finding.message);
    new Parser().parseString(result.generatedHscript);
  }}
}}'''
        result = self._run(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
