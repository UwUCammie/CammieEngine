"""Round 24 HXC native-object adapters and mounted selected-song regressions."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
HAXE = ROOT / ".tools/haxe/haxe"


def hx_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


@unittest.skipUnless(HAXE.is_file(), "portable Haxe toolchain unavailable")
class HxcRound24NativeAdapterTest(unittest.TestCase):
    def run_fixture(self, source: str) -> subprocess.CompletedProcess:
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="hxc-round24-native-", dir=ROOT / "tmp") as folder:
            main = Path(folder) / "Main.hx"
            main.write_text(source)
            env = os.environ.copy()
            env["TMPDIR"] = str(ROOT / "tmp")
            return subprocess.run(
                [
                    str(HAXE), "-cp", str(ROOT / "source"), "-cp", folder,
                    "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                    "-main", "Main", "--interp",
                ], cwd=ROOT, env=env, capture_output=True, text=True, timeout=300,
            )

    def test_current_chart_notes_uses_copied_native_difficulty_view(self):
        donor = '''class SideSwap extends Song {
          function swapNotes() {
            var notes:Array<SongNoteData> = PlayState.instance.currentChart.notes;
            var other = currentPlayState.currentChart.notes;
            PlayState.instance.playerStrumline.applyNoteData(notes);
          }
        }'''
        main = f'''import hscript.Parser;
        class Main {{ static function main():Void {{
          var result = HxcCompat.analyze({hx_string(donor)}, "scripts/songs/side-swap.hxc");
          var code = result.generatedHscript;
          if (code.indexOf("PlayState.instance.hxcCurrentChartNotes()") < 0
            || code.indexOf("currentPlayState.hxcCurrentChartNotes()") < 0
            || code.indexOf(".currentChart.notes") >= 0)
            throw "current chart note snapshot was not lowered: " + code;
          new Parser().parseString(code);
        }} }}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_synthetic_native_objects_are_lowered_and_unknown_members_stay_diagnosed(self):
        donor = r'''
class NativeObjects extends Song {
  var sprite;
  var camera;
  var video;
  var wiggle;
  function onCreate(event) {
    sprite = new FunkinSprite(10, 20).makeSolidColor(64, 64, 0xFFFFFFFF);
    sprite = FunkinSprite.createSparrow(0, 0, 'stage/popup');
    camera = new FunkinCamera('foreign');
    video = new FunkinVideoSprite(12, 34);
    video.load(Paths.videos('background-loop'));
    video.bitmap.onEndReached.add(function() { video.bitmap.time = 0; video.play(); });
    TouchUtil.pressAction('LEFT');
    wiggle = new WiggleEffectRuntime(2, 4, 0.01, WiggleEffectType.DREAMY);
    sprite.shader = wiggle;
    FunkinSound.playOnce(Paths.sound('confirmMenu'), 0.5);
    FunkinSound.playMusic('freakyMenu', {startingVolume: 0.8, looped: true});
    FunkinSound.stopAllAudio();
  }
}
'''
        main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "scripts/songs/native-objects.hxc");
    var generated = result.generatedHscript;
    for (required in [
      "HxcCompatRuntime.createFunkinSprite(hxcAssetRoot",
      "HxcCompatRuntime.createFunkinSpriteSparrow(hxcAssetRoot",
      "HxcCompatRuntime.createFunkinCamera(",
      "HxcCompatRuntime.createFunkinVideoSprite(PlayState.instance, hxcAssetRoot, 12, 34)",
      "HxcCompatRuntime.touchPressAction('LEFT')",
      "HxcCompatRuntime.createWiggleEffect(",
      "HxcCompatRuntime.freeplayPlaySound(",
      "HxcCompatRuntime.freeplayPlayMusic(",
      "HxcCompatRuntime.stopAllAudio()",
      "makeGraphic(64, 64, 0xFFFFFFFF)",
      "sprite.shader = wiggle.shader"])
      if (generated.indexOf(required) < 0) fail("missing native object adapter: " + required + "\\n" + generated);
    if (generated.indexOf("new FunkinSprite") >= 0 || generated.indexOf("new FunkinVideoSprite") >= 0
      || generated.indexOf("FunkinSound.playOnce") >= 0
      || generated.indexOf("WiggleEffectType.DREAMY") >= 0)
      fail("raw V-Slice object escaped: " + generated);
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == "unsupported-hxc-api") fail("supported object diagnosed: " + finding.message);

    var unsupported = HxcCompat.analyze(
      "class Unsupported extends Song {{ function onCreate(event) {{ FunkinSound.playBad(); FunkinCamera.makeBad(); WiggleEffectType.UNKNOWN; }} }}",
      "scripts/songs/unsupported-native-objects.hxc");
    var sawSound = false;
    var sawCamera = false;
    var sawWiggle = false;
    for (finding in (cast unsupported.diagnostics:Array<Dynamic>))
      if (finding.code == "unsupported-hxc-api") {{
        sawSound = sawSound || finding.message.indexOf("FunkinSound.playBad") >= 0;
        sawCamera = sawCamera || finding.message.indexOf("FunkinCamera.makeBad") >= 0;
        sawWiggle = sawWiggle || finding.message.indexOf("WiggleEffectType.UNKNOWN") >= 0;
      }}
    if (!sawSound || !sawCamera || !sawWiggle) fail("unsupported object diagnostics missing");

    var unsupportedStrumline = HxcCompat.analyze(
      "class UnsupportedStrumline extends Song {{ function onCreate(event) {{ PlayState.instance.playerStrumline = new ForeignStrumline(); }} }}",
      "scripts/songs/unsupported-strumline.hxc");
    var sawStrumlineAssignment = false;
    for (finding in (cast unsupportedStrumline.diagnostics:Array<Dynamic>))
      if (finding.code == "unsupported-hxc-api"
        && finding.message.indexOf("playerStrumline assignment is read-only") >= 0)
        sawStrumlineAssignment = true;
    if (!sawStrumlineAssignment) fail("unsafe strumline assignment was not diagnosed");
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_runtime_facades_reject_foreign_roots_and_preserve_wiggle_parameters(self):
        main = r'''class WiggleEffect {
  public var waveFrequency:Float = 0;
  public var waveAmplitude:Float = 0;
  public var waveSpeed:Float = 0;
  public var effectType:Dynamic;
  public function new() {}
}
class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    if (HxcCompatRuntime.createFunkinSprite('', 0, 0) != null) fail('empty sprite root escaped');
    if (HxcCompatRuntime.createFunkinSprite('../outside', 0, 0) != null) fail('traversal sprite root escaped');
    var effect = HxcCompatRuntime.createWiggleEffect(2, 4, 0.01, 'DREAMY');
    if (effect == null || effect.waveFrequency != 2 || effect.waveAmplitude != 4 || effect.waveSpeed != 0.01)
      fail('wiggle adapter metadata');
  }
}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_selected_native_object_scripts_are_lowered_without_mutating_donor(self):
        paths = [
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/stages/wilted.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/stages/schoolDDTO.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/songs/bara-no-yume.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/songs/constricted.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/songs/love-n-funkin.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/songs/you-and-me.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/songs/catfight.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/songs/dokidoggle.hxc",
        ]
        if not all(path.is_file() for path in paths):
            self.skipTest("selected DDTO HXC donors are not mounted")
        before = {path: path.read_bytes() for path in paths}
        encoded = ",\n".join(hx_string(str(path)) for path in paths)
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var paths = [{encoded}];
    for (path in paths) {{
      var result = HxcCompat.analyze(sys.io.File.getContent(path), path);
      var generated = result.generatedHscript == null ? "" : result.generatedHscript;
      new Parser().parseString(generated);
      if (path.toLowerCase().indexOf("catfight.hxc") >= 0
        && (generated.indexOf("PlayState.instance.hxcCurrentChartNotes()") < 0
          || generated.indexOf(".currentChart.notes") >= 0))
        fail("Catfight chart-side data bridge was not retained\\n" + generated);
        if (path.toLowerCase().indexOf("dokidoggle.hxc") >= 0) {{
        if (generated.indexOf("new ExtraStrumlineAdapter(") < 0 || generated.indexOf("applyNoteData(") < 0)
          fail("DokiDoggle extra strumline adapter was not retained\\n" + generated);
        if (generated.indexOf("HxcCompatRuntime.configureNativeStrumline(PlayState.instance, \\\"player\\\"") < 0
          || generated.indexOf("HxcCompatRuntime.configureNativeStrumline(PlayState.instance, \\\"opponent\\\"") < 0
          || generated.indexOf("HxcCompatRuntime.refreshNativeStrumlines(PlayState.instance)") < 0)
          fail("DokiDoggle native strumline reconfiguration route was not emitted\\n" + generated);
        if (generated.indexOf("playerStrumline =") >= 0 || generated.indexOf("opponentStrumline =") >= 0)
          fail("DokiDoggle attempted to assign read-only native strumlines\\n" + generated);
        for (finding in (cast result.diagnostics:Array<Dynamic>))
          if (finding.code == "unsupported-hxc-api"
            && (finding.message.indexOf("Strumline") >= 0 || finding.message.indexOf("NoteStyle") >= 0))
            fail("DokiDoggle strumline API was rejected: " + finding.message);
      }}
      if (generated.indexOf("FunkinSprite.create") >= 0 || generated.indexOf("new FunkinSprite") >= 0
        || generated.indexOf("new FunkinCamera") >= 0 || generated.indexOf("FunkinSound.playOnce") >= 0
        || generated.indexOf("new WiggleEffectRuntime") >= 0)
        fail("raw selected native object in " + path + "\\n" + generated);
    }}
    Sys.println("round24-mounted-native-ok");
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("round24-mounted-native-ok", result.stdout)
        for path, content in before.items():
            self.assertEqual(content, path.read_bytes())


if __name__ == "__main__":
    unittest.main()
