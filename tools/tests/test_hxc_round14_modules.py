"""Mounted and synthetic coverage for the generic Round 14 HXC modules."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")


def hx_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


@unittest.skipUnless(HAXE.is_file(), "portable Haxe toolchain is not mounted")
class HxcRound14ModuleTest(unittest.TestCase):
    def run_fixture(self, source: str) -> subprocess.CompletedProcess:
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="hxc-round14-", dir=ROOT / "tmp") as folder:
            main = Path(folder) / "Main.hx"
            main.write_text(source)
            env = os.environ.copy()
            env["TMPDIR"] = str(ROOT / "tmp")
            return subprocess.run(
                [
                    str(HAXE),
                    "-cp", str(ROOT / "source"),
                    "-cp", folder,
                    "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                    "-main", "Main", "--interp",
                ],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )

    def test_hxc_weekday_uses_scoped_host_boundary(self):
        main = r'''class Main {
  static function main() {
    var source = "class ClockSong extends Song { function new() { super('clock'); } function onBeatHit(event) { if (Date.now().getDay() == 5) trace('friday'); } }";
    var result = HxcCompat.analyze(source, "songs/clock.hxc");
    if (result.generatedHscript.indexOf("HxcCompatRuntime.weekday()") < 0
      || result.generatedHscript.indexOf("Date.now()") >= 0)
      throw result.generatedHscript;
    Sys.println("weekday-bridge-ok");
  }
}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("weekday-bridge-ok", result.stdout)

    def test_mounted_round14_modules_are_bounded_and_parseable(self):
        paths = {
            "lyrics": DONOR / "v-slice/Wacky World UPDATE [V-Slice]/scripts/modules/eventHandlers/lyricsEventHandler.hxc",
            "vignette": DONOR / "v-slice/Wacky World UPDATE [V-Slice]/scripts/modules/eventHandlers/vignEventHandler.hxc",
            "soundtray": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/DokiSoundTray.hxc",
            "rpc": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/DiscordRPC.hxc",
            "preferences": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/DokiPreferences.hxc",
            "menu": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/DokiMenuOverrides.hxc",
        }
        if not all(path.is_file() for path in paths.values()):
            self.skipTest("Round 14 HXC donor fixtures are not mounted")
        before = {name: path.read_bytes() for name, path in paths.items()}
        sources = "\n".join(
            f'var {name} = HxcCompat.analyze({hx_string(path.read_text(errors="ignore"))}, {hx_string(str(path))});'
            for name, path in paths.items()
        )
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    {sources}
    var results = [lyrics, vignette, soundtray, rpc, preferences, menu];
    for (result in results) {{
      if (result.kind != "module" || !result.moduleSafe || !result.moduleInitializationSafe)
        fail("mounted module was not safely rooted: " + result.path + " :: " + result.moduleSafetyReasons.join(","));
      if (hasCode(result, "unsupported-hxc-module-body")
        || hasCode(result, "unsupported-hxc-callback-body")
        || hasCode(result, "hxc-unsupported-payload"))
        fail("mounted module retained unsupported body/payload: " + result.path);
      new Parser().parseString(result.generatedHscript);
    }}
    if (lyrics.generatedHscript.indexOf("HxcCompatRuntime.setLyricText") < 0
      || lyrics.generatedHscript.indexOf("HxcCompatRuntime.clearLyricText") < 0
      || lyrics.generatedHscript.indexOf("new FlxText") >= 0)
      fail("lyric host adapter");
    if (vignette.generatedHscript.indexOf("HxcCompatRuntime.prepareVignette") < 0
      || vignette.generatedHscript.indexOf("HxcCompatRuntime.setVignette") < 0
      || vignette.generatedHscript.indexOf("new ShaderFilter") >= 0)
      fail("vignette host adapter");
    if (soundtray.generatedHscript.indexOf("HxcCompatRuntime.configureSoundTray") < 0
      || soundtray.generatedHscript.indexOf("Assets.getBitmapData") >= 0)
      fail("sound-tray host adapter");
    if (rpc.generatedHscript.indexOf("HxcCompatRuntime.timestamp()") < 0
      || rpc.generatedHscript.indexOf("HxcCompatRuntime.discordRPCIcon") < 0)
      fail("RPC host adapter");
    if (preferences.generatedHscript.indexOf("HxcCompatRuntime.applyPreferencePage") < 0
      || preferences.generatedHscript.indexOf("Save.instance") >= 0)
      fail("preference host adapter");
    if (menu.generatedHscript.indexOf("HxcCompatRuntime.updateMenuOverrides") < 0
      || menu.generatedHscript.indexOf("HxcCompatRuntime.applyMenuOverrides") < 0
      || menu.generatedHscript.indexOf("HxcCompatRuntime.applyMenuRedirect") < 0
      || menu.generatedHscript.indexOf("optionsCodex") >= 0
      || menu.generatedHscript.indexOf("_requestedSubState") >= 0)
      fail("menu host adapter");
    if (menu.generatedHscript.indexOf('hxcDeferredStateFactory("DokiMainMenuState", [])') < 0)
      fail("menu transition state was constructed eagerly: " + menu.generatedHscript);
    Sys.println("round14-mounted-ok");
  }}
}}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("round14-mounted-ok", result.stdout)
        self.assertEqual(before, {name: path.read_bytes() for name, path in paths.items()})

    def test_synthetic_lyrics_and_vignette_adapters_execute_through_native_boundary(self):
        lyrics = r'''class GenericLyrics extends Module {
  var lyricLine;
  function new() { super("generic-lyrics"); }
  function createText(text, duration, textColor, font, fontSize, isItalic, isBold,
      hasAntiAliasing, isCentered, opacity, letterSpacing, textBorderColor,
      borderSize, isBehindStrumLines) {
    lyricLine = new FlxText(0, 0, FlxG.width);
    lyricLine.setFormat(font, fontSize, textColor, "center", textBorderColor, borderSize);
    lyricLine.screenCenter();
  }
  function onSongRetry(event) {
    if (lyricLine != null) { lyricLine.kill(); lyricLine.destroy(); lyricLine = null; }
  }
}'''
        vignette = r'''class GenericVignette extends Module {
  var vignShader;
  var vignFilter;
  var intensity_tween;
  function new() { super("generic-vignette"); }
  function onSongStart(event) {
    vignShader = ScriptedFlxRuntimeShader.init("VignEffect");
    vignFilter = new ShaderFilter(vignShader);
    FlxG.camera.filters = [vignFilter];
  }
  function onSongRetry(event) {
    if (vignShader != null) { FlxG.camera.filters?.remove(vignFilter); vignShader = null; }
  }
  function createVig(intensity, duration, ease) {
    intensity_tween = FlxTween.num(vignShader?.scriptGet("uIntensity"), intensity,
      duration, {ease: ease}, function(value) { vignShader?.scriptCall("setIntensity", [value]); });
  }
  function onPause(event) { FlxTweenUtil.pauseTween(intensity_tween); }
  function onResume(event) { FlxTweenUtil.resumeTween(intensity_tween); }
}'''
        main = f'''import hscript.Interp;
import hscript.Parser;
class PlayState {{
  public static var instance:PlayState;
  public var lyricCalls:Int = 0;
  public var lyricClears:Int = 0;
  public var vignettePrepares:Int = 0;
  public var vignetteClears:Int = 0;
  public var vignettePauses:Int = 0;
  public var vignetteResumes:Int = 0;
  public var vignetteTweens:Int = 0;
  public function new() {{}}
  public function hxcSetLyricText(values:Array<Dynamic>, second:Bool):Bool {{ lyricCalls++; return values != null && values.length > 0; }}
  public function hxcClearLyricText():Bool {{ lyricClears++; return true; }}
  public function hxcPrepareVignette():Bool {{ vignettePrepares++; return true; }}
  public function hxcClearVignette():Bool {{ vignetteClears++; return true; }}
  public function hxcPauseVignette():Bool {{ vignettePauses++; return true; }}
  public function hxcResumeVignette():Bool {{ vignetteResumes++; return true; }}
  public function hxcSetVignette(values:Array<Dynamic>):Bool {{ vignetteTweens++; return values != null; }}
}}
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var lyricResult = HxcCompat.analyze({hx_string(lyrics)}, "synthetic/scripts/modules/generic-lyrics.hxc");
    var vignetteResult = HxcCompat.analyze({hx_string(vignette)}, "synthetic/scripts/modules/generic-vignette.hxc");
    for (result in [lyricResult, vignetteResult]) {{
      if (!result.moduleSafe || !result.moduleInitializationSafe
        || hasCode(result, "unsupported-hxc-module-body")
        || hasCode(result, "unsupported-hxc-callback-body"))
        fail("synthetic module safety: " + result.moduleSafetyReasons.join(","));
      new Parser().parseString(result.generatedHscript);
    }}
    PlayState.instance = new PlayState();
    var lyricInterp = new Interp();
    lyricInterp.variables.set("HxcCompatRuntime", HxcCompatRuntime);
    lyricInterp.variables.set("PlayState", PlayState);
    lyricInterp.execute(new Parser().parseString(lyricResult.generatedHscript));
    var createText:Dynamic = lyricInterp.variables.get("createText");
    Reflect.callMethod(null, createText, ["hello", 0.5, 0xFFFFFFFF, "vcr", 24, false, false, true, true, 1.0, 0.0, 0xFF000000, 1.0, false]);
    var retry:Dynamic = lyricInterp.variables.get("songRetry");
    Reflect.callMethod(null, retry, [null]);
    if (PlayState.instance.lyricCalls != 1 || PlayState.instance.lyricClears != 1)
      fail("synthetic lyric execution");

    var vignetteInterp = new Interp();
    vignetteInterp.variables.set("HxcCompatRuntime", HxcCompatRuntime);
    vignetteInterp.variables.set("PlayState", PlayState);
    vignetteInterp.execute(new Parser().parseString(vignetteResult.generatedHscript));
    Reflect.callMethod(null, vignetteInterp.variables.get("songStart"), [null]);
    Reflect.callMethod(null, vignetteInterp.variables.get("createVig"), [0.8, 0.25, "linear"]);
    Reflect.callMethod(null, vignetteInterp.variables.get("pause"), [null]);
    Reflect.callMethod(null, vignetteInterp.variables.get("resume"), [null]);
    Reflect.callMethod(null, vignetteInterp.variables.get("songRetry"), [null]);
    if (PlayState.instance.vignettePrepares != 1 || PlayState.instance.vignetteTweens != 1
      || PlayState.instance.vignettePauses != 1 || PlayState.instance.vignetteResumes != 1
      || PlayState.instance.vignetteClears != 1)
      fail("synthetic vignette execution");
    Sys.println("round14-synthetic-ok");
  }}
}}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("round14-synthetic-ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
